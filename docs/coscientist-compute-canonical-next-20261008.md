# ComputeCID／ResultCIDを解析の再利用へ適用する次段階

ユーザーの提案を[既存の設計](coscientist-compute-addressed-analysis-20261007.md)と[C1bのnative前提試験](coscientist-compute-c1b-native-20261008.md)へ統合する。ComputeCIDは計算前に確定できる要求のcontent address、ResultCIDは計算後の意味上の結果と順序付き更新寄与のcontent addressである。現在状態への再適用前提と更新前後の証拠は、別のTransitionReceiptCIDに保持する。対応の正しさはCIDだけから導けない。最初は直接計算を毎回実行して照合するshadow診断とし、解析を省略するC2はOFFのままにする。

要求には、正確な同一snapshotの型付き対象・依存・解析器・規則・ABI・整数／effect／trap・資源契約に加え、4つの入口bound、呼び出し先の既存集計値、support／poison、work／admission状態を含める。既存集計値は更新と消費量へ影響するので、boundだけをキーにして完全性を主張しない。contextは一度封じ、queryごとの全メモリhashを避ける。ただし全61定義の参照閉包と11 readerについて、immutable入力、query入力、reset-before-read scratch、出力の役割と所有期間を閉じる必要がある。未分類readや外部writer／aliasはHOLDとする。

結果には意味上の答え、元の順序を保つ全呼び出し辺のbound寄与、support／poison、診断・trap／effect状態、更新前提、論理的な解析消費量を封じる。同じtargetでも別の辺は統合せず、-1と0を区別する。独立したfresh集計へのreplayと、保存した既存集計へのreplayをそれぞれ直接計算と比較する。拒否・途中計算・予算切れは成功したCompute→Result対応として公開しない。

schema・規則・ABI・bound・既存集計・依存・型・effect・trap・予算を一つずつ変更して、ComputeCIDの変更または拒否を確認する。結果の辺欠落／並べ替え、poison・診断・消費量の改変、別snapshotの参照、途中書込みを拒否し、有効bitは全検証の最後にだけ公開する。旧nativeの有限3ケース通過は、この完全なcanonical payloadや共有cacheの証明ではない。

次のSOURCE実装はstrict canonical encoder／decoder、同一snapshotの型付きresolver、read-role／所有期間の検査、ordered replay、valid-last取引を対象にする。8193個のLABEL indexを省略せず、符号化領域の増分を明記し、元の解析work上限268,435,456と診断scalar上限536,870,912は維持する。seal・hash・resolve・replay・read検証の費用も計上し、超過は拒否する。

これはコンパイル時の解析再利用の検証である。Embenchの生成コード実行時間への効果、canonical shape C1、C2、跨snapshot／process共有は未認定。将来のResultCID一致による下流再解析の停止も、query依存と結果更新の完全性を確認した別段階で検証する。生成コードの最適化は、元19本の意味保存・selfhost固定点・同一quiet hostのC比較で別に判定する。

## ResultCIDと要求に従属する実行証拠の分離

canonical native C1の最初のSOURCE案は、結果の符号化scopeにComputeCIDを含めていた。この構成では結果内容が同じでも要求が変われば識別子が必ず変わるため、ユーザーの「異なる計算から同じResultCIDへ到達する」「再解析後にResultCIDが変わらなければ下流を止める」用途には適合しない。旧SOURCEを保存し、native実行前にHOLDとした。

次案では3つを明示する。ComputeCIDは全要求の識別子、ResultCIDは明示した出力契約に従う意味上の答え・順序付き寄与・意味上の診断・論理消費量の識別子、TransitionReceiptCIDは要求と既存集計に結びつく更新前後の状態・実消費・実行証拠の識別子である。Compute→Resultの検証済み対応には、必要なreplay前提とtransition証拠を別に関連づけ、最後にだけ公開する。same-snapshot段階のResultはsnapshotと出力契約をscopeに持つので、snapshotを跨ぐ一致はまだ保証しない。

