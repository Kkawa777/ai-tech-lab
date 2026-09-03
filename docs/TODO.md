# TODO.md

現在の開発状態のみを保持する。作業ログではなく、更新のたびにこの内容を上書きする。
背景・原則・優先順位は正本(ROADMAP.md / BRAND.md / CONTENT_PLAN.md / docs/PROJECT_PRINCIPLES.md)を
参照する。ここに新しい方針や原則を書かない。

開発Agentは独自のPlan/TODOファイルを作らず、状態はこのファイルに集約する。手順は
[`.claude/skills/quality-development/SKILL.md`](../.claude/skills/quality-development/SKILL.md)
のState Updateステップを参照。**履歴ファイルにしない**: 完了項目は直近1〜2 Batchのみ、
Blockedは現在有効なものだけを残す。それより古い完了履歴はGit historyに委ね、ここでは削除する。

**Task ID(任意)**: 複数手順にまたがる意味のあるBatchには`TASK-NNN`のような短いIDを振ってよい
(必須ではなく、[`knowledge/`](../knowledge/README.md)側のdecisions/lessons/revenueから
相互参照する追跡価値がある場合のみ)。**Evidence**: commit hash・レビューサイクル数
(BLOCKER/MAJOR件数)・validation結果など、完了の根拠となる情報は「Evidence:」として書く
(これは既存の運用を追認するラベルであり、新しい記録要求を増やすものではない)。

## In Flight

(現在実行中のTaskなし)

## Completed

- Dev Log自動化 Phase 2.7(A-grade Article Quality Sprint)完了。目的: Phase 2.6で
  AUTO_PUBLISH_CANDIDATEに到達した2026-08-08(82点)・2026-08-20(81点)の2記事
  (いずれも独立レビューでグレードB)を、スコアを上げずに人手修正不要のグレードAへ
  引き上げる(汎用的なgenerator改善のみ、特定2記事のハードコード禁止)。変更:
  `scripts/devlogkit/ja.py`("and"の中黒〈・〉変換・未マッピング語の大文字保持
  `KNOWN_ACRONYMS`)、`templates.py`(`_select_headline_phrase`共有化でtitle/
  description言語不整合を構造的に解消、`derive_topic_keyword`でprimary_keyword/
  search_intentを記事固有化、numbered-bold-title excerptノイズ除外、
  `_changed_files_section`のcommitスコープ拡張、`_change_composition_overview`
  機械的カウント文の新設、README/変更前後セクションへのcommit hash帰属追加)、
  `sanitize.py`(`_extract_single_line_replacement`のfrontmatter境界問題を解消
  =§31/§37からの持ち越し1件を解消)、`score.py`(Evidence Strength軸のbaseline/
  evidence件数加点の配分を調整し他軸との重複を部分的に緩和=§31/§37の持ち越し
  もう1件を部分対応。完全な再設計ではない)、`pipeline.py`(description/
  primary_keyword/search_intentの呼び出し側統合)。`docs/devlog-policy.md`39-44節に追記。
  independent-reviewerを5サイクル実施(1周目: 両記事B級判定、2周目コード:
  BLOCKER1〈templates/パス重複、Phase2.6由来〉・MAJOR1〈description言語不整合再発〉
  →修正、3周目: 新設した機械的カウント文自体の集計がsanitize.pyのMAX_ITEMS_PER_LIST
  切り詰めと詳細セクションの生データの不一致でBLOCKER〈8件と主張し実際は9件〉→
  カウント元をper_file_signals等の生データに統一して修正、4周目: README/変更前後
  セクションにcommit帰属がなく異なるファイル・commitの偶然の文言一致が自己矛盾に
  見えるBLOCKER懸念→両セクションに帰属追加、5周目: 見出し自己矛盾はBLOCKER 0を
  確認、ただしprimary_keyword/titleの自然な検索クエリとしての品質はMAJOR
  1件として両記事とも未解消)。`scripts/test_devlog.py`79/79 PASS(58→79、21件
  新規追加)、`validate-site.py`全項目PASS、`git diff --check`問題なし。Promotion
  E2E・tamper-attack実証を両記事で実施(reviewer_status: pass記録→改変コピーは
  拒否→未改変オリジナルは全ゲート通過で`_articles/`昇格に成功→実験後に削除、
  本番`_articles/`/`drafts/`に残留物なしを確認)。**結論**: BLOCKER 3件・複数の
  MAJORを発見・修正し記事の事実性・整合性・可読性は大きく向上したが、
  primary_keyword/titleの検索意図に基づく自然さは「LLMを使わない決定論的
  パイプラインの設計上の境界」と判断し、次のOwner判断を申し送り(A)人による
  最終確認・書き換え工程を明示的に維持する(既存のDev Log Gateの想定どおり)、
  (B)強いガードレール付きのLLM支援キーワード提案ステップを別途検討する。
  **READY_FOR_PHASE_3: NO**(2記事ともグレードB・MAJOR1件残存のため)
