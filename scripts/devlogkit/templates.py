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


def build_headline(display_name, notable):
    """Returns (title_text, used_japanese: bool, coverage_used: float).

    Phase 1/2.0 always translated notable[0] (the chronologically FIRST
    commit), which meant a multi-commit day's headline was whichever
    commit happened to land first, however long/complex its subject —
    Phase 2.5 found this produced unreadable titles on real data (a
    subject with 8+ concepts translates to a word-salad even at full
    dictionary coverage; see ja.MAX_TRANSLATABLE_TOKENS). Instead, try
    EVERY notable commit's subject and use the first one (in chronological
    order, so the result is still deterministic) that produces a usable
    translation; if none qualify, fall back to the Phase 1 verbatim style
    using the commit with the most changed lines (the most substantial
    change of the day, a better representative than "whichever came
    first" when nothing translates cleanly).
    """
    for commit in notable:
        subject = clean_subject(commit["subject"])
        phrase, coverage, token_count = ja.translate_subject(subject)
        if ja.coverage_is_usable(coverage, token_count):
            if len(notable) > 1:
                return f"{display_name}: {phrase}(ほか{len(notable) - 1}件の変更)", True, coverage
            return f"{display_name}: {phrase}", True, coverage

    # Fallback: Phase 1 style, verbatim English embedded in a Japanese
    # frame, using the day's most substantial commit as the headline.
    biggest = max(notable, key=lambda c: c["stat"]["insertions"] + c["stat"]["deletions"])
    top_subject = clean_subject(biggest["subject"])
    if len(notable) > 1:
        return f"{display_name} 開発ログ: {top_subject} ほか{len(notable) - 1}件", False, 0.0
    return f"{display_name} 開発ログ: {top_subject}", False, 0.0


def _file_list_line(commit, max_files=10):
    files = commit["files"]
    shown = "、".join(f"`{f['path']}`" for f in files[:max_files])
    more = f" ほか{len(files) - max_files}件" if len(files) > max_files else ""
    return f"`{commit['hash'][:7]}`: {shown}{more}"


def _commit_bullet(commit):
    stat = commit["stat"]
    return (
        f"- `{commit['hash'][:7]}` {clean_subject(commit['subject'])}"
        f"(変更ファイル{stat['files_changed']}件、+{stat['insertions']}/-{stat['deletions']})"
    )


def _evidence_section(summary):
    lines = []
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
                lines.append(f"- `{entry['path']}`: " + " / ".join(parts))
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
            lines.append(f"- `{ex['path']}`:")
            lines.append(f"  > {ex['text']}")
        lines.append("")
    if summary["behavior_pairs"]:
        lines.append("### 変更前後(diffから確認できた範囲)")
        lines.append("")
        for before, after in summary["behavior_pairs"]:
            lines.append(f"- 変更前: `{before}`")
            lines.append(f"- 変更後: `{after}`")
        lines.append("")
    return lines


def _disclosure_line():
    return (
        "この記事は、Gitのcommit履歴とdiffから安全に抽出できる情報(commit・変更ファイル・"
        "関数/テスト名・README/ドキュメントの追記内容など)をもとに自動生成された開発ログです。"
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
    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        lines.append(f"- {_file_list_line(c)}")
    lines.append("")
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
    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        lines.append(f"- {_file_list_line(c)}")
    lines.append("")
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
    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        lines.append(f"- {_file_list_line(c)}")
    lines.append("")
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
    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        lines.append(f"- {_file_list_line(c)}")
    lines.append("")
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
    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        lines.append(f"- {_file_list_line(c)}")
    lines.append("")
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
    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        lines.append(f"- {_file_list_line(c)}")
    lines.append("")
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
