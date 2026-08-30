---
name: parallel-worktree-development
description: >
  独立したTaskが2個以上あり、依存が薄い変更群をGit Worktree + subagentで安全に並列実装したいときに
  使う。Task分解・依存分析・Worktree/Branch作成・並列実装Agentへの割当・マージ順序の調整を担当する。
  実装品質・テスト・レビューはquality-development / independent-reviewerが担当するため、このSkillは
  それらを代替しない。単一Taskしかない場合、または記事執筆(インタビューが本質的に直列)には使わない。
---

# parallel-worktree-development

独立Taskを安全に並列実装するためのオーケストレーション。**並列化そのものが目的ではない**。
independence(独立性)・conflict risk(衝突リスク)・verification cost(検証コスト)・
review cost(レビューコスト)を優先し、常時並列は採用しない。標準は2〜4並列。

## このリポジトリ固有の制約

AI-Tech-Labは単独オーナーの技術メディアであり、多くの「Task」はソフトウェア機能ではなく記事執筆・
サイト改善である。並列化を検討する前に以下を確認する。

- **記事執筆そのものは基本的に並列化しない**。[CLAUDE.md](../../../CLAUDE.md)の「最重要ルール」
  により記事化にはオーナーへのインタビューが必須で、これは本質的に直列的なボトルネックになる
  (同時に2つのインタビューを効率的に進めることはできない)。また複数記事が公開順・内部リンクで
  相互依存しやすい(`CONTENT_PLAN.md`の内部リンククラスター方針を参照)。
- 並列化が有効なのは主に: 独立したスクリプト/ツール(`scripts/`配下)、独立したドキュメント作成、
  相互リンクが未確定な複数の記事下書きの「執筆以外」の作業(画像設計・技術チェックなど)、独立した
  サイト機能の実装。
- `_articles/`のstatus変更、GitHub Pages/Jekyll設定変更(`_config.yml`、
  `.github/workflows/pages.yml`、`_layouts/`)、`CLAUDE.md`変更は、常にオーナー承認が必要な変更
  であり並列worktreeでの自動実行対象にしない。

## Parallelization Gate

Taskごとに以下のいずれかへ分類してから並列化を判断する。

### PARALLEL_SAFE

独立している。別worktreeで並列実行してよい。

- 独立したスクリプト/ツール(例: 画像処理スクリプトとvalidateスクリプトの改善)
- 独立したドキュメント作成
- 相互リンクが未確定な記事下書きの、本文執筆以外の作業(画像ブリーフ作成、技術情報の裏取りなど)
- 既存記事に影響しない独立したサイト機能追加

### PARALLEL_CAUTION

共有部分が一部存在する。依存とマージ順序を明示すれば並列可能。

- 複数記事が相互リンクする場合(片方の完成が他方の内部リンクを左右する)
- `_config.yml`、`_includes/amazon-cta.html`など複数記事/ページから参照される共有ファイル
- `docs/TODO.md`(複数Taskが同時に更新すると競合しやすい。State Updateのタイミングを揃える)
- `assets/js/affiliate-tracking.js`など複数記事のCTAが依存する共通スクリプト

### SERIAL_REQUIRED

依存が強い。直列実行する。

- インタビュー必須の記事執筆そのもの
- `_articles/`のstatus変更・記事公開(オーナー承認事項)
- CLAUDE.md変更、GitHub Pages/Jekyll設定変更
- 同一の大きなファイルを複数Taskが編集する場合
- Task BがTask Aの成果(内部リンク先の実URLなど)を必要とする場合

## 1 Task = 1 Worktree

並列実行するTaskについて、`1 task = 1 branch = 1 worktree = 1 implementation agent`を基本とする。
ただし小さいTaskや強依存Taskを無理に分割しない。

## 進め方

1. `docs/TODO.md`にある(または今回追加する)Taskを確認し、上記Gateで分類する
2. PARALLEL_SAFE/PARALLEL_CAUTIONのTaskについてWorktree/Branchを作成する
3. 各Implementation Agentへ、以下の標準入力のみを渡す(リポジトリ全体を無条件に渡さない):

   ```
   Task:
   Objective:
   Scope:
   Out of Scope:
   Dependencies:
   Relevant Knowledge:      # knowledge/配下で関係するファイルがあれば
   Allowed Files:
   Protected Files:         # CLAUDE.md, docs/TODO.md, _config.yml 等、Taskの対象外なら明記
   Acceptance Criteria:
   Verification Commands:
   Stop Conditions:         # .claude/skills/quality-development/references/stop-conditions.md を参照
   ```

4. 各Implementation Agentの成果物に対し、`quality-development` Skillの通常フロー
   (Self Evaluation → Independent Review)を適用する。このSkillは実装品質を判定しない
5. 全Taskの結果を収集し、Integration Verification(下記)を行う
6. マージ順序はPARALLEL_CAUTIONで明示した依存に従う
7. `docs/TODO.md`をState Updateする(Task IDがあれば付記)。知識化基準を満たすものは
   `knowledge-management` Skillの基準で`knowledge/`へ還流する

## Integration Gate

個別TaskがPASSしても即DONEにしない。統合状態で以下を確認する。

- 複数Task間のinterface整合(内部リンク・共有include・共有スクリプト)
- 依存順どおりにマージされているか
- リグレッション(既存記事・既存機能への影響)
- 利用可能な自動チェックの再実行(例: `.claude/hooks/check-article-status.js`相当の確認、
  存在すれば`scripts/validate-site.py`)

## Git安全性

[`.claude/settings.json`](../../settings.json)の既存設定(force push禁止、`reset --hard`禁止、
`clean -f`系禁止)をそのまま踏襲する。加えて:

- 他worktreeの未マージ変更を無断で削除・上書きしない
- 使われなくなったworktreeを削除する前に、マージ済みか・価値のある未コミット変更が残っていないかを
  確認する
- 未知のbranch/worktreeを見つけた場合は先に調査し、憶測で削除しない

## quality-developmentとの関係

このSkillはtask decomposition・dependency分析・worktree/branch作成・並列実行・マージ順序の調整
のみを担当する。実装品質・テスト・lint・セキュリティ・リグレッション確認・完了判定は
[`quality-development`](../quality-development/SKILL.md)と`independent-reviewer` agentが担当し、
このSkillはそれらを代替・重複しない。並列worktree内での実装であっても、各Taskは通常どおり
quality-developmentのフロー(Plan First〜State Update)に従う。

## 発火条件

- 独立Taskが2個以上ある
- 複数の独立した機能・改善をまとめて依頼された
- Task間の依存が薄い

単一Taskしかない場合、Taskの大半がSERIAL_REQUIRED(特に記事執筆そのもの)の場合は、このSkillを
使わず通常どおり直列で進める。
