"""Sanitized Change Summary Layer (Phase 2, docs/devlog-policy.md 13節).

This is the ONLY module in devlogkit that ever reads diff *content*
(previously — Phase 1 — nothing did). The pipeline enforced here, for
every changed file in a commit, is:

    changed file path
      -> security.is_denylisted_path()?  --yes--> skip entirely, no read
      -> gitmeta.get_file_diff()  (bounded to max_lines)
      -> "Binary files ... differ" marker?  --yes--> skip
      -> security.scan_lines_for_secrets() on the raw diff text?
           --yes--> discard this file's extracted content entirely
                    (file name still appears in files_changed, which is
                    already public per Phase 1 — nothing new leaks)
      -> extract ONLY: added function/class/test names (regex, not the
         function *bodies*), and — for README/docs prose files only — a
         short excerpt of added plain-text lines (also secret-scanned)
      -> merge into the structured summary

Anything not explicitly extracted here (arbitrary code lines, values,
comments, strings) is never carried into the summary or the article.
"""
import re
from pathlib import Path

from . import gitmeta, security

FUNC_PATTERNS = [
    re.compile(r"^\+\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),                       # Python
    re.compile(r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)"),  # JS/TS
    re.compile(r"^\+\s*(?:export\s+)?const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\("),  # JS/TS arrow
    re.compile(r"^\+\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\("),      # Go
    re.compile(r"^\+\s*def\s+([a-zA-Z_][a-zA-Z0-9_?!]*)"),                          # Ruby (superset of Python but harmless dup)
]
CLASS_PATTERNS = [
    re.compile(r"^\+\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"),                          # Python/Ruby/Java-ish
    re.compile(r"^\+\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)"),          # JS/TS
]
TEST_PATTERNS = [
    re.compile(r"^\+\s*def\s+(test_[A-Za-z0-9_]*)"),                                 # pytest
    re.compile(r"^\+\s*(?:it|test)\(\s*['\"]([^'\"]+)['\"]"),                        # JS it()/test()
    re.compile(r"^\+\s*describe\(\s*['\"]([^'\"]+)['\"]"),                           # JS describe()
    re.compile(r"^\+\s*func\s+(Test[A-Za-z0-9_]*)"),                                 # Go
]

DOCS_PATH_RE = re.compile(r"\.md$", re.IGNORECASE)
# Lines that are structural Markdown (headings, code fences, list markers
# for non-prose, front matter delimiters) are excluded from the "prose
# excerpt" — only plain sentences are quoted.
MD_STRUCTURAL_RE = re.compile(r"^\+\s*(#{1,6}\s|```|---\s*$|\|.*\|$)")
# YAML frontmatter lines (`key: value`, `key:`, or a `- item` list entry
# inside a frontmatter block) read as noise when quoted as "prose" — this
# matters now that DOCS_PATH_RE covers _articles/*.md, whose diffs often
# touch the frontmatter block above the actual body prose.
FRONTMATTER_LINE_RE = re.compile(r"^\+\s*(?:[a-zA-Z_][a-zA-Z0-9_]*:\s|[a-zA-Z_][a-zA-Z0-9_]*:$|-\s+[a-zA-Z_]+:\s)")

# `yaml.safe_dump` (frontmatter.render_markdown) folds/wraps long string
# values (title/description/social_summary etc.) across multiple lines.
# A wrapped CONTINUATION line is plain indented text with no `key:` shape
# at all, so FRONTMATTER_LINE_RE alone cannot catch it — it would read as
# ordinary prose to _extract_docs_excerpt. Instead of pattern-matching
# individual lines, HUNK_HEADER_RE + _frontmatter_line_range track the
# diff's line numbers against the file's actual `--- ... ---` frontmatter
# block boundaries (read once via `git show <hash>:<path>`), so EVERY
# added line inside that block — key line or wrapped continuation alike —
# is excluded, regardless of what it looks like.
HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

MAX_DOCS_EXCERPT_CHARS = 200
MAX_ITEMS_PER_LIST = 8


def _frontmatter_line_range(full_text):
    """1-indexed (start, end) line range of the `--- ... ---` frontmatter
    block in `full_text`, inclusive of both delimiter lines. None if the
    file doesn't open with a frontmatter block."""
    lines = full_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (1, i + 1)
    return None


def _filter_out_frontmatter_lines(diff_lines, frontmatter_range):
    """Drop any added ('+') diff line whose position in the NEW file falls
    within frontmatter_range, tracking position via @@ hunk headers.
    Non-added lines (context, removed, hunk headers) pass through
    unchanged, so hunk structure is preserved for
    _extract_single_line_replacement's per-hunk counting."""
    if frontmatter_range is None:
        return diff_lines
    start, end = frontmatter_range
    out = []
    new_line_no = None
    for line in diff_lines:
        m = HUNK_HEADER_RE.match(line)
        if m:
            new_line_no = int(m.group(1))
            out.append(line)
            continue
        if new_line_no is None or line.startswith("+++"):
            out.append(line)
            continue
        if line.startswith("+"):
            if not (start <= new_line_no <= end):
                out.append(line)
            new_line_no += 1
        elif line.startswith("-"):
            out.append(line)  # removed lines don't consume a new-file line number
        else:
            out.append(line)
            new_line_no += 1
    return out


def _extract_names(lines, patterns):
    found = []
    for line in lines:
        for pat in patterns:
            m = pat.search(line)
            if m:
                name = m.group(1)
                if name not in found:
                    found.append(name)
                break
    return found[:MAX_ITEMS_PER_LIST]


def _extract_docs_excerpt(lines):
    prose = []
    for line in lines:
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if MD_STRUCTURAL_RE.match(line) or FRONTMATTER_LINE_RE.match(line):
            continue
        text = line[1:].strip()
        if len(text) < 8:  # skip near-empty/trivial additions
            continue
        prose.append(text)
    joined = " ".join(prose)
    if not joined:
        return None
    return joined[:MAX_DOCS_EXCERPT_CHARS]


def _extract_single_line_replacement(lines):
    """Very narrow heuristic: a hunk with exactly one removed and one added
    line is an unambiguous before/after pair (e.g. a changed constant or a
    renamed call). Anything more complex is left as UNKNOWN rather than
    guessed at."""
    hunk_removed, hunk_added = [], []
    pairs = []
    in_hunk = False
    for line in lines:
        if line.startswith("@@"):
            if len(hunk_removed) == 1 and len(hunk_added) == 1:
                pairs.append((hunk_removed[0], hunk_added[0]))
            hunk_removed, hunk_added = [], []
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("-") and not line.startswith("---"):
            hunk_removed.append(line[1:].strip())
        elif line.startswith("+") and not line.startswith("+++"):
            hunk_added.append(line[1:].strip())
    if len(hunk_removed) == 1 and len(hunk_added) == 1:
        pairs.append((hunk_removed[0], hunk_added[0]))
    return pairs[:1]  # only ever report the first — keep it unambiguous, not a list of guesses


def build_sanitized_summary(repo_path, commit, files):
    """files: list of {status, path} dicts (from gitmeta.get_changed_files).
    Returns the Sanitized Change Summary dict for this one commit."""
    functions_added, classes_added, tests_added = [], [], []
    docs_excerpts = []
    evidence = []
    behavior_before = None
    behavior_after = None
    files_skipped_for_safety = []

    for f in files:
        path = f["path"]
        if security.is_denylisted_path(path):
            files_skipped_for_safety.append(path)
            continue
        try:
            lines = gitmeta.get_file_diff(repo_path, commit["hash"], path)
        except RuntimeError:
            continue
        if not lines or any(l.startswith("Binary files") for l in lines):
            continue
        if security.scan_lines_for_secrets(lines):
            files_skipped_for_safety.append(path)
            continue

        funcs = _extract_names(lines, FUNC_PATTERNS)
        classes = _extract_names(lines, CLASS_PATTERNS)
        tests = _extract_names(lines, TEST_PATTERNS)
        if funcs:
            functions_added.extend(n for n in funcs if n not in functions_added)
            evidence.append(f"{commit['hash'][:7]}:{path} (function signature added)")
        if classes:
            classes_added.extend(n for n in classes if n not in classes_added)
            evidence.append(f"{commit['hash'][:7]}:{path} (class signature added)")
        if tests:
            tests_added.extend(n for n in tests if n not in tests_added)
            evidence.append(f"{commit['hash'][:7]}:{path} (test added)")

        # For Markdown files, resolve the frontmatter block's line range in
        # the NEW (post-commit) version of the file, and strip any added
        # line that falls inside it — including wrapped/folded YAML
        # continuation lines that don't look like `key: value` at all
        # (the bug FRONTMATTER_LINE_RE alone could not catch; see the
        # HUNK_HEADER_RE docstring above).
        is_markdown = DOCS_PATH_RE.search(path)
        body_lines = lines
        if is_markdown:
            try:
                full_text = gitmeta.get_full_file_at_commit(repo_path, commit["hash"], path)
                frontmatter_range = _frontmatter_line_range(full_text)
            except RuntimeError:
                frontmatter_range = None
            body_lines = _filter_out_frontmatter_lines(lines, frontmatter_range)

        if is_markdown:
            excerpt = _extract_docs_excerpt(body_lines)
            if excerpt and not security.contains_secret_pattern(excerpt):
                docs_excerpts.append(excerpt)
                evidence.append(f"{commit['hash'][:7]}:{path} (docs/README prose excerpt)")

        if behavior_before is None:
            pairs = _extract_single_line_replacement(body_lines if is_markdown else lines)
            if pairs:
                before, after = pairs[0]
                looks_like_frontmatter = bool(
                    re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*:\s", before) or re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*:\s", after)
                )
                if not looks_like_frontmatter and not security.contains_secret_pattern(before) and not security.contains_secret_pattern(after):
                    # Cap length so a huge single "line" can't smuggle in
                    # unrelated content; still just a verbatim code line,
                    # not a narrative description.
                    behavior_before = before[:120]
                    behavior_after = after[:120]
                    evidence.append(f"{commit['hash'][:7]}:{path} (single-line before/after)")

    return {
        "functions_added": functions_added[:MAX_ITEMS_PER_LIST],
        "classes_added": classes_added[:MAX_ITEMS_PER_LIST],
        "tests_added": tests_added[:MAX_ITEMS_PER_LIST],
        "docs_excerpts": docs_excerpts[:3],
        "behavior_before": behavior_before,
        "behavior_after": behavior_after,
        "evidence": evidence,
        "files_skipped_for_safety": files_skipped_for_safety,
    }


def merge_day_summaries(commit_summaries):
    """Combine per-commit sanitized summaries for the day into one dict,
    for use by score.py/templates.py which mostly reason about the whole
    day's notable commits at once."""
    merged = {
        "functions_added": [], "classes_added": [], "tests_added": [],
        "docs_excerpts": [], "evidence": [], "files_skipped_for_safety": [],
        "behavior_pairs": [],
    }
    for s in commit_summaries:
        for key in ("functions_added", "classes_added", "tests_added", "docs_excerpts", "evidence", "files_skipped_for_safety"):
            for item in s[key]:
                if item not in merged[key]:
                    merged[key].append(item)
        if s["behavior_before"] is not None:
            merged["behavior_pairs"].append((s["behavior_before"], s["behavior_after"]))
    return merged
