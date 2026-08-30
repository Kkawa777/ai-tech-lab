---
name: amazon-affiliate-asin-verification
description: 記憶だけでASIN・使用製品を断定せず、購入履歴等で確認してからCTA実装する運用と、その理由になった訂正事例
metadata:
  type: revenue
---

# ASIN・実使用製品は「記憶」ではなく購入履歴等で確認してから確定する

## Summary

Amazonアフィリエイトの`used=true`(実際に使用した製品としてのCTA)は、オーナーの記憶だけを根拠に
確定しない。ESP32-CAM記事で当初「AI-Thinker ESP32-CAM」と記録していたが、実際にはFreenove ESP32
CAM Dev Board Kit(`B0CJJHXD1W`)だったとAmazon購入履歴で判明し、訂正した事例がある。

## Why it matters

CLAUDE.mdの「事実性・信頼性」ルール(実体験を創作しない、未確認情報を断定しない)は、記事本文だけ
でなくアフィリエイト商品の同定にも同じ基準で適用する必要がある。誤った製品を「実際に使った」として
紹介すると、事実性違反かつ読者に誤った購入判断をさせるリスクになる。

## Details(仮説→実験→結果)

- **仮説**: 記憶に基づく製品名の記載で十分正確だろう
- **実験**: ESP32-CAM記事公開後、Amazon購入履歴等で実際に確認
- **結果**: 記憶違いが判明(AI-Thinker → Freenove)。本文・frontmatterとも訂正、
  「AI-Thinker」への言及は「一般的な代表例」「記憶違いの経緯説明」の2箇所のみに限定し直した
- **結論**: 実使用品としてCTA(`used=true`)を出す前に、購入履歴等の一次情報で確認するプロセスを
  経由する
- **現在の確認状況**(詳細・最新版は`docs/TODO.md`「Affiliate ASIN管理」が正本):
  `B0CJJHXD1W`(Freenove ESP32 CAM)・`B0C9THDPXP`(Freenove ESP32)・`B089LS556S`(ロードセル×4+
  HX711)はオーナー確認済みでCTA実装済み。`B09XMPPZYT`(USBシリアル変換器)は用途未確認のためCTA
  保留

## Related decisions

なし

## Source

`docs/TODO.md`「Affiliate ASIN管理」「Owner Action Required」#8(2026年8月Affiliate展開Sprint)

## Last updated

2026-08-24
