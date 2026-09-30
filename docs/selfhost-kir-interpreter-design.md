# The KIR reference interpreter on the Kotoba route: design and first families (2026-09-30)

Owner of the code: `osaho` (`src/kotoba/kir.cljk`, ~6000 lines). Kotoba-route pieces:
`src/kotoba/kir/kvalue.cljk` (the typed dynamic `Value`, 576edfb), `src/kotoba/kir/lowering.cljk`
(the validation half of `lower`, 576edfb), `src/kotoba/kir/interp.cljk` (this note), and the
guest twin `lang/compat/kotoba/kir.kotoba` in kotoba-lang, which stands in for `kir.cljk` on the
project route.

## Why this is the largest hollow spot

`kotoba.kir/execute` and `eval-expr` on the project route were named refusals
(`kotoba.kir/interpreter-unavailable`), and `lower` refused every module whose pure `:i64`/`:bool`
entry has to be sealed by running the interpreter (`kotoba.kir/oracle-unavailable`). A compiler
that cannot run its own constant oracle cannot produce the artifact `kotoba.verifier` re-derives,
so "a native compiler that builds itself" is not closed while these stay hollow.

## Inventory of `eval-expr` (kir.cljk lines 3868-5669, 1800 lines)

`eval-expr [form env functions fuel heap call-stack cap-call]` is one `cond` over the head symbol
`op`. Line ranges are in `src/kotoba/kir.cljk` at 576edfb; "ported" is what
`kotoba.kir.interp` implements today.

| lines | size | family | heads | needs beyond ints |
|---|---|---|---|---|
| 3912-3942 | 31 | core forms | `let` `if` `do` `arena-scope` | env; `let`/`if` are tail positions (host loops, no recursion) **ported** |
| 3943-3983 | 41 | text ABI v7/v8/v10 | `string-compare` `string-fold-ascii` `string-find-blank/skip-blank` `string-index-of-from` `string-compare-lines` `string-find-byte` `string-append-range` | strings, utf-8 helpers in `kir.value` |
| 3984-4003 | 20 | capability calls | `cap-call` `typed-cap-call` | host `cap-call` callback, typed-value boundary validation |
| 4004-4028 | 25 | pair heap, kgraph | `pair` `pair-first/second` `kgraph-*` | heap cells, arena capacity, datom store |
| 4029-4116 | 88 | string length, bytes value | `string-byte-length` `string-length` `string-from-i64` `bytes-*` `vector-i64-from-bytes` `string-from-utf8` | bounded strings, `:bytes` |
| 4117-4158 | 42 | task / stream | `task-ready?` `bytes-task-byte-count` | resource table |
| 4159-4264 | 106 | string / keyword / symbol | `string=?` `string-concat` `-substring` `-code-point-at` `-replace-all` `-contains?` `-index-of` `-split-count` `-fold-case` `-upper` `keyword-*` `symbol` | strings, byte budget |
| 4265-4293 | 29 | xml | `xml-*` | `kir.xml` |
| 4294-4445 | 152 | f64 / f32 / decimal | `f64-*` `f32-*` `decimal-f64-*` conversions | IEEE-754 bits; the `Value` carries f64 bits, arithmetic needs a native float op |
| 4446-4594 | 149 | map, bool, option, result, variant | `map-*` `bool-not` `option-*` `result-*` `variant-*` | tagged aggregates (`Value` tags 10, 13-15); `bool-not` **ported** |
| 4595-4890 | 296 | hetero-vector, typed list/set/map, record | `typed-list-*` `typed-set-*` `typed-map-*` `record-*` `hetero-vector-*` | typed aggregates, cell budget, item limits |
| 4891-5086 | 196 | vector, vector-f64 | `vector-*` `vector-f64-*` | vectors of i64/f64, item limits |
| 5087-5165 | 79 | string-index, disjoint-set | `string-index-*` `disjoint-set-i64-*` | persistent tables |
| 5166-5430 | 265 | document | `document-*` | documents, sha256, EDN print/read |
| 5431-5574 | 144 | kernel / memory / rodata | `kernel-*` `slice-*` `rodata-*` `image-*` | a memory image; any such head makes a module kernel-native, so it is never oracled |
| 5575-5635 | 61 | integer arithmetic, comparison | `+ - * quot bit-xor bit-and bit-or min max = < > <= >=` | i64 wrap, div traps **ported** |
| 5636-5669 | 34 | shifts, i32, call | `bit-not` `i64-shift-*` `u64-shift-right` `i32-*` `xorshift32`; `:else` = function call | **ported** |

