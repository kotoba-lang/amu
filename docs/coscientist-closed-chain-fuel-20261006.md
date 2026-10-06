# Closed-chain fuel register: proof passes, performance promotion rejected

The [original statemate fuel census](coscientist-statemate-fuel-census-20261006.md) found555 of806 first-body charges and555 of739 subsequent-body charges in closed mode2 functions. This actual native compiler candidate carries those charges in x8 across proved private tails. Full native proof passes, but one fresh unchanged-rule product/candidate/C comparison does not qualify an improvement. Keep the product unchanged. C-or-better on the original19 remains unachieved.

## Candidate contract

Reuse the original typed closed mode2 Vec-to-Vec admission: one parameter, at most3 locals/temporaries, no frame/spills/allocation/capability/floating/returning/indirect/unknown calls. No new source shape or benchmark name is admitted. Set fuel mode2 separately from the original leaf-transaction mode1.

Public entry emits the existing `MOVZ x5,#0` marker followed by `LDR x8,[x7,#CTX-FUEL]`. A private tail can skip both only with the original positive completed-access witness, unchanged actual outgoing local, and proved closed target. The guarded linker recognizes aux2 only for a terminal B whose target begins with both exact instructions; other transfers stay public. Private transfer preserves x8 without a store/reload. Other returns/tails publish current x8.

Every original charge remains. The original five-word context load/decrement/check/trap/store becomes the four-word register decrement/check/zero-publication/trap sequence. On successful execution there is no added fuel store. Cold handle/bounds/division failure paths publish the current x8 before their original trap, and all affected success/hit skips adjust for that word. Exhaustion publishes zero. This preserves the **original mode2 current-fuel** observation, rather than borrowing unrelated masked-leaf transaction publication semantics. Original assignments, accesses, runtime context layout and resource limits remain.

The new generator/layout ABI and independent excluded harness are one-off algorithm authoring, not mechanical product refactoring. Product files, generated golden and original workload sources are unchanged. Neither definition/result memoization nor a Node/JVM/nbb fallback is introduced. Recipe/source/compiler/ABI identities are separate from semantic DefCID.

## Native and mathematical evidence before timing

- Candidate native generations2/3/4 are byte-identical840,920 B, SHA256 `da56b44a5f5cd9736009016e2cd85b1b37613b9c51717c2623a326fc18f72500`; generation1 differs.
- Current593 authoritative fixtures and25,658 native expectations pass without golden changes. The diagnostic test linker is adapted to the guarded aux2 ABI; its code/literals/function offsets agree with the real candidate linker.
- 11,052 full supervisor groups pass:9,120 independent literal/local/alias/control/loop/wrapper states,1,445 all17 integer/comparison/unary operation states (including divide-by-zero and MIN/-1 traps),240 diamond/alias/root/cold-entry states,209 original19 states and38 original resource-limit states. Results, trap/exit, remaining fuel, resource counts and partial vector contents are checked.
- Native source admission rejects119 field/operation mutations, plus open/duplicate-label/incompatible-callee controls. Six actual layout mutations reject bad aux, marker, fuel load, BL opcode and fixup kind.
- Three mutations of actual candidate machine code—missing cold publication, stale private reload and reversed exhaustion branch—are independently detected by full native state observations. The correct candidate agrees with the product on each control.
- Four abstract64-bit fuel laws have UNSAT negations; three unsafe publication/reload/exhaustion equations have SAT counterexamples. They establish only those equations under their assumptions, not whole-compiler correctness.

A read-only observer reproduces exact candidate bytes/offsets on all19 original workloads. Original SIR and function frame/local/depth/leaf metadata agree. Eighteen images are byte-identical. Statemate grows87,716 to91,688 B (21,929 to22,922 words); more cold-path/static entry code is not itself a speed claim.

