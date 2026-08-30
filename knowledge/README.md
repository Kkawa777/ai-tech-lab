# knowledge/

AI-Tech-Labの「第二の脳」。Git管理下にある、長期的に再利用可能な整理済み知識を置く。

## これは何のためにあるか

このリポジトリには、すでに複数の「状態を持つ場所」がある。`knowledge/`はそのどれとも役割が重ならない。

| 置き場所 | 役割 | Git管理 |
|---|---|---|
| `ROADMAP.md` / `BRAND.md` / `CONTENT_PLAN.md` / `docs/PROJECT_PRINCIPLES.md` | プロジェクトの目的・方針・記事企画(SPEC層)の正本 | される |
| `docs/TODO.md` | **現在進行中の作業状態**の唯一の正本(In Flight / Completed / Blocked等) | される |
| `.company/secretary/` | オーナー向けの日々の壁打ち・メモ・日次TODO(雑多・未整理でよい) | **されない**(`.gitignore`対象) |
| `knowledge/`(このディレクトリ) | 上記のどこにも属さない、**将来のセッションでも再利用する価値がある整理済み知識** | される |

`knowledge/`は`docs/TODO.md`や`.company/`の内容を複製しない。作業が終わったときに「後から見返す価値が
あるものだけ」をここへ昇格させる。

## 書き込み基準

以下のいずれかに該当する場合のみ、新しいファイルを作る。該当しないものは`docs/TODO.md`(現在の状態)
または`.company/secretary/`(雑多メモ、company Skill起動時)に留める。

- 将来の再利用価値がある
- 重要な意思決定である
- コストの高い調査の結果である
- 避けるべき失敗である(失敗した実験も残す。消さない)
- アーキテクチャに関わる
- 収益化に関わる

短命な情報・現在進行中のタスクの詳細をここに書かない。

## 構造

```
knowledge/
  README.md       このファイル
  inbox/          未整理の一時情報(定期的にここから他のディレクトリへ整理する。恒久置き場にしない)
  decisions/      重要な意思決定の記録(Decision / Reason / Alternatives / Date)
  experiments/     試したこと(hypothesis / implementation / result / evidence / conclusion / next action)
  lessons/        再利用可能な教訓・失敗から学んだこと
  revenue/        収益化に関する仮説→実験→結果の記録(Amazonアフィリエイト等)
  ideas/          まだ採用されていない**非記事**のアイデア(記事アイデアは`CONTENT_PLAN.md`が正本)
```

`knowledge/projects/`は作らない。プロジェクト全体の方針・アーキテクチャ・制約は
`ROADMAP.md`/`BRAND.md`/`CONTENT_PLAN.md`/`docs/PROJECT_PRINCIPLES.md`が既に正本であり、
重複させない。

## 運用ルール

- **1ファイル = 1トピック**。巨大なまとめファイルを作らない
- ファイル名は`kebab-case-title.md`
- 関連情報は`[decisions/xxx.md](../decisions/xxx.md)`のようなMarkdownリンクで接続する
- 外部記事・調査結果から作成した場合は、可能な範囲でSource(URL・日付)を残す
- テンプレートを機械的に全ファイルへ強制しない。目安として以下の見出しを使えるときは使う:
  `Summary` / `Why it matters` / `Details` / `Related decisions` / `Related experiments` /
  `Related projects` / `Source` / `Last updated`
- `docs/TODO.md`の`In Flight`/`Completed`から、Batch完了時に知識化基準を満たすものだけを昇格する
  (`quality-development` SkillのStep 9、および`knowledge-management` Skillを参照)

## 関連

- 現在の作業状態: [`docs/TODO.md`](../docs/TODO.md)
- 品質フロー: [`.claude/skills/quality-development/SKILL.md`](../.claude/skills/quality-development/SKILL.md)
- 知識の整理・昇格運用: [`.claude/skills/knowledge-management/SKILL.md`](../.claude/skills/knowledge-management/SKILL.md)
