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
MD_STRUCTURAL_RE = re.compile(r"^\+\s*(#{1,6}\s|```|---\s*$|\|.*\|$|\{:.*\}\s*$)")
# Recognizes an added Markdown H2/H3 heading's TEXT (separate from
# MD_STRUCTURAL_RE, which excludes headings from prose excerpts — this
# captures them instead, as a distinct "section added" signal; see
# HEADING_RE usage in _extract_headings below).
HEADING_RE = re.compile(r"^\+\s*#{2,3}\s+(.+?)\s*$")
# A line that IS a fence delimiter (used to track "are we inside a code
# fence" across a hunk, regardless of whether the delimiter line itself
# was added/removed/context — a fence opened by an unchanged context line
# still means added lines under it are code, not prose).
FENCE_DELIMITER_RE = re.compile(r"^[+\- ]\s*```")
# An added line that IS a heading at ANY level (# through ######), used to
# detect a heading-LEVEL-only rename (see _extract_headings): if a hunk
# removes "# X" and adds "## X", that's a formatting change to an existing
# heading, not a new section — it must not also be reported as "added".
HEADING_ANY_LEVEL_RE = re.compile(r"^[+\-]\s*#{1,6}\s+(.+?)\s*$")
# Internal editorial/SEO-planning labels (e.g. CONTENT_PLAN.md's per-item
# "検索意図: ..." annotations, or a bare `search_intent`/`primary_keyword`
# label) read as reader-facing documentation prose to a naive scanner, but
# they are planning metadata about a DIFFERENT, not-yet-published article —
# never something a reader of THIS Dev Log should see quoted as if it were
# project documentation (Phase 2.5 finding: an independent review caught a
# real instance of this leaking into a generated article's docs excerpt).
INTERNAL_LABEL_LINE_RE = re.compile(r"^\+\s*(検索意図|search_intent|primary_keyword)\s*[:：]")
_HTML_TAG_RE = re.compile(r"<[^>]*>")
_LIQUID_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")


def _is_mostly_markup(text, threshold=0.4):
    """True if most of `text`'s characters are inside HTML tags or Liquid
    `{{ }}`/`{% %}` expressions — i.e. it's template/markup, not prose.
    A single-tag-only regex (the earlier approach) missed lines combining
    several tags with a little Liquid interpolation, e.g.
    `<h1 class="hero-title">{{ site.title | escape }}</h1>`, which is
    almost entirely markup but doesn't match a single "whole line is one
    tag" pattern."""
    if not text:
        return False
    stripped = _LIQUID_RE.sub("", _HTML_TAG_RE.sub("", text))
    return (len(text) - len(stripped)) / len(text) >= threshold
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


def _group_by_hunk(lines):
    """Split a file's diff lines into one list per `@@ ... @@` hunk (the
    hunk header lines themselves are dropped — callers that need them,
    like _filter_out_frontmatter_lines, track them separately). Shared by
    every extractor that must not let content from two different, possibly
    unrelated hunks blend together (docs excerpts, heading rename
    detection)."""
    current_hunk = []
    hunks = []
    for line in lines:
        if HUNK_HEADER_RE.match(line):
            if current_hunk:
                hunks.append(current_hunk)
            current_hunk = []
            continue
        current_hunk.append(line)
    if current_hunk:
        hunks.append(current_hunk)
    return hunks


