#!/usr/bin/env python3
"""Record an independent-review outcome on a Dev Log draft's frontmatter.

This is the ONLY way `reviewer_status` ever becomes "pass" — it is never
set by generate-devlog.py itself, precisely so that a Quality Score alone
can never promote an article to _articles/ (see scripts/promote-devlog.py,
which refuses promotion unless this has been run with --pass).

This script does not run any review itself — it only records that one
already happened (an independent-reviewer subagent pass, or a human
editorial review) outside of this script, matching this repository's
existing quality-development workflow for every other article type.

Phase 2.5 adds review PROVENANCE (Step 11, docs/devlog-policy.md): a
`--pass` records not just the status but:
  reviewed_content_hash  SHA-256 fingerprint of the CURRENT frontmatter
                          (minus the review/promotion bookkeeping fields
                          themselves) + body, via
                          frontmatter.compute_content_fingerprint().
  reviewed_at             UTC timestamp of when this was recorded.
  reviewer_method         what kind of review this was (free text, e.g.
                          "independent-reviewer" or "human-editorial") —
                          no personal names or other identifying info.

scripts/promote-devlog.py recomputes the same fingerprint at promotion
time and refuses to promote if it no longer matches — i.e. ANY edit made
to the reviewed content after this script ran (a stray character, an
added paragraph, a frontmatter tweak, a swapped source_commits list)
invalidates the review, not just the specific secret/path patterns a
regex-based re-scan happens to catch.

Usage:
  python scripts/mark-devlog-reviewed.py drafts/devlog-ai-tech-lab-2026-08-22.md --pass --method independent-reviewer
  python scripts/mark-devlog-reviewed.py drafts/devlog-ai-tech-lab-2026-08-22.md --fail --reason "..."
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devlogkit import frontmatter as fm_lib, score
from devlogkit.frontmatter import DRAFTS_DIR


def die(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("draft_path")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--pass", dest="passed", action="store_true")
    group.add_argument("--fail", dest="passed", action="store_false")
    p.add_argument("--reason", default="", help="--fail 時の理由(任意、記録のみ)")
    p.add_argument(
        "--method", default="unspecified",
        help="レビュー方法の識別子(例: independent-reviewer, human-editorial)。個人名は入れない。",
    )
    args = p.parse_args()

    draft_path = Path(args.draft_path).resolve()
    try:
        draft_path.relative_to(DRAFTS_DIR.resolve())
    except ValueError:
        die(f"{draft_path} は drafts/ 配下ではありません。")
    if not draft_path.exists():
        die(f"{draft_path} が見つかりません。")

    fm, body = fm_lib.read_frontmatter(draft_path)
    if fm is None:
        die(f"{draft_path} のfrontmatterを読み取れませんでした。")

    if args.passed:
        # Re-scan the file's CURRENT content before recording a "pass" —
        # a human may have hand-edited title/primary_keyword (the normal,
        # expected workflow per docs/devlog-policy.md 9節) since this draft
        # was generated, and that edit could have introduced something the
        # generation-time gate never saw.
        gates = score.check_safety_gates(fm_lib.render_markdown(fm, body))
        if gates["security"] == "FAIL" or gates["privacy"] == "FAIL":
            die(
                "現在の内容でSecurity/Privacy gateの再スキャンがFAILしたため、"
                f"reviewer_status を pass にできません: {'; '.join(gates['reasons'])}。"
                "内容を修正してから再実行してください。"
            )
        fm["reviewer_status"] = "pass"
        fm["reviewer_method"] = args.method
        fm["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        # Fingerprint computed AFTER the above fields are removed from the
        # canonical payload by compute_content_fingerprint() itself (they're
        # in REVIEW_BOOKKEEPING_KEYS), so setting them first vs. after
        # doesn't change the hash — order here is just for clarity.
        fm["reviewed_content_hash"] = fm_lib.compute_content_fingerprint(fm, body)
    else:
        fm["reviewer_status"] = "fail"
        # A failed review's hash/timestamp/method would be misleading if
        # left over from a previous pass attempt on the same file.
        for key in ("reviewed_content_hash", "reviewed_at", "reviewer_method"):
            fm.pop(key, None)

    if args.reason:
        fm["reviewer_note"] = args.reason

    draft_path.write_text(fm_lib.render_markdown(fm, body), encoding="utf-8")
    print(f"[OK] {draft_path}: reviewer_status = {fm['reviewer_status']}")
    if args.passed:
        print(f"[OK] reviewed_content_hash = {fm['reviewed_content_hash'][:16]}... (recorded)")


if __name__ == "__main__":
    main()
