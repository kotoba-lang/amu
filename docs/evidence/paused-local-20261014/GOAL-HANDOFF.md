# Kotoba C-performance handoff — 2026-10-14

**USER-DIRECTED PAUSE. Start with [START-HERE.md](START-HERE.md).** This pause supersedes the earlier request to resume the goal panel. Do not optimize, measure, fix, merge or deploy until the user explicitly requests a new resumption. This document and `pause-receipt.json` supersede older active notes and CI watcher state.

The objective remains unmet: total Kotoba performance at least equal to C on all 19 original benchmark programs. No 5% minimum-gain cutoff applies. Preserve all 39 images and original 483 observations (95 profile, 76 low-fuel, 312 interaction).

## Goal and budget state

The user explicitly requested stopping and preparing a handoff because the weekly allowance was getting low. `update_goal(paused)` confirmed **paused** at 2026-10-14 03:02:36 UTC. The objective remains unmet. The previous goal-panel resume question is superseded; there is no outstanding request for the user to resume now. A later explicit user request and a fresh goal/allowance check are required before restarting work.

Last pre-pause allowance snapshot (historical, not refreshed during closeout): ordinary usage allowed, weekly 54% used / 46% remaining, paid credit balance 38077.1419195000. No additional paid spending is authorized; the balance was already below the earlier 40000 floor before the weekly allowance resumed. Do not interpret remaining allowance as authorization to continue during this pause.

## Adopted main and complete fresh comparison

- PR #1312: https://github.com/kotoba-lang/amu/pull/1312 — merged normally, all 20 CI checks successful and all review threads resolved.
- Main: `43524a1ce142538c028a4b3bf57edabc6e8a2d85`.
- Source: `795a8f544b67452cf3a04db620d0d20ed93cb712`.
- Unity: `88aa8e5f6fe0119b0f1d796668c451f67ad19b5e3d577c4b8e5676bb83ab1495`.
- Native compiler: `0139f2cb69b6a4166262c1851d7bfb0802715a2ba705ca2139dd015541791df7`.
- Adoption readback: `../seed-copy-chain-forward-20261014/main-integration-receipt.json` verifies source20, unity16, native/container, loader, golden19, all20 CI, ancestry and evidence.

The available-value forwarding change observed 1.3527034132913118% shorter statemate elapsed time in paired round 113, with both pairs positive. This is one exploratory cycle, not a stable statistical claim.

Full round 114 is complete:

`../embench-total-C-round114-copy-chain-forward-20261014-v1/final-summary.json`

All 19 native + 19 newly timed C observations independently pass, all on the first attempt. Native geometric score 12745.412129167858; C 34262.179670997066; **Kotoba elapsed / C = 2.688197080154679**, so C is faster. Do not attribute the cross-round change in this ratio to the compiler: host and C timing varied. All raw attempts, CPU ticks, original result/fuel/all17 state, declared exports including the tarfind warm thunk, C source/binary custody, and upstream driver/formula were checked. There is no subset geometric mean or reuse of old elapsed times. These translated-port measurements are not certified official Kotoba or per-MHz scores.

Round114 handles 45186 (native), 82637 (C), 5874 (sequential collection and offline audit) are CLOSED 0.

## Qualified next candidate — not adopted

PR #1313: https://github.com/kotoba-lang/amu/pull/1313

- Branch/worktree: `codex/seed-copy-chain48-20261014`, `/Users/junkawasaki/github/wt/codex/seed-copy-chain48-20261014`.
- Current fixed PR head: `cdcca3523f1208abfb3bdfef0236e157f323e1b7`, base main.
- Source revision: `ffa4cfc1923b50b545c782c5b8545ba290c1c8b2`.
- Unity: `233cafbff4e01c23c3a3dab38c256483c08a3477df7f9c15cbf3f5f333d211a6`.
- Native: `87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345`.
- Container: `82f4f853191b93c540bdf51757570050cc1e48699345a86d3eb4c9916727d501`.
- Trusted loader unchanged: `f44b50995a0e45db4be35244da34dd61538a484c7d5ea2f15f7f5a73d9daa8c3`.

This extends a certified copy/write **prefix** from 16 to 48 stages. Longer chains retain their original tail; they are not refused in their entirety. The initial unreachable `>48` metadata claim is corrected by the committed review clarification. A new actual-source helper selects the original 16-stage limit below 512 remaining code words. The extended hot prefix needs at most 307 words. This is a local emission reserve, not a guarantee that every whole program fits a fixed code capacity.

The original measured source was `878ebaef1af4130ec3b27a02217a3bff50ebe58d`, compiler `facaa71e...`. Round116 observed statemate ON/OFF 0.9653516728234509, 3.4648327176549087% shorter; pairs 0.9769918606651077 / 0.9533423206591826, all four first attempts qualified. Only two statemate images change relative to the 16-stage parent (+4728 bytes each, 34 extended intervals); other37 identities.

