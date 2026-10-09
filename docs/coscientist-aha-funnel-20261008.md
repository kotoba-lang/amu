# Aha の funnel shift：隔離した native compiler 候補

C以上の速度を目指す元19本の目標は未達である。[現行Ahaの部分比較](coscientist-vector-param-timing-20261008.md)は候補/Cが1.241954、候補は約24.2%遅い。元の入力・C body・反復回数を変えず、実際の `modul64` にある `or(shl(x,1),ushr(y,63))` を generic な規則として扱う。

新しい既定OFFの[実験helper](evidence/coscientist-aha-funnel-20261008/helpers.kotoba)を隔離した。resident i64 locals、t0、正確な8 SIR、公開済みのchecked-stack前提と bounded deadnessを満たす場合だけ、元の7回の生成操作を再生して正確な3語と状態を照合し、`EXTR + NOP + NOP` に置換する。元のframe・chain/cache・coalesced LSET・fuelを保つ。source41の新規アルゴリズムに既存のAST refactor ruleはないため、一回のhelper追加として隔離した。製品のエントリや既存入力は変更していない。

2語を削除する初案は、後続のCODE容量判定も変わるためHOLDとした。現在の中間候補は3 codewordsのままで、全CODE-N・FIX・label・literal・offset・容量拒否の判定を保持する。3つのcodewordsはCPUのmicro-op発行数の測定ではない。依存するbit演算を減らして速くなるという仮説であり、サイズ削減や速度改善の認定ではない。短縮版は元の生成/layout受理後の縮約・再配置など、別の資源契約を要する後続課題である。

独立した[意味レビュー](evidence/coscientist-aha-funnel-20261008/source-semantic-review.json)と[資源レビュー](evidence/coscientist-aha-funnel-20261008/source-resource-review.json)は有限compiler buildの準備条件としてPASSした。全4 source variantの厳密な逆変換を確認した。オフラインbit比較は有限な検査であり、native全scratch・容量境界・stale descriptorの生存性・一般的な意味保存の証明を代替しない。

ON unity source SHA-256は `bbb55f5a0ca6ba7a0f292e52d4cb8065ac293cfd1ec4b8b6dc9acf61f8359ebf`、OFFは `6daa111687b0676c1c4f13f338ba9759ee3d3854310172060a237c32044339ff`。OFF1世代とON3世代のcompile/extract最大8回を別途事前登録し、ドライバーV3の[独立レビュー](evidence/coscientist-aha-funnel-20261008/driver-v3-review.json)も通った。

最初のOFF compile起動は外側のtask sandbox内で行い、loader自身の `sandbox_init` が `Operation not permitted`、終了コード125で停止した。[attempt](evidence/coscientist-aha-funnel-20261008/startup-attempts.json)と[terminal](evidence/coscientist-aha-funnel-20261008/startup-terminal.json)を保持し、stdoutは空、KSEEDは生成されていない。この終了はビルドPASSや固定点の証拠ではない。V3は閉じたまま保持し、実行環境だけを修正したV4を新規登録した。失敗した起動1回と新規上限8回を合わせると累積上限9回であり、失敗を計数から除外しない。

V4 は8回すべて終了コード0・timeoutなしで完了した。[実行結果](evidence/coscientist-aha-funnel-20261008/build-v4-report.json)と[独立したraw監査](evidence/coscientist-aha-funnel-20261008/build-v4-actual-review.json)は、ON 3世代のnative全バイトとsole `main 0` のKSEED全バイトの一致を確認した。ON nativeは947,352 B、SHA-256 `76e9f9825f1b1e38b2749575cbb4e80a21ad27abb906b97f9f048e7cd631c207`、KSEEDは `0e25e94591000de891ed4edb7ae5c8655c02820197afdd8013e8f61352f59def`。OFF nativeは945,960 B、`3f5eb9723cd5e162f8496d430d239a1ecc1e6441c699a18afd1d53978879dbc3`。V3の失敗1回を合わせた累積実行は9回である。OFF compiler自体が従来compilerと同一という主張ではない。このビルド単独では元19本・native深い状態・容量境界・機能・fuel・速度を検証していない。製品採用もしない。

