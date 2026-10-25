# 2026-10-12 停止・再開チェックポイント

最適化ゴールは **paused**。C以上の性能は未達。新しいユーザー指示があるまでビルド、ベンチマーク、SSH、最適化agent、定期実行を起動しない。

## 保存した成果

採用ソースは `f86c2a6f06e55d77b22a574ac91df59590212cdc`。既存PR #1222のブランチ `codex/seed17-continuation` の `833487fcd03a14708f09823b4cfca974089f9227` を祖先とする69コミットを、`codex/amu-selfhost-paused-20261012` に履歴ごと保存する。既存ブランチを上書きせず、mainへのマージも本チェックポイントの範囲には含めない。全コミット一覧は [adopted-commits.txt](adopted-commits.txt)。

最新採用は、pure・unchargedな型付きi64→i64のしきい値木を、不変byteテーブルに置換する汎用lowering。token容量の変更によりコンパイラ内モデル割当ては4 MiB増加する。guest ABI/fuel/loader上限は不変。過去のsafe pow2、fresh fixed-vector、physical-home scan、wide product、bit reservoir、charged reader、literal transfer、interval predicate、masked writerも同じ履歴に含む。

- 16モジュールのnative seedがG2/G3/G4でイメージ・KSEEDコンテナともにバイト一致。
- 元19本がcompile/extractを通過。変更2本、残り17本は成果物完全一致。
- 機能95条件は新規10件＋完全一致に基づく再利用85件。結果・fuel・arenaを照合。
- PicoJPEG: 121.92→119.97 µs/body、探索的短縮1.60%。Cは19.73 µs、約6.08倍遅い。
- QRduino: 180.50→172.87 µs/body、探索的短縮4.23%。Cは38.45 µs、約4.50倍遅い。
- 各1組のC/OFF/ON、n32/calls64/warm1、BATCH_ABI_RESET_VALIDATION_V1。公式Embenchスコアではなく、統計的に確認した高速化でもない。異なる基準の過去改善率を加算しない。

固定点の保証はseed/KSEED経路。製品check/compile/refactor全体、Node launcherの置換、通常の型付きKIR/provenance KEXE保証の同等性、全19本の新規性能測定は未完了。ComputeCID/ResultCIDのnative解析再利用、一般GP2/Sea-of-Nodes、アクセラレータ・低精度演算の効果もこの成果では証明しない。

## 証拠と保管検証

[checkpoint.json](checkpoint.json) が再開用の状態、[inventory.json](inventory.json) が634ファイルのサイズ・SHA-256。`evidence.tgz` は約5.2 MB、展開時約23.9 MB。主な内容は次のとおり。

- 採用receipt、16ソースとunity、source/machine/fixed-point/最終レビュー。
- G2/G3/G4本体・コンテナ、producer receipt、停止済み実行のrawログとjournals。
- 元19本の生成capsuleと成果物、2本のC比較capsule、selected95とsaved85。
- token-fit説明の撤回、失敗receipt、bootstrap前後照合。
- 現在基準のcustody V5、未採用ordinary-call候補のproposalとreview（実行しない）。

元receiptはバイトを保つため当時の絶対パスとPIDを含む。アーカイブ内の名前は `workspace/<元作業ディレクトリ>/...` と `source/seed/...`。古いパスやPIDは現在の資産・稼働プロセスを指す保証ではない。これは重要証拠とcapsuleの保存であり、すべての外部依存を含むhermetic実行環境ではない。

保管状態だけを確認するコマンド（native実行なし）：

```sh
python3 docs/evidence/native-selfhost-paused-20261012/verify.py
```

SHA-256は内容の同一性の検査で、最適化の意味保存を新たに証明するものではない。この保存時点では実験を再実行せず、既存の資格判定を保持する。

## 再開時の順序（今は実行しない）