- Dev Log自動化 Phase 2.6(Technical Depth軸拡張)完了。目的: Phase 2.5が「AUTO_PUBLISH_
  CANDIDATE 0件」の主因とした、Technical Depth軸がPython/JS/Go向けfunctions/classes/tests
  正規表現しか見ておらずこのリポジトリの実作業(記事執筆・Jekyll layout/include/
  stylesheet engineering)を評価できていない問題を是正する(閾値80点は変更禁止)。変更:
  `scripts/devlogkit/sanitize.py`(`structural_files_changed`シグナル新設、`_layouts/`・
  `_includes/`・CSS系拡張子のみ対象、`not is_markdown`で他軸との排他性を保証。GFM
  タスクリスト行・複数行HTMLコメントのdocs抜粋除外も追加)、`score.py`
  (`score_technical_depth`を5種×4点に再配分)、`classify.py`(`DAY_TYPE_JA_LABEL`辞書で
  primary_keywordの日本語化)、`templates.py`(`translated_or_original`でdescription/
  primary_keywordもtitleと同じ翻訳判定を通す)、`pipeline.py`(上記の呼び出し側統合)。
  `docs/devlog-policy.md`32-38節に追記。independent-reviewerをコード2サイクル・生成記事
  1サイクル実施(1周目コード: 一部の設計主張を暫定OKと判定、2周目コード: BLOCKER1
  [`templates/`が`is_markdown`抽出経路と重複し他軸二重加点]・MAJOR2[4→5種の再配分による
  一部日の退行が未開示・devlog-policy.md未更新]を検出→修正、記事: BLOCKER0だが
  「81点/AUTO_PUBLISH_CANDIDATE」がdevlog-policy.mdの旧記述と矛盾〈ドキュメント未更新が
  原因、指摘3と同根〉・MAJOR2[description/primary_keywordの未翻訳一貫性欠如、
  Markdownタスクリスト行の無framing混入]を検出→修正。修正の過程でタスクリスト行の
  除外が別の潜在バグ(複数行HTMLコメントの1行目が次点候補として混入)を顕在化させ、
  追加修正)。`scripts/test_devlog.py`58/58 PASS(構造ファイル信号・タスクリスト/
  HTMLコメント除外・description翻訳一貫性・テンプレート二重加点防止の回帰テストを追加)、
  `validate-site.py`全項目PASS、`git diff --check`問題なし。**結論**: 10日間の実データ
  再評価で2026-08-08(82点)・2026-08-20(81点)が新たにAUTO_PUBLISH_CANDIDATEへ到達
  (79点だった3日のうち2日。閾値は変更していない)。両記事とも独立レビュー修正後に
  グレードB(可読・事実に忠実・ハルシネーションなし。title/description等の完全な自然文
  生成、および断片の要約文非生成という設計トレードオフのみ残存)。Promotion E2E・
  tamper-attack実証を両記事で実施(reviewer_status: pass記録→改変コピーは拒否→
  未改変オリジナルはFact Gate含む全ゲート通過で`_articles/`昇格に成功→実験後に削除、
  本番`_articles/`/`drafts/`に残留物なしを確認)。**READY_FOR_PHASE_3の再判定は次の
  commit/push完了後に実施**。§31から持ち越しの未解決MAJOR2件(Evidence Strength軸の
  重複、frontmatter境界のペアリング問題)は引き続き次ラウンド送り
- Dev Log自動化 Phase 2.5(Auto-Publish Readiness Sprint)完了。目的: 「Gitから生成した
  記事が人の手直しなしで公開候補になる」ことを実データで証明する(閾値80点は変更禁止)。
  変更: `scripts/devlogkit/`の`sanitize.py`(見出し/設定キー/README抜粋の抽出・帰属を
  拡張、内部SEOラベル`検索意図:`等の漏洩除外、見出しレベル変更の二重計上防止)、
  `score.py`(`config_keys_changed`のDevelopment Value/Technical Depth二重加点を監査・
  修正)、`classify.py`(UI判定を過半数厳格化`>`)、`ja.py`(辞書拡張・
  `MAX_TRANSLATABLE_TOKENS=5`)、`templates.py`(ファイル別帰属表示)、
  `frontmatter.py`(Content Fingerprint `compute_content_fingerprint`、
  `split_frontmatter`を`"---"`部分文字列一致から行単位の正規表現へ修正)、
  `gitmeta.py`(`commit_exists`、hash形式チェック付き)、`promote-devlog.py`
  (Fact Gateのpromotion時再検証: `source_project`のallowlist再確認+`source_commits`
  全件の実在確認)、`mark-devlog-reviewed.py`(`reviewer_method`/`reviewed_at`/
  `reviewed_content_hash`記録)、`validate-site.py`・`related.py`(重複していた
  `split_frontmatter`実装を`frontmatter.py`の共有実装に統一)。`docs/devlog-policy.md`
  24-31節・`docs/publish-checklist.md`に追記。independent-reviewerをコード2サイクル・
  生成記事1サイクル実施(1周目コード: BLOCKER1[Fact Gate未検証]・MAJOR1[frontmatter
  split](その他MINOR2)を検出→修正、記事: BLOCKER1[企画ラベル漏洩]・MAJOR4を検出→
  修正、2周目コード: MAJOR2[hash形式未検証・split_frontmatter重複実装]を検出→修正、
  最終確認)。`scripts/test_devlog.py`45/45 PASS(Fact Gate/tamper検知/hash形式等の
  回帰テストを追加)、`validate-site.py`全項目PASS、`git diff --check`問題なし。
  Promotion E2E・tamper-attack実証を最終コードに対して再実施(2026-08-08の実dataで
  reviewer_status: pass記録→本文改変コピーは拒否→未改変オリジナルはFact Gate含む
  全ゲート通過で`_articles/`昇格に成功→実験後に削除、本番`_articles/`/`drafts/`に
  残留物なしを確認)。**結論**: 10日分の実データ再評価の結果、AUTO_PUBLISH_CANDIDATE
  (80点以上)はスコア監査後は0件(直前まで82/81/80点だった3日が、二重加点修正分
  ちょうど79点に下落。閾値は変更していない)。原因は主に(A)記事中心のこのリポジトリでは
  Technical Depth軸が前提とする関数/クラス/テストのシグナルが構造的に出にくいこと、
  (C)一部の日の開発規模自体が小さいこと。**READY_FOR_PHASE_3: NO**(「実データで
  score≥80かつA評価の記事が最低1件」という成功条件が未達のため。それ以外のFact/
  Security/Privacy/tamper耐性・テスト・validationはすべてPASS)。既知の未修正MAJOR2件
  (Evidence Strength軸の他軸との重複、`_extract_single_line_replacement`のfrontmatter
  境界を跨ぐ誤ペアリングの可能性)は`docs/devlog-policy.md`31節に記録。commit `551496d`
  (`feat: improve Dev Log auto-publish readiness`)としてpush、GitHub Actions
  build/deploy成功、本番確認(devlog draft/config非公開のまま、既存記事・ホームに影響
  なし)まで完了

