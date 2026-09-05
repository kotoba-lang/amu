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

## Iteration 3 — #() fn shorthand (2026-09-05, 実測 verify: amu@e3b8c9b5)

- branch: kotoba-sema `bot/lang-fn-shorthand-20260904` @ee4c5155
  (reader 層実装, kotoba_reader.cljc +91 行。未マージ: main に含まれず,
  PR 待ち。前 tick 実装分を本 tick で実測 verify)。
- 実測 (amu --jvm-free, ローカル sema worktree classpath, 2026-09-05 02:07 JST):
  - `(reduce + 0 (mapv #(* % 2) v))` check **PASS** (exit 0), wasm32 compile
    **PASS** (2214 bytes)
  - **KIR parity**: `(mapv #(* % 2) v)` と `(mapv (fn [x] (* x 2)) v)` の
    全 definition CID 完全一致 — t `bafyreidsqpt3jj23...`,
    loop_1 `bafyreicptlqjvu5hh...`, loop_2 `bafyreieuoy7c66duf...`
  - fail-closed 実測: `#()` empty body REJECT (reader, exit 65),
    `#(+ %& 1)` rest REJECT (reader), `#(* %2 2)` gap REJECT
    (subset-reject "1-source map fn requires matching unique parameters",
    span 付き — map 側の拒否で正しく落ちる)
- comparator 比: reader sugar が既存 `(fn ...)` 形へ一対一展開のため
  新規 runtime cost 0 (速度閾値不適用, iteration 1/2 と同型)。
- verdict: parity + fail-closed 済み。merge 待ち (bot/lang-fn-shorthand-20260904)。
- 次 (1 hypothesis): `parse-long` — `string-from-i64` は既存の逆向き欠落。
  hand-patch probe: 文字列→i64 の lowering (loop + digit accumulate) を
  手書きで測り, clang 同形 (atoi 相当) と wasm32 比較して ≥5% 劣勢なら
  実装設計を見直す。


## Iteration 4 — parse-long hand-patch 速度反証 (2026-09-05, amu@55b93e40)

- 仮説: parse-long (文字列→i64) は既存 op (string-code-point-at /
  string-byte-length / 自己再帰 fn / 算術) のみで表現でき, lowering 追加で
  comparator (C 同形) 比 ≥5% 以内に載る。
- hand-patch probe (実装前, 実測):
  - 許可集合確認: /tmp/langcos/parse-long-probe.kotoba (digit? + 自己再帰
    parse-digits + parse-long, 4 定義) — bin/amu check --jvm-free PASS
    (exit 0), wasm32 compile PASS, node + browser-host 実行で
    parse-long("123456789")=123456789 / reject 系 (空/非数字/符号) 全て
    正しく -1 (ALL-OK)。なお 2 変数 loop/recur ((recur (+ off 1) (+ acc ...)))
    は subset-reject「operation has no admitted lowering」→ 1 変数 loop のみ
    admit。acc を引数で運ぶ自己再帰 fn で迂回した (これ自体は言語制限の実測)。
  - fuel: 既定 fuel 512 では 23 回目の呼び出しで trap (unreachable) —
    自己再帰 1 entry = 1 charge (loop helper でないため)。--fuel 100000000
    付きで再コンパイルして計測。
- 速度反証 (手作り bench, 9 桁 "123456789" を 1e6 回 parse, loadavg 7-12):
  - kotoba wasm32-browser (--fuel 1e8): 8.019s → 8.752s / 1e6 calls
    = 8019-8752 ns/call (2 run: 8019, 8752)
  - C 同形 (再帰 parse_digits, zig cc -O3 wasm32-freestanding): 17.2-17.8
    ns/call (2 run: 17165, 17772)
  - 分離比 ~467x / ~492x (≥5% どころか 2 桁以上の劣勢)
  - 内訳分離: 同一 :string param marshal + fuel charge だけで中身が空の
    noop kernel は 750 ns/call — つまり caller 側 JS→wasm :string
    boundary と fuel charge だけで C 比 ~42x。compute 部分 (8752-750)
    でも ~450x。
  - 原因 (実測根拠): string-code-point-at は host import
    (kotoba:typed/string-code-point-at/function) で, host 側は呼び出しごとに
    assertValue (utf8Length 全走査) + new TextEncoder().encode(value) で
    文字列全体を再エンコードする (browser-host.mjs:1767-1791)。
    9 桁 parse = 9 回の host call = 9 回の O(n) 再エンコード + 9 回の
    fuel charge。C は 1 バイト読み (s[off])。
