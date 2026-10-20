# Gate evidence: deferred full-suite re-run at PR #1385 head — COMPLETED (JUN-59/60)

Tick 2026-10-20 04:22–04:55 JST. Evidence-only diff (this README). No src/test
namespace touched.

## Finding (one tick, one verification)

The full-suite re-run PR #1386 recorded as "started, not finished" (started
03:49:36 JST in `gate-1385-20261020-0347`) **completed at 04:08:08 JST, before this tick began** (this tick
04:22-04:55 observed the already-completed run's log), exit 1:

```
=== gate start 2026-10-20 03:49:36 JST ===   (HEAD ebc57f45 = PR #1385 head)
Testing kotoba.compiler.accelerator-subgroup-reduce-test   (line 11 of the log)
Testing kotoba.compiler.test-runner-completeness-test      (line 207)
...
Ran 318 tests containing 5039 assertions.
16 failures, 15 errors.
nbb: 318 tests, 5008 passed, 16 failed, 15 errors
=== gate exit 1 2026-10-20 04:08:08 JST ===
```

Verified properties of this run (tool output, committed alongside this
README as `gate-1385-full.log`, sha256
`0dd6fa0b640543aa3a8e507faef76b71872103fadba9f6d3dae00e06509047ca`,
365 lines, with its runner `gate-1385-full.sh.txt`):

- Correct worktree: every FAIL/ERROR path points at
  `.../wt/amu-gpu/gate-1385-20261020-0347/run-tests.cljk`; **0** occurrences of
  `wt/codex` — the cross-worktree script resolution that invalidated the 01:00
  run (PR #1385 comment 2026-10-19T16:12Z) is absent here.
- The new namespace `kotoba.compiler.accelerator-subgroup-reduce-test` **ran**
  and contributed **0** failures/errors.
- The 31 failures/errors are 12 distinct tests, a multiset **identical** to
  earlier runs of this suite (`row-tuple-element-argument-test` x9,
  `numbered-grants-at-any-count` x9, `malformed-policy-still-refused-by-name` x3,
  `same-policy-read-twice-is-equal` x2, and 1 each of
  `text-edit-rebound-state-is-a-row-test`,
  `refuses-macos-static-host-typed-list-operations`,
  `refuses-macos-static-host-capability-calls-without-providers`,
  `packages-macos-with-a-macos-profile-and-platform-load-command`,
  `native-constructors-charge-fuel-test`, `named-grants-at-any-count`,
  `min-max-qualified-on-typed-wasm-test`,
  `every-source-namespace-is-reachable-from-the-tests`) — all outside this PR's
  diff (`run-tests.cljk` +2 lines, one new src, one new test).

## Started, not finished (carries to the next tick)

The **exact-base** comparison run at `cc2b2362` (the direct base of `ebc57f45`,
clean worktree `gate-base-20261020-0207`) was started this tick at ~04:23 JST
and was still running when the tick budget ended (69/97 namespaces observed).
Until it completes, "red at base for this exact base" rests on the earlier base
runs (bea7b9b2, PRs #1333/#1335) and the multiset identity above — the
exact-base number is **UNMEASURED as of this tick**. No green-suite claim;
nothing flips `:measured?`.

## States

- **implemented + verified:** PR #1385 emission + its registration
  (PR #1386's targeted run). The deferred full-suite re-run is now a completed
  measurement: 318/5039, 16F/15E, exit 1, red set outside the diff.
- **accepted design only:** ADR-0356/0357 rows.
- **proposed:** nothing new this tick.
