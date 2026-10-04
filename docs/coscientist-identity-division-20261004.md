# C 比較に向けた co-scientist 第1回: identity division

2026-10-04。C 超えは未達。仮説 → 出力コードへの試作 → 実測 →
実装 → 正しさ・自己再ビルド → C との再比較、の順で進めた。
対象は自己ホスト seed の AArch64 バックエンド。製品の統合イメージや
記録済み rung を切り替えたという報告ではない。

## 実装と結果

`quot x 1` が MOV と SDIV を生成していた。これは全 i64 値で恒等演算
なので、既存のレジスタ割り当てを使って MOV 一つ、同じレジスタなら
ゼロ命令にした。ゼロ除算、MIN/-1、fuel、ABI は変更していない。
新規の局所的な生成判断なので手編集した。生成テストは既存の
`scripts/seed/a64gen-fixtures.py` から再生成した。

asher (Apple M4、macOS 26.2)、同じネイティブランナーで、順序を
ローテーションして各 30 サンプル。各サンプル 30,000 呼び出し、
事前 warmup 1 回を計時外で実施。負荷の最大値は 2.05。
LCG の 10,000 回の反復と毎回の signed-i64 `quot ... 1` を対象とし、
全 90 サンプルの答えを独立に算出した値と照合した。
C は同じ wrapping-u64 反復の C11/Clang -O2 実装。

| 実装 | 平均 / 呼び出し | 標準偏差 | 判定 |
|---|---:|---:|---|
| r6m | 25.765 µs | 1.599 µs | 比較元 |
| 新 seed | 9.330 µs | 0.648 µs | r6m 比 2.762 倍、時間 63.79% 減 |
| Clang C11 -O2 | 9.249 µs | 0.371 µs | C と新 seed の差は非分離 |

新 seed と r6m の平均差 16.435 µs は両者の標準偏差の和 2.248 µs
を超える。C との差は 0.081 µs、標準偏差の和は 1.019 µs で、
新 seed の平均は C より 0.87% 遅い。C に勝ったとは判定しない。
これは専用の算術試験であり、Embench の得点ではない。

保存する測定スクリプトでも、同じバイナリを使って 90 サンプルを
再測定した。r6m 24.697 µs、新 seed 8.969 µs、C 9.080 µs。
r6m 比 2.754 倍を再現したが、C 比の改善は 1.22% に留まり、
平均差 0.110 µs は標準偏差の和 0.218 µs を超えない。
どちらの測定でも C 超えの判定は通らない。

## 検証

- 135 個の命令生成 fixture、786/786 実行ケースが通過。MIN、MAX、
  レジスタの重なり、深い一時値、既存の拒否・trap を含む。
- r6m でテストをコンパイルし、新 seed 自身でも再コンパイルして一致。
- ネイティブの世代 1、2、3 がバイト一致。787,280 B、
  SHA-256 `bc0b31ae1abbdacf9738160b691ca610018dcdd06add700d89f1d5577cbeaad7`。
- 専用試験の出力は 112 B → 104 B。意図した SDIV が消えた。
- 既存 Embench 19 ポートを新 seed で再生成したが、19/19 が r6m
  とバイト一致。したがってこの変更による Embench 改善はない。
- 製品の Node/JVM/nbb 依存数は増えていない。新しい測定プログラムは
  bootstrap tooling。製品イメージ・`bin/amu`・rung 記録は未更新。

## 採用しなかった試作

| 仮説 | 観測 | 判断 |
|---|---|---|
| 定数 2/3/32 の除算を shift / magic multiply にする | 短い測定では改善が出ない | 採用せず。長い領域での再測定が必要 |
| MUL + ADD を MADD にする | 行列ポートの試作は平均 202.715 → 204.524 ms | 採用せず。NOP を残す試作なので命令を詰めた実装の限界は証明していない |
| ASCII 経路の context 再読み込みを消す | 短い文字列試験で有意な改善なし | 採用せず。非 ASCII 経路を含む実装には進んでいない |
| `quot x 1` の SDIV を消す | 実装前の試作が 30 組で 2.751 倍 | 実装し、境界値と固定点を検証 |

短い測定、平均の符号だけ、ばらつき内の差を採用理由にしない。
一部の試作は対象を限定した命令パッチであり、汎用変換の正しさを
証明するものではない。

## 次の設計

1. **比較する処理を揃える。** 9 個の full-correctness ポートについて、
   初期化・本体反復・検証を分け、C と同じ反復量を計時する。
   簡略ポート 10 個を含めた総合点を公式 Embench と呼ばない。
2. **判定器をネイティブ経路へ移す。** 既存の perfgate launcher は
   JVM 経路削除のため REFUSED のまま。今回の数値判定は診断用で、
   provenance、ホストの完全な資格検査、正式 claim validator を代替しない。
3. **大きな差を優先する。** 既測定の XGBoost、depthconv、ud の差から、
   読み取り専用データの表現、短い helper のインライン化、ループの
   範囲証明を調べる。すでにある ASCII 高速経路・定数テーブル最適化を
   重複実装しない。境界検査や fuel を削る案は、意味を保つ証明を先に置く。
4. **C 超えは個別に判定する。** 少なくとも平均 5% の改善、両者の
   ばらつきを超える分離、正しさ、再現可能な入力と生成物を要求する。
   一つの専用試験の改善を全 Embench の改善に広げない。

[ADR 0368](adr/0368-measured-seed-identity-division.md) と
[実測データ](evidence/coscientist-identity-division-20261004/candidate-results.json)、
[再測定](evidence/coscientist-identity-division-20261004/candidate-results-rerun.json)、
[ビルド証拠](evidence/coscientist-identity-division-20261004/build-proof.json)、
[Embench コード比較](evidence/coscientist-identity-division-20261004/ports-comparison.json)
を保存した。`artifacts.tgz` は seed、unity source、試作コード、実測 C
バイナリ、元と新しい試験バイナリを含む。

再測定用の `scripts/seed/research/measure-identity-division.py` は証拠用
ディレクトリを引数に取る。ディレクトリには `div-one.bin`、
`div-one-candidate.bin`、`div-one.c` を置き、親ディレクトリに同じ
`runner` を置く。測定中の負荷上限、答え、反復数、最低計時長を
満たさなければ停止する。
