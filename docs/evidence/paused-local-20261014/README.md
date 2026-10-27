# Paused Amu local adoption and restart snapshot

The performance goal remains **paused**. This branch preserves source, native artifacts, verification evidence, and handoff documents. Resume optimization, validation, measurement, merging, or publication only after a new explicit user request.

- Branch: `codex/amu-local-paused-save-20261014`
- Base main: `cc3848aab48362136338f24690e3c727652301c0`, which includes PR #1313.
- [Start here](START-HERE.md), [local parallel handoff](LOCAL-PARALLEL-HANDOFF-20261014.md), [primary goal handoff](GOAL-HANDOFF.md), [adopted history](ADOPTED-HISTORY.md).
- [Snapshot inventory](snapshot-manifest.json), [save summary](SAVE-SUMMARY.json).

## State preserved

| State | Identity | Evidence / remaining work |
| --- | --- | --- |
| Provisionally selected locally | selection `f5a52c9d`, source `a3ee2231`, native `19944dff` | SLRE context-return plus private-writer fuel folding, with prior NEON/MADD. Fixed point, 39 images / 483 observations, policy refusals, complete and partial payload tests passed. Nominal SLRE 7.81% and private Pico 0.49% reductions are separate experiments; causal speed gain is unestablished. Main/product integration is pending. |
| Unselected combined candidate | source `7d69ac71`, native `4b2c4f68` | Adds NSICH closed-callgraph context proof and Wiki copy-counter fold. Fixed point, 39 / 483 and policy passed. Remaining code/pool custody, fresh private incoming proof and payload reuse/validation are listed in the handoff. No timing performed. |
| Primary main history | base main above; round114 uses earlier main `43524a1c` | Existing main safety and copy-chain changes remain in the branch ancestry. Round114 time/C GM `2.688197080154679` applies to its recorded compiler. Current local-selected and combined full19 C scores are unknown. |

The branch adds only this evidence directory. Integrate local source changes with current main after resumption; preserve its newer copy-chain and safety changes. Exact archived snapshots remain separate from the product `seed/` tree.

## Verify or restore without restarting the goal

Requires Python 3 and Git. Verification and restoration only read/write files; they never invoke the compiler, a benchmark, a merge, or another agent.

```sh
python3 docs/evidence/paused-local-20261014/restore_snapshot.py --verify-only
```

Restore the workspace structure into a **new, empty destination** under your GitHub workspace. Existing files are never overwritten:

```sh
python3 docs/evidence/paused-local-20261014/restore_snapshot.py   --destination /Users/YOUR_USER/github/workspaces/codex/amu-paused-restored-20261014
```

To materialize only the local selected bundle while still verifying all saved evidence, add:

```sh
--prefix workspaces/codex/seed-local-selected-private-twocharge-slre-neon-20261014-v3
```

The restored `workspaces/codex/seed-copy-chain48-review-20261014/START-HERE.md` retains its original paused text. This repository's Start Here adds the save-time main/branch information. `path-map.json` maps original absolute paths to restored files. Original JSON, logs, and scripts retain their original path strings and hashes. On another host, bind their inputs and outputs to the new paths in a fresh phase before execution; keep the archived receipts unchanged.

The native bundle is the recorded Apple Silicon/macOS snapshot. [selected/](selected/) exposes the source, loader, compiler, container, wrapper, selection record, and smoke receipt directly. The archive deduplicates supporting files by SHA-256. Existing PR1313 evidence already present in the base Git commit is referenced by commit/path and verified during restoration.

The manifest records six old references to paths later updated (mutable Start Here, pointers/index and a historical working source). Their historical expectations remain in the original receipts; explicitly selected current files are saved with their current hashes. Scope is the specified paused evidence trees plus one-hop pinned dependencies. Rollback snapshots, negative results, incomplete stages and failure logs are retained.

## Resume order after explicit authorization

1. Read the Start Here and handoffs, verify the snapshot, and refresh current main.
2. Reconcile source with main's newer changes; do not overwrite main with the old unity snapshot.
3. Complete the combined code/pool, private-entry and partial-payload gates. The prepared NSICH fixed16 packet has never run.
4. End all heavy correctness jobs before a fixed measurement window; retain all raw samples.
5. Record a new selected identity and full original19/C comparison only when their own evidence exists. Push/merge/product/publication statuses are separate.

The archive verification and selected-bundle restoration receipts are [SAVE-VERIFICATION.json](SAVE-VERIFICATION.json). No performance exploration was restarted for this save.
