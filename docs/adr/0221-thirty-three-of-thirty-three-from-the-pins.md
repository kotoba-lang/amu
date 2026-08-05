# 0221 — 33/33 from the pins, not from an override

Status: accepted
Date: 2026-08-06
Base: `origin/main` `3463431e9a2b647c4db5922e83ad47a077c15011`

## Context

ADR 0220 advanced this repository's pins and, measuring from them with no
`:local/root` anywhere, got murakumo's 33 shipped `kotoba/*_core.kotoba` modules
to **30/33** on both native ISAs. It left three modules open **by name** —
`infer_plan_core`, `infer_schedule_core`, `task_plan_core` — all failing for one
reason on both backends:

```
record-get is only supported directly over a matching record-new construction
on the native backend
```

That was a `kotoba-native` limitation, out of scope for a pin advance. It has
since been lifted: `kotoba-native` ADR 0005 emits the chain walk for a
`record-get` whose operand is *not* syntactically a matching `record-new`, and
`kotoba-verifier` widened admission to match.

The agent that landed those two measured **33/33 on both ISAs** with
`kotoba-native f35a8ee`, `kotoba-verifier 328dd22`, `kotoba-kir 57cfa2b` —
pinned by git SHA only. But it measured against compiler `db44180`, which
predates ADR 0220's own pin advance. So the figure was true of a closure nobody
could get by depending on this repository. This change makes it reproduce from
this repository's own `deps.edn`, and re-measures rather than inheriting.

This is the same shape as ADR 0220 and exists for the same reason: a pin advance
gets its own change and its own evidence, so that a pin regression cannot hide
inside a semantic one.

## Decision

### The pins

Two move. Each was verified a genuine fast-forward through
`gh api repos/kotoba-lang/<repo>/compare/<old>...<new>` — `status: "ahead"`,
`behind_by: 0`, merge base equal to the old pin — **before** being used. Neither
was `behind` or `diverged`.

| dependency | old | new | ahead by | merge base |
|---|---|---|---|---|
| `kotoba-native` | `4a5216e6` | `f35a8ee6` | 4 | `4a5216e6…` |
| `kotoba-verifier` | `6433a81b` | `328dd229` | 2 | `6433a81b…` |

`kotoba-kir` is already at `57cfa2b3`, which is its default-branch head, and is
untouched. `abi`, `io-ipld`, `io-multiformats`, `artifact`, `kotoba-wasm`,
`kotoba-component`, `kotoba-script` and `tender-native` are unchanged.

`deps-lock.edn` is regenerated in this same commit
(`nbb scripts/lock-classpath.cljs`). Its `:lock/deps-digest` is now
`0126d9e8…`, which is the SHA-256 of the `deps.edn` beside it — checked
explicitly, because a stale lock does not fail loudly, it sends `bin/kotoba`
back to `clojure -Spath` and the JDK-free property disappears with nobody
notified. That is not hypothetical: it is exactly what ADR 0220 found and
repaired on `origin/main`.

### The graph is coherent, and the pin pair is now exact

`kotoba-verifier` at `328dd229` pins `kotoba-native f35a8ee` in its own
`deps.edn`, for the reason its ADR gives: it does not merely depend on that
backend, it **calls** it (`native-targets` holds `x86-64/emit-program`), so
admitting a shape while pinned to a backend that refuses it would put the
disagreement inside its own closure.

This repository now pins **the same commit**, `f35a8ee`. ADR 0220 had to record
a two-commit gap here (`kotoba-verifier` said `f6f29e9`, this repository said
`4a5216e6`, a descendant). **That gap is closed: the two pins are now identical,
not merely compatible.** There is no pin pair left in this graph that is not
either identical or a verified descendant.

`kotoba-native`'s `main` has moved past `f35a8ee` to `8ac35f34` while this
change was being made — two commits, "export ACPI table admission" and its
merge, from another agent active in that repository. This change pins
`f35a8ee`, **the commit that was measured**, not the moving head. Advancing to
`8ac35f34` would mean shipping a figure measured on a different closure than the
one pinned, which is the exact defect ADR 0220 exists to prevent. It is named
here as a snapshot, not as a claim that `main` has stopped moving.

