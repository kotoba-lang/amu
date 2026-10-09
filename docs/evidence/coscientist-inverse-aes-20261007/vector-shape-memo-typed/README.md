# 型付き vector の固定3ケース

`python3 replay.py` を、typed-vector-proof.tgz・typed-vector-proof.manifest.json・replay.py の3ファイルを置いた書き込み可能なフォルダーで実行する。標準ライブラリだけで安全な一時領域へデータを復元し、元の workspace を読まず、封入コードや native を実行せず再検査する。

アーカイブ 2021484 B、SHA-256 `8ce398d4017366ca08f02499b026ae56b9f014742e1187b29c3b876ecc592d51`。92 paths、重複を除いた展開 7927531 B。4 MiB／32 MiB上限内。全7回の argv・cap・終了記録、全KSEED/export、V8へのソースの完全な逆変換、長さ4・未知長0・自己呼び出しneutral・初期化した集計への再生一致を再検査する。

途中版の監査報告を固定していた梱包初版は hash assertion で停止した。途中版の報告、初版の定義、停止ログを保存し、終了後の2つのpinだけを更新した。途中版スクリプトは復元できず、そのhashを記録している。検証条件とreaderは変更していない。root は新しい3ファイルのコピーで再生し、archiveとmanifestの改変もそれぞれ拒否された。

通常版624 B／bench424は採取だけ。自己再ビルド4世代は兄弟の vector-typed-v8 packet に帰属する。固定fixtureの有限な検証であり、性能・任意の入力の証明・製品採用の証拠ではない。
