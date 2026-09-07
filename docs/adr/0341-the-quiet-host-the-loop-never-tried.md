# ADR 0341 — The quiet host the loop never tried: J-B's control effect doubles at idle 9.5/10, and 174 rank ticks refused on the wrong machine

- Date: 2026-09-07 (session handoff)
- Status: Accepted (evidence record; no compiler change, no policy change)
- Supersedes nothing. Extends ADR 0335 / 0338 / 0339 with a quieter window,
  and adds a measurement-placement finding that is upstream of all of them.

## Two findings, and the second one is the bigger one

### 1. The J-B control effect is ~13% on a genuinely idle host, not 5.4-7.8%

ADR 0339 recorded 17 consecutive positive runs across six windows at
**5.4-7.8%**, with its widest window gated on `load1 4.1-5.3 (9/9 < 7.5)` and
absolutes of `5.085 / 4.714 ns/elem`.

Re-run on fleet host `benjamin`, gated on **busy-CPU fraction** rather than
load1 — idle **9.47 of 10 CPUs before** the runs and **9.58 after**, measured
by `1 - dIdle/dTotal` from `os.cpus()` over 1s windows:

| | opaque (sdiv) | const (mulh) | ratio |
|---|---|---|---|
| ADR 0339 best window | 5.085 ns/elem | 4.714 ns/elem | 1.079 |
| this window (benjamin) | **3.567 ns/elem** | **3.099 ns/elem** | **1.151** |

Both arms are ~30% faster here, which is what "less contended" looks like;
and the **saving nearly doubles, 6-7% -> 13.1%**. This is the compression
property this repo already documents (`docs/performance.md`: contention pulls
ratios toward 1.000, so read a favourable ratio with more suspicion than an
unfavourable one) — measured in the direction that had not been sampled:
**every prior J-B window was understating the effect.**

12 process-cold runs at identical parameters (`./jb 4000000 24`), checksum
764266 agreeing on every run, passed to `perfgate.core/qualify`:

```
:qualified? true   :improvement 0.1307
:separation {:gap 0.479 :summed-stdev 0.232 :separated? true}
relative-stdev 0.034 / 0.034    n 12 / 12    provenance :measured
```

Sealed claim: `bench/runtime-comparison/jb-imod-control-claim-20260906.edn`,
fingerprint 1973540873, machine fingerprint 2058578290.

**What this verdict is NOT.** It qualifies the **control's two arms** — a
hand-written C upper bound on constant-divisor strength reduction. ADR 0339 is
right that this cannot qualify J-B itself: that still requires real
specialization in kotoba-native measured through perfgate. What is qualified
here is the **size of the prize**, and it is roughly twice what the ladder
believed. The compiler change remains unimplemented and unqualified.

### 2. The loop was refusing on the workstation while 8 of 10 fleet nodes were idle

`docs/codegen-coscientist.md` entries 85-90 and the `amu-rank` tick series each
record a refusal of the form `load1 32.89 / 5min 28.79 ... far above the 7.5
quiet limit`, with `up 11 days, 8 users, 10 CPUs`. That host descriptor is
**this workstation**, not a fleet node — fleet nodes report 0 users. 174 rank
ticks and ~50 consecutive falsify ticks are recorded as "no measured verdicts"
for want of a quiet host.

Measured 2026-09-06 with the gate's own quantity across the fleet roster:
**8 of 10 nodes passed the busy-fraction criterion on the first probe**
(busy 0.033-0.084 against a 0.10 limit), while every one of them simultaneously
reported `load1 1.5-2.9` — i.e. the nodes were idle and had been all along.

**The blocker was never scarcity of quiet machines. It was measuring on the
machine that runs the agents.** ADR 0281 established that load1 has a floor on
these hosts; this entry adds that the refusals were also pointed at the wrong
host in the first place.

## A third thing, smaller but systematic

Three separate `runtime-multidomain-suite.mjs --suite competitive` runs on
`judah` at current main: `quietGate.qualified: true` twice, and in **every**
run exactly one domain failed its per-domain load1 check — always the same one,
**`narrow-arithmetic`, which is measured first**. Its `hostLoad` was false 3/3
while the other five passed 3/3.

The per-domain check lives in `runtime-comparison.mjs` and compares load1
before and after. Because load1 is a one-minute exponential average, the first
domain measured always eats the decay of whatever ran before it — including the
suite's own prepare phase. This is not host noise; it is the proxy's memory,
and it means `hostLoadQualified` (which ANDs the quiet gate with all six
domains) has never been true. **19 of 30 comparator pairs in those runs are
blocked by nothing else** — they fail only with `multidomain host-load gate
failed` and would qualify the moment it passes.

## Decision

- No compiler change, no policy change, no claim about amu's emission.
- The J-B prize is recorded as ~13% at the control level, not 6-7%.
- Measurement placement is named as a first-class defect: a tick that refuses
  for host load has not established that no quiet host exists.

## Consequences / next

1. Port the busy-fraction criterion into `runtime-comparison.mjs`'s
   per-domain check, and stop the first-measured domain from inheriting the
   previous phase's load1 decay. Until then `hostLoadQualified` cannot become
   true and those 19 pairs stay unqualifiable.
2. Run the loop's ticks on fleet nodes, not on the workstation. The gate is
   already correct in `runtime-multidomain-suite.mjs`; nothing needs inventing.
3. J-C (constant-divisor specialization in kotoba-mir/kotoba-native) is now
   worth roughly double its previous estimate. Correctness first: divisor
   1 / -1 / powers of two / INT64_MIN over -1 / negative dividends, fail-closed
   to `sdiv` outside the proven window.
