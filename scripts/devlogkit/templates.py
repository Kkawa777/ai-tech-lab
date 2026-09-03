"""Per-type Japanese article rendering (Phase 2, docs/devlog-policy.md
15節). Replaces Phase 1's single flat "commit list" body with a structure
chosen by classify.classify_day_type(), built only from CONFIRMED_GIT_FACT
(commit metadata) and the Sanitized Change Summary (sanitize.py) — never
from invented motivation. Any section this module cannot support with
evidence is simply omitted, per Step 8's Fact rule.
"""
from . import classify, ja

CONVENTIONAL_PREFIX = None  # set by caller before clean_subject is used elsewhere


def clean_subject(subject):
    import re
    return re.sub(
        r"^(feat|fix|perf|refactor|docs|chore|style|test|build|ci)(\([^)]*\))?:\s*",
        "", subject, flags=re.IGNORECASE,
    ).strip()


def translated_or_original(cleaned_subject):
    """Try to translate one already-`clean_subject()`-ed commit subject to
    natural Japanese; return the original (English) subject unchanged if
    it doesn't meet ja.coverage_is_usable()'s bar. Shared by build_headline
    (title) and pipeline.py (description/primary_keyword) so a day's
    `description` doesn't silently stay 100% untranslated English while
    its `title` is fully Japanese — an independent review (Phase 2.6)
    found that specific inconsistency read as a generation bug rather
    than a consistent, honest fallback."""
    phrase, coverage, token_count, _object_phrase = ja.translate_subject(cleaned_subject)
    if ja.coverage_is_usable(coverage, token_count):
        return phrase, True
    return cleaned_subject, False


def derive_topic_keyword(notable):
    """Try each notable commit's subject (chronological order, same
    selection strategy as build_headline) and return the first one's
    translated NOUN PHRASE (no verb suffix, e.g. "収益化・分析基盤" rather
    than "収益化・分析基盤を開始しました") that meets
    ja.coverage_is_usable(). Used so primary_keyword/search_intent can be
    content-specific instead of a fixed day_type label repeated
    identically across every devlog article of the same type — an
    independent review (Phase 2.7) flagged exact primary_keyword/
    search_intent duplication across different articles as a real SEO
    keyword-cannibalization risk, not just a cosmetic one.

    Returns None if no commit's subject translates cleanly — callers keep
    their existing day_type-label fallback in that case."""
    for commit in notable:
        subject = clean_subject(commit["subject"])
        phrase, coverage, token_count, object_phrase = ja.translate_subject(subject)
        if ja.coverage_is_usable(coverage, token_count):
            return object_phrase
    return None


def _select_headline_phrase(notable):
    """The single (phrase, used_japanese, coverage) choice that represents
    this day. Shared by build_headline (title) and describe_day
    (description) so the two can NEVER disagree about whether Japanese
    translation succeeded — an independent review (Phase 2.6, then again
    Phase 2.7) found that translating title and description independently
    let them land on different languages for the exact same day (e.g.
    title fully Japanese because ONE commit qualified, description fully
    English because the OTHER commits that same day didn't), which read
    as a generation bug rather than a deliberate, consistent choice.

    Tries EVERY notable commit's subject (chronological order, so the
    result stays deterministic) and returns the first one that produces a
    usable translation (ja.coverage_is_usable — Phase 2.5 finding: a
    subject with 8+ concepts translates to a word-salad even at full
    dictionary coverage). Falls back to the Phase 1 verbatim-English style
    using the commit with the most changed lines (the most substantial
    change of the day) if none qualify.
    """
    for commit in notable:
        subject = clean_subject(commit["subject"])
        phrase, coverage, token_count, _object_phrase = ja.translate_subject(subject)
        if ja.coverage_is_usable(coverage, token_count):
            return phrase, True, coverage

    biggest = max(notable, key=lambda c: c["stat"]["insertions"] + c["stat"]["deletions"])
    return clean_subject(biggest["subject"]), False, 0.0


