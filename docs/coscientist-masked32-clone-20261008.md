# 定数引数のprivate cloneによるmasked32最適化の準備

元19 workloadを変更せず、checked/lowered SIRの純粋な2引数calleeの構造を判定して定数引数をprivate cloneへ移すKotoba実装を作った。workload名による分岐は使わない。実際のSHA10／AES4の14呼出に13 clone・195 SIR行が対応する。元の引数評価、OP-FUELと内側のmask呼出を保持し、既存のgeneratorへ渡す。現段階ではEXTR発行もcall/frame除去も実装していない。

`.kotoba` helpersを追加し、Unityの`gn-run`にだけdefaultOFFの入口を置く隔離実験とした。元Mを保持し、独立した全8388608-cell copyにのみ書き込んで生成が成功した結果を返す。生成時の拒否は元Mで元generatorへ戻るが、追加arena allocationやVMfuelは巻き戻さない。追加64MiBと元Mの64MiB、ほかのpoolの資源契約が必要である。staleなLABEL countを受理する局所guardの不足も残るため、ON installerをまだ実行しない。合法なSIR分岐はLABELを入口としてdescriptorをresetするので、raw machine branchがCALL直前のCONSTを飛び越す反例とは区別する。

rootとwidthのSOURCE／driverレビュー後、固定した既存selfhost producerでOFF／ONのcompile・extract計4呼出を実施した。[独立raw監査](evidence/coscientist-masked32-clone-20261008/build-v1/independent-report.json)は全144依存、4 argv・raw・read-only source copy・sole main0 export・全KSEED payloadを照合した。すべて終了コード0・stderr空で閉じ、OFF native956616 B／SHA `31ffef7c…`、ON956632 B／SHA `55d14120…`になった。生成されたどちらのcompilerも実行imageとして用いなかった。これはsourceのnativeコンパイル受理で、installer実行・原19本の変換・固定点・runtime fuel/frame/ABI・性能の証拠ではない。

[実装と選択保存資料](evidence/coscientist-masked32-clone-20261008/build-v1/snapshot.json)に新helpers、実際のsource copy、native/container、rawと監査を保存する。完全な144依存archiveではなく、全入力は元workspaceのpinと内容で保持する。新規アルゴリズムの隔離試験として実装し、製品経路の機械的refactorは行わない。SOURCE・driver・raw監査に参加したwidthの役割をreportに記す。次は新しいSOURCEでfresh LABELの事前検査と資源契約を閉じ、全19本の機能とquiet-host C比較を別に実行する。

## ラベル検査を加えたV2と資源測定用ローダー

V2は追加allocationより先に、元SIR全体のFN／END所有者とLABELの所属・範囲を検査する。stale LABEL countの反例を拒否するが、任意の壊れたSIRのbranch領域・LABEL一意性まで検証する仕組みではない。実験対象は既存のchecked／lowered producerが作る有効なSIRに限定する。

[独立build監査](evidence/coscientist-masked32-clone-20261008/build-v2/independent-report.json)は221入力とOFF／ONのcompile・extract計4呼出を照合した。OFF native957416 B／`f56af2bd…`、ON957432 B／`899b63be…`を生成し、4呼出は終了コード0・stderr空で閉じた。生成compilerの実行はまだ0で、追加arena・固定点・元19本・性能は未認定である。

資源量を測定する前提として、現在のCローダーソースから別の診断ローダーを作った。[独立監査](evidence/coscientist-masked32-clone-20261008/loader-v2/independent-report.json)は16呼出、前後14のtoolchain照会、210ヘッダー（4967667 B）、同じコンパイル条件と197736 BのARM64実行ファイル`e14c2919…`を照合した。C runtime/bootstrapのビルドであり、KotobaコードのLLVMコンパイルへの切替ではない。ローダーによるguest実行はまだ0なので、機能やarena使用量の証拠と区別する。

次のOFF資源probeは実監査のschemaとdriverの要求が一致せず、SOURCE段階でHOLDにした。実監査を書き換えず、新しいdriver版で正確なfield／statusを結び直してから実行する。旧失敗・HOLDは保存する。2つの選択snapshotは完全な依存archiveではなく、生成物とraw・監査の保存コピーである。最適化は製品へ採用せず、元の19本とquiet-host C比較を最終基準に保つ。

## OFF側の実資源観測

schemaを修正したfresh V4をrootとcontrolsがSOURCEレビューし、OFF専用の2呼出だけを実施した。[独立raw監査](evidence/coscientist-masked32-clone-20261008/off-resource-v4/independent-report.json)は533入力、新ローダーとOFF compilerの生成経路、2 argv／環境／raw／終了状態を照合した。元AES／SHAの全KSEEDは既存baselineとバイト一致した。

| OFFコンパイル対象 | pair peak | string byte peak | vector descriptor peak | vector item peak | 報告heap指標（B） |
| --- | ---: | ---: | ---: | ---: | ---: |
| nettle-aes | 14880 | 1102400 | 6 | 8510135 | 69421656 |
| nettle-sha256 | 8238 | 942586 | 5 | 8417819 | 68417026 |

heap指標は4 arenaの別々のpeakに対応するサイズを掛けた和で、同時使用最大値・RSS・時間ではない。残る12 fieldは操作回数などの活動総数で、全17 fieldをpeakとは呼ばない。`KEXE_FUEL=off`は従来のcompiler診断と同じ非計量モードを明示したもので、生成workloadのfuel契約を変えない。ONの追加M・暗黙pair・出力処理の余裕やphysical fuelはまだ証明していない。元19本の実行・selfhost固定点・C性能比較も別のgateに残す。

## ONによる元19本のコンパイルと観測器の失敗

固定した資源上限でON compilerを初めて実行した。[独立監査](evidence/coscientist-masked32-clone-20261008/first-on-v1/independent-report.json)は元AES／SHAのcompile・extract計4呼出の終了、566入力、生成物と17資源fieldを照合した。AES native40432 B（従来比+312 B）／`627fdd61…`、SHA10548 B（+1000 B）／`42aabf57…`を生成し、公開exportの名前・順序・arityを保持した。AESのexport offsetは+12 B、SHAは不変だった。サイズ増加だけからcloneの実際の所有者や意味保存は断定しない。

| ONコンパイル対象 | pair peak | string byte peak | vector descriptor peak | vector item peak | 報告heap指標（B） |
| --- | ---: | ---: | ---: | ---: | ---: |
| nettle-aes | 14880 | 1102720 | 7 | 16899647 | 136538088 |
| nettle-sha256 | 8240 | 944288 | 6 | 16809398 | 135551408 |

続く17本のcompile・extract計34呼出も終了した。[元19本の独立監査](evidence/coscientist-masked32-clone-20261008/original19-v1/independent-report.json)は746入力と元matrixのsource・symbol・arity・入力profileを照合し、17本の全KSEEDが従来とバイト一致することを確認した。最初の2本は再実行せず、計38呼出を19本のコンパイル証拠として結合した。これは生成workloadを実行した証拠ではない。次は同じC参照・OFF・ONを元19本の95入力で比較し、nativeのresult／fuel／4 arenaを確認する。比較runnerのビルド33呼出と機能確認285呼出を別段階として登録する。

clone・call・frameを読み取り専用で観測する版は、初回compileで停止した。[失敗の独立監査](evidence/coscientist-masked32-clone-20261008/observer-failure-v1/independent-report.json)は599入力、最初の1呼出の終了、未実行の残り5呼出、再試行なしを照合した。stdoutは空で、stderrに`E2104 type mismatch in 'case': expected :i64 (byte 959829)`と17資源fieldがある。整数`case`の既定値にkeyword `:else`を置いた新しい診断helperの型エラーで、資源枯渇の診断ではない。旧source・失敗namespaceを保存し、修正はfresh版として再レビューする。観測器の6呼出成功、実際のclone所有者、機能・性能は未認定である。

上記3 snapshotは選択したsource・生成物・raw・監査のコピーで、完全な依存archiveではない。元入力はworkspaceの内容とpinで保持する。製品のdefaultOFF、既存C性能結果、selfhost固定点の認定は変更していない。

## 観測器V3の実行と保存済みAESの検査

新しいCST規則で整数`case`の末尾`:else`を2箇所削除し、helperの逆変換とvalidatorのバイト一致を確認した。既存refactor規則には該当規則がないため、新しい診断コードの`:human` authoring規則として適用し、native `amu refactor verify`の成功とは扱わない。別のSOURCE／driverレビュー後、fresh namespaceで観測器compile・extractと元AES compileの3呼出が正常終了した。[独立raw監査](evidence/coscientist-masked32-clone-20261008/observer-v3-failure-and-saved-aes-v4/independent-failure-v2/report.json)は648入力、観測器native963376 B／`f93645d6…`、AESの全KSEED／exportが通常ONと一致することと17資源fieldを照合した。

その後のホストvalidatorが、V3のフォルダーに配置されていない`proposed-packets.json`を読もうとして停止した。旧型エラー1呼出とは別のFAILで、native3呼出は正常終了、AES extractとSHAの2呼出は未実行である。6呼出PASSへ再分類しない。

fresh V4はvalidatorのコードを一切変えず、元の固定packetを配置した。SOURCEレビュー後、保存済みAES stdout／containerを1回だけ読み取り検証し、4呼出箇所・3 clone・45追加SIR行と通常ONの全バイト一致を確認した。cloneを呼ぶBLとFREC／CODEの対応も得たが、opcodeの静的数はCFG・physical frame・fuelの証明ではない。[独立actual監査](evidence/coscientist-masked32-clone-20261008/observer-v3-failure-and-saved-aes-v4/independent-offline-v4/report.json)はrootの検査と全旧失敗閉包、FIX→CODE、通常ONの全コンテナを照合し、固定AESだけを受理した。登録validatorを監査側で再実行せず、nativeの再実行も0である。残る3呼出は既存の観測器とAES成果物を使う別の実行として登録し、SHAと機能比較の認定は保留する。

このsnapshotも選択保存であり、完全な依存archiveではない。高速化、元19本の生成プログラム実行、quiet C比較、自己再ビルドの固定点はまだ認定していない。

## 未実行だったAES抽出・SHA観測の終了

