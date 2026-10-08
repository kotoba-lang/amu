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
