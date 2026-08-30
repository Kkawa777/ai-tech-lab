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
    # Added for Phase 2.5 (docs/devlog-policy.md Step 5): frequent verbs
    # observed in this repo's own commit history that were previously
    # unmapped, falling straight through to the Phase 1 verbatim fallback.
    "prevent": "防止しました", "validate": "検証しました", "detect": "検知しました",
    "generate": "生成しました", "compare": "比較しました", "select": "選択しました",
    "retry": "再試行しました", "isolate": "分離しました", "promote": "昇格しました",
    "exclude": "除外しました", "resolve": "解決しました",
    "enable": "有効化しました", "disable": "無効化しました",
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
    # Added for Phase 2.5: recurring nouns from this repo's own Dev Log
    # development (a legitimately recurring topic for this project, not
    # arbitrary padding — see docs/devlog-policy.md Step 5's category list).
    "validation": "検証", "pipeline": "パイプライン", "draft": "ドラフト",
    "comparison": "比較", "gate": "ゲート", "score": "スコア",
    "promotion": "昇格", "hash": "ハッシュ", "fingerprint": "フィンガープリント",
    "reviewer": "レビュー", "evidence": "根拠", "summary": "サマリー",
    "safety": "安全性", "runner": "ランナー", "daily": "日次",
    "roi": "ROI", "poc": "PoC", "git": "Git", "history": "履歴",
    "presentation": "プレゼンテーション", "version": "バージョン",
}


def _apply_multi_word_overrides(subject_lower):
    remaining = subject_lower
    translated_fragments = []
    for phrase, ja in MULTI_WORD_OVERRIDES:
        if phrase in remaining:
            remaining = remaining.replace(phrase, f" __ja_{len(translated_fragments)}__ ")
            translated_fragments.append(ja)
    return remaining, translated_fragments


# A Japanese compound noun chain reads naturally for roughly 2-4 concepts
# (e.g. "収益化分析基盤" = monetization + analytics + foundation). Beyond
# that, concatenating more mapped words does NOT compose into a readable
# phrase — it produces a run-on word-salad even at 100% dictionary
# coverage (Phase 2.5 finding: "add Dev Log automation PoC (Git history ->
# article draft)" has 8 meaningful tokens and produced
# "devログ自動化pocgithistory記事draft", which is unreadable regardless of
# how much the dictionary is expanded). So token-count is capped
# independently of coverage, not just used as a fallback signal.
MAX_TRANSLATABLE_TOKENS = 5


def translate_subject(cleaned_subject):
    """Returns (japanese_ish_title_fragment, coverage_ratio, token_count).

    coverage_ratio in [0, 1]: fraction of tokens that were either mapped
    via the dictionary or matched a multi-word override. token_count is
    the number of meaningful tokens (verb + stopwords already excluded)
    the object phrase was built from. Both are needed by
    coverage_is_usable() — a low ratio OR too many tokens are each
    independently a sign this output shouldn't be trusted as-is.
    """
    lowered = cleaned_subject.lower()
    remaining, ja_fragments = _apply_multi_word_overrides(lowered)

    raw_tokens = re.findall(r"[a-z0-9]+|__ja_\d+__", remaining)
    tokens = [t for t in raw_tokens if t not in STOPWORDS]
    if not tokens:
        return cleaned_subject, 0.0, 0

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
        return f"{object_phrase}を{verb}", coverage, len(tokens)
    return object_phrase, coverage, len(tokens)


def coverage_is_usable(coverage_ratio, token_count=0):
    """Below this coverage, or beyond MAX_TRANSLATABLE_TOKENS concepts, a
    translated phrase tends to read as a disjointed word-salad rather than
    a sentence — better to fall back to the Phase 1 verbatim-English style
    (still factual, just less natural) than to publish something that
    looks broken. Raised from 0.34 to 0.6 in Phase 2.5 after finding 0.34
    let through partially-translated phrases that still read as broken
    (e.g. "0ESP32cam記事を追加しました" at ~0.5 coverage was borderline
    acceptable, but lower ratios were not)."""
    return coverage_ratio >= 0.6 and token_count <= MAX_TRANSLATABLE_TOKENS
