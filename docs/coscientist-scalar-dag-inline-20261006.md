# Bounded scalar call-edge graph expansion, 2026-10-06

One fresh original19 product/candidate/C campaign is independently qualified. Source commit44bfaa28c passes all seven required gates and independently audited committed integrated qualification. No C-or-better, official score, product entry switch or main release is claimed.

The candidate expands a rooted closed pure scalar call edge while preserving the original generic callee, caller frame and allocation. Admission accepts i64/bool parameters/result,1..5 parameters,<=7 locals/temporary depth,<=32 straightline SIR instructions, defined-before-read values and one final RET/END. Calls, runtime operations, memory, effects, fuel, division, f64, branches and malformed fields refuse. Existing specialized wrapper rules run first. No source or benchmark names select a rule.

Only already-framed original nonleaf callers admit. Original live earlier temps are saved before argument capture; sources are checked disjoint from x0..4. Callee locals occupy x0..6, temporary registers x9..15 and arithmetic scratch x16/17; x7/x8/x19..28 remain owned by the caller. Two38-cell generator-state snapshots distinguish pre-call rollback and post-save successful restoration. Unknown descriptors and cap exhaustion preserve normal calls. Actual compiler errors fail closed. Full emitted spans include argument/save/context and final result/protection instructions, with caps64words/site,4096words/module and256sites/module.

This is a new native compiler algorithm, covered by the one-off authoring exception; existing mechanical source-port rules do not implement it. Declaration identity is separate from the compiler/rule/target/ABI recipe. No runtime result memoization, authority reuse, effect elision or generic compiler theorem is added.

The baseline is the qualified eab3a7c2 seed at source2428e919d; current native generations2/3/4 are858392B SHA761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93.132actual callsites in11callee functions/39caller bodies change across aha-mont64,crc32,nettle-aes,sglib-combined,slre. Other14 original bodies are byte-identical, including the previously improved QR/XGB code.1117full-span inlinewords replace original call spans, net471words/1884B across all19.

Root fresh original19 inputs give95 exactresult/fuel matches+19fuel-one traps. Existing593 handwritten permanent fixtures/25658observations pass with unchanged original508/14523prefix, test/real machine bytes and function offsets. Nine committed readonly-loop regressions add117native observations. No hand-derived behavioral or refusal expectation is changed.

Independent original19 machine projection covers132expansions, originalcallee body-minusRET, originalsave/arguments/context and result/cache suffix,84717remaining tokens,16210edges,188literalwords and289private auxiliary entries.9altered raw/receipt packets fail. Native admission controls run17synthetic SIR cases across7actual source faults plus unchanged compiler,136retained runs. A initially masked undefined-local fault was corrected in the diagnostic input while preserving its original refusal; the nondetection is retained.

Independent typed controls:15genuine source programs/750fullstate pairs,60public scalar export pairs,150source mathematics/effect/trap cases,266real expansions including256sites in the module-cap source. Independent source interpreter and DAG certificate, observer/raw-machine correspondence, generic and FADDR coexistence and three actual native compiler-source faults are retained. Machine projection code reuse is disclosed; source mathematics/DAG oracle are independently authored.

Independent resource controls: original19 resource161pairs/46traps and fuel-prefix/ordinary266pairs/151traps, four new callers220pairs/30traps,10five-argument/extreme-i64/x19..28sentinel pairs. Omit-save and restore-pre-save native compiler faults each break8typed observations. Two actual raw restore faults fail. Exact64-word site admits,65falls back;256sites cap the257th call;4085used words trigger30subsequent rollbacks. Zero-site/one-word budget compilers reproduce baseline code/state. Same-M closed/open/closed reconstructs exact SIR/CODE with counters64/0/64. The original under-count fault actually reports64for65and wrongly admits; independent full-span counting detects it.

Root symbolic obligations: five arbitrary64-bit disjoint argument-capture queries, owned-register write set and growth-cap accounting are UNSAT. Overlapping swap, unsaved live temp and x8clobber controls are SAT. These are stated-assumption laws; actual source/emission audits bind the sets. They are not universal compiler soundness, arbitrary runtime replacement, compiler-heap budget-boundary or OS stack-limit proofs. Generator scratch expands by78words; emitted caller frames are unchanged.

The existing machine byte golden differs by7codewords. Independent full fixture projection explains exactly7calls to the same pure x+1 callee (FN218), each one-word BL becomes its original2-wordbody withoutRET. All36921remaining tokens,3741edges,24literalwords,30private entries,593function offsets and full pool relationship match; pool alignment gives24B net native growth.192handwritten observations for the changed fixtures retain their original expectations. The original golden FAIL is retained; a later golden update is allowed only as this explained artifact-byte update, never a behavioral/refusal relaxation.