- verdict: hypothesis 棄却 (not-separated, 大差で劣勢)。既存 op の合成で
  parse-long を載せても C 比 ≥5% に全く届かない。実装を進めるなら設計変更が
  必要: (a) 文字列の guest 側バイトアクセス op (memory 直接読み) の新 lowering,
  または (b) host 側 parse-long intrinsic (1 host call で全体 parse)。
  どちらも新 lowering/intrinsic — surface alias ではないので lang 拡張と
  backend 変更を伴う。
- gate: check PASS / compile PASS / 実行結果正し (ALL-OK) は確認済み。
  perfgate qualify は不適 (速度側で棄却)。
- 次 (1 hypothesis): parse-long host intrinsic — (parse-long s) 1 op を
  host 側 1 call で実装した場合の下限 (noop 境界 750ns/call + 1 intrinsic call)
  を hand-patch で測る (既存 intrinsic 呼び出し 1 回のコストを実測して外挿)。

## Iteration 5 - parse-long host intrinsic limit falsification (2026-09-05, amu@db6f9fe1)

- Hypothesis: (parse-long s) as 1 host intrinsic call reduces 9 host calls to 1;

  expected cost = noop boundary (750ns/call, iter 4 measured) + 1 intrinsic call.

- Hand-patch (measured before any implementation): 1 admitted intrinsic host call

  per invoke via (string-split-count s "9"), :string param, O(n) host work

  (/tmp/langcos/hostcall-bench.kotoba, check PASS, kernel cid

  bafyreicorll7sibn5gr2id54xhqch7t74xljspp3z3zwta4qcst25wyiku, wasm32 PASS).

- Measured (1e6 calls, "123456789", loadavg 5.2-6.4, 3 runs):

  739.6 / 748.1 / 766.7 ns/call - same as noop boundary 750ns/call (iter 4).

  Host-side O(n) work is marginal; the :string marshal + host-call boundary dominates.

- Verdict: parse-long host intrinsic lower bound ~= 750-770 ns/call vs C 17.2-17.8

  ns/call (iter 4) = ~43x slower. Even 9 calls -> 1 call cannot reach C within 5%.

  Hypothesis falsified (not-separated, ~43x). Fixing this needs boundary-level change

  (guest-side byte access / memory-passing string marshal) - an amu runtime issue,

  not a lang feature. parse-long coverage work stops here (blocked: string boundary).

- Gate: check PASS / compile PASS / sanity split-count("123456789","9")=2 correct.

- Next (1 hypothesis): contains? on typed map - map-contains-i64 host intrinsic

  already exists; probe whether (contains? m k) is only an alias/desugar gap

  (get PASSes already; same-shape desugar is the expected route).

## Iteration 6 — contains? on typed map (2026-09-05, 実測 amu@ef66287b)

- 仮説 (iteration 5 引き継ぎ): `(contains? m k)` は alias/desugar 欠落のみ。
- 実測 (sema main 145e8b5 classpath, amu bin/amu --jvm-free):
  - `(contains? m :k)` with `m [:map :keyword :i64]` → check **PASS (exit 0)**,
    t cid `bafyreib3wdabliqzzkwhv...`; wasm32 compile **PASS** (2 definitions)。
  - frontend.cljc:9244-9263 に `contains?` → `typed-map-contains` rewrite が
    既に実装済み (main にランド済み)。lowering は既存 qualify 済み経路。
  - probe 教訓: receiver 型注記が裸 `:map` なら `map-presence-receiver` で
    正しく fail-closed (canonical `[:map k v]` が必要)。entryless file は
    "entryless library requires an explicit non-empty namespace export list"
    で拒否 — probe には `(defn main ...)` が必要。いずれも正しい拒否。
