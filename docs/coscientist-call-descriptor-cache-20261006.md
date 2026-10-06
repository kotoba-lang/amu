# Call descriptor cache: qualified performance gain absent (2026-10-06)

候補 `1177930937d2951e4e96463a58dd9b897a995496fcb280db4c78a231b6b6395e` は意味・ABI・固定点の検査に通ったが、元の Embench 19 本を新しく測り直すと、採用基準を満たす性能改善は **0 本**だった。変更した 12 本はすべて中立。**製品には採用せず**、現行の scalar DAG seed `761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93` を維持する。C 以上という目標は未達。

これは同じ M4 端末・同じ C 実行物を使う、元の 19 本の本体の比較であり、**公式 Embench スコアではない**。過去の統計との合算・改善率の積算はしていない。全 19 本の新しい幾何平均では候補の所要時間は 0.347048487% 短く、候補/C は 7.684154748 倍、現行/C は 7.710915363 倍だった。この平均差を最適化の成果とは判定しない。

仮説は、reset・未知の呼び出し・間接呼び出し・capability を含まない有限の直接呼び出し閉包で、vector の `(length, base, handle-key)` を新しい callee-saved 3 レジスタに保持するもの。元の初回アクセスで handle と添字を検証し、同じ key の後続読み出しでも要素は毎回ロードする。元の NSV が 7 以下の framed nonleaf/mode0 だけを対象とし、97 関数・276 実際の inline 読み出しが変わった。フレームは 16/32 B 増え、元の機械コード全体では 1,435 word 増えた。意味保存の検査だけでは速さを保証できない、という負結果になった。

## 新しい全19本比較

数値は本体 1 回あたり平均 ns。平均短縮率は `1 − 候補/現行`。負数は遅くなったことを示す。変化のない 7 本も同じキャンペーンで測定し、その差を最適化に帰属させない。

| 本体 | native変更 | 現行 ns | 候補 ns | C ns | 平均短縮率 | 候補/C | 判定 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| aha-mont64 | なし | 880.166 | 880.055 | 545.282 | +0.013% | 1.613945 | 中立 |
| crc32 | なし | 3361.957 | 3370.634 | 1706.528 | -0.258% | 1.975142 | 中立 |
| depthconv | なし | 123.940 | 124.300 | 34.925 | -0.291% | 3.559106 | 中立 |
| edn | あり | 11708.128 | 11604.898 | 762.952 | +0.882% | 15.210523 | 中立 |
| huffbench | あり | 54495.246 | 55425.698 | 7461.831 | -1.707% | 7.427895 | 中立 |
| matmult-int | なし | 3326.588 | 3304.081 | 956.924 | +0.677% | 3.452813 | 中立 |
| md5sum | あり | 11281.368 | 11292.401 | 2533.813 | -0.098% | 4.456683 | 中立 |
| nettle-aes | あり | 21623.939 | 21509.769 | 1421.689 | +0.528% | 15.129732 | 中立 |
| nettle-sha256 | あり | 2816.781 | 2728.793 | 222.677 | +3.124% | 12.254518 | 中立 |
| nsichneu | なし | 733.463 | 721.388 | 79.781 | +1.646% | 9.042066 | 中立 |
| picojpeg | あり | 218135.193 | 215429.845 | 11260.653 | +1.240% | 19.131203 | 中立 |
| qrduino | あり | 281514.426 | 278783.301 | 22466.754 | +0.970% | 12.408704 | 中立 |
| sglib-combined | あり | 36820.977 | 36798.716 | 5866.540 | +0.060% | 6.272643 | 中立 |
| slre | あり | 7784.087 | 7690.263 | 1054.441 | +1.205% | 7.293211 | 中立 |
| statemate | あり | 526.127 | 533.463 | 31.727 | -1.394% | 16.814340 | 中立 |
| tarfind | なし | 14513.593 | 14679.686 | 1007.445 | -1.144% | 14.571204 | 中立 |
| ud | あり | 544.003 | 540.984 | 54.700 | +0.555% | 9.890071 | 中立 |
| wikisort | なし | 185517.262 | 186064.210 | 15303.874 | -0.295% | 12.157981 | 中立 |
| xgboost | あり | 1190571.875 | 1181456.380 | 186459.100 | +0.766% | 6.336276 | 中立 |

