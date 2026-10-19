# Gate evidence: exact-base full-suite run at cc2b2362 — COMPLETED (JUN-59/60)

Tick 2026-10-20 04:45–05:15 JST. Evidence-only diff (this README). No src/test
namespace touched.

## Finding (one tick, one measurement)

The exact-base comparison gate PR #1387 recorded as "started, not finished"
(died mid-run at 79/97 namespaces when its session ended) was re-run from
scratch in the clean worktree `gate-base-20261020-0207` (HEAD `cc2b2362`, the
direct base of `ebc57f45`) and **completed at 05:11:07 JST this tick**, exit 1:

```
=== gate start 2026-10-20 04:49:47 JST ===   (HEAD cc2b2362)
Ran 311 tests containing 4973 assertions.
16 failures, 17 errors.
=== gate exit 1 2026-10-20 05:11:07 JST ===
```

Full log: `cache/scratch/gate-base-cc2b2362-full.log` (this tick's session).

## Exact-base red set vs PR #1385 head (ebc57f45)

Base `cc2b2362` (33 red = 16F + 17E, 14 distinct tests):

- `numbered-grants-at-any-count` x9 FAIL
- `row-tuple-element-argument-test` x9 ERROR
- `malformed-policy-still-refused-by-name` x3 FAIL
- `options-map-destructures-as-a-row-test` x2 ERROR
- `same-policy-read-twice-is-equal` x2 (1 FAIL + 1 ERROR)
- 1 each FAIL: `packages-macos-with-a-macos-profile-and-platform-load-command`,
  `native-constructors-charge-fuel-test`,
  `every-source-namespace-is-reachable-from-the-tests`
- 1 each ERROR: `text-edit-rebound-state-is-a-row-test`,
  `refuses-macos-static-host-typed-list-operations`,
  `refuses-macos-static-host-capability-calls-without-providers`,
  `named-grants-at-any-count`, `min-max-qualified-on-typed-wasm-test`

Head `ebc57f45` (31 red = 16F + 15E): the identical multiset **minus
`options-map-destructures-as-a-row-test` x2 ERROR**.

So every red at head is also red at the exact base (now measured, not assumed
from the earlier bea7b9b2 runs). The base is strictly redder by 2 errors in
`options-map-destructures-as-a-row-test` — present at base, absent at head in
the one run each we hold; whether that is run-order/flake or a real delta is
UNMEASURED (one sample per side). The diff (`run-tests.cljk` +2, one new src,
one new test ns) adds 7 green tests (311->318 tests, 4973->5039 assertions)
and introduces zero new reds.

No green-suite claim. No hardware measurement this tick; nothing flips
:measured? in kotoba.compiler.accelerator-targets (all rows remain
:measured? false, provisional).

## State

- implemented: nothing (evidence-only).
- accepted design only: ADR-0355 / ADR-0002 unchanged.
- Linear 未記録 — Linear connector not connected in this cron session
  (CONNECTION_REQUIRED); JUN-55/JUN-59/JUN-60 rely on this PR trail.
