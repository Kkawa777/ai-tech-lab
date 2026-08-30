"""Quality Score model + publish-decision gates (Phase 2, docs/devlog-
policy.md 14節).

Five numeric axes (A-E, 0-20 each, summing to a 0-100 total), built only
from deterministic signals already computed by gitmeta/sanitize/classify —
never from an LLM's subjective impression of its own output. A separate
sixth axis, Safety (F), is not part of the numeric sum: it is a hard
PASS/FAIL gate applied to the *rendered* article text (defense in depth,
independent of whatever sanitize.py already excluded), and a FAIL there
forces the decision to BLOCKED regardless of score.

Decision thresholds (docs/devlog-policy.md 14節 for the rationale):
  score >= 80                        -> AUTO_PUBLISH_CANDIDATE
  60 <= score < 80                   -> DRAFT_ONLY
  score < 60                         -> SKIP
  any Security/Privacy/Fact gate FAIL -> BLOCKED  (overrides all of the above)
"""
import re

from .classify import GENERIC

AUTO_PUBLISH_CANDIDATE = "AUTO_PUBLISH_CANDIDATE"
DRAFT_ONLY = "DRAFT_ONLY"
SKIP = "SKIP"
BLOCKED = "BLOCKED"

AUTO_PUBLISH_THRESHOLD = 80
DRAFT_ONLY_THRESHOLD = 60

# Re-scanned against the FINAL rendered article text (title+description+
# body+frontmatter values), independent of sanitize.py's own filtering, so
# a bug in generation logic can't silently smuggle something through.
from .security import SECRET_VALUE_PATTERNS  # noqa: E402

PRIVACY_LEAK_PATTERNS = [
    re.compile(p) for p in [
        r"[A-Za-z]:\\\\?[A-Za-z0-9_\- \\\\]+",   # Windows absolute path (C:\... or C:\\...)
        r"/home/[A-Za-z0-9_.-]+",                  # Linux home dir
        r"/Users/[A-Za-z0-9_.-]+",                 # macOS home dir
    ]
]


def score_development_value(day_stats, summary):
    score = 0
    score += min(8, day_stats["notable_commit_count"] * 3)
    total_lines = day_stats["insertions"] + day_stats["deletions"]
    if total_lines >= 200:
        score += 8
    elif total_lines >= 50:
        score += 5
    elif total_lines >= 10:
        score += 2
    if summary["functions_added"] or summary["classes_added"]:
        score += 4
    return min(20, score)


def score_reader_value(summary):
    score = 0
    if summary["docs_excerpts"]:
        score += 8
    if summary["tests_added"]:
        score += 6
    if summary["functions_added"] or summary["classes_added"]:
        score += 6
    return min(20, score)


def score_evidence_strength(summary, day_stats):
    score = 4  # baseline: commit hash/subject/date are always CONFIRMED_GIT_FACT
    score += min(10, len(summary["evidence"]) * 2)
    if summary["behavior_pairs"]:
        score += 6
    total_files = max(1, day_stats.get("total_files_changed", 0))
    skip_ratio = len(summary["files_skipped_for_safety"]) / total_files
    if skip_ratio > 0.5:
        score -= 6
    return max(0, min(20, score))


def score_technical_depth(summary):
    signal_types_present = sum([
        bool(summary["functions_added"]),
        bool(summary["classes_added"]),
        bool(summary["tests_added"]),
        bool(summary["docs_excerpts"]),
        bool(summary["behavior_pairs"]),
    ])
    return min(20, signal_types_present * 5)


def score_seo_potential(day_type, ja_coverage_ratio):
    score = 0
    if day_type != GENERIC:
        score += 10
    score += round(10 * ja_coverage_ratio)
    return min(20, score)


def compute_quality_score(day_stats, summary, day_type, ja_coverage_ratio):
    breakdown = {
        "development_value": score_development_value(day_stats, summary),
        "reader_value": score_reader_value(summary),
        "evidence_strength": score_evidence_strength(summary, day_stats),
        "technical_depth": score_technical_depth(summary),
        "seo_potential": score_seo_potential(day_type, ja_coverage_ratio),
    }
    total = sum(breakdown.values())
    return total, breakdown


def check_safety_gates(rendered_text, summary=None):
    """Independent final-text re-scan. Returns dict {security, privacy,
    fact} each "PASS" or "FAIL", plus a `reasons` list (never containing
    the actual matched secret value — only that a gate failed and why).

    `summary` is the Sanitized Change Summary from generation time — only
    needed for the Fact gate's evidence/skipped-file contradiction check.
    Callers re-verifying an ALREADY-GENERATED file at promotion time (see
    scripts/promote-devlog.py, scripts/mark-devlog-reviewed.py) don't have
    that generation-time context available, and per docs/devlog-policy.md
    the normal workflow expects a human to hand-edit title/primary_keyword
    between generation and promotion — so Security/Privacy MUST be
    re-checked against the file's CURRENT content, not trusted from
    generation time. Pass summary=None in that case; the Fact gate is then
    reported PASS (there is nothing to contradiction-check without it) —
    this is a deliberate no-op, not a bypass, since Security/Privacy are
    the gates that a human edit could actually newly violate."""
    reasons = []
    summary = summary or {}

    security_pass = not any(p.search(rendered_text) for p in SECRET_VALUE_PATTERNS)
    if not security_pass:
        reasons.append("security: rendered text matched a secret-value pattern")

    privacy_pass = not any(p.search(rendered_text) for p in PRIVACY_LEAK_PATTERNS)
    if not privacy_pass:
        reasons.append("privacy: rendered text contains an absolute local file path")

    # Fact gate: defensive contradiction check — no evidence item should
    # reference a path that sanitize.py itself flagged as unsafe to use.
    skipped = set(summary.get("files_skipped_for_safety", []))
    fact_pass = True
    for ev in summary.get("evidence", []):
        # evidence strings look like "<hash>:<path> (...)"
        if ":" in ev:
            candidate_path = ev.split(":", 1)[1].split(" (")[0]
            if candidate_path in skipped:
                fact_pass = False
                reasons.append(f"fact: evidence references a file that was also flagged unsafe ({candidate_path})")

    return {
        "security": "PASS" if security_pass else "FAIL",
        "privacy": "PASS" if privacy_pass else "FAIL",
        "fact": "PASS" if fact_pass else "FAIL",
        "reasons": reasons,
    }


def decide(total_score, gates):
    if gates["security"] == "FAIL" or gates["privacy"] == "FAIL" or gates["fact"] == "FAIL":
        return BLOCKED
    if total_score >= AUTO_PUBLISH_THRESHOLD:
        return AUTO_PUBLISH_CANDIDATE
    if total_score >= DRAFT_ONLY_THRESHOLD:
        return DRAFT_ONLY
    return SKIP