## Measurement

Everything below was run in a worktree off `origin/main` `3463431e`, on this
host, with several other agents active on it.

### The sweep, with no `:local/root` and no `with-redefs`

All 33 shipped `kotoba/*_core.kotoba`, compiled for both native targets through
`kotoba.compiler.core/compile-source` with an empty policy. `deps.edn` and
`deps-lock.edn` were grepped for `:local/root` — the only textual hit is the
comment in `deps.edn` saying there isn't one. No `with-redefs` was used
anywhere; the sweep harness is a plain `compile-source` call per module.

| | x86-64 | aarch64 |
|---|---|---|
| pins as committed on `3463431e` (`kotoba-native 4a5216e6`, `kotoba-verifier 6433a81b`) | 30 / 33 | 30 / 33 |
| **this change** (`kotoba-native f35a8ee`, `kotoba-verifier 328dd22`, `kotoba-kir 57cfa2b`) | **33 / 33** | **33 / 33** |

The baseline row reproduces ADR 0220's figure exactly, including the identity of
the three failures — so the before/after difference is attributable to these two
pins and nothing else.

The three newly compiling are precisely the three ADR 0220 left open:
`infer_plan_core`, `infer_schedule_core`, `task_plan_core`.

The two ISAs admit the **same set**, not merely the same count — the admitted
module lists were diffed, not compared by length. The 33/33 result was produced
**twice per ISA**, because one green run of anything on this host is not
evidence.

This is a **compile** figure. These modules are entryless libraries with no
`main` and are not executed by the sweep.

Independently, `bin/kotoba -M check task_plan_core.kotoba` — one of the three —
returns `{:ok true, :effects #{}, :admission {:admitted? true …}}` through the
**JDK-free lock path**, with no fallback warning, confirming the regenerated
lock resolves the new pins.

### Full suite, before and after, compared by name

| | tests | assertions | failures | = stable + flaky |
|---|---|---|---|---|
| `3463431e`, run 1 | 929 | 7,322 | 32 | 31 + 1 |
| `3463431e`, run 2 | 929 | 7,322 | 34 | 31 + 3 |
| **this change, run 1** | 929 | 7,322 | 33 | 31 + 2 |
| **this change, run 2** | 929 | 7,322 | **31** | **31 + 0** |

**The pin advance caused no failure.** The stable set is the same 31 tests, by
name, in every row — verified by extracting the `FAIL in (…)` names and
comparing sets, not counts:

- 30 in `frontend_extensions_test` — 10 each in
  `typed-bounded-strings-remain-strings-through-checked-kir-and-web`,
  `i32-wrapping-and-xorshift-profile-is-explicit-and-bounded`,
  `entryless-library-compiles-and-runs-through-kotoba-script`. These are the
  stale negative assertions ADR 0220 diagnosed: they assert a refusal
  (`#"require the kotoba-script web target"`) that the widened gates no longer
  perform, so the `thrown-with-msg?` returns `nil`. **Still 30, still the same
  three tests** — this change neither adds to them nor fixes them, for the same
  reason ADR 0220 gave: fixing them is a semantic decision per assertion and
  does not belong in a pin advance.
- 1 in `test_runner_completeness_test` (`every-test-namespace-is-in-the-runner`):
  `kotoba.compiler.x86-64-execution-test` is still not in the runner's
  `:require` vector and has still never run.

The remainder in every row is the documented soft-performance set, and nothing
else appeared:

| run | flaky failures |
|---|---|
| before, run 1 | `dual-renderer-soft-performance-workload` |
| before, run 2 | (3, from the tail summary; names not captured) |
| after, run 1 | `heavy-document-pipeline-kir-workload`, `dual-renderer-soft-performance-workload` |
| after, run 2 | none |