残る3呼出だけをfresh領域で実行し、AES extract、SHA compile／extractは終了コード0で閉じた。[保存rawの監査](evidence/coscientist-masked32-clone-20261008/remaining3-v2/report.json)は通常ONの全コンテナ／native一致、scope内へコピーしたAES入力の内容一致、SHAの10サイト・10 clone・150 SIRとFIX→CODEを照合した。AESと合わせて14サイト・13 clone・195 SIRである。監査者はdriver作者でもあるため、その参加を明記し、[第二のrawレビュー](evidence/coscientist-masked32-clone-20261008/remaining3-v2/second-review/report.json)も全3呼出・コンテナ・SHA所有者を照合した。第二reviewerの観測器作者としての関与も開示し、完全な作者非関与とは呼ばない。旧FAIL計4呼出は保存し、この継続3呼出で成功へ再分類しない。

リモート比較runnerはtoolchainの前半7照会を通った後、最初のCビルドで停止した。内容ハッシュ名の入力が拡張子を失い、ClangがCソースとして認識しなかった。C内容・元flags・元19本を保持し、別のfresh領域でコンパイル入力だけに`.c`別名を与える修正を準備する。機能285呼出、quiet性能比較、selfhost固定点は未実行・未認定である。

C入力別名を修正したfresh remote-v3で、元19 runnerのビルドと前後14照会は閉じ、成功reportと全93ファイル（2677319 B）を読み取り回収した。[独立raw監査](evidence/coscientist-masked32-clone-20261008/remote-build33-v3/independent-report.json)が19ビルド・14照会・33閉じた呼出、同じC toolchain／SDK、型付き入力役割と19 runnerを照合した。rootはこのビルド証拠だけを受理し、生成workloadの285機能呼出を別GOで開始した。時間比較はまだ認定しない。

## 元19本のC／OFF／ON機能比較

比較285呼出が正常に閉じ、[独立raw監査](evidence/coscientist-masked32-clone-20261008/functional285-v3/independent-report.json)は回収575ファイルと各argv・環境・空stderr・終了コードを照合した。元19 workloadの95入力（0／1／2／17／32、depthconvの最後は2000）でC／OFF／ONの結果が一致し、native OFF／ONのfuelと4 arenaのterminal使用量も一致した。Cのarenaは取得不能としてnullを保持し、架空のnative arenaを与えない。

native fuel消費は1〜11079189。terminal使用量の最大はpairs256／vectors417／vector-items39566／strings0であり、arenaのpeakではない。この有限機能試験のelapsedとRSSを速度比較へ流用せず、公式Embenchスコア、quiet速度、自己再ビルド固定点、製品採用は別に未認定として残す。旧リモートFAIL1ビルド／7照会も保持した。

## 汎用full64 shift／OR融合のnative受理

private cloneの9行SIRパターンと直後の1引数CALLを構造で照合し、元の3 CODE語を`LSR + ORR shifted + NOP`へ置換する隔離Kotoba emitterを実装した。workload名では分岐せず、元のgeneratorの状態更新を実行してから、語数・descriptor・補助tableが一致した場合だけ3語を書き換える。fuel・引数評価・nested CALLは残す。逆順パターンではinactiveなX10の値が変わるため、temp1／2／3が次のCALL以降で読まれない条件を要する。任意の物理register一致は主張しない。

診断stderrの契約不足をSOURCE段階でHOLDにし、fresh driverで17 counterを厳密に読み取るよう修正した。その後OFF／ON compile・extractの4呼出は正常に閉じ、[独立監査](evidence/coscientist-masked32-clone-20261008/shift-orr-build4-v2/independent-report.json)が715入力、source copy、全KSEED／native、argv・環境・rawを確認した。生成したコンパイラの実行は0であり、この変換の実状態・容量・liveness、元19本の機能、自己再ビルド固定点、速度はまだ認定しない。[保存sourceと生成物](evidence/coscientist-masked32-clone-20261008/shift-orr-build4-v2/snapshot.json)も完全な依存archiveではない。

## 次の仮説: scalar clone の呼出・frame コスト

[静的 census と事前設計](evidence/coscientist-masked32-clone-20261008/scalar-cost-and-fuel-design-v1/snapshot.json)は、AESの3 clone／4サイトとSHAの10 clone／10サイトを元SIR・FREC・CODEから再照合した。全13 cloneは各25語、80 B frameで、成功経路はRETを含め23命令を実行する。そのうちshift／shift／OR／maskは4語、entry fuel transactionは5語である。元SHAソースの固定ループから、正の1 bodyにつき2ブロック×（48 schedule更新×4 rotation＋64 rounds×6 rotation）＝1152 clone呼出、clone内26,496命令と数えられる。これはソース由来の命令実行数であり、実測時間や支配的な時間割合ではない。shift／OR融合だけでは呼出・frame・fuelメモリ操作が残る。

次の汎用仮説は、閉じた純粋scalar bodyと検証済みmaskの呼出展開である。現在の`di-body`は`OP-FUEL`と`OP-CALL`を拒否する。単に許可へ変えると、`di-init`がleafモードへ切り替えるため、元のnonleaf fuel publication／枯渇trapを変えるおそれがある。`OP-FUEL [0,0,0]`の0はcharge無しを意味しない。元の減算・分岐・trap・成功時storeを同じ順序で保存し、最初はfuelを持たない閉じたmask calleeだけを展開する設計を登録した。引数評価、live register／context、未知effect、label ingress、部分的CODEエラーと新しいcompiler資源契約も別々に検査する。実装GO・native control・元19件の機能・quiet速度・製品採用はこの設計からは認定しない。

## shift／OR の元AES・SHAへの実生成

新しいAmuで元AES／SHAのcompile・extract4呼出が正常に閉じ、[独立監査](evidence/coscientist-masked32-clone-20261008/shift-orr-original-aes-sha4-v1/independent-report.json)が全入力・argv・環境・raw・17 arena counters・完全なKSEED／nativeを照合した。AESは3か所、SHAは10か所が登録済みの3命令へ置換された。長さ（40,432／10,548 B）、全export・offset・arity、残る全バイトと末尾は一致した。これは命令パターンの実生成の観測であり、owner／CFG・X10の実行時安全性・guest機能・速度の保証ではない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/shift-orr-original-aes-sha4-v1/snapshot.json)は全755依存の実バイトを含むportable archiveではない。

## 実状態・容量・拒否の34ケース

診断ハーネスの初回は成功マーカー777を通常のMC fallbackが失敗と扱って再生成し、3呼出でFAILした。修正版の3呼出はnativeで正常終了したが、host検証器が生成前の件数でclone ownerを調べたためFAILした。どちらも再分類せず保存した。V3は診断結果を保持し、実際の生成後SIR／FN件数を出力してowner・END・CALLを厳密に検査する。

V3のcompile／extractと34ケースの計36呼出は正常に閉じ、[独立監査](evidence/coscientist-masked32-clone-20261008/shift-orr-components-v3/independent-report.json)が全raw・環境・入力・17 counters・34比較を照合した。元AES／SHAの2方向で、scalar Mの8,388,608項目と全G、容量0〜4、dirty error、高さ・skip・shift範囲・レジスタ重なり・frame・後続使用・FUEL境界を確認した。成功時は登録した3 CODE語だけを比較対象から除き、拒否時は全状態一致を要求した。これはnativeソース拘束の有限述語による比較であり、全メモリの外部dumpや物理X10／NZCV・runtime fuel・一般の意味保存証明ではない。過去6FAILと新36を合わせ累計42呼出として保持し、guest機能、元19本、自己再ビルド、quiet C比較は別のゲートとして続ける。[選択snapshot](evidence/coscientist-masked32-clone-20261008/shift-orr-components-v3/snapshot.json)。


## shift／OR の有限AES・SHA機能比較

元AES／SHAの入力0／1／2／17／32で、従来のmaskedON・新SR・Cを比較した30呼出が正常に閉じ、[独立監査](evidence/coscientist-masked32-clone-20261008/shift-orr-functional30-v1/independent-report.json)が全raw・argv・環境・入力・10組の結果を照合した。native 2 armは結果の0／1、正常終了、fuel残量、4 arenaのcapacity／terminal使用量がすべて一致した。Cは同じ結果を返し、fuelは不変、native arenaは取得不能のnullを保持した。

| 入力32の対象 | native fuel消費（両arm） | terminal pairs | terminal vectors | terminal vector-items | terminal string bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| nettle-aes | 427363 | 0 | 1 | 635 | 0 |
| nettle-sha256 | 79084 | 0 | 3 | 290 | 0 |

このterminal値は子の終了後に共有状態から読む値で、compiler診断の独立peakではない。nativeはsource-bound e14 loaderの同一contextで実行し、以前のself-contained285とは範囲を分ける。CはOS26.2／SDK26.2／Clang17で作成済みのimmutable consumerをローカルで機能確認に再利用した。新しいローカルCビルドや現在のtoolchain一致、elapsed／RSSによる速度比較は認定しない。有限5入力の一致は一般のX10／NZCV／CFG安全性、元19本の全機能、自己再ビルド固定点、公式Embenchスコア、製品採用、CIDによる効果の証明ではない。[selected snapshot](evidence/coscientist-masked32-clone-20261008/shift-orr-functional30-v1/snapshot.json)にはsource・raw30・生成物・実監査を保存し、全依存closureの実バイトは重複保存していない。


## SR版の元19本生成と3世代自己再ビルド

残る17本のcompile／extract34呼出と、自己再ビルドG2／G3／G4の6呼出がすべて正常に閉じ、[独立監査](evidence/coscientist-masked32-clone-20261008/shift-orr-full19-selfbuild40-v1/independent-report.json)がraw・環境・17 counters・入力・完全な生成物を照合した。17本は旧maskedONのKSEED／nativeと全バイト一致した。保存済みAES／SHA4呼出を再実行せずに結合し、元19本の生成経路を確認した。