- Dev Log自動生成 Phase 2(品質モデル・Sanitized Change Summary Layer・安全な自動公開能力)を実装。
  新規: `scripts/devlogkit/`パッケージ(allowlist/gitmeta/security/sanitize/classify/score/ja/
  templates/related/screenshots/observability/frontmatter/pipeline)、`scripts/promote-devlog.py`
  (drafts/→_articles/昇格の唯一の経路。status/publish_decision/reviewer_status全部一致+
  promotion時点の内容再スキャンPASSが必須)、`scripts/mark-devlog-reviewed.py`(`reviewer_status:
  pass`を書ける唯一のスクリプト。generate側は絶対に自動設定しない)、`scripts/run-daily-devlog.py`
  (複数project対応・1project失敗の分離)、`scripts/verify-build-output.py`(実際のJekyllビルド
  出力`_site/`を検査し、`.github/workflows/pages.yml`のBuild直後に実行、drafts二重公開インシデントの
  多層防御)、`scripts/test_devlog.py`(32テスト)。変更: `scripts/generate-devlog.py`
  (devlogkit基盤に全面刷新、`--auto`モード追加)、`docs/devlog-policy.md`(Phase2章13-23節追加)、
  `docs/publish-checklist.md`(Dev Log Gateへ3項目追加)、`.gitignore`(`_site/`・`devlog-logs/`追加)。
  Sanitized Change Summary LayerはPhase1と異なりdiff内容を読むが、denylist→secret二重スキャンを
  通過した安全な範囲(関数/クラス/テスト名・frontmatter除外済みdocs抜粋)のみ抽出。Quality Score
  (5軸決定論的・0-100点)とSecurity/Privacy/Fact 3ゲート(最終テキスト独立再スキャン、1つでもFAILで
  スコアに関係なくBLOCKED)を導入。independent-reviewerを3サイクル実施(1周目: BLOCKER0・MAJOR3
  [YAML折り返し継続行のdocs_excerpts漏洩・promotion時の安全性再スキャン欠如・multi-project分離
  テストが実コード非経由]を検出→全修正→2周目: BLOCKER0・MAJOR0確認)。実データPoCとして
  `ai-tech-lab`自身の3日分(2026-08-06=57点SKIP、2026-08-22=67点DRAFT_ONLY、2026-08-23=既存
  draftとのdedupでSKIP)で比較し、AUTO_PUBLISH_CANDIDATE(80点以上)はこの3日間では到達しなかった
  ことを`docs/devlog-policy.md`に正直に記録。commit `aaf7f9b`(`feat: Dev Log Phase 2 - quality
  scoring and safe auto-publish pipeline`)としてpush、GitHub Actions build/deploy成功
  (新設の`Verify build output safety`ステップも実CI上でPASS)、本番確認(config/devlog-projects.yaml
  非公開・devlogドラフト記事は非公開のまま・既存記事/ホームに影響なし)まで完了。実験生成した
  draft(2026-08-22分)は昇格フロー自体のテストのみに使用し、テスト後に削除済み(`_articles/`への
  新規公開は行っていない)
- Claude Code開発基盤アップデート(Lead/Orchestrator・HANDOFF標準・Reusable Pattern Check)。
  既存構成(CLAUDE.md/quality-development/independent-reviewer/knowledge-management/
  parallel-worktree-development/停止条件)を壊さず3点のみ追加。変更: `CLAUDE.md`
  (「Lead / Orchestrator」節を新設=進行管理責務・HANDOFF標準・Reusable Pattern Checkのサブ項目、
  「開発基盤」節に2行追記)、`.claude/skills/quality-development/SKILL.md`(Step 9に
  Reusable Pattern Check〈判定値6種・NEW_SKILL_CANDIDATE 5条件〉を追加、Session Handoffに工程間
  HANDOFFのポインタ、参照ファイル一覧・フロー図を更新)、
  `.claude/skills/knowledge-management/SKILL.md`(「Reusable Pattern Checkとの連携」節=
  判定値→`knowledge/`昇格条件の対応)。新規: `.claude/skills/quality-development/references/
  handoff-format.md`(HANDOFFテンプレート+セッション内/永続ファイルの判断基準)。MASTER.mdは本repoに
  存在しないためCLAUDE.mdへ統合。independent-reviewer最終ゲート・Approval Gate(重大判断リスト)は
  非改変。過剰なAgent/Worktree並列化は未導入。independent-reviewer実施でBLOCKER0/MAJOR0/MINOR7
  (正本一元化の表記ねじれ・用語揺れ・LOWリスク省略条項・体裁)→全7件反映済み。commit `70b5c97`
  (`chore: add Lead/Orchestrator role, HANDOFF standard, and Reusable Pattern Check`)としてpush済み
- **インシデント対応**: Dev Log PoC commit(`90a72d5`)のpush直後、`drafts/`配下のdraft記事
  (`devlog-ai-tech-lab-2026-08-23.md`)がGitHub Pages上で実際に公開されてしまう事故が発生
  (約3〜4分間、`https://.../articles/devlog-ai-tech-lab-2026-08-23/`がHTTP 200で応答)。
  原因: `_config.yml`の`exclude`に`drafts/`を追加する変更が、実は一度もcommitされておらず
  (ローカル作業ツリーにのみ存在する状態が続いていた)、本番の`_config.yml`はdrafts/を
  Jekyllビルド対象外にしていなかった。`drafts/`はこれまで空だったため発覚しなかった潜在バグで、
  今回のPoCが`drafts/`へ初めて実ファイルを置いたことで顕在化した。commit `6c248bd`
  (`fix: exclude drafts/ from Jekyll build`)で`- drafts/`を正式にcommit・push・再deployし、
  該当URLがHTTP 404に戻ったことを確認。sitemap.xmlにも当該記事は含まれていない。露出時間が
  短く実害は限定的と判断するが、`drafts/`は今後も「Jekyll側の`exclude`設定に完全に依存する」
  設計のままである点は既知のリスクとして残る(second layer of defenseとして`_articles/`同様の
  自動チェックを`drafts/`にも設ける案は今後の検討課題)。
- Dev Log自動生成PoC(「開発したら勝手にブログ記事が生まれる」仕組みの第一歩)を実装。
  新規: `docs/devlog-policy.md`(正本ドキュメント)、`config/devlog-projects.yaml`
  (project allowlist、deny-by-default、現状`ai-tech-lab`のみenabled/public)、
  `scripts/generate-devlog.py`(Git履歴からdraft生成するCLI。diff本文は読まずcommit
  hash/subject/変更ファイル名/行数のみ使用。secret/trivial/mergeコミットの二重フィルタ、
  `_articles/`直接書き込み禁止、`source_commits`による冪等性)。変更: `_config.yml`
  (`config/`をJekyll exclude追加)、`docs/publish-checklist.md`(Dev Log Gate新設)、
  `docs/README.md`(索引追加)、`CLAUDE.md`(最重要ルールへdevlog例外条項を追記)、
  `scripts/validate-site.py`(`check_order_values`追加、18チェックに)、`.gitignore`
  (`__pycache__/`追加)。いずれも既存の無関係な未コミット差分とは`git apply --cached`
  によるhunk単位の分離stagingで混在を回避。independent-reviewerを2サイクル実施
  (1周目: BLOCKER1件[CLAUDE.mdへの例外条項欠如]・MAJOR8件[YAML生成バグ・secret正規表現の
  空白非対応・sibling project pathの誤り・trivialフィルタとdocsの不一致・order空欄時の
  Jekyll nil-sort事故リスク・タイトル英語直書きとSEO Gateの緊張・mergeコミット未対応、他]
  を検出→全修正→2周目: BLOCKER0・MAJOR3[secret正規表現一覧のdocs⇔実装再乖離・
  trivialメッセージ判定の非アンカーによる過検出・本State Update未記載]を検出→全修正)。
  実データPoCとして`ai-tech-lab`自身の2026-08-23分(commit 2件)を`drafts/
  devlog-ai-tech-lab-2026-08-23.md`へ`--write`済み(status: draft、`_articles/`へは
  未昇格)。評価: 仕組み・安全機構(allowlist・secretフィルタ・冪等性)は健全に機能するが、
  生成物自体は機械的な要約レベルで、タイトルは英語commit subject直書きのままSEO上は
  人力調整が必要。他project(ai-content-engine等)は公開可否未確認のため無効化のまま。