def _extract_docs_excerpt(lines):
    """Returns a SINGLE coherent excerpt: the first contiguous run of
    qualifying prose lines within one hunk.

    Phase 2.5 finding: the earlier version scanned the WHOLE file's diff
    and joined every qualifying line together regardless of which hunk (or
    how far apart in the file) it came from, producing a run-on paragraph
    stitched from unrelated sentences in different sections. Stopping at
    the first non-qualifying line (a heading, a blank line, a structural
    line, or the end of the hunk) keeps the excerpt to one real paragraph
    a human actually wrote together.
    """
    for hunk in _group_by_hunk(lines):
        prose = []
        in_fence = False
        for line in hunk:
            if FENCE_DELIMITER_RE.match(line):
                in_fence = not in_fence
                if prose:
                    break
                continue
            if in_fence:
                continue  # code-fence content is never prose, added or not
            if not line.startswith("+") or line.startswith("+++"):
                if prose:
                    break  # a removed/context line ends this paragraph run
                continue
            if MD_STRUCTURAL_RE.match(line) or FRONTMATTER_LINE_RE.match(line) or INTERNAL_LABEL_LINE_RE.match(line):
                if prose:
                    break
                continue
            text = line[1:].strip()
            if not text:
                if prose:
                    break  # blank line = paragraph boundary
                continue
            if _is_mostly_markup(text):
                if prose:
                    break  # e.g. an HTML/Liquid template line mid-paragraph
                continue
            if len(text) < 8 and not prose:
                continue  # skip near-empty/trivial additions before any prose started
            prose.append(text)
        if prose:
            joined = " ".join(prose)
            return joined[:MAX_DOCS_EXCERPT_CHARS]
    return None


def _extract_headings(lines):
    """Added H2/H3 headings, excluding a heading whose text was ALREADY
    present at some other level in the same hunk (a removed "# X" plus an
    added "## X" is a level-only rename, not a new section — Phase 2.5
    finding: an independent review caught this being reported as both an
    "added heading" AND, separately, a "before/after" change, which
    contradicts itself in the rendered article)."""
    headings = []
    for hunk in _group_by_hunk(lines):
        removed_texts = set()
        for line in hunk:
            if line.startswith("-"):
                m = HEADING_ANY_LEVEL_RE.match(line)
                if m:
                    removed_texts.add(m.group(1).strip())
        for line in hunk:
            m = HEADING_RE.match(line)
            if m:
                text = m.group(1).strip()
                if text and text not in removed_texts and text not in headings:
                    headings.append(text)
    return headings[:MAX_ITEMS_PER_LIST]


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


def _highlight_diff_pair(before, after, max_len=120, context=20):
    """Returns (before_display, after_display) windowed around the actual
    point of difference, or None if there's no visible difference at all.

    Phase 2.5 finding: naively truncating both lines to the first 120
    characters (the old behavior) made two genuinely different long lines
    (e.g. two versions of one long HTML `<img>` tag, differing only near
    the end) render as identical text in the article — misleading, since
    a reader sees "変更前" and "変更後" showing the exact same string with
    no visible change at all.
    """
    common_prefix_len = 0
    for a, b in zip(before, after):
        if a != b:
            break
        common_prefix_len += 1
    if common_prefix_len >= len(before) and common_prefix_len >= len(after):
        return None  # truly identical lines — nothing to show
    start = max(0, common_prefix_len - context)
    marker = "…" if start > 0 else ""
    return marker + before[start:start + max_len], marker + after[start:start + max_len]


def _extract_config_keys(diff_lines, frontmatter_range):
    """KEY NAMES ONLY (never values) added within a Markdown file's own
    frontmatter block — a safe structural signal ("this commit configured
    content_type/affiliate_products/...") distinct from the general
    frontmatter-continuation-line EXCLUSION used for prose (this is the
    intentional inverse: here we WANT the key name, just never the value
    next to it, since values can be arbitrary/longer free text)."""
    if frontmatter_range is None:
        return []
    start, end = frontmatter_range
    keys = []
    new_line_no = None
    for line in diff_lines:
        m = HUNK_HEADER_RE.match(line)
        if m:
            new_line_no = int(m.group(1))
            continue
        if new_line_no is None or line.startswith("+++"):
            continue
        if line.startswith("+"):
            if start <= new_line_no <= end:
                km = re.match(r"^\+\s*([a-zA-Z_][a-zA-Z0-9_]*):", line)
                if km and km.group(1) not in keys:
                    keys.append(km.group(1))
            new_line_no += 1
        elif not line.startswith("-"):
            new_line_no += 1
    return keys[:MAX_ITEMS_PER_LIST]