G1からG2も全バイト一致し、G2・G3・G4のコンテナとnativeはすべて同一である。nativeは961,272 B、SHA256 `5404f22ac455d66c1295a4ad0d90987722262b86b1aacd9bc9d69c8ad5cafd69`。同じunityソースを各世代がコンパイルし、`main` offset0／arity0を保持した。これはSRコンパイラの固定点であり、製品CLIの完全selfhostや残る17本の新guest実行、C以上の速度・公式スコア・製品採用を認定しない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/shift-orr-full19-selfbuild40-v1/snapshot.json)は全依存closureの実バイトを重複保存したportable archiveではない。


## 燃料を維持したscalar DAGのnative build4

現在のC比較では高速化を採用できなかったため、次の仮説として、private i64関数の限定された呼び出しを局所展開するdefault-OFF候補をKotobaで実装した。元の燃料消費をframe初期化前に1回行い、引数評価・呼び出し元descriptor・contextを保存して戻す。単一の末尾mask呼び出し、型・effect・entry label・branch/address ingress・CODE容量を検査し、未対応形は元の経路へ戻す。書込み開始後の失敗はgeneric fallbackへ戻さず拒否する。

[独立SOURCEレビューと実raw監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-build4-v2/reviews/actual-independent/report.json)付きのcompile／extract4呼出は全終了した。OFFは元のSR5404の全KSEED／nativeと一致した。ONは969,864B、SHA-256 `d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a`、単独main offset0の完全payloadを抽出した。増加8,592Bはcompilerサイズであり、速さではない。SOURCEのword計上135はvclear1を加えた136へ補正し、192 reserve内とした。旧v1 driverは実行せず保持した。

[選択snapshot](evidence/coscientist-masked32-clone-20261008/fuel-dag-build4-v2/snapshot.json)は全1,700依存の実バイトarchiveではない。生成したONコンパイラの実行、燃料0／1／2と呼び出し元状態のnative controls、Embench全19本、selfhost固定点、quiet C比較は未資格である。製品採用はしない。


## leafのvector descriptor再利用：native build4

default-OFFの別候補として、frameがなかった短いleaf関数に保存レジスタx19..21を予約し、元のmode3 descriptor再利用を適用するKotoba helperを実装した。元のsl-assignを先に実行し、単一typed vector・全到達経路の同一local由来・branch/call/allocator不在を確認する。元のhandle検査、毎回のindex検査、fuelと返り値ABIは保持する。新frameは最大160BとFP/LR16Bで、実行資源・CODE容量の条件が変わる実験である。静的なSHA／MD5の候補は実採用や頻度ではない。

[独立実監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-build4-v2/reviews/actual-independent/report.json)で、selfhost Amuのcompile／extract4呼出の終了・全17 counters・OFFの全SR5404一致、ONのsole main0／完全payloadを確認した。ONは966,320B、SHA-256 `258670d2371f3c03167fb02f574c6597479a1ce3e0af9a42cac8e41499d56931`。入力registryの形式を誤認した旧driver v1はSOURCE段階でHOLDし、未実行のまま保存した。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-build4-v2/snapshot.json)は全1,726依存の実バイトarchiveではない。生成したONの実行、採用owner、saved register／fuel／trap／ABI、元19本、固定点、性能は未資格である。

## fuel DAG component18：native3成功・host検証FAILを保持

[独立失敗監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-component18-failure3-v1/reviews/actual-independent/report.json)で、diagnostic compile／extractと最初のcase0の3呼出はnative rc0・全17 countersで閉じた一方、host validatorがALLOCの成功値をMM-R1=0と期待して停止したことを確認した。原実装は成功時1、失敗時0であり、実rawはR1=1／error0だった。case0にはSTATE成功／END777と元の5 fuel命令が記録されたが、失敗campaignを18件成功と読み替えない。残る15件は未実行。

修正対象はhost validatorの期待値だけで、native helper／fixture／imageを変更せず、case0を再実行しない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/fuel-dag-component18-failure3-v1/snapshot.json)に旧FAILを保存した。SOURCEレビューでも対応を見落としたことをreportへ明記した。保存raw再検証と未実行case1..15は別の有限継続とし、生成CODEのCPU実行・nonresuming fuel trap・性能の資格とは区別する。

## Fuel DAG component16ケースの受理（旧FAIL3を保持）

[保存済みcase0の独立offline監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-component18-accepted-v3/reviews/offline-actual-independent/report.json)がV3の1回だけの再判定を受理した。修正はallocatorの成功値MM-R1=1を期待する1箇所で、fixture・ネイティブ成果物は変えていない。検証器はハッシュ確認済みのソースバッファを直接実行し、未固定のPython bytecode cacheに依存しない。旧3呼出のFAILED terminalを保存し、case0・compile・extractを繰り返さなかった。

別登録の残り15呼出は全てrc0・reapedで終了した。[独立actual監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-component18-accepted-v3/reviews/remaining-actual-independent/report.json)が全raw、17資源counter、状態guardとfuel命令を確認した。保存済みcase0との合計16ケースを受理し、累計native呼出は18である。live REG/HOME/LOCALalias、CODE容量、dirty error、leaf/freg/frame、charged inner、非terminal call、branch ingressの各条件を含む。これは凍結したnative診断の全状態比較predicateに拘束された有限証拠で、M/G全体を独立serializeした一般証明ではない。

fuel0/1/2は抽象モデルで、5つの出力命令を確認した。生成コードのCPU上の非復帰trap・fuel・ABI・arena同等性、元19本の新候補実行、候補自身の固定点、C性能比較は未資格である。[選択snapshot](evidence/coscientist-masked32-clone-20261008/fuel-dag-component18-accepted-v3/snapshot.json)は完全な依存archiveではない。ComputeCID／ResultCIDによる解析再利用の意味契約と、生成コード最適化のfuel保存を分けて検証する方針を維持する。

## Leaf descriptor read cacheの実owner観測10

default-OFFのLC候補が出力したMD5/SHAを、それぞれ通常経路とreadonly観測経路で作成した。計10 compile/extract呼出がrc0・reapedで閉じ、[独立actual監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-owner10-v2/reviews/actual-independent/report.json)が全入力、raw、17資源counter、全KSEED/native/export/offset一致を確認した。観測V1は未固定bytecode importを理由に実行前HOLDとし、V2は検証済みdecoderソースバッファを直接実行する。旧HOLDを保存した。

MD5のFN4（SIR146..183）とSHAのFN3（77..114）に各1 ownerがあり、各4 vector readがmode3に入った。frame112、saved registers3。独立したraw/table再構成と実CODE wordsの確認ではx19/x20のSTP、x21のSTR、flag21=0、復元LDP/LDR、全8 readのCMP/BLO/UDFが残っていた。これは静的予測だけでなく実候補のowner・layout証拠であるが、CPUでの高位レジスタ保存・trap・fuel・ABIの実行検証ではない。

[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-owner10-v2/snapshot.json)は完全な依存archiveではない。元19本の新候補実行・候補自身の固定点・quiet C比較・採用は未資格。ComputeCID解析再利用の性能効果とも区別する。

## Scalar DAGの実命令列8ビルドとguest10 HOLD

2つの型付きfixtureをOFF/ONでcompile/extractし、全8呼出が正常終了した。[独立actual監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-emitted-build8-v1/reviews/actual-independent/report.json)が全入力とraw・資源counter・payloadを確認し、全232/272/216/216Bを独立decode/reencodeした。正例はbench入口140、196Bまで同一で、OFFのBL196→private entry16をONの5命令fuel196..212と6命令算術216..236へ置換していた。末尾は40B移動、負例は全KSEED/native一致。固定benchから到達する経路の入口charge1＋outer charge1、追加charge0、x7保持とfuel内部への不正入口なしを静的に確認した。これは実CPUのtrap試験ではない。

[guest HOLD](evidence/coscientist-masked32-clone-20261008/fuel-dag-emitted-build8-v1/go/guest-hold.json)。事前登録が要求したordinary typed SIRのowner/caller対応と2つの静的mask参照の記録はbuild rawにない。機械語のprivate entryを型付きFNIDの証拠に読み替えず、guest10はGOなし・実行0で保持した。次は同じ成果物と一致するreadonly SIR/FREC観測を別有限pilotとして準備する。基準を緩めず、旧8件も再実行しない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/fuel-dag-emitted-build8-v1/snapshot.json)は完全な依存archiveではない。C性能・元19本・新候補固定点は引き続き未資格。

## Leaf descriptor cache：MD5／SHAの有限runtime30

5入力（0、1、2、17、32）をOFF／ON／現在Cの3経路で実行し、全30呼出が正常終了した。[独立saved-raw監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-functional30-v2/reviews/actual-independent/report.json)で10組のC結果一致と、OFF／ONの返り値・残りfuel・pairs／string／vectors／itemsのterminal使用量一致を確認した。既存のAmu製nativeを使い、再compileは0。C consumerは現在のC image全バイトを指定位置で照合したが、新しいC toolchain buildや公式Embenchスコアとは呼ばない。

旧V1の未実行SOURCE HOLDを保持し、V2は既存の有限SR driverをLC成果物へ適合した。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-functional30-v2/snapshot.json)は完全な依存archiveではない。高位レジスタの専用canary、異常入力trap、残る17本のruntime、quiet C時間比較は別の検証とする。今回の返り値一致をC以上の速度やCIDによる高速化に読み替えない。

## LC候補：原19本コンパイルと3世代固定点

保持済みMD5／SHAを再実行せず、残る17本のcompile／extract34呼出と自己再ビルド6呼出を終了した。[独立actual監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-full19-selfbuild40-v1/reviews/actual-independent/report.json)が全40呼出・原ソース・producer連鎖・全KSEED/native/export/offsetを確認した。G1／G2／G3は完全なコンテナとnativeがバイト一致し、native966,824B、SHA-256 `5f4f591a1eb3bb46d3042a3463805a5cfb0897b766ee2de4909088be3369e1af`。G0→G1は504B増加して異なるが、事前登録はG1からの固定点を要求しており、その差も保持した。

原19本の成果物はG0によるものなので、G3での原19本出力一致は別の有限38呼出で検証する。今回のコンパイルと固定点は、全19本runtime・製品CLI完全selfhost・性能・公式スコアを認定しない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-full19-selfbuild40-v1/snapshot.json)は全2001依存のportable実バイトarchiveではない。

## LC固定点G3の原19本出力対応38