続く[元19本のコード比較](evidence/coscientist-aha-funnel-20261008/original19-report.json)は、OFF／ON 各19本のcompile・extract、計76回をすべて終了コード0・timeoutなしで完了した。[独立した実行監査](evidence/coscientist-aha-funnel-20261008/original19-actual-review.json)は、OFF 19本が旧4158 compilerのKSEED全バイトと一致し、ONはAhaだけが byte504 の `d37ffa69 d37ffeaa aa0a0136` から `93d5fe76 d503201f d503201f` へ変化したことを確認した。残る18本は全バイト一致する。Ahaは4,032 Bのままで、全export・offset・header・data・poolは保持した。新しい機能runner・元19本の機能/fuel比較・速度の検証はまだ完了していない。

このコード比較のドライバーV1は、書換え後の命令途中へ向くADRを見逃す[反例でHOLD](evidence/coscientist-aha-funnel-20261008/original19-source-v1-hold.json)となり、V2は継承環境の全値をrawへ保存する[記録範囲の問題でHOLD](evidence/coscientist-aha-funnel-20261008/original19-source-v2-hold.json)となった。どちらもnative実行0回で保存した。アドレス・literal読取り範囲の検査と、必要な固定KEXE設定・削除したキー名だけの記録へ修正したV3が[独立sourceレビュー](evidence/coscientist-aha-funnel-20261008/original19-source-v3-review.json)を通った後に、別の有限GOで一回実行した。過去の失敗を削除せず、比較条件も緩めていない。

native状態試験V1は、harness compile・extractの2回を成功した後、最初のprobeが終了コード91で `PIPELINE 2101 1 14`、`END 0 2101` を返して停止した。[失敗の独立監査](evidence/coscientist-aha-funnel-20261008/controls-v1-failure-review.json)は3回すべての終了とrawを確認した。ALLOC・ROOT・STATEには到達せず、残る11 probeは未実行である。sourceレビューとrootレビューで、通常の `drv-run` が追加する `ck-r6b-lib` と `ck-run-h`／refinement再読を、harnessの経路に含める必要を見落とした。これは状態・容量試験のPASSではない。元19本のコード差分監査とは別の失敗として保存し、V1を再実行せず、通常経路に合わせたV2を新規登録・レビューする。

通常の `drv-run` を使う状態試験V2は、2回のharness build・12 probeの14回を完了し、[独立raw監査](evidence/coscientist-aha-funnel-20261008/controls-v2-actual-review.json)もPASSした。最初の実際の根はSIR115、FN4、frameのns9/depth4/h1で、8,388,608要素のscalar MとGの149,610要素を比較した。clean、CODE残容量0〜4、dirty MMERR901の7件は、正確に検証した成功時の3 CODEセル以外が一致する。容量不足の途中状態とskipも一致し、エラーは4101を保持した。合成した5件は内部readiness guardの拒否だけを検査する。V1失敗3回を含めた累積は17回である。この診断receiptはfull memory dump、物理register、すべての入力の意味保存証明ではない。発行されたEXTRの4177入力実行と、追加の実際にchecked/loweredされたliveness負例はまだ未検証である。

元19本の新しいrunner buildは、最初の `xcrun --find clang` の照会1回が終了コード0だがstderrを出し、厳密な照会条件で停止した。[失敗の監査](evidence/coscientist-aha-funnel-20261008/runner-v2-failure-review.json)はbuild0件・機能呼出し0件を確認した。出力はXcode内のclangを選び、既存C資料はCommandLineTools内のclangを使っている。stderrのsandboxに関する因果は独立に証明していない。失敗したrootを再使用せず、プロセス単位のツール選択と新しいrootによる修正を事前登録する。既存のOS・SDK・compiler一致条件とstderr拒否は維持し、グローバルなXcode設定を変えない。