Surrounding machinery that belongs to the same interpreter: `invoke-function` (3686-3757: arity,
parameter typing, frame budget, fuel charge, closure/pair-chain checks, result typing, the
`__kotoba_loop_N` trampoline), `charge!` (1567, fuel), the budget traps (1539, `budget-traps`),
`validate-runtime-value!`/`validate-boundary-value!` (1813-1950, tags and bounded values),
`execute` (5670-5857: option checks, entry argument validation, `box-bool`, host-stack guard) and
`lower`'s oracle block (5877-6077).

## Fuel, frames, trap: one model for host and Kotoba

* **Fuel** counts function entries. `charge!` decrements once when a function is entered;
  going below zero is the trap `budget/fuel`. A self-tail re-entry of a `__kotoba_loop_N` helper
  is free (T7.1/T7.2), so a loop of any length costs one unit.
* **Frames** is the call depth of interpreted functions (`default-frames` 32). A self-tail loop
  re-entry keeps the depth. Exceeding it is `budget/frames`. `cells` and `bytes` budgets exist
  for the aggregate and string families and are not needed for pure `:i64`/`:bool`.
* **Traps are values.** On the host a trap is an `ex-info` (`trap!`); a Kotoba function cannot
  catch, so `kotoba.kir.interp` answers a `:kir.interp/res` record `{kind v fuel trap}` with
  kind 0 = value, 1 = trap (the host's full trap name: `budget/fuel`, `division-by-zero`,
  `signed-division-overflow`, `i64-shift-count-out-of-range`, `unbound-symbol`, `unknown-function`,
  `arity-mismatch`, `value-type-mismatch`, ...), 2 = self-tail call marker (the host's
  `trampoline-call` map). Every step tests the kind and returns the trap unchanged. The
  resource traps (`budget/*`) are what `lower` records as `:oracle-inconclusive`; every other
  trap aborts `lower` on the host and is a refusal `kotoba.kir/oracle-trap:<name>` in the twin.
* **Fuel is threaded, not global.** The host keeps a `volatile!`; there is no mutable cell on
  the Kotoba route, so `ev` takes the fuel and returns the fuel left in its result.

## How host recursion becomes bounded recursion (not an explicit stack, yet)

The host `eval-expr` is directly recursive over the form, with tail loops only for `let`/`if`.
The earlier agents' finding stands: the reference interpreter running *on* the KIR-interpreter
(the route the selfhost check exercises) has a small stack, so recursion depth is a design
input. The port keeps recursion where it is bounded by the program's *source*, and removes it
where it is bounded by the program's *run*:

1. **Loop iterations never recurse.** A `__kotoba_loop_N` self-tail call returns the marker
   (kind 2) up through `let`/`if`/`do` to `invoke`, which re-enters its own Kotoba `loop`/`recur`
   with the new arguments (`recur` is a trampoline on every target). A 100000-iteration loop
   uses constant interpreter stack and, as on the host, one fuel unit.
2. **Interpreted calls recurse at most `frames` deep** (32 by default, the same bound the host
   states as its deterministic budget). Each level costs the expression depth of one function
   body, so interpreter stack is `frames * source nesting`, both fixed before the run starts.
   There is no trap analogous to `host/stack-exhausted`: exceeding the budget is `budget/frames`.
3. `let` bindings recurse per binding and `do` per form (source-bounded); `if` tests recurse,
   branches are tail calls of `ev`.

An explicit-stack machine (frames as records in a `[:list ...]`, a continuation list of
`{form env pending}`) removes the `frames * nesting` bound and is the plan when `frames` is
raised for native-scale verification (`execute :frames 100000`, used by the artifact
verifier): it needs continuation records per operation family, so it is deferred until the
families with real aggregates land. The result-record protocol above does not change.

## The `Value` domain

`kotoba.kir.kvalue/Value` is the runtime domain (tags 0-16). For this subset only tag 2 (i64)
and tag 1 (bool, n = 0/1) occur. Comparisons produce i64 0/1 exactly as on the host; `=` uses
`value-eq` (so `1` and `true` differ, like Clojure); `bool-not` answers a boolean; a `:bool`
parameter or result accepts a boolean or the word 0/1 (`validate-boundary-value!`); the entry's
`:bool` result is boxed at the boundary (`box-bool`). i64 arithmetic wraps by construction (the
KIR `+ - *` wrap); `quot` traps on zero divisor and on `MIN / -1`; shifts trap outside
`[0,63]` (`[0,31]` for the i32 forms).

## `ported?`: never a wrong answer