Corrections retained: full-span accounting initially omitted final result placement; scalar snapshot repairs it before primary freeze. The old candidate is archived. Read-only observer afterBody metadata initially aliased mutable m2/m3; its corrected scalar end snapshot is byte-exact. Fixture diagnostics initially exceeded trace arenas; filtered diagnostics retain all applicable records and exact complete output blobs. Remote tar extraction lacked the modern filter keyword and failed before measurement; manual path/type verification of the SHA-pinned archive fixed setup without changing timing code or starting another campaign.

Portable native proof:15906799B archive SHAffbe90cd98940cde0c8b506262a305626b6a752e9d547ac7ab44d402bd583ae7,1433selected payload pins; three copied files suffice with Python3.12+. Saved finite proofs/observations, exactsource/native lineage,19machine/cap/fixture projections and independent source mathematics are recomputed without guests,solver,timing. Selection is not the complete owner pin sets. SMTstatuses are retained, not freshly solved by offline replay. Root replay and performance result receipts follow separately.

## Fresh aligned full19 measurements

All three arms use the same Apple M4 host and original full workload. Thirty accepted rotating triples per workload give570accepted/590attempted triples,1770raw arms;20rejected triples remain in evidence. The unchanged14bodies show no qualified variation, and there is no qualified regression. No historical timing statistics are pooled.

| Workload | Time reduction vs current product | Candidate/C time |
|---|---:|---:|
| Aha-mont64 |17.9677%|1.60350x|
| CRC32 |15.1993%|1.96552x|
| Nettle AES |17.5502%|15.0489x|
| Sglib combined |11.8544%|6.30526x|

Across all19 workloads the geometric elapsed time is3.903387% shorter, baseline/C8.0020815x becomes candidate/C7.6897293x. SLRE's1.6789% decrease is below the qualification threshold and remains neutral. These are aligned body measurements, not an official Embench score. C-or-better remains unachieved.

## Source adoption and permanent controls

The exact frozen source was adopted; its explained generated unit artifact golden includes7extra machine words. The formal module unit passes5227lines. New standalone16typed programs pass318native observations and19physical checks, with no observer/baseline/temporary-path dependency. Actual no-inline and wrong-argument compilers are detected. Product dependency inventory stays unchanged; one bootstrap test runner changes only the scaffolding counts.

A runtime boundary distinction was discovered and preserved: the product loader allows a completed straightline computation with remaining fuel0; the earlier diagnostic supervisor labels zero remaining as a trap after completion. Both sides of earlier pairwise observations used the same diagnostic supervisor. Those diagnostic trap counts are finite diagnostic classifications, not proof that the product traps after a successful final charged step. New permanent expectations follow actual instruction demand and retain this distinction.

## Verification status

Source commit44bfaa28ccb70252bf763e20de5321ced848f0e4 passes BUILD/ERR/G1/G2/G3/G4/G5 with current MANIFEST unity rebuilt to exact native fixed point. G1 uses the normal original19 single-iteration correctness sources; timing uses separately pinned original19 batch bodies, so their raw source hashes are deliberately distinct. A missing historical external G1 directory caused the initial setup failure; explicit current repository port paths correct setup without changing the gate or any golden. Integrated qualification is complete as recorded below. The source algorithm is a one-off authoring change because no existing AST refactor rule implements the new bounded admission/emission proof; existing behavioral/refusal goldens remain intact. The full own-source100% requirement and OS stack-limit/compiler scratch budget-boundary equivalence remain unproved.

## Graph rules, evidence and content identity

The experimental loop is hypothesis → rooted local admission → native emission → independent source/physical/resource controls → fixed point → one fixed full19 timing campaign → committed integrated rebuild. This follows the Simple-style local rewrite execution strategy. It does not implement general GP2 matching or DPO semantics. The bounded rule is directional (call→closed scalar body), preserves generic definitions, cannot recursively rewrite callees containing calls, and has explicit32-instruction/64-word/4096-word/256-site bounds.

The ten SMT obligations address stated i64/register/resource laws, not a proof of all compiler transformations. Native fault injection and exact physical projection bind those assumptions to this implementation; unchanged source behavior and capability boundaries are separately checked. No capability delegation/revocation model checker or TLA+/TLAPS proof was added in this change.

Definition content identity remains separate from build recipe identity. Source/compiler/rule/target/ABI and emitted-byte pins identify this experiment and its provenance. Hash equality attests content identity; it does not imply semantic equivalence or authorize execution. Effectful execution results are not cached or reused by this optimization.

