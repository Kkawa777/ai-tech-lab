---
name: line-notify-service-sunset
description: LINE Notifyは2025-03-31にサービス終了済み。既存記事・新規記事で「当時」と「現在」を分離する必要がある
metadata:
  type: lesson
---

# LINE Notifyは2025-03-31にサービス終了済み

## Summary

LINE Notifyは2025-03-31にサービス終了している(公式発表で確認済み)。後継はLINE Messaging API。
過去にLINE Notifyを実際に使った記事は、その事実(当時は実際に使用した)と、現在は使えないという
事実を明確に分離して記載する必要がある。

## Why it matters

サービス終了などの外部要因で、実体験の記述がそのままでは現在の読者に誤った情報(今すぐ使える手段
だと誤認させる)を与えてしまう。「実際に使った」ことと「現在も推奨できる」ことは別軸で、記事の
鮮度チェック時に確認すべき典型例。

## Details

- 第5号(配達物検知)記事で、本文中「当時」(実際に使用)と「現在」(後継のMessaging APIを一般情報
  として案内、筆者が使ったとは書かない)を明確に分離する対応を実施済み
- 新規に「ESP32から通知を送る方法」系の記事を書く場合は、Messaging APIを一般解説として設計する
  必要があり、「筆者が実際にMessaging APIを使った」とは書けない(未使用のため)

## Related lessons

なし

## Source

LINE公式発表(2025-03-31サービス終了)。`docs/TODO.md`「Completed」(第5号公開Sprint、2026年8月)

## Last updated

2026-08-24
