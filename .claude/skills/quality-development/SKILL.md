---
name: quality-development
description: >
  コード実装・記事執筆・設計・ドキュメント作成など、レビューに値する成果物を作る作業で使用する。
  「実装して」「記事を書いて」「修正して」「設計して」のような、何らかの成果物を生む依頼のときに、
  Plan First・Task Decomposition・Self Evaluation・Independent Review・Iterative Refinement・
  State Updateを毎回明示的な指示なしに適用するためのスキル。質問への回答・調査のみ・数行の自明な
  修正には使わない。
---

# quality-development

成果物の質を、作った本人の自己評価だけに頼らず担保するための品質管理フロー。
判断基準の詳細(重大判断リスト・リスク分類・終了条件・重大度定義)は `references/stop-conditions.md`
を正本とし、このファイルには重複記載しない。

処理フロー全体:

```
Step 0 適用判定
  → Step 1 Plan First
  → Step 2 Task Decomposition
  → Step 3 実装・執筆
  → Step 4 Automated Validation (EXECUTE_RESULT)
  → Step 5 Self Evaluation
  → Step 6 Independent Review (CHECK_RESULT)
  → Step 7 Iterative Refinement判定
  → Step 8 Final Validation
  → Step 9 State Update + Reusable Pattern Check
  → Step 10 完了報告
```

工程間(Research / Architect / Developer / independent-reviewer / Lead)の作業引き継ぎには
`references/handoff-format.md` の構造化HANDOFFを使う。

## Step 0: 適用判定

`references/stop-conditions.md` の「4. 適用対象外」に該当する作業(質問応答・調査のみ・数行の自明な
修正)は、このフローを発動せず通常どおり作業する。

記事執筆・コード実装/修正・設計・ドキュメント作成など、レビューや検証に値する成果物を生む作業のみ、
Step 1以降を適用する。調査が広範囲に及ぶ場合はExploreサブエージェントへ委譲し、Main Contextを大きな
調査結果で圧迫しない(詳細は「Prompt Cache / Context Efficiency」参照)。

## Step 1: Plan First

作業に着手する前に、計画・影響範囲・完了条件・検証方法を整理する。ユーザーへの提示は必須ではなく、
通常はそのまま作業を進めてよい(既存のEnterPlanMode運用と競合しない)。

変更を `references/stop-conditions.md` の「5. リスクベースの品質ゲート」に沿って LOW / MEDIUM / HIGH
に分類する。HIGH(=「1. 重大判断リスト」に該当)の場合のみ、`AskUserQuestion` または `EnterPlanMode`
でオーナーに確認し、承認を得るまで進めない。LOW/MEDIUMは確認なしで進める。

## Step 2: Task Decomposition

大きな要求をそのまま一度に実装しない。`Requirement → Plan → Task decomposition` の順で、1 Taskが
「目的が一つ・完了条件が明確・関連する検証が実行可能・独立レビュー可能」な大きさになるよう分割する。
細かくしすぎて管理コストを増やさない。関連する2〜3 Task程度を1つの開発Batchとして扱う。
LOWリスク(`stop-conditions.md`参照)の変更は単一Taskのまま省略してよい。

## Step 3: 実装・執筆

通常どおり作業する。UI/UXを伴う実装は、発火条件・優先順位を含めCLAUDE.mdの「UI/UX Specialist」を
正本として`ui-ux-pro-max` Skillを併用する。既存UI/Design Systemとの一貫性を`ui-ux-pro-max`の
提案より優先する。

## Step 4: Automated Validation

Taskに関係する自動チェックがあれば実行する。本リポジトリで現状利用できるのは、`_articles/*.md` の
`status: ready` frontmatter整合性チェック(`.claude/hooks/check-article-status.js` が編集直後に自動
実行する。CIの `.github/workflows/pages.yml` と同じ基準)のみ。ローカルにRuby/Jekyllが無いため、
ローカルbuildは対象外(存在しないツールに依存しない)。

