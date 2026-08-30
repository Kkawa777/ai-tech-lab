"""Screenshot candidate discovery (Phase 2, docs/devlog-policy.md 17節).

Deliberately conservative: this module NEVER embeds an image into an
article body automatically. It only lists candidate file paths (relative,
never absolute) as `screenshot_candidates` in the generated draft's
frontmatter, for a human to review and manually insert during promotion.
There is no way for a text-based script to inspect pixel content for
private UI, credentials, or personal information visible in a screenshot
— only a human reviewing the actual image can judge that — so automatic
embedding is out of scope by design, not merely unimplemented.
"""
import re
from pathlib import Path

CANDIDATE_SUBDIRS = [
    "screenshots", "artifacts", "docs/images", "test-results", "playwright-report",
]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

DENYLIST_NAME_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"private", r"internal", r"personal", r"confidential", r"secret", r"credential",
        r"(^|[\\/])(users|home)[\\/][a-z0-9_.-]+",  # looks like a per-user OS path segment
    ]
]


def _is_denylisted(rel_path):
    return any(p.search(rel_path) for p in DENYLIST_NAME_PATTERNS)


def discover_candidates(repo_path, date_str):
    """Returns a list of repo-relative POSIX-style paths (never absolute)
    for images that plausibly relate to `date_str`, found under any of the
    known candidate subdirectories. An empty list is the normal, safe
    default when a project has no such directories or no matching files —
    callers must generate the article without images in that case, not
    treat it as an error."""
    repo_path = Path(repo_path)
    candidates = []
    for subdir in CANDIDATE_SUBDIRS:
        base = repo_path / subdir
        if not base.exists() or not base.is_dir():
            continue
        for f in base.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            rel = f.relative_to(repo_path).as_posix()
            if _is_denylisted(rel):
                continue
            matches_date = date_str in f.name
            try:
                mtime_date = f.stat().st_mtime
            except OSError:
                mtime_date = None
            if matches_date or _mtime_matches_date(mtime_date, date_str):
                candidates.append(rel)
    return sorted(set(candidates))


def _mtime_matches_date(mtime, date_str):
    if mtime is None:
        return False
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d") == date_str
    except (OverflowError, OSError, ValueError):
        return False
