# フレーム再利用の10辺合成と、実行前のプロセス帰属確認

最終条件は元Embench19本を変えず、Kotoba／Amu selfhostでC以上の実行性能を同じquiet hostで示すことである。今回の成果は生成コードと検証経路の前進であり、性能条件の達成ではない。C2はOFF、解析省略0、キー除外なしを維持する。

汎用の同サイズ末尾フレーム再利用候補は、FN走査・作業量・LABEL容量を制限し、変更のたびに現在のFIX target閉包を再確認する。`gn-put`は可変`vector-assoc!`であり、不変グラフと仮定しない。元のCODE／FIX数、公開prologue／export、frameサイズを維持し、対応した末尾辺だけを同一frameのprivate引数入口へ分岐させる。入力源の名前を選択条件にはしない。

[固定4回のbuild／extractと独立保存監査](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-compose10-native4-actual-v1/snapshot.json)が通った。current7618が新しい候補コンパイラを生成し、その候補が変更していない元nsichneuを生成した。候補nativeは874,264 B、SHA256 `552939e18c86c6e7f9f8dcc5aba961ab15bc91330132b5821993c911065133f2`、sole `main@0/0`である。元nsichneu nativeは37,520 B、SHA256 `c6d22d3f547832430d7263892e8ddd9697f04317ddc16f76edddde2baf548af2`、`batch@36440/1`である。

元nsichneuは、事前登録した10辺・40ワードだけが変更され、その他の全バイト、全export、header、長さは一致した。4子プロセスはclosed0、74有限サンプル、4件すべて既存の厳密サンプリング方針を通った。これはhard peakの証明ではない。独立保存監査の担当は診断driverの作者であり、変換規則の作者・実行担当とは別である。driver自体のSOURCEレビューは別の2名が担当した。

[元5入力の新しいruntime10](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-compose10-runtime10-v1/snapshot.json)も一度だけ実行し、独立保存監査を通った。入力0／1／2／17／32のOFF／ONは結果0／1／1／1／1、fuel1／272／527／4352／8177、17 arenaの全値で一致した。10子プロセスはclosed0、25有限サンプル、10件すべて既存の厳密サンプリング方針を通った。旧1辺候補の成功を10辺候補へ移したわけではない。複数辺の一般的なprivate ABI／alias／trap、全19本、候補自身の固定点、quiet hostのC比較はまだ成立していない。10辺は試験の作業上限であり、性能上の最適値と決めていない。

実行前にGO schema欠落という誤指摘が出たが、正確な凍結バイトには必須項目が含まれていた。rootと独立レビューで19項目・19種類・該当項目1回を照合し、正しいV1でのみ実行した。誤指摘に基づく未使用V2は該当項目が重複しており、未実行のまま訂正記録と保存した。SOURCE誤読と候補コードの失敗を分ける。

[同じ汎用判定による全走査の有限census](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-full-scan-frontier-v1/snapshot.json)では、267 FN中の266 ownerを走査し、逐次変更するFIX閉包を各変更の前後で検査した。適用可能辺は123、10辺より113多く、LABELは587から710へ増える。上限131,072以内であり、次の汎用作業上限511はこの変換が受理するFN数の上限512（sentinelを含む）から導く。物理的なFN表容量は8,192であり、512ではない。123という発見数をソースの選択条件にはしない。モデルでは492ワードの変更を予測するが、全走査版の実native生成・実行はまだない。

同じABI前提の下では、実行された各辺につき公開prologueの5命令と48 Bのframe成長を省ける。末尾restoreの3命令はLDRと2 NOPへ置換するため、その3命令が消えたとは数えない。123辺が各1回走る仮定なら615命令・5,904 B、10辺なら50命令・480 Bだが、動的実行回数や実時間ではない。fuelのdebitは0件も省略しない。全走査候補を実装・生成し、元入力の意味保存と自己再ビルドを検証した後、Cと同じquiet hostで実費用を測る。

