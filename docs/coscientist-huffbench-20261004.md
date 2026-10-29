# Selfhost Huffbench: complete workload and rejected hypotheses

The complete pinned 500-byte Huffbench codec now has a Kotoba alternative,
checked and compiled by the source-built three-generation Amu image. On
asher it takes **60,339.107 ns/body**, versus unchanged C **8,278.511 ns/body**
(**7.289x slower**). C-or-better remains unachieved. This is a matched workload
research comparison, not an official full-suite Embench score.

## Correctness and execution

`bench/embench/batch-ports/huffbench.kotoba` implements input initialization,
frequency counting, heap construction, Huffman tree/codes, bit packing,
decode-table sorting, decoding, and the original 500-byte verification.
It uses one owned 3,309-cell i64 workspace, reset and reused between bodies.
The historical reduced `ports/huffbench.kotoba` is unchanged.

All **3,309 final workspace cells** match the diagnostic C observation copy.
Its decoded and compressed buffers (1,001 bytes) are cross-checked against
unchanged upstream `benchmark_body(1,1)` and `verify_benchmark`. The timed C
adapter calls unchanged `benchmark_body(1,n)`; instrumentation is untimed.
Signed C output chars are normalized to their unsigned byte values in the
state oracle. Batches 0/1/2/17/32 agree: zero iterations returns 0; positive
batches return 1. Native check and compile pass. Regeneration after adding
an explicit initialization strategy produces exactly the measured machine
bytes; updated source provenance is archived separately.

This is the fixed upstream profile, not a general arbitrary-input Huffman
API. C byte/32-bit/64-bit buffers and Kotoba i64 cells have different storage
representations. Runtime bounds, handle and fuel checks remain enabled.
The PRODUCT dependency inventory is unchanged. Python profile generation
and C measurement adapters are bootstrap tooling, outside the native codec
and native compiler execution paths; this does not prove complete product
selfhosting or an own-source process-trace gate.

## Measurement and Reflect

asher: Apple M4, Apple Clang 17 `-O2`, macOS. Thirty samples per arm, 32 bodies
per call, one untimed warmup call, calibrated to approximately 300 ms per
sample, rotating arm order. Maximum recorded load is 1.85, below the research
limit 4. CPU-idle qualification and formal native perfgate qualification are
not established. Baseline SD is 3,609.691 ns (5.98%); C SD is 466.226 ns (5.63%).

Two emitted-code Reflect prototypes memoize a previously validated vector
handle within leaf-function straight-line segments. They retain descriptor
addressing, index bounds checks, fuel accounting, trap paths and code offsets.
The second tracks exact 64-bit register copies. These are artifact-scoped
experiments, not implemented compiler optimizations. Invalid-handle, index
bounds and exhausted-fuel tests retain the original traps; paired batch fuel
consumption and all 3,309 state cells agree.

| Prototype | Same-run reference ns/body | Candidate ns/body | Reduction | Gap / summed SD ns | Verdict |
|---|---:|---:|---:|---:|---|
| x0 validation reuse, 11 patches | 60,640.107 | 58,089.190 | 4.207% | 2,550.917 / 6,126.042 | reject |
| exact-copy tracking, 16 patches | 58,120.726 | 55,784.143 | 4.020% | 2,336.584 / 5,947.717 | reject |

Both fail the 5% research threshold and sample-spread separation. These
prototype summaries were observed in completed remote harness output, but
**their raw timing/state reports have not been retrieved**: asher went offline
before the copy. Local patch metadata and guard reports are archived; the
summaries are explicitly marked `remote-raw-report-pending`, and cannot serve
as independently replayable performance evidence yet. Baseline full raw data
was retrieved. No candidate is promoted on these summaries.

A third source candidate, `--initialization fresh`, zero-initializes a new
workspace with `vector-alloc` for each body and only copies the 500 input
cells. Single-body state checks match C, but a 32-body call traps. The runner
has **65,536 vector items**; one initial allocation plus 19 body allocations
already requires 66,180 items. Local reproduction passes 17/18 bodies and
traps with SIGILL at 19/32. This candidate is rejected for the current resource
contract and has no timing result. We did not enlarge the arena or reduce
the required batch to make it pass. The measurement harness now persists
completed batch checks and the failing iteration on this failure.

## Reproduction and evidence

Upstream Embench commit: `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`;
Huffbench SHA256: `db93b8ea3c68b178348834e738ba0628c8dbf28c338d4320aebab145683d8162`.
Native compiler SHA256:
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
Both generators refuse a different upstream profile. This is new codec and
profile authoring, with no existing product source refactoring.

Generate with `generate_huffbench_port.py <libhuffbench.c> <huffbench.kotoba>`
and `generate_huffbench_oracle.py <libhuffbench.c> <c-bridge.c>`; native-check,
compile and extract `batch`, `state-cell`, and `test-huffbench`, retaining
`<symbol>-extract.log`. Place the research directory beside `runner`, pinned
`upstream`, and native `images/r6m`, then run:

```
python3 scripts/seed/image/measure-huffbench-full.py <directory>
# Same-run comparison:
python3 scripts/seed/image/measure-huffbench-full.py <candidate-directory> \
  --reference <reference-directory>
```

The harness refuses replacement of an existing report. Its final version
adds failure persistence after the remote measurements; the measured harness
version is retained with the artifacts. Evidence in
`docs/evidence/coscientist-huffbench-20261004/` contains the complete baseline
report, source/native artifacts, provenance/check/extraction logs, rejected
prototype metadata and guard checks, allocation-failure reproduction, runner
source and pinned upstream sources, plus a member hash manifest. Remote C
binaries and prototype raw reports remain on asher and are listed as pending.

Eight adapted workloads still lack complete alternatives: nettle-aes,
nsichneu, picojpeg, qrduino, sglib-combined, slre, statemate, and wikisort.
Initialization/timing audit and official size scoring remain open. Next test
bounded workspace reuse with bulk initialization, then loop/access/call
lowering; fewer instructions alone have not predicted a reliable win.

Follow-up: [bounded initialization candidates](coscientist-huffbench-reset-20261004.md)
now pass complete poisoned-workspace checks after 1/32 bodies while retaining
the arena budget. These are unmeasured experimental generator options; the
measured default and all performance claims above remain unchanged.
