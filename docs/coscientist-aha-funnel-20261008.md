# Aha の funnel shift：隔離した native compiler 候補

C以上の速度を目指す元19本の目標は未達である。[現行Ahaの部分比較](coscientist-vector-param-timing-20261008.md)は候補/Cが1.241954、候補は約24.2%遅い。元の入力・C body・反復回数を変えず、実際の `modul64` にある `or(shl(x,1),ushr(y,63))` を generic な規則として扱う。

新しい既定OFFの[実験helper](evidence/coscientist-aha-funnel-20261008/helpers.kotoba)を隔離した。resident i64 locals、t0、正確な8 SIR、公開済みのchecked-stack前提と bounded deadnessを満たす場合だけ、元の7回の生成操作を再生して正確な3語と状態を照合し、`EXTR + NOP + NOP` に置換する。元のframe・chain/cache・coalesced LSET・fuelを保つ。source41の新規アルゴリズムに既存のAST refactor ruleはないため、一回のhelper追加として隔離した。製品のエントリや既存入力は変更していない。

2語を削除する初案は、後続のCODE容量判定も変わるためHOLDとした。現在の中間候補は3 codewordsのままで、全CODE-N・FIX・label・literal・offset・容量拒否の判定を保持する。3つのcodewordsはCPUのmicro-op発行数の測定ではない。依存するbit演算を減らして速くなるという仮説であり、サイズ削減や速度改善の認定ではない。短縮版は元の生成/layout受理後の縮約・再配置など、別の資源契約を要する後続課題である。

独立した[意味レビュー](evidence/coscientist-aha-funnel-20261008/source-semantic-review.json)と[資源レビュー](evidence/coscientist-aha-funnel-20261008/source-resource-review.json)は有限compiler buildの準備条件としてPASSした。全4 source variantの厳密な逆変換を確認した。オフラインbit比較は有限な検査であり、native全scratch・容量境界・stale descriptorの生存性・一般的な意味保存の証明を代替しない。

ON unity source SHA-256は `bbb55f5a0ca6ba7a0f292e52d4cb8065ac293cfd1ec4b8b6dc9acf61f8359ebf`、OFFは `6daa111687b0676c1c4f13f338ba9759ee3d3854310172060a237c32044339ff`。native成果物はまだ得られていない。OFF1世代とON3世代のcompile/extract最大8回を別途事前登録し、ドライバーV3の[独立レビュー](evidence/coscientist-aha-funnel-20261008/driver-v3-review.json)も通った。

最初のOFF compile起動は外側のtask sandbox内で行い、loader自身の `sandbox_init` が `Operation not permitted`、終了コード125で停止した。[attempt](evidence/coscientist-aha-funnel-20261008/startup-attempts.json)と[terminal](evidence/coscientist-aha-funnel-20261008/startup-terminal.json)を保持し、stdoutは空、KSEEDは生成されていない。この終了はビルドPASSや固定点の証拠ではない。V3は閉じたまま保持し、実行環境だけを修正したV4を新規登録した。失敗した起動1回と新規上限8回を合わせると累積上限9回であり、失敗を計数から除外しない。

完全な凍結sourceと実行GO・rawは `/Users/junkawasaki/github/workspaces/codex/vector-aha-funnel-source-v1-controls` と `vector-aha-funnel-native-build-plan-v3-root`、`vector-aha-funnel-native-build-plan-v4-root` にある。この保存資料は完全なportable archiveではない。native制御試験、既定OFFの元19本バイト一致、ONの元19本機能・fuel・資源比較、3世代固定点を確認した後に、新しい静穏host cohortで実行速度を測る。以前のCRC32静穏条件不足のFAILやCohortを上書きせず、元19本・C以上の性能という成功条件も変えない。
