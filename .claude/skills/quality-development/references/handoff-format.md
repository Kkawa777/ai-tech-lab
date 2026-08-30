# Agent間HANDOFF標準

工程・Agent・Skill間で作業を引き継ぐときの構造化フォーマット。`quality-development/SKILL.md` と
`CLAUDE.md`「Lead / Orchestrator」から参照される共通定義。定義を変更する場合はこのファイルのみを
更新し、参照側にはコピーしない。

曖昧な散文だけで次工程へ渡さないためのもの。工程間の「成果物・確定した判断・残課題」を欠落なく
受け渡すことが目的で、`quality-development/SKILL.md`「Session Handoff」節(新セッション/サブAgentが
現在状態を復元する順序)とは目的が異なる。

## フォーマット

```markdown
# HANDOFF

## Goal
今回達成すべき目的

## Context
必要な背景情報(前提、関係する正本ファイルのパス)

## Findings
調査・実装・レビューで判明した事実

## Decisions
確定した設計判断・方針

## Risks
既知のリスク・注意点

## Changed Files
変更したファイル一覧。変更がなければ none

## Tests
実施したテストと結果。未実施のものも明記

## Remaining Issues
残課題。なければ none

## Next Action
次工程が実行すべき具体的な作業
```

## セッション内で済ませる / 永続ファイル化する

不要なMarkdownファイルを量産しないことを最優先する。

- **セッション内の構造化HANDOFF(既定)**: 短いタスク、単一Agent、同一セッションで完結する場合。
  上記見出しに沿ってセッション内メッセージとして次工程へ渡す。ファイルを作らない。
- **永続ファイル化(例外)**: 長時間作業、複数Agent、複数Batch、コンテキスト喪失リスクがある場合のみ。
  置き場所はタスクに紐づくscratchpad(または必要なら `docs/` 配下の一時ファイル)とし、Batch完了後に
  不要になったら削除する。`docs/TODO.md` の代替にしない(現在状態の正本は引き続き `docs/TODO.md` 一つ)。

## 典型的な流れ

```
Research → HANDOFF → Architect / Planner → HANDOFF → Developer → HANDOFF →
independent-reviewer → HANDOFF → Lead
```

各工程は必要に応じてHANDOFFを生成する。全工程で機械的に必須とはしない。LOWリスクの単一Task
(`stop-conditions.md`「5. リスクベースの品質ゲート」)では省略してよい。
