# lang-cosientist — 言語機能×速度 co-scientist 状態正本

規律: 反証が先 / quiet gate / 数字のみ / 捏造禁止。jvm-dep-ledger.edn の
blocked ギャップを実装して速度検証まで持っていく。

## Population (2026-09-03 作成, amu@764a6dba 実測 re-probe)

probe 方法: `amu/bin/amu check <probe> --jvm-free` (/tmp/langcos, 型注記あり
`(defn t [v :vector-i64] :i64 ...)` 構文)。ledger の 2026-09-03 記載は
ty 注記なし probe のため過大評価されていた — 以下は型付き re-probe の実測。

| 機能 | ledger 記載 | 2026-09-03 実測 (型あり) |
|---|---|---|
| 文字列リテラル | rejected | **PASS** (return リテラル / if 分岐) |
| str 結合 | rejected | **PASS 機構あり** (`string-concat`/`string-join` 既存, `str` エイリアスのみ未実装) |
| 文字列 = | rejected | **PASS** (`string=?` 既存; `=` は safe profile で意図的に拒否) |
| count | rejected | **PASS** (vector-i64 型付き, 内部 vector-count へ) |
| reduce | rejected | **PASS** (3-arity, inline fn 含む, zero-charge loop 既存) |
| (:k m) get | rejected | **PASS** (`(get m :k 0)`) |
| mapv/filterv (fn ...) | — | REJECT (要反証: 高階 mapv/filterv が拒否される実測) |
| #() shorthand | rejected | REJECT |
| parse-long | rejected | REJECT (`string-from-i64` はある; 逆向き欠落) |
| contains? on typed map | rejected | REJECT |

## Iteration 1 — str surface alias (2026-09-03)

- 機能: `str` → 既存 qualified `string-concat` のネスト糖衣。新 backend lowering なし。
- hand-patch 反証 (実装前に手書き展開で実測): `(string-concat s "-ok")` は
  check PASS / wasm32 compile PASS → 実装しても速くも遅くもなり得ない
  ( lowering が既に qualify 済み)。実装判断: 純 desugar で KIR 完全一致が担保できる。
- 実装: kotoba-sema branch `bot/lang-str-alias-20260903` @7483822
  (src/kotoba/compiler/frontend.cljc, desugar cond に `str` 1 case, 15 行)。
- gate (ローカル kotoba-sema classpath + amu nbb route, JVM-free):
  - check `(str s "-ok" "!")` PASS, compile --target wasm32 PASS (1973 bytes)
  - **KIR parity**: `(str s "-ok" "!")` と手書き `(string-concat (string-concat s "-ok") "!")`
    の definition CID 完全一致 `bafyreifizx5trdqu3vhvkm5lugnnzle2f44pbdbba746l7ylwtnfibki5q`;
    `(str s "-ok")` == `(string-concat s "-ok")` @`bafyreic6l4wlvonz...`
  - fail-closed: `(str)` REJECT, 非 string 部 `REJECT` (type check 通り), 1-arg は identity
  - regression (JVM compat diagnostics): defdesugar-test 10 tests/19 assertions 0 失敗,
    sema-test 29 tests/219 assertions 0 失敗
- comparator 比: 展開が既存 string-concat そのものなので新規 runtime cost 0
  (clang 同形比は未実施 — 新 lowering がないため速度反証対象なし)。
- verdict: qualify相当 (parity + fail-closed 済み)。速度閾値の問題は今回不適用
  (既存 op の sugar であるため)。
- 次 (1 hypothesis): `mapv/filterv` + inline fn が REJECT なのは許可集合か desugar
  のどちらの欠落かを 1 probe で切り分け (T4.5 reduce と同型 desugar が既に存在
  するので手書き展開 `vector-alloc` + loop で parity probe)。

## Iteration 2 — mapv/filterv surface alias (2026-09-04)

- 反証 probe (実装前, amu@e338008f lock の kotoba-sema): `map` (inline fn, 1 coll)
  check **PASS** (`__kotoba_loop_1` @bafyreicptlqjvu5hh...), `filter` 同様 **PASS**
  (@bafyreigswrxclwt5q...); `mapv`/`filterv` のみ subset-reject
  "operation has no admitted lowering" → 欠落は **alias のみ** (T4.5 desugar は
  既存, 許可集合の問題ではない)。`map`/`filter` lowering は既に eager
  vector-i64 を返すため mapv/filterv は純 surface sugar と判定。
- 実装: kotoba-sema branch `bot/lang-mapv-filterv-alias-20260904`
  (frontend.cljc desugar cond に `mapv`/`filterv` 2 case, 13 行。mapv→map /
  filterv→filter へ meta 保持で再委譲, 先に自前 arity 検査で fail-closed)。
- gate (ローカル kotoba-sema classpath + amu nbb wasm_cli route, JVM-free):
  - check `(mapv (fn [x] (* x 2)) v)` PASS / `(filterv (fn [x] (> x 0)) v)` PASS
  - **KIR parity**: mapv vs map, filterv vs filter の全 definition CID 完全一致
    (loop @bafyreicptlqjvu5hh... / t @bafyreihrc..., filter loop
    @bafyreigswrxclwt5q... / t @bafyreifbrymn7...)
  - compile --target wasm32 PASS (mapv, 2134 bytes)
  - fail-closed: `(mapv f)` 1-arg REJECT (自メッセージ),
    `(filterv p v v)` 3-arg REJECT (自メッセージ)
  - 合成: `(reduce ... 0 (mapv ...))` PASS
  - regression (JVM compat diagnostics): defdesugar-test 10 tests/19 assertions
    0 失敗; sema-test 29 tests/219 assertions 0 失敗
- comparator 比: 展開が既存 T4.5 map/filter lowering そのものなので新規
  runtime cost 0 (新 lowering なしのため速度反証対象なし)。
- verdict: parity + fail-closed 済み (str alias と同型の qualify相当)。
- 次 (1 hypothesis): `#()` shorthand — reader/analyze 層の欠落か desugar 層かを
  1 probe で切り分け。`(mapv #(* % 2) v)` が reader で落ちるなら macroexpand 相当
  の最小 reader sugar; 既存 `(fn [x] ...)` 経由なら pure desugar で #() を展開。
