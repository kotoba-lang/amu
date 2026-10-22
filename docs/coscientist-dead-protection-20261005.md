# Correct the self-tail premise; reject dead-alias preservation removal

The previous wave proposed reusing a frame for direct self-tail-recursion. Current
source evidence falsifies its premise on the measured source route:
`lw-call` already recognizes same-function calls in tail position and sends them
to `lw-jump`, which evaluates all arguments, updates parameter locals in parallel,
charges the original recurrence fuel and branches to the existing entry label.
Those calls do not reach the A64 backend as CALL/RET. Self-tail frame reuse is
already present on this path; residual calls must not be inferred from a generic
backend tail-call implementation alone.

A backend prototype nevertheless adds a same-function CALL/RET frame loop, with
arity <=7, scalar/non-leaf guards, argument setup, rebinding and branch to the
original body fuel. Its three generations match, and all 19 canonical binaries
are byte-identical to the promoted seed. Results/exact fuel/traps and all 8,192
Picojpeg workspace cells also match. No timing is run: identical machine code
cannot establish a compiler execution-speed win. The raw SIR algorithm is not
independently qualified or promoted; no benchmark opportunity was demonstrated.
The archived attempted hypothesis and patch preserve this correction explicitly.

## Actual remaining work: unnecessary alias preservation

The existing backend preserves every temporary alias to a local before writing
that local, including aliases which will never be read. Test a bounded use of
its existing `gn-kills` proof before explicit LSET. Only a local-alias temporary
other than the update operand is admitted; when the 16-step proof shows a kill
before read, retire that descriptor without materializing the old value. Unknown
paths/conditional branches keep the original materialization. Coalesced writes
remain unchanged. No effect, fuel, bounds check, allocation or result expectation
is altered. This is one-off new compiler algorithm authoring, not a mechanical
source refactor, and the prototype stays outside product source.

Native generations 2/3/4 match at 820,848 bytes, SHA-256
`3f3c420f973aad82b7bd5e681c634c99aea323aea3500c90fdc559119a66ccd6`.
All 19 canonical workloads preserve representative results, exact fuel use and
exhaustion exits. All 8,192 Picojpeg workspace cells match. Only Huffbench, MD5
and Sglib binaries change; the other 16 are byte-identical, including Picojpeg.
No unchanged workload is retimed as a new improvement experiment.

Six new handwritten SIR fixtures cover dead/live aliases, high-temp homes,
conditional-branch refusal and repeated parallel argument swaps. All 935 runs
across 163 fixtures pass hand-computed values and fuel boundaries. Real/test
layouts match. An instruction audit finds zero old-local-to-temp MOV in the dead
case and exactly one in the live case. Product fixture goldens are untouched;
no semantic expected outcome is relaxed.

## Fresh measurements of every changed workload

The registered hypothesis keeps the existing prospective policy: pinned runner
on zebulun Apple M4, fresh rotating baseline/candidate/C triples, 30 accepted,
90-attempt cap, target 300 ms, minimum 50 ms, load <=4, estimated background idle
>=90%, RSD <=10%. Promotion requires >=5% speedup and a mean gap above summed SD.
All changed workloads are selected before timing; no favorable subset is chosen.
Baseline code is verified byte-identical to the current promoted sign-extension
compiler, using completed wrapper reports only for code lineage. All timing arms
are sampled anew against the unchanged pinned C binaries.

| Workload | Baseline us/body | Candidate us/body | C us/body | Speedup | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Huffbench | 53.849 | 53.682 | 7.231 | 1.00311x | Reject |
| MD5 | 14.064 | 14.107 | 2.500 | 0.99694x | Reject |
| Sglib | 41.055 | 41.123 | 5.825 | 0.99836x | Reject |

Huffbench's 0.167 us mean gap is below its 6.180 us summed SD and the 5% threshold.
The other candidates are slower at the observed means. None establishes a gain.
Candidate/C time ratios are 7.4235x, 5.6429x and 7.0597x; C-or-better remains
unachieved. Code sizes are 13,160/6,636/24,256 bytes against 13,160/6,640/24,260.
These aligned whole-body timings are not official Embench scores, do not qualify
formal perfgate, and imply no new full-suite geometric mean. Preserve the negative
results without resampling identical candidates for promotion. Production compiler
and integrated image remain at the promoted sign-extension version.

## Next hypothesis

Picojpeg's transform path calls `floor-quot` with constant divisors 128/256 through
`multiply-idct` and `descale`. That constant is unavailable inside a separately
compiled helper. Inspect its actual SIR before implementing a name-independent
specialization for exact small helper shapes and known scalar arguments. An
arithmetic right shift alone is not automatically equivalent: the source's
negative branch uses wrapped negation/addition, so MIN and near-MIN behavior must
be preserved too. Retain entry fuel, division/trap semantics and caller temporaries;
measure fresh canonical execution rather than memoized answers. This is a next
hypothesis, not an implemented optimization or native typed-CID cache bridge.

Prototype diffs use zero context to avoid trailing-whitespace warnings from
blank unified-diff context records; full experimental sources are archived.

Evidence: [summary](evidence/coscientist-dead-protection-20261005/summary.json),
[no-op proof](evidence/coscientist-dead-protection-20261005/no-op-proof.json),
[backend self-tail attempt](evidence/coscientist-dead-protection-20261005/self-tail-no-op.tgz),
[dead-alias patch](evidence/coscientist-dead-protection-20261005/dead-protection.diff),
[native proof](evidence/coscientist-dead-protection-20261005/native-proof.tgz),
[all timing and code lineage](evidence/coscientist-dead-protection-20261005/timing.tgz).
