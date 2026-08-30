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

# Phase 2.5: Auto-Publish Readiness Sprint(2026-08-31〜)

Phase 2で「型はできたが、実データでAUTO_PUBLISH_CANDIDATEが一度も出ていない」状態
だった点を検証するための監査サイクル。**閾値(80点)は一切変更していない**。

## 24. Evidence Layer拡張(`scripts/devlogkit/sanitize.py` / `templates.py`)

Sanitized Change Summary Layer(denylist→secret-scan→sanitizeの順序は不変)に、
安全に抽出できる情報を追加した。

- 見出し(`#`/`##`等)の追加検出、frontmatter/設定ファイルの**キー名のみ**の変更検出
  (値は転記しない)、ファイル単位での関数/クラス/テスト名のグルーピング表示
- 変更前後ペア抽出を、共通接頭辞を考慮した窓表示(`_highlight_diff_pair`)に変更し、
  「見た目は同じだが実は違う」長い行の誤表示を修正
- docs抜粋抽出をhunk単位にし、別々のhunkの行を1つの段落に連結してしまう不具合を修正
- kramdownのIAL構文(`{: width="..."}`)やHTML+Liquidが混在する行、コードフェンス内部の
  行が「地の文」として誤って引用される不具合を修正(`_is_mostly_markup`による判定に変更)
- テスト追加を検知した場合、「実行結果(PASS/FAIL)はGit履歴からは確認できないため
  本記事では言及していません」という限定を明記する検証セクションを追加(テストが
  ある事実と、テストが通った事実を混同しない)
- 見出し・設定キー・README抜粋を、当日全体のフラットなリストではなくファイル単位で
  帰属表示するよう変更(独立レビューで、異なる2記事の見出しが出典なしに1つのリストへ
  混在し読者が誤解しうる点を指摘されたための修正)
- 内部の企画・SEOラベル(`検索意図:`/`search_intent`/`primary_keyword`)を含む行を
  docs抜粋の抽出対象から除外(`INTERNAL_LABEL_LINE_RE`)。独立レビューで、
  `CONTENT_PLAN.md`(次記事の企画リスト)内のこのラベル付き行が、生成記事の
  「README/ドキュメントの追記内容」として読者にそのまま提示されてしまう実例が
  見つかったため(BLOCKER判定→修正)
- 見出しレベルのみの変更(例: `# X` → `## X`)を「見出しの新規追加」として重複計上
  しないよう修正(同一hunk内で削除された見出しと同じテキストの見出しは"追加"扱いから
  除外)。独立レビューで、同じ見出しが「新規追加」と「変更前後」の両方に矛盾した形で
  提示される実例が見つかったため

いずれも読み取り対象はGitのdiff/commit metadataのみで、値そのものを抽出する場合は
既存のsecret-scanを必ず経由する(パイプラインの境界は変更していない)。

## 25. 分類ロジックの修正(`scripts/devlogkit/classify.py`)

commit件名ベースの分類(BUGFIX/PERFORMANCE/ARCHITECTURE/UI/FEATURE)を、ファイル拡張子
ベースのフォールバックより常に優先するよう順序を修正した。また、UIフォールバックが
「スタイル系ファイルが1件でもあれば発火する」実装になっており、19ファイル変更中
CSSが1件だけのGA4/アフィリエイト機能追加commitが「デザインに関する変更」に誤分類されて
いた実例を確認したため、スタイル系ファイルが変更ファイルの**過半数**を占める場合のみ
UIフォールバックが発火するよう修正した(`UI_FILE_RATIO_THRESHOLD = 0.5`、比較は
「過半数」の字義どおり`>`。独立レビューで実装が`>=`(ちょうど50%でも発火)になっており
文書表現と食い違っている点を指摘され修正)。

## 26. 日本語タイトル生成の改善(`scripts/devlogkit/ja.py`)

- `VERB_MAP`/`JA_TERM_MAP`を、このリポジトリの実commit履歴に頻出する語彙(prevent/
  validate/detect/generate/compare/select/retry/isolate/promote等の動詞、validation/
  pipeline/draft/gate/score/promotion/hash/fingerprint等の名詞)で拡張した。プロジェクト
  固有の固有名詞を大量に追加することはしていない(既知の限界として維持)
- カバレッジ率が高くても、意味の単位が多すぎる(8語以上等)subjectを訳すと単語の羅列に
  なり読めない実例を確認したため、`MAX_TRANSLATABLE_TOKENS = 5`をカバレッジ率とは独立の
  上限として追加した。カバレッジ条件は`>= 0.6`に引き上げ(旧`>= 0.34`は緩すぎた)
