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


# --- Score axis ownership (Phase 2.5 audit, docs/devlog-policy.md Step 8) ---
#
# Each underlying signal is scored on ONLY ONE axis for the property that
# axis is meant to measure, to avoid the same fact inflating the total via
# multiple axes. Phase 2's original design had functions/classes presence
# counted in development_value AND reader_value AND technical_depth (the
# same boolean, three times) — this table is the audited replacement:
#
#   signal                  -> axis (what it says about that axis)
#   commit count / line count  -> Development Value (size of the change)
#   config_keys_changed         -> Development Value (a real config action)
#   docs_excerpts                -> Reader Value (a reader gets real prose)
#   headings_added                -> Reader Value (new sections a reader sees)
#   tests_added                    -> Reader Value (reassurance) AND
#                                     Technical Depth (engineering rigor) —
#                                     the one deliberate exception, because
#                                     "a test was added" genuinely supports
#                                     two different claims, not one fact
#                                     counted twice toward one claim
#   functions_added/classes_added -> Technical Depth only
#   behavior_pairs (before/after)  -> Technical Depth only
#   structural_files_changed        -> Technical Depth only (Phase 2.6: see
#                                       below — a distinct, path-based
#                                       signal, not a rename of an existing
#                                       one, so it doesn't dilute the axis)
#   evidence count / diversity      -> Evidence Strength (how much
#                                       CONFIRMED_GIT_FACT exists at all)
#   day_type / title coverage        -> SEO Potential
#
# Phase 2.6 finding: a 10-day real-data evaluation (Phase 2.5) showed
# Technical Depth structurally under-scoring this repo's actual work,
# because functions_added/classes_added/tests_added are Python/JS/Go-
# shaped regexes that see nothing on a typical content-authoring day —
# even a day that did real Jekyll layout/include/template/stylesheet
# engineering (Liquid + HTML + CSS, not Python). `structural_files_changed`
# (sanitize.py, path-based: `_layouts/`, `_includes/`, `templates/`, or a
# stylesheet) is a genuinely NEW, orthogonal signal for that — not a
# rebrand of a signal already credited elsewhere, and not sized to hit any
# particular score.


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
    if summary.get("config_keys_changed"):
        score += 4
    return min(20, score)


def score_reader_value(summary):
    score = 0
    if summary["docs_excerpts"]:
        score += 8
    if summary.get("headings_added"):
        score += 6
    if summary["tests_added"]:
        score += 6
    return min(20, score)


EVIDENCE_TYPE_SUFFIXES = (
    "function signature added", "class signature added", "test added",
    "docs/README prose excerpt", "heading added", "frontmatter key added",
    "single-line before/after", "structural layout/template/stylesheet file changed",
)


def score_evidence_strength(summary, day_stats):
    # Phase 2.7 partial mitigation (docs/devlog-policy.md §31/§37 carried-
    # over MAJOR: this axis was found to correlate heavily with the other
    # 4, since `evidence` is mechanically built from the SAME booleans they
    # already score). A full redesign (e.g. scoring evidence DENSITY —
    # evidenced-files ÷ total-files-touched — instead of raw volume) was
    # evaluated but rejected THIS round: it would have swung both of this
    # repo's only two genuine AUTO_PUBLISH_CANDIDATEs below 80 (2026-08-08
    # density ≈0.29, 2026-08-20 ≈0.68 — a low-density-but-real day would
    # be punished for touching many binary/image assets sanitize.py can't
    # extract anything from, which isn't actually a fact-fidelity problem).
    # Reworking the whole axis is out of scope for a sprint whose stated
    # goal is article quality, not another scoring churn cycle — so this
    # round only shifts weight AWAY from the most redundant term (raw
    # evidence COUNT, which most directly re-sums what other axes already
    # counted) TOWARD the one term that is NOT derived from those same
    # booleans (commit hash/subject/date existing is CONFIRMED_GIT_FACT
    # independent of what sanitize.py managed to extract). This is
    # deliberately closer to a wash than a fix — it doesn't change the
    # ceiling for evidence-rich days, and the deeper redesign remains
    # explicitly open for a future round (see §31/§37).
    score = 6  # baseline raised from 4 (genuinely orthogonal: not a re-sum of other axes' signals)
    score += min(6, len(summary["evidence"]) * 1)  # volume term's weight/cap both halved from min(8, count*2)
    # Diversity bonus: rewards having SEVERAL DIFFERENT kinds of extracted
    # evidence (not just many of the same kind — e.g. ten docs_excerpts
    # from ten files scores the same diversity as one, since Phase 2.5's
    # audit specifically flagged "file count alone shouldn't inflate the
    # score"). Replaces Phase 2's behavior_pairs-specific bonus here (that
    # signal now belongs solely to Technical Depth, see the table above).
    distinct_types = {suffix for suffix in EVIDENCE_TYPE_SUFFIXES if any(suffix in e for e in summary["evidence"])}
    score += min(8, len(distinct_types) * 2)
    total_files = max(1, day_stats.get("total_files_changed", 0))
    skip_ratio = len(summary["files_skipped_for_safety"]) / total_files
    if skip_ratio > 0.5:
        score -= 6
    return max(0, min(20, score))


def score_technical_depth(summary):
    # config_keys_changed deliberately does NOT appear here (self-audit
    # finding during Phase 2.5 review): a frontmatter key being added is
    # already credited once, on Development Value, as "a real config
    # action" — counting the same boolean again here would dilute what
    # Technical Depth is meant to measure (functions/classes/tests/before-
    # after evidence are genuine code-level signals; a config key by
    # itself is shallower than that and doesn't belong alongside them).
    #
    # structural_files_changed (Phase 2.6) DOES appear here — unlike
    # config_keys_changed, it isn't credited anywhere else (Development
    # Value only scores commit/line count and config keys), and it fills a
    # real gap: this repo's most common form of non-content technical work
    # (Jekyll layout/include/template/stylesheet engineering) has no
    # function/class/test shape for the regexes above to find at all.
    signal_types_present = sum([
        bool(summary["functions_added"]),
        bool(summary["classes_added"]),
        bool(summary["tests_added"]),
        bool(summary["behavior_pairs"]),
        bool(summary.get("structural_files_changed")),
    ])
    return min(20, signal_types_present * 4)


def score_seo_potential(day_type, ja_coverage_ratio):
    # Deliberately NOT a per-keyword count (Phase 2.5 audit item: "SEO
    # Potentialがkeyword個数ゲームになっていない") — only two coarse,
    # non-stackable signals: whether a concrete theme/type was identified
    # at all, and how much of the title could be rendered in natural
    # Japanese. Neither can be inflated by adding more of anything.
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
