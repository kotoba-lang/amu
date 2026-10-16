# Embench を用いた比較結果と再現手順(M104 訂正版、M93 は履歴)

[English README.md](README.md)

このディレクトリは、<https://kotoba-lang.org/blog/embench-c-parity-20261015/> で公開した結果(証拠一式は
`/benchmarks/embench-official-20261015/`)を、第三者が検証・再ビルド・再計測できるようにするためのものです。

## 現在の計測状況

* **当初の M93 値 0.7999 を、同一アルゴリズムの結果として引用しないでください。** 後のカーネル監査で、計測した M93
  コンパイラに置換カーネルが含まれることが分かりました。また、Kotoba 側だけが ARMv8 SHA-256 命令を使っていました。
  M93 は以下に履歴として残します。
* 訂正版の **M104** は、同一アルゴリズムのみの selfhost 不動点コンパイラ、スカラー SHA-256、固定した upstream Embench speed
  ドライバ、文書化した反復あたりの比率式で全19 workloadを計測しています。元の Apple M4 サイクルは **Kotoba / C = 0.8213** です。
  2026-10-16には別の Apple M4 Mac mini (`Mac16,10`、16 GB、macOS 26.3.1)でも再計測し、両アーム19/19採用、Apple clang 21.0.0で
  Cを新規ビルドした結果は **0.7877703356** でした。ホストごとの結果として分けて記録し、平均していません。いずれも Kotoba のポートと
  プロジェクト固有ハーネスを使う **Embench に基づく翻訳ポートの比較**であり、公式・認定Embenchスコアではありません。再計測の全raw記録と
  独立検証スクリプトは `round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/` にあります。
* 2026-10-16 の Apple M1 Max 試行は、測定記録を残しましたが **不採択で、スコアではありません**。外部の10秒 raw-idleゲートは1回70.39%に達して計測を開始しましたが、Kotoba/C両アームで実行できた `aha-mont64` は各2試行とも計測区間の raw idle 70%未満で不採択でした。残る18 workloadは静穏ゲートのタイムアウトで実行されず、両アームとも0/19採用、GMなしです。全 raw 記録は `round-sa-m104-20261015/records/m1-attempt-20261016-r1/` にあります。
* M104 のプロトコルは各試行前の raw CPU idle 70%以上、全計測区間で raw idle と推定 background idle がともに70%以上、両アームで全19/19採用、Kotoba 出力の完全一致、raw 記録の保存を求めます。全件計測を完了し、raw 記録をプロトコルと独立照合するまで M1 のスコアは主張しません。

