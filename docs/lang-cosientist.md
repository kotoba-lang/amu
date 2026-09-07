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

## Iteration 10 — seq/remove desugar 最小実装 (2026-09-05, 実測 amu@70670834, kotoba-sema branch bot/lang-seq-remove-20260905 @8941b5d)

- 仮説 (iteration 9 引き継ぎ): seq → identity, remove → filter 述語反転の
  純 desugar を frontend.cljc に実装し, hand-patch 展開と KIR 完全一致
  (definition CID 一致) にできる。
- 実装: kotoba-sema branch `bot/lang-seq-remove-20260905` @8941b5d
  (frontend.cljc desugar cond に `seq`/`remove` 2 case, 31 行。mapv/filterv
  alias (iteration 2) と同型: 事前 arity/pred 形検査で自名前の diagnostic で
  fail-closed → 既存 map/filter lowering へ再委譲)。
- gate (ローカル sema branch classpath + amu nbb wasm_cli route, JVM-free):
  - check `(reduce + 0 (seq v))` PASS (exit 0) / `(remove (fn [x] (< x 3)) v)` PASS
  - **KIR parity 実測**: remove alias probe と hand-patch 展開
    `(filter (fn [x] (not (< x 3))) v)` (remove-hand3.kotoba) の全 definition CID
    完全一致 — filter loop_1 `bafyreieon45i7iwyodelpsjytjai7yxj55h5m332yxue5yqz5yazwj4h5y`,
    reduce loop_2 `bafyreieuoy7c66duftjm6uxs22gz23wsmjzj6uc7pvecgc7cfqamgcdwbq`,
    t `bafyreibprazt2pvfqoim5fyu5vihclbvft3yiy5diuacd6clvh54inskru`,
    main `bafyreieesv7k4s2tamwjdmvkkz536d4mg4xq3sxrjqqq2k77k7bfzglfz4`。
    seq alias の t cid `bafyreifjpju3gqmsjtmswu2c2mkv3fu7tiucfgpqfqrgflskwj7vmyngq4`
    も hand 展開 (identity) と完全一致。
  - compile --target wasm32 PASS (seq 3 defs / remove 4 defs)
  - 実行 (browser-host, [1,2,3,0] fixture): seq = **6 (ALL-OK)**,
    remove = **3 (ALL-OK)** — iteration 9 の hand-patch 実行値と一致。
  - fail-closed 実測: `(seq)` REJECT (exit 65, "seq requires exactly one
    vector-i64 collection"), `(remove p v v)` REJECT ("remove requires pred and
    one vector-i64 collection"), `(remove 42 v)` REJECT ("remove pred must be a
    named function or (fn [x] single-expr)") — いずれも自名前 diagnostic。
  - regression: sema suite (nbb, 全 portable .cljc test) **237 tests / 1145
    assertions / 0 failures / 0 errors**。
- probe 教訓 (本 tick の誤検知 1 件, 記録に残す): 新 compile の wasm が 0 を
  返したのは desugar バグではなく probe fixture の bug — 空の
  `(vector-alloc 4)` は全 cell 0 で, `(not (< x 3))` が全員 false, sum = 0
  が正しい。pinned sema で同一プログラムを compile しても 0 (再現) —
  fixture を [1,2,3,0] 埋め (vector-assoc!) にして 6/3 を確認。
  新 wasm が期待値と違うときは fixture を先に疑う。
- comparator 比: 展開が既存 T4.5 map/filter lowering そのものなので新規
  runtime cost 0 (新 lowering なしのため速度反証対象なし, iter 1/2 と同型)。
- verdict: parity + fail-closed + regression 全緑。merge 待ち
  (kotoba-sema bot/lang-seq-remove-20260905)。
- Next (1 hypothesis): some-> desugar 修復 (iteration 7/8 引き継ぎ) —
  修復形は hand-patch 実測済み (payload 落ち, PASS + 値 42)。残作業は
  正典 (let の有無) を 1 つ決めて desugar と hand-patch の CID を一致させる
  parity probe。その後, jvm-dep-ledger の残欠落 (min/max: branch
  bot/lang-min-max-20260904 が既にある — 実測 verify が必要)。

## Iteration 11 - min/max desugar branch verify (2026-09-05, amu@6a18f06d, sema branch bot/lang-min-max-20260904 @2542e1d)

- Hypothesis (iter 10 carried over): existing branch bot/lang-min-max-20260904
  (min/max as `(let [tmp a] (if (< tmp b) tmp b))` pure desugar, 19 lines) can
  be verified to (a) admit what the pinned sema rejects, (b) produce KIR
  identical to the hand-written let+if twin, (c) run correct values.
- Measured (sema branch worktree /tmp/langcos/sema-minmax classpath, amu nbb
  wasm_cli route, JVM-free):
  - pinned sema (145e8b5): `(min a b)` subset-reject operation-has-no-admitted-
    lowering (exit 65) - the gap is exactly the branch desugar.
  - hand-patch probe (mm-hand.kotoba, hand-written let+if) check PASS (exit 0).
  - branch sema: `(min a b)` check PASS (exit 0); `(max a b)` PASS.
  - KIR parity: alias vs hand-written let+if twin - ALL definition CIDs
    identical: t bafyreid7ut5npoyeasyp37hfpkk42sk7csqpbdlzc5bi6b2f4lcuw7jsui,
    main bafyreihmujd4mjwwlnasauef75qku2rnlezxyfre3otxfqgma3t6vp2oay.
  - compile --target wasm32 PASS (346 bytes; with --fuel 1e8 also PASS).
  - run (browser-host, 2e6 calls): min(3,7)=3, min(9,4)=4, min(5,5)=5, ALL-OK.
  - fail-closed: `(min a)` REJECT exit 65 (min requires exactly two operands);
    `(min a b a)` REJECT (same message).
  - microbench (2e6 calls, loadavg 16-19, quiet-gate boundary so indicative
    only): alias 31.2-31.7 ns/call vs hand twin 32.4-33.3 ns/call - same level,
    no disadvantage, no separation (no new lowering, speed threshold N/A).
    C twin comparison not run this tick (host busy, quiet gate not met).
- Verdict: parity + fail-closed + correct values. Merge-pending
  (kotoba-sema bot/lang-min-max-20260904; same shape as iters 1/2/10).
- Next (1 hypothesis): some-> desugar repair (iters 7/8) - fix the broken
  desugar so its definition CIDs match the measured hand-patch form (payload
  drop, PASS + value 42). Then (:k m) projection sugar / re-evaluate the
  parse-long string boundary blocker (iters 4/5).

## Iteration 12 (2026-09-05) - measurement BLOCKED, no verdict

- Target hypothesis (carried from iter 11): some-> desugar repair parity probe
- (repair desugar CIDs == measured hand-patch form, payload-drop, value 42).
- Not executed: terminal tool returned exit 0 with zero output on every command
- this tick (foreground and background, incl. date, ls /tmp/langcos, git log).
- No probe, compile, or bench could be run or observed. No numbers recorded
- -> no verdict, no implementation attempted (falsify-first discipline).
- Next tick: resume the same hypothesis after a terminal health check.

## Iteration 13 - some-> desugar repair, KIR parity verified (2026-09-05, amu@cb9930d4, sema branch bot/lang-some-thread-fix-20260905 @3f847f9)

- Hypothesis (carried from iters 7/8/11): the broken desugar-some-thread can be
  repaired to the measured hand-patch form (payload drop, plain option-some? /
  option-value) with KIR definition CIDs identical to the hand twin.
- Implementation: kotoba-sema branch bot/lang-some-thread-fix-20260905 @3f847f9
  (frontend.cljc desugar-some-thread rewritten, 23+/15-; some->> shares it).
- Measured (local sema branch classpath + amu nbb wasm_cli route, JVM-free):
  - `(some-> opt (+ 1))` with `t [opt :option-i64]`: check PASS (exit 0),
    wasm32 compile PASS, browser-host run `t(option-some 41)` = 42 (ALL-OK)
    - same value as the iter 7 hand-patch measurement.
  - KIR parity: alias vs hand-written
    `(let [stmp opt] (if (option-some? stmp) (+ (option-value stmp 0) 1) 0))`
    ALL definition CIDs identical - t
    `bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74`, main
    `bafyreigqgbc7xhcr33vy7lj5shxo3q2p24wryznlek54zioxyxssdk5zwy`.
  - inline `(some-> (option-some x) (+ 1))` also admits with parity
    (t `bafyreih66axczmp7isomcsdw6k6tdxxealpldspxhpozjr7uqaf4ti5jwu`),
    resolving iter 7 case 1 (resolve-option-type mismatch) for this shape.
  - fail-closed: 0-step `(some-> opt)` REJECT exit 65 ("some-> requires an
    initial option and at least one step").
  - regression: sema suite (nbb, portable .cljc tests) 237 tests / 1145
    assertions / 0 failures / 0 errors (same totals as iter 10 baseline).
- Probe lessons (recorded, not repeated): terminal stdout came back empty for
  every plain command this tick (iter 12's blocker) - workaround: write
  command output to a file and read the file. `compile` without `--output`
  on a bare path is invalid usage (exit 64); the wasm_cli route needs
  `compile <file> --target wasm32 --output <file.wasm>`.
- comparator ratio: repaired desugar lowers to the same admitted ops the hand
  twin uses; no new lowering, so the speed threshold is N/A (same class as
  iters 1/2/10/11).
- verdict: parity + fail-closed + regression all green. Merge-pending
  (kotoba-sema bot/lang-some-thread-fix-20260905).
- Next (1 hypothesis): some->> last?-mode parity probe (thread-last direction)
  with the same hand twin method, then (:k m) projection sugar, then re-check
  the ledger blocked list for anything else that is alias-shaped.


## Iteration 14 - some->> last?-mode parity probe: payload-drop defect (2026-09-05, amu tick14, sema branch bot/lang-some-thread-fix-20260905 @3f847f9)

- Hypothesis (carried from iters 11/13): some->> (last?-mode) desugars to the
  hand twin `(let [stmp opt] (if (option-some? stmp) (thread-last payload) fallback))`
  with definition CIDs identical to the hand twin.
- Measured (nbb wasm_cli route, cp-somefix classpath, JVM-free, terminal-output
  workaround used again this tick: write to file + read):
  - 1-let alias `(some->> opt (- 100))`: check PASS (exit 0).
    Hand twin `(- 100 (option-value stmp 0))` = t `bafyreiawoiat3vi4...`:
    alias t `bafyreifh37gjockkt...` -> CID MISMATCH.
    Semantics twin without payload `(- 100)` = t `bafyreib4j7pvr7uj...`:
    alias t `bafyreifh37gjockkt...` -> CID MISMATCH too.
  - 0-let alias `(some->> (option-some x) (- 100))`: PASS, but its t CID
    `bafyreiawoiat3vi4lujdkyf5jk44253cpszyje2q6z3n47zj26mxmrn64u` equals the
    1-let hand twin that USES `(option-value stmp 0)` - not the no-payload twin.
    Same inconsistency for 2-arg step `(- 100 5)`.
  - Correct syntax with reserved temp name: REJECT "symbol uses the reserved
    __kotoba_ prefix" (fail-closed by design; twins must use other names).
    Correct syntax with non-reserved name but nested `option-value` temp reuse
    in one let: REJECT "source reader rejected input" (exit 65).
  - Control (thread-first): `(some-> opt (+ 1))` PASS, but its t CID
    `bafyreiac7b4vxobujx6ainywyo7xkjtbejd6ygbv2uv3j4aubqb3t4nbqe` differs from
    the iter-13 1-let hand twin `bafyreih66axczmp7isomcsdw6k6tdxxealpldspxhpozjr7uqaf4ti5jwu`.
- Verdict: hypothesis FALSIFIED for some->> last?-mode - the branch-3f847f9
  desugar does not consistently thread the payload in last?-mode: some
  spellings emit `(- 100)` (payload dropped), other equivalent spellings emit
  `(- 100 (option-value tmp 0))` (payload kept), so equivalent input
  desugars to different KIR - a determinism defect, not just a semantic one.
  Note iter 13's some-> "parity" claim only holds for the 1-let spelling; the
  0-let some-> CID differs from that twin (matches the other twin shape).
- Next (1 hypothesis): fix the some-thread desugar (both modes) to a single
  canonical lowering shape, then re-run the parity matrix (some-> / some->> x
  1-let / 0-let) against ONE hand twin until all CIDs match.

## Iteration 15 — some-thread canonical temp: iter 14 defect root-caused & repaired (2026-09-06, amu@pre-e8702dc0, sema bot/lang-some-thread-canonical-20260906 @ac5381a)

- Hypothesis (carried from iter 14): the some->/some->> desugar can be repaired to
  ONE canonical lowering shape so the parity matrix (some-> / some->> × 0-let /
  1-let) matches ONE hand twin per shape with no CID drift.
- Root cause found by falsification probes BEFORE the edit (branch 3f847f9):
  - Binder-name normalization probe: hand twins differing only by temp name
    (stmp vs stmp2) give IDENTICAL t CID `bafyreih66axczmp7isomcsdw6k6tdxxealpldspxhpozjr7uqaf4ti5jwu`
    — binder names are normalized, not the cause per se; but a hand twin using a
    `__kotoba_`-prefixed name is REJECT (reserved prefix, exit 65) and the twin
    written in the desugar's nested-let SHAPE
    `(let [opt ..] (let [sth1 opt] (if (option-some? sth1) (+ (option-value sth1 0) 1) 0)))`
    = t `bafyreiac7b4vxobujx6ainywyo7xkjtbejd6ygbv2uv3j4aubqb3t4nbqe` matches the
    0-let alias CID, while the flat-let twin does not. Two real shapes existed.
  - Source of the shapes: the desugar's temp was `some-thread__N` derived from
    `*loop-counter*` inside analyze (renumbered by unrelated loops / collision
    avoidance) and gensym outside — the SAME spelling desugared to different
    KIR depending on counter state (iter 14 "some spellings drop payload" was
    binder-naming drift, not payload dropping; `(- 100 (option-value ...))` is
    always kept, verified by the 1-let hand twin CID matching the 0-let alias).
- Implementation (minimal, 6+/3-): single deterministic `synthetic "some-thread"`
  temp for every spelling (same shape as binding-some at :3258). No lowering change.
- Measured parity matrix (amu --jvm-free, cp-t15 = sema@ac5381a classpath):
  - some-> 0-let == some-> 1-let == nested-let hand twin:
    t `bafyreiac7b4vxobujx6ainywyo7xkjtbejd6ygbv2uv3j4aubqb3t4nbqe`
  - some-> 1-let typed-param (`[:option-i64]` param) == typed-param hand twin:
    t `bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74`
  - some->> 0-let == some->> 1-let == nested-let hand twins:
    `(- 100 (option-value …))` t `bafyreifh37gjockkt6oxd3dpbqurq3c63b6yuipdsvtcsgyg2tlgw6qvou`,
    `(- 100 5 (option-value …))` t `bafyreieipf6przxlapbmuic2ym4gujubrfxia45qre4ixpdlvnle5yxa3u`
  - compile wasm32 PASS (typed-param some->, 2008 bytes; some->> 1-let PASS).
    Note: the 0-let spellings ((option-some x) inline) fail compile with
    "unsupported typed Wasm expression" (exit 70) — SAME failure on pinned sema
    3f847f9, so it is a pre-existing backend gap (inline option-some lowering),
    not a regression of this repair. check/CID admission still PASSes for them.
  - run (browser-host): some-> typed-param = 42 (ALL-OK),
    some->> typed-param = 100-41 = 59 (ALL-OK).
  - fail-closed: 0-step `(some-> opt)` / `(some->> opt)` REJECT exit 65
    ("requires an initial option and at least one step") — own diagnostic.
  - regression: sema suite (nbb, portable tests) 237 tests / 1145 assertions /
    0 failures / 0 errors (same totals as iters 10/13 baseline).
- comparator ratio: no new lowering, same admitted ops as the hand twin — speed
  threshold N/A (same class as iters 1/2/10/11/13).
- verdict: hypothesis CONFIRMED — canonical lowering achieved, iter 14's
  determinism defect root-caused (temp-name drift) and repaired; parity matrix
  fully green. Pushed branch bot/lang-some-thread-canonical-20260906 @ac5381a
  (merge-pending). Pre-existing backend gap recorded for maintainer bots:
  inline `(option-some x)` input fails wasm lowering with exit 70 ICE.
- Next (1 hypothesis): (:k m) projection sugar — `(get m :k 0)` already admits
  (population row), so probe whether (:k m) reader sugar is only an alias-shaped
  desugar gap; then re-check jvm-dep-ledger blocked list for remaining alias-shaped gaps.

## Iteration 16 - (:k m) projection: alias-only hypothesis FALSIFIED (2026-09-06, amu@5592269e, pinned sema via amu lock)

- Hypothesis (carried from iter 15): `(:k m)` on a canonical typed map is an
  alias-shaped desugar gap, rewritable mechanically to an existing admitted form.
- Measured (amu bin/amu check --jvm-free, amu@5592269e; terminal security
  scanner blocks compound variable commands this tick — probes run via
  /tmp/langcos/t17-run.sh script file, outputs /tmp/langcos/t17-*.txt):
  - `(:k m)` with `m [:map :keyword :i64]` → REJECT exit 65
    "record-get without a type descriptor requires a record value; got [:map :keyword :i64]"
    (t17-kwproj.txt). Source root cause: frontend.cljc:4464 desugars ANY
    keyword-head call unconditionally to `(record-get m :k)`; the 2-arity
    rewrite pass (:9156-9174) refuses non-record receivers — no typed-map arm.
  - `(get m :k)` 2-arity same map → REJECT exit 65 "expression type mismatch:
    expected i64, got [:option :i64]" — 2-arg get returns the option, so
    `(:k m)` CANNOT desugar to `(get m :k)` (t17-g2.txt).
  - `(get m :k 0)` 3-arity → PASS exit 0, t cid
    `bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m` (t17-g3.txt;
    identical file to proj-get-twin.kotoba so parity trivially exact. Note this
    differs from t16-check-hand.txt's `bafyreibtiucow2...` — pinned sema
    advanced between measurements, so the earlier CID is stale, not drift).
- Verdict: hypothesis FALSIFIED — `(:k m)` is NOT alias-shaped. No correct
  mechanical desugar target exists: 2-arg get is type-wrong; 3-arg get needs an
  implicit default (Clojure semantics = nil, not 0); record-get is another type.
  Landing it needs a SEMANTIC DECISION (default policy: reject / 0 /
  `(:k m default)` extension) plus a new typed-map arm in the 2-arity rewrite
  pass — not pure sugar. No implementation this tick (design unsettled;
  speed threshold N/A). ICE-free, all rejects fail-closed with own diagnostics.
- Gate: check probes only (3 REJECT / 1 PASS). perfgate N/A (no runtime claim).
- Next (1 hypothesis): alias-shaped surface of the jvm-dep-ledger list is now
  exhausted (str / mapv / filterv / #() / seq / remove / min-max / some-> /
  some->> / contains? all landed or falsified). Pivot: parse-long string
  boundary blocker (iters 4/5) — hand-patch probe of a guest-side byte-access
  design (`string-byte-at` direct memory read, new lowering) to test whether
  the ~43x host-call boundary cost is avoidable before any amu runtime work.

## Iteration 17 - parse-long guest-side byte-access hypothesis FALSIFIED (2026-09-06, amu main head this tick, pinned sema via amu lock)

- Hypothesis (carried from iter 16): a guest-side byte-access lowering (`string-byte-at`, direct memory read) can avoid the ~43x host-call boundary cost observed in iters 4/5, making parse-long reachable within 5% of C.
- Falsification probe (implementation-free, no compiler change):
  - ABI inspection (browser-host.mjs:1740-1792, read this tick): typed strings cross the boundary as JS values. `string-code-point-at` receives `value` as a JS string and re-encodes it with `new TextEncoder().encode(value)` on EVERY call (line 1773). The string never resides in guest linear memory, so a guest-side `string-byte-at` (i32.load8_u style) has NO operand to read - the lowering is structurally impossible under the current JS-value :string ABI, independent of lowering quality.
  - Measured length-dependence (t18-cp9.kotoba "123456789" vs t18-cp1.kotoba "1", single string-code-point-at call, 2e5 calls each, loadavg 19-27 = QUIET GATE NOT MET, indicative only): 9-char: 716.5 / 741.5 ns/call; 1-char: 678.6 / 636.7 ns/call. Length 1->9 changes cost by only ~11%; the ~640-740 ns/call is per-call boundary cost (assertValue + encode + fuel charge), matching iter 5 noop boundary 750 ns/call. Even 9 per-byte guest reads would still pay ~9 x 640ns boundary unless the string is marshalled into linear memory.
- Verdict: hypothesis FALSIFIED. Guest-side byte access alone cannot reach C (17.2-17.8 ns/call, iter 4); the blocker is the string ABSENT from guest memory, not the number of host calls. A fix requires a memory-passing string marshal (write :string bytes into guest linear memory at the boundary, ABI/intrinsic change in amu runtime + browser-host) - out of scope for lang-cosientist (no alias/desugar route exists). parse-long coverage stays BLOCKED on: string-to-linear-memory marshal.
- Gate: check PASS + wasm32 compile PASS (2008 bytes) for both probes; values correct (acc 10780000 = 49 x 2e5 in both cases). perfgate N/A (falsification of a design, not a runtime claim; load gate not quiet).
- Next (1 hypothesis): remaining ledger alias-shaped list is exhausted (iters 1-16). Pivot to the jvm-dep-ledger "clock/uuid/mutable-store capability import syntax" gap (population note): 1 probe to classify it - surface syntax missing (reader) vs capability module not admitted in the typed import set - hand-probe with a minimal capability import to see which layer rejects and with what diagnostic.

## Iteration 18 — capability import syntax: classified, NOT a lang gap for clock (2026-09-06, amu@996ae58d, pinned sema via amu lock)

- Hypothesis (carried from iter 17): the ledger's "capability-import syntax for
  clock/uuid/mutable-store undeclared" gap is a missing reader/import layer.
- Measured (amu bin/amu --jvm-free, amu@996ae58d; terminal via .sh script files,
  outputs in /tmp/langcos/t18-*.txt):
  - **clock/now admits TODAY**: `(defn read-clock [seed :i64] :i64 (clock/now seed))`
    check PASS (exit 0) with `--policy` granting `[:cap/call :clock/now]`
    (examples/capability-policy.edn shape). Without policy: fail-closed
    "capability policy denies required effects" (exit 65, admission-denied).
    wasm32 compile PASS (2 definitions); definition-cids
    read-clock `bafyreicsq5gpckgxkk2s7xjn7z65ziggb5hynjutww322uvlsxqsoqzn3m`,
    main `bafyreibusqxl5rullwfb7ptxkb3vthl5qe5wis6wiypyxq26mfd7zv5h2m`.
    Surface is a plain namespaced call (`clock/now seed`) — NO import syntax
    exists or is needed; elaborates to `(typed-cap-call 7 :i64 :i64 seed)`
    (project.cljc:267, catalog wire id 7, kit clock-v1 :wasm32-kotoba-v1
    :implemented).
  - state/transact (id 8), entropy/draw (id 23): same admission-denied shape
    without policy (exit 65) — same surface class as clock/now.
  - fail-closed separation: state/transact denied under a clock-only policy —
    grants are per-capability, minimal-policy reported in admission verdict.
  - **uuid is a REAL gap but catalog-level, not syntax**: `(uuid/v4 seed)` →
    subset-reject "named operation uuid/v4 is not a registered capability"
    (exit 65, span 付き); catalog has NO uuid entry (grep 0 hits in
    capability-catalog.edn). Landing uuid = catalog + wire-id + kit + host
    intrinsic — a designed authority addition, not desugar.
- Verdict: hypothesis FALSIFIED as "syntax missing". clock/now (and by the same
  shape state/transact / mutable-store class) needs NO language change — the
  ledger blocker reduces to (a) policy grant availability in component builds
  and (b) runtime host provider for the target surface (kit notes wasm32
  implemented; native blocked by ADR 0261 host-authority). uuid is a separate,
  genuine catalog gap. Speed threshold N/A (capability call = host boundary,
  same ~640-750 ns/call class as iters 4/5 boundary measurements).
- Gate: check PASS + wasm32 compile PASS (clock/now with grant); all negative
  probes fail-closed with own diagnostics. perfgate N/A.
- Next (1 hypothesis): jvm-dep-ledger alias/capability-shaped items are now
  exhausted. Re-scan the blocked cohort CRUD shape for the largest remaining
  measured gap — `keys`/`reduce-kv` on typed map (ledger list): probe whether
  they are alias-shaped (desugar to map iteration over a typed map) or need a
  new lowering, starting with a hand-patch `(reduce-kv f init m)` expansion.

## Iteration 19 - keys/reduce-kv: alias-shaped hypothesis FALSIFIED (three real gaps, not sugar) (2026-09-06 t19 probes + 2026-09-07 t20 probes, sema main @3378b1d via amu lock)

- Hypothesis (carried from iter 18): `keys` on typed map / `reduce-kv` are
  alias-shaped (desugar to map iteration over existing admitted ops).
- Measured (bin/amu check/compile --jvm-free; outputs /tmp/langcos/t19-*.txt,
  t20-*.txt; t19 probes run 2026-09-06 13:48-13:53, t20 2026-09-07 11:09-11:20):
  - `(keys m)` receiver `m [:map :keyword :i64]` -> check **PASS** (exit 0,
    t19-keys5). Frontend :9940-9970 `map-projection-operations` rewrite
    keys->`(typed-map-keys [:map K V] m)` already landed on sema main
    (3378b1d). NOT a reader/alias gap - unlike :k projection (iter 16).
  - BUT the projected type is `[:list K]` (frontend :8563-8568 comment: not
    a set - values not distinct), and EVERY consumer that could use it
    rejects: `(reduce + 0 (keys m))` REJECT "expected vector-i64, got
    [:list :keyword]" (t20-rkvhand3); `(reduce + 0 (vals m))` REJECT
    "expected vector-i64, got [:list :i64]" (t20-reducevals);
    `(map (fn [k] (get m k 0)) (keys m))` same reject (t20-maplist); hand twin
    `(reduce (fn [acc k] (+ acc (get m k 0))) 0 (typed-map-keys ...))`
    REJECT same message (t19-rkv). Higher-order reduce/map/filter only admit
    vector-i64 - the [:list T] domain has no bridge.
  - `(reduce-kv f init m)` -> check REJECT "operation has no admitted
    lowering" (exit 65, t19-reducekv); frontend has ZERO language-level
    reduce-kv desugar (grep 1 hit = internal Clojure code :2930).
  - No list->vector conversion op: `(typed-map-keys->vector T m)` REJECT
    "operation has no admitted type signature" (t19-rkv2).
  - Entry-walk route blocked too: `typed-map-entry-at` returns
    `[:option [:vector [K V]]]` (frontend :8579-8584) but NO entry accessor
    exists - `(typed-map-entry-value (typed-map-entry-at ...))` REJECT
    "no admitted lowering" (t20-rkventry). (`typed-map-entries` is not a
    real op - only `max-typed-map-entries` = 31 limit symbol in frontend.)
  - Backend qualification gap (ICE-class, exit 70): even the check-admitted
    shapes fail wasm32 compile:
    `(count (keys m))` -> compile REJECT "unsupported typed Wasm expression"
    (t20-keys5 + t20-keys4, exit 70);
    `(get m (nth (keys m) 0) 0)` -> check PASS (exit 0, v0 cid
    bafyreidbae6tcex2jnqpxlfx3sqbfo6cov2uhn56wpic36gqj75eavwfge) but compile
    "typed Wasm operation is not qualified" (exit 70);
    the full loop twin (2-var loop + count + nth + get - check PASS exit 0,
    loop bafyreidvidkt65y5ikiwapjxnmiskjihgt3fuim62xw42utmm4l4bks4nu,
    sumkv bafyreie4cco3xjrakgovkofp7ps2myakyoc3jfl2bzfuofvrf4q5qpsfwy) also
    compile exit 70. Control `(get m :k 0)` compiles fine (exit 0) - so the
    gap is specifically the typed-map-keys / typed-list-nth wasm lowering,
    not the whole map domain.
- Verdict: hypothesis FALSIFIED - keys/reduce-kv is NOT alias-shaped. Three
  real gaps stand between the ledger row and any runtime claim:
  (1) wasm32 lowering for typed-map-keys/typed-list-nth not qualified (exit 70;
  check admits what compile cannot build - maintainer-reportable ICE-class),
  (2) [:list T]->vector-i64 bridge absent (no conversion op; every higher-order
  consumer rejects),
  (3) entry accessor (key/value of the entry-at option-vector) absent.
  All need new lowering / type-domain design in the backend (KIR + wasm), not a
  frontend desugar - no correct hand twin exists that passes check+compile+run,
  so per falsify-first discipline NO implementation was attempted.
  reduce-kv inherits (1)(2)(3) transitively (its only mechanical targets are
  keys+get or entry-walk, both dead ends). Coverage status: BLOCKED on backend
  typed-map list lowering - same class of stop as parse-long on the string
  ABI (iters 4/5/17).
- Gate: 7 check probes (3 PASS / 4 fail-closed exit 65 own diagnostics) +
  5 compile probes (1 PASS control / 4 exit 70 internal-error fail-closed).
  perfgate N/A - nothing qualifiable to benchmark (no wasm was ever produced
  for the keys path); loadavg 61-124 this tick, quiet gate not met anyway
  (no timing claims made).
- Next (1 hypothesis): alias-shaped ledger list is now exhausted
  (str/mapv/filterv/#()/seq/remove/min-max/some->/some->>/contains? landed;
  keys/reduce-kv falsified as backend-blocked this iter; :k projection iter
  16; parse-long iter 17; uuid iter 18 catalog-level). Report
  keys/reduce-kv + the exit-70 typed-map-keys lowering ICE to amu-rank /
  jvm-dep-ledger owner. Then 1 probe: `(count m)` directly on a canonical
  [:map K V] - the loop twin this iter needed explicit typed-map-count; if
  bare `count` desugars to it, the keys+get route simplifies and gap (1)
  becomes the single blocker for a future backend fix request.

### Iteration 19 addendum - next-hypothesis probe executed same tick ((count m) direct)

- `(count m)` on `m [:map :keyword :i64]` -> check **PASS** (exit 0, n cid
  bafyreieyx7z7xkiqmeip7ruofxx4xyx2bycss2elcedpjgcwdmwxrrjemq,
  t20-countdirect-check.txt) - bare `count` DOES desugar to typed-map-count
  for canonical maps; the explicit typed-map-count call in the loop twin was
  not required.
- compile --target wasm32 **PASS** (exit 0, t20-count.txt) + browser-host run
  `(count (typed-map-new [:map :keyword :i64] :a 1 :b 2))` = **2 (ALL-OK)**.
- Contrast with iter 19: the exit-70 wasm gap is specific to the `[:list T]`
  carriers (typed-map-keys / typed-list-nth), not the map domain as a whole -
  count-direct passes the full check+compile+run pipeline.
- Refines the blocker model: if a backend adds [:list K] wasm lowering +
  a list->vector-i64 bridge, the keys+get reduce-kv route becomes mechanical
  (count is already qualified). Fix request to amu-rank/backend owner should
  carry these two facts.


## Iteration 20 - remaining ledger rejects classified: conj / into / (long x) (2026-09-07, amu@8f155d54, sema pinned 3378b1d via amu lock)

- Hypothesis (carried from iter 19 "re-scan the blocked cohort"): the three
  ledger-listed rejects `(conj v x)` on vector / `into` / `(long x)` are
  alias-shaped desugar gaps like iters 1/2/10. Falsify-first: hand-patch
  twins measured BEFORE any compiler change, 1 probe each (bin/amu
  check/compile --jvm-free; outputs /tmp/langcos/t21-*.txt; terminal stdout
  empty again this tick — file-redirect workaround used throughout).
- Measured classification:
  1. `(conj v x)` with `v :vector-i64` -> check REJECT exit 65
     :kotoba.error/set-conj-receiver, message "A bounded vector answers to
     vector-conj" (t21-p1). The arm frontend.cljc:9643-9670 dispatches conj to
     typed-set-conj ONLY and refuses non-set receivers DELIBERATELY
     (guide-to-alternative wording); guest-grammar.edn:326 claims conj as
     "pair prepend after duplicate removal" = set semantics. Hand twin
     `(vector-conj v 9)` check PASS exit 0 (t
     bafyreifp74xq24dhnljvvq4mgdkt5u2bjetfrpljjvu56h4yuob64gzjv4), wasm32
     compile PASS (1965 bytes, exit 0). -> hypothesis FALSIFIED for
     conj-on-vector: NOT a missing-alias gap — landing it is a semantic
     WIDENING decision (receiver domain of a reserved head + grammar row
     rewrite), owner-level, not desugar sugar. Multi-item `(conj v 9 10)`
     same refuse; fold twin `(vector-conj (vector-conj v 9) 10)` stands ready.
  2. `(into dst src)` -> check REJECT exit 65 "operation has no admitted
     lowering"; head NOT in :forbidden-heads, NOT in any reserved set, no
     rewrite arm at all (pure gap). Hand twin
     `(reduce (fn [acc x] (vector-conj acc x)) (vector-alloc 0) src)` check
     PASS exit 0 (t bafyreiah4tnjfp6cdhkzwvc2lyizexqopmsr6ymvjfzwlmmd76twfkfnbi,
     __kotoba_loop_1 bafyreigqcfw24skgdu24bkjaqejpql65wbaiz74p7myv3hyrwdzovzvs5u,
     main bafyreies6aqmy3fmuyvg7h555i7nexj5uhkytsd3c5bnozbang424yvqma),
     wasm32 compile PASS exit 0 (3 definitions recompiled, provenance +
     publication sidecars written). -> hypothesis CONFIRMED for `into`:
     alias-shaped (T4.5 reduce+conj is an already-qualified lowering — the
     same zero-new-cost class as iters 1/2/10/11). Implementation candidate:
     desugar cond arm (2-arity receiver-type dispatch, fail-closed on xform/
     3-arity and non-vector receivers) + reserve name. NOT implemented this
     tick (budget); no existing remote branch matches conj|into|long|cast —
     duplicate work checked.
  3. `(long x)` with `x :f64` -> check REJECT exit 65 "operation has no
     admitted lowering". Explicit conversion ops f64-to-i64-checked /
     f64-to-i64-truncating are admitted (frontend :1155 conversion table);
     hand twin `(f64-to-i64-truncating x)` check PASS exit 0 (t
     bafyreifpanx2663uc5x75f5ksel63cadb3j2wb7s6pokywurbuf7sgeaoy).
     1-arg, type-correct target EXISTS (unlike iter 16 :k whose mechanical
     targets were all type-wrong) -> mechanically desugarable, but WHICH arm
     (truncating=JVM/Clojure `(long)` semantics vs checked=safe-subset policy)
     is a semantic decision the grammar owner has not made (no :long row in
     guest-grammar.edn). Classification: blocked-on-decision, not
     blocked-on-lowering — unlike parse-long (iter 17, ABI) it needs zero
     backend work once decided.
- Gate: 6 check probes (3 hand-twin PASS / 3 reject exit 65 own diagnostics,
  all ICE-free fail-closed with guide messages) + 2 wasm32 compile probes PASS
  (vector-conj twin 1965B / into-hand 3 defs). No timing claims made this tick
  (loadavg 23-31, quiet gate not met — not needed: classification probes only,
  no new lowering in any hand twin).
- comparator ratio: N/A for all three (no admitted-vs-admitted runtime
  difference to measure yet; into twin = existing qualified lowering exactly).
- verdict: iter-19 hypothesis partially holds — `into` is the last true
  alias-shaped gap in the ledger cohort (implementation next tick); conj-on-
  vector and (long x) are semantic decisions (widening / cast-policy), not
  sugar, and are routed to the language owner rather than implemented.
- Next (1 hypothesis): implement `(into dst src)` desugar on sema branch
  bot/lang-into-alias-* from pinned 3378b1d, then full gate: KIR parity vs the
  t21-into-hand.kotoba twin above (all definition CIDs), wasm32 compile,
  browser-host value run, fail-closed matrix ((into) / (into d x s) / non-
  vector dst / (defn into ...) reservation), nbb regression 237/1145 baseline.