Both named flakes are in the three-test set ADR 0220 identified
(`heavy-document-pipeline-kir-workload`,
`host-value-path-near-budget-workload`, `dual-renderer-soft-performance-workload`).
On a host running several agents at once, a soft performance budget is measuring
the neighbours. **The after run that came out at exactly 31 is the one that
settles it**: with the flakes quiet, the failure set after the advance is
*identical* to the stable set before it.

### ISA execution table

`test/kotoba/compiler/isa_execution_test.clj` is untouched by this change, and
run in isolation twice after the advance:

```
available: [aarch64 x86_64] / missing (SKIPPED): []
:ISA {:test 2, :pass 481, :fail 0, :error 0}
```

**2 tests / 481 assertions / 0 failures — 119 cases × 2 ISAs × 2 assertions —
both runs, and identical to the before-measurement.** The availability
assertion added in ADR 0220 confirms **neither ISA was skipped**; a skipped ISA
reads exactly like a passing one in the summary line, so this is asserted rather
than inferred. The same line appears in both full-suite runs after the advance.

### Golden digests

**They did not move.** `golden-digests-match-live-compile` passes on **60
cases** — the case count is asserted in the test itself (`(is (= 60
(:case-count report)))`), so a silent change in coverage would fail rather than
pass quietly. Run in isolation twice, 0 failures both times.

`resources/kotoba/lang-conformance/pilot-golden.edn` is **byte-identical**
before and after: SHA-256 `b53d0d0f…` in both cases, and the file does not
appear in this commit's diff. Nothing was re-pinned, and no mismatch was
branched around. This is the expected outcome — the advanced gates decide
accept/reject and do not rewrite the program that `:kir-sha256` digests — but it
is reported as a measurement, because a pin advance *can* legitimately move
goldens and the difference matters.

## What was deliberately NOT done

**No capability kit qualification flag is touched.** Nothing here qualifies any
capability; `:native-aot` / `:wasm-aot` / `:jit` are untouched and every kit
stays `:native-aot :pending`. The sweep is a compile figure, and compiling is
not qualifying.

**`provider` stays held at `678b0ec0`**, 249 commits behind its default branch.
ADR 0220 measured the advance and backed it out: `db41ea92` replaced
message-text errors with a generic error carrying a structured `:code`, and this
repository's `object_provider_test` and `storage_provider_test` match on message
text, so advancing turns 4 assertions red. Moving those four onto `:code` is a
better test either way — a structured code is not a sentence someone can reword
— but it is a test rewrite, and bundling it into a pin advance is the exact
coupling these changes exist to avoid. It is left open, again, by name.

**The 31 stable failures are not fixed here**, for the reasons above.

**Nothing outside this repository was modified.** `kotoba-native` and
`kotoba-verifier` have another agent active in them; they were read through the
GitHub API only. `manifest/west.yml` and the `com-junkawasaki/root` superproject
were not touched.

## Consequences

- A caller who takes this compiler at its pinned SHAs now gets **33/33 on both
  native ISAs**. The three `record-get`-over-non-`record-new` modules ADR 0220
  left open are closed, and closed *from the pins* rather than from an override.
- The `kotoba-verifier` → `kotoba-native` pin pair is now **exact** rather than
  descendant, so there is no version skew left to reason about in this graph.
- `bin/kotoba`'s JDK-free path resolves the new closure; verified by compiling
  one of the three newly-admitted modules through it.
- **Left open, named**: (1) `provider` held at `678b0ec0` until the four
  provider assertions move from message text onto `:code`; (2) the 30
  `frontend_extensions_test` stale negative assertions, diagnosed in ADR 0220,
  still unfixed; (3) `kotoba.compiler.x86-64-execution-test` still not in the
  runner and still never run; (4) rows A–E of `kotoba-native` ADR 0003, whose
  sources are not recoverable from that ADR, still uncommitted; (5) the
  untyped-encoding gap (`kotoba-kir` ADR 0221) that requires every `:bool` row
  in the ISA table to carry a `:string`; (6) `kotoba-native` `main` is two
  commits past this pin (ACPI table admission exports), unmeasured here.
