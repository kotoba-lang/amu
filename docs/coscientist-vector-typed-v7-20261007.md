# 型付きベクトル解析V7：出辺索引はalias段階を進めたが候補数は未達

V7は、全呼び出し辺の収集後に、callerごとのhead128語とnext512語を既存の予約領域に構築する。辺を逆順に登録し、索引をたどる順序は元の辺番号の昇順を維持する。FN・辺・caller・target・nextの範囲と厳密な昇順を確認してから読む。部分構築で作業上限に達した場合は、後続queryへ進めない。SCC探索のtarget-before-visited、深さ64の拒否、直接自己辺の除外、visited消去を維持した。

既存vw-old1152..1791の640語を使い、幅・bounds・visited・rootと重ならない。新しいheap確保はない。50177語の全初期化確認・後片付け、work cap268435456、既定OFF、候補や生成の条件を維持した。5 helperと3定義だけが変わり、4ソースvariantは逆適用するとV6と完全一致する。

事前登録済みの順序付きgraph model2は1,669ケースで結果と実際の辺訪問順序が一致する。全3FN graph512個、重複辺、深さ64境界のchainを含む。逆順・帰属違い・循環・辺欠落の誤実装を検出した。初回modelの逆順検査は期待リスト比較だけだったため保存し、実際の逆順head/nextを実行するmodel2へ事前追記して改善した。独立担当の容量・帰属650ケースと不正link11ケースも通った。これは抽象モデルとソース検査であり、全入力の機械証明ではない。

Amu製ネイティブコンパイラの4世代は924,032 B、offset0、SHA-256 `3942ae3b5b7fd7edae054b1867ae08b7a048a1601bef3dc6787951d5776c802e`で一致した。自己ビルド8件・診断版生成2件・元のEmbench19本の生成抽出38件が成功した。全19本のKSEED全体・native・ソース・export offsetはcharged baselineと一致する。SIR/FREC・全43候補tuple・CACHE/EMITもV6の実結果と一致した。ベンチマーク本体と性能計測は0件。

| 結果 | V6 | V7 |
| --- | ---: | ---: |
| 完了／work拒否／FN拒否 | 15／2／2 | 15／2／2 |
| 全体semantic／compatible | 43／33 | 43／33 |
| 重点compatible／本数 | 16／3 | 16／3 |
| PicoJPEGの拒否段階 | alias5 | shape6 |
| QRduinoの拒否段階 | shape6 | shape6 |
| 実際の分岐省略 | 0 | 0 |

PicoJPEGはalias段階を通過したが、shape段階で同じ上限に達した。完了数・候補数は増えず、重点32か所・3本の条件はFAILのままである。完了した他のモジュールで作業量の削減が見えても、その単位はCPU命令数や時間ではない。実行性能の改善として数えない。

全19本の参照モデル行を再計算し、公開43候補のtuple/identityと実生成経路を独立照合した。参照85候補のうち42候補が未公開であり、全候補再現ではない。初回のsource lexical failureとreader設定失敗を保存し、期待値・source意味・判定条件は変更していない。

全M・外部arena・ABI/資源同値、厳密なCPU作業量定理、候補を使った生成と意味保存、低負荷性能、製品採用は未完了。別のnative追加領域検査・後続のshape query profilingをこの証拠に含めない。製品source44bfaa28c/native761856bb…は維持し、全19本でC以上の性能と公式Embenchスコアは未達成。

次はstage/query/roundの実際の作業量を診断し、shape解析の繰り返しを調べる。同じ入力boundsの反復だけではキャッシュの正しさは証明できず、alias/effect/contextと外向きbounds更新・poison・拒否の扱いも検証する必要がある。

固定済み[三ファイル証拠と再生手順](evidence/coscientist-inverse-aes-20261007/vector-typed-v7/README.md)は、archive 4,682,062 B、SHA-256 `cccb778beea4bde1829c43bab57adaea22bd58263dcb9e7b77d4a3c320b9c09f`。object展開35,273,362 B、455 logical paths／322 objectsで登録済み5 MiB／64 MiB上限内。担当の新規コピー2回とrootの新規三ファイルコピー再生はPASS、破損envelope2種は拒否した。root再生は8自己ビルド・40診断・全19参照行・43公開tuple／42未公開・重点16か所／3本を確認し、適用可能性32／3はFAILと報告する。再生でnative・benchmark・性能測定は実行していない。
