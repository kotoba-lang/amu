# ADR 0286: The wasm32 internal error was a missing host-index conversion, not a refusal

- Status: accepted
- Date: 2026-08-30

## Decision

`bin/amu compile <file> --target wasm32` answered exit 70 and
`:kotoba/internal-error` for any source using `hetero-vector-at` or
`hetero-vector-assoc`. This was a **defect in the Wasm backend's lowering**,
not a policy refusal wearing the wrong code. It is fixed at the root
(`kotoba-lang/kotoba-wasm` ADR 0047, merged as `87a5c0b3`), this repository's
pin is advanced to it, and the falsifying regression test is added to
`test/nbb` -- the suite that runs on the runtime that was broken.

The defect: a STRUCTURAL position inside a heterogeneous value (which member
is being read or replaced) arrives from KIR as an ordinary i64 literal. An
i64 literal is a `Long` on the JVM and a JavaScript `BigInt` under cljs/nbb.
Three sites in `kotoba.wasm` fed that literal straight to `nth` to select the
member type. On the JVM the cast is a no-op. On cljs, `nth` refuses a BigInt
with `Index argument to nth must be a number` -- a host-level error carrying
no `ex-data`, which `kotoba.compiler.nbb.cli-support/error-report` can only
classify as `:internal` and print as `"internal compiler error"`.

The KIR reference interpreter already performed exactly this conversion for
exactly these two operations (`kotoba.kir`, `host-index`). The Wasm backend
did not, and had no test on the runtime where the difference exists.

No admission gate is widened. `hetero-vector-at` was already admitted by the
frontend and already lowered by the JVM backend; what was missing was the
lowering on the second runtime. Where a position is genuinely malformed -- not
an integer literal, negative, or outside the value's arity -- the backend now
refuses it with `{:phase :wasm-typed-lowering}` and a message, so a real
refusal is reported by name rather than as an internal error.

## Evidence boundary

### What was measured

**The defect, and which path served it.** `bin/amu`'s `nbbNativeEligible`
routes `compile` with `--target wasm32` to the **JDK-free nbb path**
(`src/kotoba/compiler/nbb/wasm_cli.cljs`); the JVM path was never entered.
Against `orgs/kotoba-lang/org-iso-h264/src/h264/expgolomb.kotoba` at amu
`5a2d188`, that path exited **70** in 1.29 s with

```
{:error :internal, :diagnostic {:code :kotoba/internal-error, ...},
 :message "internal compiler error"}
```

**The exception the CLI was swallowing.** Calling the pipeline directly under
the same nbb classpath (`sema/analyze` -> `admission/check` -> `ir/lower` ->
`wasm/emit`) put the throw in `kotoba.wasm.core/emit`:
`Index argument to nth must be a number`, `ex-data` `nil`. The frontend and
admission stages completed: HIR `:kotoba.hir/v3`, `admitted? true`, KIR
`:kotoba.kir/v4`. Printing the lowered KIR showed the operand:
`(hetero-vector-at [:vector [:i64 :i64]] (hetero-vector-new ...) #object[BigInt 1])`.

**Two controls, both as the brief described them.** `amu check` on the same
file exits **0** with `:exports [read-bit read-bits read-ue read-se]`.
`amu compile --target aarch64` exits 70 with `:error :target`,
`:code :kotoba/target-rejected`, and a named reason (`"typed values currently
require the kotoba-script web target, typed Wasm target, or qualified native
string/scalar-record/option-i64/result-i64 features"`). A third control: the
**JVM** `kotoba.wasm.core/emit` compiled the identical KIR to bytes without
complaint. So one runtime refused by name, one compiled, and one threw.

**Reduction.** Eight lines reproduce it -- one `defn`, one `hetero-vector`,
one `hetero-vector-at` at position 1 -- exit 70 with the same diagnostic. The
committed fixture (`test/nbb/fixtures/hetero-vector-position.kotoba`) is that
reduction with the positions made observable: they are non-zero, the members
differ in value AND in type (`[:vector [:i64 :f64]]`), and `main` folds three
positions of a triple into one i64, so a misread position is a wrong result
and a wrong Wasm member type, not only a throw.

**Falsification, on the runtime that was broken.** `npm run test-nbb-wasm32`
is 42 cases after this change. With the pin reverted to `a739f379` and the
lock regenerated, **exactly the 2 new cases fail**, with
`threw: Index argument to nth must be a number` -- the real message, not a
substitute -- and the 40 pre-existing cases still pass, so the fixture is not
failing for some unrelated reason. With the pin restored: **42 cases, 0
failed.**

**Behaviour of the emitted module, not merely exit 0.** For the same fixture
at `wasm32-browser-kotoba-v1`, the JVM and nbb emitters produce
**byte-identical** modules: SHA-256
`748ad1c19831da8b12989396fbcd48d2c4fd74c76056fb3b8b53eceb4d52ec93` on both.
The nbb-emitted module, instantiated through `runtime/browser-host.mjs` and
called **by the export names the artifact itself declares** (`:exports`
`[main tail head swapped-tail]`; no offset was guessed and zero was never
passed), returns `main` 327, `head` 3, `tail` 2.5, `swapped-tail` 9.25 -- the
same four values `kotoba.kir/execute` returns for the same inputs on both
runtimes. `kotoba.compiler.wasm-typed-test/heterogeneous-positions-agree-with-the-kir-interpreter`
pins that comparison here.

