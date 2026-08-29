# ADR 0282: The quiet gate reads busy-CPU fraction, not load1

## Decision

Take option one of ADR 0281's open question. The multidomain suite's
`waitForQuiet` now measures the intended quantity directly: the busy fraction
of aggregate CPU ticks (`1 − Δidle/Δtotal` from `os.cpus()`) over each
one-second window, and requires it at or below **0.10** for three consecutive
samples. That is the same ten-percent-of-logical-CPUs strictness the load1
limit was a proxy for; nothing is loosened. `load1` stays in every recorded
sample as a diagnostic. The injection variable
`AMU_BENCH_TEST_LOAD_SAMPLES` keeps its shape and now injects busy
fractions; an over-limit injection still fails the gate.

## Why

ADR 0281 measured, with the gate's own criterion, that macOS `load1` on
every reachable build-fleet host has a floor between 1.09 and 1.66 while
`top` shows every process at 0.0% CPU and `ps` finds no uninterruptible
threads. The proxy was unsatisfiable where the intended quantity is not: the
gate could never emit a claim artifact from this fleet, whatever the
compiler did.

The replacement quantity was measured on the same day, on the same seven
hosts, with the same three-consecutive-samples criterion at a 90% idle
threshold: two hosts qualified outright (six consecutive qualifying samples),
three reached five of six, and the criterion rejected exactly the one host
running a persistent pinned workload (its idle read 68–83%). The direct
measurement discriminates precisely where the proxy could not: it passes
genuinely idle hosts and fails genuinely busy ones.

## Scope

Only the multidomain suite's quiet gate changes. The single-fixture
`runtime-comparison.mjs` 75% sanity check and its pre/post drift check are
untouched — including the drift inversion ADR 0281 documented (a busier host
passes the drift check more easily); the claim path avoids that by the
two-phase prepare/measure split, which is unchanged. `perfgate` policy,
thresholds, ABBA rotation, sealing, and every refusal are unchanged. A
qualified quiet gate still only makes evidence *eligible* — perfgate still
decides, and as of ADR 0281 it refuses every amu/rustc and amu/clang pair as
not separated.

## Claim boundary

This ADR makes a claim artifact emittable; it does not bring one closer on
the merits. `broadFastestClaimQualified` remains false.