def build_headline(display_name, notable):
    """Returns (title_text, used_japanese: bool, coverage_used: float).

    Deliberately does NOT append a "(ほか N件の変更)" change-count suffix
    to the title (Phase 2.7, independent review): that reads as an
    operational log-entry marker, not something a human would title a
    blog post. The count is still stated naturally in describe_day's
    sentence, and every commit is still listed in full in the body — no
    information is lost, just moved to where it reads naturally."""
    phrase, used_japanese, coverage = _select_headline_phrase(notable)
    if used_japanese:
        return f"{display_name}: {phrase}", True, coverage
    return f"{display_name} 開発ログ: {phrase}", False, 0.0


def describe_day(date_str, display_name, notable):
    """One-sentence meta description, built from the SAME headline choice
    as the title (see _select_headline_phrase's docstring for why) —
    never independently re-translates every commit subject the way an
    earlier version did, so it can't land on a different language than
    the title. Matches the title's own level of summarization (naming one
    representative change plus a change count) rather than trying to
    enumerate every commit's subject in one sentence, which read as an
    unwieldy comma-list on a multi-commit day."""
    phrase, _used_japanese, _coverage = _select_headline_phrase(notable)
    extra = f"(ほか{len(notable) - 1}件の変更も含みます)" if len(notable) > 1 else ""
    return (
        f"{date_str}に{display_name}リポジトリで行われた開発のログです。"
        f"Git履歴とdiffから確認できる変更: {phrase}{extra}。"
    )


def _file_list_line(commit, already_detailed, max_files=10):
    files = [f for f in commit["files"] if f["path"] not in already_detailed]
    if not files:
        return None
    shown = "、".join(f"`{f['path']}`" for f in files[:max_files])
    more = f" ほか{len(files) - max_files}件" if len(files) > max_files else ""
    return f"`{commit['hash'][:7]}`: {shown}{more}"


def _changed_files_section(notable, summary):
    """Phase 2.7: skip files already shown with detail in "ファイル別の
    変更点" (per_file_signals — functions/classes/tests/headings/config
    keys) above. Showing the same path twice — once with real detail,
    once bare — read as redundant repetition. Only files with no
    extracted signal there (images, other assets, etc.) are listed here,
    so this section adds NEW information instead of repeating it. If
    every touched file was already detailed above, the section is omitted
    entirely rather than rendered empty.

    The exclusion is scoped PER COMMIT (matched by commit_hash), not to a
    day-wide union of paths — an independent review caught a real bug in
    an earlier version of this function that used a day-wide set: when
    the SAME path is touched by multiple commits in one day but only ONE
    of those commits' own diff produced a per_file_signals entry for it
    (e.g. only one of three commits touching an article file happened to
    change its frontmatter), a day-wide set incorrectly hid that path from
    the OTHER commits' file lists too — even though those commits' own
    contribution to that file was never shown anywhere, silently dropping
    it from the article's declared file count entirely.

    Also excludes a path already shown in "変更前後" (behavior_pairs) —
    an independent review found this section had its own detail-vs-flat-
    list duplication (a before/after-detailed file was ALSO listed bare
    here) that the per_file_signals exclusion above didn't cover, since
    behavior_pairs is a separate data structure."""
    per_file = summary.get("per_file_signals", [])
    behavior_pairs = summary.get("behavior_pairs", [])
    bullets = []
    for c in notable:
        already_detailed_for_commit = {
            entry["path"] for entry in per_file if entry.get("commit_hash") == c["hash"]
        }
        already_detailed_for_commit |= {
            pair["path"] for pair in behavior_pairs
            if pair.get("commit_hash") == c["hash"] and pair.get("path")
        }
        line = _file_list_line(c, already_detailed_for_commit)
        if line:
            bullets.append(f"- {line}")
    if not bullets:
        return []
    return ["## 変更されたファイル", ""] + bullets + [""]


