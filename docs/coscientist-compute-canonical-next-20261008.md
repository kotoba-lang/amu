# ComputeCID／ResultCIDを解析の再利用へ適用する次段階

追加のユーザー提案も同じ検証計画へ取り込む。ここでのcompute addressは、計算を指定する正規化された要求のcontent addressであり、結果の正しさを保証する別種のhashではない。型付き定義のDefCID、要求のComputeCID、結果のResultCIDを区別する。異なる要求が同じ意味結果を得る場合は、出力契約のscope内で同じResultCIDを共有できるが、要求と結果の対応は個別に検証する。

再利用の処理順序は、要求の完全性確認、完全な保存結果の照合、現在のadmission、順序付き寄与の再適用、観測可能な消費の反映、最後の公開とする。現在の権限・失効・外部書込みは保存結果で代替しない。コンパイラ内部の探索上限と、言語から観測できるfuel・課金を別fieldとして扱い、同じ予算値をキーへ入れたことだけで消費の意味保存と判断しない。

| 比較対象 | 合格に必要な実証 |
| --- | --- |
| cacheなし／shadow／replay | owned answer、ordered edge寄与、更新後aggregate、support／poison、診断、trap、論理消費の一致 |
| 要求の失効 | 解析器・依存本文・入力状態・規則・ABI・effect・trap・予算の変更を実lookupへ渡し、旧bindingを拒否 |
| 公開の原子性 | 途中計算・途中書込み・予算切れ・不完全寄与が成功bindingとして見えない |
| 下流停止 | 完全なconsumer read viewと循環依存のpending更新が安定し、現在の再適用も完了 |
| 性能 | cold／warmのseal、hash、lookup、検証、replay、失効、missまで含む実費用を比較 |

この表は受入条件であり、実装済み機能の一覧ではない。最初の検証対象は所有した解析結果と状態更新の再利用である。元19本と自己再ビルドは維持し、解析時間と生成コードのEmbench実行時間を別に測る。現時点ではC2 OFF、key除外なし、追加省略0を維持する。

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

## 元19本の実query頻度と既存memo

新しい読み取り専用の診断をAmuでビルドし、元19本のcompile／extractを含む40呼出を実行した。[独立監査](evidence/coscientist-compute-canonical-20261008/query-census40-v2/independent-report.json)は全40呼出のraw・環境・17 countersと、全19本のKSEED・native・exportの完全一致を確認した。診断は元のqueryを1回ずつ実行し、M／G更新・追加work tick・新たな省略を挿入しない。各activation内の対象と4入口boundの反復を記録し、実際のcontrol29の結果から既存memo経路を分類した。

4,212 queryのうち既存memo hitは3,404（80.8%）、missは808だった。[保存rawの費用調査](evidence/coscientist-compute-canonical-20261008/query-census40-v2/cost-report.json)では、missを初回対象539と4bound変更の再問い合わせ269へ分解した。論理解析tickはhitの中央値2,304、missの中央値199,424、合計10,497,920／226,455,168だった。これはVWの論理workで、時間・CPU・診断IOの費用ではない。slreの初回1queryではsupportが1から0へ変わった。投影形式のunsupportedとVW errorは0でも、すべての解析結果が再利用可能とは言わない。

同じ小さな入力を繰り返す経路は、すでに既存memoが扱っている。新しいComputeCID cacheを加えればこの80.8%をさらに省ける、とは推定しない。次は269回のbound変更と539個の初回対象、順序付き寄与の再適用、context封印・hash・lookupの費用を検証する。異なる要求のResultCID一致と下流停止には完全な出力・更新契約が要る。今回の4bound頻度は完全なkeyでもResultCIDでもなく、fullComputeCIDの資格付与はfalse、新cacheの省略0、C2はOFFである。元のVWのFN128／edge512領域を観測し、canonical codecを切り詰めたCIDは作らない。[選択snapshot](evidence/coscientist-compute-canonical-20261008/query-census40-v2/snapshot.json)は全763依存の実バイトarchiveではない。生成コードの速度は、quietなC比較で別に判断する。

## 保存queryの出力projectionと次の実装範囲

