# Shape queryの作業量：Pico・QRの反復を観測

V7の解析が作業上限で止まるPicoJPEGとQRduinoについて、queryの開始・終了、実際に公開されたstage、shape roundの開始を読み取り専用で記録した。元のquery・stage・roundの本体は名前だけを別名にし、追加のG書込、tick、最適化規則、作業上限変更はない。差分を戻すとV7の標準observerの41ファイルとunityに完全一致する。標準の観測記録も維持した。

| 記録された結果 | PicoJPEG | QRduino |
| --- | ---: | ---: |
| queryの開始・終了ペア | 686 | 1,052 |
| shape roundの開始 | 6 | 10 |
| 部分入力キーの2回目以降の出現 | 449 | 760 |
| 完了した反復roundの作業量 | 27,306,880 | 19,233,536 |
| 最後の拒否roundの開始から終了まで | 78,976 | 9,332,096 |
| query途中の拒否ペア | 0 | 1 |
| 最終作業量 | 268,435,456 | 268,435,456 |
| 最終phase／拒否／意味解析候補 | 6／1／0 | 6／1／0 |

Picoは5つ、QRは9つの完了したround間隔で、それぞれ同じ作業量を繰り返した。最後のroundは途中で上限に達したため、完了roundと混ぜない。Picoの拒否はqueryペアの外側で起き、QRには途中拒否のqueryが1件ある。親担当は保存した生ログから全queryのtupleを独立に照合した。stageは要求値ではなく実際の公開値を記録し、観測点のない区間や最終tailは混在区間として扱う。

ただし、同じround作業量でも状態は同じではない。親担当の追加照合では、Picoの4096、QRの2048という正の入口boundが、roundを追って別の関数へ伝播した。一部のqueryが同じ部分キーを繰り返すことと、解析全体の状態が変わらないことは区別する。収束不具合と断定せず、変更された関数だけを再解析するworklistは今後の仮説として、意味・副作用・poisonの保存を別に検証する。

呼び出しはobserverのbuild/extractが2件、PicoとQRのcompile/extractが計4件、合計6 compiler processes。Picoまでの4件の後に、readerが標準FRECの説明用schemaを実幅と誤認して失敗した。FRECを17列、LITを5列へ修正し、記録済みのPicoログをオフラインで再解析した。その失敗と元のparserを保存したまま、未実行だったQRの2件だけを別の継続フォルダーで実行した。ネイティブ処理の再試行はない。

両ソースの全KSEED、ネイティブコード全体、export offsetは、固定した通常生成のbaselineと一致する。ここで比較したのはコンパイル結果と解析の作業量である。数値は128単位の会計指標で、CPU cycleや実行時間ではない。Embench本体の実行とタイミング測定は0件。候補0件はこの2本の上限拒否ログの値であり、V7全19本の候補数を置き換えない。

同じ部分入力キーの反復は、キャッシュの正当性を証明しない。現在のキーはFN・candidate・mode・4つの入口boundだけで、alias／return／effectの情報、detail flag、予算と拒否状態、queryが行う出辺boundの蓄積やpoison処理も結果に関わる。再利用にはそれらの不変性・無効化・副作用の同値を別に検証する必要がある。キャッシュ実装、生成コードの最適化、性能向上、C以上の性能、製品採用はこの検査では認定しない。

[証拠パケット](evidence/coscientist-inverse-aes-20261007/vector-shape-profile/README.md)は1,510,149 B、展開対象の一意な内容は6,952,791 B。7つの関連フォルダーの107パスを87個のSHA-256 objectへまとめ、ソース、ログ、失敗、実引数、成果物、baseline identity、独立検査を保持した。5 MiB圧縮・64 MiB展開の上限内で、全objectのサイズとハッシュを照合した。新しい場所へ3ファイルをコピーしたオフライン検査も通り、6呼び出しと全queryペアを再確認した。readerは保存した証拠だけを読み、nativeやcompilerを実行しない。

親担当も新規三ファイルコピーで再生PASSを確認し、archive内の両ソース・KSEED・native全体・export offsetをbaselineと再計算して一致を確認した。追加native実行は0件。