def _commit_bullet(commit):
    stat = commit["stat"]
    # Phase 2.7: run each commit's subject through the same translation
    # path as the title/description (falling back to the original English
    # when it doesn't meet ja.coverage_is_usable()) — previously this list
    # was the one place in the body that NEVER attempted translation, so
    # even a fully-Japanese-titled article still read as a raw commit-
    # message dump the moment a reader reached "今回追加された内容".
    subject, _ = translated_or_original(clean_subject(commit["subject"]))
    return (
        f"- `{commit['hash'][:7]}` {subject}"
        f"(変更ファイル{stat['files_changed']}件、+{stat['insertions']}/-{stat['deletions']})"
    )


def _change_composition_overview(summary):
    """One sentence giving a reader a quick sense of "what kinds of things
    changed" before the detailed per-file breakdown — a plain MECHANICAL
    COUNT of already-extracted signal categories (headings added, config
    keys changed, docs excerpts found, code-level signatures added), not
    an interpretation of what those changes MEAN or WHY they were made.
    Phase 2.7: independent review (twice) found the body reading as pure
    "Git変更の羅列" (a fragment dump) with no sentence at all connecting
    the commit list to the detailed breakdown below it; Phase 2.6 (§36)
    had deliberately omitted any such summary to avoid inventing meaning —
    a pure count avoids that risk (it states only what Git/sanitize.py
    already confirmed exists, never why, never what it accomplished), so
    it's added here instead of reworking that same design decision.

    Counts are summed DIRECTLY from `per_file_signals` / `docs_excerpts` —
    the SAME data the "ファイル別の変更点"/"README/ドキュメントの追記内容"
    sections below actually render — rather than from
    summary["headings_added"]/["config_keys_changed"]/etc., which are
    separately capped at sanitize.py's MAX_ITEMS_PER_LIST per commit and
    can therefore diverge from what's actually shown on a single-commit
    day (independent review caught a real instance: a day with 9 real
    headings had this sentence claim "8件" because the day-level list —
    used for scoring, not for this per-file-detail display — was
    truncated while per_file_signals, which the detail section reads,
    was not). `structural_files_changed` is deliberately NOT counted here:
    it has no corresponding detail section a reader could check the
    number against, unlike every other category in this sentence.

    Categories with a zero count are omitted entirely (Step 7: omit
    UNKNOWN/absent rather than noting the absence) — returns "" if every
    category is empty (nothing to summarize)."""
    per_file = summary.get("per_file_signals", [])
    headings_count = sum(len(e.get("headings", [])) for e in per_file)
    config_keys_count = sum(len(e.get("config_keys", [])) for e in per_file)
    code_signal_count = sum(
        len(e.get("functions", [])) + len(e.get("classes", [])) + len(e.get("tests", []))
        for e in per_file
    )
    docs_excerpts_count = len(summary.get("docs_excerpts", []))  # rendered from this exact list, so always in sync
    # behavior_pairs (Phase 2.7, independent review MINOR): unlike
    # structural_files_changed, this DOES have a corresponding detail
    # section ("変更前後") — omitting it from the count wasn't a
    # deliberate design choice, just an oversight in the first version of
    # this function.
    behavior_pairs_count = len(summary.get("behavior_pairs", []))

    parts = []
    if headings_count:
        parts.append(f"見出しの追加({headings_count}件)")
    if config_keys_count:
        parts.append(f"設定・frontmatterキーの変更({config_keys_count}件)")
    if docs_excerpts_count:
        parts.append(f"ドキュメントからの抜粋({docs_excerpts_count}件)")
    if code_signal_count:
        parts.append(f"関数・クラス・テストの追加({code_signal_count}件)")
    if behavior_pairs_count:
        parts.append(f"変更前後を確認できた箇所({behavior_pairs_count}件)")
    if not parts:
        return ""
    return f"この変更には、{'、'.join(parts)}が含まれています。"


