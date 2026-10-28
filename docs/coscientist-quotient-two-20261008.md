# 符号付きliteral +2除算のnative候補

元19本でC以上という目標は未達。新しい `q2-feature` は既定OFFの隔離実験で、現在のEXTR計測cohortは変更していない。IPLD/CIDによる速度効果の主張でもない。

`quot x 2` を `ADD d,x,x LSR#63; ASR d,d,#1; MOVZ x17,#2` へ生成する。xが負なら1を加えてから算術右シフトするので、全i64で0方向への除算と一致し、MINでも加算はoverflowしない。最後のMOVZで元のscratch x17=2を復元し、3命令ともNZCVを変えない。x/d17と31は元の経路、x/d16とd==xは許可する。変更はinteger literal+2の分岐と3 helperに限定し、protect/ldt/fin/cache・元SIRのfuel経路を保持する。これらの実行時観測は後続検証が必要。

2語だけの置換はscratch x17を変えるため、継続コードの条件確認が必要だった。静的に2箇所を対応付けたが、[postpass案](evidence/coscientist-quotient-two-20261008/postpass-hold.json)はFIXに記録されないADRとinline tableを命令として誤認する恐れがありHOLDのまま。3語案は直接emitterで生成し、後続領域の全走査を避ける。

3語案は元の2語よりCODEが1語増える。ONの容量境界で以前通ったcompileが拒否される可能性と、label・offset・literal配置の変更を明示した新しい実験資源契約である。旧CODE容量・途中状態・ON出力バイトの同等性は主張しない。dirty MMERRは元の経路へ戻す。既定OFF、4 source variantの完全逆差分を確認し、[独立sourceレビュー](evidence/coscientist-quotient-two-20261008/source-review.json)は12,009符号付きモデルケースと900組のレジスタ符号化を確認した。

[有限native自己再ビルド](evidence/coscientist-quotient-two-20261008/build-report.json)はOFF1世代とON4世代、compile/extract計10回を実行し、すべて終了コード0・stderr空・timeoutなしで閉じた。旧76e9 producerで作るON1はbootstrapとして事前登録し、ON2・3・4の3世代全バイト一致を要求した。実際にON1は947,896 B、ON2〜4は947,944 Bで48 B異なり、後者のnative SHA-256は `65bccc45e9eb96ee9beddf8b1ce97c755461b37f76bdb2838bff19a5b0a02b3f`、KSEEDは `56444d10e8e44c034e49a8ee8177b60df00b865a312fbd3a3eaf3a69913591e3` で一致する。コンパイラ自身のsourceにもliteral2除算があるため、初代を後から失敗の計数から除いたものではない。

[独立raw監査](evidence/coscientist-quotient-two-20261008/build-actual-review.json)は10 argv・producer chain・root GO・review・入力・raw・全header/sole main0 payloadを照合した。[全内容packet](evidence/coscientist-quotient-two-20261008/content.tgz)は2,438,495 B、SHA-256 `3d651820dfb53f3f7f58d4d3e2190533ba2b7ce7409aaf2a13925d3fe393f0a7`、55 regular member・展開9,654,019 B。70元パスを54 content memberへ重複排除し、embedded manifestを含む。[内容監査](evidence/coscientist-quotient-two-20261008/packet-review.json)も抽出・実行なしで全件照合した。元の絶対パスとloader/producerを保存する内容証拠で、portable再実行やsource-to-loader由来証明ではない。

固定点は速度の証拠ではない。native深い状態・容量境界、実際に発行したCODEの符号付き入力実行、fuel・arena観測、元19本のOFF identity/ON machine比較と機能、同じ静穏hostでのCとの速度比較はまだ必要である。現在のEXTR cohort・製品baseline・bin entryを切り替えず、C以上・公式スコア・製品採用を未達のまま保持する。

## 成分試験V1の停止

Q2成分試験は上限14回で新規登録したが、[独立実監査](evidence/coscientist-quotient-two-20261008/state-v1-failure/independent-report.json)のとおり、compile・extract成功後の最初のprobeが終了コード91で停止した。全3回はtimeoutなし・stderr空で閉じた。raw stdoutは `PIPELINE 0 8 2`、allocation receipt、`END 0 0` の3行であり、必須のROOT／FN／SIR／STATE記録がない。想定したsiteの捕捉に入っていないので、容量境界・full M/G状態・算術・codegenのPASSにも反例にも判定しない。残る11ケースは未実行、元の試験は再実行しない。