既存集計や絶対work値を結果から外す場合は、各fieldの役割を出力契約に列挙し、その値が意味上の答え・拒否・trap・poison・寄与・課金に影響しないという根拠が必要である。単に値を0にするだけでは意味保存の証拠にならない。transition全体を意味上のresultと呼ばず、両方を保持して直接計算／既存集計へのreplay／fresh集計へのreplayを照合する。

最初の追加負例は、同じResult payloadを異なるCompute要求へ関連づけてもResultCIDが変わらず、要求またはtransitionの識別子は変わることを符号化で確認する。ただし同一payloadの符号化対照だけでは、変更した2要求を実際に解析して同じ結果を得たとは言えない。実queryの再評価、省略、下流停止の効果と費用は後続の別試験とする。C1では毎回直接解析を行い、途中結果・予算切れ・古い前提の利用は拒否し、C2は引き続きOFFにする。

## 最初のnativeケースと検証器停止

新V2 SOURCEは明示した35項目をResultから投影し、477項目を保守的に保持する。除いた値も完全な512項目のTransitionへ保存し、4 CIDを22語のvalid-last関連付けに封じる。rootとnative_controlsのSOURCEレビュー後、compile／extract／case0の計3呼出は終了コード0・stderr空で閉じたが、ホスト検証器が読み込んだ旧検証器のnamespaceに`__file__`がなく停止した。最初のcampaignはFAILとして保存し、case1・2は未実行のままにした。

別V3の修正は旧検証器の正確なpathをnamespaceへ加える1箇所だけで、fixtureとnative sourceは同じ内容に固定する。rootとwidthのSOURCEレビュー後、保存済みcase0 rawを1回だけoffline判定し、[独立監査](evidence/coscientist-compute-canonical-20261008/case0-v3/independent-report.json)が結果を確認した。context12643／request3024／Result・Transition各512語、SHA-256 raw CIDの6出力、全投影field、順序付きedge寄与とsaved集計へのreplayが一致した。論理解析消費132736、診断ledger376445092は元の536870912上限内だった。fresh direct／replayとstatus／poisonはソース拘束の出力flagに基づく有限確認であり、全メモリを外部serialize比較したとは呼ばない。

異なる要求に対する同一ResultCIDは同じpayloadの符号化対照で確認し、変更した2要求を実際に解析した成功とは区別する。元の3 native呼出と失敗を再実行せず、offline段階のnative実行は0である。[選択snapshot](evidence/coscientist-compute-canonical-20261008/case0-v3/snapshot.json)はrawと監査の保存コピーで、完全な依存実バイトarchiveではない。作者・SOURCE reviewer・実監査の参加をreportに明記した。残るcase1・2の別登録検証、一般のcanonical shape C1、C2、共有cache、省略・下流停止、実性能は未認定である。

## 未実行だった2ケースの有限継続

最初のcase0の独立監査をrootが受理し、同じnative／containerと修正済み検証器を用いるcase1・2専用の新SOURCEを登録した。rootとwidthのSOURCEレビュー後、未実行の2呼出だけを新領域で実行し、終了コード0・stderr空で閉じた。[独立raw監査](evidence/coscientist-compute-canonical-20261008/remaining2-v1/independent-report.json)は182依存、元case0の75依存と失敗記録、2 argv・raw・CID・512項目の投影・順序付き-1／0寄与・集計・status／workを照合した。case1は論理消費112640／診断375628772、case2は164096／377750244で元の診断上限内だった。

全体として固定3ケース・native計5呼出の証拠が揃ったが、元campaignのFAILはFAILのまま保存する。case0の再実行と再コンパイルは0である。[選択snapshot](evidence/coscientist-compute-canonical-20261008/remaining2-v1/snapshot.json)は完全なportable依存archiveではない。full-Mとfresh direct／replayの一致はnativeソース拘束flagに基づく有限確認、Resultの異なる要求への一致は符号化対照である。一般のread／reset完全性、C2・共有reuse、下流停止、性能への効果、C以上のEmbenchは未認定のまま保持する。

