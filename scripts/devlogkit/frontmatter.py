"""Frontmatter rendering, dedup lookup, order numbering, and content
fingerprinting.

render_markdown() delegates all YAML escaping to PyYAML (not hand-rolled
string building — a Phase 1 bug class this avoids structurally). Extended
in Phase 2 with the Quality Gate fields needed by promote.py to verify a
draft's gate results without re-running the whole pipeline, and in Phase
2.5 with a content fingerprint (see compute_content_fingerprint) so
promotion can detect ANY change made after review — not just the
specific secret/path patterns the Security/Privacy re-scan checks for.
"""
import hashlib
import json
import re
from pathlib import Path

import yaml

# A frontmatter delimiter must be its own line ("---" and nothing else,
# ignoring trailing whitespace) — matching the literal 3-character
# substring anywhere in the text (the previous implementation) breaks the
# instant a title/description contains "---" (e.g. a commit subject like
# "docs: replace === with --- style" embedded verbatim via the ja.py
# fallback path), silently truncating frontmatter mid-value or corrupting
# the split (Phase 2.5 finding from an independent code review).
FRONTMATTER_DELIMITER_RE = re.compile(r"^---[ \t]*$", re.MULTILINE)

ROOT = Path(__file__).resolve().parent.parent.parent
ARTICLES_DIR = ROOT / "_articles"
DRAFTS_DIR = ROOT / "drafts"

# Fields that legitimately change between review and promotion, and so
# must be excluded from the fingerprint (some of them — the reviewer_*
# fields — ARE the fingerprint's own bookkeeping and can't hash
# themselves; `status`/`order` are set BY promotion, not before it).
# Everything else — title, description, body, source_commits,
# publish_decision, quality_score-adjacent fields, etc. — is locked: any
# change to those after review invalidates reviewed_content_hash.
REVIEW_BOOKKEEPING_KEYS = {
    "status", "order",
    "reviewer_status", "reviewer_note",
    "reviewed_content_hash", "reviewed_at", "reviewer_method",
}


def compute_content_fingerprint(frontmatter: dict, body: str) -> str:
    canonical_fm = {k: v for k, v in frontmatter.items() if k not in REVIEW_BOOKKEEPING_KEYS}
    payload = json.dumps(canonical_fm, ensure_ascii=False, sort_keys=True) + "\n---BODY---\n" + body
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def split_frontmatter(text):
    # Delimiters must be matched as whole LINES (FRONTMATTER_DELIMITER_RE),
    # not as a bare "---" substring search — the earlier implementation
    # (`text.split("---", 2)`) broke the instant any frontmatter VALUE
    # happened to contain the 3-character sequence "---" (e.g. a commit
    # subject like "docs: replace === with --- style" embedded verbatim by
    # ja.py's fallback path), silently mis-splitting mid-value instead of
    # at the real frontmatter boundary (Phase 2.5 finding, independent
    # code review).
    matches = list(FRONTMATTER_DELIMITER_RE.finditer(text))
    if len(matches) < 2 or matches[0].start() != 0:
        return None, text
    open_delim, close_delim = matches[0], matches[1]
    fm_text = text[open_delim.end():close_delim.start()]
    body = text[close_delim.end():]
    # render_markdown() always inserts exactly one blank line ("\n\n")
    # between the closing `---` and the body as a structural template
    # separator, not as part of the body's own content. Without stripping
    # it back off here, every read-modify-write round trip (e.g.
    # mark-devlog-reviewed.py reading a file and writing it back) would
    # accumulate one more blank line into "the body" each time — which
    # silently changes the file's actual byte content on every pass, and
    # broke compute_content_fingerprint()'s idempotency (Phase 2.5 found
    # this via a failing "unmodified draft still promotes" sanity test:
    # the hash computed just before a write didn't match a hash computed
    # from re-reading that same write's output, because the body itself
    # had gained extra leading newlines in between).
    return fm_text, body.lstrip("\n")


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


def build_order(date_str, seq=0):
    # Reserved namespace for devlog articles, separate from the
    # hand-authored article catalog (order: 1-99). See docs/devlog-policy.md.
    return int(f"9{date_str.replace('-', '')}{seq:02d}")


def render_markdown(frontmatter: dict, body: str) -> str:
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{fm_text}---\n\n{body}"


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        return None, None
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None, None
    return data, body
