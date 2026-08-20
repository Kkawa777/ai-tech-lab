# TODO.md

現在の開発状態のみを保持する。作業ログではなく、更新のたびにこの内容を上書きする。
背景・原則・優先順位は正本(ROADMAP.md / BRAND.md / CONTENT_PLAN.md / docs/PROJECT_PRINCIPLES.md)を
参照する。ここに新しい方針や原則を書かない。

開発Agentは独自のPlan/TODOファイルを作らず、状態はこのファイルに集約する。手順は
[`.claude/skills/quality-development/SKILL.md`](../.claude/skills/quality-development/SKILL.md)
のState Updateステップを参照。**履歴ファイルにしない**: 完了項目は直近1〜2 Batchのみ、
Blockedは現在有効なものだけを残す。それより古い完了履歴はGit historyに委ね、ここでは削除する。

## In Flight

(現在実行中のTaskなし)

## Completed

- 収益化Sprint(Amazon Affiliate CTA/Disclosure、GA4、`amazon_click`計測、Search Console
  verification、`privacy.md`、画像CLS/LCP対応、`scripts/validate-site.py`)。independent-reviewer
  を4サイクル実施しBLOCKER/MAJOR 0を達成後、commit `8650da5`(`feat: launch monetization and
  analytics foundation`)としてpush・GitHub Actions build/deploy・公開後validation(HTTP/OGP/
  JSON-LD/GA4/Amazon CTA/キャッシュヘッダ実測)まで完了。公開URL:
  https://kkawa777.github.io/ai-tech-lab/ 。詳細な経緯はGit history側に委ね、ここには再掲しない
- quality-development開発プロセスBatch(Task Decomposition/Automated Validation/Independent
  Review/State Update等の品質基盤)、および本ファイルとの責務整合の見直し(`SKILL.md`・
  `docs/README.md`の`docs/TODO.md`セクション名の記述をIn Flight/Completed/Owner Action
  Required/Blocked/Next Upの実運用に合わせて統一、本ファイルの陳腐化した完了履歴を圧縮)

## Blocked

(現在有効なBlocked項目なし)

## Owner Action Required

1. Amazon.co.jpアソシエイト規約について、英語表記のみで日本向けサイトとして十分かは規約に明記が
   なく確認できなかった点の最終確認(現状は日本語必須文言+英語補足で対応済み、追加対応の要否は任意)
2. CONTENT_PLAN.mdへ新規提案した2記事(重量センサー配達物検知/水検知センサー雨検知)を正式な記事番号
   として追加するかの判断
3. 第4号(Lチカ)記事のインタビュー実施。既存記事(#1〜#3)からHello World→Lチカの流れ・使用ボード
   (Arduino Uno)は確認済みのため再質問しない。以下7問で、CLAUDE.md「## 最重要ルール」が求める
   必須項目(なぜ作ろうと思ったか/どんな問題を解決したかったか/失敗したこと/改善したこと/
   今ならどう作るか/実際に使用した部品/おすすめ部品/おすすめしない部品)をすべて統合済み
   (不明な項目は「覚えていない」で記事化可能な構成にする):
   1. Hello Worldの次にLチカへ進んだ理由と、当時解決したかったこと(参考にしたチュートリアル等が
      あれば)
   2. 使用したLEDと抵抗値(色・個数、キット付属か別途購入か、何Ω、覚えている範囲で)。あわせて、
      今ならどのLED・抵抗値をおすすめするか、逆におすすめしない部品があれば
   3. 配線(どのピンに接続したか、ブレッドボードの使い方)
   4. 使用したコード(Arduino IDEのBlinkサンプルをそのまま使ったか、delay等を変更したか)
   5. Lチカ特有の失敗・つまずき(光らなかった、極性ミス、抵抗忘れ等)。あれば、どう気づいて
      解決・改善したか(なければ「特になし」)
   6. LEDが光った瞬間の感想
   7. 今このLチカを初心者に説明するなら、当時分からなかったことも含めてどう説明するか。また、
      今この記事をもう一度作るとしたらどう作るか
4. `privacy.md`の「運営者・お問い合わせ」章はGitHub Issuesリンクで暫定対応した。専用の問い合わせ
   手段(メールアドレス等)を今後用意する場合は、この章の更新を検討
5. `MEASUREMENT REQUIRED`: commit `8650da5`の公開後データ(Search Console/GA4/Core Web Vitals)は
   まだ十分な期間が経過しておらず未計測。データ蓄積後に判断する(推測での最適化は行わない)

## Next Up

- 第4号(Lチカ)記事: インタビュー回答後にdraft作成
- 10記事戦略の確定(このセッションで整理予定)