完全な凍結sourceと実行GO・rawは `/Users/junkawasaki/github/workspaces/codex/vector-aha-funnel-source-v1-controls` と `vector-aha-funnel-native-build-plan-v3-root`、`vector-aha-funnel-native-build-plan-v4-root`、`vector-aha-funnel-original19-plan-v3-width`、`vector-aha-funnel-original19-run-v3-root` にある。この保存資料は完全なportable archiveではない。追加のchecked-SIR負例・発行されたEXTRの実行検証と、ONの元19本機能・fuel・資源比較を確認した後に、新しい静穏host cohortで実行速度を測る。以前のCRC32静穏条件不足のFAILやCohortを上書きせず、元19本・C以上の性能という成功条件も変えない。

runner V3 はプロセス単位でCommandLineToolsを選択したが、7件の照会で旧C cohortとの実際の不一致を検出して停止した。[独立監査](evidence/coscientist-aha-funnel-20261008/runner-v3-failure-review.json)では、現在のローカルclangは1700.0.13.5、SDK15.5、OS26.4/25E246であり、旧Cのclang1700.6.4.2、SDK26.2、OS26.2/25C56と異なる。runner build・機能実行は0件。前回を合わせて実照会8件で、同一環境条件は緩めない。新しい環境でCを作り直すか、旧cohortのhostで一致を確認する。別途、古いGOファイルを検出した起動前の失敗も保持し、その段階では照会0件だった。

発行EXTRの4177入力試験V1は、最初のOFF compileが終了コード1で停止した。stdoutは空、stderrは `seed: E2101 unknown or unsupported form 'io-out' (byte 465)`。[独立監査](evidence/coscientist-aha-funnel-20261008/emitted-v1-failure-review.json)でcompile1・extract0・guest0を確認した。単独fixtureにcompiler内部helperを宣言しておらず、source/rootレビューでも見落とした。これは最適化の反例や4177入力PASSではない。通常の `io-out` 定義だけを3 fixtureに追加したV2を新規登録し、演算・入力・比較条件を維持する。

readonly SSH1回・環境照会7件で、zebulunの[実際の環境](evidence/coscientist-aha-funnel-20261008/remote-identity-report.json)が旧C cohortとclang・SDK設定のハッシュ・OS版まで一致した。終了コード0、timeoutなし、stderr空。これはrunner buildや機能・性能PASSではなく、同hostで厳密比較を再開するための前提確認である。

発行EXTR試験V2は4回のcompile/extractが成功した後、全native blobに4バイト整列を求めた検査で停止した。両側とも2,881 B、main offset 2,132で、差分はbyte288〜299だけだった。末尾に文字列データを含むため、全blobの長さを命令整列の条件にしたsource/rootレビューが誤っていた。[停止記録](evidence/coscientist-aha-funnel-20261008/emitted-v2-terminal.json)はguest0・全4回閉鎖を保持する。V1失敗1回と合わせ実行累積5回。比較条件を演算差分だけへ緩めず、末尾データ・全metadata・他の全バイトの一致を維持する修正を、新規V3としてレビューする。

発行EXTR試験V3は、positiveの4 compile/extractで実際のEXTR63/NOP/NOPへの1か所12バイト置換と他の全バイト・literal tail・metadataの一致を確認した。しかし最初のOFF guestがPAIR1318の途中でvector-table-exhausted、終了コード120となり、[失敗監査](evidence/coscientist-aha-funnel-20261008/emitted-v3-failure-review.json)で5回閉鎖・ON guest0・負例0を保持した。1318行の完全出力とpartial行を4177入力PASSにしない。整数出力のloweringが桁ごとにpersistent vectorを作る費用を、資源見積りに含めていなかった。V4では元の演算・入力・機械差分・oracleを維持し、guestのみvector1M・items32Mへ変更する。source上の保守的上限は690,229 descriptor・26,069,681 itemsであり、以前の資源拒否と同等だという主張ではない。V1〜V3の実行累積10回を含め、新規18回の上限は28回。