30 accepted triples × 19 本 = **570 組**。651 組を試行し、81 組を棄却、raw arm samples は **1,953 件**。全 19 本で相対標準偏差は 10% 以下。各組は現行・候補・C の順を回転し、load ≤ 4、推定 background idle ≥ 90%、300 ms 目標・50 ms 最小区間、最大 90 試行を固定した。改善/悪化の判定には 1.05 倍以上と、平均差が双方の sample SD の和より大きいことを必要とした。qualified 改善・悪化・C以上はすべて 0。本条件を測定後に変えず、再測定して採用を狙うこともしなかった。

## 意味・機械コード・資源の一次証拠

- ネイティブ世代 2/3/4：865,400 B、同じ `117793…`、offset 0。候補ソースの内容ハッシュも固定。
- 元の 19 本：95 通常結果/正確な fuel、19 fuel1 traps が現行と一致。別途 161 resource + 209 fuel-prefix + 57 ordinary = 427 件の full-state pair、55 typed pair + 53 ABI sentinel pair、30 admission cases × 8 variants = 240 native runs を保持。535 full-state/ABI pair と 240 admission native run は別々に保持し、件数の種類を混ぜて一つの互換率にはしない。
- 合成 admission 30 cases、実装ソース fault 6 件、1-visit budget fallback、同一 M の closed/open/closed を検査。saved key restore を壊した実際の機械コードでは ABI sentinel が検出。
- 独立機械コード監査：97 関数、276 読み出しの正確な新ブロックと frame/home 移動を説明した上で、残る 80,739 tokens、15,658 分岐、FN/event offsets、fixups、literal pools を全部比較。8 actual machine corruptions を検出。97 全閉包の SIR と共有 131,072 scan budget の証跡も再計算して一致。
- 既存 permanent 593 fixtures / 25,658 native observations、readonly 9 programs / 117 observations、scalar DAG 16 programs / 318 observations を検査。5227 行の正式 41-a64gen unit 出力は既存 golden と完全一致。BUILD・ERR・G1〜G5 も通過。期待値・golden・製品ソースはこの候補のために変更していない。
- timing raw 校正・順序・CPU tick・load・fuel・平均・SD・判定を再計算し、11 deliberately corrupted packet controls を検出。

これらは有限の型付き例・既存不変条件・保持した観測の証拠であり、一般の compiler soundness の証明ではない。新しい saved bank により OS stack 消費が増えるので、全 stack-limit 境界の等価性は未証明。コンパイル時の closure scratch allocation の全予算境界も未証明。診断 full-state loader が remaining fuel 0 を trap とする扱いは、製品 loader の一般規則と同一とは主張しない。

## 保存と再検証

[証拠ディレクトリ](evidence/coscientist-call-descriptor-cache-20261006/README.md) の `native-replay.py` と `timing-replay.py` は、archive のハッシュと安全な展開を検査して、選択した raw 記録・元のソース数学・機械コード・呼び出し閉包・判定をオフラインで再計算する。fresh isolated replay は両方通過。ネイティブ guest・compiler・solver・timing は再実行しない。

`native-origin-pins.json` と各 owner inventory は、元の外部ディレクトリの内容識別・来歴を記録する。すべての元ディレクトリを梱包したという意味ではない。`native-selected-payload-pins.json` は独立 native archive に実際に含めたファイルだけを列挙し、これが選択 payload の完全性の境界である。タイミング archive にも選択 payload のハッシュと一回限りの raw records を含める。リポジトリ全体や無関係の build は複製していない。

候補 source/frame/closure/native は実験証拠としてのみ保持する。性能が中立なので、この候補を統合製品へ昇格させる後続ビルドは行わず、C 以上の目標は継続する。
