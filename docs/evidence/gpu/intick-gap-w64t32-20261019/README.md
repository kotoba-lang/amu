# intick-gap-w64t32-20261019 — STARTED, NOT FINISHED (tick 20261019-2221)

Question (JUN-58, the open item of PR #1380): can the w64t32 sign flip
between two batches inside a SINGLE cron session with a >=30 min
probe-idle gap? PR #1380's batch B fell into the following cron session
(37m28s gap), so the strict "inside one tick" question stayed open.

State at budget end:

- probe + 4 sha-pinned fixtures carried byte-identical to the PR chain
  (probe sha256 3696ca0d..., w32 0cf6c406..., w64 a25a6931..., w128
  c7931718..., w256 087107f9...).
- Fresh worktree environment finding (verified): the wire-42 probe CANNOT
  run in a fresh worktree before `npm ci` -- the first batch-A attempt
  logged `COULD-NOT-RUN ... nbb engine must name an existing cli.js
  file, not a directory: .../node_modules/nbb/cli.js`; after `npm ci`
  (8 packages, 3s) all 6 batch-A runs ran and verified.
- batch A COMPLETE 22:24:05--22:25:29 JST (per run-log date lines), 6/6
  runs `RESULT verified=true`
  (run-A-{1,2,3}-{w64t31,w64t32}.log), runner exit 0.
- The >=30 min gap hold hit the tick's run-time budget at ~22:39 JST
  (~13 min into the gap). batch B NOT RUN. The in-tick question is
  UNANSWERED; do not read batch A alone as any sign result.

Next tick: to keep the strict in-tick containment, RE-RUN the whole probe
in one tick (the idempotent runner skips existing logs -- delete
run-*.log or use a fresh evidence dir for batch A/B pairs). Budget plan
for a ~30 min tick: worktree+`npm ci` ~3 min, batch A ~2 min, gap 31 min
with 390 s foreground sleeps, batch B ~2 min, analyze ~1 min; the gate
and PR must be budgeted separately or honestly labeled "started, not
completed" as in PRs #1371/#1375/#1376. Note: terminal foreground calls
cap at ~420 s in this environment (a 520 s sleep timed out at 420 s) --
use sleep chunks <= 390 s.