The headroom revision emits **identical complete sources/native/container/exports for all39 and the generic54 fixture**. Original483 and prior7344 generic guests are retained by exact guest identity, with no retiming. Actual-IR physical proofs check all old/new words, stores, guards, aggregate fuel/range, relocation mapping, tails and cold code. G1=G2=G3=G4, actual-source 12 headroom boundaries, generic3672 pairs including3024 independent all8-output oracles, immutable-writer refusal, all10 standard controls, policy34 refusals, smoke42, archived19, and three standard self-build generations pass.

Portable replay derives its checkout, disables Python bytecode writes, and validates both historical and revised archives. A separate fresh checkout replay verified that every checkout file hash remained unchanged and no cache was created. Both affected replay scripts have the bytecode guard. All three existing PR review threads were resolved after the fixes were pushed. The parent raw archive and measured artifacts remain unchanged.

Local handles 35906/17464/90188/50233/93626/67774 are CLOSED 0. PR update handle88336 and final metadata handle4693 are CLOSED 0. The old CI watcher23466 is CLOSED; do not use its results for the new head.

**Local CI watcher17139 is CLOSED, exit143 (intentional SIGTERM at the user pause).** Its exact process was identified as `gh pr checks 1313 --repo kotoba-lang/amu --watch --interval 30`; only that owned process was stopped. Its log remains `pr1313-ci-watch-fixed-head.log`. GitHub-side CI was not cancelled or restarted. At 2026-10-14 03:04:07 UTC: PR1313 OPEN, head unchanged, 16/20 checks successful, 4 in progress, no failures, all3 review threads resolved, and auto-merge disabled. This is a snapshot, not a final CI result. See `pause-pr1313-snapshot.json`, `pause-pr1313-review-threads.json` and `pause-receipt.json`. Do not poll or merge during the pause, even if CI later succeeds.

## After the user resumes

1. Require a new explicit user request to resume. Confirm the goal is active and ordinary allowance remains available, without additional paid spending. The earlier resume question has no effect after this pause.
2. Read PR1313 CI afresh at exact head `cdcca352...`; watcher17139 is closed. Inspect fresh review threads. Require all20 successful checks, fresh base-main state, no unresolved review and normal merge eligibility. No admin bypass, force-push or discarded WIP. Inspect existing results before considering any rerun.
3. Save `pr1313-final-checks.json`, merge normally with `--match-head-commit`, save `pr1313-merged.json`, explicitly fetch main, then run this directory's `readback-main.py`. It is already pinned to the final head, source, unity and compiler.
4. Only after actual main readback, prepare a fresh full19 native + freshC comparison for the new adopted compiler. Round114 measures the previous adopted compiler and cannot be relabelled as a full score for the 48-stage compiler. Preserve the original source/observations and explicitly bind any reused correctness results by complete guest identity.
5. Continue reducing the largest measured gaps. Current round114 ratios: picojpeg4.51135, statemate4.34593, slre4.11484, sglib-combined3.73196, wikisort3.43879. Never use an identical retiming, fourth CPU attempt, subset mean or minimum5% rejection.

## Saved candidates and diagnostic findings

The 32-stage candidate is saved locally and on its branch at source `e2796262...`, compiler `efcf2a65...`. Its round115 failed the raw-post CPU70 rule in all three OFF attempts (69.266%,65.799%,69.852%); no ON slot or performance ratio exists. Do not adopt or identically retime it.

The bounded DAG candidate's two Pico pairs were slower (round112 median1.0049825); it remains saved and unadopted.

`../slre-pc-profile-20261014` contains whole-native/container-matched maps and diagnostic original-body profiles. The host-attributed profile has3769 samples,3155 (83.7092%) in `checked_pair_new`, with exact result/fuel/all17 state. A two-volatile-store runtime candidate did not establish a gain and is preserved unadopted; no repository runtime change was made. The C micro-experiments and their raw outputs are in `../loader-pair-store-20261014`; they are diagnostics, not Embench scores.

Joseph's diagnostic snapshot showed16GB RAM and17484.12MB swap in use. This suggests a memory-pressure investigation but does not prove the cause of the measured gap. The local Mac's CPU read was51.1976% idle, so no local performance campaign was started. Do not kill unrelated processes or weaken CPU70 admission.

Joseph transfer authorization covers C/Python measurement sources and benchmark guest binaries under `/Users/joseph/github/workspaces/codex/embench-picojpeg-edn-20261009`. Compiler binaries and Kotoba compiler/benchmark sources were not transferred. Use native Amu compilers only; no JVM/Node/Graal/compiler fallback.

All unrelated worktrees, stashes, branches and untracked files are preserved. The PR worktree is clean except existing untracked `scripts/seed/__pycache__/`. Do not repair/delete the broken compatibility checkout or revive/spawn agents. Master state: `../embench-total-C-round52-20261011/continuation-checkpoint.json`.
