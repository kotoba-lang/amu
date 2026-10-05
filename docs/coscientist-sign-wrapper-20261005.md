# Scalar sign-extension inlining

The content-equality and masked-store experiments did not clear the declared
execution-performance threshold. The next hypothesis removes calls/branches
from exact scalar sign-extension decision trees in the native compiler's SIR.
No benchmark source, input fixture or expected result is changed.

The matcher accepts one argument, natural parameter load, a low-bit mask
2^width-1 (width 1..32), a temporary local, signed comparison against
2^(width-1), subtraction of 2^width in the high half, two exact branch/join
labels, scalar RET and END. An optional original entry FUEL is recorded separately.
Other shapes, absent local SIR and CALL followed by RES2 retain the existing route.
The call emits SBFM (signed bitfield extraction) or folds a constant with exactly
the same signed-i64 behavior; the original entry fuel remains when present.
Prescan includes that fuel and leaf eligibility, and result emission uses the
existing temporary/local preservation rules, including high temporary homes.
Classification uses code shape, never function names. This is one-off new compiler
algorithm authoring; no mechanical refactor rule covers it.

Native compiler generations 2/3/4 are identical: 820,488 bytes,
SHA-256 `af790a71b85e853a910cd08e2be2f647099e33d5f688283800841f58bdb5b063`.
All 19 canonical workloads preserve representative results, exact fuel consumption
and exhaustion traps. All 8,192 Picojpeg workspace cells after one/two bodies
match the previous native selfhost compiler. Another 1,872 source-level probe
comparisons cover widths 1/2/8/16/24/31/32, signed extremes, constants, high
intermediate depth, aliasing, tail calls and a deliberately nonmatching subtraction.

Twelve handwritten SIR fixtures add charged/uncharged sign extension, constant
and high-temp callers. All 894 executions (157 fixtures) pass hand-computed results
and positive-fuel exhaustion expectations. Real/test layouts match exactly. Six
caller audits show one SBFM and zero direct BL. Generated fixture source/index and
the byte golden are regenerated; changed addresses/branches/literal displacements
are checked through real/test layout equality and actual execution, rather than
loosening results. PRODUCT bootstrap inventory is unchanged.

On zebulun (Apple M4), 30 rotating baseline/candidate/C triples meet the existing
quiet-host, duration, spread and attempt rules. Every arm is measured anew against
the same C binary and canonical benchmark source.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Previous integrated native wrapper compiler | 313.610 | 2.06% |
| Sign-extension candidate | 260.285 | 2.91% |
| C | 10.798 | 1.12% |

The 1.2049x speedup (17.00% less time) clears the 5% threshold and summed-SD
separation. Code is 45,092 bytes versus 45,652. The remaining C ratio is 24.1040x;
C-or-better performance is unachieved. Native code changes in Picojpeg, Statemate
and WikiSort; the other 16 canonical workload binaries are byte-identical.
This is an isolated aligned whole-body experiment, not a new suite geometric mean,
not an official Embench score and not formal perfgate qualification.

The committed source at `e0218f27a` rebuilds the unified Amu for three identical
generations, including all 162 objects, containers, native code and commands.
The 6,092,664-byte executable SHA-256 is
`3a6337a3c0101015369e24c0c28a8f7d3a5fbf0458de229620253aa7b1fd82e9`.
Copied source inputs are content-pinned and checked. All 19 canonical sources
check/compile through generation 3 and reproduce the exact measured raw code.
The 391-case integrated corpus retains every previous per-case check/compile
classification: check 358 same accepts and 33 same refusals; compile 300 behavior
matches, 27 Amu-only accepts, 12 Amu-only refusals, 3 differing accepted outputs,
49 shared refusals. Every export's classification is also unchanged (875 same,
15 existing differences, no timeout, one missing). The existing language and
own-source selfhost gaps are not claimed closed. `bin/amu` stays unchanged.

Fresh 30-triple measurements of the other two changed binaries find Statemate
1.0332x (below the 5% threshold; candidate/C 24.0466x) and WikiSort 1.1117x
(candidate/C 13.6253x). WikiSort's 23.08 us mean improvement is smaller than the
25.01 us sum of standard deviations, so it is not a confirmed improvement either.
Do not resample to turn this negative spread decision into a pass. All 16 other
canonical binaries are byte-identical; no new full-suite timing mean is claimed.
[Integrated proof](evidence/coscientist-sign-wrapper-20261005/integrated-summary.json)
and [changed-workload rows](evidence/coscientist-sign-wrapper-20261005/changed-timing.tgz)
retain the evidence.

[Evidence summary](evidence/coscientist-sign-wrapper-20261005/summary.json),
[native proof bundle](evidence/coscientist-sign-wrapper-20261005/native-proof.tgz),
[all timing rows](evidence/coscientist-sign-wrapper-20261005/timing.tgz).
Failed diagnostic harness runs are retained: a fixture emitter initially lacked
wire 38, and four exhaustion probes incorrectly requested initial fuel zero,
which the loader rejects before guest execution. Repeated probes use two caller
charges with positive budgets and preserve the expected successful values/traps.
The initial gate invocation used the r0 default and an out-of-scope default port
path; the repeat explicitly names r6m and the repository's gate ports, with the
existing rung golden unchanged.
