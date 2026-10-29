# 型付きベクトル解析V8：shape再解析のメモ化で候補を回復

V8は、同じ解析activation内で、caller自身の4個のboundsと固定のSIR・effect・alias条件が同じときに、完了したshape queryの外向き寄与を再生する。各辺・引数の全訪問から最小値を保持し、`-1`は寄与なし、`0`は未知・poisonとして保存する。元のcalleeへの更新も維持する。callerのkeyだけを共有キャッシュの識別子として使う設計ではなく、固定されたactivation文脈が前提になる。

メモ化は既定OFFの実験である。4keyを新しい512語に保存し、valid128語と辺ごとの寄与2048語は既存領域を使う。V7のhead128／next512は保持する。全50689語の初期化確認・後片付けを対象にし、work cap268435456は変えていない。query前にvalidを落とし、query完了後の4key保存と最後のvalid公開を作業上限で保護する。invalidate自身の中断で古いvalidが残っても、global refusalで再生を禁止する。

Amu製ネイティブコンパイラの4世代は929424 B、offset0、SHA-256 `2a0d9a3b47dab57ca8b52532e7ce5c9cff9b189de1e62af564b9436646dd239b`で一致した。自己ビルド8件・診断版生成2件・元のEmbench19本の生成抽出38件が成功した。全19本のKSEED全体・native・ソース・export offsetは比較元と一致する。ベンチマーク本体の実行と性能計測は0件。

| 結果 | V7 | V8 |
| --- | ---: | ---: |
| 完了／work拒否／FN拒否 | 15／2／2 | 17／0／2 |
| 全体semantic／compatible | 43／33 | 85／61 |
| 重点compatible／本数 | 16／3 | 44／5 |
| PicoJPEG semantic／compatible | 0／0 | 30／21 |
| QRduino semantic／compatible | 0／0 | 12／7 |
| 実際の分岐省略 | 0 | 0 |

全19本の凍結参照行を再計算し、公開85候補のtuple・token・fact identityとCACHE／EMITの生成経路を独立照合した。重点32か所／3本の適用可能性はPASSである。別のfiltered60か所／5本の条件は44か所なのでFAILであり、semantic60件と混同しない。候補を使うemitterは未実装のため、実際の32か所／3本の分岐省略条件もFAILである。

PicoJPEGの作業量は232819072、QRduinoは151583872で、どちらもshape段階の上限拒否が解消した。この単位はCPU命令数や時間ではない。小さな他のモジュールではキャッシュ処理の作業量が増える場合もあり、実行性能改善やC超越の証拠に数えない。

有限モデルとソースレビューは、寄与の最小値、自己辺・寄与なし、guarded publication、中断、レイアウトと文脈依存を検査した。全入力の機械証明ではない。この48件の証拠は、新しい512語と50689語全体のnative controlsを含まない。別途実行したscalar21ケース・計25呼び出しは独立監査でPASSとなった。型付きベクトルの正値／未知値寄与のnative再生検査、任意のM・外部arena・ABI/資源同値、候補を使う生成と意味保存、低負荷性能、製品採用はまだ別のゲートである。scalar controlsの実結果をこの48件に足して候補や性能の証拠として数えない。

初回の字句エラー、レビュー資料の同一パス上書きと元hashの完全復元、終了前に封印した監査stdout1件のハッシュ不一致を保存した。最後の不一致はプロセス終了後の追加manifestで訂正し、旧manifestを残した。rootの最終再照合は295ファイルで一致した。ソース・ネイティブ成果物・候補結果の再実行はない。

製品source44bfaa28c/native761856bb…を維持し、全19本でC以上の性能、公式Embenchスコア、製品100% selfhostは未達成である。次は型付きベクトルのnativeキャッシュ検査を完了し、意味保存を確認した候補だけで実際の生成コードを変更して、同じC・同じ19本を静かなホストで測る。

固定済み[三ファイル証拠と再生手順](evidence/coscientist-inverse-aes-20261007/vector-typed-v8/README.md)は、archive4,732,612 B、SHA-256 `c2cd267bee5bb114864ecce785f7e9eb372f928335ff278bcb77eef7b3507b3b`。展開object35,545,740 B、559 logical paths／344 objectsで5 MiB／64 MiB上限内。rootの新規三ファイルコピー再生は全19参照行・85公開tuple・互換61件／重点44件5本・48実行記録を再検査しPASS。破損envelope2種は拒否した。初版readerの外部パス依存と第2版の抽出symbol誤設定を別ファイルで保持し、最終版はopen制約の下で元の比較表からsymbolを取得する。再生はnativeを実行しない。