## 再利用条件の分離と、重複要求の測定

ComputeCIDを計算前の検索キー、ResultCIDを計算結果の識別子として使う提案を、次の実験へ組み込む。現在の完全要求は資源・既存集計・memo状態も含むため、安全な実行証拠を特定できる一方、そのまま実用的な再利用キーになるとは限らない。[保存済み3ケースの調査](evidence/coscientist-compute-canonical-20261008/exact-key-feasibility-v1/report.json)では、同じsnapshotに対する実要求3個はすべて異なり、違う項目は対象関数と診断case番号だけだった。同一対象の繰り返しを採取していないため、キャッシュのヒット率も速度も推定できない。workの変化がこの3ケースの不一致を引き起こした、という観測でもない。

次の仮説は、意味を決めるquery入力と、現在の状態で実行・再適用を許可するadmission／transitionを分けることだ。SemanticQueryCIDには対象・依存・解析器・規則・入口boundと、答え・寄与・poison・診断へ影響する全readを含める。現在の完全ComputeCIDは保持し、work・予算・既存集計・memo状態を新しいキーから外してよいとはまだ認定しない。どのreadが単なる集約更新かを証明してから、新しいschemaを登録する。

Resultは順序付き呼び出し辺の寄与とsupport／poison／診断を保持する。ヒット時も、現在の集計へ同じ規則で寄与を再適用し、現在の権限・effect・trap・予算条件を確認する。論理的な消費とhash・lookup・replayの実作業を区別し、観測可能なfuelや課金を省略しない。途中結果・拒否・予算切れは成功対応として公開せず、全検証後にだけ有効化する。未知の条件や失効は元の直接解析へ戻す。

[次段階の設計](evidence/coscientist-compute-canonical-20261008/exact-key-feasibility-v1/DESIGN.md)では、work・既存集計・control・memo状態を各1項目変更した直接解析とshadowの比較、誤ヒット・部分公開の負例、同一対象の実重複数、context封印・hash・lookup・replayを含む費用を検証対象とする。既存の有限CID符号化試験を、異なる2要求を実際に解析した意味保存の証明へ読み替えない。再解析後のResultCID一致による下流停止には、下流が読む依存と更新契約の別検証が必要である。

最適化規則のCIDは定義CIDと分けてquery契約・成果物provenanceへ結び付ける。局所graph rewriteの意味保存検証と、cache公開／失効／再適用の状態遷移検証を別の仮説として扱う。ここで一般的なモデル検査や定理証明が実装済みとは主張しない。解析時間の短縮と生成コードの実行時間は別に測定し、最終判断には元19本、selfhost固定点、同一quiet hostでのC比較を維持する。C2はOFFのままである。

[新しい事前登録](evidence/coscientist-compute-canonical-20261008/semantic-transition-prereg-v1/preregistration.json)を凍結し、[独立SOURCEレビュー](evidence/coscientist-compute-canonical-20261008/semantic-transition-prereg-v1/independent-source-review.json)で設計の整合性を確認した。固定3対象×5条件の15 shadow commandとcompile／extract2呼出は将来の計画で、実行済みではない。初期キー除外は空、現在の完全requestとResult／Transitionは維持する。具体的な実装・変異offset・資源ledgerの検証後に実行する。同一対象の実query数を元19本から採取する別phaseと、費用を含むquiet計測も登録した。設計レビューをキー完全性・意味保存の一般証明やcache採用の承認とは呼ばない。

## 内容CIDと入力解釈の契約

比較runnerのリモートビルドで、内容一致だけでは入力の解釈を保存しない具体例が得られた。Cソースの内容をハッシュ名で配置したところ、拡張子が消え、最初のClang呼出はその入力をCとして扱わず失敗した。旧失敗を保持し、コンパイル役割に限定した同一バイトの`.c`別名をfresh領域に設ける修正を準備する。内容CIDを入力形式や実行成功の証拠へ読み替えない。