G4の190回比較を止めた別の課題については、[実行前帰属確認のSOURCE設計](evidence/coscientist-masked32-clone-20261008/runtime-owned-child-handshake-design-v1/source/README.md)を保存した。現在のC loaderはfork後に子をすぐ走らせ、親がwaitpidで回収する。20msサンプリングの間に子の生存期間が収まり、最初の帰属問い合わせがESRCHになることが可能である。保存ログは子のbirthを一度も受理しておらず、旧拒否は維持する。具体的にどのwaitと競合したかを動的に証明したわけではない。

新しい診断経路はleaderとguestを保持し、専用channelで現在GOに結び付いたPID／birthを確認して耐久化してからguestを解放する。未知PIDは引き続き拒否し、既知birthの終了ギャップはfootprintをnullのまま、正確なchild waitの証跡と分ける。元のguest argv・17環境値・fuel・arena・capabilityは維持し、追加host descriptorは別の予算に明記する。待機費用は将来のguest測定区間の外に置く。

V1は18有限対照を通した設計段階で、channel I/O、割込み、FD cleanupの完全実装はない。rootレビューはstageとPIDの不整合をモデルが受理できる欠落も記録した。V2で型付きエラー由来・stage／PID／queryの照合と部分I/O／重複ACK／終了時cleanupを実装・検証する。宣言だけのAPIを稼働経路として数えず、実機でのloader lineage、sandbox、birth取得、channel所有と終了確認を通すまで、新しい全19本比較の資格へ用いない。

V2のSOURCE実装には、終了したchildを帰属確認後すぐ回収しない段階も加える。現在のDarwin SDKは`waitid`と「processをwaitableのまま残す」`WNOWAIT`を宣言している。loaderが終了を観測して保持し、監視側が同じlockの下でgroup照会・signal権限を退役してからREAP_ACKを送り、その後だけ元のwaitpidで回収する設計である。これにより照会中の数値PID再利用を防ぐ条件を置く。SDK宣言は実機挙動の証拠ではなく、zombie、WNOWAIT、割込み、deadlineとcleanupの実機資格確認は未完了である。元30秒の絶対期限を後段のsuperviseで更新しない条件も検査する。

ComputeCID／ResultCID案は、[再適用契約](coscientist-compute-replay-checkpoint-20261009.md)とこの候補を接続する。全走査の費用を下げる最初の候補は、FNのコード区間終端を各FIXごとに読み直す処理を、同じFNの検査開始時に一度だけ計算して渡すことである。共有キャッシュを先に有効化するのではなく、その計算が読むFN表・FN数・CODE数を列挙し、同じ工程のwriterがCODE／FIX／LABELだけを更新することと、各領域が重ならないことを検査する。可変M全体を不変と仮定してはいけない。FIX target閉包は変化するため、各変更時に引き続き検査する。

この工程内の不変条件の検証は、後のCompute要求のread-setを具体化する証拠になる。永続化する場合は、解析実装・規則版・対象・その読取snapshot・ABIと資源契約をComputeCIDへ封じ、区間終端というAnswerをResultCIDへ封じる。ResultCID一致だけでFIX／LABEL検査や現在の作業量確認を省かない。辺のbound更新を持つshape解析では、Answerだけでなく順序付き寄与・support／poison・診断を保存し、現在の集約器への置換と再集約をTransitionで検査する。途中拒否・予算切れは成功bindingの対象から外す。

比較は元の再計算版と候補について、適用辺・全変更バイト・拒否・容量条件を一致させ、読取箇所だけを一つずつ変更した対照で失効を確認する。その後のnative生成と自己再ビルドを通してから、解析時間を計測する。観測可能なfuelはヒット時も契約に従って消費し、物理的な探索費用と分ける。生成コードのEmbench実行時間は別の比較であり、この工程内の省略をIPLD／CIDの高速化と呼ばない。現時点では新しい共有解析再利用は未実装である。

