# devlog-policy.md

「開発したら勝手にブログ記事が生まれる」仕組み(Dev Log自動生成)の正本ドキュメントです。
CLAUDE.mdの最重要ルール(記事化前インタビュー必須)は、**Dev Log記事には適用されません**。
Dev Logは「実体験記事」(体験・感想・失敗談を人から聞き取って書く記事)ではなく、
「Git履歴という一次情報から機械的に事実だけを抽出する開発ログ」という別ジャンルとして扱うため、
このジャンルに限定してインタビュー必須ルールを適用除外します。この方針転換自体はオーナーの
指示(2026-08-28)に基づきます。他の記事ジャンル(実践プロジェクト作品集等)には引き続き
CLAUDE.mdのインタビュー必須ルールが適用されます。

## 1. Dev Logとは何か

日々の開発活動(commit・diff・README変更等)から、AIが自動的に生成する開発ログ記事です。
「ブログを書くために開発する」のではなく「開発した結果としてブログが増える」という関係を
実現するための最初のPoCです。

- `content_type: devlog` という新しいfrontmatter値で、既存の`informational`/`commercial`と
  区別する
- `category: 開発ログ` という新しいcategory値を用いる(既存の`Arduino入門`/`実践プロジェクト
  作品集`と同列の値。既存テンプレート・レイアウトは`category`を汎用的にバッジ表示するだけなので
  新しい値を追加してもテンプレート改修は不要)
- 既存の「実践プロジェクト作品集」等の実体験記事とは完全に独立したジャンルであり、置き換えでは
  ない

## 2. frontmatterスキーマ(最小追加)

既存スキーマに対する追加は以下のみ。

```yaml
content_type: devlog
source_project: <config/devlog-projects.yamlのproject key>
source_commits:
  - <commit hash>
  - <commit hash>
development_date: YYYY-MM-DD
generated_from_git: true
social_summary: <将来のX投稿用の短い要約。今回投稿はしない>
monetization: none   # Dev LogではAffiliateを必須にしない。商品が明確に確認できない限りnone
```

`title`/`status`/`permalink`/`order`/`description`/`category`/`difficulty`/`estimated_time`/
`primary_keyword`/`search_intent`は既存スキーマをそのまま使う。`affiliate_products`は、
Git履歴やAI-Tech-Lab既存knowledge(`config/devlog-projects.yaml`等)から実使用商品のASINが
明確に確認できる場合のみ追加する(このPoCでは対象なし)。

### orderの扱い(既存カタログ番号との衝突防止)

`site.articles`は`order`でソートして`/articles/`とホーム`はじめての方はこちら`に一覧表示される
(1つのcollectionを共有しているため)。既存の手動記事(第1〜7号、`order: 1`〜`7`)のカタログ
番号と衝突しないよう、Dev Logの`order`には専用の高位レンジ `9<YYYYMMDD><連番2桁>` を使う
(例: 2026年8月28日、同日1本目 → `order: 92026082800`)。これにより、Dev Logは既存カタログの
後ろに時系列で並び、将来の手動記事(`order: 8`, `9`, ...)と衝突しない。新しいindex/レイアウトは
作らず、既存の`/articles/`一覧にカテゴリバッジ「開発ログ」付きでそのまま表示される(最小変更)。

## 3. ステータス運用(`_articles/`はready専用というルールを厳守)

`scripts/validate-site.py`の`check_ready_status`と`.claude/hooks/check-article-status.js`は、
`_articles/`配下の**すべての**ファイルが`status: ready`であることを要求する(既存ルール)。
Dev Logもこの既存ルールに従う。

- `generate-devlog.py --write` は `_articles/` へ直接書き込まず、必ず **`drafts/`** へ
  `status: draft` で出力する
- `_articles/` への昇格(`status: ready`への変更・`order`の確定・ファイル移動)は、
  quality-development・independent-reviewerを経た上で、人(またはそれに代わる明示的な
  Owner許可済みバッチ実行)が行う。ツールが自動でreadyにはしない

## 4. Factルール(創作禁止の運用)

Ownerへ質問せず自律的に進めるため、以下の3分類のみを記事に使用する。

- **CONFIRMED_GIT_FACT**: commit hash・commit message・変更ファイル一覧・diffの行数サマリ
  (`--shortstat`)・commit日時など、Git履歴から直接取得できる事実