コンパイラ自己再ビルド10回と、この失敗3回を区別して保存する。次は通常のcheck・refinement・lower後のSIR／FRECを観測する有限診断を別に登録し、実際の形を確認してから新しい成分試験をレビューする。観測のためのguardを広げて旧試験の成功と呼ばない。

[失敗の全内容packet](evidence/coscientist-quotient-two-20261008/state-v1-failure/content.tgz)は1,685,896 B、SHA-256 `9bdfbde1cc2538cceed706c637b190bc6b9fd94da508a0c18c8c4f6bb49dc3af`、36 regular members・39元パス・展開6,578,685 B。凍結ソース・入力producer／loader・有限GO・3回のraw・生成harness・独立失敗監査を保存する。

[失敗packetの独立内容監査](evidence/coscientist-quotient-two-20261008/state-v1-failure/independent-packet-report.json)は36 member・39元パスと独立実監査の37依存を照合した。失敗結果は上書きせず、後続診断と区別して保持する。

## 通常loweringの観測V1

別登録のcompile・extract・observe計3回はすべて終了コード0、stderr空、timeoutなしで閉じた。[独立実監査](evidence/coscientist-quotient-two-20261008/observation-v1/independent-report.json)は通常のcheck・refinement・lower、8 SIR行、2個の全16フィールドFREC、実際に訪問した7命令直前のframe／descriptorを照合した。失敗の原因は試験側の局所slot仮定だった。SIR3のLGETはtemp0へslot1を読み、V1のsite predicateはslot0を要求していた。隣接CONST2・BINquotと命令5への訪問は一致する。これは最適化の算術失敗ではなく、成分試験の捕捉条件の不一致である。

[観測の全内容packet](evidence/coscientist-quotient-two-20261008/observation-v1/content.tgz)は1,685,153 B、SHA-256 `d57c51860baebe9e5f13e1de8cef6812b99cffb949f42abff6494a432c0764da`、46 regular members・49元パス・展開6,592,180 B。自己再ビルド10回、失敗成分試験3回、観測3回の累計16回を区別して保持する。新しい成分試験はslot1の実観測に合わせ、独立source reviewと別の有限GOを必要とする。旧失敗・残り11ケースを再実行しない。成分状態、生成CODE実行、物理register／NZCV、fuel／arena、性能、製品採用の成功はこの観測から主張しない。

[観測packetの独立内容監査](evidence/coscientist-quotient-two-20261008/observation-v1/independent-packet-report.json)は全46 member・49元パス・47実監査依存を照合した。

## 成分試験V2の有限実行

実観測のslot1に合わせた新V2は診断siteとraw validatorの2リテラルだけを変更した。独立修正レビューとroot GOを経て、新規14呼出（compile／extract＋12ケース）が終了コード0・stderr空・timeoutなしで閉じた。[実監査](evidence/coscientist-quotient-two-20261008/state-v2/independent-report.json)はargv・KEXE設定・全KSEED／native・rawの12 schemaを照合した。CODE残り2語では旧経路が成功し、新3語経路が4101を返す、明示した新資源契約の差を実際に確認した。dirty901・register16／alias・17／31 fallbackも登録した結果に一致する。

nativeハーネスは各ケースでfull M／G／CODE／metadata／overall比較を行い、rawではすべての比較flagが1だった。この判定はレビューされたソースに結び付く内部assertionであり、rawへ全メモリをserializeして第三者が再比較した証拠ではない。監査者は旧V1作者であるため、元のoracleの再確認とwidth作者による新slot修正の独立確認を区別して報告した。元V1のroot・width独立source reviewの履歴も保持する。

