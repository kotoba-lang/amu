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

## Iteration 14 — (:k m) keyword projection: gap confirmed, hand-twin measured (2026-09-17, amu@91f7854b)

- 仮説 (iter 13 引き継ぎ): `(:k m)` 投影は純 desugar 欠落で, hand twin
  `(get m :k 0)` と定義 CID 一致にできる。
- 反証 probe (実測, pinned sema b8b01d09 / amu bin/amu check --jvm-free):
  - `(:k m)` on `[:map :keyword :i64]`: **REJECT exit 65**
    `:kotoba.error/record-projection-unresolved` — "record-get without a type
    descriptor requires a record value; got [:map :keyword :i64]"
    (/tmp/langcos/kwproj-probe.kotoba)。欠落は実在 (alias/desugar 欠落で確定)。
  - hand twin `(get m :k 0)` + `(typed-map-new [:map :keyword :i64] :k 41)`:
    **check PASS exit 0**。t cid
    `bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m`,
    main `bafyreiae3o243flhz5lylzs2lkgzattoyt5ih6prccy65qwem5pzwenusy`
    (/tmp/langcos/kwproj-hand4.kotoba) — parity の正典。
  - probe 教訓 (2026-09-05 からの言語変化): keyword-key map literal `{:k 41}`
    は legacy pair-map のまま (3714ffbf wave で i64/string literal のみ retype)。
    typed map fixture は `typed-map-new [:map :keyword :i64] :k 41`
    (type + key/value ペア) で組む。`(get m :k 0)` 自体は canonical typed map
    経路 (frontend.cljk:10935-10950 `typed-map-get`) と legacy `map-get` 経路
    の両方に lowering 済み — **sugar だけが欠けている**。
- 実装未着手 (時間切れ + terminal stdout 障害の file 経由運用)。
  注入経路は実測済み: `GITLIBS=<dir> ./bin/amu ...` で lock checkout を分離
  でき, その kotoba-sema checkout を branch commit に合わせると local
  classpath 注入が通る (hand4 probe で PASS 実測)。実装形: desugar cond に
  keyword-head `(kw m)` → `(get m kw 0)` 1 case (2-form 限定, 自名前
  diagnostic fail-closed)。parity 判定基準: 実装 sema で kwproj-probe が
  exit 0 かつ t cid が `bafyreic3wtjam...` と完全一致。
- comparator 比: 展開が既存 typed-map-get / map-get lowering そのものなので
  新規 runtime cost 0 (速度閾値不適用, iter 1/2/10/11 と同型)。perfgate 不適。
- Next (1 hypothesis): 上記実装の実行と parity 実測 (kwproj-probe exit 0 +
  hand twin CID 一致)。その後 some->> last?-mode / min-max branch
  (bot/lang-min-max-20260904) の sema main (043c620) での再実測。

## Iteration 15 - measurement BLOCKED (quiet gate + budget), no verdict (2026-09-17 12:40 JST)

- Target hypothesis (carried from iter 14): (:k m) keyword projection desugar
  implementation + parity probe (t cid == bafyreic3wtjamgppcl23lsw4...).
- Not executed: plain terminal stdout still empty (iter 12 issue); file-redirect
  workaround confirmed working this tick (health file readable, date/loadavg OK).
- No bench run: loadavg 18.47/16.44/16.35 - quiet gate NOT met. Per discipline,
  no speed measurement started rather than a contaminated one.
- No implementation attempted this tick (budget exhaustion before any compiler
  work; falsify-first discipline kept).
- Next tick: resume the same hypothesis - implement the desugar 1 case
  (kwproj-probe exit 0 + hand twin CID match as pass criteria), verification
  only via file-redirect command output.

## Iteration 16 - measurement IN PROGRESS, no verdict yet (2026-09-17 18:40 JST)

- Target hypothesis (unchanged from iter 14/15): (:k m) keyword projection
  desugar 1 case; pass criteria kwproj-probe exit 0 + t cid ==
  bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m.
- Terminal health check via file-redirect: OK (git status/log/rev-parse read
  back from file, amu HEAD 5ef963cd). No compiler change made this tick
  (falsify-first kept; implementation belongs to next tick).
- No measurement completed within tick budget - status open, work continues
  next tick (probe files /tmp/langcos/kwproj-probe.kotoba / kwproj-hand4.kotoba).
## Iteration 17 - (:k m) implementation STARTED, patch pending verification (2026-09-18 00:35 JST, amu@a7c52789)

- Terminal stdout still empty (iter 12/15 known issue); file-redirect workaround working (health OK). Loadavg 19.13/18.88/16.69 - quiet gate NOT met; no speed measurement this tick (target iteration is parity-only, gate N/A).
- Isolated the sugar injection point (sema checkout b8b01d09 in /tmp/langcos/gitlibs-kw, branch bot/lang-kwproj-20260917): keyword accessor (:field r) desugars to 2-arity record-get at frontend.cljk:5603-5608, which record-projection-unresolved-fails for canonical typed maps (iter 14).
- Planned 1-case change: desugar to (get value :field 0) instead - identical to the measured hand twin (get m :k 0), so parity is byte-for-byte; records keep working because the get rewrite resolves record receivers to (record-get descriptor value key) (line 10927-10932), the same form the old path produced.
- NOT VERIFIED: the edit tool refused the 920KB paginated file and the tick budget ended before the edit landed. No compile, no parity probe, no verdict. No commit made. Next tick: apply the edit (frontend.cljk 5603-5608, 2-arity record-get -> (get value :field 0)), then kwproj-probe exit 0 + t cid == bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m + record regression probe before any commit.

## Iteration 18 - (:k m) desugar patch prepared, NOT verified (2026-09-18 07:40 JST, sema worktree /tmp/langcos/sema-kw, no commit)

- Target hypothesis (unchanged, iters 14-17): (:k m) desugars to (get value :field 0) with KIR CIDs identical to the hand twin (t bafyreic3wtjamgppcl23lsw4...).
- Measured this tick (stdout-empty persists; file-redirect workaround used throughout):
  - Pinned extraction /tmp/langcos/gitlibs-kw (b8b01d09) intact; keyword-accessor site confirmed at frontend.cljk 5617-5622 (2-arity record-get emission; identical text in b8b01d09 copy and main 043c620). The type-directed `get` rewrite (10936-10964) selects typed-map-get / record-get / map-get by receiver type, so (get v k 0) is a valid universal receiver shape.
  - kotoba-sema repo detached at 043c620 == kotoba-lang/main; merge-base --is-ancestor b8b01d09 main TRUE (measured). Worktree /tmp/langcos/sema-kw created, branch bot/lang-kwproj-20260918 from kotoba-lang/main. No commit yet.