V4は[18回すべてを完了](evidence/coscientist-aha-funnel-20261008/emitted-v4-report.json)した。positiveと2つの実際に型検査・loweringされた負例、それぞれOFF/ONの6 guestで4,177入力ずつ、計25,062行の結果を独立なmodulo64/signed oracleと照合した。positiveはbyte288の3語だけがLSL1/LSR63/ORRからEXTR63/NOP/NOPへ変わり、他のnative・container・entry offset・literal tailは一致する。負例の全バイトはOFF/ONで一致し、出力も同じだった。前3試験の失敗10回を保持し、実行累積28回である。このcommand ABIではfuel・arena終端値を観測していない。負例の厳密なSIR guard拒否原因、一般的意味保存、元19本機能、性能、製品採用は別の未達条件である。

[保存した全raw packet](evidence/coscientist-aha-funnel-20261008/emitted-v4-content.tgz)は1,187,403 B、SHA-256 `9a68949b37d8ef800c74291a841bddcee16bca179dfade84f0a9f15cecafe6eb`。145 regular member・展開5,305,781 Bを、抽出・実行なしで全件内容照合した。凍結source、入力compiler/loader、GO、生成物、全6 guest出力とrootレビューを含む。元の絶対パス対応をmanifestに保存しており、これは内容の再検証用で、portableなnative再実行手順やloaderのsource-to-binary由来証明ではない。

[独立したV4 raw監査](evidence/coscientist-aha-funnel-20261008/emitted-v4-actual-review.json)は、全18 argv・caps・producer・GO・raw SHA・終了コード・順序と、6 guestの全4,177入力を再実行なしで確認した。[packetの独立内容監査](evidence/coscientist-aha-funnel-20261008/emitted-v4-packet-review.json)は全145 memberを照合し、[coverage検査](evidence/coscientist-aha-funnel-20261008/emitted-v4-packet-coverage-review.json)も余剰・欠落なしを確認した。これらもfuel・arena・速度の証拠にはしない。

元19本のremote runner移植は、archive inventoryの先行検査、組立対象の固定allowlist、tar拡張metadataの上限不足が[独立レビューでHOLD](evidence/coscientist-aha-funnel-20261008/remote-runner-v1-source-hold.json)となった。archive・remote・nativeは0件のまま保存し、最小修正したV2は[独立sourceレビュー](evidence/coscientist-aha-funnel-20261008/remote-runner-v2-source-review.json)を通った。固定470入力を移植し、historical JSONを変更せず、実argvだけを登録した対応へ変換する。assembly・転送3process・runner build最大33process・機能171processは、それぞれ別の有限GOと監査で進める。

固定packetの[組立監査](evidence/coscientist-aha-funnel-20261008/remote-runner-assembly-review.json)は285 regular member・17,252,627 payload Bを確認した。続く[転送・展開監査](evidence/coscientist-aha-funnel-20261008/remote-runner-transfer-review.json)では3processが終了コード0・timeoutなし・stderr空で閉じ、登録先zebulunの専用rootへ285ファイルを展開したreceiptとexact pinsが一致した。追加remote disk rescanを行った主張ではない。転送監査時点ではrunner build・guest・速度は0件であり、その後の33process有限buildと171件の結果は以下に記録する。


remote runner buildは[独立実監査](evidence/coscientist-aha-funnel-20261008/remote-build-actual/actual-review.json)を通過した。環境照会14件・元19本のbuild19件、全33子processが終了コード0・timeoutなしで閉じた。Cと同じclang・SDK設定・OSを前後で確認し、19 Mach-O runnerと埋込みOFF/ON/C入力を照合した。全clang呼出しは23件。launcher/collector V1はidentityQueriesのschemaと出力allowlistの不足でSOURCE HOLD、remote実行0件のまま保持し、修正V2を新規レビュー・実行した。[raw archive](evidence/coscientist-aha-funnel-20261008/remote-build-actual/result.tgz)は522,021 B、94 payload member・展開2,666,544 B。このbuildのみでは機能・速度を認定しない。