269件の4bound変更missを同じworkload／activation／fnの直前queryと比較した。[保存rawのprojection調査](evidence/coscientist-compute-canonical-20261008/result-projection-v1/report.json)では、終了status・support・poisonと順序付きedge寄与の完全な記録バイトが60件で一致し、209件で異なった。空列、重複edge、site／target／base、-1 neutralと0 poisonを保持し、hash一致だけで判断していない。support低下のslre初回queryは成功projectionの集合から除外した。成功した538 subjectは329個が1種類、209個が2種類のprojectionを持ち、subject別の異なるprojectionは合計747だった。

これは現在記録した出力の一致であり、full ResultCIDではない。CQ-EDGEにはarityがなく、CQ-EXITには最終summary／certificateのcontrol9..14、完全なscratch／memo／aggregate更新、trap・budget guardの順序やread closureがない。60件は追加出力を閉じて調べる候補で、下流停止・production reuse・速度改善を認定しない。既存3,404 memo hitを新しい利得にも数えない。

[実装前の資源確認](evidence/coscientist-compute-canonical-20261008/result-projection-v1/feasibility.md)では、MM-WORDS=8,388,608の全Mをi64で符号化すると正確に64MiBとなり、stdoutへframingや診断を加えるだけで既存64MiB上限を超えることが分かった。まず読み取り専用observerへ完全なarityと宣言したsummary／certificate出力を追加する小さなshadow実装を行う。全M／read closureは別段階とし、raw64MiB snapshotファイル、別の上限64MiB journal、別metadata、再利用するchunk bufferとfirst-failureを設計・レビューする。出力roleを閉じる前に完全結果と呼ばず、journal上限も表現の切り詰めに使わない。[今回の選択snapshot](evidence/coscientist-compute-canonical-20261008/result-projection-v1/snapshot.json)はrawの重複archiveではなく、既存公開rawへのexact hash参照と269比較を保持する不完全な入力閉包である。追加native／SSH呼出0、解析省略0、C2 OFFのままである。

[独立再構成](evidence/coscientist-compute-canonical-20261008/result-projection-v1/independent/report.json)も4,212記録から60／209と538／747を確認した。公開入力参照は23件で全バイト一致した。同一projection60件の現行解析workは合計16,808,960・中央値239,744、異なる209件は合計61,000,960・中央値207,488だった。これは論理workの観測で、実時間、実際に省略したwork、再利用の可否や下流停止の利益を意味しない。独立readerのDEACTIVATE対応・JSON整数key修正の途中診断も保存し、nativeや元ソースを変更・再実行していない。


## arity・summary追加の実6-call pilot

新しいKotoba observerをAmuでcompile／extractし、元CRC32／SLREのcompile／extractを加えた6呼出が全終了した。[独立監査](evidence/coscientist-compute-canonical-20261008/output-role-pilot6-v1/reviews/actual-width/report.json)は全raw・環境・17 counters・全16 subject VW／FN fields・control9..14・ordered edge arity／IF-A/B/C／4寄与・CR-ENDを再構成し、両成果物のKSEED／native／export／offsetの全バイト一致を確認した。query161件のうちCRC8件は全成功、SLRE153件は152成功／1 support低下。既存memo hitは111、新しい解析省略は0だった。

111 hitのcontrol9..14はすべて直前のglobal queryの値と一致し、106件で同じfnの前回値と異なった。これはscratchの寿命を示す実証であり、control9..14を現在のfn固有の意味結果としてResultCIDへ封じてはいけない。全subject VW fieldsにも入口bound6..9があり、全記録状態を意味結果と呼ばない。SLREの3件のbound変更missは以前の小projectionでも追加記録でも一致0件だったが、このpilotを元19件の60候補全体へ広げない。

[著者参加を明示した再確認](evidence/coscientist-compute-canonical-20261008/output-role-pilot6-v1/reviews/actual-census-review/report.json)も保存した。出力role・read closure・現在のaggregateへの再適用・完全なResultCID／ComputeCIDは未資格、C2 OFFである。[選択snapshot](evidence/coscientist-compute-canonical-20261008/output-role-pilot6-v1/snapshot.json)は全763依存の実バイトarchiveではない。残る17件は既存observerと終了済みCRC／SLREを再実行せず、別の有限34-call実験として扱う。