def _evidence_section(summary):
    lines = []
    overview = _change_composition_overview(summary)
    if overview:
        lines.append(overview)
        lines.append("")
    per_file = summary.get("per_file_signals", [])
    if per_file:
        # Phase 2.5: attribute every extracted signal (function/class/test
        # names, added headings, changed config keys) to the file it came
        # from — an independent review of an earlier flat, day-wide list
        # (e.g. headings from two unrelated articles run together with no
        # indication which file each came from) found it unreadable and a
        # source of misleading juxtaposition. Grouping by path makes clear
        # which file each item belongs to, and a config-key-only entry
        # (otherwise a meaningless bare list of key names) now at least
        # says which file's frontmatter changed.
        lines.append("### ファイル別の変更点(diffから機械的に抽出)")
        lines.append("")
        for entry in per_file:
            parts = []
            if entry["functions"]:
                parts.append("関数 " + "、".join(f"`{n}`" for n in entry["functions"]))
            if entry["classes"]:
                parts.append("クラス " + "、".join(f"`{n}`" for n in entry["classes"]))
            if entry["tests"]:
                parts.append("テスト " + "、".join(f"`{n}`" for n in entry["tests"]))
            if entry.get("headings"):
                parts.append("見出し " + "、".join(f"「{h}」" for h in entry["headings"]))
            if entry.get("config_keys"):
                parts.append(
                    "設定キー " + "、".join(f"`{k}`" for k in entry["config_keys"])
                    + "(キー名のみ。値は転記していません)"
                )
            if parts:
                # Phase 2.7 (independent review, MINOR): attribute each
                # entry to its commit too, not just its path — the
                # underlying commit_hash was already tracked internally
                # (for the dedup fix in _changed_files_section) but never
                # surfaced, so a reader had to guess which commit produced
                # a given file's signal from context alone.
                commit_hash = entry.get("commit_hash", "")
                commit_ref = f"(`{commit_hash[:7]}`)" if commit_hash else ""
                lines.append(f"- `{entry['path']}`{commit_ref}: " + " / ".join(parts))
        lines.append("")
    if summary["tests_added"]:
        # Step 4 (docs/devlog-policy.md Phase 2.5): report only that tests
        # were ADDED — Git history shows this much, but never that they
        # were actually run/passed, since this generator never executes
        # any project's code (that would require allowlist-level explicit
        # opt-in this PoC does not implement).
        lines.append("### 検証")
        lines.append("")
        lines.append(
            f"このcommitで{len(summary['tests_added'])}件のテストが追加されたことをGit履歴から確認できます"
            "(実行結果・PASS/FAILはGit履歴からは確認できないため、本記事では言及していません)。"
        )
        lines.append("")
    if summary["docs_excerpts"]:
        lines.append("### README/ドキュメントの追記内容(抜粋)")
        lines.append("")
        for ex in summary["docs_excerpts"]:
            # Phase 2.7 (independent review, MAJOR): attribute the commit
            # too, not just the path — when the SAME path is touched by
            # multiple commits in one day, a reader had no way to tell
            # which commit's diff this excerpt actually came from.
            commit_ref = f"(`{ex['commit_hash'][:7]}`)" if ex.get("commit_hash") else ""
            lines.append(f"- `{ex['path']}`{commit_ref}:")
            lines.append(f"  > {ex['text']}")
        lines.append("")
    if summary["behavior_pairs"]:
        lines.append("### 変更前後(diffから確認できた範囲)")
        lines.append("")
        for pair in summary["behavior_pairs"]:
            # Same attribution fix as above, applied to before/after pairs
            # (an independent review found that without it, a heading-
            # level-change event here and an unrelated "new heading" in a
            # DIFFERENT file that happens to share the same template-
            # standard heading text elsewhere in the article were
            # indistinguishable from a genuine self-contradiction).
            source = f"`{pair['path']}`(`{pair['commit_hash'][:7]}`)" if pair.get("path") else None
            if source:
                lines.append(f"- {source}:")
            lines.append(f"  - 変更前: `{pair['before']}`")
            lines.append(f"  - 変更後: `{pair['after']}`")
        lines.append("")
    return lines


