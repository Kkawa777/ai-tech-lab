---
name: article-filename-vs-catalog-number
description: 記事ファイル名の連番とCONTENT_PLAN.mdのカタログ番号は別の名前空間であるという決定
metadata:
  type: decision
---

# 記事ファイル名の連番とCONTENT_PLAN番号を分離する

## Summary

`_articles/`のファイル名`0N-slug.md`の連番と、`CONTENT_PLAN.md`のカタログ番号(記事#5など)は、
偶然一致していただけで本来は別の名前空間である。第5号(配達物検知)で両者が衝突したため、
ファイル名から数字プレフィックスを落として回避した。

## Why it matters

01〜04号ではファイル名連番=CONTENT_PLAN番号に見えていたため、この2つが同じ意味だと誤解しやすい。
今後もカテゴリを跨ぐ記事(実践プロジェクト作品集など)が増えると同じ衝突が再発しうる。

## Details

- 公開順の正本は`order:` frontmatter
- ファイル名は原則slugのみ(数字プレフィックスなし)に統一する運用への変更が提案されている
  (既存の01〜04は大規模renumberを避けるためそのまま維持)
- 実例: `esp32-loadcell-delivery-detection.md`(`05-`プレフィックスを落とした)

## Related decisions

- [drafts-directory-separation](drafts-directory-separation.md)

## Related projects

- [CONTENT_PLAN.md](../../CONTENT_PLAN.md)

## Source

`docs/TODO.md`「Owner Action Required」#3(2026年8月時点、未確定の提案として記録)

## Last updated

2026-08-24