測定方法の参照元は [Embench User Guide](https://github.com/embench/embench-iot/blob/master/doc/README.md) と、固定した
[Embench upstream source](https://github.com/embench/embench-iot/tree/09c2ed8c3b7008c95d08b038de4a3f6dc103ed70) です。
このコミットの未変更 speed driver と baseline table を使い、Kotoba/C 用の独自 target module を与えています。
したがって、対象プログラムとハーネスは翻訳ポートの比較であり、未変更の Embench 提出物ではありません。

以下に記す過去の M93 再現では、計測したコンパイラのソースは本リポジトリのコミット `be7f0ce358ebe8d1a715b2784f272ce0eda8e934`
(ブランチ `claude/embench-c-parity-m93-20261015`)です。本パッケージは同じブランチ上の後続コミットで追加したもので、
計測対象のソースは変更していません(`seed/` は両コミットで同一です)。

## 1. 過去の M93 の主張(訂正版により置き換え)

2026年10月15日、1台の Apple M4 Mac mini(macOS、arm64)で行った 1 回の計測サイクルについて:

* Embench IoT の 19 ワークロードを Kotoba に翻訳したポートを、`be7f0ce3` からビルドした seed コンパイラでコンパイルし、
  Apple clang 17.0.0 `-O2` でコンパイルした元の Embench C と比べました。実行時間の幾何平均は **C の 0.7999 倍** でした。
  ワークロードごとの比は ratio_w = (4 / m_w) · K_ns / C_ns です。Kotoba は n_w = LSF_w · 8192 · m_w 回、C は LSF_w · 32768 回
  反復し、どちらも 1 反復あたりに正規化しています。1 未満は Kotoba が速いことを意味します。
* Kotoba の全実行は **完全一致(exact)** でした。結果、ベンチマーク燃料・検証燃料、17 個のアリーナカウンタのすべてが、
  信頼できる参照イメージから再導出した値(計測したコンパイラからは決して導出しない)と一致しました。C の全実行は
  `EMBENCH_NS` を 1 行出力し、stderr は空、終了コードは 0 でした。
* 計時は upstream の Embench speed ドライバ(`benchmark_speed.py`、upstream コミット `09c2ed8c`)と本ハーネスで行いました。
  プロトコルは次のとおりです。
  * ウォームアップ 1 回、サンプル 1 回。
  * CPU 受け入れ条件:実行前の生 idle ≥ 70 %、実行中の生 idle と推定バックグラウンド idle ≥ 70 %。
  * 試行は最大 3 回で、再試行は CPU 理由のみ。最初に条件を満たした試行を採用し、最速の試行は選びません。
  * 計時区間の下限は 0.5 秒。
  * 燃料上限は 2^35。
  * 同じサイクル内で Kotoba キャンペーン、続けて C キャンペーンを実行。
* 計測した 19 イメージはソース `be7f0ce3` だけで決まり、計測したコンパイラは selfhost の不動点です。レベル (b) は、
  JVM・GraalVM・Node.js を使わずに公開ネイティブブートストラップからそれを作ります。レベル (b) は公開ブートストラップから不動点コンパイラ
  G* = S(S) を作り、G* が 19 ポートをバイト単位で同一のイメージにコンパイルすることを示します。

## 2. 主張していないこと

* **認定された Embench スコアではありません。** Kotoba 側は翻訳ポートです。各 C ベンチマークに沿って書いた Kotoba コードで、
  `benchmark-unchecked` / `verify-state` に分離したインタフェースを持ちます。upstream のドライバと計算式を使っても、
  改変のない Embench 提出にはなりません。
* **認定カーネル。** 高速化の大部分は認定カーネルによるものです。関数の中間コードが既知の形と完全に一致すると、
  コンパイラは手書きの AArch64 を出力します。
  * 燃料の計上は汎用経路と同一で、汎用経路へのフォールバックもあります。
  * 採用はコードの形だけで決まり、ワークロード名では決まりません。
  * ただし、形はこれらのポートのホットな関数のために書かれたものなので、他のプログラムに自動的に効くわけではありません。
* **SHA 命令。** `nettle-sha256` は ARMv8 の SHA-256 命令を使います。C 側(`-O2`、イントリンシクスなし)は使いません。
  スカラーの sha256 経路(ローカル推定で約 1.27 倍)だった場合、幾何平均は約 0.848 になります。
* **単一サイクル。** 1 台のホストで 1 回の計測サイクル、各ワークロードの採用サンプルは 1 つです。信頼区間は主張しません。
  別のホスト・コンパイラ・負荷では別の値になります(レベル (d) を参照)。
* **m_w の予測は下限ではありません。** 実測 / 予測は 0.67〜1.76 の範囲でした。それでも全区間が 0.5 秒の下限を超えています
  (最小は matmult-int の 0.777 秒)。
* **C 側。** C 側は改変のない upstream C を Apple clang 17.0.0 `-O2` でビルドしたものだけです。`-O3`、LTO、`-mcpu`、
  プロファイルガイドは使っていません。

## 2a. カーネルの範囲

m93 コンパイラ(`be7f0ce3`)は認定カーネルを含みます。認識した関数の形に対する手書きの AArch64 で、2026年10月15日時点の
規則のもとで採用されたものです(2 節を参照)。公開後、本プロジェクトは以後のラウンドに向けて、より厳しい規則
「**同一アルゴリズムのみ**」を採用しました。この規則のもとでは、カーネルが変えてよいのはソース関数の処理を *どう*
実行するかだけで、*何を* 実行するかは変えられません。次は認められません。
* 反復の代わりに閉じた式で結果を出すこと。
* 別のデータ構造上でアルゴリズムを模擬すること。
* ソースが作らない実行時データ構造を新たに作ること。
* 繰り返しの間で結果を再利用すること。
* 別のアルゴリズムを使うこと。

**m93 コンパイラの監査結果。** 監査は完了しました。方針と結果の表は [`audit/`](audit/) にあります
(`KERNEL-POLICY.md`、`kernels-a.md`、`kernels-b.md`、`kernels-c.md`、`kernels-other.md`)。この方針のもとで、判断が
つかないものを置き換えとして数えると、**計測した m93 コンパイラは次の置き換えカーネルを含みます**。
* huffbench:`st`(sort-table をコピー上のラン併合で実行)、`hd`(呼び出しごとの走査表で decode-bits を実行)、`eb`
  (encode-bits をビット単位ではなく記号単位で実行)。
* qrduino:`qa`(ビット語とビット転置で all-runs を実行)、`bp` と `mr`(blocks-row と mask-row をビット並列で評価。
  判断保留)。
* tarfind:`lcg`(シード付き LCG を 2 ステップずつ進める。判断保留)。
* ud:`init` の列 0 経路(行和を閉じた式で計算)。
* picojpeg:ブロック全体の NEON IDCT。DC だけのレーンを、ソースの埋め分岐ではなく AC のバタフライに通します(判断保留)。

これに加えて、**nettle-sha256 は ARMv8 の SHA-256 暗号命令を使います**。公開値 0.7999 はこれらすべてを含みます。
**次の公式ラウンドは、同一アルゴリズムのみのビルドとスカラーの sha256 経路を使い**、同じスクリプトで実行します(7 節)。
本パッケージは、公開した m93 ラウンドを計測どおりに再現し続けます。

表は後の開発スナップショット(m97〜m101)も対象にしているため、m93 に含まれない置き換えカーネルも載っています。
picojpeg の end-of-block ビットマスク、sglib の `qk`・`ls`・`tb`、xgboost の `xs`、slre の set エントリは、m93 より後に
追加されたか、マージされていません。上の m93 についての記述は、いずれも `be7f0ce3` の `seed/41-a64gen.kotoba` で確認しました。

## 3. 必要なもの

| レベル | 必要なもの |
|---|---|
| (a) オフライン | Python ≥ 3.9 のみ。OS は問わず、ネットワークも Apple ハードウェアも不要 |
| (b) ビルド | Apple シリコン(arm64)の macOS、Xcode コマンドラインツール(`clang`)、`git`、Python 3。履歴を含む通常の clone(`--depth 1` は不可) |
| (c) 完全一致 | (b) に加えて `patch` |
| (d) 計時 | (c) に加えて、Embench IoT を GitHub から取得するためのネットワーク(1 回) |

コマンドはすべてリポジトリのルートで実行します。`--out` には毎回新しいディレクトリを指定してください。

## 4. 検証レベル

### (a) オフライン:生記録からすべてを再計算

```
python3 bench/embench/reproduce-20261015/a_offline.py --round rounds/m93-20261015.json
```

確認する内容:

* 本パッケージの `SHA256SUMS`。
* 両キャンペーンの収集カストディ。収集した各ファイルは、記録されたハッシュのまま `records/` に同梱されているか、
  同じハッシュと理由付きで `records/omitted-files.json` に記載されています。省いたのは、計測ホストのタイマーバイナリ、
  重複したローダのコピー、凍結した C バイナリ、Embench upstream のファイルです。
* 両キャンペーンの全試行について、tick カウンタと生の stdout/stderr から次を再計算します。
  * CPU 条件。
  * 完全一致。
  * 0.5 秒の下限。
  * 再試行の可否と、最初に条件を満たした試行の採用。
* 事前登録の計算(m_w と 0.6 秒のスクリーン)と、正確なタイマー起動(n_w、caps)。
* 両キャンペーンの幾何平均、19 個の比、19 ワークロード全体の幾何平均。

`--upstream <embench-iot のチェックアウト>` を付けると、省いた upstream ファイルも確認します。最終行の期待値:

```
LEVEL_A PASS GM 0.7998826447941968
```

(公開値 0.7998826447941967 との差は総和の順序による最終ビットのみです。許容誤差は 1e-12 です。)

### (b) ビルド:公開ブートストラップ → 不動点 → 計測したイメージ

```
python3 bench/embench/reproduce-20261015/b_build.py --round rounds/m93-20261015.json --out /tmp/embench-b
```

アイドル状態の M シリーズ Mac で約 10 分かかり、負荷が高いとさらに長くなります。手順と期待される SHA-256:

| 手順 | 内容 | 期待値 |
|---|---|---|
| 0 | ローダ = `clang -std=c11 -O2 seed/bootstrap/adopted-loader-20261012.c` | ソース `f44b5099…a8c3` |
| 1 | 公開ブートストラップ `seed/bootstrap/adopted-20261012.bin` が自身のソース(`ffa4cfc1` の unity、`233cafbf…`)を自身にコンパイル | `87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345` |
| 2 | ステージ A:`ffa4cfc1` の unity の `seed/00-ns.kotoba` を `be7f0ce3` のものに差し替えて(unity `f2dca71d…`)adopted でコンパイル | `5583a2fdf8267938f466782fc6c7873eecc03f321a4434f2a6d8840794a6691d` |
| 3 | G1 = A(S)、G2 = G1(S)、G3 = G2(S)。S = `be7f0ce3` の unity(`1b9d9e30…`、2,625,422 バイト)。**G2 = G3** | **G1 = G2 = G3 = G\* = `bcd70b2474f0421a53c40c07b61bef100e52220f562def767958f51f07ddad16`** |
| 4 | G* で `ports/official-*.kotoba` をコンパイルし、19 個すべての kseed・ネイティブイメージ・エクスポート表が計測時のものと一致 | `expected/measured-images.json` |

ステージ A が要る理由:`be7f0ce3` はコンパイラ自身のメモリマップを拡大しています。その `seed/00-ns.kotoba` は `ffa4cfc1`
のものと、生成された 22 個の定数(TOK・NODE・SIR・CODE・FIX・OUT の各テーブル拡大と MM-WORDS)だけが異なります。
公開ブートストラップのテーブルは計測対象のソースには小さすぎ、直接はコンパイルできません
(`seed: E101 compiler table full: region 1`、トークン表で停止します)。そこで、新しい定数を入れた
自身のソースをコンパイルし、旧コード生成器と新テーブルを持つコンパイラを作ります。他のソース変更は不要で、
入力ファイルはどちらも公開コミットにあります。

**計測に使ったコンパイラ自体が不動点です。** 計測時のコンパイラ `bcd70b2474f0421a53c40c07b61bef100e52220f562def767958f51f07ddad16`
は開発用コンパイラ m92 でビルドしたものですが、上の手順では G1 = A(S) の時点で同じバイト列になり、G1 = G2 = G3 です。
理由は、新しい最適化段(T2 と出力後パス)がサイズ予算で制限されており、コンパイラ自身ほど大きいプログラムには
適用されないことです(`seed/41-a64gen.kotoba` の `t2-max-sir` = 131072 SIR レコード)。そのためコンパイラ自身のコードは
`ffa4cfc1` と `be7f0ce3` に共通のバックエンドが生成し、そのバックエンドを持つどの生成元(ステージ A、m92、S 自身)からも
同じバイナリになります。19 個のポートは小さいので T2 と認定カーネルが適用されます。手順 4 は、それらのイメージが S だけで
決まることを示します。

### (c) 完全一致:各イメージを n_w で実行

```
python3 bench/embench/reproduce-20261015/c_exactness.py --round rounds/m93-20261015.json --out /tmp/embench-c [--count-instructions] [--images /tmp/embench-b/step4-images]
python3 bench/embench/reproduce-20261015/c_reference.py --round rounds/m93-20261015.json --out /tmp/embench-cref
```

**`c_exactness.py`** は各タイマーをビルドし、公式の caps で n_w を 1 回実行します。

* タイマーは `harness/separated-loader.c` です。これが `seed/bootstrap/adopted-loader-20261012.c` に
  `harness/separated-loader.diff` を当てたものであることを確認し、2 つのタイミングヘッダと、イメージを埋め込んだ生成ヘッダを
  加えて作ります。
* 結果・燃料・アリーナ行を `records/round/expected-accounting-mw.json` と比較します。期待値:`LEVEL_C PASS 19/19 exact`。
* `--count-instructions` を付けると、m=1 での計時区間の命令数(事前登録の I_w)を、`tools/mktimer.py` / `validate.py` と同じ
  計測方法で数え直します。事前登録値との差は 1 % を大きく下回ります。
* ここで表示される経過時間は結果ではありません。

**`c_reference.py`** は、`reference/` の信頼できる参照イメージから、各 n_w での期待値を再導出します。

* **round51**:元の翻訳ポートを、認定済みの WM G4 不動点でコンパイルしたもの。m=1 の値
  (`reference/expected-original-accounting-m1.json`)はその round51 の生記録に由来します。
* **round114**:独立したコンパイラによるイメージで、照合用に使います。

両者を同じハーネスで実行し、次を要求します。

* どちらも m=1 の値を再現すること。
* n_w で互いに一致すること。
* 公開した期待値と一致すること。
* 燃料と 17 個のアリーナカウンタが、倍率を変えたワークロードごとに 3 点以上で n に対して厳密にアフィンであること。
  唯一の例外は tarfind のベンチマーク燃料で、ステップごとの増分が 7.84e9 のうち 2,250 だけ異なります(データ依存の
  warm-seed 処理による)。n_w での値は直接測定しています。

期待値:`LEVEL_C_REFERENCE PASS`。約 10〜30 分かかります。

### (d) 計時:自分のマシンでの同一ホストキャンペーン

```
python3 bench/embench/reproduce-20261015/tools/fetch_upstream.py --dest /tmp/embench-iot
python3 bench/embench/reproduce-20261015/d_timing.py --round rounds/m93-20261015.json --upstream /tmp/embench-iot --out /tmp/embench-d
```

内容:

* 自分の clang で 19 個の C バイナリをビルドします(`c/build_c.py`、公式と同じコマンドライン)。
* 19 個の Kotoba タイマーをビルドします。
* Kotoba キャンペーン、続けて C キャンペーンを、改変のない upstream ドライバと本ラウンドの `run_trigger.py`
  (`harness/kotoba`、`harness/c`)で、完全なプロトコル(負荷ゲート、CPU 理由のみの再試行、最初に条件を満たした試行)で
  実行します。
* 38 実行がすべて採用された場合に限り、19 ワークロード全体の幾何平均を表示します。部分集合の幾何平均は出しません。

`--workloads crc32,edn` で短いスモーク実行ができますが、幾何平均は表示しません。

`--images` を指定する場合、全 kseed が選択ラウンドの kseed、native payload、exports、source table の pin と一致する必要があります。
`--c-binaries` を指定する場合は `c/build_c.py` が生成した schema 2 の `build-c.json` が必要です。検証器は固定 upstream revision、
コンパイル元と include header、記録された `-O2` コマンド、各バイナリのハッシュを照合します。全19の GM は両 upstream driver の終了コードも
0 の場合に限り表示します。

`d_timing.py` は、本ラウンドの 2 つのキャンペーンスクリプトをパスをパラメータ化して再実装したものです。元のスクリプトは
`records/official/campaign.py` と `records/fresh-C/campaign.py` にそのまま収録しています。同じに保っているのは、タイマーの
起動(n_w、caps)、ドライバのコマンド、`run_trigger.py`、スコアの計算式です。除いたのは、計測ホストのカストディレシートと
プロセスパターンです。また、凍結した C バイナリを再利用せず C をビルドします。

**ばらつきの目安。** 元の M104 Apple M4 サイクルは0.8213、別の Mac16,10 で Apple clang 21.0.0 を使った再計測は0.7877703356です。
ホストごとの結果は分けて扱い、平均して全M4共通の値にしないでください。過去の M93 0.7999 を同一アルゴリズムの結果として使わないでください。
結果は次によって変わります。

* CPU(C と Kotoba のコードはコアの使い方が異なります)。
* clang のバージョン(C バイナリが変わります)。
* バックグラウンド負荷と温度状態。

ワークロードごとの比は 10 % 以上、幾何平均は数 % 動くことがあります。負荷の高いマシンでは 70 % の CPU ゲートが試行を拒否します
(`quiet-admission-timeout`、`raw-post-cpu`)。他に処理のないマシンで実行してください。公式の凍結 C バイナリのハッシュは
`records/fresh-C/source-custody.json` にあります。別の clang では、別の(同等に正当な)バイナリになります。

## 5. 構成

| パス | 内容 |
|---|---|
| `a_offline.py`、`b_build.py`、`c_exactness.py`、`c_reference.py`、`d_timing.py` | 5 つのコマンド |
| `tools/repro_lib.py` | 共通処理:git コミットからの unity 生成、ローダのビルド、コンパイラ呼び出し、タイマー生成、caps、完全一致の判定 |
| `tools/fetch_upstream.py` | Embench IoT を `09c2ed8c` で取得して検証(ソース 40 個とドライバ 6 個のハッシュ) |
| `tools/make_sums.py` | `SHA256SUMS` を書き出す保守用ツール |
| `ports/official-<w>.kotoba` | 計測した 19 個のポートのソース(ライセンスは `ports/PROVENANCE.md`) |
| `images/<w>.bin`、`images/<w>.kseed` | 計測した 19 個のイメージ(ネイティブコード。kseed はエクスポート表付き) |
| `harness/` | タイマーローダと公開ローダからのパッチ、タイミングヘッダ、両アームの `run_trigger.py`、`darwin_cpu_idle.py`、ワークロード表(LSF、m_w、n_w、caps) |
| `c/build_c.py`、`c/boardsupport.c` | 公式と同じコマンドラインでの C ビルドと、計時用ボードサポート(`EMBENCH_NS`) |
| `reference/` | 信頼できる参照イメージ(round51 WM G4、round114)とそのエクスポート表、m=1 の元の期待値 |
| `records/round/` | プロトコル改訂の本文、ハッシュ付きの事前登録、参照会計レシート、n_w での期待値、コンパイル・準備・事前検査のレシート、検証レビュー、最終サマリ |
| `records/official/`、`records/fresh-C/` | 両アームの収集記録(レポート、全試行の生データ、受け入れ判定のプローブ、起動スクリプト、カストディ)をそのまま収録 |
| `round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/` | 2台目のM4による全19再計測、clangビルドレシート、raw試行、upstream検証、独立検証スクリプト |
| `round-sa-m104-20261015/records/m1-attempt-20261016-r1/` | M1 Max の未採択試行、CPUゲート証跡、全 raw 試行記録。ベンチマークスコアではない |
| `records/omitted-files.json` | 同梱しなかった収集ファイル(ハッシュと理由付き) |
| `expected/` | レベル (b) の固定値:ビルド入力、コンパイラチェーン、計測イメージ |
| `rounds/` | ラウンド設定(コミット、倍率表、固定値)。`sa-m104-20261015.json` が訂正版の既定値。M93 は履歴 |
| `audit/` | カーネル範囲の方針とカーネル監査表(2a 節を参照) |
| `round-sa-m104-20261015/` | 訂正版の同一アルゴリズムラウンド(8 節):記録、イメージ、ワークロード表、固定値 |

`records/` のファイルは改変のない証拠です。ハッシュがカストディの連鎖の一部なので、計測マシンの絶対パスとホスト名を
そのまま含みます。スクリプトはそれらのパスを使いません。

## 6. ライセンスと出所

* Embench IoT(upstream `https://github.com/embench/embench-iot`、コミット `09c2ed8c`)は GPL-3.0-or-later です。
  C ソースは同梱せず、取得して使います。`records/*/upstream/baseline-data/speed.json` は計算式に必要な upstream の
  ベースライン表です。
* Kotoba ポートは Embench の C プログラムの翻訳で、著作権表示と SPDX 行を保持しています(GPL-3.0-or-later。
  md5sum と tarfind は MIT、depthconv は Apache-2.0)。`ports/PROVENANCE.md` と `bench/embench/licenses/` を参照してください。
* `c/boardsupport.c` とハーネスは本プロジェクトの計測コードです。タイマーローダは
  `seed/bootstrap/adopted-loader-20261012.c` から派生したもので、その差分が `harness/separated-loader.diff` です。

## 7. 別のラウンドの実行

スクリプトはラウンド設定 `rounds/<name>.json` でパラメータ化されています。既定は訂正版の
`rounds/sa-m104-20261015.json` です。履歴として M93 を再現するときは `--round rounds/m93-20261015.json` を明示します。設定には次を記載します。
* 計測するソースのコミット。
* ステージ A がそのコミットから取るファイル(`seed/00-ns.kotoba`)。
* ポートとイメージのディレクトリ。
* ワークロード表。
* 任意の `multipliers` 表 `{workload: m_w}`。
* そのラウンドの期待値・事前登録・記録・固定値の場所。

`multipliers` を与えると、n_w = LSF · 8192 · m_w とアリーナの caps を事前登録の規則で計算し直します。規則は、m=1 での使用量
× m_w が m=1 の容量を超える KEXE 資源の容量を、容量 × m_w にするというものです。制約は 2 つあります。
* **燃料:** 予測される(ベンチマーク+検証)燃料は 0.9 · 2^35 以下でなければなりません。
* **ローダの上限:** ペア 64 Mi、文字列プール 1 GiB、ベクタ 64 Mi、ベクタ要素 128 Mi。どれかを超える倍率は実行できません。
  特に **aha-mont64 は m_w = 1 でしか実行できません**(m = 1 で約 50.3 M ベクタを使います)。statemate は燃料により m_w = 1 です。

許される値は `tools/repro_lib.py:feasible_multipliers` で確認できます。新しいコミットと倍率表の場合:

```
# 1. コンパイラの連鎖とイメージ(固定値がまだないので記録する)
python3 bench/embench/reproduce-20261015/b_build.py --round rounds/<name>.json --out /tmp/r-b --record bench/embench/reproduce-20261015/expected/<name>
# 2. 新しい n_w での期待値を信頼できる参照から導出(候補からは決して導出しない)
python3 bench/embench/reproduce-20261015/c_reference.py --round rounds/<name>.json --out /tmp/r-cref --write bench/embench/reproduce-20261015/expected/<name>/expected-accounting.json
# 3. 新しいイメージの完全一致
python3 bench/embench/reproduce-20261015/c_exactness.py --round rounds/<name>.json --images /tmp/r-b/step4-images --out /tmp/r-c
# 4. 計時
python3 bench/embench/reproduce-20261015/d_timing.py --round rounds/<name>.json --images /tmp/r-b/step4-images --upstream /tmp/embench-iot --out /tmp/r-d
```

その後、記録したファイルを設定の `pins` と `expectedAccounting` に追加すると、以後の実行は記録せずに比較します。公式ラウンドの
記録は、`records/` と同じ構成に並べれば `a_offline.py --round` で検証できます。

## 8. 訂正版の同一アルゴリズムラウンド(m104、2026年10月15日)

このブランチ `claude/embench-same-algo-m104-reproduce-20261015` は、同一アルゴリズムのみのコンパイラのソースである
コミット `a9edc1f0d5021efabf6864e70c5b92d59257f348` を基にしています。`be7f0ce3` と `ffa4cfc1` が祖先なので、上の m93 ラウンドも
このブランチから再現できます。ラウンド設定は `rounds/sa-m104-20261015.json`、データは `round-sa-m104-20261015/` にあります。

* **コンパイラ。** `e5fc0ca2b6996deb1bf4722d285790eab2a35ea9724904f5cf2be296943d702d`。連鎖は公開ブートストラップ →
  ステージ A `5583a2fd…` → G1 = G2 = G3 = `e5fc0ca2…` で、計測したコンパイラは不動点です。19 イメージはすべて計測時のものと
  一致します。
* **カーネルの範囲。** 同一アルゴリズムのみ(`audit/KERNEL-POLICY.md`)。SHA-256 暗号命令は使わず、sha256 はスカラー経路で
  実行します。
* **プロトコル。** m93 と同じものに、以下を加えています。全文は `round-sa-m104-20261015/records/round/protocol-revision.txt` に
  あります。
  * **Amendment 3:** すでに計時したイメージと同一のイメージを再び計時してよいのは、倍率が強制される場合だけです。該当するのは
    aha-mont64 で、ローダの上限により m = 1 に固定されます。
  * スクリーンは 0.85 秒で、R_w は m43・m87・m93 から較正します。
  * **Amendment 4:** 最大の実行可能な m にあるワークロードは 0.6 秒以上で受け入れます。該当するのは matmult-int で、予測は 0.78 秒、
    m93 での m = 8 の区間は 0.777 秒でした。
* **結果。** **Kotoba / C = 0.8213**(過去の m93 は 0.7999、round114 は 2.688)。Kotoba 19/19、C 19/19 が
  採用され、すべて 1 回目の試行で、すべて完全一致でした。レポートは翻訳ポートの探索的結果と分類し、
  `officialUnmodifiedCScore` は `false` です。検証:`PASS_INDEPENDENT_SA_M104_RAW_CUSTODY_MULTIPLIER_FORMULA_V1`。
* **ノイズ確認(Amendment 3)。** aha-mont64 は m93 と同じイメージと n でした:2.039 秒に対して
  m93 は 1.953 秒(×1.044)。このサイクルの C の経過時間の幾何平均は m93 の
  ×1.044 で、ホストは両アームとも約 4 % 遅く動いていました。
* **crc32** は m93 と同じイメージですが、新しい n である m = 2 で計時しました。

検証は、同じコマンドに `--round rounds/sa-m104-20261015.json` を付けて実行します(英語版 8 節のコマンド例を参照)。

| ワークロード | m_w | 比 (4/m_w)·K/C | m93 の比 | 変化 |
|---|---|---|---|---|
| aha-mont64 | 1 | 0.8688 | 0.9036 (m1) | 0.961 |
| crc32 | 2 | 0.6766 | 0.7084 (m1) | 0.955 |
| depthconv | 16 | 0.2660 | 0.2645 (m16) | 1.006 |
| edn | 4 | 0.9328 | 0.9503 (m2) | 0.982 |
| huffbench | 2 | 1.1586 | 0.6661 (m4) | 1.739 |
| matmult-int | 8 | 0.3093 | 0.3219 (m8) | 0.961 |
| md5sum | 2 | 0.5756 | 1.0322 (m2) | 0.558 |
| nettle-aes | 2 | 0.9080 | 0.7804 (m2) | 1.164 |
| nettle-sha256 | 2 | 1.0088 | 0.4158 (m2) | 2.426 |
| nsichneu | 4 | 0.3995 | 0.4096 (m4) | 0.975 |
| picojpeg | 2 | 1.4065 | 1.6002 (m2) | 0.879 |
| qrduino | 1 | 1.2088 | 0.5073 (m2) | 2.383 |
| sglib-combined | 1 | 1.1563 | 1.6124 (m1) | 0.717 |
| slre | 1 | 1.1689 | 1.8806 (m1) | 0.622 |
| statemate | 1 | 1.4356 | 1.3549 (m1) | 1.060 |
| tarfind | 2 | 0.7177 | 0.6575 (m2) | 1.092 |
| ud | 4 | 0.7559 | 0.7333 (m4) | 1.031 |
| wikisort | 8 | 0.7935 | 0.9646 (m8) | 0.823 |
| xgboost | 1 | 1.5184 | 1.9575 (m1) | 0.776 |

## 9. 2台目の Apple M4 Mac mini による計測(2026年10月16日)

`round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/` は、別の M4 Mac mini (`Mac16,10`、16 GB、macOS 26.3.1)で、訂正版 M104 を全19 workload再計測した記録です。変更していない計時スクリプトと固定 upstream コミット `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`を使い、Cは Apple clang 21.0.0で新規ビルドしました。両アーム19/19が採用され、raw idleと推定background idleを含むプロトコル条件を満たしています。GMは **0.7877703355587422** です。`verify-record.py`は全raw行、Kotobaの完全一致、CPUゲート、各比率、全19のGMを独立に照合します。これは翻訳ポートの比較であり、公式Embench結果やSPECスコアではありません。元のM4サイクル0.8213とはホストごとに分け、平均していません。
