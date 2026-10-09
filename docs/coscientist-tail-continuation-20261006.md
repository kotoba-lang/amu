# Bounded terminal continuation: native proof, no qualified speedup

The prototype passes native correctness and produces a generation2..4 fixed
point. It replaces returning calls with the existing tail emitter when their
result passes only through a bounded owned terminal continuation. However, fresh
product/candidate/C comparisons for all13 changed original guests qualify **no
improvement**, no regression and no C-or-better workload. All13 series are stable.
The experiment is rejected for performance; product code remains unchanged.
These are aligned original-body times, not official Embench scores.

The [previous full19 refresh](coscientist-current19-refresh-20261006.md) ranked
statemate as the largest stable gap and registered this hypothesis before
implementation/timing. The qualified forward-copy product is the baseline;
source snapshot `b1c0cb68eff8a9fb36c0ee4aec1c1a41e5a970fe` is unchanged.

## Implementation and independent native evidence

The prototype follows at most16 continuation steps inside one closed typed
function. Only owned unique labels, unconditional branches, exact uncharged
one-argument identities and scalar return of the original result temp are
allowed. Ownership scans refuse duplicate labels anywhere in the module,
foreign labels and cycles. Closed caller/callee metadata and exact identity
shape/type/slot/depth are checked. Unknown operations, effects, charges,
allocations, ABI, open replacements or changed temps preserve the original call.
Original frame/register assignment, context recovery, argument transfers and
published nonleaf fuel remain unchanged. The existing immediate CALL/RET path
is preserved.

Native generations2/3/4 are864968 bytes, SHA256
`c1b058d5e89239a7a1ee7dd513b1b762f42f3e6a6b817f26854ea310579d978c`.
Generation1 is recorded separately; it is not claimed byte-identical. Proofs:

- All19 original result, exact-fuel and fuel-trap comparisons agree.13 guests
  change,6 remain byte-exact. Original sources and C inputs remain unchanged.
- 541 full supervisor comparisons:294 independent arithmetic/result/fuel
  oracles,209 original19 full/partial-fuel states and38 resource/partial states.
  New oracles include three-argument permutation, shared branches, signed
  extremes, charged/effectful/changed continuations, callee and explicit traps.
- 40 continuation/identity instruction-field mutations,11 metadata mutations,
  three open dependency refusals, and owned duplicate/foreign/cycle refusals,
  with positive native controls.
- Original494 fixtures and14019 native executions retain their expectations.
  A fresh v2 real/test-layout rebuild reproduces the exact executed fixture
  artifact. That artifact is also byte-identical to the qualified product's
  original494 fixture blob. Generated goldens are unchanged.
- All19 native SIR/frame/local/register/leaf fields are exact. A read-only
  observer records the initial prototype; final v2 emits exactly the same19
  guests/offsets/results/fuel. Actual statemate code replaces201 returning BL
  sites but grows from26379 to26665 words. Static sites are not time shares.

The predicate was reinforced to validate the real callee's FN metadata before
final v2 proof/timing. Initial tool/build authoring failures are retained:
terminated unapplied patch attempt, a report-format assertion, a diagnostic
CPU limit, a temporary unity assembly reference and a branch-table variable.
These were harness/authoring corrections, not relaxed semantic expectations.
Only the final v2 fixed point and exact validated guests are timed. Python/C
remain bootstrap proof and measurement tooling; there is no product host fallback.

## One fresh campaign for every changed guest

Authorized zebulun Apple M4, unchanged pinned original C/runner/spec, rotating
product/candidate/C order;30 accepted triples each,390 total. Native exact fuel
is checked on every sample. Raw accepted/rejected rows and all C receipts remain.
All three series must satisfy10% RSD; a qualified improvement needs at least1.05x
speedup and a mean gap exceeding summed SD, with unchanged load/idle/interval
rules. There is no identical-candidate retry to change the decision.

Values are nanoseconds per original body; positive reduction means shorter.