[全内容packet](evidence/coscientist-quotient-two-20261008/state-v2/content.tgz)は1,990,898 B、SHA-256 `f36943f8f6b59bf88ea23c26a516f71dd435dbb58e32397f14fed1d217eed2c4`、56 regular members・71元パス・展開7,824,297 B。累計は自己再ビルド10＋旧失敗3＋観測3＋新成分14＝30呼出。旧未実行11ケースを流用した計数ではない。これで確認したのはoperand load後のhelper成分だけであり、生成CODE実行、後続protect／fin、物理x17／NZCV、fuel／arena、元19本とCの速度比較、製品採用は引き続き未認定である。

## Typed ordinary-pipeline観測16と構造HOLD

typed fixture3種×OFF／ONのcompile／extract12呼出は全6成果物を生成した。literal2 positiveはnative624→628 B・bench offset20→24で、literal3とruntime-divisorのnegativeは全KSEED／native／exportが一致する。この段階は生成コードを実行していない。

独立SOURCEレビュー済みのreadonly observerを別にcompile／extract4回し、その2 compilerで同じfixtureをcompile／extract12回した。全16子プロセスは終了し、全6観測成果物が既存typed成果物とバイト一致した。チェック済みSIR、FREC、FIX、LIT、実emission範囲とQ2 siteを記録した。[独立実監査](evidence/coscientist-quotient-two-20261008/observer-v2/independent-report.json)はargv／環境・raw・全成果物を確認した。

凍結したoffline構造検査器は全3対でKeyError4によりHOLDとなった。sourceのFIX列挙値はB26=1、BC19=2、CB19=3、BL26=4、LIT32=5、ADR19=6だが、検査器がlabelを1/3/4、functionを2と誤分類していた。実positiveの `[1,95,2,4,0,98]` はLABEL4へのconditional branchで、FREC4ではない。sourceと失敗を保持し、別の検査器修正をレビューする。生成コードの再実行や、失敗を除外した受理はしない。

[全内容packet](evidence/coscientist-quotient-two-20261008/observer-v2/content.tgz)はSHA-256 `a9e88ffe7660ae846e642ec9f985f3e9788f21df613ffa932cf2b33ae72955f8`、4,164,102 B・172 member・245元パス。[独立packet監査](evidence/coscientist-quotient-two-20261008/observer-v2/independent-packet-report.json)は全内容と実監査の243依存ファイル、16呼出の閉鎖、6成果物一致を確認した。CODE+1の実構造認定・CPU/scoped feature・generated guest execution・fuel／arena・runtime register／NZCV・full19性能・採用は未通過である。

## 修正検査器による保存済み3対の再判定

旧HOLDを保持した別V3検査器で、sourceのFIX enumとlabel／function・BL aux・ADR変位を合わせた。独立SOURCEレビュー2件と新しいoffline GO後、保存済み3対に各1回だけ検査器を適用した。[独立offline実監査](evidence/coscientist-quotient-two-20261008/offline-v3/independent-report.json)は全279依存資料、GO／レビュー／source pin、rawから再parseしたmetadata、全CODE／FIX／literal／exportの対応を照合した。

literal2の実typed owner FN1／SIR5、x0→d9の1 siteが、MOVZ17=2／SDIVからADD sign bias／ASR1／MOVZ17=2に対応する。native624→628 B・bench offset20→24で、それ以外の全wordと再配置・exportの対応を確認した。literal3／runtime-divisorのnegativeはQ2 site0、native668／708 Bの全KSEED／nativeが一致した。新native／SSH／再buildは0である。これは保存されたコードの構造検証で、CPU・scoped feature・runtime・NZCV・fuel／arena・性能の認定ではない。

[全内容packet](evidence/coscientist-quotient-two-20261008/offline-v3/content.tgz)はSHA-256 `d8007eb7d411922af0bad90ed94dc8bc658fef6e5b31fac6f73aafe276184c3f`、4,190,503 B・187 member・281元パス。[独立内容監査](evidence/coscientist-quotient-two-20261008/offline-v3/independent-packet-report.json)は全279依存の内容閉包と保存された構造判定を確認した。source作者controlsの内容監査への参加と、root構築・width実監査をreportに明記した。C以上の性能・採用は未達である。

## 保存済み6イメージの命令・context検証

