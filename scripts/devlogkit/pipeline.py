"""The single collect -> sanitize -> classify -> score -> generate -> gate
pipeline (Phase 2, docs/devlog-policy.md 4節). Used by every entry point
(scripts/generate-devlog.py's --dry-run/--write/--auto, and
scripts/run-daily-devlog.py) so there is exactly one implementation of the
decision logic to review and test — not a "Phase 1 path" and a separate
"Phase 2 path" that can silently drift apart.
"""
from pathlib import Path

from . import classify, frontmatter, gitmeta, related, score, screenshots, security, templates

ROOT = Path(__file__).resolve().parent.parent.parent
ARTICLES_DIR = ROOT / "_articles"
DRAFTS_DIR = ROOT / "drafts"


class PipelineResult:
    def __init__(self):
        self.decision = None
        self.reason = ""
        self.quality_score = None
        self.score_breakdown = None
        self.gates = None
        self.draft_path = None
        self.stats = {}
        self.rendered_markdown = None
        self.slug = None


def _collect_notable(repo_path, date_str):
    all_commits = gitmeta.list_commits_on_date(repo_path, date_str)
    notable = []
    stats = {"total": len(all_commits), "trivial": 0, "secret_excluded": 0, "merge_excluded": 0}
    for c in all_commits:
        if gitmeta.is_merge_commit(repo_path, c["hash"]):
            stats["merge_excluded"] += 1
            continue
        files = gitmeta.get_changed_files(repo_path, c["hash"])
        file_paths = [f["path"] for f in files]
        if security.contains_secret_pattern(c["subject"]) or any(security.filename_is_secret_like(p) for p in file_paths):
            stats["secret_excluded"] += 1
            continue
        if classify.is_trivial(c, files):
            stats["trivial"] += 1
            continue
        notable.append({**c, "files": files, "stat": gitmeta.get_shortstat(repo_path, c["hash"])})
    return notable, stats


def run(project_key: str, entry: dict, repo_path: Path, date_str: str) -> PipelineResult:
    result = PipelineResult()

    notable, stats = _collect_notable(repo_path, date_str)
    result.stats = {
        "total_commits": stats["total"],
        "trivial_excluded": stats["trivial"],
        "secret_excluded": stats["secret_excluded"],
        "merge_excluded": stats["merge_excluded"],
        "notable_commits": len(notable),
    }

    if not notable:
        result.decision = score.SKIP
        result.reason = f"{date_str} は記事化に値するcommitがありません(開発なし、または軽微な変更のみ)。"
        return result

    existing = frontmatter.find_existing_source_commits(project_key)
    new_hashes = [c["hash"] for c in notable]
    if existing and set(new_hashes).issubset(existing):
        result.decision = score.SKIP
        result.reason = f"{date_str} のcommitはすべて既存のDev Log記事に含まれています(重複防止のためSKIP)。"
        return result
    before = len(notable)
    notable = [c for c in notable if c["hash"] not in existing]
    if not notable:
        result.decision = score.SKIP
        result.reason = f"{date_str} は重複除外後、記事化対象のcommitが残りませんでした。"
        return result
    result.stats["deduped_out"] = before - len(notable)

    # --- Sanitized Change Summary Layer ---
    from . import sanitize
    per_commit_summaries = [sanitize.build_sanitized_summary(repo_path, c, c["files"]) for c in notable]
    merged_summary = sanitize.merge_day_summaries(per_commit_summaries)

    day_type = classify.classify_day_type([(c, c["files"]) for c in notable])

    display_name = entry.get("display_name", project_key)
    title, used_japanese, coverage = templates.build_headline(display_name, notable)

    total_insertions = sum(c["stat"]["insertions"] for c in notable)
    total_deletions = sum(c["stat"]["deletions"] for c in notable)
    total_files_changed = sum(c["stat"]["files_changed"] for c in notable)
    day_stats = {
        "notable_commit_count": len(notable),
        "insertions": total_insertions,
        "deletions": total_deletions,
        "total_files_changed": total_files_changed,
    }

    total_score, breakdown = score.compute_quality_score(day_stats, merged_summary, day_type, coverage)
    result.quality_score = total_score
    result.score_breakdown = breakdown

    # --- Article assembly ---
    slug = f"devlog-{project_key}-{date_str}"
    result.slug = slug
    body = templates.render_body(day_type, display_name, notable, merged_summary)

    subjects_cleaned = [templates.clean_subject(c["subject"]) for c in notable]
    # Phase 2.6: translate each subject independently for the description
    # (falling back to the original English per-subject, not per-day, when
    # a given subject doesn't meet ja.coverage_is_usable()) — previously
    # this always embedded the raw English subjects verbatim even when the
    # title above translated cleanly, which an independent review flagged
    # as an inconsistency that reads like a generation bug.
    subjects_for_description = [templates.translated_or_original(s)[0] for s in subjects_cleaned]
    description = (
        f"{date_str}に{display_name}リポジトリで行われた開発のログです。"
        f"Git履歴とdiffから確認できる変更: {'、'.join(subjects_for_description[:5])}"
        f"{f' ほか{len(subjects_for_description) - 5}件' if len(subjects_for_description) > 5 else ''}。"
    )
    primary_keyword = f"{display_name} {classify.DAY_TYPE_JA_LABEL.get(day_type, '開発ログ')}"
    social_summary = title[:140]

    screenshot_candidates = screenshots.discover_candidates(repo_path, date_str)
    related_articles = related.find_related_articles(ARTICLES_DIR, day_type, subjects_cleaned, merged_summary)

    fm = {
        "title": title,
        "status": "draft",
        "permalink": f"/articles/{slug}/",
        "order": None,
        "category": "開発ログ",
        "difficulty": None,
        "estimated_time": "読了目安 約3分",
        "description": description,
        "content_type": "devlog",
        "primary_keyword": primary_keyword,
        "search_intent": f"{display_name}の開発状況・変更履歴を知りたい",
        "monetization": "none",
        "conversion_goal": None,
        "source_project": project_key,
        "source_commits": new_hashes,
        "development_date": date_str,
        "generated_from_git": True,
        "social_summary": social_summary,
        "article_type": day_type,
        "title_translation_coverage": round(coverage, 2),
        "screenshot_candidates": screenshot_candidates,
        "related_articles": [a["permalink"] for a in related_articles],
        "reviewer_status": "pending",  # only a human/session review step may change this — see docs/devlog-policy.md 3節
    }

    rendered = frontmatter.render_markdown(fm, body)

    # --- Final-text safety gates (independent of sanitize.py's own filtering) ---
    gates = score.check_safety_gates(rendered, merged_summary)
    result.gates = gates
    decision = score.decide(total_score, gates)
    result.decision = decision
    result.rendered_markdown = rendered

    if decision == score.BLOCKED:
        result.reason = "; ".join(gates["reasons"]) or "safety gate failed"
        return result

    fm["publish_decision"] = decision
    rendered = frontmatter.render_markdown(fm, body)
    result.rendered_markdown = rendered
    result.reason = (
        f"quality_score={total_score} (>= {score.AUTO_PUBLISH_THRESHOLD} で候補昇格可)"
        if decision != score.SKIP else "score below threshold"
    )
    return result


def write_draft(result: PipelineResult) -> Path:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DRAFTS_DIR / f"{result.slug}.md"
    out_path.write_text(result.rendered_markdown, encoding="utf-8")
    result.draft_path = out_path
    return out_path
