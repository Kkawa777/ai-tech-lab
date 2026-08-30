#!/usr/bin/env python3
"""Daily Dev Log runner (Phase 2, docs/devlog-policy.md 21節).

Iterates every project in config/devlog-projects.yaml that is both
enabled and public, and runs the collect -> sanitize -> score -> generate
pipeline for "today" (Asia/Tokyo by default, or an explicit --date for
testing) against each. A project whose pipeline raises an exception is
logged and skipped — it never stops the remaining projects (Step 19).

This script does NOT register itself with any OS/CI scheduler. It is the
thing a scheduler should invoke daily (e.g. a GitHub Actions `schedule:`
cron entry, or Windows Task Scheduler at 20:00 Asia/Tokyo) — see
docs/devlog-policy.md 21節 for the invocation shape once that's set up.

Like generate-devlog.py, this never writes into _articles/, commits, or
pushes — only drafts/. Promotion remains scripts/promote-devlog.py, run
separately, after a real review.

`run_all()` is factored out as a plain function (taking the already-loaded
project list rather than reading config/argv itself) specifically so
scripts/test_devlog.py can call this module's REAL code — not a
reimplementation of its loop — when testing per-project failure isolation
(see docs/devlog-policy.md: an earlier version's test for this only
exercised a copy of the loop written inline in the test file, which would
not have caught a regression in this file itself).

Usage:
  python scripts/run-daily-devlog.py                 # today, Asia/Tokyo, writes drafts
  python scripts/run-daily-devlog.py --date 2026-08-22 --dry-run
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devlogkit import allowlist, observability, pipeline, score


def run_all(date_str, write_mode, targets):
    """targets: iterable of (project_key, entry, repo_path), typically from
    allowlist.enabled_public_projects(). Returns a list of
    (project_key, decision_str, reason_str) tuples, one per target, in
    order. Never raises for an individual project's failure — see the
    try/except below, which wraps the ENTIRE per-project unit of work
    (pipeline execution, draft writing, and logging), not just the
    pipeline call, so a failure in any of those three steps is isolated
    the same way."""
    summary = []
    for key, entry, repo_path in targets:
        print(f"--- {key} ---")
        try:
            result = pipeline.run(key, entry, repo_path, date_str)
            draft_path = None
            if result.decision in (score.DRAFT_ONLY, score.AUTO_PUBLISH_CANDIDATE) and write_mode:
                draft_path = pipeline.write_draft(result)
            observability.log_run({
                "date": date_str, "project": key,
                "commits_found": result.stats.get("total_commits", 0),
                "notable_commits": result.stats.get("notable_commits", 0),
                "security_filtered": result.stats.get("secret_excluded", 0),
                "quality_score": result.quality_score,
                "decision": result.decision,
                "reason": result.reason,
                "draft_path": str(draft_path) if draft_path else None,
            })
        except Exception as e:  # noqa: BLE001 - one project's bug must never stop the others
            print(f"[ERROR] {key}: パイプライン実行中に例外が発生しました: {e}", file=sys.stderr)
            observability.log_run({"date": date_str, "project": key, "decision": "ERROR", "reason": str(e)})
            summary.append((key, "ERROR", str(e)))
            continue
        tail = f" -> {draft_path}" if draft_path else ""
        print(f"[{result.decision}] {result.reason}{tail}\n")
        summary.append((key, result.decision, result.reason))
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", default=None, help="YYYY-MM-DD(省略時は Asia/Tokyo の本日)")
    p.add_argument("--dry-run", action="store_true", help="drafts/ へ書き出さずpreviewのみ")
    args = p.parse_args()

    date_str = args.date or datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")
    write_mode = not args.dry_run

    try:
        projects = allowlist.load_allowlist()
    except allowlist.AllowlistError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    targets = list(allowlist.enabled_public_projects(projects))
    if not targets:
        print("[WARN] enabled かつ public な project が config/devlog-projects.yaml にありません。何もしません。")
        sys.exit(0)

    print(f"=== Daily Dev Log run: {date_str} (Asia/Tokyo), {len(targets)} project(s) ===\n")
    summary = run_all(date_str, write_mode, targets)

    print("=== Summary ===")
    for key, decision, reason in summary:
        print(f"{key}: {decision} ({reason})")


if __name__ == "__main__":
    main()