[V2の独立SOURCE監査](evidence/coscientist-masked32-clone-20261008/runtime-owned-child-handshake-v2-source-hold/review/independent/report.json)はHOLDとした。正常終了の保持・lock下の権限退役・ACK・回収という順序を確認した一方、31有限対照では覆えなかった失敗cleanupの欠落を発見した。第三のreceipt workerの停止ACKがない状態でもjournalをclose／hashする経路、supervisorのdeadline／channel失敗時に未回収childをcleanupしない経路、Popen直後のpeer close失敗がPIDの耐久記録より先に起きる経路である。V2はbuild／GO／native実行0のまま保存する。V3ではwriter停止を記録公開の前提とし、childの未回収／回収済み／不確実状態を分け、cleanup wait前にalarmのsignal対象を退役する。有限の成功対照だけで失敗経路を資格化しない。

[区間終端を一度だけ計算する候補V2](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-bound-hoist-v2-source/snapshot.json)は、rootと独立SOURCEレビューが通った。22 SOURCE／80入力の全pin、current16の完全な順序付き結合、6引数の再帰、7箇所のwriterと完全なFN領域の分離、6種類の純粋検査を照合した。元の123辺・492ワードの予測を維持し、保存入力の区間終端探索は27,646,710から32,718 FN訪問、受理上限での最悪計算量は17,112,564,735から261,121へ減る。これはソースモデル上の探索量であり、native命令数・時間・速度ではない。コンパイラ自身が使うfuel／arenaの一致は主張せず、生成された元Embenchのfuel／trap／arena保存を別に検証する。新共有CID問い合わせの省略は0のままである。V1の「容量512」という説明を、受理上限512・物理容量8,192へ直したV2を正式なレビュー対象とし、旧版の封印は保存した。次は別登録した固定4回のnative build／extractで、実際の492ワードと全出力を確認する。

[区間終端hoist V2の実native生成4回](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-bound-hoist-native4-actual-v1/snapshot.json)も一度だけ完了し、rootと独立保存監査を通った。current7618から作った新しいG1は874,424 B／SHA256 `c3503b7f746b9279a27bba6f5b6a1e97f7a2770b694bdf42a558fd7cc856f445`、sole `main@0/0`である。そのG1が元nsichneuを生成し、37,520 B／SHA256 `f00efff199abd9795620e0a13be6695fb05de6d181fe080343b89ceae3703578`となった。予測した492ワードだけが変わり、他の全バイト・header・export・長さは一致した。4子プロセスはclosed0、69有限サンプル、全4件で既存の厳密方針を通った。6引数helperを含む候補の生成・この入力での実コード出力は確認できたが、一般的なtype／alias／ABI、元5入力の実行、全19本、自己固定点、C比較はまだ別の条件である。旧10辺runtime10の成功を123辺候補へ転用せず、新しいruntime10を登録する。CIDの効果や解析時間短縮の実測もまだ主張しない。

[全走査hoist候補の新しいruntime10](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-bound-hoist-runtime10-v2-failure/snapshot.json)は、一度だけの実行で7回目に停止した。V1は入力登録の実数256／20,913,901 Bに対し、古い155／13,280,263 Bを事前登録しており、2件のSOURCEレビューもその不整合を見逃した。実guardが出力rootを作る前に拒否し、native起動0だった。最初のエラー説明は実行出力から転記したもので、保存済み実プロセスreceiptと扱わない。V1の凍結・レビュー・誤りを保存し、新しいV2では本番guardと純粋対照が同じ整数型・件数・byte数照合を使う。

V2の入力0／1／2のOFF／ONは、結果0／1／1、fuel1／272／527、全17arenaで一致した。7回目の`nsichneu-OFF-n17`は、PID61254の`member-getpgid`／query21／errno3を、そのbirthが以前に受理されていないため拒否した。全7子プロセスはclosed0、20有限サンプルが保存された。OFF17の生出力は結果1・fuel4352だが、監視拒否があるため資格化しない。ON17／OFF32／ON32の3回は未実行、completeは存在せず、この試行は失敗として保存する。再試行しない。未知PIDのfootprintを0と置き換えず、元5入力・全19本・性能の資格は未成立である。