def _disclosure_line():
    # Phase 2.7, independent review: "設定キー" (frontmatter) recurs
    # throughout the body without ever being explained — a beginner
    # reader has no way to know it means "each記事の公開設定をまとめた
    # 部分の項目名". A one-clause gloss here (once, at the top) covers
    # every later mention without annotating each individual occurrence.
    return (
        "この記事は、Gitのcommit履歴とdiffから安全に抽出できる情報(commit・変更ファイル・"
        "関数/テスト名・README/ドキュメントの追記内容・記事の公開設定〈frontmatter〉の"
        "キー名など)をもとに自動生成された開発ログです。"
        "個人の体験談ではなく、確認できる事実のみに基づいています(詳細は"
        "[docs/devlog-policy.md](https://github.com/Kkawa777/ai-tech-lab/blob/main/docs/devlog-policy.md)"
        "を参照)。"
    )


def render_feature_body(display_name, notable, summary):
    lines = [_disclosure_line(), ""]
    lines.append("## 今回追加された内容")
    lines.append("")
    for c in notable:
        lines.append(_commit_bullet(c))
    lines.append("")
    lines.extend(_evidence_section(summary))
    lines.extend(_changed_files_section(notable, summary))
    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")
    return "\n".join(lines)


def render_bugfix_body(display_name, notable, summary):
    lines = [_disclosure_line(), ""]
    lines.append("## 修正されたcommit")
    lines.append("")
    for c in notable:
        lines.append(_commit_bullet(c))
    lines.append("")
    lines.append(
        "具体的な不具合の発生条件・原因の詳細は、Gitのcommit metadataからは確認できないため、"
        "本記事では記載していません(未確認)。"
    )
    lines.append("")
    lines.extend(_evidence_section(summary))
    lines.extend(_changed_files_section(notable, summary))
    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")
    return "\n".join(lines)


def render_performance_body(display_name, notable, summary):
    lines = [_disclosure_line(), ""]
    lines.append("## パフォーマンスに関する変更")
    lines.append("")
    for c in notable:
        lines.append(_commit_bullet(c))
    lines.append("")
    lines.append(
        "具体的な実測値(処理時間・メモリ使用量等)は、Gitのcommit metadataからは確認できないため、"
        "本記事では記載していません(未確認)。"
    )
    lines.append("")
    lines.extend(_evidence_section(summary))
    lines.extend(_changed_files_section(notable, summary))
    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")
    return "\n".join(lines)


def render_ui_body(display_name, notable, summary):
    lines = [_disclosure_line(), ""]
    lines.append("## UI/デザインに関する変更")
    lines.append("")
    for c in notable:
        lines.append(_commit_bullet(c))
    lines.append("")
    lines.extend(_evidence_section(summary))
    lines.extend(_changed_files_section(notable, summary))
    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")
    return "\n".join(lines)


def render_architecture_body(display_name, notable, summary):
    lines = [_disclosure_line(), ""]
    lines.append("## 構造・設計に関する変更")
    lines.append("")
    for c in notable:
        lines.append(_commit_bullet(c))
    lines.append("")
    lines.append(
        "設計変更の背景・トレードオフの詳細な理由は、Gitのcommit metadataからは確認できないため、"
        "本記事では記載していません(未確認)。"
    )
    lines.append("")
    lines.extend(_evidence_section(summary))
    lines.extend(_changed_files_section(notable, summary))
    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")
    return "\n".join(lines)


def render_generic_body(display_name, notable, summary):
    lines = [_disclosure_line(), ""]
    lines.append("## この日の変更")
    lines.append("")
    for c in notable:
        lines.append(_commit_bullet(c))
    lines.append("")
    lines.extend(_evidence_section(summary))
    lines.extend(_changed_files_section(notable, summary))
    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")
    return "\n".join(lines)


RENDERERS = {
    classify.FEATURE: render_feature_body,
    classify.BUGFIX: render_bugfix_body,
    classify.PERFORMANCE: render_performance_body,
    classify.UI: render_ui_body,
    classify.ARCHITECTURE: render_architecture_body,
    classify.GENERIC: render_generic_body,
}


def render_body(day_type, display_name, notable, summary):
    renderer = RENDERERS.get(day_type, render_generic_body)
    return renderer(display_name, notable, summary)