def build_sanitized_summary(repo_path, commit, files):
    """files: list of {status, path} dicts (from gitmeta.get_changed_files).
    Returns the Sanitized Change Summary dict for this one commit."""
    functions_added, classes_added, tests_added = [], [], []
    docs_excerpts = []
    headings_added = []
    config_keys_changed = []
    per_file_signals = []  # [{"path", "functions", "classes", "tests", "headings", "config_keys"}]
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
        frontmatter_range = None
        file_headings, file_keys = [], []
        if is_markdown:
            try:
                full_text = gitmeta.get_full_file_at_commit(repo_path, commit["hash"], path)
                frontmatter_range = _frontmatter_line_range(full_text)
            except RuntimeError:
                frontmatter_range = None
            body_lines = _filter_out_frontmatter_lines(lines, frontmatter_range)

            excerpt = _extract_docs_excerpt(body_lines)
            if excerpt and not security.contains_secret_pattern(excerpt):
                docs_excerpts.append({"path": path, "text": excerpt})
                evidence.append(f"{commit['hash'][:7]}:{path} (docs/README prose excerpt)")

            file_headings = [
                h for h in _extract_headings(body_lines) if not security.contains_secret_pattern(h)
            ]
            if file_headings:
                headings_added.extend(h for h in file_headings if h not in headings_added)
                evidence.append(f"{commit['hash'][:7]}:{path} (heading added)")

            file_keys = _extract_config_keys(lines, frontmatter_range)
            if file_keys:
                config_keys_changed.extend(k for k in file_keys if k not in config_keys_changed)
                evidence.append(f"{commit['hash'][:7]}:{path} (frontmatter key added)")

        if funcs or classes or tests or file_headings or file_keys:
            # Per-file attribution (Phase 2.5): Phase 2 only kept flat,
            # unattributed day-wide lists, which read as a meaningless dump
            # when a day touched several unrelated files/modules (an
            # independent review flagged this specifically for headings
            # and config keys). Grouping every extracted signal by path
            # lets the article say e.g. "scripts/devlogkit/security.py:
            # 関数 die、skip" instead of one undifferentiated cross-file list.
            per_file_signals.append({
                "path": path, "functions": funcs, "classes": classes, "tests": tests,
                "headings": file_headings, "config_keys": file_keys,
            })

        if behavior_before is None:
            pairs = _extract_single_line_replacement(body_lines if is_markdown else lines)
            if pairs:
                before, after = pairs[0]
                looks_like_frontmatter = bool(
                    re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*:\s", before) or re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*:\s", after)
                )
                if not looks_like_frontmatter and not security.contains_secret_pattern(before) and not security.contains_secret_pattern(after):
                    highlighted = _highlight_diff_pair(before, after)
                    if highlighted:
                        behavior_before, behavior_after = highlighted
                        evidence.append(f"{commit['hash'][:7]}:{path} (single-line before/after)")

    return {
        "functions_added": functions_added[:MAX_ITEMS_PER_LIST],
        "classes_added": classes_added[:MAX_ITEMS_PER_LIST],
        "tests_added": tests_added[:MAX_ITEMS_PER_LIST],
        "docs_excerpts": docs_excerpts[:3],
        "headings_added": headings_added[:MAX_ITEMS_PER_LIST],
        "config_keys_changed": config_keys_changed[:MAX_ITEMS_PER_LIST],
        "per_file_signals": per_file_signals,
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
        "docs_excerpts": [], "headings_added": [], "config_keys_changed": [],
        "evidence": [], "files_skipped_for_safety": [],
        "behavior_pairs": [], "per_file_signals": [],
    }
    for s in commit_summaries:
        for key in (
            "functions_added", "classes_added", "tests_added", "docs_excerpts",
            "headings_added", "config_keys_changed", "evidence", "files_skipped_for_safety",
        ):
            for item in s[key]:
                if item not in merged[key]:
                    merged[key].append(item)
        merged["per_file_signals"].extend(s["per_file_signals"])
        if s["behavior_before"] is not None:
            merged["behavior_pairs"].append((s["behavior_before"], s["behavior_after"]))
    return merged