全CODEを合法なA64命令へ分類・再構成するSOURCE検査器を作り、全CFGでprivate context、callback、stack、return状態、fuel区間を追跡した。V1の直線prefixでは分岐後のcallbackを扱えずHOLD、V2ではcallbackの直前の定数設定を分岐が飛び越す改変例を誤受理した。いずれも保存し、V3でcallback setupへの途中入口と、fuel区間への所定の成功辺以外の入口を拒否した。rootとnative_controlsの独立SOURCEレビュー後、保存済み6イメージに1回のoffline実判定を行った。

[独立成果物監査](evidence/coscientist-quotient-two-20261008/features-v3/independent-report.json)は1,001命令のnative／reencoder一致、6個の全container、前段の構造判定との一致、各2 callback・2 fuel区間・1正常return、322依存資料を確認した。rootのtool終了観測と、監査者が独立に確認した成果物／terminalを区別し、独立したOS-level exec traceとは呼ばない。native／SSH／compiler／CLT／guest実行はこのoffline段階では0である。

この判定は正確な6イメージと、信頼するtyped producer、固定したC consumerのCABI、private arena／stackの分離、外部並行書込みなし、trapから再開しないことに条件を置く。任意のguestの配列境界安全性や実行時の全状態の証明ではない。実際のrunner buildとguest機能試験は未実行で、最終feature receiptも別の監査結果合成を待つ。

[全内容packet](evidence/coscientist-quotient-two-20261008/features-v3/content.tgz)はSHA-256 `ebba957e6b288bb5c117fe97350b0bb6e9b1a791cb726ff60056cf5c18e21322`、4,335,966 B・228 member・324元パス・展開18,338,955 B。前段の全内容、SOURCE修正・HOLD・レビュー・GO、今回のoffline成果物と監査を保持する。性能・公式Embenchスコア・C以上の達成・製品採用は認定しない。

[独立packet内容監査](evidence/coscientist-quotient-two-20261008/features-v3/independent-packet-report.json)は全322依存と324元パス・228安全なmemberの一致を、展開・再実行なしで確認した。SOURCE作者widthの監査参加、native_controlsの実監査、rootのpacket構築を区別して記録した。

## feature receipt合成・runner buildとguest実行前の停止

6イメージの条件付きfeature receiptを別のoffline工程で合成し、全342依存とsource/構造/feature判定の一致を独立監査した。これを受けたrunner buildは3ビルドと14ツール識別の計17子プロセスが終了コード0・stderr空で閉じ、3 runnerと6個のembedded native imageが独立監査に一致した。これはbuild成功でありguest実行成功ではない。

次の6 guest呼出しは、実行前の証拠閉包容量検査で停止した。417依存の合計288,615,765 Bが登録上限268,435,456 Bを20,180,309 B超過し、そのうち264,942,528 Bは正確なCLT clang本体だった。失敗terminalは子プロセス0・全閉鎖・failure=trueで保存した。旧guest namespaceを再実行せず、全依存を保持する新しいSOURCE/容量契約/出力namespaceをレビューする。実際のguest fuel/arena、速度、製品採用は未認定のままである。証拠保管の容量契約と、言語・guestのfuel/arena契約は区別する。

## 新領域の6 guest呼出し

証拠読取上限だけを384 MiBへ事前登録した新V3は、全417依存を維持し、fixture／ABI／fuel／arena／期待値／終了処理を変更しなかった。rootとwidthのSOURCEレビュー後、新規領域で6呼出が終了コード0・stderr空で閉じた。[独立raw監査](evidence/coscientist-quotient-two-20261008/guest-v3/independent-report.json)は460依存、6 argv・raw・生成runner・全native/containerとGOを照合した。3 OFF／ONペアは期待mask4095、fuel消費13、terminal arena使用量pairs0／string0／vectors2／items24が一致した。12個の符号付き入力の数学的期待値も独立に確認した。旧0-child停止は上書きしていない。

[保存snapshot](evidence/coscientist-quotient-two-20261008/guest-v3/snapshot.json)は今回のraw・GO・source登録・監査報告と全依存pin表の選択コピーであり、460依存の実バイトすべてを含むportable封印archiveではない。完全な入力は元workspaceに保持される。SOURCEレビューへの監査者widthの参加を明記する。実NZCV／全register状態、原19本、quiet-host性能、公式スコア、C以上の達成、製品採用はこの有限3fixtureの結果からは認定しない。