`ported?` scans the whole KIR module: every function has `:i64`/`:bool` parameters and result, no
closure or pair-chain refinement, a name that is neither an implemented head nor one of the 372
heads the host dispatches on (`test/kotoba/kir/host_eval_ops.txt`, generated from `kir.cljk` by
`tools/gen_host_ops.py`, so a user function called `pair` is never mistaken for the builtin), and
a body of integer/boolean literals, symbols, implemented heads and calls of the module's own
functions. Anything else keeps its named refusal in the twin: `lower` answers
`kotoba.kir/oracle-unavailable`, `execute`/`eval-expr` `kotoba.kir/interpreter-unavailable`. The
scan is conservative (whole module, not only what the entry reaches).

## Wiring in `kir.kotoba`

* `lower`: after `lower-problem` passes, if `oracle-wanted?` and `ip/ported?` then
  `ip/run` the entry under the host defaults (fuel 100000, frames 32). A value seals
  `:oracle-value` and the one-block `:blocks`; a `budget/*` trap sets `:oracle-inconclusive`;
  any other trap is a refusal that carries the trap name.
* `execute kir name args opts`: `ip/run` with `:fuel` (default 512) and `:frames` (default 32)
  read from the opts Form; the result Value is erased with `kv/to-form`.
* `eval-expr form`: `ip/eval-form` for a closed ported form.

## Verification (measured 2026-09-30/10-01)

`test/kotoba/kir/interp_diff.cljk` (driver `tools/interp_diff.sh`) runs `kotoba.kir.interp` through
the project route (so: interpreted by the host interpreter) against the host oracle of
`kotoba.kir/lower` (`{:oracle-fuel F :oracle-frames M}`) on every string literal of the kotoba-sema
test directories that analyses as a program, on seeded generated programs (random grammar over the
ported operations, loops, mutual recursion, arithmetic and shift traps) and on hand-written probes,
each under three budgets (fuel 3000/frames 32, fuel 60/frames 5, fuel 50/frames 32). Outcome
alphabet `V:<hi>:<lo>` / `B:<bool>` / `T:<full trap name>`.

* 732 cases (64 sema programs, 145 generated, 35 hand, x 3 budgets, minus 3 stalled): 702 inside the
  ported subset, **702 agree, 0 disagree**. The 30 not ported are sema-corpus programs using vectors,
  documents, bytes, f64 and options. Ported outcomes: 551 values, 92 booleans, 59 traps (division by
  zero 36, frames 10, shift count 9, signed division overflow 3, fuel 1).
* `test/kotoba/kir/interp_lower_diff.cljk` runs the guest twin (`lang/compat/kotoba/kir.kotoba`)
  against the host module: `lower` 71/71 agree (the result Form, `:oracle-value` and `:blocks`,
  equal to the host's; 10 modules refused `oracle-unavailable`), `execute` 54/54 (4 refused
  `interpreter-unavailable`), `eval-expr` 22/22.
* Constant interpreter stack: `spin 30` and `spin 1000` (one loop helper, 1000 self-tail
  re-entries) both run under `node --stack-size=5000`; the iteration count does not grow the stack.
* **A host finding.** The host does not charge fuel for a zero-charge `recur` re-entry (T7.1), so a
  program whose loop does not terminate never traps on fuel and stalls the host oracle for ever;
  one such sema-corpus program was found (`(loop [i 0] (recur (+ i 1)))` shaped). This interpreter
  keeps the host's rule (a differential port must), so `lower` of such a module does not return on
  either route; the harness runs the host phase in a restartable process and records the case as
  stalled. If loops should be charged, it is a decision for both routes at once.
* Cost: the interpreter is interpreted by the host interpreter, about 50 ms per loop iteration
  (a loop iteration is ~100 Kotoba calls). Natively compiled this disappears; it bounds the size
  of the differential corpus, not the design.

## Remaining families, in the order the compiler needs them

1. strings (`string-concat`, `substring`, `string=?`, `string-length`, `string-from-i64`,
   `code-point-at`, index-of, upper/fold) and keywords/symbols: most sema-corpus programs that
   are not ported use these; needs the bounded string byte budget.
2. typed lists / vectors / records / variants / options / results (the aggregates every
   selfhost module builds): needs the cell budget and `Value` tags 8-15, plus the schema table
   (`*runtime-schemas*`) for `validate-runtime-value!` on `[:ref ...]` types.
3. `:bytes` and `document-*` (hashing needs `org-nist-sha2` on the Kotoba route).
4. f64/f32 (bits arithmetic needs a native float op or a soft-float reading).
5. pair heap, kgraph, capability calls, closures (`closure-param-indexes` with `invoke`).
6. Not oraclable by construction: kernel/memory heads (module is kernel-native), xml, task/stream.