続く[有限171件の独立raw監査](evidence/coscientist-aha-funnel-20261008/remote-functional171/actual-review.json)もPASSした。元19本をbaseline/OFF・candidate/ON・同hostのCの3armで、n=0・1・登録済み最大nの3入力ずつ実行した。全171件が終了コード0、stderr空、timeoutなし。全57組でCの結果oracleと一致し、native pairの論理fuel消費・4arenaのcapacity/最終used値も完全一致した。新しいrunner buildやC body変更はなく、各runner・入力・toolchainのhashは凍結したbuild cohortに一致する。

[封印raw](evidence/coscientist-aha-funnel-20261008/remote-functional171/result.tgz)は46,453 B、SHA-256 `db1e1ade4b54e389bcc310b565bdd97da864a9770b06caef73903bd851fbbf72`、348 payload member（inventoryを含むtar entryは349）・展開609,084 B。launcher1 SSHとcollector1 SSH/1 SCPの全3transportも閉じた。独立監査SHAは `06fa42b3ab3d90df87c7d234abb8c68ccfebf0a50d19195f186f0b43a23c6efc`。arenaは最終呼出しの終端観測であり、peak/全内部状態の証明ではない。elapsed値を性能結果に使っていない。静穏hostでの新しい元19本の速度比較・公式スコア・C以上の目標・製品採用は未達で、既定OFFを維持する。

## timed CPU計測を加えた新runnerの機能確認

短い呼出しでCPU tick差分が0の場合も構造的な診断を返す変更だけを加え、元19本のrunnerを新規buildした。[独立build監査](evidence/coscientist-aha-funnel-20261008/timed-window19/build-independent-report.json)で19 build・14環境照会の全33件の閉鎖、埋込みnative38/C19/header19の一致を確認した。SDK aliasから26.2への解決はremote sourceが記録したassertionであり、独立したfilesystem traceではない。

最初のcollectorは入力inventory変数を出力bytesで上書きしてpostguardに失敗した。SSHの終了コード0を成功証拠にせず、stderrのTypeErrorとSCP未実行を保持した。修正版V2では入力・出力変数を分離し、合成データによる全成功経路もsource段階で確認してから新規収集した。buildは繰り返していない。build launch1・失敗collection1・修正collection2の計4transportを区別する。レビュー中の改行表現の誤読も保持し、LFの実byte数とarchive一致による訂正を別記録にした。

続く[新171件の独立機能監査](evidence/coscientist-aha-funnel-20261008/timed-window19/functional171-independent-report.json)はPASSした。元19本×3入力×3armの57組すべてで、各armのresult・fuel・native4arenaの終端値が前の受理済み171件と完全一致した。Cのarenaはunavailable/null、論理fuel消費0である。新しいCPU telemetryの構造も検査したが、144件はtick差分0であり、静穏さや速度の証拠には使わない。CPU APIはsourceと出力に結び付いた証拠で、独立したOS traceではない。新171件はlaunch1・collection2のみで再実行なし。

[全内容packet](evidence/coscientist-aha-funnel-20261008/timed-window19/content.tgz)は2,448,411 B、SHA-256 `b4023ef9b09470c110ad19f7bc01c073b0dd68a33d66bb6d7c727256a70ad586`。716 logical pathsを403 regular membersへ重複排除し、展開12,524,321 B。ソース・有限GO・前提レビュー・raw・失敗と訂正を保持する。この段階で新しい性能campaignは実行しておらず、公式Embenchスコア・C以上の性能・CIDによる高速化・製品採用は未認定である。

[packetの独立内容監査](evidence/coscientist-aha-funnel-20261008/timed-window19/packet-independent-report.json)は全403 members・716元ファイルと、171件の実監査が参照する706依存証拠の収録・byte一致を、展開やnative再実行なしで確認した。