## 次の再利用単位：owned answerと現在状態へのtransition

以下は次の実装契約であり、現在のcache採用ではない。ComputeCIDは計算要求を正規化した内容CIDであり、計算結果の正しさの証明ではない。DefCIDと区別し、同じ不変snapshot内ではcontextを一度封印して、小さなquery入力を厳密比較する。永続化・共有時にComputeCIDを求め、毎queryの全M hashは要求しない。

| オブジェクト | 封じる内容 | ヒット時の確認 |
| --- | --- | --- |
| ImmutableContext | 対象・型・effect・依存閉包、解析器／規則群／工程／schema、ABI・数値・trap契約、入力readerの役割 | 現在のcontextと一致、未分類read／外部writerがない |
| ComputeRequest | context、query種別／対象／mode、入口bound、意味結果に影響する全read、資源契約 | 除外項目は初期状態で空。role証拠なしの除外は拒否 |
| SemanticQueryAnswer | 問い合わせが所有するfresh要約、support／poison／意味上の診断、全arityと元の順序を保つ辺寄与 | global scratchを答えとして代用しない。-1／0、重複辺を保持 |
| TransitionReceipt | 現在の各target集計のbefore／after、元のmerge、callerのsupport低下処理、論理消費／実作業／trap・予算証拠 | 現在の集計へ再適用し、現在の権限と観測可能なfuel／課金を確認 |
| VerifiedBinding | ComputeCID→ResultCID、transition・検証器版・証拠への参照 | 全検証後にvalid-lastで公開。途中・拒否・失効した対応は利用しない |

ResultCIDの意味payloadへComputeCIDそのものを入れない。異なる要求から同じ答えを得ることを許し、要求との関係はbindingに持たせる。論理消費が結果の意味契約に含まれる版では保存し、観測不能な解析実作業を別receiptへ移す変更は別schemaとrole検証を要する。実時間やハッシュの費用を意味結果の一致から推定しない。

coscientistの次の対照は、同じ入力状態からcacheなし／shadowありを実行して、owned answer・全target更新・caller poison処理・診断／trapを照合すること。規則、ABI、依存、effect、入口bound、予算を各1項目変えた失効負例と、部分公開・stale owner・辺欠落／順序変更の拒否を入れる。費用はcontext封印、hash、lookup、検証、再適用を含めて測る。予算切れや途中拒否を成功cacheへ登録しない。内部解析上限による完了率の変化と、言語上観測可能なfuel／課金の保存は別に判定する。

局所graph rewriteでは型・effect・trap・ABIを保存する規則条件を別に検証し、その規則CIDをcontextへ入れる。公開／失効／再適用の状態遷移不変条件は、規則の意味保存と別に扱う。現在の有限テストとCID照合を、一般のTLA+モデル検査や定理証明と呼ばない。下流停止は、下流が消費する完全なAnswer契約が閉じた後の別段階である。解析時間の改善とEmbench実行時間の改善も別々に判定する。


## 元19本への出力role観測：終了済み40呼出

残る17本のcompile／extract34呼出を終了し、pilot6を再実行せず結合した。[独立保存raw監査](evidence/coscientist-compute-canonical-20261008/output-role-joined40-v1/reviews/independent/report.json)は全19本のKSEED／native／export／offsetのバイト一致、4,212 query、13,173 ordered edge、4,211 successfulとSLREの1 support低下、3,404既存memo hitを確認した。元の解析を1回ずつ呼び出す読み取り専用診断で、新しい解析省略は0である。

269回のbound変更比較は従来の小投影60一致／209差、全追加raw投影21一致／248差だった。小投影では同じだった39件の差はglobal control13（return最小bound）または14（flow counter）だけで、subject VW／FN／辺arityの差はなかった。[差分の内訳](evidence/coscientist-compute-canonical-20261008/output-role-joined40-v1/reviews/independent/projection-differences.json)。これは39件の意味結果が異なる証明ではなく、scratchをそのままResultCIDへ入れると候補判定を歪める具体例である。21件の全raw一致も完全な意味結果や再利用資格ではない。

