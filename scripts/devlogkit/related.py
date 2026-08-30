"""Related-article matching (Phase 2, docs/devlog-policy.md 16節).

Pure keyword-overlap heuristic against existing _articles/ frontmatter —
no LLM judgment call about "relatedness". Returns at most 3 candidates,
and returns an empty list rather than a weak/irrelevant match (Step 11:
"無関係な内部リンクは入れない").
"""
import re
from pathlib import Path

import yaml

from .frontmatter import split_frontmatter as _split_frontmatter_and_body


def _split_frontmatter(text):
    fm_text, _ = _split_frontmatter_and_body(text)
    return fm_text


def _keywords_from_text(text):
    return {w.lower() for w in re.findall(r"[A-Za-z0-9]+|[぀-ヿ一-鿿]+", text) if len(w) >= 2}


def _load_existing_articles(articles_dir):
    articles = []
    if not articles_dir.exists():
        return articles
    for f in sorted(articles_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm_text = _split_frontmatter(text)
        if not fm_text:
            continue
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict) or fm.get("status") != "ready":
            continue
        title = fm.get("title", "")
        permalink = fm.get("permalink", "")
        keyword_source = " ".join(str(fm.get(k, "")) for k in ("title", "category", "primary_keyword", "search_intent"))
        articles.append({
            "title": title,
            "permalink": permalink,
            "keywords": _keywords_from_text(keyword_source),
        })
    return articles


def find_related_articles(articles_dir, day_type, notable_subjects, summary, max_results=3):
    query_text = " ".join(notable_subjects) + " " + day_type
    query_text += " " + " ".join(summary.get("functions_added", []))
    query_text += " " + " ".join(summary.get("classes_added", []))
    query_keywords = _keywords_from_text(query_text)
    if not query_keywords:
        return []

    scored = []
    for art in _load_existing_articles(Path(articles_dir)):
        overlap = query_keywords & art["keywords"]
        if len(overlap) >= 2:  # require a real overlap, not one coincidental short token
            scored.append((len(overlap), art))
    scored.sort(key=lambda pair: -pair[0])
    return [art for _, art in scored[:max_results]]