- verdict: hypothesis 棄却 — **欠落ではない** (既に実装済み)。速度反証対象なし。
  jvm-dep-ledger の contains? 記載は 2026-09-03 時点の古い実測と判断
  (ledger 更新は amu-rank / jvm-dep-migrator へ)。
- gate: check PASS / wasm32 compile PASS。perfgate は不適 (速度反証対象なし)。
- Next (1 hypothesis): `some->` — reader/macro 層の欠落か desugar 層かを
  1 probe で切り分け (既存 `option-some?`/`option-value` lowering 経由の
  純 desugar で parity が取れるか)。`seq`/`remove` は後続。
## Iteration 7 — some-> (2026-09-05, 実測 amu@8ebb3426)

- 仮説 (iteration 6 引き継ぎ): `some->` は reader/macro 層の欠落か desugar 層かを
  1 probe で切り分け (既存 option lowering 経由の純 desugar で parity が取れるか)。
- 実測 (sema main classpath, amu bin/amu --jvm-free, 2026-09-05 JST):
  - frontend.cljc に `desugar-some-thread` が**既に実装済み** (:3190-3209, :4933)。
    しかし以下の 4 形すべて check REJECT / 1 形 ICE (exit 70):
    1. `(some-> (option-some x) (+ 1))` → "expression type mismatch: expected
       [:option :i64], got option-i64" (resolve-option-type が裸 option-some
       の monomorphic `:option-i64` を解決できず legacy `[:option :i64]` を
       挿入, それが -of 系 generic op の要求と衝突)
    2. `(option-some-of :i64 x)` 直接 → **ICE** `internal-operation/option-some-of`
       (exit 70, fail-closed ではあるが ICE は品質問題)
    3. `(some-> opt (+ 1))` with typed param `[:option :i64]` →
       "if branches must have the same value type" — **desugar の構造的欠陥**:
       then 枝は threaded payload (i64) を返し, else 枝は `option-none-of` を
       返すため then/else 型が必ず不一致。1 step も then を option に包み直さない。
    4. main 経由で戻り値を `[:option :i64]` にしても同 3 と同じ reject。
  - hand-patch (正しい lowering 形, 実装前に実測):
    `(if (option-some? tmp) (+ (option-value tmp 0) 1) 0)` — check **PASS (exit 0)**,
    t cid `bafyreihietdwlgkm3fzcj...`; wasm32 compile **PASS**; browser-host 実行で
    `t(option-some 41)` = **42** (ALL-OK)。
  - 教訓: `(some-> opt f)` の正しい desugar は現行実装の
    `(let [tmp ..] (if (option-some?-of T tmp) (threaded payload) (option-none-of T)))`
    ではなく payload 落ち `(if (option-some? tmp) (thread payload) fallback)`
    (some-> は option を return しない Clojure 互換。option を返すなら
    別名 some->opt 的 sugar が要る)。
- verdict: hypothesis **部分棄却** — `some->` は「既に実装済み」ではない
  (iteration 6 の contains? と異なり, desugar が存在するが**壊れている**:
  あらゆる入力形で REJECT/ICE になり正しく desugar される入力はない)。
  速度反証対象なし (現行実装は 1 つも admit しないため)。修復が必要な場合の
  実装形は hand-patch で実測済み (PASS + 正しい値)。
  ICE (`option-some-of` exit 70) は compiler 品質バグとして maintainer 系 bot
  への報告対象 (本 bot は lang 機能の反証のみ)。
