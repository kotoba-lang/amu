# Dense dispatch frontier: reject the broad shortcut; investigate bounded continuation fusion

This is a SOURCE/static-only coscientist hypothesis. No compiler, workload, native artifact, SSH, solver, or process API was executed. Product sources were not edited. Original full19 workloads/profiles remain the performance goal. This archive is a selected source record, not a complete dependency archive.

## Observation and lineage

`census.py` parses the nineteen original Kotoba sources from the accepted LC G3 compile38 outputs and verifies each against the build52 input-origin bank. Existing matching repository batch-port files are also checked. Full picojpeg/wikisort source paths are preserved from the archived G3 corpus; their repository convenience paths are not guessed.

The two measured LC/OFF native images are unchanged: statemate 87,716 B, SHA256 `5500419beb37f71f0c2ee09c64233170bc853378b082b694025b45ccbe32152d`; nsichneu 37,520 B, SHA256 `a748745da85ace8730c4b3414ac1fe977de7f280501ebe96dc6db47b1409b1fd`. Their exact hashes agree with the freshly built same-host build52 header receipts. The C dylibs/header bytes are independently pinned here but not executed.

Current repository `seed/41-a64gen.kotoba` is pinned separately. LC G3 executable (`5f4f591a...`) is pinned as the measured producer. Historical v8 typed observer source/SIR/FREC/native outputs are separately pinned as a **different producer lineage**; their counts do not prove current producer admission, machine-code costs, or current AST-to-FN name binding.

We intentionally do not count branch opcodes by searching arbitrary native bytes. Current native images contain literal/data pools, and this source-only task lacks a qualified current instruction/data map. No C machine dispatch/inlining or runtime causal attribution is claimed.

| Structural observation | statemate | nsichneu |
| --- | ---: | ---: |
| Original-source definitions | 538 | 265 |
| Source `case` forms | 0 | 0 |
| Source `if` forms | 132 | 158 |
| Source user-call forms | 1,482 | 518 |
| Historical v8 functions (including generated wrapper) | 539 | 266 |
| Historical v8 OP-CALL sites | 1,481 | 520 |
| Historical v8 immediate CALL/RET sites, argc <=7 | 428 | 128 |
| Historical v8 OP-FUEL sites | 537 | 268 |
| Historical v8 OP-RT sites | 339 | 37 |
| Historical v8 vector-parameter functions | 532 | 262 |
| Historical v8 scalar signature functions | 7 | 4 |
| Scalar signature with branch/fuel/RT outside current DAG opcode whitelist | 6 | 3 |
| C-source switch / case tokens (lexical, not emitted dispatch) | 16 / 34 | 0 / 0 |

These are static site counts, not executed instruction counts. `vector-assoc!` appears once in statemate because the `put` wrapper represents hundreds of calls; counting one spelling is not a low mutation count.

## Falsified initial hypothesis

There is no `case` form in either current workload. A deliberately narrow recognizer for a read-only same-slot integer selector test followed by two unchanged-state calls found five individual statemate probes and zero false-successor chains of length >=2; nsichneu has none. This does not prove that a stronger whole-CFG analysis will find none. It **does** deny evidence for a broad dense-jump-table optimization at the currently recognized sites.

Nsichneu's step functions call t1/t2 **before** testing `limit`. Jumping directly to the selected step would skip preceding state updates, callee fuel, and potential traps. Statemate's emitted source decomposes C switch/while state transitions into many vector-state helper continuations; merging them as a dispatch table based only on integer constants can cross writes or repeated checked reads. Both shortcuts are rejected.

## Current guard facts: bool is already allowed

Current `di-type` accepts **TY-I64 and TY-BOOL**, so widening an imagined i64-only guard to bool would add nothing. `di-body` is a bounded 32-instruction **straight-line** scalar certificate: it excludes branch opcodes, runtime operations, OP-CALL, and OP-FUEL. `di-shape` admits 1..5 scalar parameters and scalar result, slots/depth <=7. `di-admit` excludes immediate RET/RES2 successors and limits code growth to 256 sites /4,096 words with snapshot/rollback.

