# ADR 0261: clock's `:native-aot :pending` is a refused host authority, not an unfinished schema

Status: accepted

## Context

`clock-v1.edn` has read `:native-aot :pending` since the kit was written, in
the same word `log-v1.edn` and `storage-v1.edn` use. For those two the word is
accurate and actionable: the native targets refuse them at `:phase :target`
because their own request/result types are not one-word values, so whoever
narrows the schema moves the key.

For clock it was neither accurate nor actionable, and
`wasm32_kotoba_v1_qualification_test.clj` had generalised the wrong half into
prose:

> Native is a third, independent seam ... The kits at `:native-aot :pending`
> are pending because of their own schemas, not because the backend is
> unavailable.

Clock's schema is sealed and admitted, and the backend is neither unavailable
nor unwritten. **Everything except the loader already works.** Measured on
this tree, `aarch64`/macOS, a guest doing `typed-cap-call :clock/now` with the
kit's exact variant and record types:

```text
=== STEP 1: compile to native target ===
COMPILE OK; artifact keys (:format :compatibility :value :fuel-abi :exports
 :effects :kir-sha256 :code :target-profile :sha256 :context-abi :limits
 :target :lowering :program)
=== STEP 2: sign + execute in a real process ===
EXECUTE -> {:status :trap,
            :runtime {... :loader-source-sha256
                      "f28b175fd240f542bae9ea45b8942066d57b5e820572d7e6b0b2496c201d4d3f"
                      :target-profile {:isa :aarch64 :os :macos
                                       :runtime :kotoba-macos-supervisor-v1}},
            :trap {:kind :signal, :signal :SIGILL}}
```

It compiles, it is admitted by `kotoba.kir`'s `native-provider-contract?`
(ADR 0227 sealed capability 7 with exactly these descriptors on 2026-08-11),
it lowers through `kotoba-gmir`'s closed table
`{:i64 0 :string 1 :option-i64 2 :result-i64 3 :clock-v1 4 :dataspace-v1 5}`,
and both ISA encoders emit the call. It then reaches a real signed process and
dies in `checked_typed_cap_call`, at request validation, because
`valid_typed_value` in `tools/kexe_loader.c` has no `KEXE_TYPED_CLOCK_V1`
case — the enum constant was reserved by `be2130e`, the commit that wired
dataspace, and never implemented.

So the gap is one file, and that file is the one place the gap may not be
closed without a decision.

## The question this answers

*May `tools/kexe_loader.c` hold a clock source at all?* Both available
implementations are refused, by decisions already made.

**A real OS clock is refused by ADR 0240** (accepted 2026-08-11), whose own
Context paragraph is about this exact contract:

> The native clock contract now reaches KIR, the independent verifier, and both
> machine backends. That proves a sealed artifact can represent the request and
> result; it does not prove an OS process can execute the effect. Earlier text
> assigned the guest-to-host syscall to Tender and allowed a C loader process to
> look like the production runtime. aiueos ADR-0013 already owns the C-free OS
> boundary, so that dependency direction was wrong.

with the evidence rule that *hosted Tender, Linux, JVM/FFM VMM and C-reference
kernel runs are oracles only* and `:aiueos-c-free-bare-metal-v1` is the sole
production native-effect surface. A kexe run is an oracle run. It cannot be the
evidence that qualifies an effect.

The sandbox says the same thing in the other language. The kexe child installs
a seccomp filter admitting exactly ten syscalls —
`write`, `exit`, `exit_group`, `rt_sigreturn`, `rt_sigprocmask`, `getpid`,
`gettid`, `tgkill`, `munmap`, `brk` — with `SECCOMP_RET_TRAP` as the default,
and macOS runs under `(deny default)`. `clock_gettime` is not there. Reading a
real clock is not an added case statement; it is a widening of the TCB's
sandbox policy.

**A synthetic clock is refused by ADR 0084**, which already built one — the
component provider whose `$wall` starts at `1700000000000` and increments by
one per observation, `$mono` by a thousand — and then declined to flip the key
on the strength of it:

> What this does NOT claim: `:wasm-aot :implemented` on `clock-v1.edn` (left
> pending ... packaging evidence ≠ production host-time / security review)

A counter in `kexe_loader.c` is that same construct on a different surface. It
would fabricate values at a typed boundary that declares
`:wall {:unit :unix-milliseconds}` and `:source-authority :host`, and
`provider/clock.cljc` throws unless a host supplies `wall-now`/`monotonic-now`
— the loader would have to *become* the source, which is the authority in
question. There is no channel for a seeded one either: the loader's argv
carries file, offset, arity, ISA, allow-mask and `main`'s guest arguments, and
nothing else.

**Dataspace is not a precedent.** `dataspace_inject` is bounded in-process
memory, deterministic, and needs zero new syscalls, so ADR 0240 does not reach
it; and it implements the kit's real semantics rather than inventing values.
Clock has no third option, because the semantics *are* a time source.

## Decision

`clock-v1.edn` keeps `:native-aot :pending` and gains a sibling
`:native-aot-blocked-by` block recording `:kind :undecided-host-authority`,
`:not :schema`, the measured trap, the four ADRs it rests on, the seccomp
allowlist, and the exit condition: capability 7 served over
`:aiueos-c-free-bare-metal-v1` with a runtime vector, per ADR 0240's dependency
chain.

`wasm32_kotoba_v1_qualification_test.clj` stops claiming that every
`:native-aot :pending` is a schema statement, names the two kinds, and guards
both: the schema kind must NOT carry a blocker, the blocked kind must, and the
block must name a measured trap, its ADRs, and something that would clear it.
A blocker with no exit condition is permanent by accident.

