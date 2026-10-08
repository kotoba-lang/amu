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
