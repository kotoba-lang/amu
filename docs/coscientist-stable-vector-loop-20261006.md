# Stable-vector readonly-loop experiment, 2026-10-06

Decision: reject v1. Correctness gates passed, but one fresh fixed performance campaign found no qualified improvement. The qualified product remains unchanged. C-or-better across the original Embench19 and complete own-source selfhosting remain unachieved. This document records an excluded native optimizer experiment, independent audits and a separately preregistered successor.

## Candidate and hypothesis

The candidate keeps a stable vector's validated length and items base in three explicitly owned/saved callee registers. A runtime flag starts false; the first actual read executes the original handle validation before capturing the descriptor. Subsequent reads retain unsigned bounds, traps, fresh element loads and the original fuel charges. It does not memoize results or move first validation before a branch or charge.

Admission is a finite whole-function rule: leaf, one typed vector parameter among at most five parameters, scalar other parameters, readonly closed body, backward edge, at least two vector reads, and a proven unchanged chosen vector local. Calls, indirect calls, capabilities, allocation, writes, floating operations, unknown runtime operations and uncertain origins refuse optimization. The v1 origin query is linear and refuses control joins. Body scan is capped at 8,192 instructions; frame/register constraints fall back to the original path. New algorithm authoring used the documented one-off research exception; this is not a product mechanical refactor.

Actual admission is five functions in four workloads: nsichneu FN261, picojpeg FN46, sglib-combined FN8/FN9, tarfind FN5. All five originally had no frame; the candidate creates frames of 80, 112, 112, 112 and 144 bytes respectively. Fifteen other original workload images are byte-identical to product. Every one of the twelve actual transformed reads retains a runtime CBNZ flag guard; there is no compile-time validation omission in these bodies.

Generations 2/3/4 byte-match at 844,152 bytes, SHA256 `cb83290d6d6ef471570adac42c891be0e084d836697a56f26617b026f2145769`. Generation 1 differs. The unchanged qualified product is 839,648 bytes, SHA256 `f00e38312ac7278b1b597207054cba521fafa28f30f03d20d237a07fd59647e2`.

## Actual verification

Root and independent agents verify separate evidence:

- All 593 permanent native fixtures / 25,658 observations pass; the original 508 fixtures / 14,523 expectations remain exact prefixes. Real/test emission bytes and offsets agree. No golden expectations were changed.
- Original19 full five-input matrix gives 95 actual result/exact-fuel matches, plus 19 fuel=1 trap matches against product. These are correctness runs, not performance samples.
- Independent machine audit verifies twelve exact guarded-read replacements, 74 net added words, 84,513 retained tokens, 16,304 projected edges, 188 literal words and 289 private auxiliary destinations. Twelve altered machine/fixup/literal/entry packets refuse verification.
- Independent constructor controls cover 448 native full-state pairs, 56 mathematical cases, additional two-vector/ABI cases and actual unsafe source/register mutants. Independent admission gives seven accepted and seven refused fixture shapes. Runtime validation state and handle origin are distinct obligations.
- Independent resource audit checks 161 original resource pairs (46 traps), 209 fuel states (151 traps), sixteen native callee-register sentinel pairs, frame-ceiling fallback and unsafe source/register mutations. Reserved registers stop at x28; frame pointer x29 remains intact.
- Local SMT checks yield two UNSAT equivalence/bounds queries and five SAT unsafe-assumption controls. They assume descriptor immutability and the stable-handle witness, and do not establish a universal compiler proof. The offline replay checks retained statuses without rerunning a solver.

Guest fuel/arena parity is verified for these finite controls. Native OS stack-limit boundary equivalence is unproved because frames grow. No adoption was made. No general concurrency, authority, TLC or TLAPS proof is asserted.

`implementation/ports-correctness.json` inside the native archive is explicitly the copied baseline oracle. Actual candidate artifacts are identified by `ports-build.json`, `observer/admission.json` and the fixed-point hash. An initial root comparison against the copied oracle was corrected before timing; no candidate artifact was changed. The retained authoring receipts also record a prebuild helper-name correction and a missing fixture-support import repaired using the unchanged support file.

## One fresh C comparison

Authorized zebulun Apple M4 hosted rotating product/candidate/C measurements of the four changed original bodies. The pinned C source, compiler recipe, runner and original inputs remain unchanged. Thirty accepted triples per workload give 120 accepted / 126 attempted triples; six are rejected with raw receipts retained. All 378 attempted arm samples are archived. No earlier campaign is pooled into these means.