- 第7号(`_articles/esp32-rain-sensor-detection.md`、水検知センサーで雨を検知した話)を新規公開。
  Owner実体験インタビュー(動機・使用マイコンESP32・デジタル出力・屋外窓際設置・3Dプリンター製
  二重構造ケース・LINE/メール/Teams通知(サーバー保存なし)・誤検知/腐食/最終故障・使用中止・
  「今ならどう考えるか」は特になし、を確認)を経て執筆。ASIN`B07PVRWDSW`(水検知センサー)は
  Ownerが実使用品と確認済みのため`role: used`・CTA実装(`used=true`、`position="used-water-sensor"`)。
  independent-reviewerで2サイクル実施(1周目でBLOCKER1件[「コードについて」節が未確認事実を
  断定調で記載]を検出→修正→2周目でBLOCKER0/MAJOR0)。第3号記事の「雨検知への発展」段落(前方
  参照のまま保留していた箇所)を、この記事への実リンクに更新。commit `3221baf`(`feat: publish
  ESP32 rain sensor detection article`)としてpush、GitHub Actions build/deploy成功、公開後
  validation(HTTP 200/title/description/canonical/OGP/JSON-LD/H1 1個/GA4/Amazon URL
  `https://www.amazon.co.jp/dp/B07PVRWDSW?tag=aitechlab-22`/tag1回のみ/UTMなし/rel・target/
  data-affiliate-*属性/Affiliate Disclosure描画/第3・5・6号との内部リンク/sitemap反映)まで完了。
  公開URL: https://kkawa777.github.io/ai-tech-lab/articles/esp32-rain-sensor-detection/
- 収益化Sprint(Amazon Affiliate CTA/Disclosure、GA4、`amazon_click`計測、Search Console
  verification、`privacy.md`、画像CLS/LCP対応、`scripts/validate-site.py`)。independent-reviewer
  を4サイクル実施しBLOCKER/MAJOR 0を達成後、commit `8650da5`(`feat: launch monetization and
  analytics foundation`)としてpush・GitHub Actions build/deploy・公開後validation(HTTP/OGP/
  JSON-LD/GA4/Amazon CTA/キャッシュヘッダ実測)まで完了。公開URL:
  https://kkawa777.github.io/ai-tech-lab/ 。詳細な経緯はGit history側に委ね、ここには再掲しない
- quality-development開発プロセスBatch(Task Decomposition/Automated Validation/Independent
  Review/State Update等の品質基盤)、および本ファイルとの責務整合の見直し(`SKILL.md`・
  `docs/README.md`の`docs/TODO.md`セクション名の記述をIn Flight/Completed/Owner Action
  Required/Blocked/Next Upの実運用に合わせて統一、本ファイルの陳腐化した完了履歴を圧縮)。
  commit `37965c3`(`chore: improve Claude Code quality workflow`)としてpush済み
- `drafts/`ディレクトリを新設(`_config.yml`の`exclude`に追加、`docs/README.md`に運用ルールを
  追記)。`_articles/`はJekyll collectionのためstatusに関わらずビルド・公開されてしまう点への
  対策として、ready未満の記事の置き場を明確化した(未コミット)
- 第4号(Lチカ)記事公開Sprint: 仕上げ後、`status: ready`へ変更し`drafts/04-arduino-lchika.md`→
  `_articles/04-arduino-lchika.md`へ移動。第1〜3号の関連記事リンク・本文中の前方参照(「扱う予定
  です」→実リンク)を更新。independent-reviewerを2サイクル実施しBLOCKER/MAJOR 0を達成後、
  commit `287b40b`(`feat: publish Arduino LED blink guide`)としてpush・GitHub Actions
  build/deploy・公開後validation(HTTP/title/description/canonical/OGP/JSON-LD/H1重複なし/
  内部リンク/sitemap/GA4/アセット404なし)まで完了。公開URL:
  https://kkawa777.github.io/ai-tech-lab/articles/arduino-lchika/
- 第5号(ESP32配達物検知)記事公開Sprint: インタビュー7問すべて反映(Owner回答をSoTとして使用、
  推測・補完による創作なし)。使用マイコンがArduino UnoではなくESP32だったことが判明したため、
  primary_keyword/search_intentをESP32前提に再設計。LINE Notifyは2025-03-31にサービス終了済み
  であることを公式発表で確認し、本文で「当時」(実際に使用)と「現在」(後継のMessaging APIを
  一般情報として案内、筆者が使ったとは書かない)を明確に分離。**CONTENT_PLAN.mdの正式な#5
  (「Arduinoの基本構文(setup/loop)」)との番号衝突を避けるため、ファイル名の`05-`プレフィックス
  を落とし`esp32-loadcell-delivery-detection.md`に変更**(frontmatterの`order: 5`は公開順として
  維持、CONTENT_PLAN上のカタログ番号とは独立)。independent-reviewerを合計4サイクル実施し
  BLOCKER/MAJOR 0を達成(draft段階3サイクル: サイクル1 BLOCKER1[SparkFun引用の過剰帰属]・
  MAJOR1[「マークチューブ」という未確認の具体的表現]・MINOR5件→修正、サイクル2 MINOR1件→修正、
  サイクル3 BLOCKER0/MAJOR0確認。公開直前の最終サイクル: 名称変更後の内容ドリフトなし・
  第3号の内部リンク更新の整合性を確認しBLOCKER0/MAJOR0)。`status: ready`へ変更し
  `_articles/esp32-loadcell-delivery-detection.md`へ移動。第3号記事の「配達物検知への発展」
  段落を実リンクに更新(「雨検知への発展」は引き続き未公開のため前方参照のまま維持)。commit
  `8b24119`(`feat: publish ESP32 load cell delivery detector`)としてpush・GitHub Actions
  build/deploy・公開後validation(HTTP/title/description/canonical/OGP/JSON-LD/H1/GA4/
  Amazon CTAなし/内部リンク/sitemap/アセット404なし/drafts二重公開なし)まで完了。公開URL:
  https://kkawa777.github.io/ai-tech-lab/articles/esp32-loadcell-delivery-detection/