[同じcurrent16候補のG2→G3→G4固定点6](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-bound-hoist-fixedpoint6-actual-v1/snapshot.json)は、別の2件のSOURCEレビューと新GOの下で一度だけ完了し、rootと独立保存監査を通った。保存したG1がG2を作り、G2がG3、G3がG4を作った。各世代の2回のcompile／extract、順序付き生成receipt、全source／builder／GO／payload／exportを再照合した。G2／G3／G4のnativeは874,424 B／`c3503b7f…`、containerは874,450 B／`cf3e43cd…`、sole `main@0/0`で全バイト一致した。G1も結果として一致したが、事前条件にはしなかった。全6子プロセスはclosed0、199有限サンプル、全6件で既存の厳密方針を通った。これは最新候補自身の自己再ビルド証拠であり、元19本のguest実行・C比較・一般的な機械証明を代替しない。

[保持付き監視のV3／V4](evidence/coscientist-masked32-clone-20261008/runtime-owned-child-handshake-v3-v4-source-hold/snapshot.json)は、SOURCEの失敗対照でHOLDとした。V3はwriter停止ACKとC側の未回収child cleanupを修正したが、Controllerを作った後のpeer close失敗では、早期leader終了条件が`ctl is None`なので処理を飛ばす。V4はpeer closeをControllerより前へ移したが、その後のFD引渡しのsecond-dup失敗でも同じ条件で飛ばすことを、実SOURCEから抜き出した注入対照で確認した。正常対照の成功だけで後始末を資格化せず、両版はGO／build／native0で保存する。次のV5では、TICKET前という状態をControllerの存在とは分け、監視の退役・停止確認後、まだwaitしていない正確なdirect leaderだけを一度終了させる条件を検査する。実C build／FD引渡し／WNOWAIT／birth／回収順の実機資格は依然として必要である。

並行作業は、候補自身の固定点と全19本の生成登録、保持付き監視の失敗経路修正、元入力・C比較条件の照合に分けた。SOURCE読取・純粋対照・保存監査は並行し、native呼出しはrootが逐次実行する。同じhostで性能測定とビルドを重ねない。最新G4を全19本へ使う際には、旧G4の証拠を転用せず、今回の順序付き生成receiptと完全なcurrent16のinterfaceへ結び直す。ComputeCID／ResultCID共有再利用はまだ有効化せず、C2 OFF・新CID問い合わせ省略0・キー除外なしを維持する。

[保持付き監視V5の2件のSOURCEレビュー](evidence/coscientist-masked32-clone-20261008/runtime-owned-child-handshake-v5-source/snapshot.json)は、既知のpeer close／FD引渡し失敗の終了条件を修正したことと、wait／不確実状態の後にsignal権限を復活させない順序を確認した。実SOURCEから16 setup境界、8 signal拒否条件、独立した9条件を照合した。これは順序・signalの安全条件のSOURCE確認であり、全失敗の期限内終了を保証しない。capture停止待ちが残り期限を使い切ると、leader終了後のdirect waitには最小0.001秒しか残らず、不確実終了として拒否する可能性がある。未知・未回収の所有権を成功へ変えない。V5は実操作0のまま、C bootstrap→実FD／channel／保持birth／WNOWAIT fixture→新paired2の順に資格化する。fixtureの将来の証拠はGOだけから参照し、凍結済みpolicyの入力へ追加しないため、循環する依存にはしない。元95入力の比較とは別の診断呼出しとして数える。

[監視用C bootstrapのbuild5 V2](evidence/coscientist-masked32-clone-20261008/runtime-owned-loader-build5-v2-preview-failure/snapshot.json)は、2件のSOURCEレビューを経て一度だけ照会し、3回目のlink previewで停止した。3 direct waitはclosed0、build／guestは0である。凍結済みV5の予定argvと完全一致させたが、実cc1の`-dumpdir`に続く出力prefixを、未登録の絶対入力と誤判定した。両SOURCEレビューがそのオプションをモデルへ含めていなかったことも保存した。後続の絶対include search operand、prefix形式の`-I`／`-L`も、入力・探索directory・出力の役割を分ける必要がある。無制限に絶対パスを許可せず、実保存previewの完全なtemplate、SDK／resource解決先、local shadow library／headerの不在確認を次の登録へ含める。失敗したV5出力namespaceを再利用せず、同じC・監視mechanicsのV6を新しい出力先へ結び直す。これはCローダーbootstrapの検証であり、KotobaをLLVM経路へ切り替えたものではない。

