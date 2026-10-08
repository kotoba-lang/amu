# Compile twin spike: nbb.cli `compile-native!` on the Kotoba route (2026-10-08)

Question: can the product entry nbb.cli reach the Kotoba route as a thin `compile!` twin (the check-driver pattern)
instead of a line-by-line port of its 858 host lines, and what actually blocks it?

## Method

`seed/tests/compile-twin/spike.kotoba` is an entry that runs `compile-native!`'s aarch64 steps with existing Kotoba
modules only: `nbb-io/read-text-file` -> `sema/analyze` -> `effect-row/check` (policy through the new cli-support
readings) -> `kir/lower` -> `native-program` (host `kotoba.kir/native-program` without the recursive-schema clause) ->
`native.aarch64/emit-program`, and writes `:code`/`:exports`. It is compiled and linked by seed r6m `8d3338e1` against
the seed17 frontend objects (`build/seed17/front0`, kotoba-native `752cdf2`, kotoba-sema `c2e1343`), and run with the
native image's budgets (`scripts/seed/launcher/build.sh`; the default 64 Ki vector table traps immediately).
`seed/tests/compile-twin/run.sh` compares it with `bin/amu compile --target aarch64-macos` (BOOTSTRAP-REFERENCE, host
lock: kotoba-native `33418cd`) on the 372 programs of the parity corpus dirs present in this tree (no Embench ports).

## Result (measured)

| class | n | meaning |
|---|---:|---|
| SAME | 256 | code bytes and export entries equal (2 of them differ only in the printed order of `:exports`) |
| BOTH-REFUSE | 60 | both refuse |
| GUEST-FAILS | 49 | the Kotoba route refuses what the host compiles |
| CODE-DIFF | 4 | code bytes differ |
| GUEST-ONLY | 3 | the Kotoba route emits code the host refuses |

Of the 309 programs the host compiles, the Kotoba route emits identical native code for 256 (83%).

### The gaps, by cause

1. **Oracle interpreter (41 of 49 GUEST-FAILS).** `kotoba.kir/lower` (the guest twin) refuses
   `kotoba.kir/oracle-unavailable` when a pure entry uses an operation family `kotoba.kir.interp` has not ported. A
   spike variant that falls back to `kotoba.kir.lowering/lower-base` (the structural module, no oracle) emits code
   equal to the host's for all 41: the emitter is not the problem, the sealed `:value` is.
2. **kgraph capacity (8 of 49).** The frontend itself traps `:budget/cells :arena :kgraph`: the loader's
   `KEXE_KGRAPH_CAPACITY` is a fixed 4096 (tools/kexe_loader_decisions.kotoba). A resource decision, not a port.
3. **Native admission gate (3 GUEST-ONLY).** The host refuses `record-assoc` / typed closure results before emitting
   (`kotoba.kir/only-native-word-typed-features?`, `unqualified-native-feature`); the guest kir twin has no such gate,
   so the spike emits code for programs native does not qualify. The twin needs this gate.
4. **Counted self-recur loops (4 CODE-DIFF).** Every differing program has a counted self-recursive loop; the guest
   code carries the bulk fuel prepay entry (`cmp`, `b.lt` cold, ...) where the host's does not. Both kotoba-native
   versions contain the plan (`counted-self-recur-plans`); the guest's Kotoba arm
   (`counted-self-recur-plans-of-gmir`, d2c0f1f) applies it and the host lock's host arm does not. A same-source host
   comparison was not possible: the host arm of `752cdf2` does not load on nbb (`Integer/toString`,
   machine_ir.cljk:2397). To be settled in kotoba-native.
5. **Printed map order.** The host prints a map of more than eight entries in hash order, so a byte comparison of the
   kexe text is not meaningful; compare entries (and the seal, which is over canonical bytes).

## What this settles for the twin

- The route exists end to end: frontend, lowering, the aarch64 emitter and the cli-support readings link into one
  6.8 MB image and compile real programs with no node/JVM/nbb.
- The twin is wiring plus four named pieces, in order of reach: the native admission gate (correctness: never emit
  what native does not qualify), the oracle interpreter families (41 programs), the loop fuel divergence
  (kotoba-native), the kgraph capacity decision (8 programs).
- Artifact assembly (target profile, compatibility, seal, provenance, verifier) takes `:document` on the Kotoba
  route, not Form: the twin converts with `frontend.base/form->document` / `form/from-document`, and compares
  artifacts by entries and seal, not by text.

Out of scope of the spike: the artifact map, seal, provenance, verifier, caches, `--source-path`, x86-64.