固定点G3で原19本を改めてcompile／extractし、全38呼出が終了した。[独立saved-raw監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-g3-original19-compile38-v1/reviews/actual-independent/report.json)は各containerがextract前にG0と全バイト一致し、native・全export・arity・offsetも一致することを確認した。原ソースを保持し、G3が実際に同じベンチマーク成果物を作れることを確認した。以前のG0出力を固定点だけからG3の出力と推測していない。

監査者は先のactual40と次のfunctional255 SOURCEに参加し、今回のdriver author／SOURCE reviewer／native実行者とは異なる。読み取り専用の監査で、元呼出を繰り返さない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-g3-original19-compile38-v1/snapshot.json)は全依存のportable archiveではない。全19本のruntimeとquiet C比較は次段階で、今回の一致は性能認定ではない。

## Scalar typed owner：native成功3とoffline失敗1を保持

readonly SIR／FREC observerはcompile／extractと正例compileの3呼出が全rc0で閉じ、正例の全KSEED298B／native272Bは元のON成果物と一致した。しかしhost検証器がstack高さ減少後の再admission、lazy context更新、CODE0 sentinel、1-based CODE offsetを誤認して停止した。[独立失敗監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-typed-owner-failure3-offline-failure1-v2/reviews/native-failure-independent/report.json)。4つ目のextractは実行せず、native FAIL3を保持した。

ソース契約で修正したV2は保存rawをoffline1回だけ再判定したが、FX-BL26 kind4をBL opcodeの保証と誤認して再度停止した。実際のtail-callはB `0x17ffffdf`、変位−33でmask入口へ向かい、relocationはopcodeを保持する。[独立offline失敗監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-typed-owner-failure3-offline-failure1-v2/reviews/offline-failure-independent/report.json)。この期待値はrootと独立SOURCEレビューでも見落とした。V2のFAIL1とSOURCE承認を保存し、候補やfixtureを変更しない。次のV3は厳密なB判定1箇所だけを修正し、typed tail関係と全FIX／target／payload検査を保持する。

## LC：残る17本runtime255、原19本285への結合

残る17本×各5入力×OFF／ON／現在Cの255呼出を終了し、保持済みMD5／SHAの30呼出と結合した。[独立saved-raw監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-functional255-v1/reviews/actual-independent/report.json)が全raw・argv・環境・原ソース・container/native/export・C consumer内の全C image位置を照合した。原19本・95入力・285呼出でC結果一致、OFF／ONの残りfuelと4 terminal arenasが一致。診断のfile上限は全2787依存を保持するため事前登録で448MiB／3072へ明示したが、runtimeの16M fuel・全pool・入力・timeoutを変えていない。

これらのON成果物はG0で作ったが、別のG3原19本全バイト一致38の監査で固定点G3との対応も確認している。新consumerでのABI・専用saved-register canary・異常入力trap・quiet時間比較・公式スコアは別の検証である。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-functional255-v1/snapshot.json)は完全依存archiveではない。

## Scalar DAG：typed owner保存raw受理とCPU guest10

V3はvalidatorの厳密なopcodeをBLからBへ変える1箇所だけを修正し、typed tail関係、全FIX target、35 SIR行、4 typed functions、全272Bの対応を保持した。保存rawをoffline1回だけ再判定しnative0で終了、[独立closeout](evidence/coscientist-masked32-clone-20261008/fuel-dag-typed-owner-v3-guest10-v1/reviews/observer-receipt-closeout/receipt.json)と既存auditorの照合を受理した。旧native FAIL3とoffline FAIL1を保存し、4つ目のextractは実行しない。

component16・実machine build8・typed owner対応をrootが結合して受理し、固定2 fixtureのguest10を実行した。[独立saved-raw監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-typed-owner-v3-guest10-v1/reviews/guest-actual-independent/receipt.json)は全1998依存、10 argv／環境／raw／終了記録、5組のOFF／ON全結果・fuel・4arena一致と全17 counterゼロを確認した。正例n7は初期fuel1で非復帰SIGTRAP／exit120・remaining0、初期2／3でresult16・remaining0／1。負例n−1は初期2／3でresult4294967289・remaining0／1だった。

CPUのfuel／trapを確認した範囲はこの固定2 fixtureだけで、原19本への一般保証や性能認定ではない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/fuel-dag-typed-owner-v3-guest10-v1/snapshot.json)は完全依存archiveではない。次はscalar候補による原19本compile／extract38と3世代自己再ビルド6を別の有限44呼出で検証し、quiet C比較へ進む。
## Scalar DAG：元19本のコンパイルと3世代固定点

Guest10の独立監査を受理した後、元19本のcompile／extract38呼出と自己再ビルド6呼出を実行した。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-original19-selfbuild44-v1/reviews/actual-independent/report.json)は44呼出の終了、全raw・引数・環境・17 counters、元のbody・symbol・profile、全export・payload、生成compilerの使用を確認した。G0・G1・G2・G3のnativeはすべて969,864 B、SHA-256 `d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a`で一致した。監査readerのfield名取り違えによる初回HOLDも保存し、nativeを再実行せず修正した。

[全19本の静的比較](evidence/coscientist-masked32-clone-20261008/fuel-dag-original19-selfbuild44-v1/go/original19-static-baseline-comparison.json)でSR基準とnative bytesが異なるのはnettle-sha256だけだった。これは速度改善の証拠ではない。新candidateで全19本・95 profiles・285呼出の返り値／fuel／terminal arenaを確認し、同じquiet hostのC測定へ進む。選択snapshotは完全な依存archiveではない。

## Compute addressの検証と実行速度の測定

ユーザーのComputeCID／ResultCID案は[解析再利用契約](coscientist-compute-canonical-next-20261008.md)に統合する。要求には解析器・対象依存・入力状態・規則・ABI・effect／trap・予算を含め、Resultには問い合わせが所有する答えと順序付き寄与を保存する。現在の集計への再適用、更新前後・観測可能な消費はTransitionReceiptで別に検証する。完全なread／output契約を閉じるまで、Result一致による下流停止やC2の解析省略は有効にしない。

coscientistの判定を二つに分ける。解析再利用はcacheなし／shadow／replayの意味・失効・valid-last公開と、封印・hash・lookup・replayを含むコンパイル時間で判定する。生成コード最適化は元19本の意味・資源契約・selfhost固定点と、同一ホストでのC比較で判定する。既存memo hitを新cacheの利益へ加算せず、CIDの一致を意味保存証明やEmbench高速化として扱わない。

[zebulunの読み取り専用調査](evidence/coscientist-masked32-clone-20261008/zebulun-host-survey-v1/survey/report.json)はarm64／Mac16,10、macOS26.2／SDK26.2／Apple clang17を確認した。Tailscale SSHのDNS失敗と、同じIPへの通常SSHの成功を両方保存した。8秒のCPU調査はstable quiet hostの資格ではなく、性能結果は未取得である。
## 同一ホストのC19本・新consumer19本：52呼出の独立確認

zebulunの専用領域で、環境照会7・元のC19本・新consumer19本・環境照会7の計52呼出を実施した。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-build52-v2/reviews/actual-independent/report.json)は全引数・順序・環境・timeout・104 raw streams・正常終了とreap、前後のclang／SDK／OS identity、全C recipeとcb3f consumer recipeを確認した。19 headerはOFF／LCの全payload・offset・symbol・featureと、そのホストで新しく作ったC imageの全bytesに一致し、38成果物はthin ARM64である。

封印済み121,263,001 Bのパッケージは全3,493 originの415,361,908 Bを保持する。64MiBを超える歴史的clang資料だけをlossless chunkへ分割し、順序・全origin SHAを検証した。runtime operandはchunkを受理しない。独立assembly／transfer監査、3転送呼出、1launch、読み取り専用1回収も保存した。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-build52-v2/snapshot.json)は完全な依存archiveではなく、全workspaceパッケージの正確な参照を保持する。

これは同一ホストのビルドidentityと全imageの対応の証拠である。SDK tree全体のhash、fresh consumerの全19本・285呼出、quiet条件、実時間比較は別の段階であり、この52件から性能を主張しない。


## scalar DAG元19本の機能285呼出：V1 FAIL1保存とV2受理

初回V1は最初のOFF aha-mont64 n0でloaderのsandbox初期化が`Operation not permitted`となり、exit125で停止した。[独立FAIL1監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-original19-functional285-v2/preserved/v1-reviews/failure-independent/report.json)と元のSOURCE・GO・raw・terminalを保存した。fuelは16,777,216のまま、4 arenaの使用量は0で、body返り値、candidate ON、C、完了triplesの証拠は0である。rootの外側launcher権限の誤りを記録し、この失敗を成功基準へ読み替えない。

外側launcherを`functions.exec_command`の`require_escalated`で実行する条件だけを加えたfresh V2を別に事前登録・SOURCEレビュー・GO承認し、285呼出が正常に閉じた。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/fuel-dag-original19-functional285-v2/reviews/actual-independent/report.json)は元19本×5 profiles＝95 triplesのOFF／scalar ON／historical C、全285 argv・環境・raw SHA・exit0・終了状態、全source・export・payload・offsetとwhole C consumer anchorを照合した。native190呼出ではBoolean結果、16M初期fuelと残fuel、4 terminal arenaのcapacity／usedがOFF／ONで完全一致し、C95呼出のBoolean結果も一致した。C arenaはunavailable-C／null、terminal usedはpeakではない。depthconvの最終profile2000も保持した。

[受理receipt](evidence/coscientist-masked32-clone-20261008/fuel-dag-original19-functional285-v2/go/functional285-acceptance.json)はこの有限機能範囲を受理する。retained candidateは0、V1失敗1＋V2新規285＝累計286呼出である。この285は成功returnだけを受け入れる試験で、新しいbudget境界trapの証拠ではない。固定fixtureのGuest10 CPU trap確認とは区別する。timing、C2、register canary、official scoreとfull selfhost目標達成はfalseのまま。[選択snapshot](evidence/coscientist-masked32-clone-20261008/fuel-dag-original19-functional285-v2/snapshot.json)は依存pinと選択rawを保存するが、完全依存の実バイトarchiveではない。


## fresh consumer285初回：入力証跡の配置で実行前停止

