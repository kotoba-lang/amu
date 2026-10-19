# Gate evidence: PR #1385 registration check (20261020-0347)

Tick: amu-gpu 20261020-0347. State under test: `ebc57f45` (PR #1385 head,
`bot/amu-gpu-20261020-0028`) — executed in a **detached worktree** at that exact
commit (`wt/amu-gpu/gate-1385-20261020-0347`), nothing edited.

## Verified this tick (targeted run, exit 0)

Command (from the detached worktree root):

```
kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-ns-1385.cljk
```

`run-ns-1385.cljk` requires and runs exactly the two namespaces PR #1385 left
unverified: the new `kotoba.compiler.accelerator-subgroup-reduce-test` and
`kotoba.compiler.test-runner-completeness-test` (the registration check).
Output verbatim:

```
kbb: 2 dep(s) are not :local/root and are NOT on the classpath (kbb resolves :local/root and :git/sha coordinates, not Maven; a jar cannot load on this engine): com.google.javascript/closure-compiler-unshaded, org.clojure/tools.reader

Testing kotoba.compiler.accelerator-subgroup-reduce-test

Testing kotoba.compiler.test-runner-completeness-test
SCANNED	241
EXECUTED	97
LEDGER-ONLY	144

Ran 10 tests containing 244 assertions.
0 failures, 0 errors.
```

(CORRECTED 2026-10-20: the first revision of this line recorded 8 tests / 75
assertions (7/66 + 1/9) from a STALE selection at 53248c1. Re-run at the
current tree: `kotoba.compiler.accelerator-subgroup-reduce-test` = 9 tests /
235 assertions (its 4b7a1cc expansion), `test-runner-completeness-test` =
1 test / 9 assertions, together 10 tests / 244 assertions. Registration in both
lists of `run-tests.cljk` (require line 74, `t/run-tests` line 215 at
`ebc57f45`) is now **verified** — closed as of this tick.)

## Full suite gate: started, NOT finished

The full gate (`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)"
run-tests.cljk`) was re-started at 03:52 JST in the background and was still
running when this tick's run budget ended (~04:05 JST). **No completion claim.**
Partial observation only: 73 namespaces had begun, 19 FAIL/ERROR lines so far —
all in the namespaces prior ticks reported red at base (`policy-grant-count`,
`namespace-reachability`, macos-profile refusals; e.g. `numbered-grants-at-any-
count`, `same-policy-read-twice-is-equal`, `every-source-namespace-is-reachable-
from-the-tests`). Not re-observed to completion; not claimed unchanged. The
runner log continues at `cache/scratch/gate-1385-full.log` on this host; the
next tick picks up the completion run.

No src/test `.cljk` namespace is touched by this diff (evidence only).
