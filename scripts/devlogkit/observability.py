"""Structured JSONL run logging (Phase 2, docs/devlog-policy.md 20節).

One JSON line per generation run, appended to `devlog-logs/<project>.jsonl`
(gitignored — this is operational telemetry, not site content or reviewed
documentation, so it does not belong in Git history). Every field is
passed through a defensive secret-redaction pass before being written,
even though nothing upstream should ever hand this module a raw secret
value in the first place — this is the same "assume upstream might have a
bug" posture as score.py's final-text safety gates.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from .security import SECRET_VALUE_PATTERNS

ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT / "devlog-logs"


def _redact(value):
    if isinstance(value, str):
        redacted = value
        for pat in SECRET_VALUE_PATTERNS:
            redacted = pat.sub("[REDACTED]", redacted)
        return redacted
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    return value


def log_run(entry: dict):
    """entry should include at least: date, project, decision. Common
    optional fields (per Step 20): commits_found, notable_commits,
    security_filtered, quality_score, draft_path, article_path, reason."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    project = entry.get("project", "unknown")
    safe_entry = _redact(dict(entry))
    safe_entry["logged_at"] = datetime.now(timezone.utc).isoformat()
    log_path = LOG_DIR / f"{project}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe_entry, ensure_ascii=False) + "\n")
    return log_path
