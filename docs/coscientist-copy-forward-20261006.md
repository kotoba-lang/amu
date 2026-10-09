# Guarded native forward-copy composition

Adopted on the research branch after independent native proofs, fresh measurements,
permanent tests, gates and committed-source integration. Original matmult is26.937912%
shorter than the preceding whole-dot product; MD5 is11.063853% shorter. Other17 guest
binaries remain exact. C still runs3.498214x and4.409767x faster, respectively.
The all19 C-or-better goal remains open. These are aligned original-body times,
not official Embench scores or a newly measured full-suite aggregate.

Source commit: `5869e7ee14002a520aa77d5a5cdc41e76e7f03ea`.
[Summary](evidence/coscientist-copy-forward-20261006/summary.json),
[checksums](evidence/coscientist-copy-forward-20261006/checksums.sha256).

## Evidence-driven mechanism

A fresh all19 native SIR/emission census starts from the qualified whole-dot return.
It reproduces every quiet product byte and offset. Matmult FN4 and MD5 FN11 each
contain the same55-word frameless copy: their loop bodies repeat original vector
read and typed writer checks, plus private fuel charges. Static instruction counts
are not treated as dynamic time shares; runtime measurement decides adoption.
The original C source, library, runner and workload bodies stay fixed.

The compiler admits an exact28-quadruple closed typed copy and exact9-quadruple
closed typed writer, including every operand, local, entry/branch label owner and
return. Trips1..2047, destination0..2047, source starting index0, original x0/x1
leaf locals, no frame and original x8 private fuel are required. Unknown shapes,
types, local mappings and open replacements refuse composition.

After the unchanged leaf entry charge, guards require initial index0, a valid
handle, both full ranges and enough remaining fuel for all2n original writer and
backedge charges. Failure changes neither input locals nor private fuel or items
and runs the original loop. Success copies one source load followed immediately
by its destination store, then advances the pointers. This preserves overlapping
forward copies, including propagation through previously written source items.
It subtracts2n from private fuel after the bounded valid writes and publishes
through the original leaf epilogue. It does not use memcpy, result memoization,
new resource limits, capabilities or a host product fallback.

The generated copy is86 words versus55:31 added guard/fast-path words. The original
five-word private entry and50-word fallback/return tail are byte-exact in both
actual affected functions. The guarded six-instruction loop preserves scalar
load/store order; the original private-fuel store and return sequence remain.

Current definition identity is content addressing of normalized typed code,
effects and dependencies. This optimization proves native SIR structure directly;
the native DefCID/artifact/result cache bridge remains unconnected.

## Native correctness before timing

Four native compiler generations are831,000 B, SHA256
`4c36b9893d7efc6f527d262dfd6c9b957988e5d6b4a759eed5d37339b6a96755`.
All19 original results and exact fuel/fuel-trap checks agree with the prior product.
1,532 full supervisor-state comparisons include1,160 independent scalar-copy
oracles across13 source shapes,125 direct invalid/unused handles,209 original19
full/partial-fuel states and38 resource/partial-allocation states. Invalid ranges,
private fuel and partial writes remain exact; zero-trip unused handles retain the
original behavior. Native controls mutate112 copy plus36 writer fields,15 metadata
entries and four owned labels; both open replacements and invalid local mapping
refuse. Independent real/test layouts agree in code/literals and all offsets,
allowing only checked trailing zero padding. Thirty store-sentinel controls show
actual successful hits and unchanged fallback. Diagnostics never enter timing.
All19 observer and quiet emitted bytes agree.

The original480 fixtures/11,843 native executions pass before timing without a
golden change. Adoption expands to494 fixtures/14,019 native executions, with
original tables/expectations preserved as an exact prefix. Durable independent
value oracles observe copied items, overlap, zero/partial trips, invalid result
probes, high offsets, bound2047, refused2048, negative destination and extreme i64.
The normal unit reproduces the independently executed blob/offsets before its
reviewed golden update. ERR/G1-G5 pass with recorded native generations2/3/4;
seed0 is not bootstrap stage0. Existing G2/G3 refusals remain. PRODUCT and bootstrap
inventory are unchanged after removing a task-created Python bytecode cache.

Initial authoring failures are retained: a nonexistent condition helper refused
the first prototype before execution; the revised unsigned range check uses an
existing condition. The actual typed writer has an owned entry label, so its
exact schema was corrected before the successful build. The new durable fixture
helper initially left a format placeholder and was refused by the reader before
execution; the generator formatting was fixed without changing expectations or
the measured product algorithm. New algorithm/oracles are a documented one-off
hand-authoring exception; generated source uses the authoritative fixture table.

## Fresh measurements on authorized zebulun Apple M4

| Original workload | Previous product | Candidate | Same-host C | Reduction | Candidate/C |
| --- | ---: | ---: | ---: | ---: | ---: |
| matmult-int | 4.409318 µs | 3.221540 µs | 0.920910 µs | 26.937912% | 3.498214x |
| md5sum | 12.374915 µs | 11.005772 µs | 2.495772 µs | 11.063853% | 4.409767x |

Matmult accepts30 triples/30 attempts, MD5 accepts30/32. Both independently pass
the original10% maximum RSD,1.05 minimum speed ratio and mean gap beyond summed SD.
Matmult baseline/candidate/C RSD9.409%/7.478%/0.927%; MD5 2.530%/2.247%/0.339%.
Mean gaps1187.778ns/1369.142ns exceed summed SD655.757ns/560.432ns. Independent
raw-row audit recomputes means, SDs and decisions and pins source, machines, C,
runner, specification, exact fuel and pre-timing proofs. No historical speedups
are multiplied or treated as a new measurement. Both changed guests qualify;
no benchmark-name filtering or criterion change is used.

## Committed-source integration

Three generations reproduce all162 objects (117 frontend), containers, native
code and executable commands. Executable6,109,176 B, SHA256
`b6fb0799a809b10694c95a3ab119fd397eb5509046ee565089d4527da7dae76c`. Generation3 checks/compiles all19 original
sources and reproduces exactly the measured native artifacts and offsets.
All391 check/391 compile/891 export classifications,391 normalized full checker
messages and1780 native output/status files match the prior qualified product.
Existing gaps remain: compile300 behavior matches/27 Amu-only accepts/12 Amu-only
refuses/3 differing accepted behaviors/49 shared refusals; exports875 same/15
closure-handle differences/0 timeouts/1 missing. This is not100% release qualification.
Default rung records, bin/amu selection and wire20 grant remain unchanged.

Full archives preserve the fresh baseline census, prospective hypotheses, initial
failures, prototype and source snapshots, every native observation, original and
new fixture tables, normal unit, gates, both raw timing/C receipts, complete
hashed external inputs, three integrated generations and actual per-case results.
Research-branch adoption remains draft PR1222; main is unchanged.

Next registered experiment: refresh all19 current native-versus-C timings to rank
the remaining gaps, then test pair-load/pair-store copy only when overlap semantics
can be proved (even trips, destination0 or>=2). It is unimplemented and unmeasured.