全3,404 hitのcontrol9..14は直前global queryと一致し、2,968件で同じ対象の前回値と異なった。[SOURCEのrole／寿命確認](evidence/coscientist-compute-canonical-20261008/output-role-joined40-v1/source/result-role-contract.md)ではstage6のhitはfresh flowを走らせず、現在のcallerもこのglobal summaryを読まないことを確認した。一方、同じ辺の寄与は現在のtarget集計へ再適用される。保存する答えの所有者と、集計更新・support低下後のcaller処理を別契約にする根拠として使う。現在の処理をこの観測だけで不正と扱わない。

[選択snapshot](evidence/coscientist-compute-canonical-20261008/output-role-joined40-v1/snapshot.json)と封印済みraw34 archive／inventoryを保存した。全828依存の実バイトarchiveではない。read closure、owned summary、現在状態への再適用、予算・trap契約、hash／lookup費用は未資格で、C2はOFFのままである。

## 生成コードの候補検証との接続

ユーザーのComputeCID／ResultCID案は、解析器・不変な対象依存・入力状態・規則群・段階・ABI・effect・trap・予算の契約を要求へ封じ、答えと順序付き寄与をResultへ、現在状態の更新・admission・消費の証拠をTransitionへ分ける方針として維持する。同じResultを得る要求の対応は検証済みbindingへ置き、valid-lastで公開する。Resultから現在の権限や外部書込みを代替せず、途中拒否・予算切れを初期reuse対象に含めない。

生成コードの性能候補は、この再利用資格と分けて測る。[LCの有限runtime・原19本コンパイル・3世代固定点・G3出力一致の証拠](coscientist-masked32-clone-20261008.md)は、返り値・fuel・資源と再現性の確認であり、ComputeCIDキャッシュの効果ではない。規則群の識別子はDefCIDを改変するために使わず、ビルド要求とprovenanceへ関連付ける。次の解析reuse試験も、cacheなし／shadow／replayのowned answer、順序付き寄与、poison／diagnostics／現在aggregateを比較し、各key field失効と部分公開拒否を先に検証する。hash・lookup・replayを含む実時間を別に測るまでC2の省略はOFFである。


## reader・資源契約の違いによる計測失敗

同じ成果物CIDでも、呼出側のreader契約・OS資源制限が変わると実行できない。fresh同一hostの機能285ではC比較が通ったが、timing V1の最初のC校正はSIGXFSZで終了した。[独立保存ログ監査](evidence/coscientist-masked32-clone-20261008/leaf-read-cache-current19-timing-v1-failure/reviews/actual-failure/failure-report.json)は14子プロセスの終了、4 native校正の成功、C校正1の空stdout／stderr、測定triple 0を確認した。

比較runnerは計測前に埋込みCライブラリ17,432 Bを一時ファイルへ書く。新ledgerは標準出力の16 KiB上限をプロセス全体のRLIMIT_FSIZEにも適用しており、書込みとの契約衝突が静的ソースから確認できる。これを停止原因の有力な仮説とするが、失敗した具体的syscallの追跡はしていない。標準出力／標準エラーのstream契約、一時成果物のファイル契約、言語のfuel・arena契約を分けて扱う。

この失敗を成功ResultCIDへの対応に登録しない。実装CIDと不変な入力内容に加え、readerの意味、ABI・effect・trap・予算などの実行契約を要求へ封じ、現在状態への再適用は別のTransitionで検証する。現在の権限判断や外部書込みをキャッシュで代替しない。この診断はハーネスの正しさの証拠であり、ComputeCIDの性能効果や19本のC比較結果ではない。

## 完全キーの失効と、所有した結果の再適用を検証する

ユーザーの再利用案を[独立gap監査](evidence/coscientist-masked32-clone-20261008/compute-replay-gap-audit-v1/source/AUDIT.md)で既存の実証と照合した。既存のfield反転対照は符号化した値の相違を検出する試験であり、変更したABI・規則・effect・trap・予算を実際のcache lookup／admissionへ渡して古い結果を拒否した証拠ではない。既存15 shadowケースやpublication-prefix試験を、この不足を埋めるために重複実行しない。