新consumerの元19本・計95 profiles×3 armsを実行するSOURCEをレビューし、一度だけSSHで起動したが、最初の入力閉包検査が停止した。build52の読み取り専用collectorがstreamに生成した`collection-receipt.json`を、リモートbuild領域に存在する入力として扱っていたためである。SSH自体はexit0でもstdoutは空、stderrは2,059 Bのtracebackで完了sealがないため、成功とはしない。元SOURCE・GO・失敗rawを保存した。

[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-functional285-v1-failure/reviews/failure-independent/report.json)は、読み取り専用collection20 filesと`functional285`領域の不在、native／compiler／guest呼出0を確認した。旧領域の再試行は行わない。次のfresh SOURCEでは、同じ証跡bytesをsourceとして転送し、新領域での配置と役割を封じる。元19本のbody・profile・ABI・fuel・arena比較条件は維持する。内容hash一致だけではファイルの存在・入力解釈・計算の成功は保証されない具体例として、ComputeCID要求に配置役割とreader契約を含める設計へ反映する。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-functional285-v1-failure/snapshot.json)は完全な依存実バイトarchiveではない。機能285とquiet timingは未認定である。


## fresh consumer285修正版：同一ホスト全19本の機能受理

証跡31372Bを同じbytesのままfresh V2 SOURCEとして転送する修正を登録し、rootと独立レビュー後に一度だけ起動した。元の3896 local参照、3592 installed package member、228 actual build参照を保持し、変えたremote参照は証跡の配置1件だけである。本文・95 profiles・判定処理・ABI・16M fuel・4 arena・timeout・reap条件は変えない。

新しい同一zebulunホストのconsumerとCを使い、全285呼出が終了した。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-functional285-v2/reviews/actual-independent/report.json)は全285 argv／環境／正常終了、570 raw streams、strict14-field JSON、95 OFF／LCの結果・fuel・4 terminal arenaの完全一致、CのBoolean結果・課金なし・unavailable arena、全19本の152 runtime資料、SOURCE・2GO・完了sealと601 collection memberを照合した。旧failed launch1／native0は保存し、累計native/C285・launch2と区別する。

[root受理receipt](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-functional285-v2/go-and-actual-collection/functional285-acceptance.json)と19 nmaxの意味baselineを次のタイミングSOURCEに渡した。これは成功returnの機能範囲であり、新しいtrap境界・register canary・quiet条件・性能・official scoreの認定ではない。C2はOFF。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-fresh-functional285-v2/snapshot.json)は完全な依存実バイトarchiveではない。次の性能測定は全19本・同一ホスト・30組のpaired sampleと実測quiet条件で判定する。


## LC quiet timing V1：C校正で停止、性能未認定

2件の独立SOURCEレビューとroot GOで同一hostの元19本3arm計測を1回起動した。[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v1-failure/reviews/actual-failure/failure-report.json)はread-only collection88 members、14 children（runner5／load9）全終了、OFF／LC校正4成功、最初のC校正のSIGXFSZ・stdout／stderr空を確認した。測定paired tripleは0、statisticsなし、性能未認定である。旧namespaceは再試行しない。

[ソースに基づく診断](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v1-failure/diagnosis/report.json)では、変更していないC比較runnerが計測前に17,432 Bの埋込みlibraryを一時ファイルへ書く一方、ledgerが全regular fileへ16 KiB上限を与えていた。これは有力な停止原因仮説であり、実際の失敗syscallは未追跡。次のSOURCEではstdout／stderrのbounded pipeとregular-file上限を分け、元19本・ABI・fuel・arena・生成成果物・quiet条件・統計を維持する。ComputeCID設計へ[readerと資源契約の分離](coscientist-compute-canonical-next-20261008.md)を反映した。[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v1-failure/snapshot.json)は全依存の実バイトarchiveではない。C2 OFF、公式スコア／CID実行時効果／C以上の性能は未認定のままである。


## LC quiet timing V2：11本のstable30、C超えなし

streamとregular-fileの上限を分けた修正版は1 launchで正常終了した。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v2-partial/reviews/actual/report.json)は36,452 archive members、runner3,638／load7,276の10,914子プロセス全終了、strict14-field telemetry・意味・fuel・4 arena一致とclosed pipeを確認した。V1の14終了も保持し累計10,928である。元19本のうち11本はquietな30 paired triplesに達し、8本は有限上限内で部分終了した。全19本のGM・公式スコア・C以上の性能は認定しない。partial summaryでfixed19 bootstrapを実行していないことは[監査scope補足](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v2-partial/reviews/actual/scope-supplement.json)に明記した。

[別の独立COMPLETE30診断](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v2-partial/diagnostic/report.json)は11本それぞれのmean・sample SD・paired20K bootstrapを再計算した。全armのCVは0.1未満だが、11本すべてのC/candidateの95%上限は1未満で、individual C-or-betterは0本だった。下表はcandidate/Cの実行時間比で、1より大きいと候補が遅い。11本だけの集約はしない。

| Workload | Candidate/C time | Candidate code changed |
|---|---:|---|
| crc32 | 1.87120x | no |
| edn | 14.61239x | no |
| huffbench | 7.13431x | no |
| md5sum | 4.17285x | yes |
| nsichneu | 8.51466x | no |
| sglib-combined | 6.02778x | no |
| slre | 7.02217x | no |
| statemate | 15.98152x | no |
| tarfind | 13.91825x | no |
| wikisort | 11.65575x | no |
| xgboost | 6.27562x | no |

変更が入ったMD5はbaseline/candidate mean1.01599、paired95%[0.99545,1.03570]で、事前登録の5%・SD・CI採用条件を満たさない。SHA256は校正部分終了なので、速度を認定しない。LCの性能採用を見送り、生成コードの意味保存・固定点の証拠とは分けて保持する。

partialはaha29/90、AES26/90、picojpeg29/90、qrduino22/90のquiet triple上限、depthconv／matmult-int／SHA256／udの校正上限である。保存rawの拒否集計ではbackground-idle条件が主で、picojpegにはload条件の拒否もある。1回のread-only進捗probeは保存し、observed host activityへ含まれるが、影響0の証明や原因帰属はしない。再実行はせず、次のhost／待機・有限上限設計は別の事前登録とする。

[選択snapshot](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v2-partial/snapshot.json)は全36,452 collected membersを4,516,385 Bのraw archiveへ封じるが、449 MBの元依存bank全体を含むarchiveではない。ComputeCIDのruntime効果、C2省略、product採用、full own-source100%は未認定。次の生成規則は、ハードウェアfeatureに依存しない、bounded callerと完全CFG証明を持つsplit immutable table readerの直接読みに絞る。


## 次の規則：split immutable table readerのcall edgeを縮約

[TC V2 SOURCE](evidence/coscientist-masked32-clone-20261008/table-decision-collapse-v2-source/source/proposal.md)をnative Kotobaでコピーへ実装し、[root](evidence/coscientist-masked32-clone-20261008/table-decision-collapse-v2-source/reviews/root/report.json)と[独立SOURCEレビュー](evidence/coscientist-masked32-clone-20261008/table-decision-collapse-v2-source/reviews/independent/report.json)を通した。規則は名前やCRC polynomialを参照せず、immediate AND-maskによる32／64／128／256の入力範囲、完全なreader CFG、defined-before-read、各pathの1 immutable read・1 entry fuel、連続16要素literalとlayout42の順序・8-byte alignmentを条件にする。既存poolを使い、新しいliteral／arena領域を追加しない。generic／public／FADDR readerは残す。

V1のprefix-save欠落・context/cache publication・数値overflow／bounds／tail lifetimeのSOURCE指摘を保存し、V2へ直した。V2は元のgn-save、gn-vclear、context解析、gn-takeを保ち、RET／RES2 successorと未知shapeをgenericへ戻す。38-cell snapshot、64-word／4096-word／256-siteの既存予算でrollbackする。新しいアルゴリズムの一回のauthoringで、既存AST refactor ruleに対応規則はない。

historical同一sourceの256 paths、13 reader mutations、6 caller mutations、synthetic32／64／128／256 readerの480 pathsとprefix／fuel modelは有限source-data証拠で、実際のKotoba/native fault validationではない。copied candidate133,738 B・SHA3d7c169818cdf0fabc151da98017d3b28bbe38fc3407d9b42921b646520c2abaはまだコンパイルしていない。current typed producer binding、実命令・relocation・register／fuel／trap／arenaの検証、元19本と固定点・required gates、fresh C比較が次の条件。callee frameを省くため、任意のOS stack-limit同等性は未証明である。

[LC性能採用のroot判断](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v2-decision/root/performance-decision.json)はMD5の未達とSHA256の未認定を保持する。TC SOURCEレビューは実行GO・速度改善・production採用の証拠ではない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/table-decision-collapse-v2-source/snapshot.json)は完全な依存archiveではない。


## 次の測定hostのread-only確認

[有限read-only survey](evidence/coscientist-masked32-clone-20261008/quiet-host-recon-v1/recon/report.json)では3回のSSHが閉じ、ZebulunはApple M4・10 logical cores、10秒のidle93.11%、load1.88→1.75でsurvey条件を満たした。AsherはSSH timeoutで未確認。単一Tailscale inventoryは非JSONでwrapperが停止し、最初の元診断を永続保存し損ねたことを記録した。他の端末は未確認である。surveyは新しいtiming資格ではない。次のcampaignは元のquiet条件を緩めず、有限の待機・readiness条件を別に事前登録する。今回bench／compiler／転送／remote変更は0。


## current typed binding8：実行前資源設定で停止

次の有限8-call gateは、native scalar d3を明示したstage0として、現在のMANIFEST／41(4ed9)から通常版とread-only observerを作り、その後に元CRCをcompile／extractする計画である。測定済みLC5fとcurrent41の系統を同じとはしない。全FN／SIR／node／symbol／token／call／38-cell context／literal／label／fixup／exportの順序付きinventoryを検査する。V1はreader IDが最後のexport IDへ上書きされるSOURCE不具合をrootと独立担当が確認し、未実行のまま保存した。V2で所有者を分離し、返す証拠のowner／range／siteも照合した。