Thus vector-state functions fall outside the current scalar DAG contract for substantive semantic reasons; there is no authorization here to simply relax the type test. Existing `gn-small-tail` already handles restricted small <=1-argument tail functions and validates owned branch labels, inlined runtime operations, and fuel. Existing generic CALL/RET lowers to an epilogue plus branch when argc <=7. These optimizations must be accounted for before predicting removable frame cost. Counting 428/128 CALL/RET sites is an opportunity census, not evidence that those sites still use BL or full frames in measured machine code.

## Next generic hypothesis: bounded continuation-region fusion

Hypothesis: retain ordered checked state operations and every logical function-entry fuel/publication boundary, while compile-time-fusing a finite region of small direct tail continuations into one ordinary nonleaf machine frame. Names such as `s-123` or `step-45`, workload IDs, and state values must never be admission criteria.

Earliest experiment is **a current typed-producer observer only**, not candidate execution: produce exact FN/SIR/type/call-edge/frame/native emission maps for these two original workloads; prove readonly observer vs unobserved machine bytes equal; classify existing small-tail/generic-tail/wrapper admissions before implementing a broader rule. This will determine whether the frame/call hypothesis has remaining targets after existing lowering.

Possible initial region contract (proposal, not a verified emitter):

* Static direct tail edges only; one vector handle plus at most two scalar parameters; no FADDR escape, CALLI, RET2/RES2, unknown native wires, allocation, or transitive external effects.
* Closed forward-owned CFG, defined-before-read locals, explicit region-entry/exit mapping. Bound discovery (e.g. 32 FN /256 SIR) and emitted growth, with all-or-nothing rollback and unchanged generic fallback. Budgets are design parameters pending preregistration, not proven accepted limits.
* Every vector read/write keeps the original handle/index checks, ordering, alias-visible updates, and trap behavior. A vector pointer may not replace the checked handle unless current descriptor lifetime, mutation, alias, arena, and failure-prefix proof exists.
* Preserve **per original function** fuel transaction: private decrements, zero publication on exhaustion, context publication on successful exit, and pre-call fuel on trap where the original callee uses private fuel. Do not bulk debit a guessed total before state writes. Nested wrappers and loops keep their own charges.
* Preserve live caller prefix temps, x7 context/cache facts, locals, target ABI, fixups, each chosen exit, result handle, native arena counters/capacities, and budget diagnostics. Physical frame fusion must not silently claim equivalence under unmodeled OS stack exhaustion or stack-observing effects.
* Repeated mutable reads cannot be memoized across writes merely because the vector handle CID/definition CID matches. A proof/query result records ordered edges/effects and explicit alias/state assumptions; mutable input contents are not immutable definition content.

The desired win is fewer register shuffles/frame exits/entries between already-proven continuations. State operations and fuel are retained. No static estimate is a measured speedup.

## Secondary bounded hypothesis: signed-quadrant comparison recognition

Statemate includes a scalar helper equivalent to unsigned i64 `<`: `(if (< a 0) (if (< b 0) (< a b) false) (if (< b 0) true (< a b)))`. Current scalarDAG permits its types but not its branches; a generic closed-pattern rule could emit target unsigned CMP/CSET while preserving entry fuel and caller prefix/cache contracts. Recognize the exact typed expression/CFG, never the name `uless`. This small helper has only five source call forms; it is not a plausible sole explanation for a ~16x workload gap. A finite boundary model supports the algebraic hypothesis but is not an SMT proof or native qualification.

## Reproducible decisions and next gates

`pure-model-controls.py` records three finite model controls: signed-quadrant/unsigned comparison, the unsafe step-jump counterexample, and the unsafe eager-bulk-fuel failure-prefix counterexample. They are **models**, not actual Kotoba/native fault or ABI tests.

No candidate, native emitter, current observer run, production cache enablement, or performance adoption is authorized by this SOURCE archive alone. After current-producer binding, prepare finite execution SOURCE/go schema, independent review, exact runtime functional/trap/fuel/arena/high-i64/prefix/cap-negative controls, unchanged original19 compile/self-rebuild fixed point, and paired quiet full19 C comparisons. The root goal remains C-or-better on the full original workload scope; this record contains no official Embench score and no achieved goal claim.

For ComputeCID reuse, key the region proof by typed graph/reader-state+alias facts, analyzer version, code-growth budget, compiler/ISA/ABI and fuel/trap/effect semantics. ResultCID records accepted/refused region plus ordered edge contributions; transition receipts recheck current resource/caller state. Cache hit alone never authorizes suppressing mutable state operations or observable fuel.