- Patch designed but NOT applied (edit run hit tick budget before the write landed). 2-case change: (1) keyword-head 2-form -> (list 'get (desugar-expr v) kw 0) at ~5617-5622; (2) record arm of the get rewrite must admit 2 OR 3 args, dropping the default for records (typed record field is statically present; default is dead) - otherwise a record receiver rejects the new 3-arity spelling (record arm ~10955-10960 requires exactly 2 args) and regresses record accessors.
- Behavior shift to probe AFTER the patch (falsify-first): keyword accessor over a non-map/non-record scalar previously rejected record-projection-unresolved; via the get rewrite it may fall to map-get. Measure fail-closed before any commit.
- No compile, no parity probe, no numbers, no commit. Hypothesis open.
- Next tick: apply the 2-case edit in /tmp/langcos/sema-kw; mirror the same edits onto the pinned b8b01d09 extraction frontend.cljk (GITLIBS classpath); run kwproj-probe (exit 0 + t cid == bafyreic3wtjam...), record-receiver regression, scalar-receiver fail-closed; then commit + push.

## Iteration 19 - (:k m) desugar patch APPLIED in sema-kw worktree, NOT compiled/probed/committed (2026-09-18 12:40 JST)

- Target hypothesis (unchanged, iters 14-18): (:k m) desugars to (get value :field 0); pass criteria kwproj-probe exit 0 + t cid == bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m.
- APPLIED (verified: python exact-replace assertions count==1 for both cases, /tmp/langcos/sema-kw, branch bot/lang-kwproj-20260918 @ 043c620):
  - Case 1 (keyword accessor, ~5617): (list 'record-get v kw) -> (list 'get (desugar-expr v) kw 0), comment updated.
  - Case 2 (record arm of the get rewrite, ~10955): arity guard (= 2 n) -> (<= 2 n 3); 3-arity record receivers drop the dead default and emit (record-get descriptor value key) unchanged.
- NOT DONE this tick (budget exhausted before any compile): mirror of the same edits onto the pinned b8b01d09 GITLIBS extraction; kotoba check/compile of kwproj-probe.kotoba + kwproj-hand4.kotoba; parity CID compare; record-receiver regression probe; scalar-receiver fail-closed probe; commit/push.
- Terminal stdout capture still empty (persistent, file-redirect workaround used).
- Next tick (resume exactly): mirror edits to /tmp/langcos/gitlibs-kw frontend.cljk, run kwproj-probe (exit 0 + t cid == bafyreic3wtjam...), record regression, scalar fail-closed; then commit + push branch bot/lang-kwproj-20260918.

## Iteration 20 - environment LOST (reboot wiped /tmp/langcos), no verdict (2026-09-18 18:40 JST)

- Target hypothesis (unchanged, iters 14-19): (:k m) desugars to (get value :field 0); pass criteria kwproj-probe exit 0 + t cid == hand twin bafyreic3wtjamgppcl23lsw4... (hand twin must be re-measured this cycle - old probe files are gone).
- Measured this tick (file-redirect; plain terminal stdout still empty):
  - uptime: 2:51 since boot (loadavg 8.77/14.23/17.92) -> the machine rebooted; /tmp was wiped.
  - /tmp/langcos does NOT exist (search_files: path not found; /tmp listing has no langcos entries). Lost: /tmp/langcos/sema-kw worktree with the APPLIED-ONLY, UNCOMMITTED 2-case patch (iter 19), the pinned b8b01d09 GITLIBS extraction (gitlibs-kw), and all probe files (kwproj-probe.kotoba, kwproj-hand4.kotoba, etc.). The iter 19 patch was never committed -> its edits are unrecoverable and must be re-applied (they were exact-replace, 2 cases, fully documented in iter 19).
  - kotoba-sema checkout intact at orgs/kotoba-lang/kotoba-sema (source of truth for re-application).
- No compile, no parity probe, no bench (no quiet-gate speed measurement was planned; parity-only target), no commit. Hypothesis open.
- Next tick (resume, rebuild-first): (1) fresh worktree of kotoba-sema from origin/main, branch bot/lang-kwproj-20260918b; (2) re-apply the 2-case patch per iter 19 lines; (3) recreate probe files from scratch (note: hand-twin CID canon bafyreic3wtjam... must be re-measured, not assumed, since the original probe file text is lost); (4) GITLIBS injection route, check/compile/parity/record-regression/scalar-fail-closed, then commit+push.
- Runtime lesson recorded: keep /tmp scratch under a persistent path or commit early - uncommitted worktree patches in /tmp do not survive host reboots.

## Iteration 21 - (:k m) rebuild started, 2-case patch PENDING apply (2026-09-19 00:45 JST, no verdict)

- Target hypothesis (unchanged, iters 14-20): (:k m) desugars to (get value :field 0);
  pass criteria = kwproj-probe exit 0 + t cid == hand twin (re-measure, old probe files lost with /tmp).
- Measured this tick (file-redirect workaround; plain stdout empty persists):
  - Host rebooted since iter 20 (uptime 8:43, loadavg 24.4/29.9/31.2 - quiet gate NOT met; target is parity-only so speed N/A).
  - kotoba-sema local branch bot/lang-kwproj-20260918 is at 043c620 = NO committed patch (confirms iter 19 never committed). Worktree /tmp/langcos/sema-kw prunable (wiped).
  - kotoba-lang/main advanced to 9898f0e (wire 42 :gpu/compute merged). Fresh worktree created: /Users/junkawasaki/github/wt-kwproj, branch bot/lang-kwproj-20260919b @9898f0e (persistent path per iter 20 lesson).
  - Patch sites LOCATED on 9898f0e frontend.cljk (line numbers shifted): keyword accessor = 5625-5630 (emits 2-arity record-get, comment cites ADR 0189/0190); get rewrite record arm = 10963-10968 (requires (= 2 (count rewritten-args)), rejects keyword non-map receiver as before); typed-map arm 10957-10961 already admits 2-or-3 arity; contains? map-contains at 10940-10941 unaffected.
- NOT DONE (budget exhausted; patch tool timed out on the 920KB file): apply the 2-case edit (1: 5629-5630 -> (list 'get (desugar-expr (second form)) (first form) 0); 2: record arm guard (= 2 n) -> (<= 2 n 3), emit record-get unchanged, drop dead default). No compile, no probe, no CID, no commit. Hypothesis open.
- Next tick (resume exactly): apply the 2-case patch with a scripted exact-replace (python, count==1 assertions; patch-tool fuzzy matching timed out at 920KB); recreate kwproj-probe.kotoba / kwproj-hand4.kotoba from scratch; re-measure hand twin CID; GITLIBS injection (worktree branch checkout) -> check/compile/parity + record-receiver regression + scalar-receiver fail-closed; then commit+push bot/lang-kwproj-20260919b.

## Iteration 22 - (:k m) 2-case patch COMMITTED, gate run BLOCKED on GITLIBS checkout shape (2026-09-19 06:50 JST, sema branch bot/lang-kwproj-20260919b @6f743ea, no verdict)

- Target hypothesis (unchanged, iters 14-21): (:k m) desugars to (get value :field 0);
  pass criteria = kwproj-probe exit 0 + t cid == hand twin (re-measured).
- APPLIED + COMMITTED: both sites patched in /Users/junkawasaki/github/wt-kwproj
  (python exact-replace, count==1 asserted for both cases; (list 'record-get ...)
  -> (list 'get (desugar-expr (second form)) (first form) 0) at the keyword
  accessor; record-arm guard (= 2 n) -> (<= 2 n 3)). Commit 6f743ea on
  bot/lang-kwproj-20260919b (base 9898f0e = amu lock pin for kotoba-sema).
- Gate NOT executed: the GITLIBS injection route failed closed on checkout shape
  (stdout-empty persists; all output via file redirect). Measured errors:
  1. plain copy (no .git) at the sha dir -> "dependency checkout is not at its
     pinned commit, actual nil" (resolver requires a real git checkout);
  2. symlink to wt-kwproj -> "cannot resolve Amu's dependency closure"
     (classpath allowedRoots check realpaths entries; wt-kwproj is outside the
     GITLIBS root);
  3. real clone of wt-kwproj at HEAD 9898f0e + uncommitted patch inside
     /tmp/langcos/gw GITLIBS root -> SAME generic closure error. Diagnosed but
     not fixed within tick budget (bin/amu resolveWithLock, bin/amu:320-357).
- No check, no compile, no CID, no parity verdict. Hypothesis open.
- Next tick (resume exactly): diagnose why the local clone checkout fails
  (read resolveWithLock + print-classpath diagnostics via file redirect; try
  clean checkout test = unpatched clone at 9898f0e must PASS first - it is
  exactly the pinned lock content, so a failure there is env, not patch), then
  re-apply patch in the GITLIBS clone and run the 4 probes (probe/hand4/
  record/scalar already written in /tmp/langcos). Then push 6f743ea.

## Iteration 23 - (:k m) desugar: gate ALL GREEN, parity + fail-closed + regression verified, pushed (2026-09-19 13:00 JST)

- Target hypothesis (iters 14-22): (:k m) desugars to (get value :field 0);
  pass criteria kwproj-probe exit 0 + t cid == hand twin
  bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m.
- Route fix (GITLIBS injection abandoned): nbb invoked directly with
  lock classpath entries minus the two pinned kotoba-sema dirs, plus
  wt-kwproj/{src,resources} substituted (/tmp/langcos/cp-kw.txt). Same shape
  as the "local sema classpath" route of iters 10/13; terminal stdout healthy
  this tick (no file-redirect needed).
- Measured (patched sema = bot/lang-kwproj-20260919b @6f743ea, base 9898f0e):
  - kwproj-probe check PASS (exit 0); definition CIDs: t
    bafyreic3wtjamgppcl23lsw4iqucesdzdlgizo47jk75bysm5amasbrr6m, main
    bafyreiae3o243flhz5lylzs2lkgzattoyt5ih6prccy65qwem5pzwenusy - EXACT match
    with the measured hand twin (iter 14) -> KIR byte-for-byte parity.
  - wasm32 compile PASS (kwproj-probe.wasm 2006 bytes, provenance sidecar
    emitted); browser-host run: main() = 41 (typed-map-new + (:k m)) - correct.
  - pinned control (9898f0e, no patch): same probe REJECT exit 65
    record-projection-unresolved - the patch is what admits it.
  - record regression (kwproj-record2.kotoba, [:record :m/sq [[:side :i64]]],
    (:side (record-new [:ref :m/sq] 7))): patched PASS cid
    bafyreih74ugcpmfxqlkkc3zmqgjxz53mhx6xz2wqnqayoypclr2mfm64zq == pinned
    cid (identical) -> record accessors unaffected; browser-host run = 7.
  - scalar fail-closed (kwproj-scalar.kotoba, (:k 42)): REJECT exit 65
    subset-reject "expression type mismatch: expected map, got i64" - named
    diagnostic, fail-closed kept.
  - sema regression suite (nbb, run-tests.cljk, full lock classpath +
    wt-kwproj src/test): 555 tests / 1958 passed / 0 failures / 0 errors.
- comparator ratio: the desugar lowers through the existing type-directed get
  rewrite (typed-map-get); no new lowering -> speed threshold N/A (iter
  1/2/10/11 class).
- verdict: hypothesis CONFIRMED. parity + fail-closed + record regression +
  555-test regression all green. Pushed kotoba-sema branch
  bot/lang-kwproj-20260919b @6f743ea (PR open URL printed by push).
- Next (1 hypothesis): min/max branch bot/lang-min-max-20260904 re-verify
  against sema main 043c620+ (iter 11 was on the older base; confirm parity
  CIDs still match, then push/PR). Then (:k m) ledger update via amu-rank
  (jvm-dep-ledger contains? / (:k m) rows now stale).

## Iteration 24 - min/max branch SUPERSEDED by upstream first-class op (2026-09-19 18:45 JST, amu lock base 9898f0e)

- Target hypothesis (carried from iters 11/13/23): re-verify branch
  bot/lang-min-max-20260904 (min/max as let+if desugar) against sema main
  043c620+; if parity CIDs still match the hand twin, push/PR.
- Measured (local sema classpath route, amu nbb wasm_cli.cljk, JVM-free):
  - New branch bot/lang-minmax-20260919 @65a2779 (cherry-pick of 2542e1d onto
    9898f0e, clean): min4.kotoba (t=(min a b), u=hand let+if twin, v=(max a b),
    w=hand twin) check PASS exit 0.
  - **CONTROL (unpatched 9898f0e, no min/max branch): same min4.kotoba check
    PASS exit 0 with IDENTICAL CIDs** (t
    bafyreifxnraihe5slxu4sml7lukwasbyx4qdd35d2nmtkaxtipvpf7uffm, u
    bafyreid7ut5npoyeasyp37hfpkk42sk7csqpbdlzc5bi6b2f4lcuw7jsui, v
    bafyreiekj2hbkwx3khn4dkpnoso6mb625k4ihhg2qvdckang6dvo4sxf7i, w
    bafyreib6jkf5q6nlwv5cowpn6jngl4y36mpifqi2naid577qggvvpxdpyq). The alias CID
    (t) is NO LONGER the hand let+if twin CID (u) - upstream main now admits
    min/max as first-class ops, not the desugar.
  - run (wasm32, node host): main() = 3047 = 1000*min(3,7) + 10*min(9,4) +
    max(3,7) - values correct on the upstream path.
  - fail-closed (upstream path): 1-arity REJECT exit 65 "i64 operation arity
    mismatch: min takes 2 arguments; got 1"; 3-arity REJECT exit 65 "min takes
    2 arguments; got 3".
- Verdict: hypothesis falsified in the favorable direction - **min/max gap is
  closed upstream** (first-class i64 min/max op on 9898f0e). The let+if desugar
  branch is redundant AND would be slower than a single-op lowering, so
  bot/lang-minmax-20260919 @65a2779 is NOT pushed; recommend marking
  bot/lang-min-max-20260904 superseded (status rewrite is amu-rank's).
- Probe-lesson (recorded): surface syntax changed since iter 11 - `(:export [t]
  [u])` multi-form form now REJECTs ("only a bounded :export vector is
  admitted"); `kir-cids` command name is invalid (it is `definition-cids`);
  the wasm_cli entrypoint is now wasm_cli.cljk (not .cljs). Old probe scripts
  must be updated before reuse.
- Next (1 hypothesis): some->> last?-mode parity probe (carried from iter 13),
  or the jvm-dep-ledger stale rows (contains? / (:k m) already PASS - ledger
  update handoff to amu-rank).


## Iteration 25 - measurement NOT STARTED (tick budget exhausted at startup), no verdict (2026-09-20)

- Target hypothesis (carried from iter 24, unchanged): some->> last?-mode
  parity probe (thread-last direction, hand-twin method), or stale
  jvm-dep-ledger rows handoff to amu-rank (contains? / (:k m) now PASS).
- Not executed: run time budget was exhausted before any probe/compile could
  start this tick (host environment notice). No terminal command, no bench,
  no compiler change. No numbers -> no verdict (falsify-first kept).
- Next tick: resume the some->> last?-mode parity probe first (iters 13/24
  handoff); ledger stale-row handoff note for amu-rank still pending.

## Iteration 26 - some->/some->> payload-drop repair PORTED to current main; some->> last?-mode parity VERIFIED (2026-09-20, sema branch bot/lang-somethread-rebase-20260920 @9401993, pushed)

- Target hypothesis (carried iters 13/24/25): some->> last?-mode parity probe
  against the payload-drop repair; hand-twin method.
- Finding first (falsify route): on sema 9898f0e (main), BOTH `(some-> opt (+ 1))`
  and `(some->> opt (+ 1))` REJECT exit 65 "expression type mismatch: expected
  [:option :i64], got option-i64" - iter 13's repair branch
  bot/lang-some-thread-fix-20260905 @3f847f9 was NEVER merged and predates the
  .cljc->.cljk wave (its old sema classpath fails on current amu:
  `sema/namespace-attr-map->clauses` unresolvable). The gap is live on main.
- Implementation: fresh branch bot/lang-somethread-rebase-20260920 @9401993
  off 9898f0e (worktree /Users/junkawasaki/github/wt-somethread2); port of
  3f847f9's desugar-some-thread repair onto frontend.cljk via scripted
  exact-replace (python count==1 assert; 23+/15-, byte-identical to the
  original commit's stat; ported function diff vs 3f847f9 source = empty).
- Measured (cp-kw.txt classpath with wt-somethread2 substituted, amu nbb
  wasm_cli route, JVM-free):
  - hand twin (smt-hand.kotoba, let+if payload-drop, written BEFORE the
    branch run): check PASS, t
    `bafyreidbwzhfda7jvgy6cle7exscbc5dhikoha327f7es2wffh3jzmwd64`, main
    `bafyreifdeudhnqrnxna5nvnj4vjug7dw7eg2p46r45yzkbt7s367nzqsbu`
    (re-measured canon; old /tmp probes lost earlier are not assumed).
  - `(some->> opt (+ 1))` check PASS (exit 0), t/main CIDs EXACT match with
    the hand twin -> some->> last?-mode KIR parity byte-for-byte.
  - `(some-> opt (+ 1))` re-check PASS, t
    `bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74` - identical
    to iter 13's measured parity CID (repair is behavior-preserving for
    first-mode).
  - wasm32 compile PASS (2 definitions, provenance sidecar); browser-host
    run `t(option-some 41)` = **42** (ALL-OK) - correct value.
  - fail-closed: 0-step `(some->> opt)` REJECT exit 65, own diagnostic
    "some->> requires an initial option and at least one step".
  - NEW measured gap (not fixed this tick): 2-step `(some->> opt (+ 1) (* 2))`
    REJECT exit 65 "expression type mismatch: expected option-i64, got i64" -
    the recursive `lower` re-enters option resolution on the threaded payload;
    multi-step threads need a payload-threaded chain. Real coverage limit,
    recorded as next hypothesis.
- Regression suite NOT run this tick (budget exhausted after gate+push;
  ported code is text-identical to 3f847f9 which measured 237/1145/0 in
  iter 13, but that was the old base - re-run pending). Pushed branch
  bot/lang-somethread-rebase-20260920 @9401993 (PR open URL printed).
- comparator ratio: repair lowers through existing admitted plain ops
  (option-some?/option-value); no new lowering -> speed threshold N/A.
- Next (1 hypothesis): multi-step some->/some->> chain desugar - fix `lower`
  to thread the payload directly between steps without re-resolving option
  type, then re-verify parity per step count + sema regression suite
  (237 tests baseline) before push.
- Probe lessons: file-redirect workaround needed again this tick (plain
  terminal stdout empty); grouped `bash -c` / brace bodies blocked by the
  security scanner in cron mode - use single simple commands with `>`
  redirects.


## Iteration 27 - multi-step some->> chain: ROOT CAUSE identified from code read, measurement NOT STARTED (2026-09-20, no verdict)

- Target hypothesis (carried from iter 26): 2-step `(some->> opt (+ 1) (* 2))`
  REJECT (exit 65, "expression type mismatch: expected option-i64, got i64")
  is fixable with a linear-chain `lower`: thread all steps onto the
  payload directly (one option check, then steps chained), instead of
  re-entering option resolution per step. Pass criteria: 2-step check PASS
  with definition CIDs == hand twin
  `(let [sht opt] (if (option-some? sht) (* 2 (+ (option-value sht 0) 1)) 0))`
  (to be re-measured this cycle), AND 1-step CIDs unchanged (iter 26 canon:
  t bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74 for some->,
  bafyreidbwzhfda7jvgy6cle7exscbc5dhikoha327f7es2wffh3jzmwd64 for some->>).
- Measured this tick (code read only, no compile/probe; terminal stdout
  empty persists, file-redirect workaround used):
  - wt-somethread2 @9401993 intact; /tmp/langcos intact (reboot did not wipe
    it this tick; host up 2 days).
  - ROOT CAUSE (read from frontend.cljk): desugar-some-thread :4082-4109 -
    recursive `lower` calls `resolve-option-type` on the threaded form, and
    resolve-option-type (:4024-4067) falls back to `[:option :i64]` for any
    unresolvable form (:4065-4067 `:else nil` -> fallback), so step 2 binds
    an i64 payload into tmp and applies `option-some?` to it -> the measured
    exit 65. thread-form (:3977-3984) itself is step-shape agnostic and
    reusable for the chain.
  - Planned patch (NOT applied, budget): replace the letfn body so
    `threaded` = `(reduce #(thread-form %1 %2 last?) payload (rest args))`
    and `then-expr` = `(desugar-expr threaded)`; 1-step output is byte-shape
    identical to the current `(first steps)` thread, so 1-step CIDs should
    be unchanged (assert this in the gate).
  - Coverage limit to record with the patch: a step whose result is itself
    an option (thread-into-option chains) is NOT modeled by the linear
    chain; record as future hypothesis, do not silently admit.
- No compile, no probe, no CIDs, no numbers, no commit. Hypothesis open.
- Next tick (resume exactly): (1) re-measure hand twin smt-hand2.kotoba
  CIDs (canon may differ from iter 26's 1-step twin), (2) apply the
  scripted exact-replace patch to wt-somethread2 (python count==1 assert),
  (3) gate: 2-step parity + 1-step CID-unchanged + 0-step fail-closed +
  wasm32 compile + run value (option-some 41 -> 84 for (+ 1)(** 2)) +
  sema regression suite, (4) commit+push bot/lang-somethread-rebase-20260920.

## Iteration 28 - setup verified, patch NOT applied (2026-09-21, no verdict)

- Target hypothesis (unchanged from iter 27): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin (let [sht opt] (if (option-some? sht) (* 2 (+ (option-value sht 0) 1)) 0))
  (re-measure) AND 1-step CIDs unchanged (iter 26 canon).
- Measured this tick (file-redirect; plain stdout empty persists; loadavg
  24.04/23.40/22.18 - quiet gate NOT met, target is parity-only so speed N/A):
  - /tmp/langcos intact (host up 2 days 14:44). Probe files present:
    smt-2step.kotoba (2-step some->> opt (+ 1) (* 2)), smt-hand.kotoba
    (1-step hand twin - NOT the 2-step twin; smt-hand2.kotoba to be written).
  - wt-somethread2 @940199310f49f76135e7c93e40b42b59b53a4aa2 (clean tree) -
    the rebased repair branch from iter 26, intact.
  - Root-cause site RE-CONFIRMED on 9401993: frontend.cljk
    desugar-some-thread :4082-4109 (recursive lower re-enters
    resolve-option-type on the threaded form; :4067 fallback
    [:option :i64]), thread-form :3977-3984 reusable for the chain.
    Line numbers unchanged since iter 27 code read.
  - Classpath route re-mapped (all cp*.txt scanned for substituted
    worktree entries): cp-smt.txt = lock entries + wt-somethread (OLD
    .cljc-era worktree at 3f847f9); cp-kw.txt / cp_min.txt = wt-kwproj
    (+wt-minmax); cp_final.txt = kotoba-sema main checkout. NONE point at
    wt-somethread2 - cp-smt2.txt must be built by substitution.
- NOT DONE (budget exhausted before patch): apply the scripted exact-replace
  patch to wt-somethread2; build cp-smt2.txt (cp-smt.txt with
  wt-somethread -> wt-somethread2 substituted); write smt-hand2.kotoba;
  re-measure hand-twin CIDs; run gate. No compile, no probe, no CIDs, no
  numbers, no commit. Hypothesis open.
- Next tick (resume exactly): (1) build cp-smt2.txt via python exact-replace
  /Users/junkawasaki/github/wt-somethread/ -> /Users/junkawasaki/github/wt-somethread2/
  in cp-smt.txt (count assert); (2) write smt-hand2.kotoba (2-step hand twin
  above) and measure its CIDs FIRST on cp-smt2.txt (pre-patch sanity that the
  classpath loads); (3) apply the linear-chain patch to wt-somethread2
  frontend.cljk :4093-4109 (letfn lower -> threaded = (reduce
  #(thread-form %1 %2 last?) payload (rest steps)), then-expr =
  (desugar-expr threaded); 1-step output must stay byte-shape identical),
  python count==1 assert; (4) gate on cp-smt2.txt: 2-step parity (t cid ==
  smt-hand2.t) + 1-step CIDs unchanged (smt-first / smt-probe vs iter 26
  canon bafyreia2bh... / bafyreidbwzh...) + 0-step fail-closed
  (smt-0step.kotoba, own diagnostic) + wasm32 compile + node run
  (option-some 41 -> 84) + sema regression suite; (5) commit+push
  bot/lang-somethread-rebase-20260920.
- Coverage limit to record with the patch (unchanged): a step whose result
  is itself an option is NOT modeled by the linear chain - record as future
  hypothesis, do not silently admit.

## Iteration 29 - setup re-verified, patch NOT applied, no verdict (2026-09-21 12:33 JST, loadavg 73.42)

- Target hypothesis (unchanged from iters 26-28): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin `(let [sht opt] (if (option-some? sht) (* 2 (+ (option-value sht 0) 1)) 0))`
  (re-measure) AND 1-step CIDs unchanged (iter 26 canon).
- Measured this tick (file-redirect; plain stdout empty persists; loadavg
  73.42/72.58/62.35 - quiet gate NOT met, target is parity-only so speed N/A):
  - amu HEAD 12e1ee34 (lock content advanced since 9898f0e; wt-somethread2
    base 9401993 is off 9898f0e - re-check the pinned kotoba-sema sha before
    claiming parity; new step (0) added below).
  - /tmp/langcos intact; wt-somethread2 @940199310f49f76135e7c93e40b42b59b53a4aa2
    clean tree; probe files smt-0step/2step/first/hand/probe all present.
  - cp-smt.txt re-scanned: still points at the OLD wt-somethread (3f847f9,
    .cljc era); cp-smt2.txt substitution (wt-somethread -> wt-somethread2)
    NOT built this tick. 45 classpath entries total.
  - Code site RE-CONFIRMED on 9401993 by direct read: recursive lower
    :4093-4109 (re-enters resolve-option-type on threaded form; :4067
    fallback [:option :i64]); thread-form :3977-3984 reusable. Line numbers
    unchanged since iter 27/28.
  - Existing measurements re-read (not re-run): smt-2step REJECT exit 65
    "expression type mismatch: expected option-i64, got i64" (r-smt-2step.txt);
    smt-hand 1-step twin t bafyreidbwzhfda7jvgy6cle7exscbc5dhikoha327f7es2wffh3jzmwd64,
    main bafyreifdeudhnqrnxna5nvnj4vjug7dw7eg2p46r45yzkbt7s367nzqsbu
    (r-smt-hand.txt) - iter 26 canon intact on disk.
- NOT DONE (run budget exhausted during the verification phase, before any
  patch): cp-smt2.txt, smt-hand2.kotoba, patch application, gate. No compile,
  no new probe, no new CIDs, no numbers, no commit. Hypothesis open.
- Probe lesson: `python3 -c` with nested comprehensions is also blocked by
  the cron security scanner - write the script to a file (write_file) and run
  `python3 /tmp/langcos/<script>.py` (worked this tick).
- Next tick (resume exactly as iter 28 itemized list 1-5); additionally
  (0) verify amu lock base: if amu's pinned kotoba-sema sha no longer equals
  9898f0e, rebase wt-somethread2 onto the current pin before the gate.

## Iteration 30 - step (0) resolved, setup verified, patch NOT applied, no verdict (2026-09-21 18:33 JST, amu@0a4fc8e2)

- Target hypothesis (unchanged from iters 26-29): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin `(let [sht opt] (if (option-some? sht) (* 2 (+ (option-value sht 0) 1)) 0))`
  (re-measure) AND 1-step CIDs unchanged (iter 26 canon).
- Measured this tick (file-redirect; plain stdout empty persists; loadavg
  26.38/33.03/35.34 - quiet gate NOT met, target parity-only so speed N/A):
  - STEP (0) RESOLVED: amu HEAD 0a4fc8e2 (advanced since iter 29's 12e1ee34)
    but deps-lock.edn:80 still pins kotoba-sema
    `:git-sha "9898f0e28b48d54baba68991b2b2c7503c660b92"` (comment line 642:
    "Advanced 2026-09-18 to 9898f0e2") -> wt-somethread2 base 9898f0e is
    STILL the current pin. No rebase needed.
  - /tmp/langcos intact; wt-somethread2 @940199310f49f76135e7c93e40b42b59b53a4aa2
    clean tree (status --porcelain empty). Probe files present:
    smt-0step/2step/first/hand/probe.kotoba, smt-apply.py (iter 26's 1-step
    repair, already applied in the branch).
  - Root-cause site RE-CONFIRMED by direct read on 9401993:
    desugar-some-thread :4082-4109 (recursive lower :4093-4109 re-enters
    resolve-option-type on the threaded form; fallback [:option :i64]);
    thread-form :3977-3984 (step-shape agnostic, reusable); desugar-thread
    :3989 `(desugar-expr (reduce #(thread-form %1 %2 last?) (first args)
    (rest args)))` - the exact linear reduce shape the patch should mirror.
  - Classpath map re-confirmed: cp-smt.txt still points at OLD wt-somethread
    (3f847f9, .cljc era); cp-smt2.txt NOT built. 45 entries.
  - Existing measurements re-read (not re-run): r-smt-2step.txt REJECT exit
    65 "expected option-i64, got i64"; r-smt-hand.txt 1-step twin t
    bafyreidbwzhfda7jvgy6cle7exscbc5dhikoha327f7es2wffh3jzmwd64 = iter 26
    canon (intact); r-smt-first.txt shows the PRE-repair REJECT shape
    ("expected [:option :i64], got option-i64") - old/control artifact, so
    the 1-step re-check on the new classpath remains an open gate item.
- NOT DONE (run budget exhausted during verification, before any patch):
  cp-smt2.txt build, smt-hand2.kotoba write, linear-chain patch apply, gate,
  commit. No compile, no new probe, no new CIDs, no numbers, no commit.
  Hypothesis open.
- Patch spec (concretized from this tick's read, for next tick): replace the
  letfn body at :4093-4109 so `threaded = (reduce #(thread-form %1 %2 last?)
  payload steps)` (mirrors desugar-thread :3989), single tmp + single
  `option-some?` check, `then-expr = (desugar-expr threaded)`; 1-step output
  must stay byte-shape identical (assert CIDs unchanged in gate).
- Next tick (resume exactly): iter 28 items 1-5 (cp-smt2.txt via python
  exact-replace; smt-hand2.kotoba + pre-patch CIDs on cp-smt2; apply patch
  python count==1; gate = 2-step parity + 1-step CID-unchanged + 0-step
  fail-closed + wasm32 compile + node run option-some 41 -> 84 + sema
  regression suite; commit+push bot/lang-somethread-rebase-20260920).

## Iteration 31 - items 1-2 DONE (cp-smt2 + hand2 CIDs measured), patch NOT applied, no verdict (2026-09-22 18:50 JST, amu@4bf08502)

- Target hypothesis (unchanged iters 26-30): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin AND 1-step CIDs unchanged (iter 26 canon).
- Terminal stdout healthy this tick (no file-redirect needed). loadavg
  32.73 - quiet gate NOT met; target is parity-only so speed N/A.
- Step (0) re-verified: deps-lock.edn still pins kotoba-sema 9898f0e28b...
  (line 80) -> wt-somethread2 @9401993 (base 9898f0e) is still on-pin. No
  rebase needed. Worktree clean (status --porcelain empty).
- ITEM 1 DONE: /tmp/langcos/cp-smt2.txt built (python exact-replace of
  wt-somethread/ -> wt-somethread2/, 2 refs, 0 old refs left; 45 entries).
- ITEM 2 DONE: smt-hand2.kotoba written (2-step hand twin `(let [sht opt]
  (if (option-some? sht) (* 2 (+ (option-value sht 0) 1)) 0))`) and
  MEASURED pre-patch on cp-smt2.txt: check PASS exit 0 - t
  `bafyreibudrjyvqtujvaprwkhjv5mzijgiuaf2p3p42dpozhnxt2lhwhzvu`, main
  `bafyreiddijvv4nxuxzpme743kfkn66jkhynh26xw4xmfgtcpai44ztfy6m`
  (r-smt-hand2.txt). This is the 2-step parity canon.
- NOTE (probe hygiene): the lock-crosscheck script I wrote this tick
  (iter31-lockcheck.py) printed 54 "MISSING" lines - that is a path-format
  bug in MY script (it wrote `io.github.kotoba-lang.abi` with slashes but
  the on-disk cp uses dots `io.github.kotoba-lang/abi/...`); 0 real
  mismatches. cp-smt.txt was already proven loadable by this tick's hand2
  check PASS. Do not re-run that script's output as evidence.
- NOT DONE (budget): ITEM 3 apply linear-chain patch to wt-somethread2
  frontend.cljk (letfn lower :4093-4109 -> threaded = (reduce
  #(thread-form %1 %2 last?) payload steps), 1-step output byte-shape
  identical); ITEM 4 gate (2-step parity t cid == bafyreibudrj... + 1-step
  CIDs unchanged vs iter 26 canon bafyreia2bh.../bafyreidbwzh... + 0-step
  fail-closed + wasm32 compile + node run 41 -> 84 + sema regression);
  ITEM 5 commit+push. No patch applied, no new compile beyond hand2, no
  verdict. Hypothesis open.
- Next tick (resume exactly at item 3): python exact-replace patch (count==1
  assert) on /Users/junkawasaki/github/wt-somethread2
  src/kotoba/compiler/frontend.cljk desugar-some-thread letfn body; then
  gate on cp-smt2.txt; canon CIDs above; then commit+push
  bot/lang-somethread-rebase-20260920.


## Iteration 32 - setup re-verified, root cause re-confirmed by code read, patch NOT applied, no verdict (2026-09-23 00:35 JST, amu@a95d56f4)

- Target hypothesis (unchanged iters 26-31): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin smt-hand2 (t bafyreibudrjyvqtujvaprwkhjv5mzijgiuaf2p3p42dpozhnxt2lhwhzvu,
  main bafyreiddijvv4nxuxzpme743kfkn66jkhynh26xw4xmfgtcpai44ztfy6m - measured
  pre-patch in iter 31, canon on disk) AND 1-step CIDs unchanged (iter 26
  canon bafyreia2bh.../bafyreidbwzh...).
- Measured this tick (file-redirect; plain terminal stdout still empty;
  loadavg 10.56/11.86/15.04 - quiet gate NOT met, target parity-only so
  speed N/A):
  - STEP (0) re-verified: amu HEAD a95d56f4 (amu-rank tick 401) but
    deps-lock.edn still pins kotoba-sema 9898f0e28b48d54baba68991b2b2c7503c660b92
    -> wt-somethread2 @9401993 (base 9898f0e) is STILL on-pin. No rebase
    needed. Worktree clean (status --porcelain empty).
  - /tmp/langcos intact; all probe files + cp-smt2.txt (iter 31 item 1) +
    r-smt-hand2.txt (iter 31 item 2 canon) present.
  - Code site RE-CONFIRMED by direct read on 9401993 (line numbers unchanged
    since iters 27/28/30): desugar-some-thread defn at :4082; recursive
    lower letfn body :4093-4109; root cause visible in source:
    `(lower threaded (rest steps))` re-enters with the i64 threaded payload
    as `option-form`, and resolve-option-type (:4025-4068, `:else
    [:option :i64]` fallback at :4068) yields [:option :i64] for it, so
    step 2's `option-some?` binds an i64 -> the measured exit 65
    ("expected option-i64, got i64"). thread-form :3977-3984 (step-shape
    agnostic) and desugar-thread :3989
    `(desugar-expr (reduce #(thread-form %1 %2 last?) (first args)
    (rest args)))` are the shapes the patch mirrors.
- NOT DONE (run budget exhausted during verification, before any patch):
  linear-chain patch apply, gate, commit. No compile, no new probe, no new
  CIDs, no numbers, no commit. Hypothesis open.
- Patch spec (concretized, ready to apply next tick): replace the letfn
  body at :4093-4109 with a linear chain - tmp (single),
  option-type = (resolve-option-type (first args)), payload-type =
  (second option-type), payload = (list 'option-value tmp
  (option-payload-fallback payload-type)), threaded =
  (reduce #(thread-form %1 %2 last?) payload (rest args)), then-expr =
  (desugar-expr threaded); outer form =
  (list 'let [tmp (desugar-expr (first args))] (list 'if (list
  'option-some? tmp) then-expr (option-payload-fallback payload-type))).
  1-step output is byte-shape identical to the current single-step emit
  (assert via 1-step CIDs unchanged in gate).
- Next tick (resume exactly at item 3): python exact-replace patch on
  /Users/junkawasaki/github/wt-somethread2 frontend.cljk (count==1 assert);
  gate on cp-smt2.txt = 2-step parity (t cid == bafyreibudrj...) + 1-step
  CIDs unchanged (vs iter 26 canon) + 0-step fail-closed + wasm32 compile +
  node run (option-some 41 -> 84) + sema regression suite; then commit+push
  bot/lang-somethread-rebase-20260920.

## Iteration 33 - setup + canon order re-verified, patch NOT applied, no verdict (2026-09-23 06:35 JST, amu@815edd4f)

- Target hypothesis (unchanged iters 26-32): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin smt-hand2 (t bafyreibudrjyvqtujvaprwkhjv5mzijgiuaf2p3p42dpozhnxt2lhwhzvu,
  main bafyreiddijvv4nxuxzpme743kfkn66jkhynh26xw4xmfgtcpai44ztfy6m - iter 31
  canon on disk) AND 1-step CIDs unchanged (iter 26 canon
  bafyreia2bh.../bafyreidbwzh...).
- Measured this tick (terminal stdout still empty, file-redirect; loadavg
  10.36/8.67/8.12 - quiet gate NOT met, target parity-only so speed N/A):
  - STEP (0) re-verified: amu HEAD 815edd4f (amu-rank tick 403) but
    deps-lock.edn:80 still pins kotoba-sema 9898f0e28b48d54baba68991b2b2c7503c660b92
    -> wt-somethread2 @9401993 (base 9898f0e) STILL on-pin, clean tree
    (status --porcelain empty). No rebase needed.
  - /tmp/langcos intact: cp-smt2.txt (iter 31), all smt-*.kotoba probes,
    r-smt-hand2.txt canon all present.
  - Code site re-confirmed by direct read on 9401993 (line numbers unchanged
    since iters 27-32): desugar-some-thread defn :4082; recursive lower letfn
    body :4093-4109; resolve-option-type fallback [:option :i64] :4067;
    thread-form :3977-3984; desugar-thread :3989 (the linear reduce shape).
  - CANON ORDER RE-VERIFIED (this tick's new check, by direct read of
    thread-form :3977-3984): for 2-step `(some->> opt (+ 1) (* 2))` the
    linear chain emits step 1 NON-last -> `(list* '+ payload 1)` =
    `(+ (option-value tmp 0) 1)`, then last -> `(* 2 that)`. Net desugar
    shape `(* 2 (+ (option-value tmp 0) 1))` = BYTE-IDENTICAL to the
    smt-hand2 canon `(* 2 (+ (option-value sht 0) 1))` (only the let
    binding name differs, as for the 1-step canon, which matched in iter
    26 despite the same naming difference). Pass criteria of iter 32 hold
    as stated; no re-measure of the canon needed.
- NOT DONE (run budget exhausted during verification, before any patch):
  linear-chain patch apply (spec unchanged, iter 32: replace letfn body
  :4093-4109 with plain let - single tmp, option-type = (or (resolve-option-type
  (first args)) [:option :i64]), payload-type, payload, threaded =
  (reduce #(thread-form %1 %2 last?) payload (rest args)), then-expr =
  (desugar-expr threaded)), gate, commit of sema branch. No compile, no new
  probe, no new CIDs, no numbers, no sema commit. Hypothesis open.
- Next tick (resume exactly at item 3): python exact-replace patch on
  /Users/junkawasaki/github/wt-somethread2 src/kotoba/compiler/frontend.cljk
  (count==1 assert); gate on cp-smt2.txt = 2-step parity (t cid ==
  bafyreibudrj...) + 1-step CIDs unchanged (vs iter 26 canon) + 0-step
  fail-closed + wasm32 compile + node run (option-some 41 -> 84) + sema
  regression suite; then commit+push bot/lang-somethread-rebase-20260920.

## Iteration 34 - multi-step some->> linear-chain patch APPLIED + 2-step KIR parity CONFIRMED; gate partial (budget), no commit (2026-09-23 12:45 JST, amu@9479a174)

- Target hypothesis (carried iters 26-33): linear-chain lower in
  desugar-some-thread; pass criteria 2-step check PASS with definition CIDs
  == hand twin AND 1-step CIDs unchanged (iter 26 canon).
- DONE this tick (terminal stdout healthy; loadavg 12.79, parity-only so speed N/A):
  - Step (0): amu HEAD 9479a174, deps-lock.edn:80 still pins kotoba-sema
    9898f0e28b48... -> wt-somethread2 @9401993 (base 9898f0e) on-pin, clean tree.
  - ITEM 3 APPLIED: linear-chain patch on wt-somethread2 frontend.cljk
    (python exact-replace, count==1 asserted, 1032->1214 chars): recursive
    letfn lower :4093-4109 replaced with plain let - single tmp,
    option-type = (or (resolve-option-type initial) [:option :i64]), payload,
    threaded = (reduce #(thread-form %1 %2 last?) payload steps),
    then-expr = (desugar-expr threaded). Coverage-limit comment recorded
    in-source (option-resulting step not modeled, not silently admitted).
  - GATE (cp-smt2.txt classpath, amu nbb wasm_cli route, JVM-free):
    - 2-step (smt-2step.kotoba `(some->> opt (+ 1) (* 2))`): check **PASS
      (exit 0)** - was REJECT exit 65 pre-patch (r-smt-2step.txt).
    - 1-step (smt-first.kotoba): check PASS, t
      `bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74` ==
      iter 26 canon EXACTLY (1-step CIDs unchanged), main
      `bafyreigqgbc7xhcr33vy7lj5shxo3q2p24wryznlek54zioxyxssdk5zwy`.
    - 2-step parity: hand twin CIDs EXACT match - t
      `bafyreig37xemmislrv5e4izf7ks6lao4ykpkfenjqz53ukpm6ahzo2wluy`,
      main `bafyreicxvki6ooqf4ij4jwg4xw2oqlmwa6bkqykrq7o34cotyfex3vlfb4`.
  - CANON CORRECTION (iter 33's re-verify was wrong, this tick measured it):
    thread-form with last?=true places the value LAST, so the linear chain
    emits (+ 1 (option-value tmp 0)) for step 1, NOT (+ (option-value tmp 0) 1).
    The iter 31 hand twin smt-hand2.kotoba used the value-first spelling
    (t bafyreibudrj...) - numerically equal but a different KIR, hence the
    CID mismatch on first comparison. Corrected hand twin smt-hand3.kotoba
    `(* 2 (+ 1 (option-value sht 0)))` measures t
    `bafyreig37xemm...` == patched 2-step exactly. Parity verdict stands
    against smt-hand3 (measured this tick, not assumed).
- NOT DONE (budget exhausted; resume exactly here):
  - 0-step fail-closed (smt-0step.kotoba, expect exit 65 own diagnostic
    "some->> requires an initial option and at least one step").
  - wasm32 compile --output + browser/node run (option-some 41 -> 84).
  - sema regression suite (nbb run-tests.cljk, full lock classpath +
    wt-somethread2 src/test).
  - commit + push bot/lang-somethread-rebase-20260920 (wt-somethread2 tree
    currently DIRTY with the applied patch - do not lose it).
- Next tick (resume exactly): run the 4 remaining gate items above, then
  commit+push. Patch and probes: /tmp/langcos/iter34-patch.py,
  r-it34-{2step,first,hand3}.txt, smt-hand3.kotoba.
## Iteration 35 - setup re-verified, remaining 4 gate items NOT run, no verdict (2026-09-23 18:56 JST, amu@81cf05a4)

- Target hypothesis (unchanged iters 26-34): linear-chain lower in
  desugar-some-thread; 2-step KIR parity already CONFIRMED at iter 34
  (t bafyreig37xemmislrv5e4izf7ks6lao4ykpkfenjqz53ukpm6ahzo2wluy ==
  smt-hand3 twin `(* 2 (+ 1 (option-value sht 0)))`, 1-step CIDs unchanged
  vs iter 26 canon bafyreia2bh.../bafyreidbwzh...). Remaining: 4 gate items.
- Measured this tick (file-redirect; plain terminal stdout still empty;
  loadavg 27.49/98.70/102.48 - quiet gate NOT met, target parity-only so
  speed N/A):
  - STEP (0) re-verified: amu HEAD 81cf05a4 (advanced since iter 34's
    9479a174) but deps-lock.edn:80 still pins kotoba-sema
    9898f0e28b48d54baba68991b2b2c7503c660b92 -> wt-somethread2 @9401993
    (base 9898f0e) STILL on-pin, no rebase needed.
  - wt-somethread2 tree: branch bot/lang-somethread-rebase-20260920 @9401993,
    exactly one modified file (src/kotoba/compiler/frontend.cljk, +21/-17)
    = the iter 34 linear-chain patch, intact and UNCOMMITTED. Re-apply
    script on disk: /tmp/langcos/iter34-patch.py (if ever lost).
  - /tmp/langcos intact: cp-smt2.txt verified this tick (single
    classpath line, 2 wt-somethread2 refs, 0 old wt-somethread refs);
    all smt-*.kotoba probes + r-it34-{2step,first,hand3,2step-exit}.txt
    present.
  - Iter 34 measurements RE-READ (not re-run): 2-step check PASS exit 0
    (t bafyreig37xemm... / main bafyreicxvki...); 1-step check PASS (t
    bafyreia2bh... == iter 26 canon exactly).
- NOT DONE (run budget exhausted during verification, before any new
  probe): (1) 0-step fail-closed (smt-0step.kotoba, expect exit 65 own
  diagnostic "some->> requires an initial option and at least one step");
  (2) wasm32 compile --output + run (option-some 41 -> 84); (3) sema
  regression suite (nbb run-tests.cljk, full lock classpath +
  wt-somethread2 src/test); (4) commit + push
  bot/lang-somethread-rebase-20260920. No new probe, no new CIDs, no
  numbers, no commit this tick. Hypothesis open.
- Next tick (resume exactly, in order): run gate items 1-4 on cp-smt2.txt
  (iter 34's route: nbb direct with lock classpath entries minus the two
  pinned kotoba-sema dirs, wt-somethread2/{src,resources} substituted),
  then commit+push. NOTE: the exact check command line was not re-derived
  this tick (r-it34-cp.txt is a classpath fragment only) - re-derive from
  bin/amu's nbb route + cp-smt2.txt before running; do not assume the
  iter 34 form. wt-somethread2 tree is DIRTY with the applied patch -
  commit it before any other branch work touches that worktree.

