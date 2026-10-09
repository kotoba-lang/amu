# Selfhost NSichneu: all upstream transitions

The complete pinned NSichneu workload now has a native Kotoba alternative,
checked and compiled by source-built Amu. **17,272 individual state values**
agree with C across eight inputs and all 127 transition boundaries. The
production full chain also agrees on all 136 final-state values across those
inputs. asher remains offline, so this wave has **no performance result**,
no optimization promotion and no C-or-better claim. Seven adapted workloads
remain without complete alternatives; official full-suite scoring is open.

## Workload and source audit

`bench/embench/batch-ports/nsichneu.kotoba` executes all six T1 permutations
and all 120 T2 permutations in the original source order. An owned 17-cell
i64 workspace contains the three marking counts and P1[3]/P2[5]/P3[6]. Each
body resets the counts; member arrays retain their contents between bodies,
as in C. A batch allocates the workspace once, initially zeroed, and verifies
the full final state once. The historical 3,000-event simplified Petri-net
model in `ports/nsichneu.kotoba` is untouched.

The generator verifies each complete C transition block against its expected
operations before emitting new Kotoba code. Its checked manifest records
the exact order, indices, minimum input count and optional P2 compaction.
Some T2 variants require five input tokens and move the unconsumed member
to slot zero; others require four and do not move it. Omitting that distinction
would only happen to pass the default all-zero profile. Parentheses removed
for the source audit surround relational expressions joined exclusively by
`&&`; operation order and token sequences are checked. The source hash pin
remains enforced even when Python assertions are disabled.

The generated runtime uses typed helpers and a static chain of 126 calls;
it does not interpret a table, skip transitions known not to fire, or return
a stored answer. The production chain has no per-stage diagnostic limit
check. The separate stoppable chain is untimed. A single 126-binding ownership
chain was refused by native `check`, despite `compile` accepting it; the
accepted formulation uses individual typed tail-call helpers. The harness requires native check acceptance and checks the diagnostic
compiler exit status. No compiler
change or bypass of the refusal was made.

C uses volatile globals; this port uses owned checked vector operations.
State comparisons establish sequential workload parity for the recorded
inputs, not general C volatile or concurrent access semantics. No volatile
primitive is added. All array/index, handle and fuel guards remain enabled.
The native artifact is 39,596 bytes including diagnostic code; this is not
an official dummy-subtracted size score. PRODUCT dependencies are unchanged,
and Python/C generation/observation tools are outside the native product path.
This benchmark acceptance does not establish 100% product selfhosting.

## Differential evidence

The C adapter includes unchanged upstream code. An untimed observation copy
inserts snapshots before each transition and after the final transition,
without changing the original conditions/actions. For each of eight input
profiles its final 17 cells are also compared with unchanged
`benchmark_body(1,1)`. Timed C calls would use the unchanged body, after one
untimed-profile initialization per batch.

All 8 x 127 x 17 state comparisons pass. Additional inputs deliberately
exercise both kinds of transition, output saturation, negative values,
no-match equal values and P2 compaction:

| Input case | Transitions that fire (1-based) | P2[0] moved |
|---|---|---|
| 0, original zero profile | none | no |
| 1 | 1, 7 | no |
| 2 | 3, 13 | no |
| 3/4/5 | none | no |
| 6 | 31 | yes |
| 7 | 54 | no |

A separate diagnostic export exercises the **production** full chain on all
eight profiles, rather than relying solely on the stoppable chain; all 136
final-state cells match. Batches 0/1/2/17/32 match unchanged C, and one-fuel
native batch execution traps with SIGTRAP. This finite profile corpus is not
an exhaustive proof for arbitrary external marking arrays. The stage audit
input domain is cases 0..7, stages 0..126, cells 0..16, encoded as
`case*4096 + stage*17 + cell`; batch comparisons use uint32-positive iteration
counts (with zero treated as a no-op returning zero).

## Reproduction and remaining work

Upstream commit: `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`;
NSichneu SHA256: `7d15a238b045f23d5206406fe0d5a15bd4050cf0ccd7e4c3dc49fb71429e2081`.
Native Amu SHA256:
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.

Generate with `generate_nsichneu_port.py <libnsichneu.c> <nsichneu.kotoba>`
and `generate_nsichneu_oracle.py <libnsichneu.c> <c-bridge.c>`. Native-check,
compile and extract `batch`, `stage-cell` and `test-nsichneu`, keeping
`<symbol>-extract.log`. Put the directory beside the pinned `upstream`,
`runner` and source-built `images/r6m`. Then run:

```
python3 scripts/seed/image/measure-nsichneu-full.py <directory> --correctness-only
# On asher when reachable and quiet, use a fresh directory without results.json:
python3 scripts/seed/image/measure-nsichneu-full.py <fresh-directory>
```

The final harness includes the full-chain diagnostic, checks native acceptance,
refuses report replacement and persists failures. Timing requires load <= 4,
32 bodies/call, one untimed warmup, calibrated counts and 30 rotated samples
per arm. CPU-idle/formal native qualification remain separate requirements.
No timing samples were run or compared on the busy local M1 Max.

`docs/evidence/coscientist-nsichneu-20261004/` archives source/native/C artifacts,
transition manifest, provenance/check/extraction logs, full raw correctness
reports, original and final harness versions, source audit and member hashes.
Its replay bundle is prepared for asher; it is not a running process. This is
new algorithm/profile generation, not a rule-shaped refactor of product code.

Remaining complete alternatives: nettle-aes, picojpeg, qrduino,
sglib-combined, slre, statemate and wikisort. Next measure the queued Huffbench
reset candidates and this full workload on asher, recover pending previous
reports, and use separated full-body evidence to choose compiler optimizations.
The full-suite C-or-better objective remains active.
