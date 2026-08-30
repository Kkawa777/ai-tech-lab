"""Deterministic English -> Japanese term mapping for titles/descriptions.

No LLM call, no free-text translation model: this is a fixed lookup table
plus a small set of mechanical rules (strip stopwords, reorder VERB OBJECT
-> OBJECTを VERB). It is meant to remove Phase 1's "raw English commit
subject in a Japanese sentence" problem for the vocabulary that actually
appears in this repo's commit history, while staying auditable and
impossible to hallucinate with — an unmapped word is left verbatim (safe
degrade), never guessed at.

`coverage_ratio()` reports what fraction of the meaningful tokens were
found in the dictionary, so score.py's SEO-potential axis can reward a
well-translated title over a mostly-untranslated one, and callers can
choose to fall back to the Phase 1 verbatim-English style when coverage is
too low to produce something readable.
"""
import re

# Checked BEFORE single-token lookup, longest first, case-insensitive,
# against the whole cleaned subject. This is where repo-specific /
# domain-specific vocabulary lives (the single-token dictionary below is
# the generic fallback for anything not covered here).
MULTI_WORD_OVERRIDES = [
    ("load cell", "ロードセル"),
    ("rain sensor", "雨センサー"),
    ("water sensor", "水検知センサー"),
    ("delivery detection", "配達物検知"),
    ("delivery monitoring", "配達物監視"),
    ("starter kit", "スターターキット"),
    ("affiliate link", "アフィリエイトリンク"),
    ("affiliate products", "アフィリエイト商品"),
    ("quality workflow", "品質ワークフロー"),
    ("analytics foundation", "分析基盤"),
]

STOPWORDS = {"to", "for", "in", "with", "from", "of", "the", "a", "an", "on", "and"}

# Verbs get a polite past-tense Japanese suffix so a title reads as an
# action taken, matching this site's existing article title tone.
VERB_MAP = {
    "add": "追加しました", "added": "追加しました", "adds": "追加しました",
    "remove": "削除しました", "removed": "削除しました",
    "fix": "修正しました", "fixed": "修正しました",
    "update": "更新しました", "updated": "更新しました",
    "improve": "改善しました", "improved": "改善しました",
    "implement": "実装しました", "implemented": "実装しました",
    "introduce": "導入しました",
    "support": "対応しました",
    "publish": "公開しました", "published": "公開しました",
    "refactor": "リファクタリングしました",
    "optimize": "最適化しました", "optimise": "最適化しました",
    "launch": "開始しました",
    "strengthen": "強化しました",
    "establish": "整備しました",
    "configure": "設定しました",
}

# Generic single-token fallback dictionary. Unmapped tokens are left
# verbatim (usually fine for product/model names like ESP32, ROI, CSS).
JA_TERM_MAP = {
    "article": "記事", "articles": "記事", "post": "記事", "blog": "ブログ",
    "sensor": "センサー", "detection": "検知", "monitoring": "監視",
    "rain": "雨", "water": "水", "delivery": "配達物",
    "affiliate": "アフィリエイト", "product": "商品", "products": "商品",
    "link": "リンク", "links": "リンク",
    "image": "画像", "images": "画像", "photo": "写真",
    "guide": "ガイド", "kit": "キット",
    "test": "テスト", "tests": "テスト", "testing": "テスト",
    "feature": "機能", "features": "機能",
    "bug": "不具合", "error": "エラー", "issue": "問題",
    "performance": "パフォーマンス", "speed": "速度", "cache": "キャッシュ",
    "config": "設定", "configuration": "設定", "setting": "設定", "settings": "設定",
    "script": "スクリプト", "tool": "ツール", "tools": "ツール",
    "automation": "自動化", "automatic": "自動",
    "workflow": "ワークフロー", "pipeline": "パイプライン",
    "validate": "検証", "validation": "検証", "check": "チェック",
    "review": "レビュー", "quality": "品質",
    "build": "ビルド", "deploy": "デプロイ", "deployment": "デプロイ",
    "style": "スタイル", "layout": "レイアウト", "design": "デザイン",
    "ui": "UI", "ux": "UX", "api": "API", "database": "データベース",
    "seo": "SEO", "analytics": "分析", "monetization": "収益化",
    "section": "セクション", "page": "ページ", "site": "サイト",
    "module": "モジュール", "component": "コンポーネント",
    "function": "関数", "functions": "関数", "class": "クラス",
    "log": "ログ", "logging": "ログ",
    "install": "インストール", "installation": "インストール",
    "documentation": "ドキュメント", "docs": "ドキュメント", "doc": "ドキュメント",
    "structure": "構造", "template": "テンプレート", "templates": "テンプレート",
}


def _apply_multi_word_overrides(subject_lower):
    remaining = subject_lower
    translated_fragments = []
    for phrase, ja in MULTI_WORD_OVERRIDES:
        if phrase in remaining:
            remaining = remaining.replace(phrase, f" __ja_{len(translated_fragments)}__ ")
            translated_fragments.append(ja)
    return remaining, translated_fragments


def translate_subject(cleaned_subject):
    """Returns (japanese_ish_title_fragment, coverage_ratio).

    coverage_ratio in [0, 1]: fraction of tokens that were either mapped
    via the dictionary or matched a multi-word override. A low ratio means
    "mostly untranslated" — callers should treat that as a signal to fall
    back to a more conservative rendering rather than trust this output.
    """
    lowered = cleaned_subject.lower()
    remaining, ja_fragments = _apply_multi_word_overrides(lowered)

    raw_tokens = re.findall(r"[a-z0-9]+|__ja_\d+__", remaining)
    tokens = [t for t in raw_tokens if t not in STOPWORDS]
    if not tokens:
        return cleaned_subject, 0.0

    verb = None
    if tokens[0] in VERB_MAP:
        verb = VERB_MAP[tokens[0]]
        tokens = tokens[1:]

    mapped_count = 0
    object_parts = []
    for tok in tokens:
        m = re.match(r"__ja_(\d+)__", tok)
        if m:
            object_parts.append(ja_fragments[int(m.group(1))])
            mapped_count += 1
        elif tok in JA_TERM_MAP:
            object_parts.append(JA_TERM_MAP[tok])
            mapped_count += 1
        elif tok.isdigit() or re.match(r"^[a-z]+\d+$|^\d+[a-z]+$", tok):
            object_parts.append(tok.upper())  # model numbers like esp32 -> ESP32, kept verbatim
        else:
            object_parts.append(tok)

    coverage = mapped_count / len(tokens) if tokens else 0.0
    object_phrase = "".join(object_parts)

    if verb:
        return f"{object_phrase}を{verb}", coverage
    return object_phrase, coverage


def coverage_is_usable(coverage_ratio, min_tokens=1):
    """Below this coverage, a translated phrase tends to read as a
    disjointed word-salad rather than a sentence — better to fall back to
    the Phase 1 verbatim-English style (still factual, just less natural)
    than to publish something that looks broken."""
    return coverage_ratio >= 0.34
