# ComputeCID / ResultCID を解析再利用へ接続する

状態：設計・事前登録。永続キャッシュ、IPLD の符号化、ComputeCID の native 実装を追加した記録ではない。既存の V8 shape memo と、既定で無効な局所的 bounds-check 省略候補へ、この契約を接続する。

## 二つの内容アドレス

`ComputeCID = CID(canonical calculation request)` と `ResultCID = CID(canonical semantic result)` を分ける。ComputeCID も計算要求の **content address** であり、計算の正しさを保証する別種のハッシュではない。計算前に検索できる要求と、計算後に得る内容を別々に識別する。DefCID は変更しない。

Bazel の action cache と CAS は、要求から結果への対応と結果の内容保管を分ける参考になる。[公式資料](https://bazel.build/remote/caching)。ただし CID が一致しても、要求を正しく評価した結果だという証明にはならない。

### ComputeCID が封じるもの

| 要素 | この解析で必要な内容 |
| --- | --- |
| domain / schema | query 種別、符号化版、計算契約版。DefCID・ResultCID と domain を分離 |
| evaluator | 実際の解析実装と transitive implementation dependencies の CID |
| subject | 型付き定義または厳密な SIR/FREC snapshot の CID、再帰群、依存閉包、edge の対応 |
| read context | effect・alias・lifetime・return bound・parameter mapping・support・poison と、読み取る解析結果の CID |
| input | 全4入口 bound、query mode、candidate、必要な根・公開境界情報 |
| rules | 方向・工程・前提・停止条件・cost model を含む規則群と設定の CID |
| semantics | 数値幅・overflow・trap・target・ABI・descriptor・fuel の意味を規定する契約 |
| resources | 予算の種類と版、admission / logical charge 契約。必要な残量や限度 |

読み取り集合が不明な query は共有再利用しない。読み取り順に意味がある場合は順序も保存する。依存の集合と順序付き列を勝手に同一視しない。型・effect・trap の解釈、規則または ABI が変わったら別の要求になる。

既存の [definition identity](../src/kotoba/compiler/definition_identity.cljk) は、checked KIR・profile・desugar・effect・interface・直接依存を扱う。native SIR/KSEED 経路から同じ DefCID へ接続した証拠は、この実験では持っていない。最初の共有実装は厳密な snapshot identity を使い、名前変更や宣言順変更での共有は拒否してよい。native の DefCID bridge と正規化を検証するまで Unison 的な rename cache hit を主張しない。SHA-256 の hex をそのまま IPLD CID と呼ばない。

### ResultCID が封じるもの

結果は純粋な値だけではなく、検証できる再適用データを含む。

```
semantic-result
ordered per-edge contributions: stable-edge-ref, stable-target-ref, ordinal, bound
supported / poison / semantic diagnostics
replay schema and preconditions
observable charge / effect / trap observations, if the query contract includes them
```

shape の bound は非負値、neutral は -1、未知長・poison の寄与0は neutral と区別する。保存する寄与は元の全訪問を集約した値であり、最後の訪問だけではない。ヒットは新しく初期化した callee 集計に元の meet 規則で再適用する。集計済み状態での冪等性だけを根拠にしない。

共有データに activation の FN 番号・edge index・scratch のメモリアドレスを保存して使い回さない。安定した参照を、その要求が封じた現在の graph へ一意に解決し、型・arity・ordinal・呼び出し位置も検査する。解決できなければ miss とする。

解析時間、CPU 時間、host load、キャッシュヒット率、scratch の途中値は semantic ResultCID に混ぜない。観測可能な fuel・診断・trap が契約に入る場合は省かない。物理的な作業量と必要な再現性証拠は、ComputeCID / ResultCID を参照する別の receipt に置く。キャッシュヒットを実際の query 再実行として証言しない。

## V8 と emitter 候補への対応

V8 は **activation 内の exact memo** である。同じ SIR/FREC、phase4 effect/lifetime、phase5 alias/return、mode1 の不変な view を保持し、その中で全4入口 bound を厳密比較する。これはプロセスをまたぐ ComputeCID ではない。不変な view を変えたら同じ小さいキーを使ってはいけない。

[V8 の実験](coscientist-vector-typed-v8-20261007.md)は、辺ごとの4寄与を保持し、元の neutral/min 集約で再生する。mode0 の alias query と mode2 の証明生成へ同じ memo を流用しない。valid は reset 前に無効化し、完了した query と key の保存後に公開する。途中拒否、作業上限、部分書込み、unsupported query は再利用しない。

[型付き native 制御試験](coscientist-vector-shape-memo-typed-controls-20261007.md)は、固定した5関数で寄与4・未知長0・実際の自己呼び出し neutral を検査した。全5関数の新しい集計への再生も直接解析と一致した。これを Result の状態更新契約の有限な証拠として使う。IPLD、永続化、一般的な意味保存の証明とは区別する。

局所的 bounds-check 省略候補は、解析の証明情報を module-owned の別領域へ移し、生成終了時に消去する。[局所割当の native 検証](coscientist-vector-local-bounds-20261007.md)を経て、private 関数の引数への寄与を封じる候補も有限の native 検証を通った。後者の現時点の範囲は、下記の1 fixture・3入力だけである。その証明情報は将来 ResultCID と結び付けられるが、識別子だけを emitter の許可条件にしない。現在の SIR・private body・割当または全呼び出し元の確定した寄与・定数 index・ABI・lifetime の検査を維持する。SSA、effect、trap を保存する規則の前提と検証結果は provenance に明記する。

### 引数への状態更新を封じる最初の有限な証拠

実験用 native compiler は `4158d7de2dfe4d922450b60788bb5f6a950ca129f92f0b841069aa4c0f76b509`、ソースは `ea8281843170b65999ff5a6460a2ba2b3474f04e8e5fda8abc616bf283a0acf5`。どちらも SHA-256 であり、native IPLD CID の実装ではない。

private `read-param(v, n)` が `vector-at(v, 0) + n` を返し、公開された呼び出し元が長さ4のベクトルの要素0へ `n` を入れる fixture で、全呼び出し元の寄与と現在の解析キーを確認して証明を封じた。生成物は276から264バイトになった。差は `CMP / B.LO / UDF` の12バイト削除と1分岐の位置補正のみで、handle 検査・descriptor・pool・address 計算・load は保持された。

`n=0,7,-1` で結果は両方とも `0,14,-2`、fuel は `16777216→16777214`、heap/string 使用量0、vector1個・items4個で完全一致した。compile/extract 4回と機能確認6回を上限10回で実行し、独立レビューは raw bytes・ログ・入力・GO の対応を再実行なしで確認した。owner report SHA は `030ab5a7717f722d2dd6e9c1175badaea85eaa9f3f375a4f9e6fecba546322b2`、独立 raw review SHA は `18aefab19a094c983bd1fe6c3d19eb9b42114602095baf438e7d1dcaf1dd1a9b`。

ソース・native compiler/loader・有限 GO・生成物・機能ログ・独立レビューは[封印した証拠](evidence/coscientist-inverse-aes-20261007/vector-param-positive/README.md)に保存した。archive SHA は `257ec431b2629bcb09af8a36c77e0007d7be53f8b2cb05776fe99b4cd6fddb32`、69 member・展開4,267,707バイトを抽出・実行なしで全件照合した。元の絶対パスを含む実行記録であり、portable な再実行手順ではない。

この証拠は、解析の値だけでなく呼び出し辺の寄与と再適用条件を保持する設計を具体化する。永続保存・共有 import・cold/warm cache の同一性・一般的な意味保存の証明・Embench の速度向上は証明しない。未知の入口、短いベクトル、自己再帰、returned-origin の拒否と元の19本は、別の事前登録した検査として扱う。実験は既定で無効で、製品採用の変更ではない。

続く[parameter bounds checkpoint](coscientist-vector-param-bounds-20261007.md)では、3世代のnative/KSEED一致、元19本の13か所の登録済み省略・12本の完全一致・4本のHOLD、拒否スイートの46回目でのFAIL停止を記録した。これは永続キャッシュやC以上の性能の証拠ではない。

## 予算と再現可能な生成物

予算をキーに含めるだけでは不十分である。ヒットが物理的作業を節約し、以前は上限に達した後続解析まで完了させると、冷たいキャッシュと温まったキャッシュで採用される最適化が変わり得る。同じ BuildCID から異なる生成バイトが出る状態は、この selfhost 実験では受理しない。

V8 は各 activation の空の memo から始まり、共有された warm state に依存しない。永続・共有キャッシュの初版は既定で無効とし、同じ入力・設定について cold / warm / shared-cache disabled の成果物と exports が一致するまで採用しない。このバイト一致ゲートでは activation-local memo と最適化設定を同じに保ち、共有 cache の可用性だけを変える。異なる最適化設定の比較は、別の意味保存・性能実験として扱う。

永続版の候補は、決定的な logical admission / charge と物理作業の計測を分ける方式である。記録した charge の再利用には、その charge が読む状態も要求へ封じる。callee 集計などで元の charge が変わる場合、現在の小さい4要素キーだけでは不十分である。charge 契約を新しく定義するなら意味論版を変え、予算境界の拒否・結果・生成バイトを比較する。物理上限による拒否を、ヒットの有無で異なる最適化を選ぶ隠れた条件にしない。

言語が観測する fuel・課金は別の契約である。必要な消費とその順序をヒットでも保存する。外部書込み、現在の権限判断、時刻や乱数を読む query は最初の共有対象から除外する。以前の署名や receipt は現在の権限判断を代替しない。

共有 importer は、decode 前の符号化サイズ、展開サイズ、深さ、参照数、edge 数、要求・結果件数に上限を設け、サイズを検査してから確保する。decode・hash・materialize・参照解決・検証・replay・保管・eviction・cleanup の全経路を物理資源の計測と上限の対象にする。超過や改変は cache miss として同じ決定的な解析を行うか、action 全体を失敗として記録する。fallback の物理予算も不足した場合、別の最適化を黙って選ばない。異なる fallback を提案するなら、決定的な規則として別に事前登録し、cold / warm の生成バイト一致を検証する。これらの importer と上限はまだ実装していない。

## Result が同じ場合に止められる範囲

入力が変わって再評価しても ResultCID が同じなら、**その結果だけを読む**下流 query は再利用できる可能性がある。これは依存結果を比較する増分計算の考え方である。[query の公式解説](https://rustc-dev-guide.rust-lang.org/queries/incremental-compilation-in-detail.html)。Rust をビルドや実行の依存には加えない。

下流が変わった DefCID、型・effect・ABI、graph 構造も直接読む場合は、同じ ResultCID だけで停止しない。Result の一致と、下流の完全な read footprint の一致を両方検査する。結果が同じでも、新しい要求との検証済み対応を記録する。payload の semantic fields を実験中は厳密比較し、digest の一致だけで比較を省かない。

## 事前登録する比較

1. cache disabled / activation-local memo / 将来の persistent memo を別々に扱う。元の19入力と同じ compiler・target・ABI を固定する。
2. 結果だけでなく、初期化した集計に再適用した全寄与、support、poison、診断、観測可能な charge を照合する。
3. 上表のキー要素を一つずつ変え、必要な miss が発生することを確認する。依存の追加・削除・再帰群変更、edge の入替えも含める。
4. valid 公開の各 prefix、中断、途中拒否、改変・不正な参照・古い schema を拒否する。CAS の内容検査と ComputeCID→ResultCID の計算対応の検証は別々に行う。
5. 異なる要求で同じ結果を得る場合、完全な結果の一致と下流の read footprint 条件を確認する。異なる poison・診断・target update を同じ結果として扱わない。
6. 同じ activation-local memo・最適化設定で、cold / warm / shared-cache disabled の生成バイトと exports、3世代自己再ビルドを照合する。生成バイト一致を result-value parity に緩めない。
7. 同じ低負荷の条件で、入力符号化・hash・検索・検証・再適用・保管の全費用を含めて解析時間を測る。生成物の実行時間と分け、CID の性能寄与は cache 有無の ablation で測る。現在の Embench 高速化を CID の効果とは呼ばない。

最初の実装範囲は純粋で完了した shape query に限定する。canonical encoder、read-footprint extractor、安定した graph reference bridge、検証済み対応の publisher / importer、決定的 charge は未実装である。この設計は、既存の局所 memo とコード生成候補を進めるための契約であり、共有 cache を製品へ有効化する変更ではない。

## 計算結果の再利用を進める実装順序

計算要求のアドレスと結果のアドレスを分ける提案を、次の三段階で検証する。最初から共有キャッシュを有効にせず、現在の native shape 解析を基準にする。

| 段階 | 実装するもの | 採用条件 |
| --- | --- | --- |
| C0：activation 内 | 同じ不変な解析 view の下での厳密キー、結果と全辺への寄与の保存・再生 | 新しく初期化した集計への再生、neutral / unknown / poison、完了後公開の有限検査。既存 V8 はこの段階の証拠 |
| C1：shadow receipt | 正規化した要求・結果の native 符号化と安定参照。直接解析を毎回実行し、保存結果を別の新しい集計へ再生して比較 | 要求・結果の全 semantic fields と更新が一致。receipt を読むだけで解析を省略しない |
| C2：検証済み再利用 | 同じ符号化と参照解決で、完了した純粋 query の計算を省略 | cache disabled / cold / warm の生成バイト・exports・論理 charge が一致し、全費用込みの解析時間に改善がある |

C1 / C2 は未実装である。C0 の証明情報を emitter が使う場合も、現在の型・effect・trap・private boundary・descriptor の検査を保つ。ComputeCID→ResultCID の対応を取得しただけでは省略を許可しない。

最初の C1 実験では、対象を固定した shape query、読み取る graph snapshot、全4入口 bound、解析実装、規則、ABI、資源契約を一つの要求に封じる。直接評価の結果と、**空の callee 集計**へ保存寄与を再生した結果を比較する。共有 importer と同じ参照検査を通し、activation 内の番号をそのまま移植しない。失敗した比較は保存結果の利用を止め、失敗 receipt を残す。

### 失効と再生の対照実験

| 一つだけ変える入力 | 期待する扱い | 確認する観測 |
| --- | --- | --- |
| 入口 bound、alias、effect、lifetime、return、support、poison | 別の ComputeCID、古い結果は miss | 直接解析と同じ結果・全辺更新・拒否 |
| 解析実装、規則、工程、停止条件、数値・trap 意味論、ABI | 別の ComputeCID | 古い証明で新しい emitter の省略を許可しない |
| 読み取る依存結果または graph edge の対応 | 別の ComputeCID | arity・ordinal・参照解決と全 incoming meet |
| 物理的な cache の有無・検索順 | 同じ計算契約のまま | 同じ生成バイト・exports・意味上の診断・論理 charge |
| 観測可能な fuel / admission 状態 | 契約が読む値を要求へ含める | 必要な消費・順序・予算境界の拒否 |
| 再評価後に ResultCID が同じ | 完全な下流 read footprint も同じ場合だけ下流を再利用 | 値に加え、更新・poison・診断・charge と直接入力の一致 |
| 保存途中の prefix、改変 payload、古い schema、不正参照 | 公開または import を拒否 | 有効な対応を残さず、部分更新を集計へ適用しない |

性能の仮説は二つに分ける。C2 は重複する**コンパイラ解析**を減らす仮説であり、正しい証明情報に基づくチェック省略は**生成プログラムの実行**を短くする仮説である。同じ成果物なら C2 だけで Embench 実行時間は変わらない。解析費用の比較には符号化・hash・lookup・検証・replay・保管を含め、実行性能は同じ元19本と C を同じ host で別に測る。両方の改善を一つの CID 効果として集計しない。