チェック結果を内部的に `EXECUTE_RESULT: OK` または `EXECUTE_RESULT: FAILED` として扱う。FAILEDの場合は
Step 3に戻って修正する。該当する自動チェックが存在しないTask(通常の記事執筆など)は、要件を満たして
いることを目視確認できた時点で `EXECUTE_RESULT: OK` として次へ進んでよい。

## Step 5: Self Evaluation

成果物の種類(コード/記事/設計/ドキュメント等)に応じて、その場でタスクに適した3〜5個の評価基準を
決める。固定リストは持たない。

記事の場合は独自基準を新設せず、`docs/publish-checklist.md` の観点(インタビュー・事実性、初心者向け
分かりやすさ、技術・安全、SEO、アフィリエイト、GitHub運用)を評価基準の土台にする。UI/UXを伴う変更の
場合は、`ui-ux-pro-max`のaccessibility/anti-patternチェックとCLAUDE.mdの優先順位(既存UIとの
一貫性を優先)を評価基準の土台にする。

各基準を100点満点で採点し、減点理由を短く記録する。

## Step 6: Independent Review

`Agent` ツールで `independent-reviewer` サブエージェントを起動する(LOWリスクでは省略してよい。
MEDIUM/HIGHでは必須)。作成者本人と同じ会話コンテキストでは完結させない。渡す情報:

- 元のタスク要求と完了条件
- 成果物本体(diff、記事全文、設計文書など)
- 参照すべき正本ファイルのパス(記事なら `CLAUDE.md` / `BRAND.md` / `docs/publish-checklist.md` など)

記事の場合、`.company/editorial/reviews/` や `.company/seo/reviews/` に既にレビューメモがあれば
そのパスも伝え、同じ観点の再指摘を避けさせる(cc-companyとの重複回避)。

レビュー結果を内部的に `CHECK_RESULT: OK` または `CHECK_RESULT: NG` として扱う。指摘の重大度は
`references/stop-conditions.md` の BLOCKER / MAJOR / MINOR をそのまま使い、独自の重大度体系を作らない。

自己評価の点数は参考情報として渡してよいが、reviewerの判定を誘導しない。

## Step 7: Iterative Refinement判定

`references/stop-conditions.md` の「2. Iterative Refinementの終了条件」を判定する。

- 満たしていない場合: Independent Reviewerの指摘と自己評価の差分をもとに改善し、Step 5(または
  Step 3)に戻る。
- 3iteration到達後も未解決の場合: それ以上の変更は行わず、`BLOCKED` として原因・試した内容・必要な
  人間判断を Step 9(State Update)の `Blocked` に記録し、Step 10へ進む。minorだけを理由に延々と
  改善を続けない。

## Step 8: Final Validation

Batch(2〜3 Task)がすべて完了した時点で、関係する自動チェックを再確認し、Claude Codeの通常操作
(Skill/Agentの読み込み、設定ファイルのパース等)を壊していないかを確認する。

## Step 9: State Update + Reusable Pattern Check

[`docs/TODO.md`](../../../docs/TODO.md) を現在の状態に更新する(`In Flight` / `Completed` /
`Owner Action Required` / `Blocked` / `Next Up` を付け替える。ログとして追記せず、その都度上書きする)。
セクション名自体はプロジェクトの実運用に合わせてよく、この5分類が固定の正解ではない。LOWリスクの
変更は該当行を1行更新する程度でよい。**新しい独自のPlan/TODOファイルを作らない**。プロジェクト状態の
正本は `docs/TODO.md` 一つに集約する。

