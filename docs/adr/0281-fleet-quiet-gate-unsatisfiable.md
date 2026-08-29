# ADR 0281: The quiet-host gate is unsatisfiable on this fleet, and the six domains are not separated from Rust or Clang

## Decision

Record two measurements and change nothing in the gate.

1. The bounded-fastest claim's quiet-host requirement — `load1 <= min(1.0,
   logical-cpus * 0.10)` for three consecutive samples, introduced in
   `cadfefb5` — **is not satisfiable on any host in the murakumo fleet**. This
   is a property of the hosts, not of Amu.
2. On every domain whose host load did qualify, `perfgate.core/qualify`
   **refuses to separate Amu native from rustc or Apple Clang C11** in either
   direction. Amu neither wins nor loses those domains; the experiment does
   not resolve them.

Neither the threshold nor the policy is weakened here. A gate that cannot
go green is a defect, but manufacturing a claim by loosening the quantity it
reads would be the larger one.

## The quiet gate, measured with its own criterion

Every reachable Darwin arm64 host in the fleet, sampled at the gate's own
1 Hz cadence for 120 consecutive samples on 2026-08-29:

| host | cores | minimum load1 | longest run of samples at or below 1.0 |
|---|---:|---:|---:|
| benjamin | 10 | 1.09 | 0 |
| dan | 10 | 1.30 | 0 |
| asher | 10 | 1.35 | 0 |
| levi | 10 | 1.41 | 0 |
| judah | 10 | 1.63 | 0 |
| joseph | 10 | 1.66 | 0 |
| simeon | 10 | 1.66 | 0 |

The limit on a ten-core host is 1.0. No host produced a single qualifying
sample, let alone three consecutive ones.

**This is not contention.** On levi, `top -l 1` reports every process at
0.0% CPU while `vm.loadavg` reads 1.35–1.80, and `ps -Ao state` finds no
uninterruptible threads and three to six runnable ones, most of them the
sampling commands themselves. Disabling Spotlight indexing (`mdutil -i off
-a`) on benjamin, asher and dan moved nothing; the setting was restored.
macOS `loadavg` on these machines has a floor above the limit that does not
correspond to a busy scheduler.

The consequence is structural: **no evidence gathered on this fleet can emit
a bounded-fastest claim artifact**, whatever the compiler does. That is
independent of, and prior to, any question about Amu's speed.

### The drift check inverts on a quiet host

`runtime-comparison.mjs` requires `|load1_after - load1_before| <=
logical-cpus * 0.10`, sampled around the whole run, comparator builds
included. On a host already at load 6.2–6.8 the build is invisible in the
one-minute average and the check passes — which is how ADR 0277 and ADR 0279
passed it. On levi at load 2.4 the same build moved load1 from 2.36 to 6.38
and the check failed. **The busier host passes more easily.** The two-phase
prepare/measure split already solves this where it is used; the single-fixture
path does not use it.

## The six domains, adjudicated

Compiler commit `d63740ac`, clean worktree, on levi (Apple M4, Mac16,10, four
performance and six efficiency cores, 128-byte lines, 16 KiB pages, macOS
26.2), rustc 1.98.0, Apple clang 1700.6.4.2, Zig 0.16.0, Go 1.27.0, Swift
6.2.4. Seven samples per engine, 100,000 calls after 10,000 warmup, `n=200`,
every engine returning the manifest's known answer. Samples were passed to
`perfgate.core/qualify` in both directions under
`kotoba.perfgate.policy/default-v1` against a `:measured` machine descriptor
probed from levi's own `sysctl`.

| domain | host load qualified | Amu | rustc | clang | Amu vs rustc | Amu vs clang |
|---|---|---:|---:|---:|---|---|
| kernel | **no** (drift) | 6.93 ns | 6.47 | 6.42 | rustc qualified | clang qualified |
| kernel_wide | **no** (drift) | 5.52 ns | 5.90 | 6.16 | Amu qualified | Amu qualified |
| kernel_deep | yes | 9.38 ns | 9.11 | 9.67 | not separated | not separated |
| kernel_call | yes | 5.43 ns | 5.06 | 5.04 | not separated | not separated |
| kernel_call_branch | yes | 4.97 ns | 4.95 | 4.76 | not separated | not separated |
| kernel_loop_call | yes | 140.77 ns | 140.40 | 139.91 | not separated | not separated |
| kernel_batch | yes | 4.58 ns/iter | 4.24 | — | **refused: too noisy** | — |

Read the two rows that produced a winner together with their host-load
column. **Both of them failed it, and they point in opposite directions** —
rustc, clang and Swift each qualified against Amu on `kernel`, and Amu
qualified against all five comparators on `kernel_wide`. Every domain that
did qualify its host is a refusal: `:improvement-below-threshold` and
`:not-separated-from-noise` in both directions. No arm was rejected as noisy
in the per-call suite; relative standard deviations ran 0.4% to 6%, well
inside the 10% tolerance.

Against the other three comparators, on host-load-qualified domains only, Amu
qualified over Zig on `kernel_call`, `kernel_call_branch` and
`kernel_loop_call`, and over Go and Swift on all four. Go crosses a cgo export
boundary and Swift a dylib call boundary by construction, so those margins are
not code-generation margins.

## `kernel_batch` is too noisy to carry a ratio

The `artifact-batch` fixture measured relative standard deviations of 0.471
for Amu and 0.481 for rustc — nearly five times the policy's tolerance.
`perfgate` refuses it as `:too-noisy` and reports no verdict. Both arms
returned the same checksum, so the fixture measures the right function; the
timing is the problem, most plausibly the scheduler moving a long single-call
timed region between performance and efficiency cores.

This applies backwards. ADR 0279 recorded `5.24` against `3.88416`
ns/iteration on the same fixture and derived `1.349069039380458`, stating in
the same paragraph that perfgate was not run. **That ratio should not be
quoted.** It is a median of a sample set that this policy rejects. ADR 0279's
fuel-equivalence and fail-closed claims are untouched; only its performance
number is withdrawn as unusable.

## What is still open

The gate wants "an actually idle host" and reads a quantity that, on Darwin
arm64, does not reach the value it demands. Three responses are available and
none is taken here:

- measure the intended quantity directly — idle CPU fraction, or runnable
  threads excluding the sampler — at a strictness no lower than today's;
- qualify a host class that can reach the current threshold, and record which
  hardware that is;
- leave the gate as it stands and accept that no bounded-fastest claim will
  ever be emitted from this fleet.

Choosing among these is a contract decision and belongs in its own ADR.

## Claim boundary

This establishes that the quiet-host gate is unsatisfiable on the measured
fleet, and that four per-call domains plus one batch domain do not separate
Amu from rustc or Apple Clang under the named policy. It establishes no
speedup, no parity — "not separated" is the absence of a result, not a
finding of equality — and no fastest claim. `broadFastestClaimQualified`
remains false, and no claim artifact was emitted. Rust, Clang, Zig, Go and
Swift remain optional benchmark adapters, never compiler or runtime
dependencies. Raw reports are host-specific and were not committed, per the
existing convention in `docs/performance.md`.