Independent machine validation normalizes exactly773 closed charge sequences,390 public loads and1,376 cold-trap/public-escape stores. Every remaining emitted opcode and all3,320 normalized branch destinations agree with the product. All289 aux2 private transfers land two words after the exact public prefix. Public calls remain public; cold stores map to the original failure nodes. This is stronger than simply comparing code sizes or counts. It assumes valid typed admitted SIR and supervisor metadata.

Audits caught test-authoring errors: the historical test helper duplicated fixture families already included in current593; the old test linker rejected aux2; numeric condition/fixup constants were initially guessed incorrectly; and an ns4 refusal audit incorrectly demanded byte identity across globally relocated call targets. The diagnostic adapters now reuse current unique fixtures, derive source constants, validate both entry instructions, and compare unchanged refused opcodes with relocation separated. Semantic expected outcomes and performance thresholds are unchanged. Failures/corrections are retained. No optimizer source changed after the native proof before timing.

## One fresh comparison

Quiet zebulun is arm64 Apple M4/Mac16,10. The same original statemate workload, pinned C/reference runner and pre-registered rotating three-arm protocol execute30 accepted triples from31 attempts. The rejected triple is retained. All arms satisfy load/activity and relative-SD admission.

| Original statemate, ns/body | Mean | Standard deviation |
| --- | ---: | ---: |
| Current native product | 519.867 | 14.433 |
| Fuel-register candidate | 505.307 | 15.037 |
| C | 30.202 | 0.312 |

Candidate mean time is2.801% shorter (product/candidate1.028815x). It fails the original>=1.05 speedup threshold; the14.560 ns gap is also below the29.470 ns summed SD. Neither gain nor regression qualifies. Candidate/C is16.730646x. These are aligned complete original-body timings, **not an official Embench aggregate score**. Do not compound prior experiments' gains or retime identical code until it happens to pass.

Independent raw-row audit verifies admission, statistics, source/native/C hashes, entry offsets, exact fuel, fixed-point identities and sealed proof inputs. Extracted replay recomputes retained hand oracles, instruction/CFG comparisons and raw timing. Replay does not repeat native execution or measurement. The performance prerequisite failed, so skip adoption gates and integrated product rebuild; the candidate is not promoted.

## Next registered diagnostic

Compute generic closed-callgraph return-identity and fixed-vector-length summaries, then determine where constructor-established length and constant indices can remove repeated bounds checks. Original statemate constructs169 items, but proof that this fact safely reaches each callee is still missing. Public exports must retain their generic route. Local/branch/SCC/alias transfers must erase unsupported facts, and unknown/indirect/effectful/handle-changing paths must fail closed. Vector length immutability, allocation/resource failure, original fuel/access/trap order and source-name-independent admission are required.

This diagnostic is unimplemented and does not claim speed. A subsequent specialization needs independent native/mathematical/source/machine/mutation proof, current593/25,658, a native fixed point, all19 original states and one distinct prospectively registered C comparison. The C-or-better goal keeps its full scope.

Evidence: [summary](evidence/coscientist-closed-chain-fuel-20261006/summary.json), [sealed preflight](evidence/coscientist-closed-chain-fuel-20261006/preflight.json), [timing audit](evidence/coscientist-closed-chain-fuel-20261006/timing-audit.json), [fuel ABI](evidence/coscientist-closed-chain-fuel-20261006/internal-abi.json), [law proof](evidence/coscientist-closed-chain-fuel-20261006/law-proof.json), [native source, baseline snapshots, machines and state histories](evidence/coscientist-closed-chain-fuel-20261006/native-proof.tgz), [all accepted/rejected timing and pinned C](evidence/coscientist-closed-chain-fuel-20261006/timing.tgz), [next hypothesis](evidence/coscientist-closed-chain-fuel-20261006/next-hypothesis.json), [extracted replay](evidence/coscientist-closed-chain-fuel-20261006/replay.json), [archive hashes](evidence/coscientist-closed-chain-fuel-20261006/archive-manifest.json).
