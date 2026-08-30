"""Trivial-commit filtering (Phase 1, unchanged) + article-type
classification (Phase 2, new — drives which Japanese template in
templates.py is used)."""
import re
from pathlib import Path

TRIVIAL_MESSAGE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # All anchored at the start (docs/devlog-policy.md 5節: 「...で始まる」)
        # so a substantive commit that merely *mentions* "typo" or
        # "formatting" mid-sentence is never silently dropped.
        r"^chore\b", r"^typo\b", r"^fix\s+typo\b", r"^style\b",
        r"^formatting\b", r"^docs?:\s*(minor|fix typo)",
    ]
]
TRIVIAL_ONLY_FILENAMES = {
    "package-lock.json", "skills-lock.json", ".gitignore", "poetry.lock",
    "Gemfile.lock", "yarn.lock", "uv.lock", "README.md",
}
TRIVIAL_LOCK_SUFFIXES = (".lock",)


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


# --- Article-type classification (Phase 2) --------------------------------

FEATURE = "feature"
BUGFIX = "bugfix"
PERFORMANCE = "performance"
UI = "ui"
ARCHITECTURE = "architecture"
GENERIC = "generic"

_BUGFIX_RE = re.compile(r"^fix\b|\bbug\b|\bregression\b", re.IGNORECASE)
_PERF_RE = re.compile(r"^perf\b|\boptimi[sz]e|\bspeed\s*up\b|\bfaster\b|\bcache\b|\breduce\b.*\btime\b", re.IGNORECASE)
_UI_RE = re.compile(r"\bui\b|\bstyle\b|\bcss\b|\blayout\b|\bdesign\b|\bresponsive\b", re.IGNORECASE)
_ARCH_RE = re.compile(r"^refactor\b|\brestructure\b|\bmigrat|\barchitecture\b", re.IGNORECASE)
_FEATURE_RE = re.compile(r"^feat\b|\badd\b|\bimplement\b|\bintroduce\b|^publish\b", re.IGNORECASE)

_UI_EXTENSIONS = {".css", ".scss", ".sass", ".less"}


def classify_commit_type(commit, files):
    subject = commit["subject"]
    exts = {Path(f["path"]).suffix.lower() for f in files}

    if _BUGFIX_RE.search(subject):
        return BUGFIX
    if _PERF_RE.search(subject):
        return PERFORMANCE
    if _UI_RE.search(subject) or (exts & _UI_EXTENSIONS):
        return UI
    if _ARCH_RE.search(subject):
        return ARCHITECTURE
    if _FEATURE_RE.search(subject):
        return FEATURE
    return GENERIC


def classify_day_type(notable_commits_with_files):
    """A day can mix commit types; pick the single most common one so the
    whole article uses one coherent template rather than switching
    mid-article. Ties broken by a fixed priority order (bugfix and
    performance findings tend to be the most concretely reportable)."""
    priority = [BUGFIX, PERFORMANCE, ARCHITECTURE, UI, FEATURE, GENERIC]
    counts = {t: 0 for t in priority}
    for commit, files in notable_commits_with_files:
        counts[classify_commit_type(commit, files)] += 1
    best = max(priority, key=lambda t: (counts[t], -priority.index(t)))
    return best if counts[best] > 0 else GENERIC