- **VERIFIED_TECH_FACT**: 公式ドキュメント等、外部の一次情報で確認できる一般的な技術情報
  (このPoCでは基本的に使用しない。使う場合は出典URLを明記する)
- **UNKNOWN**: 上記以外(なぜ必要だったか、実際の使用感、体験談など、Gitから読み取れない情報)。
  **記事に一切使用しない**。一般化・推測による埋め合わせも禁止

全文diffは記事に貼らない。ファイル一覧・行数サマリ・commit messageのみを情報源とする
(後述のSecurity/Privacyフィルタが、diff本文そのものを読まない設計になっている理由でもある)。

## 5. 重要度判定(記事化フィルタ)

1日のcommitのうち、以下を「trivial」として記事化対象から除外する。

- commit messageが `chore:` / `typo` / `fix typo` / `style:` / `formatting` 等で始まる
- 変更ファイルが lockfile(`*.lock`, `package-lock.json`, `skills-lock.json`等)・
  `.gitignore`・`README.md`のみで構成されている(実装では、commit messageの接頭辞に関わらず
  変更ファイルがこの一覧だけの場合を機械的にtrivial判定する。「軽微」かどうかを行数で判定する
  処理は現時点では実装していない)
- マージコミット(親commitが2つ以上)は、変更ファイル一覧が正しく取得できない既知の制約が
  あるため、記事化対象から除外する(このリポジトリは現状linear historyのため未発火)

該当日にtrivialなcommitしか存在しない、またはcommitが1件もない場合は **SKIP**(記事を作らず、
正常終了する)。「毎日投稿」ではなく「価値がある日だけ投稿」という設計を、SKIPをエラー扱い
しないことで実現する。

同一日・同一projectのnotableなcommitは、原則として1本のDev Log記事にまとめる(複数の
小commitが同一機能に属する場合の細切れ記事化を避ける)。

## 6. Security / Privacyフィルタ(allowlist方式)

### 6.1 対象project allowlist

`config/devlog-projects.yaml` に列挙され、かつ `enabled: true` かつ `public: true` の
projectのみを記事化対象とする。設定ファイルに存在しないrepository、または
`enabled: false`/`public: false`のrepositoryは、パスを直接指定されても**絶対に**読み取り・
記事化しない(deny-by-default)。

さらに、`--project`で指定されたproject keyの設定にある`path`と、`--repo`で実際に指定された
パスの実体(`os.path.realpath`で解決した絶対パス)が一致することを確認する。一致しない場合は
処理を中断する。これにより、「project名だけ`ai-tech-lab`(公開許可済み)と偽装して、実際には
別の非公開repositoryを読み込ませる」という設定なりすましを防ぐ。

### 6.2 secrets/private情報フィルタ

このツールは設計上、**diff本文(コード内容そのもの)を記事の情報源として一切使わない**
(commit hash・commit message・変更ファイル名・行数サマリのみを使用)。これにより、
コード中のAPI key・token・passwordがそのまま記事に転記されるリスクを構造的に減らしている。

その上で、二重の防御として、commit messageと変更ファイル名に対して以下のパターンを
大文字小文字を区別せず走査し、一致したcommitは記事から除外する(値そのものは記事は
おろかログにも出力しない。「除外した」という事実のみを記録する)。

- `secret` / `password` / `passwd` / `token` / `api[\s_-]?key` / `access[\s_-]?key` /
  `credential` / `oauth` / `private[\s_-]?key` / `aws_access_key_id` /
  `aws_secret_access_key` / `bearer` / `ssh[\s_-]?key`
  (`api[\s_-]?key` / `access[\s_-]?key` / `private[\s_-]?key` / `ssh[\s_-]?key`の4つのみ、
  空白・アンダースコア・ハイフンの区切り文字の表記揺れを許容する正規表現。`aws_access_key_id` /
  `aws_secret_access_key`はアンダースコア区切りの固定文字列一致で、他の表記揺れには一致しない。
  残りは区切り文字を含まない単語一致。この一覧は`scripts/generate-devlog.py`の
  `SECRET_MESSAGE_PATTERNS`と完全に一致させること)

対象ファイル名パターンで即座に除外するもの: `.env`, `*.pem`, `*.key`, `*credentials*`,
`*secret*`。

