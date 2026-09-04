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
