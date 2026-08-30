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
  残りは区切り文字を含まない単語一致。この一覧は`scripts/devlogkit/security.py`の
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

---

# Phase 2: 品質モデルと自動公開能力(2026-08-30〜)

Phase 1(PoC)は「Git履歴からdraftを生成できる」ことの実証だった。生成物は
「commit metadataを並べた機械的な要約」に近く、そのまま公開する記事品質には
届いていなかった。Phase 2は、安全性を一切下げずに、この生成品質を引き上げ、
将来の自動公開に向けた品質ゲート・昇格の仕組みを追加する。

実装は`scripts/devlogkit/`パッケージに集約し、`scripts/generate-devlog.py`
(`--dry-run`/`--write`/`--auto`)・`scripts/promote-devlog.py`・
`scripts/run-daily-devlog.py`はすべて同一の`devlogkit.pipeline.run()`を呼ぶ
(Phase1相当の簡易ロジックとPhase2の高度なロジックを別々に持たない。実装が
1本のパイプラインしかないことで、レビュー対象・テスト対象を一本化している)。

## 13. Sanitized Change Summary Layer(`scripts/devlogkit/sanitize.py`)

Phase 1は「diff本文を一切読まない」設計だった。Phase 2はこれを「安全な範囲でのみ
diff内容を読む」に緩和するが、以下の順序を必ず守る(この順序自体がセキュリティ境界)。

```
変更ファイルパス
  → security.is_denylisted_path()? --yes--> 読まずにスキップ(ファイル名はfiles_changedに残るのみ)
  → gitmeta.get_file_diff() (最大400行)
  → "Binary files ... differ" ? --yes--> スキップ
  → security.scan_lines_for_secrets() (diff本文への二次スキャン) --hit--> このファイルの抽出結果を全て破棄
  → 関数/クラス/テスト名のシグネチャ行のみ正規表現抽出(本文・値は抽出しない)
  → README/ドキュメント(`*.md`全般。`_articles/`配下も含む)は追加された地の文のみ抽出
    (YAML frontmatter行・見出し・コードフェンス・表は除外)
  → 単純な1行置換(削除1行+追加1行のみのhunk)は「変更前後」として記録、それ以外はUNKNOWN
```

`PATH_DENYLIST_PATTERNS`(`security.py`)は`.env`・秘密鍵・credential・lockfile・
`node_modules`/`vendor`/`dist`/`build`等のvendored/生成物・バイナリ拡張子を対象とする。
false positiveで読まれない分には実害がない(その分、機械的なfiles_changedの記載のみに
留まる)設計のため、意図的に広めに倒している。

## 14. Quality Score(`scripts/devlogkit/score.py`)

5軸(各0〜20点、合計0〜100点)。すべてGit metadata・Sanitized Change Summaryから
決定論的に算出し、AIの主観評価は使わない。

| 軸 | 何を見るか |
|---|---|
| Development Value | notable commit数・変更行数の規模・関数/クラス追加の有無 |
| Reader Value | docs抜粋・テスト追加・関数/クラス追加の有無 |
| Evidence Strength | evidence件数・変更前後ペアの有無・安全性理由での除外率(高いと減点) |
| Technical Depth | 抽出できたsignalの種類数(関数/クラス/テスト/docs/前後ペア) |
| SEO Potential | 記事タイプがGENERICでないか・タイトルの日本語変換カバレッジ |

安全性(Security/Privacy/Fact)はスコアに含めない**独立したgate**とし、
`score.check_safety_gates()`が**最終的にレンダリングされた記事全文**を対象に、
`sanitize.py`の除外ロジックとは独立に再スキャンする(defense in depth。生成ロジック
自体にバグがあっても検出できるようにするため)。

- Security Gate: 記事全文が`SECRET_VALUE_PATTERNS`(AWSキー・sk-系トークン・GitHub PAT・
  Slackトークン・PEM秘密鍵・JWT等の値そのものの形)に一致しないか
- Privacy Gate: 記事全文にWindows/Linux/macOSの絶対パス(個人環境のディレクトリ構造)が
  含まれていないか
- Fact Gate: evidenceが参照するファイルパスが、同時にfiles_skipped_for_safetyにも
  含まれているという矛盾(実装バグの検出器)がないか

3つのうち1つでもFAILなら、スコアに関わらず`BLOCKED`(Step3の要求どおり)。

### Publish Threshold

```
score >= 80                          -> AUTO_PUBLISH_CANDIDATE
60 <= score < 80                     -> DRAFT_ONLY
score < 60                           -> SKIP
Security/Privacy/Fact のいずれかFAIL  -> BLOCKED(スコアを上書き)
```