SOURCEと1,769入力371,271,887 Bの照合、rootと独立レビュー後にV2を一度実行したが、最初のPopenが`preexec_fn`例外で停止した。[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/table-current-bind8-v2-preexec-failure/reviews/actual-failure/report.json)は試行1、stdout／stderr0 B、実compiler0・native成果物0、retryなしを確認した。どのFSIZE／CPU／AS setterが失敗したかは不明。返されたprocess objectはなく、内部fork不在やledgerのallClosedをnative wait証明とは扱わない。outer exit1はrootのtool観測で、保存outer raw receiptはない。current typed binding・byte identity・最適化実行は未認定のまま。

[選択snapshot](evidence/coscientist-masked32-clone-20261008/table-current-bind8-v2-preexec-failure/snapshot.json)はSOURCE・失敗・レビューを保存し、371 MBの全依存実バイトbankは含まない。次はloaderを起動しない1子プロセスの診断で、各resource setterのbefore／desired／outcome／readbackを記録する。有限の継承hard／softを引き上げず、ASを黙って除去しない。これは別の事前登録で、旧V2は再試行しない。

## Tailscale一覧と代替hostの有限survey

新しい一覧取得はstatus子プロセスexit0で44 entriesを保存したが、outer writerのduplicate keywordでexit1となった。[独立保存監査](evidence/coscientist-masked32-clone-20261008/inventory-alternative-host-surveys-v2/selected/inventory/reviews/independent/report.json)はprivate rawからhost／OS／online／IPの4 fieldsだけを再構成した。保存された一覧だけを受理し、outer completionは受理しない。RawJSONは公開しない。Asherは一覧でもofflineだった。

既存identityとonline Mac一覧を根拠に、Benjamin／Levi／Issacharへ各1回のread-only surveyを行った。[独立監査](evidence/coscientist-masked32-clone-20261008/inventory-alternative-host-surveys-v2/selected/surveys/reviews/independent/report.json)は3 SSH closed0（旧3＋新3＝累計6）、10秒のticksからidleとquiet条件を再計算した。全3台M4／10 cores／arm64／macOS26.2(25C56)。Levi94.46254%・load1.79199→1.97119、Issachar93.00257%・2.36035→3.01855はsurvey条件を満たし、Benjamin89.74765%は満たさない。bench／compiler／転送／remote設定変更は0。短いsnapshotの適格性で、持続quiet・SDK／toolchain・タイミング資格ではない。process countsはschema照合のみで、元ps rawの独立再構成ではない。次のC比較host候補はLeviとし、実際のcampaignでは新しいCビルドと各sampleのquiet条件が必要である。


## 1-child資源診断：AS4GiBの設定拒否を記録

[独立保存監査](evidence/coscientist-masked32-clone-20261008/table-resource-diagnostic1-as-failure/reviews/actual-independent/report.json)は、loaderを呼ばない1 Python診断childのargv／環境、10 SOURCE／9 input pins、6保存outputs、1,065 Bのjournal／stdout完全一致・stderr0を検査した。通常のchild bodyでFSIZE64MiB、CPU1800の設定とreadbackが一致し、AS4GiBは`ValueError('current limit exceeds maximum limit')`で失敗しreadbackはinfinityのままだった。childはexit78でreap済み、first failureで終了しcompletionなし、retryなし。外側exit78はrootのtool観測に限る。

これは今回の診断のAS設定拒否であり、旧native V2の失敗setterを確定する証拠でも、すべてのmacOS／AS値で未対応という証拠でもない。次のnative adapterは平台の有限メモリ契約を明示して別SOURCE／GOで扱う。ASを黙って除去せず、resident memoryやarena契約との意味差を混ぜない。現時点のcompiler／native execution0、TC生成・current typed binding・C以上の性能は未認定のままである。[選択snapshot](evidence/coscientist-masked32-clone-20261008/table-resource-diagnostic1-as-failure/snapshot.json)は完全なPython／OS／共有library閉包ではない。
## SOURCEの性能仮説とプロセス群の資源契約

[静的census](evidence/coscientist-masked32-clone-20261008/dense-dispatch-frontier-v1/source/proposal.md)では、元のstatemate／nsichneuに認識対象のdense dispatch chainはなかった。現在のscalarDAGはboolも許可済みで、主な境界はvector引数・分岐・fuel・runtime操作だった。歴史的typed observerと測定済みLC、現在の41-a64genを別のproducerとして記録した。状態更新やfuelを飛ばす置換は採用せず、既存tail loweringの適用を現在のproducerで観測してから、順序を保持した継続領域の融合を検討する。これはSOURCE仮説で、性能改善を測定した結果ではない。

[owned-group memory adapterと旧fixtureのSOURCE記録](evidence/coscientist-masked32-clone-20261008/owned-group-memory-source-and-holds-v1/snapshot.json)を保存した。メトリックは所有する最大2プロセスのri_phys_footprintの合計、4GiBを超えたsampleで拒否する別契約である。AS・RSS・hard peakの上限とは同等でない。V1〜V3で見つかった終了処理の競合を保存し、V4はwaitに入る前にシグナル送信権を永久に取り下げる。割り込みで所有権が曖昧なら、成功や終了済みとは推定しない。

V4の固定fixtureを1回実行したが、2つのleader-only sample後にhelper argvの完全一致検査で停止した。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/owned-group-memory-v4-helper-path-failure/reviews/actual/report.json)は各9,257,392 Bのsample、固定登録したCellar pathとsys.executableが返した互換リンクpathの差、leaderの-9終了とreapを確認した。helperの開始は記録したが別のreap証拠はなく、2プロセス群の正常終了も8 sampleの資格も主張しない。failure terminalのnormalClosureProof文字列は期待する形のテンプレートであり、実証として採用しない。再実行は0、native呼出0である。

固定canonical interpreterを明示し、起動前に実行ファイルとfixture sourceを検査するfresh V5を2レビュー後に1回実行した。[独立raw監査](evidence/coscientist-masked32-clone-20261008/owned-group-memory-v5-qualified-fixture/reviews/actual/report.json)は全8 sample、member数1・1・2・2・2・2・1・1、PIDごとのbirth／UUID、footprint合計を照合した。合計は10,355,144 Bを2回、20,693,904 Bを4回、10,420,680 Bを2回。helper wait0のhandshake・stable one-again 2 sample・leader wait0、signalなし・wait uncertaintyなしを確認した。旧V4の失敗は保存したままである。

この成功は固定2子プロセスの有限adapter試験の資格だけで、hard memory peak・native8・current compiler binding・性能の資格ではない。次のnative8要求は、sampled footprint契約とCPU soft1800／hard1801、file／wall／arenaの契約を別に登録し、レビューしてから実行する。AS上限を黙って省く同一要求として扱わない。

## 新しいnative8要求の環境検査と、継続領域の観測ソース

V5の独立証拠を封じた新しいportable native8要求を2レビュー後に1回実行したが、最初のwrapperがPython内部環境と登録済み17項目の完全一致検査でexit1となった。[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/table-current-bind8-portable-v3-env-failure/reviews/actual/report.json)はwrapper reap1、2 memory sample、空のsetter journal、exec-readyとnative成果物がないことを確認した。親が渡した17項目は登録値と一致していた。失敗したwrapperの実際の追加keyは記録していないので、後から断定しない。native execは観測されておらず、syscall traceによる非実行証明とは区別する。

別の固定Python起動1回では、同じ17項目に対して__CF_USER_TEXT_ENCODINGだけが追加され、元の項目の欠落・変更はなかった。[診断sourceと結果](evidence/coscientist-masked32-clone-20261008/table-current-bind8-portable-v3-env-failure/separate-env-diagnostic/report.json)はkey名だけを記録し、環境値は出力しない。[Appleの公開CF実装](https://github.com/apple-oss-distributions/CF/blob/main/CFRuntime.c)にも初期化時のencoding関数によるsetenvの可能性が記されているが、インストール済みframeworkの実行traceではない。次の別要求は、渡した環境・Python観測環境・native execへ明示して渡す環境を分け、元の17値と未知key拒否を保持する。旧試験の再実行は0である。

並行して[現在producerの継続・tail・descriptor-cache観測用Kotoba SOURCE](evidence/coscientist-masked32-clone-20261008/continuation-current-producer-observer-source-v1/source/DESIGN.md)を凍結した。元のpredicateを再評価せず、実際に選んだcall arm、frame／fuel／cache状態とcode／fixup範囲を記録する。baseline unity sourceはnative8の現ソースと完全一致するが、native baselineの再利用資格はまだない。runner・nativeコンパイル・2本の生成物一致検証は未実施で、call除去やdescriptor保持の採用根拠・性能結果とはしない。

## 現ソースでの8呼出・CRC型付き閉包の実確認

fresh portable V4は渡した17項目を厳密に検査し、Python内の追加keyを__CF_USER_TEXT_ENCODINGだけに限定し、native execには元の17項目を明示して渡す。2レビュー後の1回の実行で固定8呼出すべてが正常終了した。[独立raw監査](evidence/coscientist-masked32-clone-20261008/table-current-bind8-portable-v4-actual/reviews/actual/report.json)は全23 SOURCE・1,835入力、8起動引数、環境と6-row journal、FSIZE64MiB／CPU1800・1801、17 arena counters、141 memory witnessを照合した。親のreap0は8件、guest子の終了は封じたloader supervisionに依存する。memory sampleは最大2 memberでbirthと合計を照合し、hard peakは主張しない。

現baseline compilerは858,392 B／SHA256 `761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93`、readonly observerは876,648 B／`8f5fdf02193733ec84fd14d7de8b55b0f5b556bc85be11a407d76a0aca230c2d`。通常版と観測版で元CRC32のKSEED 3,724 B・native 3,640 B・4 exportとbench offset 1,224が完全一致した。native SHAは`8c5ab9f7a78b4df15a735d655bdcbee8b4b3bef6613cdcf99e639b153332b7d4`である。

現在の型付きrawからreader FN1／SIR1..174、caller FN3・eligible SIR220、256 finite paths・2,048 Bのtable poolを再構成し、48 resolved branch fixupも独立照合した。歴史的v8だけを適用根拠にせず、現在の入力閉包とのbindingが得られた。typed gateは8番目のextractより前にsource上で強制されるが、外部event traceによる工程観測とは区別する。

これはreadonly bindingと成果物一致の資格で、TC emitterや生成workloadの実行、compiler arena同等性、3世代固定点、C以上の性能の資格ではない。次はこの現baselineと証拠を封じてTC候補をビルドし、実guestの値・prefix・fuel・trap・arenaを通常経路と比較する別試験へ進む。継続領域observerもsourceが同じ現baselineを使えるが、runnerと別登録の検証は引き続き必要である。
## TC候補の実生成7呼出と、レジスタ推測を固定した検証器の失敗

current7618でTC候補と観測用compilerをcompile／extractし、元CRC32を双方でコンパイルした。8呼出として登録した試験は、7呼出がすべてexit0でreapされた後、命令検証器のassertionで停止した。8回目のextractは実行しておらず、旧namespaceを再試行していない。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/table-emitted7-register-gate-failure-v1/reviews/saved-failure-independent/report.json)は全18 SOURCE・1,911入力、GOと2レビュー、140 memory witness、環境・資源journal、17 counters、生成物hashを照合した。これは失敗した試験の記録であり、build8成功ではない。

