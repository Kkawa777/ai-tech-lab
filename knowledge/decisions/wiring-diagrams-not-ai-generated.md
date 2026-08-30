---
name: wiring-diagrams-not-ai-generated
description: 電気配線図は画像生成AIで作らず、Fritzing等の正確なツールで別途作成する方針
metadata:
  type: decision
---

# 配線図はAI生成せず、Fritzing等で別途作成する

## Summary

画像生成AIはブレッドボードの穴位置・Arduino/ESP32のピン位置を電気的に正確に再現できないため、
電気配線図(wiring diagram)は生成AIで作らない方針とする。Fritzingなど電気的に正確なツールで
別途作成し、届くまでは「未着手」のまま公開してよい(配線図がないことは公開のブロッカーにしない)。

## Why it matters

初心者向け電子工作メディアという性質上、配線図の誤りは電圧・極性・ショートなど安全上の問題に
直結しうる。「それらしく見えるが不正確な図」を出すくらいなら、図なしで公開し後から正確な図を
追加する方が安全という判断。

## Details

- システム構成概念図(論理構成、電気的な正確性を要求しないもの)はAI生成/SVG等で作ってよい
- 電気配線図(breadboard/pin位置が意味を持つもの)のみAI生成を避ける
- 第4号・第5号・第6号(ESP32-CAM)の各記事で同じ理由により配線図が「画像TODO」として残っている

## Related decisions

なし

## Source

`docs/TODO.md`「第4号 画像TODO」「第5号 画像TODO」(2026年8月)

## Last updated

2026-08-24
