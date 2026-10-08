# Compute／Result／現在の再適用を分ける、小さな追加契約

この案は既存契約の補足である。追加点は **辺の所有者ごとに寄与を置換して集計し直すこと**、その状態更新の冪等性と **毎回必要な admission・消費** を分けることにある。製品の cache 実装、native importer、IPLD encoder、解析省略、性能測定ではない。C2 OFF、キー除外なし、追加省略0を維持する。

既存資料は、canonical 診断の有限 native ケースと意味上の payload／transition の照合を記録している。それは一般の再利用資格ではない。current16／current41 に historical stage6 の `vw-*` query がないという SOURCE 照合を維持する。current7618 を builder に使って historical subject を組む場合も、現在の製品 query を観測したことにはならない。

## 三つの識別

| 識別 | 内容 | 含めないと決める前に必要なこと |
| --- | --- | --- |
| ComputeCID | schema／同一 snapshot／owner、解析器実装、型付き対象と推移的依存、全 read-set と alias・writer・reset 契約、4入口 bound・現在 aggregate・support／poison・work／control、規則群・工程、入力の role／reader／展開ライブラリ、target／ABI、数値・effect・trap・資源意味 | read-role と所有期間の閉包。単なる DefCID や bound だけを完全キーと呼ばない |
| ResultCID | 出力 schema と snapshot scope、owned answer、辺 owner・ordinal・target・param・arity・寄与を保持した順序列、support／poison、意味診断、effect／trap、契約上の論理消費 | ComputeCID、既存集計、絶対 work、global scratch を除ける根拠。出力に影響する値を便宜的に消さない |
| TransitionReceiptCID | 今回の Compute→Result 対応、現在 state の前後、fresh authority／admission、全辺の再適用、caller support／poison、論理消費と実作業 ledger、nonce、完全性／公開証拠 | Result 一致から admission 成功を推定しない。古い権限・終了・資源証拠を流用しない |

ComputeCID は要求内容の content address である。結果正しさを hash 自体が証明するわけではない。Result は要求から独立した出力 identity を持つが、最初は同一 snapshot／出力契約の範囲に留める。モデルの異なる実装 CID→同じ ResultCID は **同じ synthetic payload の符号化対照のみ** で、2実要求の直接解析が同じ答えだった証明ではない。

## 辺ごとの置換と順序の保持

最小の候補は historical `vw-run-fn` mode1 が完全に終了した query の owned summary と、全 outgoing edge の4つの寄与である。`vw-arg-bound` は parameter position、alias、self、既存 callee aggregate を読み、`-1` neutral と `0` unknown を区別する。`vw-shape-functions` は support 低下時に outgoing bounds を poison する。答えだけを保存してこの更新を省くことはできない。

モデルでは `(snapshot, query-owner, output-contract, edge-id)` ごとの寄与台帳を持つ。完全な新回答を検証したら、その owner の **全** 旧寄与を新しい順序列に置換し、他 owner の寄与と宣言した merge 規則で再集計する。同じ回答を二度使っても台帳と aggregate は増えない。寄与が4→10へ変わる例では古い min4を残さない。これは歴史的実装に台帳があるという主張ではなく、再利用に伴う retraction を明示する新設計案である。

同じ target の二辺をまとめず、ordinal／重複／arity を照合する。モデルの min が可換・冪等でも、元の診断・trap・fuel・poison・前後状態の順序まで可換とは扱わない。実装では元順序の前後 trace を direct／shadow／replay で照合し、台帳置換が元解析の更新規則を保存することを別途検証する。途中回答を置換して旧寄与を失わせない。

## 状態更新は冪等でも、再利用が無料とは限らない

fresh Transition は今回の権限・effect・trap・予算と request/state 一致を再確認する。モデルは remaining observable fuel と既存 aggregate を完全要求に保つ。再適用後に変わった状態へ旧要求をそのまま使う負例は拒否する。新しい完全要求の Result が同じ場合だけ、別の Transition を検査する。これを実際のヒットやキー除外の認定とは呼ばない。

モデルでは同じ辺回答の再適用でも契約上の fuel を毎回消費し、同じ nonce の二重適用を拒否する。実コードに対する fuel 値は導いていない。コンパイラ内部 work 上限と観測可能な言語 fuel／課金を別 ledger にする。seal・encode・hash・resolve・lookup・照合・replay・publish・失効／miss／拒否経路の実費用は未測定で、モデル receipt の実費用欄は null である。

## valid-last と下流停止

全 read の所有確認、答え・辺の完全照合、現在 Transition 成功、資源・trap／unsupported 拒否、保存完了を確認してから有効 binding を公開する。部分書込み、未所有 scratch、予算切れ、失敗 Transition、保存 raw の一致だけでは公開しない。root から受けた最新 G4 runtime190 の停止6件も、raw 一致と unbound member ESRCH の admission 拒否を分け、成功 binding へ読み替えない。元の失敗は保持する。この新モデルが実行記録を資格付けることもない。

ResultCID が同じでも、consumer の型・effect・interface・診断・辺・aggregate・poison・権限・予算 read-view を版付きで閉じ、現在 replay 後の値が一致する必要がある。SCC の全構成員・worklist revision・pending 更新が安定しないうちは停止しない。モデルは同じ Result＋変わった poison を停止不可にし、pending SCC／開いた consumer 契約を拒否する。

## 次に必要な証拠

最初の blocker は **正確な historical subject の完全 reader／alias／writer／reset／answer 所有閉包** である。小さな JSON/SHA 対照はこれを解決しない。既存 hit が owned summary を保持している証拠がなければ `SUMMARY_NOT_OWNED` とし、global scratch から回答を捏造しない。current16 と旧 stage6 を混ぜない。

その後の実験は毎回 direct を行う shadow で、owned answer・全辺前後・support／poison・診断・論理消費を独立状態で比較する。失効変異、owner／snapshot／順序／公開／予算の負例を **実 native importer／lookup／admission** に渡す。最後に cold／warm と全費用を測る。Embench 生成コードの実行速度と解析時間短縮は別成果として扱う。製品変更・native／network 実行はこの登録に含めない。

`model.py` の strict sorted JSON＋domain-separated SHA は bounded key/equality の説明用で、IPLD canonical encoding の証明ではない。強制 digest 衝突でも完全 bytes を比較する対照を含む。入力を所有した bytes に封じ、元の mutable alias の変更が別 snapshot になることも確認する。実装では reader が同じ bytes／epoch を読み続けること、外部 writer がないこと、原子 publication が必要である。

V2 は保存 binding に ResultCID を持たせ、lookup で所有した Result の全 bytes から再計算して一致を検査する。V1 の保存 payload 改変検出の欠落を保持し、新版の改変・不完全 binding・欠落 CID の負例で拒否する。旧版の純粋テスト通過をこの新条件の資格へ移さない。
