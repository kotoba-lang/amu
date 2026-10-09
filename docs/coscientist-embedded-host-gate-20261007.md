# 埋め込み実行契約の試作（2026-10-07）

CPU最適化と燃料カウンタの重複処理削減に必要な、埋め込み専用の実行契約を試作した。要求とコードを同じ固定header/binaryへ束ね、実際のOS検出でCRC32/AESを確認する。不明な要求、検出失敗、未対応、ISA不一致は、実行用メモリ化・fork・entryより前に拒否する。既定は要求なし。raw loaderへ非空要求を付けるとビルドを拒否する。

19ビルド・25実行の保存されたrawと186 pinを独立レビューし、ゲートを削除・移動・反転した3つのソース制御も検出した。rootは別の3ファイルコピーから再検証した。未対応・検出エラーの一部は明示したテスト用shimであり、未対応実機を測定したという主張ではない。

`fuel-exclusive-writer-v1` は、この固定ローダーが初期化したcontextを監督下の子プロセスが書くという限定契約である。任意のguest store、callback、汎用ABIにおける書き込み禁止を保証しない。次の最適化には、閉じた呼び出し・副作用なし・scratch所有・各燃料公開・不足fallbackの別の検証が必要。DefCIDと生成recipe/host requirementsは分ける。

**製品統合・producerの要求生成と検証・provenance統合は未実装。燃料処理を変更した試作でも、C以上の達成証拠でもない。** [証拠と再検証](evidence/coscientist-embedded-host-gate-20261007/README.md)を保存した。