候補compilerは866,384 B／`5cda246fec1d653b5ff044a56491069874f7a0b58da87785887c369573ccec8c`、観測用は878,888 B／`f5bce9fe13a9a11a602be4d2272a053c5ce9e6eb96849ebd97b2d10eb4b75ecc`。元CRCの両KSEEDは3,764 B／`c7b2b04eed1c0e5b07b4ac9d217c5f27c96b81b86b9003dc8767ea90312a68d3`で全バイト一致した。通常側のnative payloadは3,680 B／`5187d8338730957bf4611f294117c811099af65c9d1117492dd57430e8fa8999`。いずれも固定点や実行時間の資格ではない。

保存rawではsite220に13命令のTCEMITがあり、入力captureは`MOV X0,X24`、結果は`MOV X9,X0`だった。検証器のx25固定は、slot7に保存した値25を実レジスタ番号と取り違えたものだった。`gn-sreg`は保存値から1を引くため、正しい番号は24である。[sourceと命令の復号](evidence/coscientist-masked32-clone-20261008/table-emitted7-register-gate-failure-v1/reviews/saved-failure-independent/DECODE.md)。SOURCEレビュー時のsynthetic positiveも同じ推測を用いており、この誤りを検出できなかった。

独立担当が検証器をメモリ内でその1命令だけ訂正すると、残るassertionはすべて通った。OFFとのphaseを対応させた全76 TCG値、元reader本体、型付きSIR、literalとfixupも一致した。担当の途中のTCG差分仮説はpreとpostを取り違えた比較だったため撤回し、rawと報告に保存した。凍結検証器・旧試験の失敗は書き換えず、正式な保存raw修正版のレビューと、未実行のextractを行う別の有限試験を次に登録する。guestの値・fuel・trap・arena、元19本、3世代固定点、quiet hostでのC比較は未実施・未資格である。TCやCIDによるC以上の性能は主張しない。

## 保存raw修正版の正式なoffline検証

レジスタをTCGのslot値と`gn-sreg`から復号する修正版を別ソースとして凍結し、2 SOURCEレビュー後に保存データだけの検証を1回実行した。[独立保存監査](evidence/coscientist-masked32-clone-20261008/table-emitted7-saved-repair-v1/reviews/actual-independent/report.json)は全7 SOURCE／1,976入力、GO・レビュー・新reportを照合し、完全なraw検証を別に再構成した。13命令・407 code words、sourceRegister24／destination9、literal fixup `[49,252,5,1,0]`、全76 descriptor値、移動したliteral即値だけ正規化したgeneric readerの一致を確認した。15種類の保存モデル負例も拒否した。追加native／setter／process API呼出は0である。

これは保存済みの実生成についての正式な修正版検証であり、旧build8の成功への書換えではない。旧7呼出のfailure、未実行の観測側extract、guest・固定点・性能の未資格を保持する。新reportは通常側nativeが両KSEED payloadと一致することを確認するが、未実行のextractを代行したとは扱わない。残るextractは別SOURCE・別出力rootの1呼出として登録する。元CRCのprefix／benchで置換siteを通るguest比較、fuel／trap／arena／fallback、元19本・3世代固定点・fresh quiet C比較が次の条件である。

## 残るextractの別試験：生成物の完全一致

残る観測側extractだけをfresh V2の1呼出として実行し、正常終了した。[独立保存raw監査](evidence/coscientist-masked32-clone-20261008/table-remaining-extract1-v2-actual/reviews/actual-independent/report.json)は2,004入力・10 SOURCE、1 reap0、2 memory witness、環境・資源journal・17 countersと4 exportを確認した。観測側nativeは3,680 B／`5187d8338730957bf4611f294117c811099af65c9d1117492dd57430e8fa8999`で、通常側と両saved KSEED payloadに全バイト一致した。bench offsetは1,264である。

V1は記述に旧8-group資源集計が残るため未実行のHOLDとして保存した。V2 rootレビューの文字列比較ミスも診断として保存し、凍結SOURCEを変更せずレビュー側を訂正した。旧7呼出のnamespaceはFAILのまま、再実行0、旧completionと旧観測側nativeは不在を維持する。[選択snapshot](evidence/coscientist-masked32-clone-20261008/table-remaining-extract1-v2-actual/snapshot.json)は392 MBの全依存archiveではない。

この試験は抽出とバイト一致だけの資格である。元CRCのprefix 1・2・1,024とbench 1を各OFF／ONで実行し、値・fuel・全arenaを比較する次の8-call SOURCEを準備する。trap・fuel境界、fallback、原19本、selfhost固定点、quiet hostでのC性能比較、ComputeCIDによる解析省略は未資格である。C2はOFFを維持する。

## 元CRC guest8：2回目の観測処理で停止

8-call SOURCEは全11ファイル・2,032入力を2担当が照合した後、別GOで一度実行した。[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/table-original-guest8-sampler-failure-v1/reviews/actual-failure-independent/report.json)はprefix-crc(1)のOFF／ONのみ2呼出、各parent reap0、6-row環境・資源journal、全17 arena countersが0、計3 accepted memory sampleを確認した。OFFは期待値3,523,407,757、initial fuel1,000,000／remaining999,996だった。

ONはsamplerの`ProcessLookupError`とcleanupの`killgroup:PermissionError`で失敗した。捕捉したstdoutは0 Bで、stderrは完全なarena行だった。adapterのowner／member照合は複数箇所で`os.getpgid`を呼ぶが、保存exceptionには内側tracebackがなく、失敗した呼出・PID・原因は特定できない。cleanupはpipeを完全にdrainせず閉じるため、空の保存stdoutをguestが出力しなかった証拠と扱わない。

残る6呼出とcompletionは不在、accepted pairは0で、凍結campaignはFAILのまま再実行0である。[選択snapshot](evidence/coscientist-masked32-clone-20261008/table-original-guest8-sampler-failure-v1/snapshot.json)は全393 MB依存archiveではない。tool session3728のouter exit1はrootのtool観測に限る。次は有限pipe捕捉と所有権を維持したsamplerの試験を別SOURCEで設計する。今回の失敗から意味の不一致や性能改善を推定せず、guest parity・full19・固定点・C比較は未資格を保持する。

## CRC置換の有限意味モデルと、捕捉処理の12対照

[保存された実13命令の有限モデル](evidence/coscientist-masked32-clone-20261008/table-emitted13-finite-model-v1/model/report.json)を独立に作り、rootも再計算した。実TCEMIT・FIX・typed SIR・literal bytesを照合し、入力256値とfuel 0／1／2の768ケースで整数結果・fuel更新を確認した。10命令変異と3範囲外対照は拒否した。mapped context、readonly literal、入力範囲などの前提を明示している。これは保存命令の有限モデルであり、hardware実行、元readerの全scratch／stack／trap状態の同等性や一般的な形式証明ではない。レビューの初回dictionary比較失敗と訂正も保存した。

pipe捕捉V1はsetup失敗時のFD所有権が不十分なため、未実行HOLDとして保存した。新V2は所有権grant／denyを明示し、writer停止後にだけhashを公開する。12対照を一度実行し、[独立監査](evidence/coscientist-masked32-clone-20261008/capture-fixture12-v2-actual/reviews/actual-independent/report.json)は8捕捉状態と4setup失敗、16 rawファイルを照合した。非対称EOF、上限超過、short write、fsync失敗、join timeout、曖昧なthread startを含む。停止後にrawが完全になっても、最初の失敗を消さない。native／Popen／group操作はfixture内部で0で、元CRC guest試験は再実行していない。

[選択package監査](evidence/coscientist-masked32-clone-20261008/capture-fixture12-v2-actual/reviews/package-independent/report.json)は、16 rawの合計9,437,262 Bを9,654 Bのtgzへ保存したことと、展開内容の完全一致を確認した。SOURCE、GO、completion、レビューも保存している。これは全依存archiveではない。chronologyとFD closureは凍結fixtureのassertionであり、独立syscall traceではない。通常ファイルのwrite／fsyncが任意にblockしないことや、native samplerのmemory admissionを資格化してはいない。

## vector状態の次の仮説：コピー除去から実read／store観測へ

[元statemate／nsichneuのSOURCE調査](evidence/coscientist-masked32-clone-20261008/vector-state-source-frontier-v1/source/report.md)は、両者がaffine mutable vector-assoc!を使い、状態vectorを反復外で一度確保することを確認した。persistent vector-assocは0で、ループ内のimmutableコピー除去という仮説を退けた。syntax上のcall／read数を生成後の命令数やCとの差の原因と扱わない。

次の候補は、実allocationとchecked storeを保持したまま、同じhandle・定数indexの直線区間で値をforwardできるかである。alias、write、call、join、寿命、fuel／trapの条件が未確認なら通常経路を維持する。実typed eligibilityは未確定であり、SOURCE上の数から推定しない。元19本、3世代固定点、同一quiet hostのC比較は引き続き最終条件である。

## 観測controllerの成功判定をSOURCE負例で修正