`docs/TODO.md`は「現在状態の復元」専用であり、履歴ファイルにしない。サイズを以下の目安でコンパクトに
保つ: `In Flight`は現在実行中のTaskのみ、`Completed`は直近1〜2 Batch程度のみ(それより古い完了履歴は
削除してよい。詳細はGit historyに委ねる。commit/push/deployまで完了した項目は、コミットハッシュへの
言及のみを残し詳細な経緯は書かない)、`Owner Action Required`はオーナー判断待ちの項目のみ、`Next Up`は
直近の実行候補のみ、`Blocked`は現在有効なBlockerのみ。過去の履歴を保持するための新しい仕組み(別ファイル・
ログ等)は作らない。

### Reusable Pattern Check(Batch完了時)

Batch(2〜3 Task)・機能実装・重要デバッグの完了時に、State Updateと合わせて毎回実行する
(明示指示を待たない)。LOWリスクの単一Task(`references/stop-conditions.md`「5. リスクベースの
品質ゲート」)では省略してよい。今回の手順・知見について次を確認する:

1. 今回の成功手順は他プロジェクトでも再利用可能か
2. 新しいSkillとして一般化できるか
3. 既存Skillを改善できる知見か
4. `CLAUDE.md` へ追加すべき恒久的なプロジェクトルールか
5. グローバル設定(`~/.claude` 等)へ追加すべきルールか
6. `knowledge/` へ記録すべき意思決定・失敗・成功パターンか
7. 一時的・プロジェクト固有で保存不要か

判定を次のいずれかで示す(`REUSABLE_PATTERN:`):

- `NONE` — 一時的/自明。保存しない
- `SECOND_BRAIN_ONLY` — `knowledge/` へ記録する。`knowledge-management` Skillの書き込み基準で
  `decisions` / `experiments` / `lessons` / `revenue` / `ideas` のいずれかへ
- `UPDATE_EXISTING_SKILL` — 既存Skillの手順を更新する
- `NEW_SKILL_CANDIDATE` — 新Skill候補(下記5条件をすべて満たす場合のみ)
- `UPDATE_PROJECT_RULE` — `CLAUDE.md` へ恒久ルールを追記(HIGHリスクに準じオーナー確認)
- `UPDATE_GLOBAL_RULE` — グローバル設定の変更(オーナー確認必須)

`NEW_SKILL_CANDIDATE` は次をすべて満たすときのみとする: 複数プロジェクトで再利用できる /
手順が再現可能 / 明確な入力と出力がある / 人間またはClaude Codeの判断コストを削減できる /
既存Skillと重複していない。一度しか使わない処理・プロジェクト固有処理はSkill化しない。

`SECOND_BRAIN_ONLY` 以上と判定したものだけを `knowledge-management` Skillへ引き継ぐ。単なる作業ログを
大量保存しない。`UPDATE_PROJECT_RULE` / `UPDATE_GLOBAL_RULE` はオーナー承認を得るまで適用しない
(`references/stop-conditions.md`「1. 重大判断リスト」に準じる)。

## Step 10: 完了報告

ユーザーへ以下を簡潔に報告する。

- 自己評価の点数(基準ごと)
- Independent Reviewerの指摘とその解消状況(`CHECK_RESULT`)
- 残課題(`BLOCKED`があれば)

## Session Handoff

新しいSessionやSubagentは、過去の会話全文に依存せず、以下の順で現在状態を復元する:

1. `CLAUDE.md`(原則)
2. `ROADMAP.md` / `BRAND.md` / `CONTENT_PLAN.md` / `docs/PROJECT_PRINCIPLES.md`(SPEC層:目的・
   要件・制約・設計判断の正本。新しいSPEC.mdは作らない)
3. `docs/TODO.md`(現在の実行状態)
4. 関連するコード/記事ファイル
5. `git diff` / `git status`

これは「現在状態の復元」の順序。工程間(Research → Architect → Developer → independent-reviewer
→ Lead)で成果物・確定した判断・残課題を受け渡す場合は、目的が異なるため
[`references/handoff-format.md`](references/handoff-format.md) の構造化HANDOFFを使う。
短いタスクはセッション内で完結させ、永続ファイルは長時間・複数Agent・コンテキスト喪失リスクがある
場合のみ作る。

