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

## Iteration 3 — `#()` fn shorthand (2026-09-04)

- 反証 probe (実装前, iteration 2 lock の kotoba-sema classpath):
  `(mapv #(* % 2) v)` → **reader 段階で REJECT** (`:kotoba/source-read-failed`)。
  nbb kotoba-reader の `#` dispatch は `#{`/`#?`/`##` のみ → 欠落は reader 層のみ。
  展開先 `(fn [x] ...)` は iteration 2 で qualify 済み。速度反証対象なし
  (新 lowering なし) を確認してから実装に進んだ。
- 実装: kotoba-sema branch `bot/lang-fn-shorthand-20260904` @ee4c515
  (kotoba_reader.cljc +~80 行: `read-fn-shorthand`, `%`/`%N` を `p1..pN` に
  rewrite, `%&` と空 body は fail-closed)。Clojure 規約どおり **中身は 1 呼び出し
  form**。合成 form には reader 位置の meta を全 level に付与
  (実測: meta なし / `(do ...)` wrapper は loop typing が exit を `:i64` と
  誤判定し loop-result-type REJECT — 1 call form が正解)。
- gate (JVM-free, nbb wasm_cli route):
  - check `(mapv #(* % 2) v)` PASS, compile --target wasm32 PASS (2134 bytes)
  - **KIR parity**: hand-written `(mapv (fn [p1] (* p1 2)) v)` と definition CID
    完全一致 (`t` @bafyreihrclqjeir7..., `__kotoba_loop_1`
    @bafyreicptlqjvu5hh...)
  - fail-closed: `#()` 空REJECT, `%&` REJECT, `#(+ %2 1)` gap REJECT
    (map 形状 rule が自 span で拒否)
  - regression: nbb run-tests **176 tests / 556 assertions / 0 失敗**
    (新規 kotoba-reader-test 6 assertions を含む)
- comparator 比: 展開先は既存 `(fn ...)` lowering そのもの (parity CID 一致) で
  新規 runtime cost 0。速度閾値は不適用 (pure reader sugar)。
- verdict: parity + fail-closed 済み (iteration 1/2 と同型の qualify相当)。
- 次 (1 hypothesis): `parse-long` (string→i64)。`string-from-i64` は既存なので
  逆方向。jvm-dep-ledger の blocked 実測欠落の中で下流影響が大きい候補。
  まず hand-patch probe: `string-substring`+手書き数字パース loop の lowering が
  既に qualify されるか (既存 op のみで組めるか) を 1 probe で切り分け。

## Iteration 4 — parse-long hand-patch 反証 (2026-09-04, 実装なし = surface alias 不可の結論)

- probe (amu@4257c685 lock, kotoba-sema @ee4c515 classpath, JVM-free):
  - `(parse-long s)` 単独 → subset-reject "operation has no admitted lowering" (実測 再確認)。
    `(:string → :i64)` 逆向き変換の lowering も許可集合にないため parse-long は
    純 desugar では実装できない (iteration 1-3 と決定的に異なる)。
  - hand-patch: 既存 string op のみでの桁パース loop
    `(string-length)` + `(string-code-point-at s i)` + i64 算術:
    - check PASS (`__kotoba_loop_1` @bafyreievvk..., `t` @bafyreifu3i7...)
    - compile --target wasm32 --jvm-free PASS (pl1.wasm, 2079 bytes)
  - 符号対応拡張版 (先頭 +/-, 非数字で 0): check PASS, wasm32 compile PASS (pl3.wasm)。
- 反証 verdict: **既存 op 組み合わせで parse-long と同値の loop は qualify 済み**。
  よって実装経路は 2 択: (a) parser/lowering 層に新 string-parse-i64 lowering を
  追加 (新 backend work, 速度反証が本来必要), (b) stdlib snippet 側で hand-patch
  同型を提供 (compiler 変更 0)。速度面では (a) の intrinsic 化は hand-patch loop と
  同一 lowering になるはずなので、(a) を選んでも速度閾値は新規コスト 0 と予測 —
  次の担当 (実装側) への引き継ぎ情報として記録。
- comparator 比: 未実施 (実装なし、新 lowering なしのため反証対象なし)。
## Iteration 5 — `contains?` on typed map: ledger 記載は stale (2026-09-04, 実装不要の反証)

- probe (kotoba-sema @ee4c515 classpath, amu nbb route, JVM-free):
  現行 sema frontend には `contains?` → `typed-map-contains` の rewrite が
  既に実装済み (frontend.cljc `map-presence-operations`, `rewrite` arm
  `= op 'contains?'`, commit 93790c4「integer and string map keys through the
  friendly surface」時点で降りている)。ledger の REJECT 記載は stale。
  - `(contains? m :k)` / `[:map :keyword :i64]` → check **PASS**
  - `(contains? m 3)` / `[:map :i64 :i64]` → check **PASS**
  - compile --target wasm32 **PASS** (ct1 1942 bytes / ct2 1936 bytes)
  - `(get m :k 0)` も PASS (既知)。