ComputeCIDの要求は、内容CIDに加え、入力の役割、reader／frontendの種類と言語モード、正規化schema、読み取る範囲、出力契約を封じる。ファイル名が意味へ影響する経路では名前または明示した解釈契約も必要である。一方、物理配置先だけの変更で内容・役割・reader契約が同じなら、不要な失効を避けられるかを別に検証する。まず役割や言語モードの変更を誤ヒット負例へ追加し、全要求のshadow照合と現在状態へのordered replayを維持する。

ResultCID一致を使う下流停止は、下流が読む出力と更新をすべて含む場合に限る。入力解釈・ABI・規則・effect／trap・現在の予算確認を省略する理由にはならない。これはコンパイル要求の契約改善であり、CIDによるEmbench実行速度改善を測定した結果ではない。

## 同一対象×5状態の具体的native shadow

既存canonical encoder／decoder・resolver・512項目のResult／Transition・ordered replayを保持し、3対象×5種類の入口状態（同一入力、work、既存集計、control、memo）の診断をKotobaで実装した。[SOURCEと初回失敗の選択保存](evidence/coscientist-compute-canonical-20261008/semantic-shadow-v1-failure/snapshot.json)。各ケースで独立した状態コピーに元の解析器を2回実行し、解析は省略しない。初期キー除外は空で、非ゼロの状態変更ケースは再利用証明を公開しない。

rootとcontrolsのSOURCEレビュー後、最大17呼出の試験を開始したが、最初のnative compileが`E2109 cond needs a final :else clause (byte 1175658)`で停止した。1呼出は閉じ、extractと15 shadowケースは未実行である。SOURCEレビューをnative型検査の代用とせず、旧失敗を保存してfresh版で既定節を修正する。現時点で同一対象のヒット率・省略・性能改善を確認したとは言えない。

## 実際に異なる要求を解析した15ケース

既定節だけを修正したfresh V2を再レビューし、compile／extractと3対象×5状態の計17呼出が終了した。[独立raw監査](evidence/coscientist-compute-canonical-20261008/semantic-shadow-v2/independent-report.json)は全argv・環境・raw、60個のcanonical objectとCID、順序付きのsaved／fresh寄与を照合した。元のFAIL1呼出は保存し、累計18呼出として区別する。直接状態・first-read・fresh状態の一致はnativeソース拘束flagに基づく有限確認であり、全メモリを別にserializeして比較したとは言わない。

| 固定3対象で変更した状態 | ComputeCID／TransitionCID | ResultCID | 再利用証明の公開 |
| --- | --- | --- | --- |
| 同一入口状態の2回の直接解析 | 元の完全要求を保持 | 一致を照合 | 完全な3ケースだけ公開 |
| work +128 | 変わる | 3対象すべて一致 | 公開しない |
| 呼出先の既存集計1項目 | 変わる | 3対象すべて一致 | 公開しない |
| control20 1項目 | 変わる | 3対象すべて一致 | 公開しない |
| 未検証のmemo-valid | 変わる | 3対象すべて変わる、complete=false | 公開しない |

work／既存集計／controlの9組は、同じpayloadの符号化対照だけでなく、変更した要求を実際に直接解析して得た有限観測である。意味上のqueryと現在状態へのadmission／transitionを分ける候補を支持する。ただし、キー除外は空のまま、解析を省略した回数は0、C2と共有キャッシュはOFFである。control20が一般に不要な入力とは認定しない。memoの不完全状態は失効・拒否が必要な具体例として保持する。

診断ledgerは352603062〜355838326で元の536870912上限内だった。これは符号化・検査の費用を含む診断量で、elapsed・RSS・速度ではない。次は実際の重複queryの分布とhash／lookup／replayを含む費用を測り、除外候補のread依存を検証してから、新しいキーschemaと限定した再利用を試す。生成コードのEmbench速度とC比較は別の評価のままである。