- タイトル生成はその日の最初のcommitのsubjectだけでなく、当日の全notable commitを
  順に試し、最初に条件を満たしたものを採用するよう変更した(1件目が複雑すぎて訳せない
  場合でも、後続のcommitで自然な日本語タイトルが作れることがある)

## 27. Quality Score監査: 二重加点の発見と修正(`scripts/devlogkit/score.py`)

Step 8の監査観点(「同じEvidenceで複数軸に二重加点していないか」)に沿って全5軸を
手作業で洗い出した結果、`config_keys_changed`(frontmatter/設定キーの変更)が
Development ValueとTechnical Depthの**両方**で加点されており、Phase 2.5自身が新設した
「1シグナル・1軸」の設計原則(tests_addedのみが、Reader Value=読者への安心材料・
Technical Depth=エンジニアリング上の裏付け、という2つの異なる主張を支えるため意図的に
2軸で加点される唯一の例外)に反していることが判明した。

設定キーの変更単独は、関数/クラス/テスト追加や変更前後ペアと並べて「技術的な深さ」の
根拠にするには性質が異なる(実装コードの変更ではない)と判断し、Technical Depthの
シグナル一覧から`config_keys_changed`を除外した(Development Valueには残す)。

この修正は**スコアを既存の80点到達日に合わせて調整したものではなく**、逆にその結果、
Phase 2.5の作業中に一時的にAUTO_PUBLISH_CANDIDATEとして観測されていた3日分
(2026-08-08=82点、2026-08-20=81点、2026-08-30=80点)が、修正後はいずれも79点
(DRAFT_ONLY)に下がった。3日とも下落幅は、修正前にTechnical Depthへ計上されていた
`config_keys_changed`分にちょうど一致しており、この二重加点が閾値超えの決め手になって
いたことを裏付けている。閾値自体は変更していない(Step 13の禁止事項どおり)。

## 28. Content Fingerprint とレビュー来歴(`scripts/devlogkit/frontmatter.py`)

`compute_content_fingerprint(frontmatter, body)`は、`status`/`order`/`reviewer_*`系
フィールド(レビュー前後で正当に変わる、または来歴自体を記録するためのフィールド)を
除いたfrontmatter全体とbodyをJSON化してSHA-256ハッシュ化したもの。`title`・
`description`・`source_commits`・`publish_decision`・本文を含め、それ以外のすべての
フィールドと内容がこのハッシュでロックされる。

- `mark-devlog-reviewed.py --pass`が、`reviewer_method`(自由記述。個人名は記録しない)・
  `reviewed_at`(UTC ISO8601)・`reviewed_content_hash`をこの順で記録する
- `promote-devlog.py`は、`reviewer_status: pass`に加えて、**現在のファイル内容から
  再計算したフィンガープリントが`reviewed_content_hash`と一致すること**を必須条件とした。
  これは既存のSecurity/Privacy再スキャン(既知のパターンにしか反応しない)より強く、
  レビュー後に1文字でも本文・frontmatterが変わっていれば理由を問わず昇格を拒否する

**実機検証**(`scripts/test_devlog.py`の自動テストに加え、本ラウンドで手動でも実施):
`drafts/`配下で本文末尾に1文追加したコピーに対し`promote-devlog.py`を実行したところ、
「content fingerprintが一致しません」というエラーで昇格が拒否されることを確認した
(改変前のオリジナルは正常に昇格できることも合わせて確認。手順の詳細は本ラウンドの
作業ログを参照)。

なお、この改修中に`frontmatter.split_frontmatter()`が本文の先頭改行を除去しておらず、
読み込み→書き込みを1往復するたびに本文へ改行が2つずつ蓄積する不具合(フィンガープリントの
冪等性を壊す)を発見し、`.lstrip("\n")`で修正した。フィンガープリント機能とは独立に
存在していた実バグで、修正しなければ「変更していないファイルなのにハッシュが一致しない」
という誤検知を起こしうるものだった。

さらに独立レビューで、`split_frontmatter()`本体がテキスト中の`"---"`という3文字を
リテラル検索して分割している(`text.split("---", 2)`)ため、`title`等の値に`"---"`が
含まれると(例: commit件名`"docs: replace === with --- style"`がja.pyの英語フォール
バック経由でそのまま埋め込まれた場合)誤った位置で分割されうるというMAJORが見つかった。
`FRONTMATTER_DELIMITER_RE`(行全体が`---`である行のみにマッチする正規表現、
`re.MULTILINE`)で先頭2つの区切り行を探す実装に置き換えて修正し、値に`---`を含む
frontmatterのラウンドトリップを回帰テストに追加した。

### Fact Gateのpromotion時再検証(`scripts/promote-devlog.py`)