- ESP32-CAM記事(前編の続編)公開Batch: `_articles/esp32-cam-delivery-monitoring.md`として
  commit `ab3009c`でpush・deploy済み(公開URL:
  https://kkawa777.github.io/ai-tech-lab/articles/esp32-cam-delivery-monitoring/)。
  当初の使用ボード表記(ESP8266→AI-Thinker ESP32-CAM)は、その後さらに**Freenove ESP32 CAM**
  であったと判明し訂正済み(詳細は直下の「実使用製品訂正Batch」を参照)。詳しい経緯・レビュー
  サイクルはGit history(コミットメッセージ)に委ね、ここには再掲しない
- ESP32-CAM記事 収益化準備Batch(**未commit、公開はこれから**、下記「実使用製品訂正Batch」で
  さらに更新): 将来のAffiliate Sprintに備え、公開済み記事の内容を強化。ESP32/ESP32-CAM/
  メーカー名の3階層説明+Arduino Unoとの違いへ拡充、「使用した構成」→「実際に使ったもの」へ
  買い物ガイド風に再構成、新設「ESP32-CAMはこんな人に向いていた」節で実体験由来と一般知識由来を
  明確に分離(Ownerが明言していない
  「おすすめしない」は創作せずヘッジ表現に統一)。前編記事のESP32-CAM紹介も軽微に補強。
  **monetization: none・Amazon CTAは維持し、ASIN未確認のため一切追加していない**。
  independent-reviewerを2サイクル実施しBLOCKER0/MAJOR0達成(サイクル1: MAJOR1[前編記事に
  追加した一文が「ここまで使ってきたArduino Uno」と書いており、同記事が実際にはESP32を
  使用しているという既存記述と自己矛盾]・MINOR2[価格の実体験/一般知識混同、カメラ型番の
  橋渡し文欠如]→すべて修正。サイクル2: BLOCKER0/MAJOR0最終確認)。commit/push/deployは
  行っていない(オーナー承認待ち)

## Blocked

(現在有効なBlocked項目なし)

## Owner Action Required

1. **Dev Log Phase 3判断(READY_FOR_PHASE_3: NO、Phase 2.7時点)**: Phase 2.6でscore≥80の
   AUTO_PUBLISH_CANDIDATEを2件(2026-08-08=82点・2026-08-20=81点)実現し、Phase 2.7で
   両記事の事実性・整合性・可読性を大きく改善したが(BLOCKER3件・複数MAJORを検出・修正)、
   独立レビューの最終判定はいずれもグレードB(primary_keyword/titleが「読者が実際に
   検索する自然な日本語クエリ」になっていないというMAJORが1件ずつ残存)。これは
   `docs/devlog-policy.md`42節のとおり実装バグではなく「LLMを使わない決定論的パイプライン
   の設計上の境界」と判断した。方針判断が必要: (a)primary_keyword/titleの最終確認・
   書き換えを`_articles/`昇格前の人によるレビュー工程として明示的に維持する(既存の
   Dev Log Gateの想定どおり運用を続ける)、(b)強いガードレール付き(生成された事実のみを
   入力、出力を短いキーワード候補に限定等)のLLM支援キーワード提案ステップを別ラウンドで
   検討する、(c)score≥80=無人自動promotion可、という前提自体をPhase 3で採用するかどうか
   (現状は(a)を前提にしないと安全に運用できない)
2. score.pyのEvidence Strength軸が他軸と実質重複している設計上の緊張は、Phase 2.7で
   部分的に緩和した(baselineを他軸から独立した項目へ引き上げ、最も重複する「evidence
   件数」の加点を半減。詳細は`docs/devlog-policy.md`40節)が、完全な再設計はまだ行って
   いない(次のDev Log関連ラウンドでの課題として残る)。なお`sanitize.py`の
   `_extract_single_line_replacement`のfrontmatter境界問題はPhase 2.7で解消済み(40節)
3. Amazon.co.jpアソシエイト規約について、英語表記のみで日本向けサイトとして十分かは規約に明記が
   なく確認できなかった点の最終確認(現状は日本語必須文言+英語補足で対応済み、追加対応の要否は任意)
4. CONTENT_PLAN.mdへ新規提案した2記事は両方とも公開済み(カテゴリE「実践プロジェクト作品集」に
   正式なカタログ番号を割り当てるかは未定。配達物検知は`esp32-loadcell-delivery-detection.md`、
   水検知センサー雨検知は`esp32-rain-sensor-detection.md`として存在)。正式な記事番号を追加する
   かどうかの判断が残る
5. Dev Log PoCの`drafts/devlog-ai-tech-lab-2026-08-23.md`を実際に`_articles/`へ昇格(status:
   ready化)して公開するかどうかの判断。Phase 2の`scripts/promote-devlog.py`
   (+`scripts/mark-devlog-reviewed.py`)で昇格自体は可能になったが、機械的な要約レベルの内容の
   ため、公開する場合はtitle/primary_keywordの日本語化(docs/devlog-policy.md 9節)を推奨
6. Dev Logの対象project拡大(`ai-content-engine`/`global-trend-discovery`/
   `line-stock-news-bot`/`content-revenue-engine`を`config/devlog-projects.yaml`で
   `enabled: true`/`public: true`にするか)は、各repositoryを公開してよいというOwnerの
   明示判断が出るまで保留
7. Dev Logの20:00毎日自動実行(`scripts/run-daily-devlog.py`)をGitHub Actions cronまたは
   Windows Task Schedulerへ実際に登録するかどうかの判断(Phase 2ではrunner自体は実装済みだが、
   スケジューラへの登録は意図的に見送っている。上記1のPhase 3判断待ち)
8. 命名規則の改善提案(要判断): `_articles/`のファイル名`0N-slug.md`は、01〜04号が偶然
   CONTENT_PLAN.mdのカテゴリA番号と一致していたために「公開順」と「CONTENT_PLAN上のカタログID」が
   同じ意味であるかのように見えていたが、実際には別の名前空間。第5号(配達物検知)で両者が衝突した
   ため、今回はファイル名から数字プレフィックスを落として回避した。今後もカテゴリを跨ぐ記事(実践
   プロジェクト作品集等)が増える見込みのため、`order:`frontmatterを公開順のSoTとし、ファイル名は
   常にslugのみ(数字プレフィックスなし)に統一する運用への変更を提案する。既存の01〜04は
   大規模renumberを避けるためそのまま維持し、今後の新規ファイルにのみ適用する案
9. `privacy.md`の「運営者・お問い合わせ」章はGitHub Issuesリンクで暫定対応した。専用の問い合わせ
   手段(メールアドレス等)を今後用意する場合は、この章の更新を検討
10. `MEASUREMENT REQUIRED`: 下記「計測 TODO」を参照
11. 第4号本文中に、既公開の第3号記事への同種の前方参照debtが残存(`_articles/01-arduino-toha-
    hajimekata.md`の69行目・102行目、「別記事「Arduinoスターターキットの選び方」で扱う予定です」
    →実リンク化されていない)。今回の第4号公開diffの対象外だったため見送ったが、次回の軽微な
    修正機会に「第3号記事「...」」+リンクの形式へ統一することを推奨(independent-reviewer指摘)
12. ESP32-CAM監視の続編記事(下記候補)で配線図・コードを扱う場合は、電源仕様など
    安全上の注意点を必ず含めること(第5号は配線図・コードを意図的に割愛したため今回は問題なし、
    independent-reviewer指摘)
13. `B09XMPPZYT`(USBシリアル変換器、第6号記事対象)が実際に購入した商品と同一か、オーナーに確認が
    必要(`B089LS556S`・`B0C9THDPXP`は2026年8月のAffiliate Sprintで確認済み・CTA実装済みのため、
    このリストからは除外した。詳細は下記「Affiliate ASIN管理」および「第5号 Affiliate実装済み内容」参照)

## Affiliate ASIN管理(2026年8月 Affiliate展開Sprint)

Associate Tag: `aitechlab-22`(既存設定を維持)。

**訂正の経緯**: 第6号(ESP32-CAM)記事の実使用ボードは、当初「AI-Thinker ESP32-CAM」と記録して
いたが、これはOwnerの記憶違いだったと判明。Amazon購入履歴等により、正しくは**Freenove ESP32
CAM Dev Board Kit(ASIN `B0CJJHXD1W`)**であることをOwner本人が確認した。記事本文・frontmatter
とも訂正・実装済み(下記参照)。

| ASIN | 商品 | 分類 | 対象記事 | 状態 |
|---|---|---|---|---|
| `B0CJJHXD1W` | Freenove ESP32 CAM Dev Board Kit | **実使用品(Owner確認済み)** | 第6号 | **CTA実装済み**(`used=true`) |
| `B089LS556S` | ロードセル×4+HX711セット | **実使用品(Owner確認済み)** | 第5号 | **CTA実装済み**(`used=true`) |
| `B0C9THDPXP` | Freenove ESP32開発ボード | **実使用品(Owner確認済み)** | 第5号 | **CTA実装済み**(`used=true`) |
| `B09XMPPZYT` | USBシリアル変換器 | 実使用候補(確認待ち、用途不明) | 第6号 | Owner確認待ち(#11、CTA追加せず) |
| `B07PVRWDSW` | 水検知センサー | **実使用品(Owner確認済み)** | 第7号 | **CTA実装済み**(`used=true`) |
| `B0FT818HCH` | 3Dプリンター | future-article | 3Dプリンター関連記事(未執筆。第5号・第6号の「今なら」将来案は言及のみで実使用ではない) | 実体験との一致確認後に利用 |

### 第6号 Affiliate実装済み内容(**commit `63ff017`でpush・deploy済み**)

- サイト初のAmazon Affiliate CTA。commit `63ff017`(`feat: add affiliate link to ESP32-CAM
  article`)としてpush、GitHub Actions build/deploy成功、公開後validation(HTTP 200/title/
  description/canonical/OGP/JSON-LD/H1 1個/GA4/Amazon URL`https://www.amazon.co.jp/dp/
  B0CJJHXD1W?tag=aitechlab-22`/tag1回のみ/UTMなし/rel・target/data-affiliate-*属性/
  Affiliate Disclosure描画/前編⇔第6号の相互内部リンク/sitemap/CSS・JS404なし)まで完了。
  公開URL: https://kkawa777.github.io/ai-tech-lab/articles/esp32-cam-delivery-monitoring/
- independent-reviewerで25項目の重点確認を実施しBLOCKER0/MAJOR0/MINOR0(指摘事項なし)を確認
- `_articles/esp32-cam-delivery-monitoring.md`: frontmatterを`content_type: commercial`・
  `monetization: amazon_affiliate`・`conversion_goal: amazon_cta_click`・
  `affiliate_products: [{asin: B0CJJHXD1W, role: used, label: Freenove ESP32 CAM Dev Board
  Kit}]`へ変更
- CTA: 「Freenove ESP32 CAMとは?」節(今回実際に使用した製品の説明)の直後に1箇所のみ設置。
  文言「今回使ったESP32 CAMをAmazonで確認する」、`used=true`、
  `position="used-esp32-cam"` `article="esp32-cam-delivery-monitoring"`
- USBシリアル変換器(`B09XMPPZYT`)は、Freenove製品仕様上USB内蔵書き込みに対応しているため、
  Owner実体験(当時使用した記憶)との関係が未確認。CTAは追加していない(#11参照)
- 本文中、「AI-Thinker」への言及は「一般的なESP32-CAMの代表例」および「記憶違いの経緯説明」の
  2箇所のみ残し、実使用品としての記載はすべてFreenoveへ訂正済み

### 第5号 Affiliate実装済み内容(2026年8月Sprint。commitはこのSprint完了後に追記)

- Ownerが`B0C9THDPXP`(Freenove ESP32開発ボード)・`B089LS556S`(ロードセル×4+HX711セット)の
  両ASINについて「第5号の配達物検知システムで実際に使用した商品と同一」と確認
- `_articles/esp32-loadcell-delivery-detection.md`: frontmatterを`content_type: commercial`・
  `monetization: amazon_affiliate`・`conversion_goal: amazon_cta_click`・
  `affiliate_products: [{asin: B0C9THDPXP, role: used, ...}, {asin: B089LS556S, role: used, ...}]`
  へ変更。`tested_hardware`・`amazon_products`も確認済みASINを反映するよう更新
- 本文「使用した構成」節に「ESP32とは」「今回使用したFreenove ESP32」「ロードセル・HX711とは」の
  各見出しを追加し、一般的な製品仕様(Freenove公式・Amazon商品ページ、2026年8月確認)と筆者の
  実体験を分離して記載
- CTA1: 「今回使ったFreenove ESP32をAmazonで確認する」、`used=true`、
  `position="used-esp32"` `article="esp32-loadcell-delivery-detection"`
- CTA2: 「今回使ったロードセル＋HX711をAmazonで確認する」、`used=true`、
  `position="used-loadcell"` `article="esp32-loadcell-delivery-detection"`
- CTAは商品ごとに1箇所ずつ、各商品の実使用説明の直後に配置。記事の主目的(実作品記事)は変えていない
- independent-reviewerによる22項目レビューを実施(BLOCKER/MAJOR検出→修正のループを経てクリア)

### 第6号 USBシリアル変換器(実装保留、ESP32-CAM本体CTAとは別)

- `B09XMPPZYT`は「実際に使ったもの」節に、当時使用した記憶がある旨を本文で記載済み(ただし
  Freenove製品仕様上USB内蔵書き込みに対応しているため、このボードへの書き込み用途だったかは
  未確認と明記)
- CTA実装案(保留): 「USBシリアル変換器について(製品仕様と実体験の違い)」節の直後
  - 文言案: 「今回使ったUSBシリアル変換器をAmazonで確認する」
  - `used=true`(`B09XMPPZYT`が実使用品と確認でき、かつ用途[このボードへの書き込みか否か]も
    確認できた場合のみ)
  - data属性: `position="used-usb-serial"` `article="esp32-cam-delivery-monitoring"`
  - 用途不明のまま`used=true`でCTA化すると実体験を都合よく解釈することになるため、
    Owner確認(#11)が完了するまで実装しない

### amazon_click(GA4)確認

`assets/js/affiliate-tracking.js`は`data-affiliate-product`/`data-affiliate-position`/
`data-affiliate-article`を読み取る既存実装のまま(前Sprintで確認済み)。新CTA追加時も同じdata属性
パターンを使えばそのまま動作する見込み。実装時に`amazon-cta.html`のinclude引数(`asin` `label`
`position` `article` `used`)経由で設定する。

### 既存記事のAffiliate候補 洗い出し結果

1. **実使用品+ASIN確認済み → CTA実装済み**: 第6号のFreenove ESP32 CAM Dev Board Kit
   (`B0CJJHXD1W`、`used=true`)、第5号のFreenove ESP32開発ボード(`B0C9THDPXP`、`used=true`)・
   ロードセル×4+HX711セット(`B089LS556S`、`used=true`)
2. **実使用品+ASIN不明/確認待ち → Owner Action**: 第6号(USBシリアル変換器`B09XMPPZYT`)。
   上記「Owner Action Required」#11参照
3. **未使用/候補 → 無理にCTAを入れない**:
   - 第1号: 具体的な商品名・型番を本文で「未確認」と明記しており、紹介可能な実使用品がそもそもない
   - 第2号: ソフトウェアインストール記事のため対象製品なし
   - 第3号: 実使用したスターターキットの型番は「未確認」。既存の候補商品(`affiliate_products`、
     いずれも`role: candidate`)は`B06Y56JV64`(CTAボタン2箇所、`used=false`)・`B08KYFQSWZ`
     (本文・比較表内のテキスト参照のみ、CTAボタンなし)で、いずれも前Sprintで設定済みのため変更不要
   - 第4号: LED・抵抗の型番は「未確認」と明記、紹介可能な実使用品なし

## 第6号(ESP32-CAM) 画像設計ブリーフ(`_articles/esp32-cam-delivery-monitoring.md`)

実際の画像ファイルは未作成(このAgentに画像生成ツールがないため)。以下は画像を作成する際の設計方針。
電気配線図は作成しない。実機写真・撮影画像はOwner提供があれば追加するOPTIONAL扱い。

**A. eyecatch**: テーマ=「玄関・宅配ボックス・荷物」+「小型IoTカメラ」+「スマートフォンで確認」。
ESP32-CAM基板を電気的に正確に再現する必要はなく、「配達物をIoTカメラで確認する」という記事内容が
一目で伝わることを優先。既存記事(#1〜#5)のeyecatchとのデザイン整合性を確認すること。避けるべき要素:
過剰な未来感、意味不明な電子回路、存在しない配線、読めない文字、大量の発光エフェクト。

**B. システム構成概念図(当時の実装)**: 電気配線図ではなく論理構成のみ。
```
[重量検知]                    [カメラ確認]
4つのロードセル                Freenove ESP32 CAM
      ↓                            ↓
   HX711                         Wi-Fi
      ↓                            ↓
   ESP32                   一定間隔で静止画送信
      ↓                            ↓
  「荷物あり」                    サーバー
                                    ↓
                          ブラウザ/スマートフォン
                                    ↓
                          「何が届いたか確認」
```
**重要な制約**: 重量検知とカメラ確認の間に「自動連動」の矢印を描かないこと。当時のESP32-CAMは
重量検知と連動せず一定間隔で画像を送信していたため、2つのシステムは独立した「並列の役割分担」として
表現する(「荷物がある」を知る系統と「何が届いたか見る」を知る系統は別物)。

**C(参考・別図・OPTIONAL). 「今ならこう作る」概念図**: 本文の「今ならどう作るか」節に対応する、
将来案としての図。上記Bとは明確に分離し、必ず「今ならこう作る(将来案)」ラベルを付けること。
```
重量検知 → 荷物あり → ESP32-CAM撮影 → 写真送信 → スマホ通知
```
このイベント駆動の矢印は、Bの「当時の実装」概念図には絶対に転用しないこと。

## 第7号 画像TODO(`_articles/esp32-rain-sensor-detection.md`、公開済み・READY WITH TODO)

電気配線図は今回生成AIで作成しない方針(第4号・第5号Sprintと同じ理由)。

- A. eyecatch: 未着手。AI生成可(技術的な配線図としては使わない、概念イメージのみ)
- B. システム構成概念図: 未着手。AI生成/SVG等可(水検知センサー→ESP32→通知、という抽象的な
  システム構成図のみ。電気配線の正確性は要求しない)
- C. 電気配線図: 未着手。Fritzing等の正確なツールで別途作成(未確認なら公開せずTODOのまま。
  ESP32のGPIOは3.3V、センサーモジュール側の対応電圧は未確認のため、正確な電圧確認ができるまで
  配線図は作成しない)
- D. 実機写真・センサー写真・設置状態(屋外窓際)写真: オーナー提供があれば最優先で使用。
  なくても公開を止めない
- E. 3Dプリンターケース写真(二重構造): オーナー提供があれば追加。現物が既に故障・使用中止のため
  提供不可の可能性が高い(未確認)

## 第5号 画像TODO(`_articles/esp32-loadcell-delivery-detection.md`、公開済み・READY WITH TODO)

電気配線図は今回生成AIで作成しない方針(第4号Sprintと同じ理由: 生成AIはブレッドボード穴位置・
ピン位置を正確に再現できないため)。

- A. eyecatch: 未着手。AI生成可(技術的な配線図としては使わない、概念イメージのみ)
- B. システム構成概念図: 未着手。AI生成/SVG等可(4ロードセル→HX711→ESP32→通知/保存、という
  抽象的なシステム構成図のみ。電気配線の正確性は要求しない)
- C. 電気配線図: 未着手。Fritzing等の正確なツールで別途作成(未確認なら公開せずTODOのまま)
- D. 実機写真: オーナー提供があれば最優先で使用。なくても公開を止めない

## 第4号 画像TODO(`_articles/04-arduino-lchika.md`、公開済み・READY WITH TODO)

配線図は今回のSprintでは新規生成しない方針(画像生成AIがブレッドボード穴位置・Arduinoピン位置を
正確に再現できないため)。公開後も引き続き以下が必要。

- A. eyecatch画像: 未作成(他記事と同様、記事内容を表すビジュアル。電気的に厳密な配線図としては
  使わない)
- B. 配線図: 未作成。Fritzing等、電気的に正確なツールで別途作成する(画像生成AIによる配線図は
  不採用の方針)
- C. 実機の配線写真: あれば追加(必須ではない、なくても公開を止めない)

## 計測 TODO(MEASUREMENT REQUIRED)

commit `8650da5`(収益化Sprint、2026-08-20 deploy)以降のデータが十分に蓄積してから確認する。
データが揃うまでは推測で判断・最適化しない。

### Search Console(数週間程度のデータ蓄積が必要)
- impressions(表示回数)
- clicks(クリック数)
- CTR(クリック率)
- average position(平均掲載順位)
- query別内訳(どの検索語で流入しているか)
- page別内訳(どのページが表示・クリックされているか)

### GA4(数日〜数週間のデータ蓄積が必要)
- users(ユーザー数)
- page_view(ページビュー)
- amazon_click(カスタムイベント。発火数・記事別/位置別の内訳)
- Amazon適格販売(GA4では取得不可。Amazonアソシエイト管理画面側のレポートを確認)

### Core Web Vitals(実ユーザーデータの蓄積が必要。PageSpeed Insights/Search Console)
- LCP(Largest Contentful Paint)
- CLS(Cumulative Layout Shift)
- INP(Interaction to Next Paint)

上記が揃うまでは現状維持する。特に`index.md`のfeatured cardと`articles/index.md`一覧カードの
`loading`属性の扱いの不整合(収益化Sprintで既知のMINORとして記録済み)は、LCP実測データが揃って
から対応を検討する。

## 新規記事候補(配達物検知記事インタビューから抽出、Search Intentが独立するもののみ)

記事数稼ぎを避けるため、実体験の有無とSearch Intentの独立性で選別した。

**有力候補(実体験あり・検索意図が独立)**:
- **ESP32-CAMで配達物をカメラ確認できるようにした話(次記事)**: `drafts/esp32-cam-delivery-
  monitoring.md`としてdraft作成済み(`status: draft`)。Owner Interview 7問すべて反映済み。
  independent-reviewerでBLOCKER0/MAJOR0を確認(MINOR2件は用語説明の体裁統一として修正済み)。
  詳細は下記「Completed」セクションを参照。`_articles/`への移動・commit/push/deployは未実施
  (オーナー判断待ち)
- ESP32から通知を送る方法(LINE Messaging API/メール等、一般的な技術記事): LINE Notifyが
  サービス終了済み(2025-03-31)のため、現行のMessaging APIでの実装を一般情報として解説する記事は
  タイムリーかつ独自の検索意図を持つ。ただし「筆者が実際にMessaging APIを使った」とは書けない
  (未使用)ため、一般解説記事として設計する必要がある

**保留(実体験が今回のインタビューでは不足)**:
- ESP32+HX711の基本的な重量測定(チュートリアル): 配線・コードの具体が未確認のため、追加インタビュー
  なしでは基礎チュートリアルとして書けない
- ロードセルのノイズ対策: 配達物検知記事の「失敗したこと」節と内容が重複しやすく、
  カニバリゼーションのリスクがある。今回の記事より深い実体験が確認できない限り独立記事化しない

**時期尚早(実体験なし、将来の願望のみ)**:
- 3DプリンターでIoT機器の筐体を作る: 「今なら使ってみたい」という将来案のみで、実際に作った実体験が
  まだない。実際に作った後で記事化を検討
- Bambu Lab X1/H2Dを使った実体験記事: 3Dプリンターの使用経験自体はあるが、具体的なプロジェクトの
  実体験が今回のインタビューでは確認できていない。追加インタビューが必要

## Next Up

- 第4号(Lチカ)記事は公開済み。eyecatch画像・配線図が届き次第、上記「第4号 画像TODO」に沿って
  本文へ反映(A/Bとも未着手)
- 第5号(ESP32配達物検知)記事は公開済み。eyecatch・システム構成概念図・配線図・実機写真が届き
  次第、上記「第5号 画像TODO」に沿って本文へ反映(A〜D未着手)
- ESP32-CAM記事は公開済み。eyecatch・システム構成概念図(当時)・実機写真・撮影画像が届き次第、
  上記「第6号(ESP32-CAM) 画像設計ブリーフ」に沿って本文へ反映(A〜Dとも未着手)。Amazon ASIN
  確認(Owner Action Required #11)は次のAffiliate Sprintで検討
- 第7号(水検知センサー雨検知)記事は公開済み。eyecatch・システム構成概念図・実機写真・センサー/
  設置状態写真・3Dプリンターケース写真が届き次第、下記「第7号 画像TODO」に沿って本文へ反映
  (未着手)。正確な配線図が必要な場合はFritzing/SVG等で別途作成する方針(未確認の配線は画像化しない)
- `CONTENT_PLAN.md`の「10記事到達までの推奨公開順」における他の次候補: #5(setup/loop) →
  #13(シリアルモニタ) → #6 → #7。既存の提案どおりで変更なし。低品質な記事数稼ぎは行わない方針を維持
- Claude Code開発基盤統合(`knowledge/`新設、2026-08-24)で移行を見送った項目: `.company/
  secretary/notes`の意思決定・学びの精査、本ファイルの古いCompleted履歴のさらなる`knowledge/`化。
  価値が明確なものがあれば都度`knowledge/decisions/`等へ昇格する(大量migrationはしない)
