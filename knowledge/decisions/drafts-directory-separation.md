---
name: drafts-directory-separation
description: readyに満たない記事をdrafts/へ、_articles/はstatusに関わらず常にビルド公開されるという制約
metadata:
  type: decision
---

# `drafts/`ディレクトリを新設し、非readyの記事を分離する

## Summary

`_articles/`はJekyllのcollection(`output: true`)であるため、置いたファイルは`status`の値に
関わらず常にビルド・公開されてしまう。`idea` / `interview` / `draft` / `testing` / `review`など
`ready`未満の記事は`drafts/`(リポジトリ直下、`_config.yml`の`exclude`でビルド対象外)に置き、
執筆・レビューが完了してから`_articles/`へ移す。

## Why it matters

「`status: draft`と書いてあれば公開されない」という誤解をしたまま`_articles/`に記事を置くと、
未完成・未検証の内容がそのままGitHub Pagesで公開されてしまう。この制約はJekyll固有の挙動であり、
記事執筆時に毎回意識する必要がある。

## Details

- `_config.yml`の`exclude`に`drafts/`を追加
- 運用ルールは[`docs/README.md`](../../docs/README.md)に記載
- 記事のstatusフロー(`idea → interview → draft → testing → review → ready`)自体は変更しない
  ([CLAUDE.md](../../CLAUDE.md)「記事ステータス」が正本)

## Related decisions

- [article-filename-vs-catalog-number](article-filename-vs-catalog-number.md)

## Source

`docs/TODO.md`「Completed」(2026年8月)

## Last updated

2026-08-24