**No new `:qualification` value was introduced**, deliberately. Read with an
EDN reader, the eleven kits use exactly two status values, `:implemented` and
`:pending`; the two other values that appear (`:direct-move-only`,
`:task-stream-handle-slice`) are `stream-object-v1`'s answers to
non-status keys in its own separate vocabulary. `kits-in-this-vocabulary-
answer-all-five-keys` pins the key set at five. A third status would be a
schema change to the one artifact this repo tells readers to consume, to carry
information that fits the shape this file already uses twice —
`:wasm32-kotoba-v1-surface` and `:wasm-aot-surface`, each a top-level sibling
explaining one qualification key, each guarded so it cannot outlive its claim.
The blocker is the same shape pointed the other way.

What could now mis-read this: a reader who consults only `:qualification` sees
clock and storage as identical, exactly as before. The block is additive, so it
informs whoever looks, and misinforms nobody. If that proves insufficient, the
next step is a status value, not a bigger block.

## The sub-question this deliberately does NOT answer

aiueos grants `:clock/monotonic` and nothing else — `policy.cljc`'s
`default-kernel-caps`, and `component_abi.cljc` mapping import key 7 to
`:clock/monotonic` — and its control loop has no wall clock at all
(`manifest.cljc`: *the control loop's `clock()` is a cycle counter, not a wall
clock*). Yet the sealed native request variant ADR 0227 admits has a `:wall`
case. **What a native clock returns for `:wall` is undecided**, and this ADR
does not decide it, for the same reason it does not decide the first question.

## Three corrections to the record

Each of these was believed and is wrong; each would send the next attempt into
the wrong file.

1. **The live emitter is `machine_ir.cljc`, not the cond in the ISA files.**
   `emit-typed-cap-call` in `kotoba-native/src/kotoba/native/{aarch64,x86_64}.cljc`
   handles kinds 1–3 and `:else`-throws on the clock boundary. That is the
   legacy emitter, superseded by the IR migration (ADRs 0241–0244). Reading it
   suggests the native backend cannot represent this call. It can, and does.
2. **`kexe_loader_windows.c` omits dataspace on purpose, and the omission is
   pinned.** Its `typed_cap_call` is pure identity over kinds 1/2/3. The
   docstrings on the two pinned digests in `kotoba-lang/artifact` show the
   split: the POSIX hash records *"Advanced 2026-08-17: typed callback kind 5
   is dataspace-v1"*, the Windows hash stops at 2026-08-11. Whatever native
   clock eventually does, matching that omission is the default, not an
   oversight to fix.
3. **A loader edit is a three-repo change.** `loader-source-sha256` is pinned
   in `kotoba-lang/artifact` (`runtime_identity.clj`) and `build-runtime!`
   refuses any source whose digest is not the reviewed one, so touching
   `tools/kexe_loader.c` means amu → artifact → amu's dependency pin, the way
   `be2130e` did it for dataspace.

## Evidence

- The compile-and-trap run quoted above, on `:aarch64-kotoba-v1`, macOS,
  through `kototama.native.executor` with a signed envelope and a measured
  runtime identity.
- `tools/kexe_loader.c`: `KEXE_TYPED_CLOCK_V1 = 4` present in the enum, absent
  from `valid_typed_value` and from `checked_typed_cap_call`.
- Two new tests and nineteen new assertions in
  `wasm32_kotoba_v1_qualification_test.clj`: 11 tests / 84 assertions before,
  13 / 103 after, 0 failures.
- Discrimination, each break applied and reverted, both with the file still
  valid EDN so that a reader throw could not be mistaken for a guard firing
  (the first attempt at break 1 did exactly that -- it deleted one brace too
  many and produced nine `Unexpected EOF` errors, which prove the EDN was
  broken and nothing about the guard):

  | Break | Reported |
  | --- | --- |
  | `:native-aot-blocked-by` deleted from `clock-v1.edn` | 7 failures, 0 errors, in `clock-is-pending-on-native-for-a-host-authority-reason` and `only-blocked-kits-carry-a-native-aot-blocked-by-block` |
  | the block copied onto `storage-v1.edn` | 2 failures, 0 errors, in `kits-pending-on-native-are-pending-for-a-schema-reason` and the same block/claim guard |

- Full amu suite: 1,102 tests / 8,318 assertions / 0 failures before this
  change (ADR 0260's measurement, which `a41a510` is the merge of);
  **1,104 tests, 8,337 assertions, 0 failures, 0 errors** after. The delta is
  exactly this ADR's two tests and nineteen assertions.

## What this does NOT claim

- that a native clock is impossible, or that the language cannot express it
- that `clock_gettime` in the loader would be wrong on the merits — only that
  it is not decided here and not decidable by an oracle run
- anything about `:wasm-aot`, which stays pending for the reason ADR 0084 gave
- that the other kits at `:native-aot :pending` were audited for which of the
  two kinds they are; only log and storage carry a measured schema rejection

## Related

- ADR 0240 — native-effect evidence terminates at the aiueos C-free surface
- ADR 0084 — the synthetic clock provider that declined to flip the key
- ADR 0227 (kotoba-kir) — sealed the capability-7 native provider contract
- ADR 0257 — clock's i64 `wasm32-kotoba-v1` surface, the other host that does
  return real time, via `System/currentTimeMillis` in tender
- ADR 0029 / ADR 0073 — the kit's semantics and its real CLJ/CLJS sources
- ADR 0259 / ADR 0260 — the sibling shape: a check that could not measure must
  not answer what a measured pass answers
- superproject ADR-2608650000 — a permanent constraint and an unfinished
  backend must not be recorded the same way