次の観測対象は、queryが所有するsummary、全呼び出し辺の順序付き寄与とtargetの更新前後、callerで行うsupport低下・poison処理である。既存memo hitが返すglobal scratchを、そのqueryのResultとして扱わない。所有者を特定できないsummaryは未資格として記録し、現在の集計や権限・予算への再適用はTransitionで別に検査する。

CRC32／SLREの元の本体を使う新observerのcompile／extractと2本のcompile／extract、最大6呼出を次の有限試験案とする。これは未実行の提案で、SOURCE・正確な資源契約・2レビューの確定後に別登録する。wrong owner、辺の欠落・並べ替え、arity変更、-1から0への変更、caller poison欠落、診断・課金改変、途中valid公開、予算不足を実際のnative importer／admissionが拒否する負例も別に実装する。

キー除外は空、C2はOFF、追加解析省略は0のまま維持する。hash・lookup・replay・公開と失敗経路を含む実費用を測るまで、ResultCID一致や既存memo hit率から速度向上を推定しない。生成コードの局所書き換えとCIDによる解析再利用は別々に評価し、元19本・自己再ビルド固定点・quiet hostでのC比較を最終条件に保つ。


## immutable table規則の解析再利用への適用

次の[TC V2 SOURCE規則](coscientist-masked32-clone-20261008.md)でも同じ分離を使う。ComputeRequestへcurrent typed FN／SIR／literal・layout閉包、規則実装・工程、callerの入力範囲とprefix／successor条件、ABI・fuel／trap／資源契約を含める。意味Answerはreaderの全有限domainの値と制御・effect／fuel証明、必要なordered fixup役割を所有し、現在のcode offset・literal address・caller register cacheなどの可変global scratchを答えに混ぜない。現段階ではComputeCID／ResultCIDを実装したcacheではなく、証明対象の契約である。

再適用時には現在のliteral配置・fixup・register／context publicationを検査し、元fuel debitとadmissionを保存する。code／fixup cap失敗はrollbackしgeneric経路へ戻す。古いmachine bytesを新しい配置へ単純コピーせず、現在状態のTransitionとして検証する。規則・layout・mask・reader edge・effect・entry fuel・ABIを一つずつ変える負例、途中公開とrollback拒否をSOURCE／native段階で分けて検証する。同じAnswerCIDでもcaller条件が変われば現在のadmissionを省略しない。

LC timing V2は11本のstable30を得たが、C以上は0本、MD5の採用条件も未達だった。この[負の測定結果](coscientist-masked32-clone-20261008.md)は生成コードの評価であり、解析再利用のhash／lookup／replay費用を測った結果ではない。C2はOFF、解析reuseとEmbench速度の資格は別に維持する。


## 資源admission失敗も成功Resultへ登録しない

current typed bindingの最初のPopenはpreexecの資源設定例外で停止した。別の1-child診断はFSIZE／CPUの設定成功とAS4GiBの設定拒否を記録した。[失敗と資格の範囲](coscientist-masked32-clone-20261008.md)。いずれもcompiler結果はなく、成功ComputeCID→ResultCID bindingへ登録しない。旧失敗の正確なsetterは未確定のまま保持する。資源契約やplatform readerを変える次の要求は別ComputeRequestとして扱い、現在のadmissionを別Transitionで検証する。失敗receiptの再利用と成功解析結果の再利用を同じ状態にしない。C2の解析省略はOFFである。

## 起動環境の役割と、現在のreader閉包

portable native8の別要求でも、Python内部環境と渡した17項目を同一視した検査が失敗した。別診断で追加key名を確認した後、fresh版は渡した17値・Pythonの観測環境・native execの17値を分け、元の値の変更と未知keyを拒否した。runtime metadataをnativeへ転送する理由にせず、正規化処理とその契約も要求の実装・reader・provenanceへ結びつける。[失敗とfresh V4実証](coscientist-masked32-clone-20261008.md)。これは一般の環境key除外や既存cacheの資格ではない。

fresh V4の8呼出と独立raw監査で、現在のCRC reader FN／SIR、256通りの値、連続literal pool、callerの適用siteと通常／観測生成物の完全一致を確認した。TC規則の次の実guest検証はこの現在閉包を根拠にする。読み取り規則の候補が適用できることと、今回のnative変換のfuel・trap・prefix・arenaが一致することは別の検証であり、まだ候補コードを実行した証拠ではない。ComputeCID／ResultCID cache、C2の解析省略、生成コードのC以上の性能も未資格のまま保持する。

