# C1: shapeのみのnative shadowを最小化する提案

ソース提案のみ。native・build・SSHは0件。現在のC0と製品コードを変更しない。shared importer、永続cache、graph mutation、解析の省略、早期停止は実装しない。ここで示す関数名とcodecは新規提案であり、現在のAPIではない。

## 実在する接続点

- frozen `analysis.kotoba` の `vw-run-fn` はmode1の直接計算、`vw-memo-capture` はedge別・4 parameter別の最小寄与、`vw-memo-replay` はfresh/current aggregateへのmeetを実装する。`vw-call` は4entry boundsに加え、callee effect/purity2・alias4・return5を読む。4boundsだけを新しいComputeCIDにしない。
- `gn-op`/`gn-sir`/`gn-fnf` はcounted SIR/FREC、`vw-f`/`vw-e` は16word summaryと4word edgeを読む。ordinalは同じsnapshot内でbody/type/callsite/target/arityが一意に解決できた場合だけ参照に使う。
- `tools/kexe_loader.c:7295` の `hash_sha256_provider` はstring handleの**実際のUTF-8 byte列**をSHA-256し、64文字のlowercase hexを返す。wire3のgrantが必要。既存compiled loaderと現在のCソースが同一由来かは別receiptで束縛する。sourceの存在だけでは現在のloaderでnative hashを実行した証拠にならない。
- `io-multiformats/src/multiformats/base32.cljk:80` は型付きvector-i64→lowercase base32の実装。`core.cljk:386` のCID組み立てはhost形のgeneric APIであり、そのまま現在のunityにnative callableな関数があるとは言わない。
- `definition_identity.cljk` はchecked KIR・alpha normalization・dependency/SCCの別契約。これをSIRのordinalへ橋渡しするnative resolverは未実装。初期C1のsame-exact-snapshot参照にはそのrename/cross-snapshot bridgeを必須にしない。

## 最小codec

任意binaryをstring hashへ無理に渡さず、payloadをASCIIに限定する。例としてdomain/schemaを固定し、各sectionに固定tag・固定順序・countを付け、各i64をtwo's-complementの**16桁lowercase hex**で出力する。空sectionもcount0で存在させる。文字列の自由入力は初期schemaに入れず、evaluator/config/target/ABI等は登録済み識別値・digest32bytesとversioned定数で表す。未登録値、bool/floatの代用、重複section、余剰byte、非正規表現は拒否する。

`SnapshotCID`、`ComputeCID`、`ResultCID`は別domain/versionを持つこの正規ASCIIの**CIDv1 raw**にする案が最小。hash後の32bytesへ `[0x01 0x55 0x12 0x20]` を前置し、全36bytesをbase32し、multibase `b`を付ける。これは正当なraw codecのCIDであり、DAG-CBORを名乗らない。定義のDefCIDと既存DAG-CBOR契約は変更しない。SHAhex64を単にCIDと呼ばない。

encoderはallocation前に全lengthを足し、count×16等をoverflowなしで検査する。snapshotWords8192とencodedBytes131072は独立の上限であり、8192wordsをhex化するとheaderの余地がない。したがって両方を満たさない最大入力は拒否する。実際の5fn fixtureでも測らず収まると断定しない。CIDの36byte/base32は既存純粋typed実装の限局port候補で、source reviewとknown vectorsを通すまで未実装。

## snapshot、request、resultの順序

