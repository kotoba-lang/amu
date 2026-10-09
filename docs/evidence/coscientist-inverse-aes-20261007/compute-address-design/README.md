# Compute-addressed analysis の設計記録

設計のみ。ネイティブCID encoder・persistent importer・logical charge は未実装。preregistration-v1 と semantic review は、資源上限追記前の design-before-resource-clarification.md に帰属する。resource-review-v1-hold を保存し、資源上限を明示した現行文書は resource-review-v2-pass と preregistration-v2 に帰属する。emitter-alignment は固定ソースを変更しない追記である。

publication-receipt はハッシュ・資格範囲の記録であり、IPLD CID または計算結果の意味保存証明ではない。範囲検査省略候補の2回の native build は正常終了したが、機能・命令差分・trap・fuel・自己再ビルド・性能はまだ未検証。モデルやABIの意味を変えずに共有キャッシュを有効化した証拠ではない。
