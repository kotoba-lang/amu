# PR CI in five minutes, by content addressing (design)

Status: design, not implemented. Tracking: JUN-358 (canonical), JUN-332 (history).
Replaces the 20-minute target of JUN-332/JUN-358 for the *unchanged-compiler* PR tier; the uncached
main and scheduled tiers keep their full, unbounded chain.

## 1. What a PR costs today (measured, run 40609475261 and its sibling workflows, 2026-10-28)

Job wall times (seconds). Workflows run in parallel; `needs:` edges give the chain.

| job | seconds | needs |
| -- | -- | -- |
| native-preflight | 116 | - |
| bootstrap-arm64 (root bootstrap 206, one-compiler derivation 212) | 434 | preflight |
| qualify-arm64 (gates 318) | 450 | bootstrap-arm64 |
| qualify-benchmark-arm (host 71, built+executed timing 427) | 534 | bootstrap-arm64 |
| derive-x86_64 (qualification 252, fixed point 148) | 429 | - |
| qualify-x86-shards (gates 308) | 435 | derive-x86_64 |
| qualify-benchmark-x86-factory | 314 | benchmark-arm, derive-x86_64 |
| native-checked-source x2 | 656 / 638 | - |
| native-definition-graph x2 | 473 / 266 | - |
| native-checked-definition x2 | 336 / 174 | - |
| native-definition-build x2 | 126 / 94 | - |

Critical chain: preflight 116 + bootstrap 434 + benchmark-arm 534 + benchmark-x86-factory 314 =
1,398 s (23 min) before queueing. Observed wall: about 20 min. No single job is under 5 minutes except the
small ones, so sharding alone cannot reach five minutes.

Earlier measurement (JUN-332, x86 mutant images): rebuilding the mutant image took 1,113 s and
executing it 81 s. Most gate time is **building**, not **executing**. That is the lever.

## 2. The Unison property we use, and the one we must not

Unison names a definition by the hash of its normalized syntax tree, so a build or a test result for a
hash can never be stale. Kotoba already has this identity: the `native-definition-cid`, `-graph`,
`-checked-definition` and `-build` workflows compute DefCIDs, SCCs and symbolic-relocation objects.

Use: **a build output is a pure function of content**, so it may be reused when every input hash matches.
`scripts/seed/content_reuse.py` already does this per call, keyed by file hashes.

Do not use (owner rule, JUN-358): **verdicts, approvals, fuel state, side effects and receipts are never
reused.** Unison would also cache test results; we do not. A reused image is still run fresh by every gate
(fresh target, link, fuel, context and admission). This costs little because execution is the small part
(81 s of 1,194 s in the measurement above).

So the invariant is: reuse artifacts, re-execute every gate, rerun everything uncached on main and on
schedule.

## 3. Three tiers by change class

| tier | trigger | what happens | target |
| -- | -- | -- | -- |
| T0 | the PR does not change a definition the compiler image depends on (gates, tests, docs, workflow text) | every image is an artifact hit; all gates execute fresh, sharded wide | <= 5 min |
| T1 | the PR changes compiler definitions | rebuild only the reverse closure (changed DefCIDs, their SCC and dependents), reuse the rest; all gates execute fresh | <= 5 min once persistent object reuse is qualified (JUN-358 steps 2-6); until then the T1 time is what it is today |
| T2 | push to main, schedule, dispatch | full uncached chain, C0 included | unbounded, unchanged |

