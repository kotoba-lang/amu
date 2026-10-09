# Private length layout: native proof passes, performance unqualified

The [previous private-length candidate](coscientist-private-length-clones-20261006.md) passed semantic proof but regressed. Its causal audit contradicted loss of existing fusion/descriptor/private ABI optimizations. This prospectively registered successor changes only native emission placement: each original generic function is followed by its private versions, in original source order. It preserves all contexts, source instructions, calls, labels, safe facts, public exports and function-address contracts. It does not remove generic bodies or select benchmark names.

The optimizer is native Kotoba, built by native amu. Complete original and clone FN/END partitions and metadata are validated before emission. Each range is emitted once; a fusion crossing a body boundary refuses. A separate ephemeral origin map lies beyond the source safe-map region. Open, no-clone and refused preparation paths keep the original sequential generator. This excluded new algorithm is a one-off research authoring exception, not a mechanical product refactor. Product, workload sources and golden files remain unchanged; semantic DefCID is separate from the new compiler/layout/artifact recipe.

Native generations1/2/3/4 are identical **902,456 B**, SHA256 **`b13e68066dd54ba604f9bb989106d9412c75db7012d46469eb388b74c0eb837d`**, offset0. All original19 targets build. Fourteen are product-byte-exact; matmult-int, nsichneu, picojpeg, statemate and ud differ. All19 native sizes equal the preceding v3 candidate. An initial author report incorrectly inferred16/3 from guard sites; authoritative target hashes established14/5 and the report/inventory were corrected without source or binary changes.

Independent qualification before timing:

- A read-only native observer reproduces all19 target bytes/offsets. Compared with frozen v3 observations, every pre/post SIR/FN/context/fact/safe record agrees. The auditor projects85,210 exact ordinary words,19,795 branches,66,525 source intervals,10,944 fixups and578 private aux1 entries. There are **zero added or removed instructions**. Five code/entry/fixup/source calibration faults refuse. Every physical body and instruction is covered despite reordered function entries; literal pool payloads remain exact.
- Original19 recorded results/fuel/fuel1 traps and209 full supervisor groups agree with the qualified product. Native current593 fixtures/25,658 observations pass without expectation changes. Real/test code, literal bytes and function offsets agree. Original508/14,523 prefixes remain unchanged.
- Twelve original constructor/alias/branch/loop/indirect/public controls pass304 full-state comparisons. An actual compiled mutant omitting private-version emission refuses an otherwise accepted source with E4203 undefined branch target.
- Resource boundary pairs across original19 pass161 comparisons, including46 resource traps and actual partial vector contents. Pristine same-M closed/open/closed regeneration restores calls/counts and exact native code. Six bad undo and ten malformed partition/map controls refuse. Four actual compiled restore/validation/emission mutants are detected.

The [complete source/native/raw evidence archive](evidence/coscientist-private-length-layout-20261006/native-proof.tgz) has516 pinned artifacts. [Extracted independent replay](evidence/coscientist-private-length-layout-20261006/replay.json) verifies every pin, recomputes the machine audit and all25,658 retained expectations from the frozen table, and rechecks304/161/209 raw state comparisons. It makes zero fresh native executions; actual execution evidence and harnesses are retained. Guest state equality does not imply identical compiler transient allocation. The layout scan may cost original-functions×clones during compilation. No universal compiler/CFI/authorizer theorem or TLC/TLAPS run is claimed.

## One fresh aligned native comparison

All native proof gates completed before the new zebulun M4 campaign. The existing fixed protocol rotates product/candidate/C, requires30 accepted triples per workload, maximum load4, background idle≥90%, minimum interval50ms and relative SD≤10%. Qualification requires speedup≥1.05 and mean gap greater than the sum of SDs. Rejected samples and calibration data are retained. Five changed original workloads are freshly measured; fourteen byte-identical targets are not represented as new measurements. This is an aligned native comparison, **not an official Embench score**.

| Original workload | Product mean ns | Candidate mean ns | C mean ns | Decision |
| --- | ---: | ---: | ---: | --- |
| matmult-int | 3328.076 | 3201.204 | 922.812 | Speedup1.040 and mean gap below sum of SDs; unqualified |
| nsichneu | 703.414 | 701.742 | 77.456 | Within variation |
| picojpeg | 211209.421 | 210255.833 | 11064.941 | Within variation |
| statemate | 520.085 | 704.178 | 31.220 | Candidate relative SD17.372%; **unstable, no qualified performance conclusion** |
| ud | 539.864 | 538.525 | 53.363 | Within variation |

The campaign is terminal:150 accepted triples from155 attempts. No workload qualifies as an improvement or C-or-better. Statemate raw product/candidate SDs are15.130/122.330ns. Its apparent slower mean is not a qualified regression because the original stability ceiling fails. The isolated placement experiment does not qualify adoption; no product promotion, integration rebuild or unchanged-candidate timing retry follows. The previous v3 campaign remains a distinct experiment and is not pooled with this one.

The [raw timing audit](evidence/coscientist-private-length-layout-20261006/timing-audit.json) and [extracted timing replay](evidence/coscientist-private-length-layout-20261006/timing-replay.json) recompute all150 accepted triples, checksums, fuel/result/C pins and decisions. [Complete raw timing package](evidence/coscientist-private-length-layout-20261006/timing-results.tgz) retains rejected attempts, samples and exact comparison binaries.

The next step is diagnostic dynamic hot-path evidence to choose a general graph rewrite or layout policy: identify actually entered logical functions/source intervals and preserve original result/fuel/trap/resource ordering in a distinct trace artifact. Static code growth and displacement alone are insufficient to establish cache or predictor causation. Trace instrumentation is not a performance artifact; no runtime result/capability cache is proposed. The full original19 C-or-better goal remains active and unachieved.

Portable replay: `python3 docs/evidence/coscientist-private-length-layout-20261006/replay.py` and `python3 docs/evidence/coscientist-private-length-layout-20261006/replay-timing.py`.
