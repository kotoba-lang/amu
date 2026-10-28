# Private parameter bounds: native checkpoint

状態：既定で無効な実験。製品 `44bfaa28c` / native `761856bb…` は変更していない。C以上の性能、公式Embenchスコア、製品全体の100% selfhostは未達である。

## 仮説と契約

private 関数の全呼び出し元の確定した vector 長を使えば、定数indexの境界チェックを省略できる。解析値だけでなく辺ごとの寄与・現在の入力キー・公開境界を確認して証明を封じる。[ComputeCID / ResultCID 設計](coscientist-compute-addressed-analysis-20261007.md)の状態更新契約を、activation 内のコード生成へ接続した実験である。永続キャッシュ、native IPLD CID、共有importは実装していない。

未知の入口、公開関数、逃げた関数参照、不完全な解析、poison、短い呼び出し元、非定数indexを省略の根拠にしない。self-neutralには非自己呼び出しの確定した根拠を必要とする。returned-originの緩和は加えない。2056-word seal、256 record、128 function等の既存上限は維持する。実験用source SHA-256は `ea8281843170b65999ff5a6460a2ba2b3474f04e8e5fda8abc616bf283a0acf5`、nativeは `4158d7de2dfe4d922450b60788bb5f6a950ca129f92f0b841069aa4c0f76b509`。

## 実測した証拠

private parameterの1 fixture・3入力の正例は[先の検証資料](evidence/coscientist-inverse-aes-20261007/vector-param-positive/README.md)に保存した。276→264バイト、結果・fuel・arena一致である。

今回の3世代再ビルドは6回で終了した。各世代は943,320バイトで、native全体が初期compilerと完全一致した。KSEED全体も `1c43f47612e0150c52519b5da811ac0654276609dbb914eb4c2c8879e9187dd6` に一致し、唯一のexportは `main / offset0 / arity0`。独立raw audit `252d9e19b4030d857c6fd8ff9ef8f6428fe3cc47bd6958f01c137a551d8bd2ef` は、最後に保存された全3世代・6 argv・ログ・環境・producer連鎖を再実行なしで確認した。監査側の最初の入力ファイル名誤記と、その修正記録も保存した。

元の19入力はソースを変更せず38回でcompile/extractした。独立raw audit `966c7d206bafae4c83ce7d0060fc874681c8253f82944e7873bf6e1ed47be88a` が、末端の全input pin、生成KSEED/native/offset/exportと差分を確認した。

| 結果 | 範囲 |
| --- | --- |
| 全体バイト一致 | 12入力 |
| 登録したチェック省略を確認 | nettle-sha256 11か所、tarfind 1か所、ud 1か所 |
| HOLD: データ尾部の移動を未検証 | edn、huffbench、qrduino |
| HOLD: 登録したread列では差を説明できない | picojpeg |

認定した13か所はCMP/B.LO/UDFの各12バイト削除、登録済み分岐・export位置補正のみ。handle検査・descriptor・pool・address・loadを保つ。HOLDの差を省略件数へ加算しない。データ尾部を命令として解釈しない。19本のcompile成功は19本の機能・速度の合格ではなく、HOLD成果物は現時点の性能測定候補へ認定していない。

## 拒否試験の失敗を保持する

10 fixture / 3 arm / 最大150回のv1手順は、予期しないcompile失敗を3 arm後に判定する欠陥がsource reviewで見つかった。v1をHOLDとして保存し、実行していない。事前登録したv2で即時停止へ修正し、独立source review後に実行した。

v2は46回目でFAIL停止した。最初の3ケースは45回で完了した。長さ4/2の呼び出し元のminimumを使う正例は536→524バイトで、3入力の結果 `0,28,-4` が全3 armで一致した。長さ0の呼び出し元と公開されたcalleeの2拒否例はKSEED/native全体が一致し、各3入力で結果またはSIGILL・fuel・arenaが全3 armで一致した。

46回目のaddress-taken-direct基準compileはrc1、stdout空、stderr `seed: E2102 unknown symbol 'read-param' (byte 135)`。事前の拒否出力契約と一致しないため停止した。以降6ケースは未実行であり、v2全体をPASSへ読み替えない。独立raw audit `2f008738e0dadffe716d74ffb6634d0d23ef62a0d452e6ecdfbe67f929c78e6f` は、46ログと実際の停止順を確認した。

試験がbare function nameを値として束縛していた点を調べ、sourceの対応構文 `(fn-ref f)` を確認した。新しい構文のfixtureは別の事前登録で扱い、元のFAIL・fixture・期待値は保持する。構文拒否を、optimizerのescaped-entry拒否の実行証拠にはしない。

## 封印と次の検証

[checkpoint capture](evidence/coscientist-inverse-aes-20261007/vector-param-checkpoint/README.md)は588 member / 展開43,117,348バイト。archive SHA-256は `02b38c0a006ac1724a6e5d5403058ec8c83a9223b63e8931fa3275c303b25569`。全memberを抽出・実行なしで照合した。これは元の絶対パスを含む証拠保管であり、portableな再実行手順ではない。

残る差分4件と未実行の拒否例を検証した後、同じ測定先でbaseline/candidate/Cを比較する。測定先zebulunの実際のcompilerはApple Clang17・SDK26.2、ローカルはClang21・SDK26.5なので、ローカルC成果物で置き換えない。元のC source/flagsを固定した新しいremote build receiptを作り、過去のrecipe不明なC binaryや歴史統計と混ぜない。低負荷・CPU idle・反復比較を満たすまで性能の結論を出さない。