A change class is computed from content (the set of changed DefCIDs against main's index), not from paths.
Paths stay as the coarse first filter only.

## 4. Design

### 4.1 The artifact store

Key = sha256 over: the producing image (first), every input file or DefCID named by the call, argv, the
full environment with the output directory as `$OUT`, host ISA, and `REUSE_VERSION` (the existing key
material of `content_reuse.py`; DefCIDs replace whole-file hashes as the unit in T1). A hit restores outputs
and verifies them against the recorded pins; any mismatch reruns the call.

Where it lives: the GitHub Actions cache, **written only by push-to-main and scheduled runs**, **read-only
in pull requests**. A PR (including from a fork) can therefore not poison what a later run reads. A miss
falls back to building. The store is an optimization with no authority: deleting it changes time, never a
verdict.

What is stored (the build-dominated rows of section 1): the bootstrapped compiler images (root -> F), the
x86_64 images and the packed core P, the mutant images of the gates, the factory and benchmark images, the
wasm32 case modules.

What is not stored: any stdout/stderr verdict, any receipt, any admission result.

### 4.2 Flatten the critical path (no semantic change)

Edges are removed only where they carry no data. Checked against the workflow:
- `qualify-benchmark-x86-factory` **does** consume data from `qualify-benchmark-arm`: it downloads the
  `native-benchmark-arm-host-reference` artifact and checks exact equality with the executed ARM results
  (and `native-x86-derivation` from `derive-x86_64`). The edge stays, but the arm side is split so the host
  reference is a short job of its own (host 71 s) and the 427 s timing/mutation work leaves the chain; the
  x86 factory then waits for the 71 s part, not for 534 s.
- `native-preflight` (116 s) gates `bootstrap-arm64`. Not yet checked whether `bootstrap` consumes its
  output; if it does not, the two run in parallel and the aggregate guard fails the run on a preflight
  failure. To be verified before changing it.
- Benchmarks split into per-benchmark shards (the built-and-executed timing 427 s is a sum over independent
  programs), each its own runner.

After 4.1 on T0 the chain is: restore (<= 30 s) -> fresh gate execution per shard (the measured execution
parts, tens of seconds each) -> aggregate. After flattening alone (no cache) the chain would be roughly
bootstrap 434 + the 71 s host reference + the x86 factory 314, about 14 min (an estimate from the step
times above, not a measurement). Worth doing before the store exists, but it does not reach five minutes
without 4.1.

### 4.3 Definition-level keys (T1)

Move the key unit from files to DefCIDs and SCCs: a change to one definition invalidates its SCC and
dependents only. This is the existing JUN-358 sequence, unchanged: seal the abort control row, nominal and
schema closure, SCCs above 8, a trusted producer joining source, image, dependencies, target/ABI/layout and
symbolic relocations, then measurement on one native x86 host (cold, warm, changed, corrupted, wrong
dependency or resource).

### 4.4 Guards that keep it honest

- The aggregate job still requires **every** original gate row and argv (17 x86 gate rows today).
- A run records, per step: reused or built, the key, the artifact hashes. Receipts keep what ran.
- A scheduled "paranoid" run rebuilds every artifact uncached and compares byte for byte against the store;
  any difference is a determinism bug and fails.
- A negative control per reuse step: a changed input, a corrupted artifact and a wrong key must each rerun
  or fail, never hit.
- The five-minute budget is measured and printed per run (wall clock of the workflow), initially as a
  report, not a failure; it becomes a check when T0 has held for a week.

## 5. Dependency order (what blocks what)

0. Amu #1568 (pool/scope limits; in CI) lands first. It changes pins and the wasm32 runtime; every CI
   change below must be rebased on its pins.
1. Measure: record build-versus-execute per step on one host (extends the existing observer). Without it
   the estimates in section 1 stay estimates.
2. Flatten the critical path (4.2). Pure scheduling; independent of the store. Estimated 20 -> about 14 min.
3. Artifact store, read-only in PRs (4.1) for the bootstrap images and mutant images. Expected T0 <= 5 min.
   Needs step 1 for sizing and the negative controls of 4.4.
4. Remaining images (benchmarks, wasm32 modules) join the store.
5. Definition-level keys (4.3) = JUN-358 steps 2-6, in that order. This is the only part that makes T1 fast
   and it is the longest.
6. #1544 (named-refusal diagnostics) and #1559 (bounded code cache) are re-implementations that each cost
   several CI cycles; they are cheaper after step 2 and 3, so they go after them, #1544 first (smaller, no
   manifest change), #1559 second (49th module).
   #1443 and #1428 stay unmerged (regression and public-entry risk, see their reviews).

## 6. Not decided here

- Reusing *verdicts* of pure gates (Unison's test cache). Faster still, but it contradicts the owner rule in
  JUN-358; it would need an explicit owner decision with a determinism argument per gate.
- Larger or more runners. Costs money; the first target is to not need them.
- Whether the store should be the Actions cache or an OCI/object bucket (cache has size and eviction
  limits; the choice does not change the design).

## 7. Acceptance

1. Per-step build/execute table from a real run is recorded (step 1).
2. A T0 PR completes in 5 minutes or less on real CI, all original gates executed fresh, uncached main
   passing (steps 2-3).
3. The negative controls of 4.4 pass.
4. T1 is stated with its measured time; it is not claimed under 5 minutes before step 5 is qualified.
