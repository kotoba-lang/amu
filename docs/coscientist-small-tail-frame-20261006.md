# Small terminal-only frames: qualified native statemate improvement

The candidate reduces original statemate body time by **23.509%**
in one fresh rotating product/candidate/C campaign. The gap exceeds summed SD
and the speedup exceeds1.05x. All9 changed workloads are stable; no qualified
regressions. Statemate still takes **18.471882x C**. These are
aligned original-body times, not official Embench scores. C-or-better across
all19 remains unachieved; no new all-suite aggregate is claimed.

Source commit `a0e46233008ffda03fc96b4cc1fdbbe76ba52a59` is adopted on the research branch after
native proof, durable expectations, BUILD/ERR/G1-G5 and committed-source integrated
self-rebuild/parity. The default rung, bin/amu selector and wire20 grants are
unchanged. PR remains draft; no main merge/release or100% selfhost claim.

## Registered hypothesis and implementation

The [rejected terminal-continuation experiment](coscientist-tail-continuation-20261006.md)
found391 current statemate small framed functions without observed returning
BL/BLR. That static census was neither eligibility proof nor a time share. This
new experiment starts from the qualified scalar forward-copy product and removes
only proved terminal-only frames; it does not adopt the rejected prototype.

Mode0 ordinary nonleaf and mode1 private-fuel leaf behavior remain intact.
Separate mode2 permits at most one incoming parameter, seven locals/temporaries,
no outgoing stack area/spill, closed typed single-register arguments/results,
owned unique labels and a complete bounded function scan. All actual calls must
be exact known inline wrappers or immediate scalar terminal transfers with at
most one argument. Genuine returning calls, indirect calls, capabilities,
allocation, unknown runtime operations/types, multi-result ABI, malformed/open
metadata and foreign/duplicate labels retain the original frame.

Mode2 uses low local registers and avoids saving x30/callee-saved registers;
there is no returning call to overwrite the return address. One-argument transfer
avoids an unproved multi-argument shuffle. x7 remains known even after labels;
no absent context frame slot is read. Nonleaf scratch-dependent clamp/mask/reader
specializations are disabled only in mode2. Crucially, published FUEL remains the
original five-instruction ctx transaction; it is never changed to private x8 fuel.
This removes frame cost without memoizing results or changing source workloads.

All19 read-only SIR/emission partitions are audited.391 statemate functions enter
mode2; code shrinks26379→21316 words. Other mode0/1 frame/register metadata is
exact. Ten guests, including the earlier matmult/md5 optimizations, are byte-exact.
Static frame/instruction counts are not dynamic time shares.

## Native correctness and adoption evidence

- Generation1 recorded separately; generations2/3/4 are identical834304 bytes,
  SHA256 `188c11b4bbeb6e6e16f833538cbf76145ef1f97a6be4932f941a3c04686d5bd3`. Exact MANIFEST concatenation, including its
  trailing newline, independently rebuilds the same bytes.
- 793 exact full supervisor comparisons:504 independent signed extrema,
  locals/branches/vector/context/fuel oracles,209 original19 partial/full-fuel
  states,38 resource/partial states and42 additional invalid-handle trap states.
  The first751 were sealed before timing; invalid-handle42 were added afterward
  without any source/compiler/guest change.
- 23 instruction/metadata refusal mutations,3 positive controls,2 open refusals
  and duplicate-label refusal. Expected fallback frames are inspected directly.
- Original494 fixtures/14019 expectations are exact prefixes; append14 fixtures
  and504 independent runs. All508 fixtures/14523 native executions pass using
  real and test layouts, with exact code/pool/offset equality. Normal unit exit0
  and its blob/offsets equal the independently executed artifact before updating
  the generated golden. No original expectation is weakened.
- BUILD/ERR/G1-G5 pass. G3 retains233 refused/67 accepted with exactr6m refusal
  goldens. The test compiler lineup is actual native generations2/3/4, not stage0.
- Integrated Amu3 generations have162 objects/117 frontend objects and identical
  objects/container/native/command. Command SHA256
  `050f078a2cc8457ab782e7445b36fd749ea99b90db0e3cc7a4dfdd7a58917a56`. Its own check/compile/extract route
  reproduces all19 measured native bodies/offsets exactly.
- All391 check and391 compile classifications/exit statuses,891 export rows,
 391 normalized full checker messages and1780 native output/status files agree
  with the previous qualified product. Existing300 behavior-same compile cases,
 27 Amu-only accepts,12 Amu-only refusals,3 accepted differences and49 shared
  refusals remain visible. Exports875 same,15 existing closure-handle differences,
 0 timeouts and1 missing remain visible.