Content Fingerprintは「レビュー後に内容が変わっていないこと」は保証するが、
「レビューされた内容がそもそも本物のGit履歴に裏付けられていること」までは保証しない。
独立レビューでこの点がBLOCKERとして指摘された(既存テストの手書きfixtureが、
実在しないcommit hash`"abc1234"`を含むdraftでも`reviewer_status: pass`とハッシュ一致
さえ揃えば昇格に成功することを、テスト自身が証明していた)。

対策として、`promote-devlog.py`にFact Gateのpromotion時再検証を追加した(content
fingerprintチェックの直後、Security/Privacy再スキャンの直前)。

- `generated_from_git`が`true`であること
- `source_project`が`config/devlog-projects.yaml`のallowlistに存在し、かつ
  `enabled`/`public`とも`true`であること(生成時だけでなく昇格時にも再確認するため、
  生成後にプロジェクトが無効化された場合も検出できる)
- `source_commits`が空でないこと、かつ**そのすべてのhashが実際に対象リポジトリの
  commitとして存在すること**(`gitmeta.commit_exists()`、`git cat-file -e <hash>^{commit}`
  で検証)

いずれか1つでも満たさない場合はpromotionを拒否する(`scripts/test_devlog.py`の
`test_promotion_rejected_when_source_commit_does_not_exist`で、正当にレビュー済み・
フィンガープリント一致のdraftであっても、存在しないcommit hashが1つでも含まれていれば
拒否されることを確認)。

この初版実装には、`git cat-file -e <hash>^{commit}`がコミットhashだけでなく`HEAD`・
ブランチ名等のシンボリック参照も解決してしまうという抜け穴が2回目の独立レビューで
見つかった(`source_commits: ["HEAD"]`のようなdraftが、hashの形をしていないにも
かかわらず「実在するcommitである」と誤判定されうる)。`gitmeta.commit_exists()`に
16進hash形式(7〜40文字)であることの事前チェックを追加して修正し、
`test_promotion_rejected_when_source_commit_is_a_symbolic_ref`で回帰を防止した。

また、`frontmatter.split_frontmatter()`と全く同じ「`"---"`部分文字列で分割」バグが、
`scripts/validate-site.py`(Publication Gate/CIで使用)と`scripts/devlogkit/related.py`
(関連記事マッチングで使用)にそれぞれ独立実装として重複していたことも2回目のレビューで
見つかった。両方とも独自実装を削除し、`devlogkit.frontmatter.split_frontmatter`を
共有で呼び出す形に統一した(同じ修正を3箇所に別々に適用する重複保守を避けるため)。

## 29. 10日分の実データ評価と結論

このリポジトリ自身のGit履歴から、既存のdedup(`source_commits`)と衝突しない10日分を
評価した(実際に記事ファイルを大量生成することはせず、`pipeline.run()`を直接呼び出す
dry-run相当の評価のみ)。

| 日付 | commit概要 | Score | 判定 |
|---|---|---|---|
| 2026-08-06 | 創業日、7 commit(型がGENERIC) | 67 | DRAFT_ONLY |
| 2026-08-07 | 4 commit(1件trivial除外) | 53 | SKIP |
| 2026-08-08 | Arduino記事へのビジュアルガイド追加・レイアウト改善・IDEインストール記事公開、3 commit | 79 | DRAFT_ONLY |
| 2026-08-12 | 2 commit | 64 | DRAFT_ONLY |
| 2026-08-20 | ESP32ロードセル関連、1 commit | 79 | DRAFT_ONLY |
| 2026-08-21 | 1 commit | 61 | DRAFT_ONLY |
| 2026-08-22 | 記事2本公開 | 67 | DRAFT_ONLY |
| 2026-08-23 | (既存draftとdedup、再評価対象外) | - | SKIP(dedup) |
| 2026-08-24 | 1 commit | 69 | DRAFT_ONLY |
| 2026-08-30 | Dev Log自動化PoC、5 commit | 79 | DRAFT_ONLY |

**結論(Step 13の分類に従う)**: 上記の27節のスコア監査修正を適用した結果、この
10日間では**80点以上(AUTO_PUBLISH_CANDIDATE)に到達した日は0件**だった。最も近い
3日(2026-08-08/2026-08-20/2026-08-30)はいずれも79点で1点差だが、この1点は
二重加点の除去分そのものであり、それを埋め合わせるための閾値変更・スコア調整は
行っていない(Step 13で明示的に禁止されている「今回の目的のためだけの閾値変更」に
該当するため)。

