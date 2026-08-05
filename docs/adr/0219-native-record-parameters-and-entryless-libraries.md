# ADR-0219 — Records cross the native parameter boundary, and native targets carry entryless libraries

- Status: accepted
- Date: 2026-08-05
- Extends: ADR-0062 (native sealed scalar record construction/projection),
  ADR-0063 (native sealed scalar variant construction/dispatch)

## Context

ADR-0062 gave the native backends a record with no runtime representation: a
`let`-bound record is FLATTENED into one stack slot per field, and a record that
must cross a function boundary as a RESULT is boxed into a `pair` chain — one
word, built from arena primitives the backends already had. Both directions of
that design were deliberate, and both work.

What was never reachable is the other half of the boundary: a record arriving as
a **parameter**. The admission gate (`kotoba.kir/only-native-word-typed-features?`)
restricted `param-types` to `#{:i64 :string}`, `kotoba.verifier` independently
restricted them to the same set, and both backends' `emit-record-get-of-new`
threw `"record-get is only supported directly over a matching record-new
construction"` when the operand was anything else.

That single restriction, not any deeper property of the machine model, is what
kept real callers off this backend. Measured 2026-08-05 against
kotoba-lang/murakumo's shipped pure-planner cores — 33 `*_core.kotoba` modules
that already compile for wasm32, js and cljs and ship as precompiled KIR:

- **0 of 33** compiled for `:x86_64-kotoba-v1`.
- Every one that failed on a signature failed on a record parameter, an
  `[:option T]` record field, or a `:bool` result — never on anything in a body.

`murakumo.infer.join` is the representative case. Its whole surface is
`(defn needs-relay? [r [:ref :join/relay]] :bool …)` — a record parameter, a
`:bool` result, and a `[[:mem [:option :i64]] [:tmax :i64]]` schema whose parts
were each individually representable while the schema as a whole was not.

A second, independent restriction sat behind that one: a module with no entry
(`:entry nil`) — which is what a library IS — was admitted only on the
js/wasm32/cljs backends, and `kotoba.verifier`'s module shape required
`(= 'main (:entry p))` outright.

## Decision

**A record crosses INTO a function exactly the way it already crossed OUT: boxed
into the `pair` chain from ADR-0062.** This adds no representation, no ABI
change, no new primitive and no loader change — the caller's `record-new` becomes
the chain, the callee's projection becomes a walk of it, and both are source
rewrites into forms the backends already emit.

1. **Both backends** (`x86_64.cljc`, `aarch64.cljc`): `emit-record-get-of-new`
   treats a projection whose operand is a *parameter* as a chain walk — the same
   `boxed-record-projection` the call-result path already used. `emit-call`
   boxes a record argument on the way in, from a literal `record-new` or by
   re-boxing a flattened `let`-bound record from its slots in field order.

2. **`kotoba.kir` and `kotoba.verifier`** widen the boundary type set, each
   deriving it independently as they already do for every other shape: `:i64`,
   `:string`, `:keyword`, `[:option T]`/`[:result T E]`, and records. `[:option
   T]` also becomes an admissible record FIELD, because it is already one word.

3. **Entryless libraries compile on native targets that need no entry point**
   (`:x86_64-kotoba-v1`, `:aarch64-kotoba-v1` and the OS-suffixed profiles).
   The aiueos profiles are excluded: each names a mandatory entry symbol
   (`:efi_main`, `:aiueos_kernel_entry`, `:aiueos_process_entry`), so an
   entryless module there would package into an image whose declared entry does
   not exist. `kotoba.verifier` gains the library module shape beside the entry
   shape — no entry, no signature, and a non-empty export list in their place,
   each part checked as strictly as the entry shape's.

### What is deliberately NOT done

- **A bare `:bool` PARAMETER stays rejected**, preserving both gates' prior
  behaviour exactly. Measured: `(defn f [b :bool] …)` is refused by
  `kotoba.kir/execute` itself with `{:trap :value-type-mismatch :expected :i64
  :position {:parameter b}}`. That is a real gap, but it is in the INTERPRETER,
  not in either backend, and admitting the type while the oracle cannot run one
  would ship a boundary that nothing had executed. `:bool` remains available
  where it already worked: as a result, and as a record field.

- **KIR signatures are NOT ref-expanded.** The first attempt expanded
  `[:ref :ns/name]` in `lower` so the verifier could resolve it. That is a
  cleaner shape and it was reverted: `:kir-sha256` digests exactly the
  `select-keys`-ed program, so expansion moved the digest of every module using a
  schema reference **on every target**, which a native-slice change has no
  business doing. It was caught by `golden-digests-match-live-compile` drifting
  on `:composed-surface-kit` — including its **wasm** digest. The verifier
  instead admits the reference by name and requires a projection's schema to be a
  well-formed record whose own name equals it, so projecting schema A through a
  parameter declared as a reference to B is still rejected.

## Consequences

- **14 of murakumo's 33 shipped cores now compile to native machine code, from
  0.** `infer_join_core` emits 2,041 bytes with all 8 exports. The remaining 19
  fail on other typed features still outside the slice (11) or on a `record-new`
  in a position the backends still cannot place (4) — both are follow-on work
  with their own evidence, not claims made here.

- **Every widened shape is executed, not argued.** The shared ISA table
  (`isa-execution-test`) gains record parameters (first field, second field,
  forwarded through a second function, re-boxed from a `let`, and a record result
  fed straight in as a parameter), keyword/option/result parameters, and
  option-typed record fields in both the some and none cases — run as real
  processes on **both** ISAs: 185 assertions, 0 failures.

  Rows select DIFFERENT fields on purpose: a chain walked to the wrong depth
  still returns a plausible i64, so a row whose fields shared a value could not
  see the bug it is there to catch. The table's shared-across-ISAs design earned
  itself again here — the x86-64 half was written first and passed all rows while
  aarch64 threw, which is exactly the divergence two separate tables would hide.

- **One test changed policy rather than failing**:
  `keyword-literals-preserve-canonical-identity-without-i64-hashing` asserted
  that every non-web target rejects an entryless keyword library. Ten of them now
  carry it, so it asserts the split instead.

- Suites: kotoba-kir 470 assertions green, kotoba-verifier 65 green,
  kotoba-native 2,152 green. The compiler suite goes from 6,870 assertions with
  30 failures + 1 error to 7,017 assertions with **the same 30 failures** and 0
  errors — those 30 are pre-existing on unmodified `origin/main` in this
  environment, and the baseline error was these new ISA rows correctly failing
  against unpatched libraries.