[最新G4による元19本の生成38回](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-bound-hoist-g4-original19-compile38-actual-v1/snapshot.json)も、2件のSOURCEレビューと新GOの下で一度だけ完了し、rootと独立保存監査を通った。全38子プロセスはclosed0、元19ソース・95入力profile・全payload・選択export・全export・生成元G4を照合した。122有限サンプル、37件は既存の厳密方針、`aha-mont64-compile`の1件は以前に受理したbirthの終了ギャップとして別に記録した。hard peakは主張しない。nsichneuは最初のnative4と同じ`f00efff1…`で、OFFとの差は事前登録した492ワードに限定される。旧OFFとの保存バイト比較は実行の意味保存を証明しない。生成した19本のguestはこの38回では起動しておらず、全95入力OFF／ON・C比較・候補採用はまだ別の資格である。

[最小V6のSOURCE](evidence/coscientist-masked32-clone-20261008/runtime-owned-child-handshake-v6-source/snapshot.json)は2件のレビューを通った。C・ownership・native-call・capture・controllerなど17 mechanismはV5と同じバイトで、失敗V5の3照会を保存した上で新しいsource／loader出力namespaceと将来のbuild／fixture証拠statusへ結び直した。監視の意味を変えて失敗を通したものではなく、旧出力を再利用しないための登録変更である。実build／fixture／期限内cleanupの資格は未成立である。

[新しいV6 C bootstrapの実build5 V3](evidence/coscientist-masked32-clone-20261008/runtime-owned-loader-build5-v3-actual/snapshot.json)は、一度だけの5照会／ビルドを完了し、独立保存監査を通った。5 direct waitはclosed0、実buildは1、guest起動は0。240 header／5,270,106 Bと39 TBD、保存link previewと出力・探索operandの役割、local shadow不在、Mach-Oの限定したload contractを照合した。ローダーは215,224 B／SHA256 `35441a47f8c2f64adde93a08d98767ca94c9c22078fdd5889df2228e98b7078c`。これはC bootstrapの成果物同一性の証拠であり、guest実行や全動的runtime閉包の証明ではない。

[保持付き監視V6の実fixture4](evidence/coscientist-masked32-clone-20261008/runtime-owned-child-handshake-v6-fixture4-actual/snapshot.json)も別の2件のSOURCEレビュー、新GOの下で一度だけ完了し、独立保存監査を通った。正常OFF／ON、second-dup失敗注入、writer callback停止の4件で、正常3件はwait0、注入1件はwait−9、9有限memory samples、12所有権行、6保持birthを記録した。正常OFF／ONは結果1、fuel1698、全17arenaで一致した。停止中のwriterを強参照してjournalを未close・未hashのまま保持する条件を実確認し、callback解放後のfsync・停止ACK・回収も照合した。これは実kernel fsync stall注入でも、外部syscall traceによる普遍的race証明でもない。元95 profileへの実行creditは0、性能資格も0である。

次の全19本比較は、今回生成したG4成果物、current7618 OFF、限定した実fixture4、同じV6監視mechanicsに結び付けた新しい190回登録を使う。元95 profileを隣接OFF／ONで実行し、結果・fuel・全17arenaと保存CのBoolean結果を照合する。SOURCEと保存監査を並行し、native起動とquiet host性能測定は直列に保つ。ネイティブ共有ComputeCID／ResultCIDの実装・失効／寄与再適用検証は別担当が並行して進めるが、未実装の資格は変更しない。

