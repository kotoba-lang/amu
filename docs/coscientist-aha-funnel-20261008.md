# Aha の funnel shift：隔離した native compiler 候補

C以上の速度を目指す元19本の目標は未達である。[現行Ahaの部分比較](coscientist-vector-param-timing-20261008.md)は候補/Cが1.241954、候補は約24.2%遅い。元の入力・C body・反復回数を変えず、実際の `modul64` にある `or(shl(x,1),ushr(y,63))` を generic な規則として扱う。

新しい既定OFFの[実験helper](evidence/coscientist-aha-funnel-20261008/helpers.kotoba)を隔離した。resident i64 locals、t0、正確な8 SIR、公開済みのchecked-stack前提と bounded deadnessを満たす場合だけ、元の7回の生成操作を再生して正確な3語と状態を照合し、`EXTR + NOP + NOP` に置換する。元のframe・chain/cache・coalesced LSET・fuelを保つ。source41の新規アルゴリズムに既存のAST refactor ruleはないため、一回のhelper追加として隔離した。製品のエントリや既存入力は変更していない。

2語を削除する初案は、後続のCODE容量判定も変わるためHOLDとした。現在の中間候補は3 codewordsのままで、全CODE-N・FIX・label・literal・offset・容量拒否の判定を保持する。3つのcodewordsはCPUのmicro-op発行数の測定ではない。依存するbit演算を減らして速くなるという仮説であり、サイズ削減や速度改善の認定ではない。短縮版は元の生成/layout受理後の縮約・再配置など、別の資源契約を要する後続課題である。

独立した[意味レビュー](evidence/coscientist-aha-funnel-20261008/source-semantic-review.json)と[資源レビュー](evidence/coscientist-aha-funnel-20261008/source-resource-review.json)は有限compiler buildの準備条件としてPASSした。全4 source variantの厳密な逆変換を確認した。オフラインbit比較は有限な検査であり、native全scratch・容量境界・stale descriptorの生存性・一般的な意味保存の証明を代替しない。

ON unity source SHA-256は `bbb55f5a0ca6ba7a0f292e52d4cb8065ac293cfd1ec4b8b6dc9acf61f8359ebf`、OFFは `6daa111687b0676c1c4f13f338ba9759ee3d3854310172060a237c32044339ff`。OFF1世代とON3世代のcompile/extract最大8回を別途事前登録し、ドライバーV3の[独立レビュー](evidence/coscientist-aha-funnel-20261008/driver-v3-review.json)も通った。

最初のOFF compile起動は外側のtask sandbox内で行い、loader自身の `sandbox_init` が `Operation not permitted`、終了コード125で停止した。[attempt](evidence/coscientist-aha-funnel-20261008/startup-attempts.json)と[terminal](evidence/coscientist-aha-funnel-20261008/startup-terminal.json)を保持し、stdoutは空、KSEEDは生成されていない。この終了はビルドPASSや固定点の証拠ではない。V3は閉じたまま保持し、実行環境だけを修正したV4を新規登録した。失敗した起動1回と新規上限8回を合わせると累積上限9回であり、失敗を計数から除外しない。

V4 は8回すべて終了コード0・timeoutなしで完了した。[実行結果](evidence/coscientist-aha-funnel-20261008/build-v4-report.json)と[独立したraw監査](evidence/coscientist-aha-funnel-20261008/build-v4-actual-review.json)は、ON 3世代のnative全バイトとsole `main 0` のKSEED全バイトの一致を確認した。ON nativeは947,352 B、SHA-256 `76e9f9825f1b1e38b2749575cbb4e80a21ad27abb906b97f9f048e7cd631c207`、KSEEDは `0e25e94591000de891ed4edb7ae5c8655c02820197afdd8013e8f61352f59def`。OFF nativeは945,960 B、`3f5eb9723cd5e162f8496d430d239a1ecc1e6441c699a18afd1d53978879dbc3`。V3の失敗1回を合わせた累積実行は9回である。OFF compiler自体が従来compilerと同一という主張ではない。このビルド単独では元19本・native深い状態・容量境界・機能・fuel・速度を検証していない。製品採用もしない。

続く[元19本のコード比較](evidence/coscientist-aha-funnel-20261008/original19-report.json)は、OFF／ON 各19本のcompile・extract、計76回をすべて終了コード0・timeoutなしで完了した。[独立した実行監査](evidence/coscientist-aha-funnel-20261008/original19-actual-review.json)は、OFF 19本が旧4158 compilerのKSEED全バイトと一致し、ONはAhaだけが byte504 の `d37ffa69 d37ffeaa aa0a0136` から `93d5fe76 d503201f d503201f` へ変化したことを確認した。残る18本は全バイト一致する。Ahaは4,032 Bのままで、全export・offset・header・data・poolは保持した。新しい機能runner・native状態試験・速度の検証はまだ完了していない。

このコード比較のドライバーV1は、書換え後の命令途中へ向くADRを見逃す[反例でHOLD](evidence/coscientist-aha-funnel-20261008/original19-source-v1-hold.json)となり、V2は継承環境の全値をrawへ保存する[記録範囲の問題でHOLD](evidence/coscientist-aha-funnel-20261008/original19-source-v2-hold.json)となった。どちらもnative実行0回で保存した。アドレス・literal読取り範囲の検査と、必要な固定KEXE設定・削除したキー名だけの記録へ修正したV3が[独立sourceレビュー](evidence/coscientist-aha-funnel-20261008/original19-source-v3-review.json)を通った後に、別の有限GOで一回実行した。過去の失敗を削除せず、比較条件も緩めていない。

完全な凍結sourceと実行GO・rawは `/Users/junkawasaki/github/workspaces/codex/vector-aha-funnel-source-v1-controls` と `vector-aha-funnel-native-build-plan-v3-root`、`vector-aha-funnel-native-build-plan-v4-root`、`vector-aha-funnel-original19-plan-v3-width`、`vector-aha-funnel-original19-run-v3-root` にある。この保存資料は完全なportable archiveではない。native制御試験とONの元19本機能・fuel・資源比較を確認した後に、新しい静穏host cohortで実行速度を測る。以前のCRC32静穏条件不足のFAILやCohortを上書きせず、元19本・C以上の性能という成功条件も変えない。
