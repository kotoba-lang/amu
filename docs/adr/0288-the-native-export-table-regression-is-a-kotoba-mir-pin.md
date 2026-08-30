# ADR 0288: The native export-table rejection is a kotoba-mir pin, bisected — not ADR 0284's vector fix

- Status: accepted
- Date: 2026-08-30

## Decision

`amu extract-native` rejects both H.264 native kernels on current main with
`:kotoba/verification-failed "native export table rejected"`. **Bisected to a
single dependency: `kotoba-mir` `3f88f71bea80` → `3aea0acc1e89`**, reached
through `kotoba-native` `3162d868`, which this repo pins.

Rolling back **only** that one coordinate, with `kotoba-native` left at the
current `3162d868`, makes both kernels extract cleanly. Nothing else in the
55-commit `kotoba-native` range reproduces it.

**This clears ADR 0284's `:vector-i64` boundary fix**, which was the obvious
suspect — it is the one change in the range that alters which types cross a
native function boundary, and it tests GOOD.

The fix is not made here: `kotoba-mir` is outside this repo, and the mitigation
that is available — reverting the pin — would undo the x86 preserved-tier direct
reentry that landed with it. That is an owner decision, recorded rather than
taken.

## Evidence boundary

### What was measured

Reproduction: `org-iso-h264` (main `2736765`)
`test/h264/kotoba-compiler-repro/native-export-table-rejected.kotoba`, a
byte-for-byte copy of `src/h264/quant.kotoba`, plus `src/h264/transform.kotoba`.
Both compile to `--target aarch64` at exit 0 and are then rejected at
`extract-native`, which calls `verifier/verify-artifact!` before writing.

**Failure sets, not counts:**

| pinning | `quant` copy | `transform` |
|---|---|---|
| current main (`kotoba-native` 3162d868 → `kotoba-mir` 3aea0ac) | **rejected 65** | **rejected 65** |
| identical, `kotoba-mir` alone rolled to 3f88f71 | ok, `group-idx` offset 332 len 48 arity 2 | ok, `idct4-1d` offset 116 len 220 arity 5 |

**Bisect over `kotoba-native` `100fb7a8..3162d868` (55 commits).** Each point
compiled and extracted through `clojure -Sdeps` with the coordinate overridden:

| pin | result |
|---|---|
| `100fb7a8` (pre-range) | GOOD |
| `85f8c07e` (after bounded native vector region lowering) | GOOD |
| `a8f8cfe3` (**ADR 0284's `:vector-i64` boundary spelling**) | **GOOD** |
| `3dab370e` (kotoba-mir pool-exclusion merge) | GOOD |
| `da3b56b7` (x86 direct self reentry) | GOOD |
| `16572dc1` (iteration 49's LEA-fused numerator) | GOOD |
| `3162d868` (merge of the two above) | **BAD** |

A merge whose two parents are both GOOD is itself BAD, which is the whole
finding: the merge carries changes neither parent had. Its diff against
`16572dc` is three files, and only two can matter — a `kotoba-mir` pin advance
`3f88f71` → `3aea0ac`, and one line in `machine_ir.cljc` selecting
`:x86-64/jmp-rel32` instead of `:aarch64/b-imm26` on x86. **The kernels are
aarch64**, so the opcode line cannot reach them; the isolation above confirms it
by rolling back the pin alone and leaving that line in place.

**Not an nbb/JVM divergence.** Both entrypoints reject the same artifact
identically (`./bin/amu extract-native` and `clojure -M:run extract-native`,
exit 65 both). That control matters because two other defects landed today were
exactly that shape (ADR 0286, ADR 0287), so it was the first thing to rule out.

**Not iterations 51 or 52.** Those changed `docs/adr/`,
`docs/codegen-coscientist.md` and `bench/bulk-carrier/`. `bench/bulk-carrier` is
on no classpath — `deps.edn` declares `:paths ["src" "resources"]` and the only
bench path in any alias is `bench/runtime-comparison/cljs` — so neither could
reach a compiler code path.

### The mechanism, and what is inferred about it

The verifier re-runs the emitter on the artifact's **own stored KIR** and
compares the result against the artifact's stored export table. The decode-kernel
agent established that verify-time emission is deterministic: `emit-program`
twice on the same KIR yields an identical table. So the disagreement is between
**compile-time and verify-time emission**, not between two verify-time runs.

**Inferred, not measured:** that means compile-time emission consumes something
the stored KIR does not carry. A preserved-tier direct-reentry allocation change
is a plausible source — layout moved (`group-idx` sits at 332 under the rolled-back
pin and the pre-range pin put it at 416), and if the layout depends on allocator
state that the KIR does not reconstruct, re-emission cannot land in the same
place. **This ADR does not demonstrate that.** Establishing it means dumping both
export tables and diffing them, which is the next step and was not done here.

### Why this is worth having even unfixed

This is the producer/verifier independence property (ADR 0230) doing exactly what
it is for. The verifier does not trust the producer's export table; it rebuilds
it. A change that made native layout depend on non-KIR state was caught at the
boundary rather than shipping an artifact whose table describes code that is not
there.

### Limits of this evidence

- aarch64 only, two kernels, one host.
- Seven points bisected, not all 55 — the range was narrowed by hypothesis
  (the two commits naming vectors and native boundaries) before being closed by
  the merge/parent contradiction. A commit between two tested GOOD points could
  in principle also fail; nothing here excludes that.
- The mechanism is inferred. What is measured is which coordinate flips it.
- `transform`'s `idct4-1d` reads length 220 here where the decode-kernel agent
  recorded 232. Different pins, so different code; the offsets agree.
