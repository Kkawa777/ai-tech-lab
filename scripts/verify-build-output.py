#!/usr/bin/env python3
"""Post-Jekyll-build safety check (Phase 2, docs/devlog-policy.md 8節).

Runs against the actual `_site/` build output in CI, AFTER `Build with
Jekyll` and BEFORE the artifact is uploaded/deployed. This is defense in
depth for the exact incident this Phase's design responds to: `drafts/`
was missing from _config.yml's `exclude:` list for an unknown period, so
a draft article was built and published live (fixed in commit 6c248bd;
regression-tested statically by validate-site.py's check_drafts_excluded,
which only checks _config.yml's *source* text). This script instead
inspects the *built output*, so it would catch the same class of bug even
if some other future misconfiguration (not just a missing drafts/
exclude) let something unintended through.

Checks:
  1. _site/drafts/ must not exist.
  2. _site/config/ must not exist.
  3. Every _site/articles/<slug>/index.html must correspond to a
     `_articles/<file>.md` whose `permalink:` is `/articles/<slug>/` —
     i.e. every published URL must be traceable to a real, checked-in,
     status: ready source file. A URL with no such backing source (e.g.
     one built from drafts/ using its own frontmatter permalink) fails.
  4. sitemap.xml (if present) must not reference any URL that isn't
     backed by an `_articles/*.md` permalink either.

Usage (from repo root, after `Build with Jekyll` has produced ./_site):
  python scripts/verify-build-output.py
Exit code: 0 if all checks pass, 1 otherwise.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "_site"
ARTICLES_DIR = ROOT / "_articles"

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print(f"[FAIL] {msg}")


def ok(msg):
    print(f"[ OK ] {msg}")


def known_permalinks():
    permalinks = set()
    if not ARTICLES_DIR.exists():
        return permalinks
    for f in ARTICLES_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        m = re.search(r"^permalink:\s*(\S+)", parts[1], re.MULTILINE)
        if m:
            permalinks.add(m.group(1).strip())
    return permalinks


def check_no_drafts_in_site():
    if (SITE_DIR / "drafts").exists():
        fail("_site/drafts/ が存在します(drafts/ がビルドに含まれています)")
    else:
        ok("no _site/drafts/")


def check_no_config_in_site():
    if (SITE_DIR / "config").exists():
        fail("_site/config/ が存在します(config/ がビルドに含まれています)")
    else:
        ok("no _site/config/")


def check_every_built_article_has_source(permalinks):
    articles_out = SITE_DIR / "articles"
    if not articles_out.exists():
        ok("no _site/articles/ (nothing to check)")
        return
    bad = []
    for entry in sorted(articles_out.iterdir()):
        if not entry.is_dir():
            continue
        permalink = f"/articles/{entry.name}/"
        if permalink not in permalinks:
            bad.append(permalink)
    if bad:
        fail(f"_articles/ に対応するsourceがない公開URLがあります: {bad}")
    else:
        ok(f"built articles match _articles/ sources ({len(permalinks)} known permalinks)")


def check_sitemap(permalinks):
    sitemap = SITE_DIR / "sitemap.xml"
    if not sitemap.exists():
        ok("no sitemap.xml (nothing to check)")
        return
    text = sitemap.read_text(encoding="utf-8", errors="replace")
    urls = re.findall(r"<loc>(.*?)</loc>", text)
    bad = []
    for url in urls:
        m = re.search(r"(/articles/[^/]+/)$", url)
        if m and m.group(1) not in permalinks:
            bad.append(url)
    if bad:
        fail(f"sitemap.xml に _articles/ の裏付けがないURLがあります: {bad}")
    else:
        ok(f"sitemap.xml URLs all backed by _articles/ ({len(urls)} URLs checked)")


def main():
    if not SITE_DIR.exists():
        print(f"[ERROR] {SITE_DIR} が見つかりません。Jekyll buildの後に実行してください。", file=sys.stderr)
        sys.exit(1)

    permalinks = known_permalinks()
    check_no_drafts_in_site()
    check_no_config_in_site()
    check_every_built_article_has_source(permalinks)
    check_sitemap(permalinks)

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s).")
        sys.exit(1)
    print("\nAll build-output safety checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