- hand-patch 反証 (2 値 desugar 案 `(not= (get m :k sentinel) sentinel)`):
  check PASS, wasm32 compile PASS (ct4 2004 bytes — native より **+68 bytes**)。
  definition CID は native `typed-map-contains` と別値
  (t @bafyreigvmnfzfyy5... vs @bafyreicrksxcdq2e...) — lowering が異なるため
  parity は成立しない (意味論差: sentinel 衝突で偽陰性の可能性が残る)。
- 反証 verdict: **実装不要** — `contains?` は既に qualify 済み lowering で
  動作し、desugar 案 (sentinel) は bytes 増 + 意味論劣るため採らない。
  「contains? が REJECT」という jvm-dep-ledger 記載の反証が今回の成果。
  jvm-dep-migrator 側に stale 記載の更新を依頼する情報として記録。
- comparator 比: 新 lowering なし (既存 typed-map-contains を確認しただけ)
  のため速度反証対象なし。
- 次 (1 hypothesis): population 表の他の REJECT 記載の stale 再確認
  (`min` / `seq` / `some->` / `keys` / `remove` は 2026-09-03 の型付き
  re-probe 表に未記載。まず `min` が現行 sema で qualify されるか 1 probe)。

## Iteration 6 — `min` / `seq` / `keys` / `remove` / `some->` 一括 re-probe (2026-09-04)

probe 環境: kotoba-sema @ee4c515 (`bot/lang-fn-shorthand-20260904` classpath) +
amu nbb wasm_cli route, JVM-free。数字は全て実測。

- **min: ledger 記載は正しい (REJECT 実在)**。
  `(min a b)` → subset-reject "operation has no admitted lowering"。
  hand-patch `(if (< a b) a b)` → check PASS / wasm32 compile PASS (305 bytes)。
  hand-patch reduce 版 `(reduce (fn [acc x] (if (< acc x) acc x)) 0 v)` →
  check PASS / wasm32 PASS (2017 bytes, loop CID
  `bafyreickegiixyfjcuqstkuibiaqfoh7ef7o54o6up3ri7msjgzelnobje`)。
  → `min` は既存 op (`<`/`if`) への純 desugar で qualify 可能。
  実装候補 (parity 検証は次 iteration)。
- **seq / keys / remove: REJECT 実在** ("operation has no admitted lowering")
  — `(seq v)`, `(if (seq v) ...)`, `(keys m)`, `(remove p v)` いずれも拒否。
  展開先が存在しないため surface alias では解決不可 (実装要)。
- **some->: 部分動作 (新規知見)**。
  - 0-step `(some-> (get m :a))` → check PASS / wasm32 PASS (1930 bytes)、
    definition CID は手書き `(get m :a)` と**完全一致**
    (`bafyreiegx2bnqhijjhxgxi4itycortorg4zwdqzjabofa2m4ziwvfvisl4`) — parity 確認。
  - 1-step `(some-> (get m :a) (+ 1))` は REJECT。desugar-some-thread
    (frontend.cljc:3042) の resolve-option-type (:2984) が `(get m :a)` の
    option 型を解決できず fallback `[:option :i64]` を仮定 →
    "if branches must have the same value type"。型指示 rewrite pass
    (:8501 option-or) では解決できる — `(option-or (get m :a) 0)` は check PASS。
  - hand-patch 代替 `(option-value-of [:option :i64] (get m :a) 0)` →
    check+wasm32 PASS (1975 bytes, CID
    `bafyreihgdputlxvrheeztyj3yhnhvpt5hk6sxmhdydneonad2icsuhpk54`)。
  - 反証 verdict: some-> の連鎖 step は新 lowering ではなく
    resolve-option-type への typed-map get 認識追加 (または option-or 経由の
    型指示 rewrite への desugar 委譲) が最小修正。既存 option lowering への
    委譲のため新 runtime cost 0 予測。
- comparator 比: 新 lowering なし (全て既存 op 展開の確認) のため
  速度反証対象なし。jvm-dep-ledger 側への更新依頼事項:
  `min`=REJECT 是正 (hand-patch で qualify 可能な desugar 欠落)、
  `contains?`=stale (iteration 5)、`some->`=部分 (0-step のみ)。
- 次 (1 hypothesis): `min` 2-arity desugar `(if (< a b) a b)` を実装した場合、
  手書き同形と definition CID 完全一致 (parity) になるかを 1 probe で確認
  (fail-closed の 0/3+ arity も併せて検証)。