このフィルタは「記事に使わない」ための除外であり、対象repository自体の安全性を保証するもの
ではない。**allowlistに載せる判断自体が、そのrepositoryを公開して問題ないことの一次防波堤**
であることに変わりはない。

## 7. 重複防止・冪等性

`_articles/`と`drafts/`の両方から、`generated_from_git: true`かつ`source_project`が一致する
既存ファイルの`source_commits`を収集する。今回生成しようとしているcommit hashの集合が、
既存のいずれかのファイルの`source_commits`に完全に含まれる場合は、再生成せず正常終了する
(同じ入力に対して同じ出力を保証する冪等設計)。

## 8. Screenshot対応(設計のみ、今回は自動撮影しない)

`dev-log-artifacts/<project>/<date>/`(リポジトリ直下、`.gitignore`対象、Git管理しない
一時置き場)にスクリーンショットが存在すれば、`--write`時に`assets/images/devlog/<slug>/`
へコピーして本文で参照する。存在しなければ画像なしで記事を生成する(画像がないことを理由に
生成を止めない)。今回のPoCでは自動撮影の実装は行わない。

## 9. SEO

`title`・`primary_keyword`・`description`は、commit messageと変更ファイルから機械的に
生成する(創作しない)。「開発日記 8月28日」のような日付だけのタイトルにはせず、
commit messageに含まれる実装内容の説明をそのままタイトルの主要素にする。

**既知の制約(未解決のトレードオフ)**: 本リポジトリのcommit messageは英語表記の慣習(例:
`feat: add affiliate link to ...`)のため、機械生成されたtitleは英語のcommit subjectを
翻訳せずそのまま含む(例: `AI-Tech-Lab 開発ログ(2026-08-23): add affiliate link to
ESP32-CAM article ほか1件`)。これは創作防止のFactルールを優先した結果であり、
`docs/publish-checklist.md`のSEO Gate(「読者が実際に検索するキーワードを含めている」)を
Dev Logが完全には満たさないことを意味する。自動翻訳は行わない(誤訳による事実のねじれを
避けるため)。`_articles/`へ昇格する際は、人がtitle/primary_keywordを日本語の自然な検索
クエリに書き換えることを推奨する(Dev Log Gateのチェック項目として明記)。書き換えなしで
昇格しても事実性は損なわれないが、SEO上の効果は限定的になる。

## 10. Affiliate/Monetizationとの関係

Dev LogはAffiliateを必須にしない。実使用商品がGit履歴や既存knowledgeから明確に確認できない
限り`monetization: none`のまま公開する。収益化できないことを理由にDev Log自体の生成・公開を
止めない(SEO資産の蓄積を優先する)。

## 11. content-revenue-engineとの責務分離

`content-revenue-engine/`(別repository、独立管理)は「Knowledge Card→Topic Scoring→
Campaign Planning→Content Generation→...→Publish」という、**トレンド・実験結果・商品情報
などの外部ナレッジを起点にした収益コンテンツパイプライン**を目的とする。

一方、本Dev Log機能は「**このリポジトリ自身(および将来のsibling project)のGit履歴**を
起点にした、AI-Tech-Lab固有のJekyll記事生成CLI」であり、対象データソース(Git履歴 vs
外部ナレッジ)・出力先(AI-Tech-Lab `_articles/`直接 vs 汎用パイプライン)・実行主体
(このリポジトリのスクリプト vs 独立repositoryのCLI)のいずれも異なる。将来的に
`social_summary`をX投稿に使う段階になった際は、投稿実行そのものは`content-revenue-engine`
側のPublisher機能に委譲する設計が自然だが、今回のPoCではその結合は一切実装しない
(`content-revenue-engine/`は変更禁止という指示にも従う)。

## 12. 20:00自動実行への対応

このPoCではscheduler自体を実装しない。ただし`scripts/generate-devlog.py`は
`--repo`/`--project`/`--date`を引数で受け取る非対話的なCLIとして設計しており、
GitHub Actions(`schedule:` cron)・Windows Task Scheduler・その他の環境から
`python scripts/generate-devlog.py --project ai-tech-lab --date $(date +%F) --write` の
ように呼び出せる。「記事価値のある開発が存在しない日はSKIP」は本ツール自体の判定ロジック
(重要度判定・trivial-only時のSKIP)で既に実現されているため、スケジューラ側は単に毎日
定時にこのCLIを呼ぶだけでよい。