The fixed gates require load <= 4, background CPU idle >= 90%, intervals >= 50 ms with a 300 ms calibration target, relative sample SD <= 10%, speedup >= 1.05 and an absolute gap exceeding summed sample SD. All four campaigns are stable. None qualifies as an improvement, regression, or C-or-better result.

| Original body | Product mean ns | Candidate mean ns | C mean ns | Candidate / C |
| --- | ---: | ---: | ---: | ---: |
| nsichneu | 693.102 | 692.966 | 76.535 | 9.05x |
| picojpeg | 212,085.734 | 210,929.514 | 11,009.913 | 19.16x |
| sglib-combined | 40,911.986 | 41,039.828 | 5,795.331 | 7.08x |
| tarfind | 14,299.220 | 14,434.640 | 1,005.985 | 14.35x |

Independent replay recomputes means/SDs, accepted/rejected rotations, calibration, calls, background CPU accounting, source/native/C/runner/fuel pins and nine deliberately altered timing packets. This is an aligned native body comparison; it is not an official Embench score or a fresh full19 aggregate. The product is not promoted, integrated rebuild is not repeated, and the rejected candidate is not retimed unchanged.

## Successor preregistration

[Next hypothesis](evidence/coscientist-stable-vector-loop-20261006/next-hypothesis.json) requires an already-framed original leaf and replaces the linear origin query with a bounded ALL-predecessor query. Each backward path must end at a last temporary definition that reads the chosen vector local. The same proof applies to every write of that local, including self-tail-loop updates. Other definitions, undefined entry paths, unresolved cycles, malformed CFG and shared budget exhaustion refuse optimization. Runtime validation flags remain at every read.

Read-only analysis of exact original19 SIR examines 98 eligible shapes. The general rule would add qrduino FN62 and xgboost FN15; the original-frame > 0 guard excludes all five v1 admissions and retains these two. Names identify evidence only and do not enter admission. Estimated frames are 144 -> 160 and 144 -> 176 bytes; estimated word growth is 21 and 15 words, with possible literal-pool padding. These are static estimates, not compiled artifacts or speed claims. Frame growth is a hypothesis variable, not a demonstrated cause of v1's negative result.

CFG construction is O(N+E), E <= 2N. Each rooted origin query costs O(N+E), and up to N queries can cost O(N²); a shared 131,072 visited-node cap bounds query work, with fallback on exhaustion. Eleven diagnostic counterexamples/budget controls pass; these mutate diagnostic SIR and are not typed/native executable proof. The successor needs implementation, fixedpoint, existing regressions, original19 semantic checks and independent native machine/CFG/ABI/resource mutation audits before a new changed-body C campaign.

Definition content identity remains distinct from generator/rule/ABI/target provenance. A computation cache would additionally require arguments and all observable state; none is introduced here. Capability authority is not inferred from a CID or optimization proof.

## Portable evidence

[Evidence index and hashes](evidence/coscientist-stable-vector-loop-20261006/evidence-pins.json), [root replay receipt](evidence/coscientist-stable-vector-loop-20261006/root-replay.json).

- Native archive: `native/native-proof.tgz`, SHA256 `d0b8e580a3c7bbad4b2a774e308dc1f8b81dee824aefa9d373b98f8b57ad5d3c`, 11,165,052 bytes, 1,020 payload pins. Run `python3 native/replay.py` with Python >= 3.12 alongside its manifest/archive. It rechecks saved native observations, fixture expectations, sources, fixedpoint and machine/constructor/resource proof data without a checkout, compiler, guest execution, network or solver.
- Timing archive: `timing/timing-replay.tgz`, SHA256 `2cfe3215c663449fc8e82da0a4569a6e41d7f78d55b25a62a8bf3f0f00c0f00f`, 801,656 bytes. Extract into a fresh directory and run `python3 amu-stable-loop-timing-replay/team-timing/timing-audit.py`, then `checker-calibrate.py` from the same script directory. Binaries are hashed, never executed. Primary raw campaign archive and preflight are also retained.
- CFG: run `python3 cfg/replay.py` alongside owned JSON inputs to repeat the 98-shape original19 feasibility analysis. Control receipts are retained separately.

The root independently executed all three portable replays from the versioned copies; all passed. No fresh native, timing or solver run occurred during replay. Independent assignments accelerate verification while keeping implementation, oracle, measurement and promotion decisions separate.