**Suites.** `kotoba-wasm` after its fix: 119 tests / 525 assertions / 0
failures. This repository's nbb wasm32 suite: 42 cases / 0 failed.
`kotoba.compiler.wasm-typed-test`, the JVM namespace this change touches:
28 tests / 79 assertions / 0 failures / 0 errors. The original repro now
compiles through `bin/amu` end to end: exit 0, 3,030 bytes.

**The full JVM suite did not finish, and the one red namespace observed in it
is pre-existing.** This host sat at load average 449-498 throughout (other
sessions), with one document-render test alone taking 134 s wall for 3.8 s of
CPU. Two attempts at `clojure -M:test` (152 namespaces) were still in the
first ten namespaces after an hour. What ran showed
`kotoba.compiler.isa-execution-test` failing. That namespace is native
(`kexe`) and is not on the Wasm backend's path at all, but "not on the path"
is an argument, not a measurement, so it was measured: the same namespace was
run against the **unmodified** dependency closure -- identical classpath with
`kotoba-wasm` at the old pin `a739f379` -- and failed **15 assertions of 760
across 6 tests** (`the-verified-surface-executes-identically-on-every-available-isa`,
`a-call-and-a-back-edge-in-one-function-execute`,
`a-call-and-a-back-edge-across-a-spill-execute`,
`a-value-spilled-in-one-branch-arm-survives-into-the-other`,
`multi-phi-consumer-plan-and-real-process-have-zero-frame-traffic`,
`scalar-direct-call-preserves-a-live-caller-value`,
`source-record-sroa-has-zero-frame-traffic-and-runs-both-edges`), every one
of them `{:status :trap :exit 120 :fuel {:initial 512 :remaining 512}}` -- a
trap before any fuel was consumed. It is red without this change. **No claim
is made here about why it is red**, only that this change is not the cause.

**One unrelated defect observed and not fixed.** `-o` is not a recognised flag
on either path -- `--output` is the only spelling, and no `"-o"` appears
anywhere in `src/kotoba/compiler/`. `amu compile ... -o /tmp/eg.wasm` does not
fail; it silently ignores the flag and writes the artifact, its provenance and
its publication record next to the SOURCE file. That is an unknown option
accepted in silence, and it wrote three files into a read-only repository
during this investigation (removed). It is a separate defect and is left
alone here.

### What was NOT done, and why

**No audit of other operands used as host indices.** `record-get` and
`record-assoc` derive their position from a keyword via `keep-indexed`, so it
is a host number before it reaches `nth`; the dynamic-index operations
(`vector-at`, `typed-set-nth`, `typed-map-entry-at`) emit their index as an
expression rather than consuming it in the emitter. Those two families were
read and reasoned about; **they were not tested**, and no systematic search
for the same shape elsewhere in the emitter was run.

**No cljs test was added to `kotoba-wasm`.** That repository has no cljs
runner, and adding one is a larger decision than this fix. The consequence is
recorded honestly in its ADR 0047: the assertions added there **cannot see
this defect** -- on the JVM the conversion is a no-op cast and the pre-change
code passed the identical positions. That is precisely why it survived. The
discriminating test lives here, in `test/nbb`.

**The h264 module was compiled, not executed.** `expgolomb.kotoba` now emits a
valid 3,030-byte module. Its semantics were not checked against
`kotoba.kir/execute`; only the fixture's were.

**No count of how much guest code was affected.** Two attempts to scan the
workspace's `.kotoba` sources for these operations were killed by `timeout`
at 280 s under host load. A scan that did not finish is **unmeasured**, not
zero, so no figure is claimed. What is known is bounded and specific: at least
one existing admitted source (`expgolomb.kotoba`) could not reach any non-JVM
backend, and no `examples/*.kotoba` fixture and no pre-existing `test/nbb`
case used either operation -- which is why nothing here noticed.

### Limits of this evidence

- The behavioural comparison covers four exports of one fixture at one set of
  inputs, through one host (`runtime/browser-host.mjs`) at
  `wasm32-browser-kotoba-v1`. `wasm32-wasi` was not executed; `wasm32` was
  compiled and validated only.
- The byte-identity result is for that one fixture. It is not a claim that the
  two emitters agree in general.
- `main` folding three positions into 327 makes a misread position visible at
  a host that can only call `main`, but 327 is one value: a permutation that
  happened to sum the same would not be caught. The per-export comparisons are
  what actually distinguish the positions.
- The full JVM suite is unmeasured, not green. Only
  `kotoba.compiler.wasm-typed-test` was run to completion here, plus the
  `isa-execution-test` control at the old pin.
- The `:phase :wasm-typed-lowering` refusals are covered by JVM assertions in
  `kotoba-wasm` only. They have never been exercised on cljs, because no
  admitted source reaches them -- the frontend does not emit a non-literal or
  out-of-range structural position. They are a floor against a future
  regression re-entering as an internal error, not a path anyone travels.
