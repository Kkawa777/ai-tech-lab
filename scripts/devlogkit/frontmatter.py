"""Frontmatter rendering, dedup lookup, and order numbering.

render_markdown() delegates all YAML escaping to PyYAML (not hand-rolled
string building — a Phase 1 bug class this avoids structurally). Extended
in Phase 2 with the Quality Gate fields needed by promote.py to verify a
draft's gate results without re-running the whole pipeline.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
ARTICLES_DIR = ROOT / "_articles"
DRAFTS_DIR = ROOT / "drafts"


def split_frontmatter(text):
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    return parts[1], parts[2]


def find_existing_source_commits(project_key):
    seen = set()
    for d in (ARTICLES_DIR, DRAFTS_DIR):
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm, _ = split_frontmatter(text)
            if not fm:
                continue
            try:
                data = yaml.safe_load(fm) or {}
            except yaml.YAMLError:
                continue
            if isinstance(data, dict) and data.get("generated_from_git") and data.get("source_project") == project_key:
                for h in data.get("source_commits") or []:
                    seen.add(h)
    return seen


def build_order(date_str, seq=0):
    # Reserved namespace for devlog articles, separate from the
    # hand-authored article catalog (order: 1-99). See docs/devlog-policy.md.
    return int(f"9{date_str.replace('-', '')}{seq:02d}")


def render_markdown(frontmatter: dict, body: str) -> str:
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{fm_text}---\n\n{body}"


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        return None, None
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None, None
    return data, body