閾値は、このリポジトリ自身の実データ3日分(2026-08-06・2026-08-22・2026-08-23)で
検証した([Old vs Phase2比較](#old-vs-phase-2の比較)参照)。2026-08-22
(記事公開2件、docs抜粋・前後ペアあり)がスコア67でDRAFT_ONLY、2026-08-06
(創業日、7 commit・docsは豊富だが記事タイプがGENERIC)がスコア57でSKIPとなり、
「型が明確でない日は厳しめに評価する」という意図した挙動を確認した上でこの閾値とした。

## 15. 記事タイプ別テンプレート(`scripts/devlogkit/classify.py` / `templates.py`)

commit subjectとファイル拡張子からFEATURE/BUGFIX/PERFORMANCE/UI/ARCHITECTURE/GENERICの
いずれかに分類し(1日に複数種類が混在する場合は最頻出タイプを採用)、タイプごとに
見出し構成を変える。Bug Fix/Performance/Architectureタイプでは、原因・実測値・
トレードオフの詳細がGitから確認できない場合に「本記事では記載していません(未確認)」と
明記する定型文を必ず含める(Step8のFactルールをテンプレートレベルで強制する)。

## 16. 日本語タイトル生成(`scripts/devlogkit/ja.py`)

LLM呼び出しは行わない。理由: 20:00無人実行を想定する以上、生成過程に自由生成モデルを
挟むとhallucinationリスクが常時運用に乗ってしまう。代わりに、

1. リポジトリ固有の複数語フレーズ辞書(`MULTI_WORD_OVERRIDES`。例: "load cell"→
   "ロードセル")を最長一致で先に適用
2. 残った単語を汎用辞書(`JA_TERM_MAP`)で置換(未知語はそのまま、大文字化のみ)
3. 先頭の動詞を`VERB_MAP`で「〜しました」に変換し、目的語を前に置く
   (例: "publish ESP32 rain sensor detection article" →
   "ESP32雨センサー検知記事を公開しました")

翻訳カバレッジ(辞書で置換できた語の割合)が34%未満の場合は、不自然な単語の羅列に
なるため翻訳を採用せず、Phase 1と同じ「日本語の枠に英語のcommit subjectをそのまま
埋め込む」形にフォールバックする。この辞書はこのリポジトリの実際のcommit履歴の語彙を
中心に構築しており、他projectでは未知語が増えてフォールバックが多くなる想定(既知の限界)。

## 17. Screenshot候補化(`scripts/devlogkit/screenshots.py`)

`screenshots/`・`artifacts/`・`docs/images/`・`test-results/`・`playwright-report/`配下の
画像ファイルのうち、ファイル名に日付を含む・または更新日時が対象日と一致するものを候補化する。
ファイル名に`private`/`internal`/`personal`/`confidential`/`secret`/`credential`や
OSユーザーディレクトリらしきパスを含むものは候補から除外する。

**設計上の制約**: 画像を自動で本文へ埋め込むことは行わない。テキストベースのスクリプトには
画像のピクセル内容(映り込んだプライベートUI・個人情報等)を判定する手段がないため、
`screenshot_candidates`としてfrontmatterに列挙するに留め、実際に使うかどうかの判断は
昇格時の人によるレビューに委ねる。

## 18. Related Articles(`scripts/devlogkit/related.py`)

`_articles/`の`status: ready`な記事から、タイトル・category・primary_keyword・
search_intentのキーワード(日本語・英数字とも)を抽出し、当日のcommit件名・関数名・
クラス名との重複語が2語以上ある記事のみを関連記事候補とする(最大3件)。0件なら
「関連記事なし」のまま出力し、無理に内部リンクを作らない(Step11)。

## 19. 二段階構造とPromotion Gate

```
generate-devlog.py --write   ->  drafts/<slug>.md (status: draft)
mark-devlog-reviewed.py      ->  reviewer_status: pass|fail を記録(人/セッションのレビュー結果)
promote-devlog.py <draft>    ->  _articles/<slug>.md (status: ready)
```

`promote-devlog.py`は以下の**すべて**を満たさない限り昇格を拒否する。

- `status: draft`である
- `publish_decision`が`DRAFT_ONLY`または`AUTO_PUBLISH_CANDIDATE`である(`SKIP`/`BLOCKED`は拒否)
- `reviewer_status`が`pass`である

`reviewer_status`は`generate-devlog.py`が**絶対に自動設定しない**フィールドであり、
`mark-devlog-reviewed.py`という別スクリプトを人(またはこのセッションのindependent-reviewer
プロセス)が明示的に実行した場合のみ`pass`になる。これにより、Quality Scoreがどれだけ
高くても、スコアだけでは`_articles/`へ昇格できない設計になっている
(2026-08-29のdrafts誤公開インシデントを踏まえた、意図的な安全側の設計)。

promotionはファイル移動とfrontmatter書き換えのみを行い、Git操作(add/commit/push)は
一切行わない。commit/pushは引き続き人が明示的に行う既存の運用を維持する。

## 20. drafts多層防御

Jekyll `exclude:`設定(`_config.yml`)への依存だけに頼らない、以下の追加防御層を実装した。

- `scripts/validate-site.py`の`check_drafts_excluded`(Phase 1で追加済み): `_config.yml`の
  ソーステキストに`- drafts/`が存在するかを静的チェック
- `scripts/verify-build-output.py`(Phase 2で追加): **実際のJekyllビルド出力**
  (`_site/`)を検査し、(a) `_site/drafts/`・`_site/config/`が存在しないこと、
  (b) `_site/articles/<slug>/`という公開URLが必ず`_articles/<file>.md`の
  `permalink:`と対応していること(対応するsourceがないURLは、draftや設定ファイルなど
  意図しない場所からビルドされた証拠として検出する)、(c) `sitemap.xml`内のURLも同様に
  `_articles/`で裏付けられることを検証する。`.github/workflows/pages.yml`の
  `Build with Jekyll`直後、`Upload artifact`の前に実行され、1つでも失敗すればCI全体を
  失敗させる

この2層構成により、「`_config.yml`の設定ミス」という原因に限定されない、より一般的な
「意図しないURLが公開された」というクラスの事故を検出できる。

## 21. Observability(`scripts/devlogkit/observability.py`)

実行ごとに`devlog-logs/<project>.jsonl`(Git管理外。`.gitignore`参照)へ1行追記する。
記録項目: `date`/`project`/`commits_found`/`notable_commits`/`security_filtered`/
`quality_score`/`decision`/`reason`/`draft_path`/`logged_at`。書き込み前に
`SECRET_VALUE_PATTERNS`で全フィールドを再スキャンし、万一該当すれば`[REDACTED]`に
置換する(上流に秘密情報が渡らない設計だが、念のための多重防御)。

将来のLearning(Step21)は、この観測ログとGA4/Search Consoleの記事別パフォーマンスを
突き合わせる分析基盤として拡張できるが、Phase 2では分析基盤自体は作り込まない
(JSONLを貯めるところまでに留める)。

## 22. Multi-project対応

`config/devlog-projects.yaml`で`enabled: true`かつ`public: true`のprojectは
`allowlist.enabled_public_projects()`で列挙され、`run-daily-devlog.py`が順番に処理する。
1つのprojectで例外が発生しても`try/except`で捕捉してログに記録し、次のprojectの処理を
継続する(1project失敗が全体を止めない設計。`scripts/test_devlog.py`の
`TestMultiProjectFailureIsolation`で検証)。現時点で`enabled: true`は`ai-tech-lab`のみ。

## 23. Old vs Phase 2の比較

このリポジトリ自身の3日分の実データで比較した(実際に記事を公開してはいない。
比較はいずれもdry-run/write出力の内容比較)。

| 日付 | commit概要 | Phase1出力 | Phase2出力 | Quality Score |
|---|---|---|---|---|
| 2026-08-23 | 記事へのAffiliate追加2件 | commit件名を英語のまま列挙するのみ | (dedup対象、Phase1のdraftが既存のため再生成せずSKIP) | - |
| 2026-08-22 | 記事2本を公開 | commit件名の機械的な列挙 | タイトル日本語化(`ESP32ロードセル配達物detectorを公開しました`)、実際の記事本文から動機・役割分担を引用した抜粋、関連記事として第6号を自動検出 | 67(DRAFT_ONLY) |
| 2026-08-06 | 創業日、7 commit(README・CLAUDE.md・記事公開等) | commit件名の機械的な列挙 | README/各種mdファイルの追加プロセス(ブログの目的・方針)を抜粋、CLAUDE.mdのバージョン変更を「変更前後」として提示 | 57(SKIP) |

**評価**:
- 日本語自然さ: Phase2は複数語の実際の技術用語(ロードセル・センサー・検知等)を正しく
  変換でき、Phase1の「英語がそのまま日本語文に埋め込まれる」問題を実際のcommit履歴の
  過半で解消した。ただし辞書に無い語彙(例: "claude code"のような複合名詞)は
  読みにくい形になるため、カバレッジ閾値でフォールバックする設計を維持している
- 技術理解: docs抜粋・変更前後ペアにより、commit件名だけでは分からない「何が
  変わったか」を実際の文章から示せるようになった
- Fact fidelity: 抜粋・前後ペアはすべて実際のdiff行から抽出しており、Owner体験や
  動機の創作は一切行っていない(テンプレート自体がBug Fix/Performance/Architecture
  タイプで「未確認」の明記を強制する構造)
- SEO: タイトル・primary_keywordの日本語化により検索クエリとの親和性は改善したが、
  依然として機械的な言い回しの域を出ない(完全な自然文生成にはLLM等の追加ステップが
  必要で、Phase 2ではhallucinationリスクを避けるため意図的に採用していない)
- 読者価値: 「Git logをMarkdownにしただけ」からは脱却したが、「開発者本人が書いた記事」
  と見分けがつかない水準ではない。現状のQuality Scoreは、AUTO_PUBLISH_CANDIDATE
  (80点以上)に達する日がこの3日間では出ておらず、現行の閾値・生成ロジックでは
  「安全側に倒れて多くの日がDRAFT_ONLY以下に留まる」設計になっていることを確認した
- Security: 3日間とも3つのgate(Security/Privacy/Fact)はすべてPASS。意図的に
  secretを含むテストケース(`scripts/test_devlog.py`)は正しくBLOCKED相当の判定になった
- 重複: 2026-08-23は既存draftとのdedupが正しく機能し、再生成されなかった
- Hallucination: 生成された全文を目視確認した限り、Gitから確認できない体験・理由・
  数値は含まれていない(テンプレートが明示的に「未確認」と書くよう強制するため)
