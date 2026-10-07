# ComputeCID解析再利用のC1b native前提試験

[計算要求・結果・全辺更新の設計](coscientist-compute-addressed-analysis-20261007.md)から、読み取りと更新の干渉を調べる有限native診断を別登録した。キャッシュでqueryを省略せず、常に直接計算し、独立したfull Mコピー2個、読み取り・書込みtrace、fresh集計への順序付きreplayを照合する。full Mは物理診断のsnapshotであり、canonicalなComputeCID payloadではない。型付きordinalは同一snapshot内のみで、DefCIDの名前変更・共有importへ一般化しない。

sourceは61定義の保守的参照閉包、11 reader・1 writerの計測、GN・2056語の既存seal bank・917,512語の診断領域の分離を検査した。固定計上208,666,688とmetered hash-probe/input-scanを分け、診断scalar accountingの上限536,870,912を登録した。これは全VM命令・ホストの全作業量の証明ではない。別のsource/resource reviewとroot GOにより、最大7呼出だけを新規登録した。

[独立実監査](evidence/coscientist-compute-analysis-20261008/c1b-native-v1-failure/independent-report.json)のとおり、診断compilerとfixtureのcompile／extract計4回は成功し、最初のcase0が終了コード93で停止した。全5回は閉じ、stderrは空、成功caseは0、残り2 caseは未実行。PIPELINEのerror0とallocationを通り、trace5,225 event・traceerror0・trace counter209,335,488を記録した。first-read、直接計算同一性、fresh replay、入力改変拒否、trace容量拒否と元解析保持、cleanupは内部flag1だったが、全入力cell検証のflagだけ0である。全部を通す必要があるため、C1bは成功と呼ばない。

失敗理由は現在のrawでは特定できない。input-scan累積予算、probe-budget sentinel、未書込みcellのA/B差分のいずれもfalse経路を持つ。最小scanと開始量は約508.35Mで536.87M未満だが、衝突probeの追加費用で残る約28.52Mを消費する可能性がある。可能性を原因として断定しない。次は最初の失敗理由・index・累積量・probe／key／written／A-B値を別の有限診断で記録し、元のpredicateと予算上限を維持する。旧失敗の再実行や予算拡張による成功化はしない。

[失敗の全内容packet](evidence/coscientist-compute-analysis-20261008/c1b-native-v1-failure/content.tgz)は1,425,224 B、SHA-256 `6dd55f961d62300e373b347d7a0aa6b8c0b9b5918389e11a41fac6114c47c3b3`、43 regular members・50元パス・展開5,541,897 B。凍結source・reviews・GO・producer／loader・raw・生成native・失敗監査を保持する。元の設計文書は入力pinを保持するため変更していない。

full shape C1・native解析用canonical CID・共有cache C2・解析省略・性能改善・C以上のEmbench達成は未認定。IPLD/CIDの内容一致と、入力キー完全性・更新再適用の意味保存の検証を混同しない。製品既定OFFを維持する。

[失敗packetの独立内容監査](evidence/coscientist-compute-analysis-20261008/c1b-native-v1-failure/independent-packet-report.json)は全43 member・50元パスと実監査依存の一致を、展開・再実行なしで確認した。
