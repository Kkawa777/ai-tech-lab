---
title: Arduino IDEのインストール方法(Windows版)｜ボード認識・書き込みでつまずいた話
status: ready
permalink: /articles/arduino-ide-install-windows/
order: 2
category: Arduino入門
difficulty: 初級
estimated_time: 読了目安 約8分
description: Windows環境でArduino IDEをインストールする手順と、ボードが認識されない・書き込みができないというつまずきの実体験、その対処法を初心者向けに解説します。
image:
  path: /assets/images/articles/arduino-ide-install-windows/eyecatch.webp
  alt: Windows PCにArduino IDEをインストールし、USBでArduinoボードへ接続して書き込みを行うイメージイラスト
tested_hardware: Arduino Uno(当時使用。PCの詳細環境は未確認)
tested_software: Arduino IDE(当時使用した正確なバージョンは不明)
amazon_products: 該当なし(本記事では製品紹介を行わない)
---

## Arduino IDEとは？

Arduino IDE(アイディーイー)は、Arduinoにプログラムを書き込むための公式の開発ソフトです。パソコンで書いたプログラム(スケッチと呼ばれます)を、USBケーブル経由でArduino本体に転送する役割を持っています。

この記事では、Windows環境でArduino IDEをインストールし、実際にArduinoへ書き込みができるようになるまでの手順と、その過程でつまずいたポイントを実体験ベースで紹介します。

※Mac環境については、筆者自身の実体験が確認できていないため、今回の記事では扱いません。

## この記事でわかること

- Windows環境でArduino IDEをインストールする手順
- ボードが認識されない、書き込みができないというトラブルの実体験と対処の考え方
- 今から始めるならおすすめしたい準備の順番

![公式サイトからのダウンロードから動作確認までの9ステップを示すインストールフロー図]({{ "/assets/images/articles/arduino-ide-install-windows/install-write-flow.webp" | relative_url }})
{: width="1200" height="900" loading="lazy" decoding="async"}
*インストール〜書き込みまでの流れを示すイメージ図（AI生成のフロー図）*

## この記事はこんな人におすすめ

- これからArduinoを始めたい、Windows環境の人
- Arduino IDEをインストールしたが、ボードが認識されずに困っている人
- 書き込みがうまくいかず、何を確認すればいいか分からない人

## Arduino IDEを入れようと思った理由

第1号記事「[Arduinoとは？電子工作初心者だった僕が最初に選んだ理由と始め方]({{ "/articles/arduino-toha-hajimekata/" | relative_url }})」で紹介した通り、仕事をきっかけにArduinoを知り、Arduino Unoを購入しました。購入後、何を使ってプログラムを書き込めばいいのかを調べたところ、Arduino公式の「コーディングGUI」(画面上の操作でプログラムを書き込めるソフト、という意味です)であるArduino IDEがあることを知り、それを使うことにしました。

## インストール手順(Windows)

### 1. 公式サイトからダウンロードする

Arduino公式サイト(arduino.cc)からWindows版のインストーラーをダウンロードします。

