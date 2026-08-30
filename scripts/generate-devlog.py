#!/usr/bin/env python3
"""Generate a Dev Log article draft from a project's Git history for one date.

Phase 2 (docs/devlog-policy.md): a single collect -> sanitize -> classify
-> score -> generate -> gate pipeline (scripts/devlogkit/pipeline.py) drives
all three modes below. See docs/devlog-policy.md for the full design
(allowlist rules, Sanitized Change Summary Layer, Quality Score, Publish
Gate, dedup/idempotency, order numbering, status lifecycle).

Modes:
  (no flag)   dry-run preview to stdout. Default and safe: writes nothing.
  --write     writes the draft to drafts/ (status: draft) unless the
              pipeline's decision is BLOCKED, in which case it refuses and
              explains why — even an explicit --write cannot force past a
              failed Security/Privacy/Fact gate.
  --auto      same effect as --write, but framed for unattended/scheduled
              invocation: prints a single-line decision
              (AUTO_PUBLISH_CANDIDATE / DRAFTED / SKIPPED / BLOCKED) and
              uses a distinct exit code for BLOCKED (3) so automation can
              alert on it differently from "nothing to do" (0).

Neither --write nor --auto ever writes into _articles/ or promotes,
commits, or pushes anything — see scripts/promote-devlog.py for that
separate, explicitly human/session-gated step.

Usage:
  python scripts/generate-devlog.py --project ai-tech-lab --repo "C:\\Projects" --date 2026-08-24
  python scripts/generate-devlog.py --project ai-tech-lab --repo "C:\\Projects" --date 2026-08-24 --write
  python scripts/generate-devlog.py --project ai-tech-lab --repo "C:\\Projects" --date 2026-08-24 --auto
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devlogkit import allowlist, observability, pipeline, score


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", required=True, help="config/devlog-projects.yaml のproject key")
    p.add_argument("--repo", required=True, help="対象repositoryのパス(allowlistのpathと一致する必要あり)")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="生成結果を標準出力へ表示するのみ(デフォルト)")
    mode.add_argument("--write", action="store_true", help="drafts/ へ実際にファイルを書き出す")
    mode.add_argument("--auto", action="store_true", help="自動運用向け(--writeと同じ効果+決定結果を1行出力+専用exit code)")
    return p.parse_args()


def main():
    args = parse_args()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        print("[ERROR] --date は YYYY-MM-DD 形式で指定してください。", file=sys.stderr)
        sys.exit(1)

    try:
        projects = allowlist.load_allowlist()
        entry, repo_path = allowlist.resolve_and_validate_project(args.project, args.repo, projects)
    except allowlist.AllowlistError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    result = pipeline.run(args.project, entry, repo_path, args.date)

    print(
        f"[INFO] {args.date}: 全commit {result.stats.get('total_commits', 0)}件 "
        f"(trivial除外 {result.stats.get('trivial_excluded', 0)}件, "
        f"secret該当除外 {result.stats.get('secret_excluded', 0)}件, "
        f"merge除外 {result.stats.get('merge_excluded', 0)}件, "
        f"記事化候補 {result.stats.get('notable_commits', 0)}件)"
    )
    if result.quality_score is not None:
        print(f"[INFO] Quality Score: {result.quality_score}/100 {result.score_breakdown}")
    if result.gates is not None:
        print(f"[INFO] Gates: security={result.gates['security']} privacy={result.gates['privacy']} fact={result.gates['fact']}")

    log_entry = {
        "date": args.date, "project": args.project,
        "commits_found": result.stats.get("total_commits", 0),
        "notable_commits": result.stats.get("notable_commits", 0),
        "security_filtered": result.stats.get("secret_excluded", 0),
        "quality_score": result.quality_score,
        "decision": result.decision,
        "reason": result.reason,
        "draft_path": None,
    }

    if result.decision == score.SKIP:
        print(f"[SKIP] {result.reason}")
    elif result.decision == score.BLOCKED:
        print(f"[BLOCKED] {result.reason}", file=sys.stderr)
    elif args.write or args.auto:
        # DRAFT_ONLY or AUTO_PUBLISH_CANDIDATE, and the caller asked to persist it.
        out_path = pipeline.write_draft(result)
        log_entry["draft_path"] = str(out_path)
        print(f"[WRITE] {out_path} へ status: draft で書き出しました(decision={result.decision})。")
        from devlogkit.frontmatter import build_order
        print(
            f"[NEXT] _articles/ への昇格は `python scripts/promote-devlog.py {out_path}` を使用してください。"
            f" suggested order: {build_order(args.date)}"
        )

    observability.log_run(log_entry)

    if not (args.write or args.auto):
        # dry-run: always show what was generated, whatever the decision,
        # so an operator can see *why* something scored the way it did —
        # nothing is written to disk in this mode regardless.
        if result.rendered_markdown:
            print("\n" + "=" * 70)
            print(f"[DRY-RUN] 以下は生成プレビューです(decision={result.decision})。ファイルは書き出していません。")
            print("=" * 70 + "\n")
            print(result.rendered_markdown)
        else:
            print("[DRY-RUN] 生成対象のcommitがなかったため、プレビューはありません。")

    if args.auto:
        print(f"DECISION={result.decision}")

    sys.exit(3 if result.decision == score.BLOCKED else 0)


if __name__ == "__main__":
    main()
