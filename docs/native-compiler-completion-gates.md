# Native compiler completion gates

The progress gauge covers the entire requested delivery, through merged main,
post-merge verification, tracking completion and task cleanup. It counts
completed gates; it is not an estimate of elapsed time or remaining effort.
Only all ten completed gates mean 100%. Bootstrap evidence does not complete a
public-product gate.

Current gauge: **2 / 10 gates complete**. Gate 3 is in progress.

| Gate | Status | Evidence or remaining acceptance |
| --- | --- | --- |
| 1. Native measured-core compiler and packager experiment | Complete for its stated bootstrap scope | `seed/MANIFEST` / `41-a64gen` lineage preserved; standalone native compiler generates byte-identical G3/G4 core containers; native FS2 packager executes. See the bootstrap progress report. |
| 2. All 19 native Embench correctness workloads | Complete for the experimental toolchain | All nineteen original `bench-verify(1)` workloads pass with the recorded native chain and empty guest grants. This is correctness evidence, without a new performance score. |
| 3. Current candidate integration | In progress | Main `d13c486e` and PR #1428 head `588a96a4` (quote reader, FARM roots) are merged into this task branch at `0fb68cb6`; the only conflicts were three concurrently ported `.cljk` files, kept from main. Requalification is **not** passing: `selfhost-bootstrap.py` fails for the merged input (S2 SIGILL, exit 120). Controls: main alone passes S2 = S3; the pre-merge checkpoint and PR #1428 alone (SIGTRAP) fail. Receipt: `gate3-pr1428-integration.json`. Remaining: rerun the explicit FS1 bootstrap-snapshot recipe for the new delta and localise the #1428 failure with its owner. Main remains unmerged. |
| 4. Whole canonical dependency closure | Pending | Complete and qualify owning canonical source ports, neutral Form ownership, public identity domain, locks and Definition CIDs. The whole-CLI audit currently refuses because `kotoba.sema` is missing; the native 72-decision routing test is not locked-build success. |
| 5. Public import and CLI | Pending | Replace exit 69 with the admitted compiler; execute dotted IDs, legacy aliases and locked imports, default Kototama output, explicit targets and refusal cases. Preserve lock failures without an unpinned or hosted fallback. |
| 6. Whole native self-rebuild and runtime qualification | Pending | Compiler, CLI, packager, build graph, gate and controller generations use the same pinned canonical closure; retain verifier/seal/profile bounds, native target qualification and forbidden-process evidence. Execute positive/refusal/authority/resource/path/race/cleanup gates, including the preserved failure corpus. |
| 7. Final admitted-toolchain Embench | Pending | Repeat all nineteen complete correctness workloads with the final admitted toolchain. Any new performance score needs fresh measurements and host qualification for that exact toolchain. |
| 8. Review and main merges | Pending | Review and repair dependencies, then merge native #205 before Amu #1428 after the preceding acceptance gates pass. Preserve branch/WIP/history and keep execution foundations in their own repositories. |
| 9. Post-merge main verification | Pending | Read back exact remote main ancestry/content; finish available main CI and public import/CLI smoke tests, fixing failures. Keep all user-specified disabled Actions disabled; record unavailable gates accurately. |
| 10. Tracking completion and cleanup | Pending | Record final commits, verification and limitations in Linear, mark Done only when acceptance is met, and remove only verified task residue after merge. Preserve unrelated WIP, untracked files, stashes, branches and broken worktrees. |

Detailed native results and qualification boundaries:
[native-compiler-bootstrap-progress.md](native-compiler-bootstrap-progress.md).
The public CLI and main merges remain incomplete while any required gate above
is pending. Absence of workflow runs is not a CI pass.