1. 現在のordinary checked/lowered fixtureとphase4 effect・phase5 aliasをそのまま使う。FN8/edge16/SIR512をallocation前に検査する。C1 observerはdefault OFFで、C0がhitする場合もshadow側は必ず`vw-run-fn(...,candidate0,mode1)`を直接計算する。shadow出力をlive optimizerへ戻さない。
2. counted SIR全4word/FREC全16word、fn summaries全16word、widths、previous-round bounds、typed parameter mapping、effect/alias/return/support/poison、public/private/escape/roots、edge/call mappingをcompact独立scalar snapshotへコピーする。work/residual/admission contractも含める。queryが読むLABEL/outgoing indexはSIR/edgesからの再構築と現在値の照合が必要。8193wordのLABEL table全体を8192word seal内へ無断で入れない。読み得るlabel referencesの一意性・ownershipと再構築証明がない間はHOLD。
3. seal後に全sectionのcount/type/boundsを検査し、canonical bytesを作り、実hash/CIDを付ける。参照は `(SnapshotCID,FN ordinal)` または `(SnapshotCID,caller,callsite,target,base,arity)`。同じcanonical snapshot bytesに再照合してからtyped一意resolverで解決する。activation pointer、G offset、未束縛FN番号は輸入しない。same-snapshot CIDはrename耐性を作らない。
4. direct queryを必ず実行する。full direct transitionとmin captureの順序は元実装のまま。edgeごとの4値すべてを昇順で取り、複数provisional visitsのmeetを保持する。neutral−1は寄与なし、unknown0はゼロへのmeetで別物。supported・poison・refusal・semantic diagnostics・contract-observable charge/effect/trapをResult payloadに含める。partial/refusal/unsupportedは診断だけでsuccessful mappingを発行しない。
5. decodeしたresultを**別のfresh−1 callee aggregate**へtyped references解決後にreplayする。同じfresh初期値で計算したdirect aggregateと全fn×4fieldを比較し、support/poison/診断も一致させる。live aggregateが既にmeet済みなら、fresh replayの最終値をlive最終値と直接同一視しない。保存したpreaggregateへdecoded contributionをmeetし、live direct transitionとの比較も別に必要。
6. result/hash対応はC1のdirect comparison receiptとしてのみ発行する。CAS hash確認はbytesの同一性であり、Compute→Resultの正しさ・trustの証明ではない。C2までどんなmatching CIDも計算を省略しない。

## 実装前に解消する具体的HOLD

現在のread footprintはqualified extractorではない。`vw-call`のcallee summaries、`vw-label`のpersistent index、`vw-out-checked`のheads/links、`vw-width-at`、control admissionを含むtransitive closureとwrite interferenceを実sourceで列挙しなければ「complete sealed snapshot」とは呼べない。reset-flowのscratchと出力accumulatorを同じmutable vectorの浅いaliasへコピーする方法も不可。

元native evaluatorは8,388,608要素のflat Mを使う。一方C1 planはsnapshot8192words/diagnostic262144wordopsを登録している。compact semantic snapshotの上限を満たすことと、native Mの独立materialization/copy/zeroコストを満たすことは別。既存typed controlsのfull Mコピーをそのまま262144ops内と呼べない。physical vector pool・copies・allocation/zero costの有限上限を明示したprospective resource appendixが必要。あるいは既存Mを安全に借りる別証明が要るが、shared mutation/dirty restorationを推定で許可しない。ここは現在HOLD。

最小追加source単位は `c1-encode-i64/section/request/result`, `c1-decode-exact`, `c1-raw-cid`, `c1-seal/resolve`, `c1-shadow/replay`。encoder/hash known vectors→complete footprint/resource appendix→isolated same-snapshot seal/resolve→direct/fresh replayの順で独立source reviewする。どれもまだnative implementationではない。7futurecallsの元planは保持し、追加source/guard/capsを凍結してroot GOを受けるまで実行しない。

## 有限の受理条件

positive4、unknown0、preserving-self−1の既存3条件をnativeで保持する。同一canonical requestの反復はbyte/CID一致、context/edge/type/admissionの各変更はrequest変更または拒否、非正規codec・overflow・missing/duplicate・ambiguous reference・partial/poisonは拒否する。decoded fresh resultとdirect結果を全値比較し、ordinary compilation全byte/exportsも一致させる。追加hash/encode/resolve/replayの物理コストは別診断で数え、元`vw-work-cap`/logical charge/50689cleanupを変えない。timingや生成プログラム性能への効果は未検証。