| Workload | Product ns | Prototype ns | C ns | Time reduction | Prototype/C |
| --- | ---: | ---: | ---: | ---: | ---: |
| edn | 11337.315 | 11342.973 | 742.328 | -0.050% | 15.280271x |
| huffbench | 53679.997 | 53610.492 | 7322.126 | 0.129% | 7.321711x |
| md5sum | 10946.941 | 11131.142 | 2502.758 | -1.683% | 4.447551x |
| nettle-aes | 25619.519 | 25036.080 | 1407.744 | 2.277% | 17.784545x |
| nettle-sha256 | 2783.262 | 2778.949 | 220.742 | 0.155% | 12.589124x |
| nsichneu | 711.529 | 711.282 | 78.955 | 0.035% | 9.008706x |
| picojpeg | 214933.745 | 217467.523 | 11206.641 | -1.179% | 19.405236x |
| qrduino | 282017.708 | 279737.946 | 22284.699 | 0.808% | 12.552915x |
| sglib-combined | 41286.757 | 40004.396 | 5809.043 | 3.106% | 6.886573x |
| slre | 7904.822 | 7756.256 | 1055.917 | 1.879% | 7.345513x |
| statemate | 764.080 | 756.400 | 31.677 | 1.005% | 23.878801x |
| tarfind | 13976.861 | 14604.581 | 1006.547 | -4.491% | 14.509580x |
| wikisort | 187067.188 | 188141.233 | 15188.546 | -0.574% | 12.387047x |

Independent raw-row/statistic/source/native/C/fuel audit finds0 improvements,
0 regressions,0 unstable entries and0 C-or-better qualifications. Statemate's
approximately1.005% reduction is below the speed threshold and its mean gap is
smaller than summed SD. The earlier original19 product/C result is not overwritten
by this rejected prototype. No full-suite aggregate or historical compounded
speedup is claimed.

Product gates and committed-source integrated adoption were not run: the
performance prerequisite failed. The831000-byte qualified product and its
existing gates/integration remain unchanged.100% selfhost and C-or-better across
all19 remain unachieved. Rung selection, bin/amu and wire20 grants are unchanged.

## Next registered experiment

The current qualified product already contains391 small framed statemate
functions with no observed returning BL/BLR. That static observation does not
prove eligibility or dynamic importance. A separate terminal-only allocation
mode could avoid frame setup/restore while retaining original published fuel.
The prospective [hypothesis](evidence/coscientist-tail-continuation-20261006/next-hypothesis.json)
requires small local/temp sets, at most one incoming/outgoing argument, no stack
spill or returning calls, closed owned control flow, no unknown runtime/context
clobbers, and a complete audit of leaf predicates/scratch/local/ABI behavior.
Unknown cases keep original frames. This experiment starts from the qualified
product, not this rejected prototype. It is unimplemented and unmeasured.

Current definition identity content addresses normalized checked typed code,
effects and dependencies. Neither experiment connects native DefCID/artifact
caching or reuses execution results. The [identity contract](coscientist-content-address-20261005.md)
requires sealing compiler/target/ABI for reusable proof/specialization artifacts
and arguments/observable state for any computation identity.

## Evidence and replay

[Summary](evidence/coscientist-tail-continuation-20261006/summary.json),
[independent timing audit](evidence/coscientist-tail-continuation-20261006/timing-audit.json),
[checksums](evidence/coscientist-tail-continuation-20261006/checksums.sha256),
[native proofs/source snapshot](evidence/coscientist-tail-continuation-20261006/native-proof.tgz),
[raw timing and receipts](evidence/coscientist-tail-continuation-20261006/timing-proof.tgz).
The native archive preserves both source revisions, all native generations,
original19 source snapshots, complete supervisors/oracles/regression observations,
actual SIR/emission census, mutation controls and initial failures. The timing
archive preserves all390 raw accepted triples/rejected attempts, product/prototype/C
bytes, manifests and receipts. Extract timing archive and run
`replay-timing-audit.py` for independent offline raw-statistic replay.

One-off algorithm/diagnostic authoring is a research exception; no mechanical
product refactor or benchmark source edit was performed. PR remains draft.
