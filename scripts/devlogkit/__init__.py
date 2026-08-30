"""Dev Log automation engine (Phase 2).

See docs/devlog-policy.md for the full design (Fact rules, security model,
Quality Score, promotion gate). This package is imported by the CLIs:
scripts/generate-devlog.py, scripts/promote-devlog.py,
scripts/run-daily-devlog.py.

Module map:
  allowlist.py    - config/devlog-projects.yaml loading + realpath validation
  gitmeta.py      - Git metadata collection (hash/date/subject/files/stat)
  security.py     - secret patterns + denylisted-path patterns (Phase 1 +
                    Phase 2 diff-content scanning)
  sanitize.py     - Sanitized Change Summary Layer (Step 4/5)
  classify.py     - trivial-commit filter + article-type classification
  score.py        - Quality Score model + gates + publish decision
  ja.py           - deterministic English->Japanese term mapping (no LLM)
  templates.py    - per-type Japanese article body rendering
  related.py      - related-article matching against _articles/
  screenshots.py  - screenshot candidate discovery (design + minimal impl)
  observability.py - structured JSONL run logging (secret-redacted)
  frontmatter.py  - YAML frontmatter render/parse, dedup, order numbering
  promote.py      - draft -> _articles/ promotion logic
"""
