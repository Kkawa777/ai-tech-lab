"""Git metadata collection. Unchanged in spirit from Phase 1: this module
still never reads full diff content itself (that boundary moved into
sanitize.py, which is the only module allowed to look inside a diff, and
only for allowlisted-path files, and only after a secret scan). This module
only ever returns hash/date/subject/file-list/line-count metadata.
"""
import re
import subprocess


def run_git(repo_path, args):
    result = subprocess.run(
        ["git", "-C", str(repo_path)] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} に失敗しました:\n{result.stderr}")
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
    # --root: without it, `git diff-tree` silently reports zero changed
    # files for a repository's root commit (no parent to diff against).
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


def is_merge_commit(repo_path, commit_hash):
    out = run_git(repo_path, ["show", "-s", "--format=%P", commit_hash])
    parents = out.strip().split()
    return len(parents) > 1


def get_file_diff(repo_path, commit_hash, file_path, max_lines=400):
    """Return the unified diff hunks for one file in one commit, capped at
    max_lines. Callers MUST have already checked the file path against
    security.is_denylisted_path() before calling this — this function does
    not itself enforce the denylist, to keep the "what can see a diff"
    decision in one place (sanitize.py)."""
    out = run_git(
        repo_path,
        ["show", "--no-color", "-U1", "--format=", commit_hash, "--", file_path],
    )
    lines = out.splitlines()
    return lines[:max_lines]


def get_full_file_at_commit(repo_path, commit_hash, file_path):
    """Full file content of one path as of one commit (`git show <hash>:<path>`).

    Used only to locate a Markdown file's YAML frontmatter block boundaries
    (see sanitize.py) — never to extract arbitrary body content wholesale.
    """
    return run_git(repo_path, ["show", f"{commit_hash}:{file_path}"])