原因の分類:
- **(A) 生成器の抽出能力がまだ不十分**: 本リポジトリは記事(Markdown)中心のサイトで
  あり、Technical Depth軸が前提とする「関数/クラス/テスト」シグナルは、記事執筆や
  レイアウト調整が中心の日にはそもそも発生しにくい。config_keys_changedを含めれば
  79点は80点に届いていたが、27節の理由によりTechnical Depthへの計上は妥当でないと
  判断した。記事中心のリポジトリに合ったTechnical Depth相当の代替シグナル
  (例: テンプレート構造の変更、before/afterペアの複数件評価等)を今後の別ラウンドで
  検討する余地がある
- **(C) 一部の日の開発規模自体が小さい**: 2026-08-07/12/21等はnotable commitが1〜3件
  程度で、Development Value・SEO Potentialの伸びしろが構造的に小さい

閾値変更(D)は、今回の10日分布だけでは正当化しない(1点差の近似は複数日あるが、
「10日以上のデータに基づく」という条件は満たしても、「今回の作業の都合で下げる」
ことと区別がつかないため、本ラウンドでは見送り、Owner判断待ちの論点として残す)。

## 30. Promotion E2E実証(実データ、実験後に削除)

2026-08-08のdraftで2回実施した。1回目は24節の記事品質修正・27節のスコア監査直後
(Fact Gateのpromotion時再検証を実装する前)に実施し、`mark-devlog-reviewed.py --pass
--method "manual-self-review-substitute"`で記録した上でtamper拒否・正常昇格・
実験成果物の削除を確認した。その後、独立レビューで生成記事のBLOCKER(28節参照)と
Fact Gate自体の抜け穴(28節「Fact Gateのpromotion時再検証」参照)が見つかり、
両方を修正したため、**最終コードに対する2回目のE2Eを実施し直した**(こちらが
最終的な実証結果)。

1. 修正後のコードで2026-08-08のdraftを再生成(`--write`、score=79、DRAFT_ONLY。
   検索意図ラベル漏洩・見出しの自己矛盾がいずれも解消されていることを本文で確認)
2. `mark-devlog-reviewed.py --pass --method "independent-reviewer(BLOCKER1件検出→
   修正、修正内容を手動で再確認)"`でレビュー来歴を記録
3. レビュー記録後に本文へ1文追加したコピーに対し`promote-devlog.py`を実行 →
   content fingerprint不一致で拒否(エラーメッセージを確認)
4. 改変していないオリジナルに対し`promote-devlog.py`を実行 → 新設のFact Gate
   (source_project/source_commits の実在性チェック)を含めすべてのゲートを通過して
   `_articles/`への昇格に成功し、`scripts/validate-site.py`も全項目PASS
5. 実験目的の昇格だったため、確認後に`_articles/devlog-ai-tech-lab-2026-08-08.md`を
   削除し、本番`_articles/`・`drafts/`に実験成果物を残していないことを`git status`で
   確認した

DRAFT_ONLY判定の記事で実証した(AUTO_PUBLISH_CANDIDATEは29節のとおり0件だったため)。
`promote-devlog.py`はDRAFT_ONLY/AUTO_PUBLISH_CANDIDATEのどちらも同じゲート
(reviewer_status=pass + content fingerprint一致 + Fact Gate + Security/Privacy
再スキャン)で扱う設計であり、この実証はメカニズム自体の健全性を確認するものである。

## 31. 既知の未解決事項(次ラウンドへの申し送り)

2回にわたる独立レビューで指摘されたが、本ラウンドでは意図的に修正を見送った項目
(quality-developmentのIterative Refinement終了条件に従い、無限に修正ループを
続けるのではなくBLOCKEDとして明示的に記録する)。

- **[MAJOR] Evidence Strength軸(`score.py`)の他軸との重複**: `evidence`リストは
  functions/classes/tests/docs/headings/config_keys/behavior_pairsの各シグナルから
  機械的に1件ずつ追加されるため、Evidence Strengthは実質的にこれらの軸と強く相関し、
  27節で修正した「1シグナル・1軸」の原則を完全には満たしていない。軸の再設計は
  スコア全体の再検証(10日分の再評価・記事の再生成・レビュー)を要する規模のため、
  次ラウンドの課題とする
- **[MAJOR] `_extract_single_line_replacement`(`sanitize.py`)のfrontmatter境界を
  跨いだ誤ペアリングの可能性**: `_filter_out_frontmatter_lines`は追加(`+`)行のみを
  frontmatter範囲で除外し、削除(`-`)行は素通りさせるため、同一hunk内でfrontmatterの
  折返し継続行の削除と本文プロースの追加が同時に起きた場合、無関係な文字列同士が
  「変更前後」としてペア化される可能性が理論上残る。狭いcontext(`-U1`)かつ複数条件が
  同時に揃う必要がある稀なケースであり、次ラウンドで`_filter_out_frontmatter_lines`の
  削除行側にも同様の範囲追跡を拡張することを推奨する
