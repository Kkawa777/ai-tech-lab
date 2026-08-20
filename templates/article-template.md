---
title:
status: idea # idea / interview / draft / testing / review / ready
category:
difficulty: # 初級 / 中級 / 上級
estimated_time:
description: # 70〜120字程度。meta description / OGP descriptionに使用。未設定時はsite.descriptionにフォールバック
image: # アイキャッチ画像(未設定時はOGP画像なしでビルド可能)
  path: # 例: /assets/images/articles/<article-slug>/eyecatch.webp
  alt: # 画像の内容を簡潔に説明する日本語
tested_hardware:
tested_software:
amazon_products: # 自由記述の要約(何をどう紹介したか等の注記)。CTA表示には使われない。CTA用の
# 構造化データは下のaffiliate_productsを使う(名前が似ているが役割が異なるので注意)
# 収益化メタデータ(すべて任意。未設定でも既存記事の挙動に影響しない)
content_type: # informational / commercial / transactional
primary_keyword: # 主要検索キーワード1つ
search_intent: # 検索意図。descriptionと内容が重複してよい
monetization: # none / amazon_affiliate
conversion_goal: # 例: amazon_cta_click
affiliate_products: # 商品メタデータ台帳(任意)。実際のCTA表示は本文の{% include amazon-cta.html %}で行う
# - asin:
#   role: # used(実際に使用) / candidate(未使用・公開情報に基づく候補)
#   label:
---

## この記事でわかること

<!-- 読了後に読者が得られる知識・成果を箇条書きで -->

## この記事はこんな人におすすめ

<!-- 対象読者のレベル・状況を具体的に -->

## 作ろうと思った理由

<!-- インタビュー: なぜ作ろうと思ったか / どんな問題を解決したかったか -->

## 実際に困ったこと

<!-- インタビュー: 制作中に直面した具体的な問題 -->

## 使用した部品

<!-- 実際に使用した部品名・型番。おすすめ/おすすめしない部品があれば理由も記載 -->

## 配線図

<!-- 配線図・回路図。5V系/3.3V系の混在がある場合は安全性の注意点を明記 -->

## サンプルコード

<!-- 処理内容がわかるコメント付き。使用ライブラリ・対応ボード・必要バージョンを明記
     未実機検証の場合は「未実機検証」と明記 -->

## 動作確認

<!-- 実際に動かした結果。未確認の場合は「未確認」「要検証」と明記 -->

## 失敗したこと

<!-- インタビュー: 失敗したこと -->

## 改善したこと

<!-- インタビュー: 改善したこと -->

## 今ならこう作る

<!-- インタビュー: 今ならどう作るか -->

## Amazonで紹介する商品

<!-- 読者の課題解決に必要な場合のみ。実際に使用したものを優先し、選定理由を記載。
     CTAボタンは {% include amazon-cta.html asin="..." label="..." position="..." article="..." used=true|false %}
     を使う(直接<a>タグやアフィリエイトURLを本文へ書かない)。未使用商品は used=false を指定する -->

## よくある質問

## まとめ
