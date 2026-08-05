# 0220 — The pinned closure is the measured one, and the ISA rows are committed

Status: accepted
Date: 2026-08-06
Base: `origin/main` `db4418056579ec3158c46b6082c82f2e49f8a1e6`

## Context

A run of work on 2026-08-05 took murakumo's 33 shipped `kotoba/*_core.kotoba`
modules from 14/33 to 30/33 compiling to native machine code on both x86-64 and
aarch64. It landed across four repositories — `kotoba-native`, `kotoba-kir`,
`kotoba-verifier`, `artifact` — and every figure in it was measured through a
`:local/root` override.

This repository's `deps.edn` did not move. **A caller invoking the compiler as
pinned still got 16/33**, measured, below. The agents who landed the gate
changes deliberately left the pins alone: silently coupling a pin advance to a
semantic change is how a pin regression gets in unnoticed. So it is this
change, on its own, with its own evidence.

Two other things had accumulated in the same gap.

**The ISA execution rows were never committed.** Four agents in a row added rows
to `test/kotoba/compiler/isa_execution_test.clj`, ran them green as real
processes on both ISAs, and left them uncommitted because this repository was
outside each of their scopes. Each reproduced its rows in an ADR of the
repository it *was* allowed to touch. Four ADRs is not a regression gate; the
table is.

