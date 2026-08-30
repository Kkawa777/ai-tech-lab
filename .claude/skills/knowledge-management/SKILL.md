---
name: knowledge-management
description: >
  knowledge/(第二の脳)の整理・昇格を行うときに使う。inbox整理、意思決定/実験/教訓/収益化学習の
  記録、cross-link、重複・陳腐化チェックを担当する。通常の実装作業(記事執筆・コード修正)は担当
  しない。ユーザーが「覚えておいて」「取り込んで」と言ったとき、重要なarchitecture decisionが
  確定したとき、reusable lessonやexperimentの終了時、quality-developmentのState Updateで
  Taskが知識化基準を満たすと判断したときに使う。
---

# knowledge-management

[`knowledge/`](../../../knowledge/README.md)(第二の脳)を、書きすぎず・陳腐化させずに保つための
Skill。実装は行わない。

## 担当

- `knowledge/inbox/`の整理(他ディレクトリへの昇格、または価値がなければ削除)
- `knowledge/decisions/` `experiments/` `lessons/` `revenue/` `ideas/`への記録
- 関連ファイル同士のcross-link(Markdownリンク)
- 重複・陳腐化したナレッジの検出と統合・更新

## 担当しないこと

- 記事執筆・コード実装・設計そのもの(`quality-development` Skillの対象)
- `docs/TODO.md`の現在状態管理(通常どおり`quality-development` Step 9で更新する)
- `.company/`配下のファイル・運用ルールの変更(不可侵。オーナー向けの非Git・雑多メモ専用)

## 発火条件

- ユーザーが「覚えておいて」「取り込んで」と明示的に指示したとき
- 重要なarchitecture decisionが確定したとき
- 再利用可能な教訓(lesson)が発生したとき
- experimentが終了し、結論が出たとき
- `quality-development` Skill Step 9(State Update)で、完了したTaskが下記「書き込み基準」を
  満たすと判断されたとき

## 書き込み基準

以下のいずれかに該当する場合のみ`knowledge/`へ書く。該当しない短命な情報は`docs/TODO.md`
(現在の作業状態)または`.company/secretary/`(オーナー向け雑多メモ、company Skill起動時のみ)に
留める。

- 将来の再利用価値がある
- 重要な意思決定である
- コストの高い調査の結果である
- 避けるべき失敗である(失敗した実験も残す)
- アーキテクチャに関わる
- 収益化に関わる

## 進め方

1. **inbox整理**: `knowledge/inbox/`に溜まっているファイルを確認し、上記基準を満たすものを
   `decisions/` `experiments/` `lessons/` `revenue/` `ideas/`のいずれかへ移す(内容を整理して
   1ファイル=1トピックにする)。基準を満たさないものは削除するか、`docs/TODO.md`側に留める判断を
   提案する
2. **新規記録**: 該当するサブディレクトリへ`kebab-case-title.md`で新規作成する。
   [`knowledge/README.md`](../../../knowledge/README.md)のテンプレート(Summary / Why it
   matters / Details / Related decisions / Related experiments / Related projects / Source /
   Last updated)を目安にするが、機械的に全項目を強制しない
3. **cross-link**: 関連する既存の`knowledge/`ファイル、`docs/TODO.md`の該当箇所、
   `ROADMAP.md`/`BRAND.md`/`CONTENT_PLAN.md`/`docs/PROJECT_PRINCIPLES.md`(SPEC層)への
   Markdownリンクを追加する。SPEC層の内容そのものは複製しない
4. **重複・陳腐化チェック**: 新規作成前に同トピックの既存ファイルがないか`knowledge/`内を検索する。
   既存ファイルと矛盾する情報を見つけた場合は、新規ファイルを作らずその場で既存ファイルを更新し
   `Last updated`を書き換える

## .company/との関係

`.company/secretary/`(inbox/notes/todos)はオーナー向けの日々の壁打ち・メモ・日次TODOであり、
Git管理外・整理されていなくてよい前提で運用されている。`knowledge/`はその対極で、Git管理下にある
整理済み・再利用可能な知識のみを置く。

- 両者のファイル・運用ルールは互いに変更しない
- `.company/secretary/notes/`の意思決定・学びメモの中に、上記「書き込み基準」を満たす価値の高い
  ものが見つかった場合は、内容をコピーして`knowledge/`側へ**昇格**してよい(元の`.company/`側の
  ファイルは変更しない)
- `.company/`が起動していなくても`knowledge/`は独立して機能する(`quality-development`と
  `.company/`の関係と同じ設計)

## docs/TODO.mdとの関係

`docs/TODO.md`は「現在実行中の作業状態」の正本であり、`knowledge/`は「長期的に再利用する価値がある
知識」の正本。同じ内容を両方に書かない。Batchが完了しState Updateで`docs/TODO.md`から該当項目を
圧縮・削除するタイミングで、書き込み基準を満たすものだけを`knowledge/`へ昇格させる。

## Reusable Pattern Checkとの連携

`quality-development` Skill Step 9の「Reusable Pattern Check」で判定された結果のうち、次のものだけを
このSkillで扱う(判定値の定義はStep 9が正本。ここでは複製しない)。

- `SECOND_BRAIN_ONLY` — 上記「書き込み基準」に従い、`decisions/` `experiments/` `lessons/`
  `revenue/` `ideas/` のいずれかへ記録する
- `UPDATE_EXISTING_SKILL` / `NEW_SKILL_CANDIDATE` — 主対応はSkill側の更新・新設。関連する意思決定の
  背景を残す価値がある場合のみ `knowledge/decisions/` へ記録する。`NEW_SKILL_CANDIDATE` の成立条件は
  Step 9 が正本。条件を満たさずSkill化しないものは、必要なら `lessons/` に教訓として残すに留める
- `NONE` / プロジェクト固有の一時情報 — `knowledge/` には書かない

`UPDATE_PROJECT_RULE`(`CLAUDE.md`)・`UPDATE_GLOBAL_RULE`(グローバル設定)はこのSkillの対象外。
オーナー承認を得たうえで該当ファイルを直接更新する。