The initial G1 setup failure and rejected overly broad source-hash equality assumption are retained as captured status/error summaries. The subagent did not save the original raw gate subtree before rerun; its earlier preservation statement was inaccurate and is corrected in adoption-initial-failure-capture.json. Final raw gate logs are retained. No claim of preserved initial raw logs is made.

## Committed integrated qualification

Source44bfaa28ccb70252bf763e20de5321ced848f0e4 yields3identical integrated generations,162objects/117frontend per generation. Command6142200B SHA1df5677800b7664a00992cc63eb6ba877b5933a750f181ddcb213c75604fc1bd; command/container/bin/objects match across generations. Frozen external closures308inputs and1766committed dependency contents are pinned. An excluded tracked .nbb symlink rejected safe archive extraction; exactarchive member/link metadata and partial extraction are retained. Registering exact44bf Git object/ref in the owned snapshot repaired launcher archive setup without altering source. No bootstrap compiler fallback occurred.

All19 measured batch programs produce exactly the measured native bytes and entry offsets. All391 committed corpus sources are selected upfront, including historical19 single-iteration correctness ports, so no new supplemental run is needed.391checker/391compile outcomes and all891export classification rows match the previous image. This is890executable rows (875stage0SAME,15existingDIFF) and one preexisting missing ->Reading row, not891successful executions.782full raw checker files normalize only exact recorded source roots before display truncation;1780native output/status files compare exactly.330images retain non-layout export signatures/provenance;28legitimate native code/layout changes are listed. Twelve refactor operation pairs match. These finite comparisons are not a universal theorem for all28changed programs.

The root and independent auditor each reread31086owned artifact hashes and21terminalpins. A fresh three-file offline replay recomputes21874included payload pins and all retained fixedpoint/source/provenance/19code/391391891/refactor comparisons without native guests or new timing. Archive39255514B SHAe2ea3f6bcbdc05a0fe2b3ae38087e821ab393487283107a1bcd542f3af1de018. No bin/amu switch, main release, official score, full own-source100percent or C-or-better claim.

## Next hypothesis: descriptor lifetime across known calls

Read-only source/ABI/call-closure analysis identifies120new-mode0 nonleaf functions/345static reads, including Picojpeg19/64 and Statemate57/169. These are applicability counts, not dynamic hit rates or predicted speedups. Positive handle equality alone is unsafe across arena_leave (RT232): release rewinds the used counts, and a new vector can reuse the same number with a different length. The original scoped vector need not escape for this to occur. Contents-only writes require a fresh element load.

Initial experiments must preserve existing modes and require original nonleaf frame, old saved-register count<=7, a newly saved3-register bank, bounded closed no-reset/no-unknown/no-capability/indirect call summary, and original-site handle/bounds/fuel/effect/partial-write checks. Unknown/reset boundaries invalidate or refuse. The finite lifetime model detects stale row, invalid released handle and stale element controls. Fresh9SMTqueries give6UNSAT stated-assumption laws and3SAT unsafe controls. Source/machine binding and actual native controls for the proposed rule remain required; these are not native optimizer evidence. An optional deeper native loader probe was not executed because its subagent turn was rejected by the service; it is not claimed as a test.

## Prospective hardware frontier (unimplemented and unmeasured)

A separate read-only audit pins the original19 workload sources, actual C bridges/build recipes and C disassembly. The C baseline has no CRC/AES/SHA crypto instructions, while EDN/Pico already use SIMD widening/narrowing. A measured-host receipt reports AES/SHA256/CRC32 support on the Apple M4; other targets need feature guards and software fallback. Three general structural candidates are an immutable IEEE CRC-byte recurrence, certified pure four-column AES round values, and bounded signed narrowing/rounding/rotation followed by SIMD value regions. Selection must use semantics and dataflow certificates, never workload or function names.

Finite source models verify CRC256 table entries/41 linear basis-and-zero cases, AES2816 table elements, and Pico262144 multiplication/131071 descaling cases; seven unsafe generalizations are detected. These are model certificates, not native optimizer proofs. Fuel prefixes, first validation, traps, ordered partial writes, arena usage, existing vector-i64 layout, register ownership and generic/FADDR fallback remain implementation obligations. Static applicability and counts do not establish a speedup or close the separate control/memory gaps.

[Portable frontier evidence](evidence/coscientist-scalar-dag-inline-20261006/frontier-README.md) replays102 selected pins with only three files and no guests or timing. C binaries are omitted from the new archive; exact hashes and the existing timing archive are the primary re-verification boundary. These candidates are unimplemented and unmeasured. Overall C-or-better, an official score and full own-source100percent remain unachieved.
