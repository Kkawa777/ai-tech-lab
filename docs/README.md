# docs

運営・レビュー用ドキュメントを置くディレクトリです。公開サイト(GitHub Pages)には含まれません。

**記事本文の正本は、このディレクトリではなく[`_articles/`](../_articles/)(リポジトリ直下)です。** `status: ready`になった記事だけを`_articles/`に置き、GitHub PagesがJekyllでビルドして公開します。`review` / `testing` / `draft`などready未満の記事は`_articles/`に置かず、執筆・レビューが完了してから`_articles/`へ移します。

## このディレクトリのドキュメント

- [PROJECT_PRINCIPLES.md](./PROJECT_PRINCIPLES.md) — CLAUDE.md / BRAND.md / ROADMAP.mdの原則索引
- [publish-checklist.md](./publish-checklist.md) — 記事を`ready`にする前の最終チェックリスト
- [devlog-policy.md](./devlog-policy.md) — `content_type: devlog`(Git履歴から自動生成する開発ログ)の設計・Factルール・allowlist・重複防止の正本
- [TODO.md](./TODO.md) — 現在の開発状態(In Flight / Completed / Owner Action Required / Blocked / Next Up)。ログではなく都度上書きするHandoff Contractの一部
- 記事執筆用テンプレートは [`templates/article-template.md`](../templates/article-template.md) が正本です(docs内には複製しません)

## このディレクトリのサブディレクトリ

- `reviews/` — 公開前レビュー用の内部メモ(記事ごとのチェック結果・承認記録)
