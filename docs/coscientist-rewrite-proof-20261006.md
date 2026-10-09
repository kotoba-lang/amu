# Integrate rooted rewrites, rule laws, state models and translation validation

The co-scientist performance process now has an executable diagnostic proof layer.
This is implementation and verification of that layer, not a new product emitter
or a performance promotion. The full original Embench C-or-better goal remains
unachieved. The qualified product generator and original workloads are unchanged.

The attachment's proposals are split into four falsifiable experiments. Simple's
local node processing and dependency worklist inspire the execution strategy;
GP2's rooted rules inspire the rule interface. Neither a GP2/DPO implementation
nor a full Sea-of-Nodes/SSA conversion is claimed. Source references:
[Simple chapter 9](https://github.com/SeaOfNodes/Simple/blob/main/chapter09/README.md),
[Fast rule-based graph programs](https://doi.org/10.1016/j.scico.2021.102727).

1. Declarative `rules.json` records root pattern, replacement, phase, guards,
   direction, decreasing measure, work budget and adoption gates. Exact supported
   schemas bind each named law to its pattern/guards. Replacement, guard and phase
   mutations are refused; a familiar rule name cannot reuse an unrelated proof.
2. A diagnostic Kotoba rooted matcher dispatches on the Add opcode and runs a
   bounded deterministic worklist over a six-node pure value DAG with explicit
   reverse-use lists. The fixture initially visits a dependent before its input
   simplifies, so dependency re-enqueue is necessary. It retains an independent
   pre-rewrite evaluation and compares the result after rewriting. Original
   semantic fuel/effect schedules are outside this value-only prototype.
3. SMT obligations check abstract 64-bit laws and a finite authority transition
   model explores revocation. A TLA+ specification is saved, with the distinction
   between model checking and proof checking from the official
   [TLA+ tools documentation](https://lamport.azurewebsites.net/tla/tools.html).
   TLC/TLAPS were not run. The finite model was explored independently and its
   transition checker compiled/executed as native Kotoba.
4. A strict observation gate compares results, exit, trap/site, fuel, resources,
   arena contents and ordered effects. It rejects missing fields/cases and source
   or semantic-profile changes. Its controls are synthetic adapter tests, not
   evidence that a new product candidate has passed translation validation.

The seven solver obligations returned UNSAT for the negated laws: wrapping i64
add-zero, unsigned constant-index bounds, scaled-address arithmetic, sequential
same-address store/load, permission-mask intersection without expansion, current
validity recheck after revocation, and strict decrease of eligible-root count.
These establish the stated abstract laws under their recorded assumptions, not
compiler soundness. Memory forwarding remains inadmissible without proving
aliasing, intervening effects, trap order and concurrency conditions. UNSAT relies
on Z3 5.1.0; no independently checked solver proof certificate is claimed.

Five bad laws returned SAT with saved counterexamples: signed instead of unsigned
bounds, omitting zero-index bounds, wrong address scaling, dropping fuel, and
stale cached authorization. Correct native graph rewriting reports 0 failures
for 258 inputs (0..255, signed MIN/MAX). Wrong replacement reports 257 failures;
zero work budget and missing dependency updates each report 258. The finite
current-authority model reaches 64 states/770 edges without an unauthorized use;
the stale-cache mutation reaches 128 states/1540 edges and finds the sequence
set all five conditions -> issue -> revoke compiler permission -> use. Native
exhaustive state/transition checks report 0 versus 341 violations, matching an
independent arithmetic oracle. Atomic use is assumed; concurrent linearization,
real Biscuit/provenance handling and liveness are not proved.

Both diagnostic kernels were compiled by the qualified native selfhost seed
`f00e38312ac7278b1b597207054cba521fafa28f30f03d20d237a07fd59647e2`
and executed by the existing native supervisor. Python/Z3 orchestrate excluded
diagnostic tooling only. No Node/JVM/Rust product dependency is added. The
bootstrap-boundary scan remains at 58 distinct PRODUCT files; product files and
launchers were not edited. This does not establish the separate whole-product
100% selfhost acceptance criterion.

Recipe provenance seals rule source, checker/model source, solver version,
compiler image, loader image, native kernels, target and entry offset. Its domain
is `amu.rewrite-proof-recipe/v1`; the recorded SHA-256 is a diagnostic recipe hash,
not a derived KIR DefCID, signature, authority grant or execution-result cache.
The existing logic manifest requires separate definition/artifact/compiler/
semantics/world identities; this diagnostic does not change that contract.

The next performance experiment remains bounded straight-line scalar local
constant facts followed by checked constant-index lowering inside the existing
closed mode2 vector contract. All runtime assignments, handle checks, unsigned
bounds, original fuel, trap positions and memory operations must remain. Explicit
and coalesced writes, control boundaries and unknown effects invalidate facts.
The new abstract bound/address laws support this candidate, but its native
emitter integration is still pending. Native generator invariants, current
593-fixture/25658-run expectations, fixed point, original19 state proof,
prospective paired timing, normal gates and integrated corpus/fixed point remain
mandatory before adoption. No repeated unchanged timing or smaller-code speed
claim is authorized by these proofs.

One-off authoring exception: these are new diagnostic algorithms/specifications,
not mechanical source refactors. An early graph prototype accidentally included
an unregistered constant-fold branch. Its wrong-replacement test produced 258
structural failures instead of the independently expected 257 value failures.
The extra branch was removed to match the declared add-zero-only rules; expected
results were preserved. The diagnostic log is retained. One native execution
approval timed out; the authorized retry succeeded.

Reproduce with `PYTHONPATH` pointing to an external diagnostic Z3 installation:

```
python3 scripts/seed/rewrite-proof/verify.py --out /private/tmp/amu-rewrite-proof-replay \
  --seed <qualified-native-seed.bin> --offset <seed.offset> --loader <kexe-loader>
```

Evidence: [summary](evidence/coscientist-rewrite-proof-20261006/summary.json),
[saved solver inputs, native code/logs and source snapshots](evidence/coscientist-rewrite-proof-20261006/native-proof.tgz),
[checksums](evidence/coscientist-rewrite-proof-20261006/checksums.json).

The complete archive was restored into a distinct directory. Its source, included
native seed/supervisor, solver inputs and kernels reran successfully, reproducing
the entire summary and recipe hash exactly. See [replay receipt](evidence/coscientist-rewrite-proof-20261006/replay.json).

The next concrete application is the [native closed-operation and normal-return identity summary](coscientist-shape-summary-20261006.md): rooted CFG transfers, reverse caller worklist, independent raw-SIR oracle, native mutant controls and a finite schedule model. It leaves the product unchanged and does not claim a performance improvement.
