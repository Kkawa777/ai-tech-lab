#!/usr/bin/env python3
"""Generate a Dev Log article draft from a project's Git history for one date.

See docs/devlog-policy.md for the full policy this script implements
(allowlist rules, Fact rules, secret filtering, dedup/idempotency, order
numbering, status lifecycle). This docstring only summarizes behavior.

Design summary:
  - Only reads Git metadata (commit hash / date / subject / changed file
    names / insertion-deletion counts via `--shortstat`). It NEVER reads or
    includes full diff content, so secrets embedded in code changes cannot
    leak into the article by construction. As a second layer of defense, it
    also pattern-scans commit subjects and file names and drops any commit
    that matches (see SECRET_* patterns below).
  - Only processes a project if it is listed in config/devlog-projects.yaml
    with enabled: true and public: true, AND the --repo path's realpath
    matches that entry's configured path (prevents allowlist bypass by
    project-name spoofing).
  - Never writes into _articles/ (which must contain only status: ready
    files, per scripts/validate-site.py and .claude/hooks/check-article-
    status.js). --write outputs to drafts/ with status: draft; promotion to
    _articles/ (status: ready, final `order`) is a separate, reviewed step.
  - Idempotent: if every notable commit for the requested date is already
    present in some existing article's `source_commits`, it skips instead
    of generating a duplicate.
  - No development, or only trivial development (docs/lockfile/formatting-
    only commits), on the requested date is not an error: the script exits
    0 and prints that it skipped.
  - Never invents motivation, experience, or explanations not derivable
    from the Git metadata above (see docs/devlog-policy.md Fact rules).

Usage:
  python scripts/generate-devlog.py --project ai-tech-lab \\
      --repo "C:\\Projects" --date 2026-08-24 --dry-run
  python scripts/generate-devlog.py --project ai-tech-lab \\
      --repo "C:\\Projects" --date 2026-08-24 --write
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "devlog-projects.yaml"
ARTICLES_DIR = ROOT / "_articles"
DRAFTS_DIR = ROOT / "drafts"

# Metadata-level secret screen. Deliberately conservative (over-excludes
# rather than risks leaking): matches are dropped from the article, and the
# matched *value* is never printed anywhere, including dry-run output.
SECRET_MESSAGE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"secret", r"password", r"passwd", r"token", r"api[\s_-]?key",
        r"access[\s_-]?key", r"credential", r"oauth", r"private[\s_-]?key",
        r"aws_access_key_id", r"aws_secret_access_key", r"bearer", r"ssh[\s_-]?key",
    ]
]
SECRET_FILENAME_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(^|[\\/])\.env(\.|$|[\\/])", r"\.pem$", r"\.key$",
        r"credential", r"secret",
    ]
]

TRIVIAL_MESSAGE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # All anchored at the start (docs/devlog-policy.md 5節: 「...で始まる」)
        # so a substantive commit that merely *mentions* "typo" or
        # "formatting" mid-sentence (e.g. "fix: correct a typo and add rate
        # limiting") is never silently dropped from article consideration.
        r"^chore\b", r"^typo\b", r"^fix\s+typo\b", r"^style\b",
        r"^formatting\b", r"^docs?:\s*(minor|fix typo)",
    ]
]
TRIVIAL_ONLY_FILENAMES = {
    "package-lock.json", "skills-lock.json", ".gitignore", "poetry.lock",
    "Gemfile.lock", "yarn.lock", "uv.lock", "README.md",
}
TRIVIAL_LOCK_SUFFIXES = (".lock",)

CONVENTIONAL_PREFIX_RE = re.compile(
    r"^(feat|fix|perf|refactor|docs|chore|style|test|build|ci)(\([^)]*\))?:\s*",
    re.IGNORECASE,
)


def die(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def skip(msg):
    print(f"[SKIP] {msg}")
    sys.exit(0)


def split_frontmatter(text):
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    return parts[1], parts[2]


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

def load_allowlist():
    if not CONFIG_PATH.exists():
        die(f"allowlist設定が見つかりません: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("projects", {})


def resolve_and_validate_project(project_key, repo_arg, projects):
    if project_key not in projects:
        die(
            f"project '{project_key}' は config/devlog-projects.yaml のallowlistに"
            "存在しません。deny-by-defaultのため処理しません。"
        )
    entry = projects[project_key]
    if not entry.get("enabled") or not entry.get("public"):
        die(
            f"project '{project_key}' は enabled/public のいずれかが false のため"
            "対象外です(公開可否が確認できないrepositoryを勝手に処理しない設計)。"
        )
    configured_path = (ROOT / entry["path"]).resolve()
    actual_path = Path(repo_arg).resolve()
    if configured_path != actual_path:
        die(
            "--repo の実パスが allowlist設定の path と一致しません。"
            "project名の詐称によるallowlistバイパスを防ぐため中断します。"
        )
    if not (actual_path / ".git").exists():
        die(f"{actual_path} はGitリポジトリではありません(.gitが見つかりません)。")
    return entry, actual_path


# ---------------------------------------------------------------------------
# Git collection (metadata only; diff content is never read)
# ---------------------------------------------------------------------------

def run_git(repo_path, args):
    result = subprocess.run(
        ["git", "-C", str(repo_path)] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        die(f"git {' '.join(args)} に失敗しました:\n{result.stderr}")
    return result.stdout


def list_commits_on_date(repo_path, date_str):
    out = run_git(repo_path, ["log", "--date=short", "--pretty=format:%H%x1f%ad%x1f%s"])
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        h, ad, subject = parts
        if ad == date_str:
            commits.append({"hash": h, "date": ad, "subject": subject})
    commits.reverse()  # chronological order for narrative purposes
    return commits


def get_changed_files(repo_path, commit_hash):
    # --root: without it, `git diff-tree` silently reports zero changed files
    # for a repository's root commit (no parent to diff against), which would
    # cause the very first commit in a repo to be misclassified.
    out = run_git(repo_path, ["diff-tree", "--no-commit-id", "--name-status", "-r", "--root", commit_hash])
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append({"status": parts[0], "path": parts[-1]})
    return files


def is_merge_commit(repo_path, commit_hash):
    # `git diff-tree --no-commit-id --name-status -r --root` returns an empty
    # file list for merge commits unless -m/-c is passed, which would make
    # is_trivial()'s `if files and all(...)` guard treat them as "not
    # trivial" and render an article section with no changed files. This
    # repo currently has linear history (no merge commits), but the check
    # is added defensively for when that changes.
    out = run_git(repo_path, ["show", "-s", "--format=%P", commit_hash])
    parents = out.strip().split()
    return len(parents) > 1


def get_shortstat(repo_path, commit_hash):
    out = run_git(repo_path, ["show", "--shortstat", "--format=", commit_hash])
    line = out.strip().splitlines()[-1] if out.strip() else ""
    files_changed = ins = dele = 0
    m = re.search(r"(\d+) files? changed", line)
    if m:
        files_changed = int(m.group(1))
    m = re.search(r"(\d+) insertions?\(\+\)", line)
    if m:
        ins = int(m.group(1))
    m = re.search(r"(\d+) deletions?\(-\)", line)
    if m:
        dele = int(m.group(1))
    return {"files_changed": files_changed, "insertions": ins, "deletions": dele}


# ---------------------------------------------------------------------------
# Safety filter + triviality classification
# ---------------------------------------------------------------------------

def contains_secret_pattern(text):
    return any(p.search(text) for p in SECRET_MESSAGE_PATTERNS)


def filename_is_secret_like(path):
    return any(p.search(path) for p in SECRET_FILENAME_PATTERNS)


def is_trivial(commit, files):
    if any(p.search(commit["subject"]) for p in TRIVIAL_MESSAGE_PATTERNS):
        return True
    if files and all(
        Path(f["path"]).name in TRIVIAL_ONLY_FILENAMES
        or f["path"].endswith(TRIVIAL_LOCK_SUFFIXES)
        for f in files
    ):
        return True
    return False


def collect_notable_commits(repo_path, date_str):
    all_commits = list_commits_on_date(repo_path, date_str)
    notable = []
    stats = {"total": len(all_commits), "trivial": 0, "secret_excluded": 0, "merge_excluded": 0}
    for c in all_commits:
        if is_merge_commit(repo_path, c["hash"]):
            stats["merge_excluded"] += 1
            continue
        files = get_changed_files(repo_path, c["hash"])
        file_paths = [f["path"] for f in files]
        if contains_secret_pattern(c["subject"]) or any(filename_is_secret_like(p) for p in file_paths):
            stats["secret_excluded"] += 1
            continue
        if is_trivial(c, files):
            stats["trivial"] += 1
            continue
        notable.append({**c, "files": files, "stat": get_shortstat(repo_path, c["hash"])})
    return notable, stats


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def find_existing_source_commits(project_key):
    seen = set()
    for d in (ARTICLES_DIR, DRAFTS_DIR):
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm, _ = split_frontmatter(text)
            if not fm:
                continue
            try:
                data = yaml.safe_load(fm) or {}
            except yaml.YAMLError:
                continue
            if isinstance(data, dict) and data.get("generated_from_git") and data.get("source_project") == project_key:
                for h in data.get("source_commits") or []:
                    seen.add(h)
    return seen


# ---------------------------------------------------------------------------
# Article generation (CONFIRMED_GIT_FACT only; see docs/devlog-policy.md)
# ---------------------------------------------------------------------------

def clean_subject(subject):
    return CONVENTIONAL_PREFIX_RE.sub("", subject).strip()


def extension_summary(notable):
    exts = {}
    for c in notable:
        for f in c["files"]:
            ext = Path(f["path"]).suffix or "(no ext)"
            exts[ext] = exts.get(ext, 0) + 1
    return sorted(exts.items(), key=lambda kv: -kv[1])


def build_title(display_name, date_str, notable):
    top = clean_subject(notable[0]["subject"])
    if len(notable) == 1:
        return f"{display_name} 開発ログ({date_str}): {top}"
    return f"{display_name} 開発ログ({date_str}): {top} ほか{len(notable) - 1}件"


def build_description(display_name, date_str, notable):
    subjects = "、".join(clean_subject(c["subject"]) for c in notable[:5])
    more = f" ほか{len(notable) - 5}件" if len(notable) > 5 else ""
    return (
        f"{date_str}に{display_name}リポジトリで行われた開発のログです。"
        f"Git履歴から確認できる変更: {subjects}{more}。"
    )


def build_primary_keyword(display_name, notable):
    return f"{display_name} 開発ログ"


def build_social_summary(display_name, date_str, notable):
    top = clean_subject(notable[0]["subject"])
    suffix = f"ほか{len(notable) - 1}件" if len(notable) > 1 else ""
    text = f"{display_name}({date_str}): {top} {suffix}".strip()
    return text[:140]


def build_body(display_name, date_str, notable):
    lines = []
    lines.append(
        "この記事は、Gitのcommit履歴をもとに自動生成された開発ログです。"
        "個人の体験談ではなく、commit・変更ファイル・行数などGitから直接確認できる"
        "事実のみに基づいています(詳細は"
        "[docs/devlog-policy.md](https://github.com/Kkawa777/ai-tech-lab/blob/main/docs/devlog-policy.md)"
        "を参照)。\n"
    )

    lines.append("## この日の変更")
    lines.append("")
    for c in notable:
        stat = c["stat"]
        lines.append(
            f"- `{c['hash'][:7]}` {clean_subject(c['subject'])}"
            f"(変更ファイル{stat['files_changed']}件、+{stat['insertions']}/-{stat['deletions']})"
        )
    lines.append("")

    lines.append("## 変更されたファイル")
    lines.append("")
    for c in notable:
        file_list = "、".join(f"`{f['path']}`" for f in c["files"][:10])
        more = f" ほか{len(c['files']) - 10}件" if len(c["files"]) > 10 else ""
        lines.append(f"- `{c['hash'][:7]}`: {file_list}{more}")
    lines.append("")

    ext_summary = extension_summary(notable)
    if ext_summary:
        lines.append("## 技術的なポイント")
        lines.append("")
        top_exts = "、".join(f"`{ext}`({n}件)" for ext, n in ext_summary[:5])
        lines.append(
            f"この日変更されたファイルの拡張子別内訳は {top_exts} でした"
            "(Gitのdiff-tree統計から機械的に集計したものです)。"
        )
        lines.append("")

    lines.append("## 関連project")
    lines.append("")
    lines.append(f"- {display_name}")
    lines.append("")

    return "\n".join(lines)


def build_order(date_str, seq=0):
    # Reserved namespace for devlog articles, separate from the hand-authored
    # article catalog (order: 1-99). See docs/devlog-policy.md.
    return int(f"9{date_str.replace('-', '')}{seq:02d}")


def build_article(project_key, entry, repo_path, date_str, notable):
    display_name = entry.get("display_name", project_key)
    slug = f"devlog-{project_key}-{date_str}"
    title = build_title(display_name, date_str, notable)
    description = build_description(display_name, date_str, notable)
    primary_keyword = build_primary_keyword(display_name, notable)
    social_summary = build_social_summary(display_name, date_str, notable)
    source_commits = [c["hash"] for c in notable]

    frontmatter = {
        "title": title,
        "status": "draft",
        "permalink": f"/articles/{slug}/",
        "order": None,  # 昇格時にbuild_order()相当の値を明示的に設定する(draftでは未確定のまま)
        "category": "開発ログ",
        "difficulty": None,
        "estimated_time": "読了目安 約3分",
        "description": description,
        "content_type": "devlog",
        "primary_keyword": primary_keyword,
        "search_intent": f"{display_name}の開発状況・変更履歴を知りたい",
        "monetization": "none",
        "conversion_goal": None,
        "source_project": project_key,
        "source_commits": source_commits,
        "development_date": date_str,
        "generated_from_git": True,
        "social_summary": social_summary,
    }
    body = build_body(display_name, date_str, notable)
    return slug, frontmatter, body


def render_markdown(frontmatter, body):
    # Delegate all YAML escaping/quoting to PyYAML itself rather than
    # hand-rolled string building: a manual `if ":" in text: quote it` check
    # (the previous approach) misses cases like an unquoted "#" starting a
    # trailing comment, or a `"`-quoted string that itself contains an
    # un-escaped backslash (e.g. a commit subject with regex-like text),
    # either of which would silently corrupt the frontmatter or make it
    # fail to parse.
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{fm_text}---\n\n{body}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", required=True, help="config/devlog-projects.yaml のproject key")
    p.add_argument("--repo", required=True, help="対象repositoryのパス(allowlistのpathと一致する必要あり)")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="生成結果を標準出力へ表示するのみ(デフォルト)")
    mode.add_argument("--write", action="store_true", help="drafts/ へ実際にファイルを書き出す")
    return p.parse_args()


def main():
    args = parse_args()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        die("--date は YYYY-MM-DD 形式で指定してください。")

    projects = load_allowlist()
    entry, repo_path = resolve_and_validate_project(args.project, args.repo, projects)

    notable, stats = collect_notable_commits(repo_path, args.date)
    print(
        f"[INFO] {args.date}: 全commit {stats['total']}件 "
        f"(trivial除外 {stats['trivial']}件, secret該当除外 {stats['secret_excluded']}件, "
        f"merge除外 {stats['merge_excluded']}件, 記事化候補 {len(notable)}件)"
    )

    if not notable:
        skip(f"{args.date} は記事化に値するcommitがありません(開発なし、または軽微な変更のみ)。")

    existing = find_existing_source_commits(args.project)
    new_hashes = [c["hash"] for c in notable]
    if existing and set(new_hashes).issubset(existing):
        skip(f"{args.date} のcommitはすべて既存のDev Log記事に含まれています(重複防止のためSKIP)。")
    before = len(notable)
    notable = [c for c in notable if c["hash"] not in existing]
    if len(notable) < before:
        print(f"[INFO] 既存記事と重複する{before - len(notable)}件のcommitを除外しました。")
    if not notable:
        skip(f"{args.date} は重複除外後、記事化対象のcommitが残りませんでした。")

    slug, frontmatter, body = build_article(args.project, entry, repo_path, args.date, notable)
    markdown = render_markdown(frontmatter, body)

    if args.write:
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DRAFTS_DIR / f"{slug}.md"
        out_path.write_text(markdown, encoding="utf-8")
        print(f"[WRITE] {out_path} へ status: draft で書き出しました。")
        print(
            f"[NEXT] _articles/ への昇格時は、status: ready と order: {build_order(args.date)} "
            "(このproject・日付での1本目。同日に複数本ある場合は連番を2桁で増やす)を明示的に設定して"
            "ください。quality-development / independent-reviewer を経てから手動で行うこと"
            "(docs/devlog-policy.md 3節)。order を空欄のまま ready にすると、Jekyllの"
            "sort:\"order\"がnilを先頭扱いするため、ホームの「はじめての方はこちら」に"
            "誤って表示される可能性があります(scripts/validate-site.pyのcheck_order_valuesが検出します)。"
        )
    else:
        print("\n" + "=" * 70)
        print("[DRY-RUN] 以下は生成プレビューです。ファイルは書き出していません。")
        print("=" * 70 + "\n")
        print(markdown)


if __name__ == "__main__":
    main()
