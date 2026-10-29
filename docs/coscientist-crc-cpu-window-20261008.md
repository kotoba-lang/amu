# CRC32 の CPU 計測区間を分ける有限診断

起動から終了までの外側の CPU 診断と、warmup 後の timed loop を囲む内側の診断を分けた。これは計測方式の有限な確認であり、全19本の性能結果、公式 Embench スコア、C以上の速度、CID の性能効果を認定しない。[以前の CRC32 静穏条件不足による停止](coscientist-vector-param-timing-20261008.md)は保持し、再開・統計の混合はしていない。

独立ソースレビュー後、zebulun の新しい専用ディレクトリで CRC32 runner を1本だけビルドした。現在の Apple Clang17・SDK26.2・OS26.2 の同一性を前後14 queryで照合した。clang 呼出しは、version/target の前後確認4回とビルド1回の計5回である。既存19 runner、元入力、header、C dylib は変更していない。

baseline・candidate・Cについて旧／新 collector を各3回、合計18回実行した。`n=32`、warmup 1回、fuel `16777216`、固定 calls は順に2703・2736・4428。全18回が終了し、既存171件の機能 oracle に対して結果・fuel・4種 terminal arena が一致した。C の arena は測定不能の `null` のままである。新しい CPU 診断フィールドだけを意味比較から除外し、結果や fuel の差を許容していない。

新 collector の C 3回で、外側の推定 background idle は90.623%、89.394%、89.326%、内側は93.858%、90.859%、92.421%だった。同じ process の異なる区間の推定値である。90%によるサンプル選別はこの実験では行っていない。この3回で静穏 host、一般的な起動負荷の因果、測定器の無負荷性、性能差の有意性を認定しない。内側にも endpoint sampling の費用があり、外側には起動・warmup・raw記録など timed loop 外の作業が入る。

独立 [actual raw audit](evidence/coscientist-crc-cpu-window-20261008/report.json) は、1 build・14 query・18 call の argv・環境・raw hash・現在の成果物と oracle・厳密な CPU decoder の再計算を確認した。report SHA-256 は `9733c2828315cd61f84e06e88453931969bda10fb69ec4dd474db42a61d8d8e1`。監査は SSH・native・compiler を再実行していない。

全rawと有限GOは `/Users/junkawasaki/github/workspaces/codex/vector-param-timed-cpu-diagnostic-go-v1-root` に保持する。ここに保存した監査報告とinput pinsは完全なportable archiveではない。今後この計測方式で全19本を比べる場合は、方式・静穏条件・反復数を先に固定した別のcohortとして扱う。以前の失敗や Aha の部分結果を上書きしない。