## 新しいtimed-window V2の部分結果

V1の実行前source reviewで初回失敗の収集とsource-pins再照合に不備が見つかった。V1は未実行のHOLDとして保存し、修正版V2を別のソース・出力・GOへ固定した。独立reviewとroot GO後、zebulunで一度だけ実行・封印・収集した。[独立raw監査](evidence/coscientist-aha-funnel-20261008/timed-campaign-v2/independent-report.json)は2,803 runnerと5,606 load query、全8,409子プロセスの終了、既存171件との結果／fuel／4 arena／C nullの同一性、全順序・calibration・静穏判定を再計算した。

元19件中16件に静穏条件を満たす30組が揃った。tarfind・wikisortはcalibration上限、udは90組中2組だけ合格してPARTIAL。失敗したworkloadのretryや過去結果とのpoolingはない。全19件のGMはnull、C達成・公式スコア・製品採用はfalseである。以下は完了した16件の同一host・元body当たりnsであり、別のEmbench標準referenceへ正規化した公式スコアではない。

| 元workload | Kotoba候補 ns/body | C ns/body | Kotoba/C |
|---|---:|---:|---:|
| aha-mont64 | 710.871 | 581.167 | 1.2232 |
| crc32 | 3248.174 | 1817.916 | 1.7868 |
| depthconv | 120.705 | 36.790 | 3.2809 |
| edn | 11317.008 | 813.282 | 13.9152 |
| huffbench | 52906.789 | 8031.905 | 6.5871 |
| matmult-int | 3526.357 | 1018.817 | 3.4612 |
| md5sum | 10748.297 | 2721.447 | 3.9495 |
| nettle-aes | 8197.603 | 1537.959 | 5.3302 |
| nettle-sha256 | 2801.162 | 237.403 | 11.7992 |
| nsichneu | 716.282 | 84.913 | 8.4355 |
| picojpeg | 215996.307 | 11853.854 | 18.2216 |
| qrduino | 277255.821 | 23686.771 | 11.7051 |
| sglib-combined | 36262.661 | 6164.435 | 5.8826 |
| slre | 7815.652 | 1116.852 | 6.9979 |
| statemate | 528.303 | 34.215 | 15.4407 |
| xgboost | 1194653.125 | 194730.629 | 6.1349 |

別保存した完了16件の統計を独立に再計算した。全16件でrelative SD≤0.1だが、C以上は0件、baseline／Cに対する採用基準を満たすものも0件。Ahaのbaseline/candidate平均比は1.0290197583、平均差20.629 nsはSD和56.742 ns未満、paired bootstrap95%CIは[1.021385,1.036317]で1.05未満である。残り18件のOFF／ON生成バイトは同じなので、それらの小さい時間差をEXTRの効果と解釈しない。EXTR候補は既定OFFのまま、次の調査では大きいC差の生成処理・call・vector・fuel経路を根拠付きで区別する。

[完了16件の統計独立監査](evidence/coscientist-aha-funnel-20261008/timed-campaign-v2/analysis-report.json)は全mean・sample SDと32個の20,000回paired bootstrap CIを再計算した。最初の全内容packetは転送reviewの二次依存14件が欠け、[HOLD](evidence/coscientist-aha-funnel-20261008/timed-campaign-v2/packet-review-v2-hold.json)として保持する。[追加封印V3](evidence/coscientist-aha-funnel-20261008/timed-campaign-v2/revision-v3/content.tgz)は4,442,914 B、SHA-256 `f03cf0ccdbe7a714c21920671fb711c2f4ff52cab330ff64744b859319336667`、6,630 regular members・19,756元パス・展開35,881,825 B。[独立内容監査](evidence/coscientist-aha-funnel-20261008/timed-campaign-v2/revision-v3/independent-packet-report.json)は全primary19,733依存と3種類の二次依存の完備を照合した。追加は証拠の収録だけで、実験・計測・転送を再実行していない。
