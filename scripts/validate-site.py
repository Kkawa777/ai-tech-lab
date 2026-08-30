#!/usr/bin/env python3
"""Lightweight, dependency-light site validation for AI-Tech-Lab.

No local Ruby/Jekyll is available, so this cannot run a real `jekyll build`.
It instead statically checks the things most likely to break the site or
violate the project's factuality/affiliate rules, mirroring (and extending)
the checks already done in .github/workflows/pages.yml and
.claude/hooks/check-article-status.js.

Usage: python scripts/validate-site.py
Exit code: 0 if all checks pass, 1 if any check fails.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from devlogkit.frontmatter import split_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FAILURES = []
WARNINGS = []


def fail(check, msg):
    FAILURES.append(f"[FAIL] {check}: {msg}")


def warn(check, msg):
    WARNINGS.append(f"[WARN] {check}: {msg}")


def ok(check, msg=""):
    print(f"[ OK ] {check}{(': ' + msg) if msg else ''}")


def read(path):
    return path.read_text(encoding="utf-8")


def check_ready_status():
    """_articles/*.md must all have status: ready (mirrors CI + local hook)."""
    articles_dir = ROOT / "_articles"
    files = sorted(articles_dir.glob("*.md")) if articles_dir.exists() else []
    bad = []
    for f in files:
        content = read(f)
        if not re.search(r"^status:\s*ready\s*$", content, re.MULTILINE):
            bad.append(f.name)
    if bad:
        fail("status:ready", f"_articles/ に status:ready でないファイル: {bad}")
    else:
        ok("status:ready", f"{len(files)} files")


def check_frontmatter_yaml():
    """Frontmatter must be parseable YAML for every _articles/ and docs/articles/ file."""
    try:
        import yaml
    except ImportError:
        warn("frontmatter-yaml", "PyYAML未インストールのためスキップ")
        return
    targets = list((ROOT / "_articles").glob("*.md"))
    docs_articles = ROOT / "docs" / "articles"
    if docs_articles.exists():
        targets += list(docs_articles.glob("*.md"))
    bad = []
    for f in targets:
        fm, _ = split_frontmatter(read(f))
        if fm is None:
            bad.append((f.name, "no frontmatter block found"))
            continue
        try:
            yaml.safe_load(fm)
        except yaml.YAMLError as e:
            bad.append((f.name, str(e)))
    if bad:
        for name, err in bad:
            fail("frontmatter-yaml", f"{name}: {err}")
    else:
        ok("frontmatter-yaml", f"{len(targets)} files")


def check_liquid_balance():
    """{% ... %} tags must open/close in equal counts across templates and articles."""
    patterns = ["_layouts/*.html", "_includes/*.html", "_articles/*.md", "docs/articles/*.md"]
    bad = []
    checked = 0
    for pattern in patterns:
        for f in ROOT.glob(pattern):
            content = read(f)
            o, c = content.count("{%"), content.count("%}")
            checked += 1
            if o != c:
                bad.append(f"{f.relative_to(ROOT)} (opens={o} closes={c})")
    if bad:
        for b in bad:
            fail("liquid-balance", b)
    else:
        ok("liquid-balance", f"{checked} files")


def check_images_exist_and_have_alt():
    """Every ![alt](...) in _articles/ must have non-empty alt text and an existing file."""
    bad_missing_file = []
    bad_empty_alt = []
    checked = 0
    for f in (ROOT / "_articles").glob("*.md"):
        content = read(f)
        for m in re.finditer(r'!\[([^\]]*)\]\(\{\{\s*"([^"]+)"\s*\|\s*relative_url\s*\}\}\)', content):
            checked += 1
            alt, path = m.group(1), m.group(2)
            if not alt.strip():
                bad_empty_alt.append(f"{f.name}: {path}")
            local_path = ROOT / path.lstrip("/")
            if not local_path.exists():
                bad_missing_file.append(f"{f.name}: {path}")
        # frontmatter eyecatch
        fm, _ = split_frontmatter(content)
        if fm:
            img_path_m = re.search(r"image:\s*\n\s*path:\s*(\S+)", fm)
            img_alt_m = re.search(r"image:\s*\n\s*path:\s*\S+\s*\n\s*alt:\s*(.+)", fm)
            if img_path_m:
                checked += 1
                p = img_path_m.group(1).strip()
                if p and not (ROOT / p.lstrip("/")).exists():
                    bad_missing_file.append(f"{f.name} (frontmatter image): {p}")
                if not img_alt_m or not img_alt_m.group(1).strip():
                    bad_empty_alt.append(f"{f.name} (frontmatter image alt)")
    if bad_missing_file:
        for b in bad_missing_file:
            fail("image-exists", b)
    if bad_empty_alt:
        for b in bad_empty_alt:
            fail("image-alt", b)
    if not bad_missing_file and not bad_empty_alt:
        ok("images (exist + alt)", f"{checked} references")


def check_internal_links():
    """{{ "/articles/x/" | relative_url }} targets must match a real article permalink."""
    permalinks = set()
    for f in (ROOT / "_articles").glob("*.md"):
        fm, _ = split_frontmatter(read(f))
        if fm:
            m = re.search(r"^permalink:\s*(\S+)", fm, re.MULTILINE)
            if m:
                permalinks.add(m.group(1).strip())
    bad = []
    checked = 0
    for f in (ROOT / "_articles").glob("*.md"):
        content = read(f)
        for m in re.finditer(r'\{\{\s*"(/articles/[^"]+/)"\s*\|\s*relative_url\s*\}\}', content):
            checked += 1
            link = m.group(1)
            if link not in permalinks:
                bad.append(f"{f.name} -> {link}")
    if bad:
        for b in bad:
            fail("internal-links", f"{b} (no matching permalink)")
    else:
        ok("internal-links", f"{checked} links, {len(permalinks)} known permalinks")


def check_amazon_cta_url_template():
    """amazon-cta.html must build the URL with exactly one tag= param and no UTM keys."""
    f = ROOT / "_includes" / "amazon-cta.html"
    if not f.exists():
        warn("amazon-cta-url", "_includes/amazon-cta.html not found")
        return
    content = read(f)
    href_m = re.search(r'href="([^"]+)"', content)
    if not href_m:
        fail("amazon-cta-url", "href属性が見つかりません")
        return
    href_template = href_m.group(1)
    if href_template.count("tag=") != 1:
        fail("amazon-cta-url", f"tag= の出現回数が1でない: {href_template}")
    else:
        ok("amazon-cta-url tag= count", "1")
    forbidden = ["utm_source", "utm_medium", "utm_campaign", "utm_"]
    hits = [k for k in forbidden if k in href_template]
    if hits:
        fail("amazon-cta-utm", f"禁止パラメータを検出: {hits}")
    else:
        ok("amazon-cta-utm", "none found")
    if 'rel="nofollow sponsored noopener"' not in content:
        fail("amazon-cta-rel", 'rel="nofollow sponsored noopener" が見つかりません')
    else:
        ok("amazon-cta-rel")
    if 'target="_blank"' not in content:
        fail("amazon-cta-target", 'target="_blank" が見つかりません')
    else:
        ok("amazon-cta-target")
    required_attrs = ["data-affiliate-product", "data-affiliate-position", "data-affiliate-article", "data-affiliate-active"]
    missing_attrs = [a for a in required_attrs if a not in content]
    if missing_attrs:
        fail("amazon-cta-data-attrs", f"見つからない属性: {missing_attrs}")
    else:
        ok("amazon-cta-data-attrs", "all present")


def check_disclosure_gating():
    """affiliate-disclosure.html must not render when associate_tag is empty."""
    f = ROOT / "_includes" / "affiliate-disclosure.html"
    if not f.exists():
        warn("disclosure-gating", "_includes/affiliate-disclosure.html not found")
        return
    content = read(f)
    if 'site.amazon.associate_tag' in content and re.search(r'\{%-?\s*if\s+tag\s*!=\s*""', content):
        ok("disclosure-gating", "tag未設定時は非表示になる条件分岐あり")
    else:
        fail("disclosure-gating", "associate_tag空時のガード条件が見つかりません")


def check_no_price_display():
    """Articles with affiliate_products must not show a hardcoded currency price near CTAs."""
    window = 3  # lines of surrounding body text to check, not just the include line itself
    for f in (ROOT / "_articles").glob("*.md"):
        content = read(f)
        if "affiliate_products:" not in content:
            continue
        lines = content.splitlines()
        cta_idxs = [i for i, l in enumerate(lines) if "amazon-cta.html" in l]
        for idx in cta_idxs:
            lo, hi = max(0, idx - window), min(len(lines), idx + window + 1)
            for line in lines[lo:hi]:
                if re.search(r"[0-9][0-9,]*\s*円", line):
                    fail("no-price-display", f"{f.name}: CTA近傍に価格らしき表記: {line.strip()}")
    ok("no-price-display (CTA lines +/-3)")


def check_static_assets_exist():
    """CSS/JS files referenced from layouts/includes must exist on disk (no broken refs)."""
    checks = [
        (ROOT / "_layouts" / "default.html", "/assets/css/style.css", ROOT / "assets" / "css" / "style.css"),
        (ROOT / "_includes" / "ga4.html", "/assets/js/affiliate-tracking.js", ROOT / "assets" / "js" / "affiliate-tracking.js"),
    ]
    bad = []
    for referring_file, ref_path, disk_path in checks:
        if not referring_file.exists():
            bad.append(f"{referring_file.relative_to(ROOT)} not found")
            continue
        content = read(referring_file)
        if ref_path not in content:
            bad.append(f"{referring_file.relative_to(ROOT)} does not reference {ref_path}")
        if not disk_path.exists():
            bad.append(f"{ref_path} referenced but missing on disk ({disk_path.relative_to(ROOT)})")
    if bad:
        for b in bad:
            fail("static-assets-exist", b)
    else:
        ok("static-assets-exist", f"{len(checks)} references checked")


def check_no_duplicate_includes():
    """_layouts/default.html must not include the same partial/stylesheet more than once."""
    f = ROOT / "_layouts" / "default.html"
    if not f.exists():
        warn("no-duplicate-includes", "_layouts/default.html not found")
        return
    content = read(f)
    dupes = []
    for needle, label in [
        ('href="{{ "/assets/css/style.css"', "style.css link"),
        ("{% include ga4.html %}", "ga4.html include"),
        ('{% seo %}', "seo tag"),
    ]:
        count = content.count(needle)
        if count > 1:
            dupes.append(f"{label} appears {count} times")
    if dupes:
        for d in dupes:
            fail("no-duplicate-includes", d)
    else:
        ok("no-duplicate-includes")


def check_ga4_gating():
    """ga4.html must gate all output behind an empty-measurement-id check."""
    f = ROOT / "_includes" / "ga4.html"
    if not f.exists():
        warn("ga4-gating", "_includes/ga4.html not found")
        return
    content = read(f)
    if re.search(r'\{%-?\s*if\s+ga_id\s*!=\s*""', content) and "jekyll.environment" in content:
        ok("ga4-gating", "ga_id空 または non-production の間は出力されないガードあり")
    else:
        fail("ga4-gating", "ga_id空/非production時のガード条件が見つかりません")


def check_image_dimensions_declared():
    """Every markdown image in _articles/ should have a following kramdown IAL with width/height."""
    missing = []
    checked = 0
    for f in (ROOT / "_articles").glob("*.md"):
        lines = read(f).splitlines()
        for i, line in enumerate(lines):
            if line.startswith("!["):
                checked += 1
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if not re.match(r'\{:.*width="\d+".*height="\d+".*\}', nxt):
                    missing.append(f"{f.name} line {i + 1}: {line[:60]}...")
    if missing:
        for m in missing:
            fail("image-dimensions-declared", m)
    else:
        ok("image-dimensions-declared", f"{checked} images")


def check_order_values():
    """_articles/*.md must all have a non-empty integer `order:` value.

    index.md and articles/index.md both do `site.articles | sort: "order"`,
    and Jekyll/Liquid's sort treats a missing/nil order as sorting first —
    so a promoted article with a blank `order:` (e.g. a Dev Log draft moved
    to _articles/ without filling this in) could silently become the site's
    single "featured" article on the homepage (`| first`), displacing the
    intended curated article. This check catches that before it ships.
    """
    articles_dir = ROOT / "_articles"
    files = sorted(articles_dir.glob("*.md")) if articles_dir.exists() else []
    bad = []
    for f in files:
        content = read(f)
        fm, _ = split_frontmatter(content)
        if fm is None:
            bad.append(f"{f.name}: no frontmatter block found")
            continue
        m = re.search(r"^order:\s*(\S*)\s*$", fm, re.MULTILINE)
        if not m or not m.group(1) or not re.match(r"^-?\d+$", m.group(1)):
            bad.append(f"{f.name}: order is missing or not an integer")
    if bad:
        fail("order-values", "; ".join(bad))
    else:
        ok("order-values", f"{len(files)} files")


def check_drafts_excluded():
    """`drafts/` must be in _config.yml's Jekyll `exclude:` list.

    drafts/ is documented (docs/README.md, docs/devlog-policy.md) as a safe
    holding area for non-ready content, on the assumption that Jekyll never
    builds it. That assumption was silently false for a period (the
    `- drafts/` exclude line existed only in an uncommitted local change),
    which went unnoticed only because drafts/ was empty — the first real
    file placed there was built and published live before anyone noticed.
    This check makes that specific class of regression fail CI instead.
    """
    config_path = ROOT / "_config.yml"
    if not config_path.exists():
        fail("drafts-excluded", "_config.yml が見つかりません")
        return
    content = read(config_path)
    if re.search(r"^\s*-\s*drafts/\s*$", content, re.MULTILINE):
        ok("drafts-excluded")
    else:
        fail("drafts-excluded", "_config.yml の exclude: に `- drafts/` がありません(drafts/ が公開されるリスク)")


def check_git_diff():
    result = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        fail("git diff --check", result.stdout + result.stderr)
    else:
        ok("git diff --check")


def main():
    print("=== AI-Tech-Lab site validation ===\n")
    check_ready_status()
    check_order_values()
    check_drafts_excluded()
    check_frontmatter_yaml()
    check_liquid_balance()
    check_images_exist_and_have_alt()
    check_internal_links()
    check_amazon_cta_url_template()
    check_disclosure_gating()
    check_no_price_display()
    check_static_assets_exist()
    check_no_duplicate_includes()
    check_ga4_gating()
    check_image_dimensions_declared()
    check_git_diff()

    print("\n=== Summary ===")
    if WARNINGS:
        print(f"{len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(" ", w)
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(" ", f)
        sys.exit(1)
    print("All checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