## Prompt Cache / Context Efficiency

独自のキャッシュや履歴管理は作らない。Claude Code標準のPrompt CachingとContext管理を活かす、
「不要なContextを入れない」ことを最優先にした運用ルールのみを以下に定める。優先順位:
(1)不要なContextを入れない (2)正本から必要時に取得する (3)Stable Prefixを維持する
(4)Subagentへ分離する (5)Prompt Cacheを再利用する (6)必要な場合のみCompact/Session Reset。
「Cache hit率を上げること」自体を目的にフローを複雑化しない。

**Stable Context**: 同一Batch内では、基盤変更そのものがTaskの目的でない限り、モデル・基本設定・
CLAUDE.md・Skill定義を不必要に変更しない(Prompt Cacheのprefixを壊さない)。

**Reuse instead of Re-send**: 「Session Handoff」に挙げた正本群(CLAUDE.md/SPEC層/`docs/TODO.md`/
Git状態)の内容をプロンプトへ再記述せず、必要になった時点でそれぞれの正本を読む。

**Log Reduction**: build/test/install/検索結果/大きいgit diffの全文をMain Contextに保持しない。
成功時は結果のみ残す。失敗時はエラー・関連スタックトレース・失敗箇所・修正に必要な周辺情報だけを残す。

**Search Scope**: 調査対象を「関連ディレクトリ→関連ファイル名→関連シンボル」の順で絞る。リポジトリ
直下には本プロジェクトと無関係な兄弟プロジェクト(`ai-content-engine/`, `global-trend-discovery/`,
`line-stock-news-bot/`, `claude-code-practice/`)が存在し、範囲を絞らない検索はこれらを巻き込み数万
ファイルに一致しうる。検索は `_articles/` `docs/` `assets/` `_layouts/` `.claude/` など関連ディレクトリ
に絞る。

**Subagent Context Isolation**: 調査が広範囲に及ぶ場合はExploreサブエージェントへ委譲し、Independent
Reviewは常に別Context(Agentツール経由)で行う。Subagentから受け取ってMain Contextへ残すのは、
結論・重要な根拠・BLOCKER/MAJOR/MINOR・必要な次Actionのみとし、調査ログ全文は持ち込まない。

**Session Boundary**: 関連する2〜3 Task = 1 Batchを目安に区切る。ただし機械的にSessionを切らない。
Context肥大化・Taskのテーマが大きく変わる・大量のTool output蓄積・完全に独立した次Batchへの移行・
参照ミスや混同の増加、のいずれかが起きた場合にのみContext整理や新Sessionを検討する。`/compact`
`/clear` はTask途中で習慣的に使わず、State Update完了後のBatch境界で検討する。

## cc-companyとの関係

`.company/`(company Skill)はオーナー向けの進行管理・意思決定ログ・部署ごとの一次レビューを担う。
このスキルはそれとは独立した、Claude Codeが成果物を出す前の内部品質ゲート。`.company/` が起動して
いなくても常に機能する。`.company/` 配下のファイル・運用ルールは変更しない。

`docs/TODO.md`(開発Batchの実行状態: In Flight/Blocked等)と `.company/secretary/todos/`(オーナー
向け日次ビジネスTODO、company Skill起動時のみ)は粒度も起動条件も異なる別物。一方のルールを他方へ
コピーしない。

## 参照ファイル

- `references/stop-conditions.md` — 重大判断リスト、リスクベースの品質ゲート(LOW/MEDIUM/HIGH)、
  Iterative Refinementの終了条件、重大度定義(このスキルと `independent-reviewer` エージェントの
  共通の正本)
- `references/handoff-format.md` — 工程・Agent・Skill間の作業引き継ぎに使う構造化HANDOFF
  フォーマットと、セッション内/永続ファイルの判断基準(`CLAUDE.md`「Agent間HANDOFF標準」から参照される)