独立レビューはcontroller V2の正常分岐がPID／birthとloader証拠のbindingを参照せず、3負例を成功として返すことを見つけた。V2を変更せず、新V3で全admissionにbindingを必須化した。[独立V3レビュー](evidence/coscientist-masked32-clone-20261008/capture-controller-v3-source-hold/reviews/independent/report.json)は元9対照・正常1対照・追加3負例を注入して再計算し、3件すべての拒否を確認した。これはsequential SOURCE検査で、実kernel／thread／native操作は0である。

型付きESRCHのtermination-gapを扱う観測policyは別の版とし、missing sampleを0にも旧strict policyのPASSにも変換しない。旧guest8 failureはそのまま保存する。耐久sample journal、native callback、完全FD台帳、Popen transferとwatchdogの統合fixtureは未資格で、V3もruntime HOLD／GOなしを維持する。

## CRCの全table到達：元1024は255項目まで

[独立SOURCE評価](evidence/coscientist-masked32-clone-20261008/crc-source-table-reach-v1/reviews/independent/report.json)は、元の1024バイトCRCが256項目中255項目を読み、index154だけを通らないことを確認した。prefix1080までは255、1081で初めて全256に到達し、CRCは4,018,572,661になる。通常nativeのpool1592と候補nativeのpool1632の全256 little-endian値も元SOURCEと一致する。index154を一ビット変える反例は1024の答えを変えず1081を変えるため、1024だけを全項目の実行検証と扱えない。

これは元SOURCEの分岐木とrecurrenceを評価した有限結果であり、候補の実compiled site到達やfuel／trap状態の検証ではない。元19本のbody／profileを変えず、追加OFF／ON prefix1081を別の到達試験として登録する。既存の元CRC8-call scopeも置き換えない。

## 実FileIO移譲と所有権の11ケース

[独立保存監査](evidence/coscientist-masked32-clone-20261008/capture-fileio-fixture11-v2-actual/reviews/actual-independent/report.json)は、V4と同じcapture／integration／controllerで11ケースを一度実行した結果を照合した。8件のFD ledgerは収支が一致し、最大9 controlled FD、6 rawファイルの合計7 B、停止前のhash不公開を確認した。実threadによるretire-before-wait、不確実なwait、callback例外時の同じlock内での退役も対象にした。process callbackは注入で、fixture内Popen／native／group APIは0。外部supervisorがdriver1件をclosed0でreapし、stdout／stderrは各0 Bだった。

最初のfixture SOURCEにはPython runtimeのsymlink aliasがあり、rootのregular-file pinで起動前HOLDになった。新V2は同じcanonical targetへの重複pinを整理し、全9 SOURCE／1,944入力をregular・nonsymlinkとして2担当が照合した。11ケースのPython本体は同一で、旧V1は未実行を維持する。最初のsupervisorも固定child bindingと不確実waitの扱いを修正し、各SOURCEとHOLDを保存した。

この結果は制御したFD／thread fixtureの資格であり、全scheduleの証明やsyscall trace、native sampler／Popen全体、hard peak・任意library内部FD数の保証ではない。V4 native driverには耐久sample journal、元の6-row資源証拠、17 counters、結果・fuel・rawのpair比較を配線し、追加SOURCEレビュー後にfresh8呼出へ進む。旧guest8の2-call failureを成功へ変更せず、再試行も0を維持する。

## fresh V4：元CRCの4組・8呼出が正常終了

2担当のSOURCEレビューと実FileIO fixtureを前提に、別driver・別出力領域のV4を一度実行し、8呼出すべてをrc0でreapした。OFF／ONの完全なstdout・stderr、構造化report、fuel、17 arena countersは各pairで一致し、全arena値は0だった。

| 対象 | OFF＝ONの答え | OFF＝ONのfuel消費 |
| --- | ---: | ---: |
| prefix 1 | 3,523,407,757 | 4 |
| prefix 2 | 3,468,463,104 | 6 |
| prefix 1024 | 1,703,161,001 | 2050 |
| bench 1 | 1 | 2052 |

有限memory sampleは19件で、この実行にはsampler failure／termination gapはなかった。[独立保存監査](evidence/coscientist-masked32-clone-20261008/crc-original-native8-v4-actual/reviews/actual-independent/report.json)は全20 SOURCE／2,135入力、8 argv／17 env、各6 setter行、両EOF、4 pairのraw・report・fuel・17 arena一致を確認した。これはhard peak、OS stack上限、全scheduleの証明ではない。旧guest8の2-call failureと残り6件の未実行はそのまま保持する。[選択snapshot](evidence/coscientist-masked32-clone-20261008/crc-original-native8-v4-actual/snapshot.json)は全依存archiveではない。

全256項目の実到達、専用fuel／trap境界、fallback／FADDR、cap rollback、原19本、候補の自己再ビルド固定点、quiet C性能比較は未資格。元1024だけで全tableを検証したとは扱わず、追加prefix1081は別試験とする。ComputeCID／ResultCID解析reuseの性能効果とも区別し、C2 OFFを維持する。

## prefix1081：出力は一致、sampler拒否で試験はFAIL

全256 indexを通るSOURCE期待値を別の2呼出へ登録し、一度実行した。[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/crc-prefix1081-v1-sampler-refusal/reviews/actual-failure-independent/report.json)は全18 SOURCE／2,141入力、2 argv／17 env、各6 setter行、5 memory samples、2 wait rc0を照合した。OFF／ONともCRC 4,018,572,661、fuel消費2164・残量997836、17 arena値0であり、完全なstdout235 Bとstderr291 Bのhashも一致した。全256への到達は元SOURCE／typed recurrenceと保存済みemissionからの推論であり、各indexの動的トレースではない。

ONは3回目のgroup操作で例外となり、同じlock内でgroup権限を退役し、sampler不確定としてREFUSEした。両EOF、停止後hash、正常reapは保存できたが、completionは存在せず、campaignはFAILのままである。再試行は0。元の8-call PASSと旧2-call failureの領域も変更していない。

今回のcontrollerは失敗contextとotherRefusalsを内部recordに作る一方、返却値へ含めていなかった。保存証拠からerrno・stage・PIDやpolicy refusalの種類を特定できず、終了raceやESRCHが原因だったとは言えない。次の版ではこの有限recordを保存し、admissionを緩めず、変更したcomponentを改めて検証する。[選択snapshot](evidence/coscientist-masked32-clone-20261008/crc-prefix1081-v1-sampler-refusal/snapshot.json)は全依存archiveではない。出力一致をmemory admissionのPASS、TC採用、固定点、原19本やC性能達成へ昇格しない。

## 失敗recordの保存：判定を変えず部品を再検証

新controllerは既存の判定を保ち、内部のmemoryAdmissionRecordを返却値へ追加する。AST比較はこの1 fieldだけの差分を確認した。2担当が型付き例外・policy拒否・wait不確定・正常終了など16個の純粋な注入対照を再計算し、failureとotherRefusalsの保持を照合した。実kernel・FD・thread操作はこの対照に含まれない。

新しい同一componentの実FileIO／thread11ケースを一度実行し、[独立保存監査](evidence/coscientist-masked32-clone-20261008/capture-fileio-fixture11-v3-record-actual/reviews/actual-independent/report.json)が全12 SOURCE／1,950入力、GO／レビュー／supervisor、11 receipts、8 FD台帳、最大9 controlled FD、6 raw計7 Bを確認した。supervisorはdriver1件をwait rc0でreapし、kill・wait不確定はなかった。停止前hashは未公開で、起動を拒否したcaptureを停止済みworkerとは扱わない。controllerは6a78a0ff、capture／integrationは旧版と同じ実バイトである。

[選択snapshot](evidence/coscientist-masked32-clone-20261008/capture-fileio-fixture11-v3-record-actual/snapshot.json)は全依存archiveではない。native sampler、元19本、固定点、C比較の資格ではなく、旧prefix1081 FAILも変更しない。44-call SOURCEは元19本のcompile／extractと同一TC全ソースからのG1／G2／G3を対象にする。最初のハーネスはCRC専用wrapperの入力schemaと、terminal保存前のCOMPLETE公開が独立レビューでHOLDになった。別V2で各呼出のproducer／全container／入力／GOを封じ、terminalと最終検査の後にだけ完了を公開するよう修正した。この部品監査の時点では44-callの実行は0だった。次節の実行には2担当のSOURCEレビューと別GOを用いた。

## TC44 V2：ahaの成果物は一致、strict samplingはFAIL

2担当のSOURCEレビューと新fixtureの独立監査後、別GOでV2を一度実行した。[独立保存失敗監査](evidence/coscientist-masked32-clone-20261008/tc-original19-v2-extract-termination-gap-failure/reviews/actual-failure-independent/report.json)は全17 SOURCE／2,563入力、最初の2 argv／17 env、封印済み入力・producer、6-row資源journal、17 arena counters、6 memory samples、2 wait rc0を確認した。aha-mont64の全container4,039 Bから得たpayload3,976 Bはnative全体と一致し、bench3456／observe3644／bounds-probe3824はすべてarity1だった。これはこの保存成果物の条件付きidentity資格であり、guestの実行結果ではない。

extractの4回目のgroup操作は、既存のleader-getpgidに対してPID52693／queryOrdinal29／errno3の型付き失敗を記録した。以前の3 sampleでleader birthは確認済みで、両EOF・完全hash・正常wait・資源証拠は揃っていた。controllerは既存policy v2のSEMANTIC_DIAGNOSTIC_TERMINATION_GAPを返したが、V2のstrict sampling条件は拒否した。欠けたfootprintはnullであり、0にもPASSにも置き換えない。今回のAPI失敗箇所は特定できたが、kernelのタイミング原因や欠測値は不明である。

V2はFAIL、report／images／generationsは存在せず、残り42件は未実行。再試行は0。[選択snapshot](evidence/coscientist-masked32-clone-20261008/tc-original19-v2-extract-termination-gap-failure/snapshot.json)は全依存archiveではない。次の別SOURCEは、監査済みaha identityを保持し、残る18本とG1／G2／G3を検証する案である。型付きtermination-gapが既存の意味上のadmissionを満たす場合にも、成果物identityとstrict memory資格を分けて記録する。arena・fuel・CPU・FSIZE・raw・権限の条件は変えず、未知のsampling拒否は受理しない。元19本のruntime／固定点／C性能は依然未達である。
