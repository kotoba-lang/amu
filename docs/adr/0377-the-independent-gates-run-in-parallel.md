# 0377 — the independent gates run in parallel (measured; wall clock)

Date: 2026-10-25

## Status

Candidate for the selfhost-native workflow and the CDCI refusal probes. The
JUN-93 integration retains nested-shell pipefail and serializes receipt
writes, addressing the review of PR #1566. Its final exact-head native CI
is still required. The measurements below describe the original historical
candidate, not this repaired integration. It changes no gate: every check script keeps its own output directory, its own
verdict and its own negative asserts. Only the execution order changes.
Original implementation is on `claude/ci-parallel-independent-gates` (PR #1566);
that does not assert a merge into main.

## The measurement

Baseline run 40144527108 (step timings) against candidate run 40152181593,
same workflow content otherwise, both arms green:

| job | baseline | candidate |
|---|---|---|
| bootstrap-arm64 | 631s bootstrap + 977s one-compiler + 425s gates = 33.9 min | 629s bootstrap + 966s parallel gates + 76s = 28.4 min |
| qualify-x86_64 | 239s x86 + 227s complete-x86 + ~700s gates + 1735s controller = 46.4 min | 156s x86 + 154s complete-x86 + 1136s parallel gates+controller = 24.7 min |
| wall clock | 84.2 min | **53.1 min** |

Deterministic counts (the judge; wall clock is the observation):
serial gate invocations on the critical path 13 -> 6; the CDCI refusal probes
run in one serial loop of 18 -> three waves of 8; the controller step's wall
1735s -> 1136s (the probes hid inside it).

## The break test

The parallel harness was broken on purpose (one gate `exit 3` between two
passing gates): the wrapper printed the gate's own rc, collected it and
exited 1 (measured in a container run, 2026-10-25). A failing gate fails the
step.

## What was not measured (the next hypothesis's input)

The remaining serial depth is `bootstrap rebuild (629s) -> one-compiler
(966s) -> complete-x86 (154s) -> the controller group (1136s)`. Inside those:

1. the one-compiler interior (F1=F2=F3 is three serial full compiles; the
   24 static cases' 48 compiles may be concurrent),
2. the controller group interior (gate-positive's 24 case executions and the
   controller's container rebuild are serial),
3. whether a content-addressed derivation cache keyed on (compiler image,
   source unity) is acceptable gate semantics (the builds are already
   asserted byte-identical) — an owner decision,
4. what larger runners do to the four serial steps — a cost decision.

None of 1-4 was measured in this iteration.
