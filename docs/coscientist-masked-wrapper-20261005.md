# Masked checked-store wrapper experiment

Diagnostic source instrumentation counts 30,246 masked-byte stores and 2,978
masked-16-bit stores per complete Picojpeg body. Counters occupy workspace cells
4094/4095; they are absent from timed sources. This is a call-count observation,
not a timing comparison. The native lowerer's real SIR shows natural-order
parameter loads, a constant low-bit mask, AND, a call to a checked-store wrapper,
and scalar RET. The original simple wrapper is already inlined inside this
helper, but the outer masked helper remains a guest call.

Hypothesis: inline this exact two-helper shape, retaining the mask, original
outer/inner entry fuel and the existing handle/index checks. The experimental
matcher uses SIR, never source/benchmark names; only three-argument checked
in-place stores, masks 2^k-1 up to 65535, temporary base <= 3, one helper level,
and scalar results qualify. RES2, unsupported masks/temporaries and absent
callee SIR retain existing calls. Fuel flags are encoded separately so the AND
stays between the outer and inner entry charges. No production code is changed.
This is one-off new compiler algorithm authoring; no mechanical refactor rule
covers it.

The prototype compiler is a native three-generation fixed point. All 19 canonical
workloads preserve representative results, exact fuel consumption and fuel
exhaustion traps. Picojpeg's whole 4096-cell workspace after one and two bodies
is identical. Targeted probes additionally exercise 3/8/16-bit masks, a rejected
noncontiguous mask, high temporaries, signed extremes, bounds and low-fuel traps.

Zebulun's rotating baseline/prototype/C experiment retains the existing pinned
C binary, runner and quiet-host policy: 30 accepted triples, 300 ms target,
50 ms minimum, load <=4, estimated background idle >=90%, RSD <=10%, maximum
90 attempts. The canonical benchmark source is unchanged and every arm is
measured afresh.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Previous integrated wrapper code | 314.200 | 2.39% |
| Masked-wrapper prototype | 309.174 | 1.59% |
| C | 10.886 | 0.99% |

The 1.0163x speedup fails the predeclared 1.05x threshold and the mean difference
is below summed standard deviations. Code grows to 51,692 bytes from 45,652.
The candidate remains 28.4005x C time. Reject performance promotion, retain the
previous production compiler, and investigate other helper/representation costs.
These are custom whole-body comparisons, not official Embench scores or formal
perfgate qualification. This single workload does not establish suite speedup.

Picojpeg consumes 222,003 fuel units at n=1 (n=0 consumes 1). This total is an
execution-contract observation, not evidence that every scalar helper is charged:
the isolated real SIR of the sign-extension helper has no entry FUEL. Its calls
and branches provide a separate next hypothesis.

Evidence: [summary](evidence/coscientist-masked-wrapper-20261005/summary.json),
[native proof and diagnostic inputs](evidence/coscientist-masked-wrapper-20261005/native-proof.tgz),
[timing rows](evidence/coscientist-masked-wrapper-20261005/timing.tgz).
The diagnostic compiler initially exhausted the default pairs arena; the failure
is retained and the repeat uses the existing explicit 16M-pair compilation budget.
