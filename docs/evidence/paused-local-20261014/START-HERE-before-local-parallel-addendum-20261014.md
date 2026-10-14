# 高速化ゴールの停止・引継ぎ — 2026-10-14

ユーザーの「週間利用枠が少なくなったので、ここで止めて整理してほしい」という指示で停止しました。ゴール管理も **paused** です。目標「19本全体で Kotoba が C 以上」は未達です。次の明示的な再開依頼まで、高速化・測定・修正・マージ・公開を進めないでください。以前の「ゴール欄で再開してください」という質問は、この停止指示で取り消されています。

## 現在地

| 区分 | 内容 | 状態・証拠 |
| --- | --- | --- |
| 採用済み | main `43524a1ce142538c028a4b3bf57edabc6e8a2d85`、[PR #1312](https://github.com/kotoba-lang/amu/pull/1312) | 16段のcopy/write区間で直前の書込み値を再利用。statemateの対応比較で実行時間 **約1.35%短縮**。通常マージとmain読戻し済み。 |
| 採用済み | [PR #1311](https://github.com/kotoba-lang/amu/pull/1311) | Picojpegの色変換を4画素単位のNEON命令で処理。対応比較で **約15.72%短縮**。mainに含まれます。 |
| 未採用・次の候補 | [PR #1313](https://github.com/kotoba-lang/amu/pull/1313)、head `cdcca3523f1208abfb3bdfef0236e157f323e1b7` | copy/writeの先頭区間を16→48段に拡張。statemateの対応比較で **約3.46%短縮**。ローカル検証とレビュー修正済み。PRはOPEN、マージしていません。 |
| 最新の全19本比較 | round114、採用済みPR1312のコンパイラ | Kotobaの実行時間 / Cの実行時間の全体比 **2.688197080154679**。1が同速、大きいほどKotobaが遅く、現在はCのほうが速い結果です。 |

各短縮率は限定された対応比較での観測値で、安定した統計的効果を確定したものではありません。合算して全体の高速化率にはできません。**5%未満を一律に却下する基準はありません。** 小さい改善も、意味のある効果と安全性を確認できれば採用する方針です。

round114はKotoba 19本＋新しく実測した元のC 19本がすべて合格し、CPU条件による再試行もありません。上流Embenchの変更していない集計ドライバ・計算式を使用していますが、Kotoba移植版の探索的測定です。**認証済みの公式KotobaスコアやMHz当たりのスコアではありません。** native幾何スコア12745.412129167858、C幾何スコア34262.179670997066。round114は未採用の48段版の全体性能を示しません。

## 停止時点のPR・実行状況

2026-10-14 12:04 JSTの読取り時点で、PR1313は20チェック中16成功、4実行中、失敗0。レビュー3件は解決済み、自動マージは無効です。GitHubのCIは既存の実行を残しました。ローカルの監視session17139は終了済み（停止に伴うexit143）で、後続のマージ処理はありません。再開時にはGitHubを読み直してください。

ベンチマーク・コンパイル・検証の既存ハンドルはすべて終了済みです。古い子エージェント3体も停止状態で、再起動していません。停止後に新たな最適化・測定は開始していません。

## 引継ぎ資料と保存先

- [詳細な技術引継ぎ](GOAL-HANDOFF.md)：正確なピン、検証内容、測定上の制約、再開順序。
- [停止時の記録](pause-receipt.json)：main/PR/CI/停止状態。GitHubスナップショットは同じディレクトリの `pause-*.json`。
- [採用・候補の索引](candidate-index.json)：今回の再開期間に記録した全候補と保存先。古いstatus文字列より、採用フラグ・main読戻し・最新停止記録を優先してください。
- [採用済み変更の一覧](ADOPTED-HISTORY.md)：週次枠の再開以降の統合履歴。さらに以前の履歴は[前回の引継ぎ](../embench-paused-handoff-publication-20261013/HANDOFF.md)。
- [全19本の最新結果](../embench-total-C-round114-copy-chain-forward-20261014-v1/final-summary.json)と[独立検証](../embench-total-C-round114-copy-chain-forward-20261014-v1/collection-plan/verified/review.json)。
- [mainへの統合確認](../seed-copy-chain-forward-20261014/main-integration-receipt.json)。
- PR1313のworktree：`/Users/junkawasaki/github/wt/codex/seed-copy-chain48-20261014`。ソースと証拠はpush済み。証拠は `docs/evidence/copy-chain48-20261014/` に元のqualification・レビュー修正・標準検証のアーカイブを別々に保存しています。
- [保存ファイルのSHA-256一覧](preserved-artifacts.json)、[保存ブランチのリモート参照](pause-saved-remote-refs.txt)、[worktree一覧](pause-worktrees.txt)。無関係なWIP・stash・untrackedは保持。PR1313には既存untracked `scripts/seed/__pycache__/` が残っています。
- [長期チェックポイント](../embench-total-C-round52-20261011/continuation-checkpoint.json)：`userRequestedPause20261014` と `weeklyAllowanceResume20261013.currentAdoptedMain` が現在状態。古いラウンドの結果は履歴として残しています。

## 保存した未採用候補・診断

| 候補 | 保存先（このworkspaceの隣） | 判断 |
| --- | --- | --- |
| copy/write 48段・レビュー修正版 | `seed-copy-chain48-review-20261014`、元の実測は `seed-copy-chain48-20261014` | 有望、PR1313未採用。修正後も全39画像と汎用54画像が実測版と完全一致。再測定で数字を探し直さないこと。 |
| copy/write 32段 | `seed-copy-chain32-20261014` | 正しさは合格。OFF側のCPU条件が3回とも不合格のため比較値なし。4回目・同一候補の測り直しをしないこと。 |
| bounded DAG round | `seed-dag-bounded-round-20261014` | Picoの2組とも遅く、未採用。ソース・結果を保持。 |
| SLREの割当て箇所調査 | `slre-pc-profile-20261014`、`loader-pair-store-20261014` | 診断サンプルの約83.71%がhost側 `checked_pair_new`。実行系のストア変更は改善未確認・未採用。Cマイクロ測定はEmbenchスコアではありません。 |

そのほかの負例・画像不変候補・割込み候補は `candidate-index.json` と長期チェックポイントに保存済みです。Josephの16GB RAM・swap約17.5GBという診断記録はありますが、性能差の原因と確定していません。無関係なプロセスを止めたり環境を掃除したりしないでください。

## 明示的に再開された後の順序

1. 最新のユーザー指示・goal状態・利用枠を確認。追加の有料クレジット消費は未許可。前回残高38077.1419195000と週次54%使用は過去のスナップショットです。
2. PR1313のhead/main/CI/レビューを読み直す。mainの差分があれば、保存した実測と証拠がなお適用できるかを確認。通常のチェックとレビューを満たしてから通常マージすること。保護の迂回やforce-pushをしないこと。
3. 実際に統合した場合のみ `pr1313-final-checks.json` と `pr1313-merged.json` を保存し、このディレクトリの `readback-main.py` でmainのソース・unity・native・container・golden・祖先を読戻す。スクリプトは準備済みで、まだ実行していません。
4. 統合を確認できてから48段版の全19本＋新規C計測を準備。元の19本・39画像・483観測を維持。過去の時間やsubset幾何平均を流用しないこと。
5. 現在の大きな差はpicojpeg約4.51、statemate約4.35、slre約4.11、sglib-combined約3.73、wikisort約3.44。SLREのhost割当て診断は次の調査材料です。

計測条件はCPU idleの事前・生の事後・背景値が70%以上、測定本体0.5秒以上、warm1/sample1、事前固定した4スロット、CPU条件だけ最大3回・最初の合格を採用。同じ画像を何度も測って都合のよい値を選ばないこと。コンパイラはnative Amuのみ。Josephへ許可された転送物は専用ディレクトリ内の測定用C/Pythonとguestバイナリだけで、Kotobaソースやコンパイラ本体は範囲外です。

今回の停止整理ではkotoba-lang.orgを更新していません。既存の公開情報と、ここにある最新のローカル・GitHub証拠を区別してください。