- gate: hand-patch probe で check PASS / wasm32 compile PASS / 実行値 42 正しい。
  perfgate は不適 (速度反証対象なし)。
- Next (1 hypothesis): `some->` desugar 修復の事前反証 — 正しい形は hand-patch
  実測済みなので, 修復 desugar が hand-patch と KIR 完全一致 (definition CID 一致)
  にできるかを parity probe で確認 (`if-some`/`when-some` desugar :3229-3261 が
  同型の正しい構造 — これを雛形に some-> を張り直す)。その後 `seq`/`remove`。
## Iteration 8 — some-> desugar 修復の事前反証 (parity probe) (2026-09-05, 実測 amu@fc88a4e4)

- 仮説 (iteration 7 引き継ぎ): 修復 desugar (`if-some`/`when-some` 雛形の
  payload 落ち構造) は hand-patch (iteration 7 実測, t cid
  `bafyreihietdwlgkm3fzcj...`) と KIR 完全一致 (definition CID 一致) にできる。
- 実測 (sema main 145e8b5 classpath, amu bin/amu --jvm-free, host busy
  load1 23.47/10CPU — quiet gate 不成立のため timing 計測は行わず check /
  compile / 実行結果のみ):
  - 修復 desugar の生成物シミュレーション (手書き展開, `let` + `if` +
    `option-some?` + `option-value` payload 落ち, /tmp/langcos/
    some-desugar-sim.kotoba) — check **PASS (exit 0)**, wasm32 compile
    **PASS** (2008 bytes), browser-host 実行 `main() = 42` (**ALL-OK**)。
  - **KIR parity 実測**: シミュレーション展開の t cid は
    `bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74`。
    iteration 7 の hand-patch (`(if (option-some? tmp) (+ (option-value tmp 0) 1) 0)`
    直書き) の t cid は `bafyreihietdwlgkm3fzcj...` — **CID 一致しない**
    (let binding の有無が definition identity に入るため)。
    → 修復 desugar は let を導入せず `(if (option-some? opt) (thread
    (option-value opt 0)) fallback)` を **opt を複写して** 直接組み立てる
    (option-form が pure な場合) か, let 込みの identity を desugar 契約の
    正典として hand-patch 側も let 込みに揃える必要がある。どちらでも
    parity は取れるが, **正典 (canonical) を 1 つ決める作業が残る**。
  - 2 call 合成 probe (some-desugar-sim2.kotoba, option-some 41 と
    option-none) — check PASS (exit 0), t cid は 1-call 版と一致
    (`bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74` —
    t の identity が呼び出し側に非依存で安定することも実測)。
  - 教訓 (fail-closed 再確認): `__kotoba_` prefix の手書き binding は
    "symbol uses the reserved __kotoba_ prefix" で正しく拒否される
    (exit 65, span 付き)。synthetic 名の正典は desugar 側のみが生成できる。
- verdict: hypothesis **部分確認** — 修復 desugar の lowering 形自体は
  admit + 正しい値 (42) で動くことを実測。ただし hand-patch との CID 完全
  一致には let の有無 (正典の選択) が必要で, 現行 `desugar-some-thread`
  (:3190-3209) の option-none 落ち構造が型不一致を起こす根本は iteration 7
  実測の通り。修復は「payload 落ち + 正典 let の有無を決めて hand-patch を
  揃える」1 作業として実装可能 (lang 拡張, backend 変更不要)。
  host busy につき速度閾値は不適用 (純 desugar のため新 lowering なし)。
- gate: check PASS / wasm32 compile PASS / 実行値 42 正しい (ALL-OK)。
  perfgate は不適 (速度反証対象なし)。
- Next (1 hypothesis): `seq`/`remove` — `(seq v)` と `(remove p v)` が
  既存 op (vector-count / eager filter 等) の desugar で載るか, 1 probe で
  切り分け (mapv/filterv と同型の alias/desugar 欠落か, lowering 欠落か)。