Initial authoring/harness failures are retained: a final-function diagnostic
region lookup, one mutation-source parenthesis, reused temporary directory,
wire35 input scope, unit vector budget and stale copied unity metadata. Formal
unity differs from prototype assembly only by a final newline; native bytes were
independently reproduced before correcting lineage metadata. The unqualified
unit budget trap was not accepted as a pass. Python/C remain bootstrap evidence
and measurement tooling; product code remains Kotoba. PRODUCT boundary counts
are unchanged. This new algorithm/independent fixture authoring is a one-off
research exception; authoritative generator owns the test source/golden.

## One fresh all9 changed-body campaign

Authorized zebulun Apple M4; unchanged pinned C/runner/spec;30 accepted rotating
triples each,270 total. Every sample validates exact native fuel. Preserve raw
rejected rows, load/idle/minimum interval rules,10% maximum RSD,1.05x speedup and
gap greater than summed SD. No identical-candidate retry changes the decision.

Nanoseconds per original body; positive time reduction means shorter.

| Workload | Product ns | Candidate ns | C ns | Time reduction | Candidate/C | Improvement decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| crc32 | 3951.941 | 3967.394 | 1706.604 | -0.391% | 2.324731x | below threshold |
| depthconv | 122.773 | 121.194 | 34.569 | 1.286% | 3.505817x | below threshold |
| edn | 11583.980 | 11588.686 | 755.715 | -0.041% | 15.334735x | below threshold |
| huffbench | 53803.306 | 53851.112 | 7409.014 | -0.089% | 7.268324x | below threshold |
| nettle-aes | 25612.517 | 25720.125 | 1403.925 | -0.420% | 18.320151x | below threshold |
| nsichneu | 711.504 | 710.883 | 78.781 | 0.087% | 9.023559x | below threshold |
| sglib-combined | 40899.313 | 40971.404 | 5793.162 | -0.176% | 7.072374x | below threshold |
| slre | 7897.764 | 7887.699 | 1050.071 | 0.127% | 7.511584x | below threshold |
| statemate | 762.440 | 583.201 | 31.572 | 23.509% | 18.471882x | qualified |

Statemate SDs are7.262/15.011/0.203ns
(product/candidate/C), with RSDs0.952%/
2.574%/0.643%.
All other changes remain below the qualified-improvement threshold; none is a
qualified regression. Independent raw-row audit pins all proof/source/native/C/
runner/spec inputs and recomputes every admission/statistic/decision. The timing
audit's productPromoted=false records the pre-adoption stage; final summary
records the completed subsequent native gates/integration. Historical wins are
not compounded and the earlier whole19 refresh is not overwritten.

## Identity and next experiment

Current definition identity **content addresses** normalized checked typed KIR,
semantic/desugar versions, effects, interface and dependency identities. This
identifies implementations, not every mathematically equivalent computation.
A computation recipe also seals canonical arguments and observable handler/state/
resource inputs; that recipe can itself be content addressed. Reusing checked
specialization/proof/native artifacts additionally requires compiler/target/ABI/
optimization-contract pins. See the [identity contract](coscientist-content-address-20261005.md).
The native DefCID/artifact/result-cache bridge remains unconnected. This
experiment freshly executes original bodies and claims no result reuse.

Extending frame admission to two arguments alone finds zero remaining statemate
small-framed no-returning-call candidates. Retain that negative census. A next
[registered hypothesis](evidence/coscientist-small-tail-frame-20261006/next-hypothesis.json)
targets exact uncharged `uless`: signed-branch unsigned comparison,18 emitted
words,5 actual returning BL sites. Closed exact i64/i64→bool proof could permit
a native unsigned comparison at callers while retaining live values, original
fuel/trap/resource/context behavior. It is unimplemented and unmeasured; static
sites do not imply a speedup. No C-level completion claim follows from it.

## Evidence

[Summary](evidence/coscientist-small-tail-frame-20261006/summary.json),
[timing audit](evidence/coscientist-small-tail-frame-20261006/timing-audit.json),
[checksums](evidence/coscientist-small-tail-frame-20261006/checksums.sha256),
[native source/proofs](evidence/coscientist-small-tail-frame-20261006/native-proof.tgz),
[raw timing/receipts](evidence/coscientist-small-tail-frame-20261006/timing-proof.tgz),
[committed-source integration/parity](evidence/coscientist-small-tail-frame-20261006/integrated-proof.tgz).
Extract timing archive and run replay-timing-audit.py for offline independent
raw statistic/receipt validation. Native archive retains source snapshot, actual
machine generations, complete oracles/states/regression outputs, mutations,
observer partitions, unit/gates and initial failures. Integrated archive retains
external input hashes/snapshot, all3 generations and actual corpus results.