※2026年8月8日時点でArduino公式サイトを確認したところ、現在配布されているのはArduino IDE 2系(バージョン2.3.10)でした。バージョンや配布方法は今後変更される可能性があるため、実際にインストールする際は公式サイトで最新の情報を確認してください。(参考: [Arduino Software | Arduino](https://www.arduino.cc/en/software))

### 2. インストーラーを実行する

ダウンロードしたインストーラーを実行し、画面の指示に従って進めます。

このステップについては、英語表示の画面がそのまま読めれば特につまずくところはなかった、というのが筆者の実感です。インストール自体で大きく困った記憶はありません。

※2026年8月8日時点のArduino公式情報によると、Windows環境でのインストール時にArduino関連ドライバー(周辺機器をパソコンが正しく認識・動作させるためのソフト)のインストール許可を求められる場合があります(必ず表示されるとは限りません)。表示された場合は許可することが案内されています。(参考: [Download and install Arduino IDE – Arduino Help Center](https://support.arduino.cc/hc/en-us/articles/360019833020-Download-and-install-Arduino-IDE))

### 3. 初回起動を確認する

インストール完了後、Arduino IDEを起動します。ここまでのインストール作業全体を通して、大きな問題はありませんでした。

![PC・Arduino IDE・USB・Arduinoボードの関係と、Board設定・Port設定がそれぞれ何を指すかを示す構成図]({{ "/assets/images/articles/arduino-ide-install-windows/pc-ide-usb-board-port.svg" | relative_url }})
{: width="800" height="560" loading="lazy" decoding="async"}
*PC・IDE・USB・Arduinoボードの関係を示す構成図（Board＝ボード種類の設定、Port＝接続先の設定）*

## ボード設定・接続でつまずいたこと

インストールよりも、ここから先の「ボードの設定」と「接続」でつまずきました。具体的には、以下の2つの症状が同時に起きていました。

- Arduino IDE上でボードの種類が正しく選べていなかった
- PCがArduinoをポート(接続先)として認識せず、書き込みもうまくいかなかった

このときに、ボードの種類を調べる方法や、PC側の設定を見直すという対処の仕方を覚えました。

**2026年8月現在のArduino IDE 2では**、Board・Portは次のように扱われています(2026年8月8日時点でArduino公式ドキュメントを確認)。

- 「Board Selector」という機能があり、接続したボードを自動的に認識しようとします
- 認識できた場合はボード名が、認識できない場合は「Unknown」と表示されることがあります
- 従来どおり、「ツール」メニューの「Board」「Port」からそれぞれ個別に選択する方法も使えます
- Board(どのボード向けに書き込むかの設定)・Port(どの接続先に書き込むかの設定)という考え方は、上の構成図の通りです

(参考: [Select board and port in Arduino IDE – Arduino Help Center](https://support.arduino.cc/hc/en-us/articles/4406856349970-Select-board-and-port-in-Arduino-IDE))

> **安全上の注意**
> Arduino本体の取り扱いにおける注意点(ショート・破損防止など)は、第1号記事「[Arduinoとは？電子工作初心者だった僕が最初に選んだ理由と始め方]({{ "/articles/arduino-toha-hajimekata/" | relative_url }})」でも紹介しています。あわせてご確認ください。

## 書き込みができなかった時にやったこと

書き込みができない状態が続いたときは、PC側のポート設定を見直したことは覚えています。ただし、それ以外に具体的にどの設定をどう変更したかまでは、はっきりと覚えていません。そのため、当時行った具体的な解決手順については、この記事では断定しません(記憶が曖昧なため未確認)。

![認識確認からUSB・Board・Port確認、再書き込み、ソフト設定確認までの切り分け手順を示すトラブルシューティング図]({{ "/assets/images/articles/arduino-ide-install-windows/troubleshooting-flow.webp" | relative_url }})
{: width="900" height="1350" loading="lazy" decoding="async"}
*書き込みができない時の切り分け手順を示すイメージ図（AI生成のフロー図）*

### 2026年現在の公式情報で確認すると

上のイメージ図の流れとも対応していますが、2026年8月8日時点でArduino公式のサポート情報を確認したところ、ボードが認識されない場合の一般的な確認手順として、以下が案内されています(筆者が当時この順番で試したという意味ではありません)。

1. Arduinoボードを一度抜き差しする
2. USBケーブルの接続を確認する
3. 充電専用ではなく、データ通信に対応したUSBケーブルを使う
4. 別のUSBケーブル・別のUSBポートを試す
5. Board・Portの設定を確認する
6. 「ツール」>「Port」の一覧を開き直して再読み込みする
7. 必要に応じて、Windowsの「デバイスマネージャー(接続機器の認識状態を確認する画面)」も確認する

それでも認識されない場合は、Arduino Uno(Rev3以前)などの一部のボードでUSB-シリアル変換に関わるドライバー・ファームウェアが原因になっているケースもあるとされています。詳しくはArduino公式サポートページを参照してください。

(参考: [If your board is not detected by Arduino IDE – Arduino Help Center](https://support.arduino.cc/hc/en-us/articles/4412955149586-If-your-board-is-not-detected-by-Arduino-IDE))

## 今ならこの順番ですすめたい

今振り返ると、以下の順番で進めるのがおすすめだと感じています。

1. Arduinoを購入する
2. 届いたら、データシート(部品の仕様がまとめられた資料)を見ながらピン配置など基本的な情報を確認する
3. Arduino IDEをインストールする
4. 実際に接続して動作を確認する(うまくいかない場合はそのつど調べる)

## ダウンロード元についての注意

ソフトウェアに関しては、公式サイトから入手するのが一番だと考えています。非公式の配布元は、安全性やバージョンの信頼性が確認しづらいため、特別な理由がない限りは避けることをおすすめします。

## よくある質問

**Q. Arduino IDEのインストールでつまずきやすいポイントはありますか？**
A. 筆者の場合、インストール自体よりも、ボードの種類の選択とポート(接続先)の認識でつまずきました。

**Q. ボードが認識されないときはどうすればいいですか？**
A. まずボードの種類が正しく選択されているか、次にPC側がArduinoを接続先として認識しているか(ポート設定)を確認する、という順番で切り分けると原因を絞り込みやすいです。具体的な対処法は環境によって異なるため、公式サイトや公式フォーラムもあわせて確認することをおすすめします。

**Q. Macでも同じ手順でインストールできますか？**
A. 本記事はWindows環境での実体験に基づいて書いています。Mac環境については筆者の実体験が確認できていないため、この記事では扱っていません。

## まとめ

Windows環境でのArduino IDE導入は、インストール作業そのものよりも、その後の「ボードの種類」と「ポート」の設定でつまずきやすいというのが実体験からの気づきです。これから始める方は、インストールが終わった時点で安心せず、動作確認までを一つの区切りとして進めることをおすすめします。

## 関連記事

- [Arduinoとは？電子工作初心者だった僕が最初に選んだ理由と始め方]({{ "/articles/arduino-toha-hajimekata/" | relative_url }})
- [Arduino初心者向けスターターキットの選び方｜5,000円キットのその後]({{ "/articles/arduino-starter-kit-guide/" | relative_url }})
- [Arduinoで最初のLチカ(LED点滅)に挑戦]({{ "/articles/arduino-lchika/" | relative_url }})
