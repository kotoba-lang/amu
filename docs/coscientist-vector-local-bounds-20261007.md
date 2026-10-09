# 解析結果の再利用から生成命令の省略へ

状態：既定で無効な実験。製品への採用、C以上の性能、公式Embenchスコア、製品100% selfhostの達成を意味しない。

[ComputeCID / ResultCID契約](coscientist-compute-addressed-analysis-20261007.md)を、解析要求と検証可能な結果・状態更新を分ける契約として使う。永続キャッシュ、native CID符号化、共有ストアを実装した記録ではない。最初の実装は同一コンパイラactivation内の不変な解析文脈と、生成後に消去する証拠領域を使う。CID一致だけでチェックを省略しない。

## 実測した最初の生成コード

候補コンパイラはAmuのnative compilerから作った936,688 Bのイメージ、SHA-256 `c75d41f758231844be1c1ca49124068eeed85e72a073803d73ba5ae00783289c`。比較基準は929,424 B、`2a0d9a3b47dab57ca8b52532e7ce5c9cff9b189de1e62af564b9436646dd239b`。Node/nbb/JVMでfixtureをコンパイルする代替経路は使っていない。

対象はprivate関数内の `vector-alloc 4`、`vector-assoc!` index 0、`vector-at` index 0。元のEmbenchワークロードを置き換えるものではない。

事前登録した最大10呼び出しを実行し、4コンパイル・抽出と6機能確認が終了した。入力は両生成物に0、7、-1。全呼び出しexit 0、stderr空。

| 観測 | 比較基準 | 候補 |
| --- | ---: | ---: |
| 完全なnative payload | 260 B | 248 B |
| bench export offset | 232 | 220 |
| 戻り値 | 入力値と一致 | 入力値と一致 |
| fuel消費 | 2 | 2 |
| vector / item使用量 | 1 / 4 | 1 / 4 |

旧byte offset 180の `CMP 0xeb10015f`、`B.LO 0x54000043`、`UDF 0` だけを削除した。handle検査8命令、descriptor、pool、address、loadは維持。残る差は旧PC252から新PC240への分岐補正で、分岐先0は同じ。全残存命令と構造化された結果・fuel・arena出力を照合し、独立レビューも通過した。

これは単一の正例。無効handle・範囲外indexのtrap実行、全拒否条件、dirty/partial公開、全selfhostの保証を与えない。12 B削減は実行時間の測定ではない。

## 候補コンパイラの固定点

同じ候補ソース `d9cfe46b781ff57235d2e0284682d1a745bd166e0fc3a698399d5e3f9a3475eb` を、各世代のnative compilerで次の世代へコンパイル・抽出した。事前登録した6呼び出しが終了し、3世代すべて936,688 B、SHA-256 `c75d41f758231844be1c1ca49124068eeed85e72a073803d73ba5ae00783289c` で最初の候補とバイト一致した。完全なKSEED payload、唯一のmain export、offset 0も検査した。

手順の凍結連絡前にrootが読んだ旧driver `7cc61181f27c8538aaecc93ed6adec2d2477bb550c4011d3aba67469dbe3be0d` を承認・実行した。その後、authorが同じ場所に追加guardを持つ `ed592d238a4aa7656f9985e9c2d9f89b9aec83ba1870d2e89d96f1f6905306aa` を書いたため、最初の独立監査でdriver pin不一致を検出した。旧driverと当時のsource reportを元のハッシュに完全一致して復元し、失敗記録と新版を残した。新版の追加guardを実行済みとは扱わない。nativeの再実行はしていない。

これは実験用候補コンパイラの固定点であり、製品のcheck/compile/refactor全経路について100% selfhostを認定するものではない。

## 元の19本への適用範囲

元の19ソースをハッシュで固定し、候補コンパイラで最大38呼び出しのコンパイル・抽出を実行した。19/19の完全なnative payload、KSEED container、export tableとoffsetは従来V8生成物とバイト一致した。独立に実行記録と入力・生成物のハッシュを再確認した。速度測定の追加ではない。

凍結したV8観測を読む静的censusでは、916個のRT176 read、41個のRT200 allocation、85個の解析certificateを確認した。

| certificateの起点 | 件数 |
| --- | ---: |
| parameter | 64 |
| returned allocation | 20 |
| direct allocation | 1 |

今回のprivate・同一body・RT200という省略条件に該当するものは **0**。唯一のdirect allocationはexportされたqrduinoの関数で、この条件により拒否される。解析certificate件数を生成命令の書き換え件数と呼ばない。19本のバイト一致も、この狭い実装が性能改善を与えていないことと整合する。

## 次の仮説とComputeCID / ResultCID

最初の候補はnettle-sha256のprivate関数FN19にある8個のparameter起点read（SIR564,572,580,588,596,604,612,620）。最初のdesignはworkload全体の11件をこの関数へ誤って帰属させたため、独立のraw再確認で8件へ訂正した。全call edgeと外部入口を閉じ、すべての寄与の最小値を再適用し、未知・unsupported・short callerは0として拒否する。関数番号は観測の位置であり、実装をこのbenchmarkに特化させる条件ではない。

ComputeCIDはchecked body、全caller/依存/read footprint、alias/return/effect/lifetime、規則・ABI・trap・予算契約を封じる。ResultCIDはsupported/poison、全edge寄与、return identity、site/indexと診断を封じる。外部から呼べるparameterに内部callerの長さを流用しない。戻り値起点は全returnの下限とaliasを別途検査する。冷/温キャッシュの決定的なlogical chargeと生成バイト一致も必要になる。

statemateは540関数のため現行解析の関数数上限で拒否され、certificateがない。このbridgeだけで対応できない。別のSCC/context分割仮説が必要で、上限を単純に増やす変更はしていない。

今回の実験にEmbenchの性能測定はない。IPLD/CIDによる高速化、C超え、製品採用を主張しない。原始ログ・生成物・ソースの内容ハッシュと、独立レビューを[封印したcapture](evidence/coscientist-inverse-aes-20261007/vector-local-bounds/README.md)へ保存した。315ファイルの全ハッシュ検査は通過した。これは内容の検査であり、新しいnative再実行ではない。固定点の独立監査v3は、復元した実行時driverと当時のroot承認を照合している。