[最新G4の元19本・95 profileのruntime190](evidence/coscientist-masked32-clone-20261008/homogeneous-tail-frame-bound-hoist-g4-original19-runtime190-actual-v1/snapshot.json)は、新しい2件のSOURCEレビューとGOの下で一度だけ完了し、rootと独立保存監査を通った。全190 direct waitと保持guestのwaitはclosed0、95組で結果・fuel初期／残量／消費・全17arena値が一致し、保存済みsource/profile-bound CのBoolean結果とも一致した。Cのfuel／arenaは取得していない。587数値memory samples、760所有権行、190 invocation seal・raw・資源・memory・所有権journalと実wait receiptを再照合した。全190件は保持付きの厳密方針を通過した。元nsichneuのfuelは入力0／1／2／17／32について1／272／527／4352／8177で一致した。独立担当は190登録driverの作者であり、変換規則・実実行担当とは別である。監視mechanicsのSOURCEは別担当がレビューした。この結果は元19本の有限実行比較の資格であり、一般ABI証明・hard peak・C以上の速度・公式Embenchスコア・製品採用ではない。

[次の同一quiet host C比較](evidence/coscientist-masked32-clone-20261008/current-g4-quiet-c-comparison-design-v1/snapshot.json)では、旧LC consumerが4 arena値と古いhelper bankを使うため、そのまま最新イメージを差し替えない。現行17カウンタとreset／helper contractを維持する測定consumerを新規に適合させ、fresh Cと同じhost・元body・profile・実行区間で資格化してから反復測定する。設計資料は実行登録・GO・測定結果ではない。負荷の単発読取もquiet資格にしない。

[ComputeCID／ResultCIDに向けたnative fragments](evidence/coscientist-masked32-clone-20261008/compute-result-native-edge-replay-fragments-v1/snapshot.json)は、1,149有限モデル照合を作者とrootが再現した。旧V7 shape解析用の順序付きedge contribution capture／reset／replay／invalidate／valid-last publishと、現行generic callの`gn-ctx-safe(M,f,n,8,512)`のexact top-level memo案を分ける。旧V7は現行41に存在しない。現行案も8セルのscratch所有権・cleanup、最新G4 candidateのread-set、実際の同一キー重複と探索削減、native differentialが未資格である。現行コードのSOURCE observerと測定consumerの実装を並行し、native実行はrootが直列に行う。共有CID cache／IPLD符号化・永続化・性能効果は未実装のまま、C2 OFF・新共有query skip0・キー除外なしを維持する。

[現行17カウンタに対応する測定consumer V2](evidence/coscientist-masked32-clone-20261008/current17-timing-consumer-v2-source-and-syntax1/snapshot.json)を実装し、rootと独立SOURCEレビューを通した。V6 C helper bankは3つの診断hookを逆変換すると元の全バイトと一致する。各呼出しでfuel・allocator・region／validation状態と17カウンタをリセットし、warmup後の各呼出し結果と全状態を照合する。計時はreset後からguest関数終了までとし、snapshot、画像照合、dylib materialization、所有権handshakeを含めない。CPU quiet envelopeにはresetなど全実行過程を含める。C側へ追加したarena準備費用でCの数値を遅くした比較を主結果にはしない。時計境界の費用は残る。

元の19 C bridgeは8引数の型を持つことを実ソースへ照合した。V1のJSON decoderが重複keyを受理するSOURCE上の欠落を保存し、実操作前にV2へ修正した。V2は190保存raw対照、774拒否対照とheader生成モデルを通し、独立レビューはC decoderの別対照も確認した。C bytesが同じV1コピーについて、合成Mach-O data headerを明示してClang `-fsyntax-only`を一度だけ実行し、closed0・stdout／stderrとも空だった。object／実行ファイル・guest・fresh C成果物は0。この合成headerは実Cビルド証拠ではなく、consumerの型・field・symbolの構文確認に限る。

fresh C19を独立監査した後にその実バイトから19 headerを作り、consumerをビルドする。285 fresh profile／arm呼出しと57 repeat-reset呼出し（warmup込み741 guest invocation）の登録と厳密decoderはSOURCEで実装したが、実行adapter・追加FD／dlopenの資格は未成立であり、342回を実行したとはしない。性能・公式Embench・C以上の数値はまだない。現時点のhost選択読取はzebulunのApple M4／10 cores／16 GiB／macOS26.2／Clang17で、quietやコンパイラ依存閉包の資格ではない。