**`deps-lock.edn` was stale on `origin/main`, and failing closed.** Its recorded
`:lock/deps-digest` was `4a9ffb99…`; the actual SHA-256 of the `deps.edn` beside
it was `2a72798b…`. Its entries named `kotoba-kir b12eaf85`, `kotoba-native
470fd94` and `kotoba-verifier aa85109e` while `deps.edn` declared `d895d1f0`,
`8e7c0530` and `ccf37fed`. `bin/kotoba` therefore refused the lock and fell back
to `clojure -Spath` — which is the failure mode the header comment in `deps.edn`
describes exactly ("it silently sends the compiler back to `clojure -Spath`, and
the JDK-free property is gone with nobody notified"). Nobody was notified.

## Decision

### The pins

Every `kotoba-lang` dependency that was behind its default branch advances.
Each target was verified a genuine fast-forward through
`gh api repos/kotoba-lang/<repo>/compare/<old>...<new>` — `status: "ahead"`,
`behind_by: 0`, and a merge base equal to the old pin — **before** being used.
None was `behind` or `diverged`.

| dependency | old | new | ahead by |
|---|---|---|---|
| `kotoba-kir` | `d895d1f0` | `57cfa2b3` | 2 |
| `kotoba-verifier` | `ccf37fed` | `6433a81b` | 5 |
| `kotoba-native` | `8e7c0530` | `4a5216e6` | 4 |
| `artifact` | `d94cc03e` | `86d88bd5` | 2 |
| `kotoba-wasm` | `1a162198` | `b0c9837f` | 3 |
| `kotoba-component` | `58b52e0c` | `35fb4d59` | 3 |
| `kotoba-script` | `1fad35dd` | `57f623ce` | 3 |
| `tender-native` (test) | `f92f3902` | `3fcd5912` | 1 |

`abi`, `io-ipld` and `io-multiformats` were already at their default-branch
heads and are untouched.

### One pin is held, and why

**`provider` stays at `678b0ec0`.** Its default branch is 249 commits ahead —
a genuine fast-forward, verified like the rest — and advancing it was tried,
measured, and backed out.

At `db41ea92` the provider stopped raising errors whose *message* names the
fault and started raising a generic one carrying a structured code:

```
expected: (thrown-with-msg? … #"binding is not allowed" …)
  actual: "object request denied"
          {:phase :object-provider, :code :object/binding-not-allowed, …}
```

The denial still happens and the code is right; only the message moved. But
this repository's `object_provider_test` and `storage_provider_test` match on
message text, so the advance turns **4 assertions red** — measured, in the same
suite run as everything else here:

| test | file |
|---|---|
| `bindings-and-empty-fields-fail-closed` (×2) | `object_provider_test.clj:64,69` |
| `get-stream-binding-denial-and-transport-redaction` | `object_provider_test.clj:124` |
| `invalid-conditional-versions-fail-before-the-transport` | `storage_provider_test.clj:59` |

Landing it would mean rewriting four assertions from message matching to code
matching, in the same commit as a pin advance. That is precisely the coupling
this change exists to avoid, and it is the reason the pins were left out of the
gate changes in the first place. `provider` is a test-only `:extra-deps` entry
and contributes nothing to the sweep figure below, so holding it costs nothing
that this change is about.

It is left open by name. Moving those four assertions onto `:code` is a better
test either way — a structured code is not a sentence someone can reword — and
it belongs in its own change with its own evidence.

`deps-lock.edn` is regenerated in this same commit
(`nbb scripts/lock-classpath.cljs`). Its digest now matches the `deps.edn`
beside it, so `bin/kotoba`'s JDK-free path resolves again rather than falling
back.

### Coherence of the graph after the advance

`kotoba-verifier` at `6433a81b` pins `kotoba-native f6f29e9` in its own
`deps.edn`, with the reasoning that it does not merely depend on that backend
but **calls** it (`native-targets` holds `x86-64/emit-program`), so admitting a
`:bool` parameter while pinned to a backend that miscompiles a literal `false`
would put the defect inside its own closure. That reasoning is sound and this
change does not disturb it.

This repository pins `kotoba-native 4a5216e6`, which is `f6f29e9` **plus two
commits** (`286c5fe7` PCI config exports and a fuel-replenish fix, and its merge)
— verified a fast-forward from `f6f29e9`, `behind_by: 0`. A top-level pin wins
over a transitive one, so the resolved closure is `4a5216e6`, a strict superset
of what the verifier requires. **The graph is coherent.**

The one pin pair that is *not* identical, stated rather than glossed:
`kotoba-verifier` says `f6f29e9`, this repository says `4a5216e6`. That is a
descendant, not a divergence, and the difference is two commits that landed
after the verifier's ADR was written. `kotoba-native`'s `main` moved under this
change while it was being made — another agent is active there — so this pin is
a snapshot of `4a5216e6`, not a claim that `main` has stopped moving.

### The ISA rows

74 table entries are brought into `cases`, taken from the four ADRs rather than
re-derived, so that what runs here is what those ADRs claim ran.

| source | documented rows | table entries |
|---|---|---|
| `kotoba-native` ADR 0001 | 5 | 5 |
| `kotoba-native` ADR 0002 | 31 | 48 |
| `kotoba-verifier` ADR 0003 | 17 | 17 |
| `kotoba-native` ADR 0003, rows F–G | 4 | 4 |

ADR 0002's 31 rows become 48 entries because each of its 17 `replace-all` rows
runs twice, as that ADR specifies — once comparing the produced text with
`string=?`, once measuring its byte length. Neither check subsumes the other: a
content check alone cannot see a result that is right up to a truncation, and a
length check alone cannot see right-length wrong-bytes.

Two constraints are preserved deliberately rather than tidied away.

- **Every `:bool` row carries a `:string` parameter.** `kotoba-kir` carries
  `:param-types` into KIR only when the HIR is typed, so a function whose *only*
  typed feature is a `:bool` parameter loses its table and traps at `:phase :ir`
  as `:i64`. That is an open `kotoba-kir` gap (its ADR 0221). The `:string` is
  what keeps the row out of it, and the test comment says so.
- **Some rows are documentation, not gates.** The `:bool`-result rows reach
  admission by recursion through `native-word-value-type?` and passed before the
  widening too, as the verifier's own tests record. They are marked as such
  instead of being presented as regression gates.

### The harness no longer races another copy of itself

`tmp` built **fixed** names in the shared temp directory —
`kotoba-isa-code-x86_64.bin`, `kotoba-isa-loader-<isa>.bin`. `run-native`
writes the program to that path and then execs the loader on it, so any other
process running this table on the same machine can land in that window and the
loader runs **somebody else's program** while reporting it under this row's
name.

It does not surface as an error. It surfaces as a wrong answer. Observed here
2026-08-06, with a second agent running this table concurrently in another
worktree: `replace-all: two occurrences (byte length)` returned `:result -6`,
which is the expected value of the `bit-not` row — a different row's program,
executed under this row's name — and 43 rows failed that way in one run and
none in the run before it.

With two rows in the table the window was narrow enough that this was never
hit. At 119 rows it is hit readily, so committing the rows without fixing this
would have shipped a table that goes red for a reason that has nothing to do
with either backend. Every scratch path is now prefixed with a per-process
token (`pid-nanotime`) and marked `deleteOnExit`.

**Falsified, not asserted.** Two copies of the table run concurrently:

| `tmp` | run A | run B |
|---|---|---|
| fixed names (before) | 107 failures | 54 failures |
| per-process token (after) | **0 failures** | **0 failures** |

Both after-runs report 2 tests / 481 assertions and
`available: [aarch64 x86_64] / missing (SKIPPED): []`.

### The harness asserts no ISA was skipped

`the-verified-surface-executes-identically-on-every-available-isa` now prints
its availability set **and asserts it equals the full table**. A skipped ISA
reads exactly like a passing one in the summary line, so a green "2 tests, N
assertions, 0 failures" was never evidence that both backends produced it. A
host that cannot build both loaders now fails this test rather than quietly
halving it. Observed here: `available: [aarch64 x86_64] / missing (SKIPPED): []`.

## Measurement

### The point of the exercise: the sweep, with no `:local/root` anywhere

All 33 shipped `kotoba/*_core.kotoba`, compiled for both native targets, from a
checkout whose `deps.edn` and `deps-lock.edn` contain no `:local/root` at all —
verified by grep, not assumed.

| | x86-64 | aarch64 |
|---|---|---|
| `origin/main` `db44180`, pins as committed | 16 / 33 | 16 / 33 |
| this change | **30 / 33** | **30 / 33** |

The two ISAs admit the **same set**, not merely the same count — compared
explicitly, since equal totals can hide a divergence.

The 14 newly compiling: `connect_core`, `dash_state_core`, `deploy_plan_core`,
`fleet_inventory_core`, `infer_waste_core`, `kekkai_gate_core`,
`overlay_crypto_core`, `overlay_stream_core`, `persist_core`,
`provision_plan_core`, `reconcile_plan_core`, `report_core`, `secret_core`,
`tunnel_core`.

The 3 that remain are identical on both ISAs and share one reason:
`infer_plan_core`, `infer_schedule_core`, `task_plan_core`, all
`record-get is only supported directly over a matching record-new construction
on the native backend`, at `:phase :x86-64` / `:phase :aarch64`. That is a
`kotoba-native` limitation, out of scope here, and left open by name — it is the
same three the verifier's ADR 0003 named.

This is a **compile** figure. These modules are entryless libraries with no
`main` and are not executed by the sweep.

### Full suite, before and after

| | tests | assertions | failures | = stable + flaky |
|---|---|---|---|---|
| `origin/main` `db44180`, run 1 | 929 | 7,026 | 34 | 31 + 3 |
| `origin/main` `db44180`, run 2 | 929 | 7,026 | 31 | 31 + 0 |
| this change, with `provider` advanced | 929 | 7,322 | 36 | 31 + 4 provider + 1 |
| **this change, as landed** | 929 | 7,322 | **32** | **31 + 1** |

The third row is the measurement that caused `provider` to be held: +4 over
baseline, all four attributed above, none of them flaky.

**As landed, the pin advance caused no failure.** The sets were compared **by
name**, not by count: the stable 31 are the same 31 tests before and after, and
the remainder in every row is the timing-sensitive workload set described below.
The stable 31:

- 30 in `frontend_extensions_test` — 10 each in
  `typed-bounded-strings-remain-strings-through-checked-kir-and-web`,
  `i32-wrapping-and-xorshift-profile-is-explicit-and-bounded`, and
  `entryless-library-compiles-and-runs-through-kotoba-script`.

  **These 30 have a cause, and three prior agents reported them without one.**
  Every one of the 30 is the same assertion shape:

  ```
  expected: (thrown-with-msg? clojure.lang.ExceptionInfo
                              #"require the kotoba-script web target"
                              (compiler/compile-source source target))
    actual: nil
  ```

  They are **stale negative assertions**: they assert that a typed value is
  *refused* on a native target, and the widened admission gates no longer refuse
  it — the compile succeeds, so nothing is thrown. That message is the same
  `typed values currently require the kotoba-script web target…` that the 16/33
  sweep above shows on eight modules and the 30/33 sweep shows on none.

  They were already failing on unmodified `origin/main`, so they are residue of
  an **earlier** pin advance (`de5bd12`, "advance the stack pins") that widened
  admission without revisiting the tests that asserted the old narrowness. This
  change does not add to them: 30 before, 30 after, the same three tests.

  Fixing them means deciding, per assertion, whether the refusal was the point
  of the test or incidental to it. That is a semantic change to three tests and
  is deliberately not bundled into a pin advance — which is the same reason the
  pins were not bundled into the gate changes in the first place.
- 1 in `test_runner_completeness_test`:
  `kotoba.compiler.x86-64-execution-test` exists but is not in the runner's
  `:require` vector, so it never runs. Pre-existing; not fixed here, because
  adding a namespace that has never run would change the failure count this ADR
  is trying to attribute.

**The run-to-run variance is real and is now attributed.** Three prior agents
reported "roughly 30–33 failures, varying between runs" and none of them said
which. It is exactly three timing-sensitive workload tests —
`heavy-document-pipeline-kir-workload` and `host-value-path-near-budget-workload`
in `document_perf_workload_test`, and `dual-renderer-soft-performance-workload`
in `document_dual_renderer_test`. Across the four full runs recorded above they
contributed 3, 0, 1 and 1 failures with nothing relevant changing between them.
**The flaky count is three soft performance budgets, not a wandering
correctness failure** — and on a machine running several agents at once, a soft
performance budget is measuring the neighbours.

The +296 assertions are exactly the new rows: 74 entries × 2 ISAs × 2 assertions
each. The ISA table itself goes from **2 tests / 185 assertions** to **2 tests /
481 assertions**, 0 failures, both ISAs asserted present.

### Golden digests

**They did not move.** `golden-digests-match-live-compile` passes on **60
cases**, unchanged, and `resources/kotoba/lang-conformance/pilot-golden.edn` is
untouched by this commit. Nothing was re-pinned and no mismatch was branched
around. This is the expected outcome — the advanced gates decide accept/reject
and do not rewrite the program that `:kir-sha256` digests — but it is reported
as a measurement, not as an argument, because a pin advance *can* legitimately
move goldens and the difference matters.

## What was deliberately NOT done

**Rows A–E of `kotoba-native` ADR 0003 are not committed, and this is the one
place the four ADRs did not carry their rows.** That ADR records those twelve
entries as a summary table — position, `false` result, `true` result — without
the source text. The expected values (2/3, 8/5, 8/5, the four 223/213/123/113
combinations, 5/100) do not determine a program; several shapes produce them.
Reconstructing them would have meant inventing sources and then presenting
whatever they returned as a reproduction of that ADR, which is not a
reproduction. They are named here as an open gap instead.

What *is* committed covers the same defect. The verifier's 17 rows are verbatim,
and that ADR records them going red against `kotoba-native 8e7c053` — the pin
this repository carried until this commit — with **10 failures, all on x86-64,
all traps, on exactly the ten rows whose bool argument is written as the literal
`false`**. Rows F and G are committed because they are the ones ADR 0003 calls
reachable with nothing relaxed at all: `option-some-of` / `result-ok-of` lower
to `(pair 1 payload)`, so a `:bool` payload sits in a host-call argument slot
without crossing a function boundary.

**No capability kit qualification flag is touched.** Nothing here qualifies any
capability; `:native-aot` / `:wasm-aot` / `:jit` are untouched, and every kit
stays `:native-aot :pending`.

**Nothing outside this repository was modified.** `kotoba-native` and
`kotoba-verifier` have another agent active in them; they were read through the
GitHub API and read-only worktrees, never written.

## Consequences

- A caller who takes this compiler at its pinned SHAs now gets 30/33 on both
  native ISAs instead of 16/33. That was the whole point, and until this commit
  it was true only of people who overrode with `:local/root`.
- The four ADRs' rows are a regression gate rather than a description of one.
  74 entries, run as real processes through `tools/kexe_loader.c` on both ISAs.
- `bin/kotoba`'s JDK-free path works again. It had been falling back silently.
- **Left open, named**: (1) the three `record-get`-over-`record-new` modules, a
  `kotoba-native` limitation; (2) the untyped-encoding gap, `kotoba-kir` ADR
  0221, which is why every `:bool` row carries a `:string`; (3) rows A–E of
  `kotoba-native` ADR 0003, whose sources are not recoverable from that ADR;
  (4) `kotoba.compiler.x86-64-execution-test` is not in the runner and has never
  run; (5) the 30 `frontend_extensions_test` failures are pre-existing stale
  negative assertions, diagnosed above but not fixed here; (6) the `provider`
  pin is held at `678b0ec0`, 249 commits behind its default branch, until the
  four provider assertions are moved from message text onto `:code`.
