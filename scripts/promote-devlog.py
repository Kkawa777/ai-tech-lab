#!/usr/bin/env python3
"""Promote a Dev Log draft (drafts/*.md, status: draft) to _articles/
(status: ready) — the ONLY code path allowed to do so.

This is Phase 2's two-stage structure (docs/devlog-policy.md 3節/19節):

    generate-devlog.py --write   ->  drafts/<slug>.md (status: draft)
    promote-devlog.py <draft>    ->  _articles/<slug>.md (status: ready)

Promotion is refused unless ALL of the following hold (Step 16):
  - the file is under drafts/ and has status: draft
  - publish_decision is DRAFT_ONLY or AUTO_PUBLISH_CANDIDATE (not SKIP/BLOCKED)
  - reviewer_status is "pass" in the draft's frontmatter

`reviewer_status` starts as "pending" and is NEVER set to "pass" by
generate-devlog.py itself — only a human, or this session's own
independent-reviewer review of that specific article, may legitimately
set it (see scripts/mark-devlog-reviewed.py). This keeps a real review
checkpoint in the promotion path instead of letting the score alone
decide what goes live, directly addressing the drafts/ mispublication
incident this Phase's design responds to (docs/TODO.md, commit 6c248bd).

Promotion does not commit, push, or otherwise touch Git — it only moves
the file and rewrites its frontmatter. Committing/pushing remains a
separate, manual step, same as for every other article on this site.

Usage:
  python scripts/promote-devlog.py drafts/devlog-ai-tech-lab-2026-08-22.md
  python scripts/promote-devlog.py drafts/devlog-ai-tech-lab-2026-08-22.md --order 92026082200
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devlogkit import frontmatter as fm_lib, score
from devlogkit.frontmatter import ARTICLES_DIR, DRAFTS_DIR, build_order

REQUIRED_DECISIONS = {"DRAFT_ONLY", "AUTO_PUBLISH_CANDIDATE"}


def die(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("draft_path", help="drafts/ 配下のDev Log draftファイルへのパス")
    p.add_argument("--order", type=int, default=None, help="明示的なorder値(省略時は development_date から自動計算)")
    args = p.parse_args()

    draft_path = Path(args.draft_path).resolve()
    try:
        draft_path.relative_to(DRAFTS_DIR.resolve())
    except ValueError:
        die(f"{draft_path} は drafts/ 配下ではありません。promotionはdrafts/からのみ許可されます。")
    if not draft_path.exists():
        die(f"{draft_path} が見つかりません。")

    fm, body = fm_lib.read_frontmatter(draft_path)
    if fm is None:
        die(f"{draft_path} のfrontmatterを読み取れませんでした。")

    if fm.get("status") != "draft":
        die(f"status が 'draft' ではありません(現在: {fm.get('status')!r})。promotion対象外です。")

    decision = fm.get("publish_decision")
    if decision not in REQUIRED_DECISIONS:
        die(
            f"publish_decision が {REQUIRED_DECISIONS} のいずれでもありません"
            f"(現在: {decision!r})。SKIP/BLOCKEDのdraftは昇格できません。"
        )

    if fm.get("reviewer_status") != "pass":
        die(
            "reviewer_status が 'pass' になっていません"
            f"(現在: {fm.get('reviewer_status')!r})。"
            "independent-reviewer(または人による最終レビュー)を経て、"
            "scripts/mark-devlog-reviewed.py で明示的にpassへ更新してから再実行してください。"
            "スコアだけでは昇格できない設計です。"
        )

    # Re-scan the draft's CURRENT content (not the score/gate results
    # recorded at generation time). docs/devlog-policy.md's normal workflow
    # expects a human to hand-edit title/primary_keyword between generation
    # and promotion, so a stale `publish_decision`/`reviewer_status` alone
    # cannot prove the file is still safe — an edit made after generation
    # (or after the reviewer's pass) could have introduced a secret or a
    # local path that neither of those recorded fields would reflect.
    gates = score.check_safety_gates(fm_lib.render_markdown(fm, body))
    if gates["security"] == "FAIL" or gates["privacy"] == "FAIL":
        die(
            "promotion時の再スキャンでSecurity/Privacy gateがFAILしました: "
            f"{'; '.join(gates['reasons'])}。draft生成後またはレビュー後に本文・frontmatterへ"
            "加えられた変更が原因の可能性があります。内容を修正してから再実行してください。"
        )

    development_date = fm.get("development_date")
    order = args.order if args.order is not None else build_order(development_date, 0)

    fm["status"] = "ready"
    fm["order"] = order
    rendered = fm_lib.render_markdown(fm, body)

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = ARTICLES_DIR / draft_path.name
    if dest_path.exists():
        die(f"{dest_path} は既に存在します。上書きを避けるため中断します。")

    dest_path.write_text(rendered, encoding="utf-8")
    draft_path.unlink()

    print(f"[PROMOTED] {draft_path} -> {dest_path} (status: ready, order: {order})")
    print(
        "[NEXT] scripts/validate-site.py を実行し、git add で明示的にstageしてから"
        "commit/pushしてください(promoteはGit操作を一切行いません)。"
    )


if __name__ == "__main__":
    main()
