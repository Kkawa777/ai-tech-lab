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
    """Returns (title_text, used_japanese: bool). Tries the deterministic
    JA translation of the day's primary (first) commit subject; falls back
    to the Phase 1 verbatim-English style when translation coverage is too
    low to read naturally (see ja.coverage_is_usable)."""
    top_subject = clean_subject(notable[0]["subject"])
    phrase, coverage = ja.translate_subject(top_subject)
    if ja.coverage_is_usable(coverage):
        if len(notable) > 1:
            return f"{display_name}: {phrase}(ほか{len(notable) - 1}件の変更)", True
        return f"{display_name}: {phrase}", True
    # Fallback: Phase 1 style, verbatim English embedded in a Japanese frame.
    if len(notable) > 1:
        return f"{display_name} 開発ログ: {top_subject} ほか{len(notable) - 1}件", False
    return f"{display_name} 開発ログ: {top_subject}", False


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
    if summary["functions_added"]:
        lines.append("### 追加された関数・メソッド")
        lines.append("")
        lines.append("、".join(f"`{n}`" for n in summary["functions_added"]) + "(diffのシグネチャ行から機械的に抽出)")
        lines.append("")
    if summary["classes_added"]:
        lines.append("### 追加されたクラス")
        lines.append("")
        lines.append("、".join(f"`{n}`" for n in summary["classes_added"]))
        lines.append("")
    if summary["tests_added"]:
        lines.append("### 追加されたテスト")
        lines.append("")
        lines.append("、".join(f"`{n}`" for n in summary["tests_added"]))
        lines.append("")
    if summary["docs_excerpts"]:
        lines.append("### README/ドキュメントの追記内容(抜粋)")
        lines.append("")
        for ex in summary["docs_excerpts"]:
            lines.append(f"> {ex}")
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