[転送コアmanifest](evidence/coscientist-masked32-clone-20261008/current19-transfer-core-manifest-v1/snapshot.json)は156 regular file／4,299,692 B、元19 Kotoba source・OFF／ON各19の全native／container・53 C-owned source／support／bridge・recipe／証拠の最小一覧である。古いLC consumer／C binary／SDK全体を含めない。アーカイブ・転送・ビルドはまだ行っておらず、frozen consumerと新C build-phase driverを束ねる実行登録を並行して作成する。現ホストの実Clang `-M`依存閉包、有限resource／raw／artifact、fresh namespaceと再試行しない条件を検査する。

[最新626／b8d系譜の解析観測prototype](evidence/coscientist-masked32-clone-20261008/current-g4-ctx-observer-prototype-v1/snapshot.json)は原queryを省略せず、一度の評価のkey／answerと有限の再帰走査を記録する。DI snapshot二bankが既存tail80セルを全て占有するため、コピーしたallocationを80→88へ明示的に延長し、8 observerセルを普通／generator-error returnで清掃する。割込み・trap後の清掃の機械証明ではない。最初の「空きtail」census誤りは保存した。追加のdiagnostic FF／SIR読取も境界を明示する修正が必要で、実行登録V2を準備中である。rootの最初の指摘が元queryのguard順を過大に述べた点も訂正した。元queryはFF-SIRをBoolean guardより先に束縛しており、任意のinvalid fが元から安全に拒否されるとは主張しない。元queryのバイト・評価順を維持し、追加loggerの無効域読取を避ける。native parsing・artifact equality・重複keyと実探索費用の観測は未成立、共有CID cacheと性能効果も未資格である。

### Current G4 structural-query observer4: actual bounded observations

The four compiler-only calls completed with direct exit0. The copied observer compiler compiled the unchanged original statemate and nsichneu bodies. Complete KSEED bytes, native payloads and export lists equal the saved ordinary current G4 outputs. The independent saved audit is `docs/evidence/coscientist-masked32-clone-20261008/current-g4-ctx-query-observer4-actual-v2/reviews/independent-actual/report.json` (origin report SHA256 `38803a8d5df6eb15c66226eccded09d9386da503de03d754c8e0bb2ddd767878`). It checks all four closures, raw records, 30 SOURCE/75 input pins, producer gate, resource witnesses and 76 numeric memory samples. One statemate sample retains the previously admitted typed termination gap and null unknown footprint; this is not a hard peak or arbitrary process-tree proof.

| Original workload | Total top queries | Complete observed summaries | Equal-key repeats | Hypothetical repeated scan entries | Hypothetical repeated safe entries |
| --- | ---: | ---: | ---: | ---: | ---: |
| statemate | 221 | 221 | 24 | 4,305 | 333 |
| nsichneu | 392 | first 256 | 127 | 23,804 | 490 |

Only the first16 queries have complete recursive traces. Every original query still executes; the observed repeat counts do not establish cache-key completeness, memo speed, ComputeCID reuse or runtime performance. The observer uses a copied explicit80→88 scratch allocation and preserves original query bodies/evaluation. This gives a concrete hypothesis for a bounded in-pass memo; persistent ComputeCID/ResultCID publication, edge replay and effect/fuel/trap contracts remain separate implementation and validation work.

The selected zebulun host identity read completed separately. Its canonical CLT Python is3.9, and it adds `__CF_USER_TEXT_ENCODING` to the supplied environment. Clang is272,034,048 bytes, exceeding the first diagnostic's128MiB read cap; that failed read is retained and was not a build/native failure. A fresh512MiB streaming identity registration pins stable Python/Clang/linker/libSystemTBD bytes and the actual SDK26.2 alias. This is tool selection evidence, not quiet-host, fresh C build or timing proof. C-build SOURCE is being revised to accept only named Python metadata and exec the exact prescribed environment. Packet-install V1 operational eligibility was withdrawn after finding completion-before-finally-raw-fsync; no V1 transfer occurred. A fresh V2 writes raw and terminal evidence before publishing completion.