## 計算結果CIDと下流consumerの停止条件

ユーザーの追加案を[consumerの受入条件](coscientist-compute-result-consumers-20261008.md)へ具体化した。ResultCID一致後も現在のtarget集計・caller poison・権限・予算を検査し、consumerが読む全入力と循環依存のpending更新が安定した場合だけ、追加再解析停止の候補とする。Answer一致だけでworklistを消さない。SOURCE照合ではcurrent16に旧stage6の`vw-*`経路がないことも確認した。旧解析を現在のbuilderで組む診断と、現在の製品解析を観測する検証を別lineageとして扱う。追加native呼出0、解析省略0、C2 OFFであり、CIDの実測性能効果はまだない。

## Owned queryと順序付き更新の有限契約モデル

[新しいsource proposal](evidence/coscientist-masked32-clone-20261008/compute-owned-query-shadow-proposal-v1/source/PROPOSAL.md)はhistorical V7のdirect mode1 queryとcallerのsupport低下・poison処理を分ける。global scratch summaryはdirect return直後に所有したcopyを作り、既存hitに所有者がなければ未資格とする。全辺の寄与は順序と重複targetを保持し、-1と0を区別する。現在の集計・work・admissionは要求に保守的に含め、更新前後と観測可能な消費をTransitionへ保存する。ResultにはComputeCID自身を含めない。

有限Python診断モデルは25の要求field変更、digest bucketの衝突を模した不一致、9の結果・replay改変、予算不足・support低下・途中valid公開を拒否した。rootも全5 source／5 input pinsとcontrol結果を再確認した。これはsynthetic JSON/SHA契約の確認で、Kotoba解析の実装、IPLD canonical encoding、native importer、一般の健全性証明や性能測定ではない。[選択snapshot](evidence/coscientist-masked32-clone-20261008/compute-owned-query-shadow-proposal-v1/snapshot.json)。

最初の未解決条件は、正確なhistorical snapshotでの全reader・alias・writer・reset-before-read・出力所有期間の閉包である。current16には同じ解析経路がないため、historical queryの証拠を現在の製品cacheの資格へ移さない。次のobserverも毎回direct解析を実行するshadow診断とし、C2 OFF・キー除外なし・追加省略0を維持する。hash／lookup／replayと失敗経路を含む費用を実測するまで、CIDによる性能向上を主張しない。

current OFF/TCの機能V3でも、SLRE32の保存rawは戻り値・fuel・17arenaで一致した一方、未登録childのsampling拒否でcampaignは停止した。[保存失敗の範囲](coscientist-masked32-clone-20261008.md)。結果内容の一致と現在のadmission成功は別である。raw一致を理由に拒否を成功bindingへ書き換えず、成功した結果の再利用契約と失敗TransitionReceiptを分けて保持する。

## 現在のfuel規則にも要求・結果・再適用を分ける

[公開型x8 fuel候補](coscientist-masked32-clone-20261008.md)の適用証拠を将来再利用する場合も、ComputeRequestは現在のtyped FN／SIR、call／CFG・private entry・layout、規則の実装、register／context reader、ABI・effect・trap・fuel契約を封じる。Owned Answerは適用可否と意味保存の条件を持ち、過去のcode offsetや可変register scratchをそのままコピーしない。実際の現在配置、x8／contextの全writer、entry初期化とfuel公開をTransitionで検査する。規則の条件を証明できたことと、現在のnative codeが条件を満たすことを分ける。

残り50件を含む95組の保存raw一致でも、SLREの旧admission拒否は残った。Resultが一致しても現在のadmissionを省略できない具体例として保持する。今回の214 tickモデルは生成命令の有限契約検査であり、ComputeCID cacheの実装・IPLD符号化・解析費用の改善ではない。cacheなし／shadow／replayのowned Answerと順序付き寄与・現在の更新を一致させ、実lookup失効・途中公開拒否と全費用の測定を通すまではC2をOFFに保つ。