1. ユーザーから明示的な再開指示を受ける。保存ブランチから専用worktreeを作り、上の保管検証を実行する。新worktreeは `/Users/junkawasaki/github/wt/<agent>/<task>`、scratchは `github/workspaces/<agent>/<task>`。
2. `f86c2a6f0` の16ソースとG4のハッシュを起点にする。checkpointの後の文書保存コミットは最適化ソースを変えない。古いguardのHEAD条件を回避せず、現在のHEAD・パス・producer・ABI・limitsを明示した新custodyを作る。
3. archiveは専用scratchへ安全に展開し、原本を上書きしない。capsuleのREADME/preregistrationと所有権・監督・プロセス帰属契約を読み、パス・依存・loaderを再束縛する。古いrun.py/guard.pyをそのまま起動しない。終了receiptから現在のプロセス生存を推定しない。
4. 最新基準で元19本とC比較を維持する。速い探索サイクルでもresult・fuel・arena・trap・ABI・bootstrap境界の確認を省かない。小さな正の改善を一律の閾値で捨てず、探索値と確定値を分ける。
5. 未採用候補はordinary-callの既存byteテーブル転送を先に検討。より大きなgn-op-call bypassは引数・一時値・home/contextの保存証拠が必要。finite-4 constructorは実行capsule未完成。これらは採用済み成果と混ぜない。
6. 並行化するならソース設計・独立監査・検証harnessを別ownerへ分け、native測定の監督を一つにする。再開のたびに現行AGENTS.mdと契約を再確認する。

公開状況報告: https://kotoba-lang.org/ja/blog/native-selfhost-status-20261012/ 。サイトの2026-10-12記事は公開時点の「ローカル採用」を記録している。この保存ブランチのpushはソースと証拠の公開で、main統合・製品リリース・性能目標達成を意味しない。

## 安全修正を保持した再統合 — 2026-10-12

この文書の上部と`checkpoint.json`は元の停止時点の記録。現在の再統合版は
`seed/preserved-20261012/`へ独立した16ソースとして配置し、現行mainの最適化系列を
上書きしない。保存版driverをmainのpolicy拒否へ置換し、現行版・保存版の双方で
単一ファイル／projectの`check --policy`にも同じ拒否を適用した。

新しいsource/producer pinは`seed/preserved-20261012/adoption.json`、現行版は
`seed/adoption-20261012.json`。どちらも3世代固定点、34拒否ケース、policyなしの結果42、
元19本の完全nativeイメージ同一性を確認した。seedの拒否は終了コード1とE2170で、
出力ファイルを作らない。公開loaderとfuzz基準はmainの一致する組を保持し、
coverage floorを下げない。ローカルmacOS ASan/UBSan 20,000ケースは通過、Linuxの
source-bound coverageは追加CIで検証する。

`reintegration.json`が新検証のまとめ、`reintegration-raw.tgz`が生ログ・3世代成果物。
外側sandbox拒否、harnessのexport名・command-mode誤認、修正前checkの見逃しを含む
失敗ログも保存した。失敗を成功に書き換えていない。現在の再開先は上の新pinを優先し、
元archiveの実行capsuleを無変更で起動しない。

最適化ゴールはpausedのまま。これらの自己再ビルド・fuzz・policy検証は保守の正当性検証で、
性能探索・新しい性能測定・製品CLI切替・100% selfhostの主張ではない。

公開loaderと凍結trusted bootstrap loaderを別々のSHAに結び付け、同じ既存coverage floorを下げずにLinux x64/arm64で検査する。値なし`--policy`の4経路も拒否ケースに含む。

Trusted bootstrap loaderはABI v11に対応する凍結fuzz targetを使い、公開loaderは現行ABI v12 targetを使う。両方のsource pin、全reach counter、既存Linux coverage floorを検査する。初回のv12 targetによる未到達はharnessの不整合で、失敗ログを残して適合targetで再検証した。

mainの19本の比較基準は、修正前main `03c72db2a` のbootstrap `c3b7b6ff...`で最初に生成した独立成果物を`main-pre-policy-native19.tgz`と`seed/main-pre-policy-native19.json`へ凍結した。候補compilerから基準を生成し直さない。結果42はstdout全体と空stderrを厳密照合し、証跡の新旧archiveサイズ・SHAも保管検証する。
