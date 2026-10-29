# CUDA paired-timing run -- xavier, 2026-10-25 (JUN-57 HONEST LEFT (a-rest))

The paired-timing protocol of the baseline execute record's HONEST LEFT
(a-rest) LANDS: the protocol instrument exists
(scripts/gpu-cuda-reduce-timing.cu) and the protocol RAN on real GPU
hardware over the whole three-arm grid. This record is MEASURED TIMING
DATA and nothing more -- no sign claim is made anywhere in it (below).

HOST: xavier USER: root; Linux xavier 5.10.120-tegra aarch64 (NVIDIA
Jetson AGX Xavier, L4T R35.4.1); nvcc: NVIDIA CUDA compiler driver,
Cuda compilation tools, release 11.4, V11.4.315; device=Xavier sm_72
(read by the instrument through the driver API). DATE-UTC
2026-10-25T02:14:18Z.

## The instrument (scripts/gpu-cuda-reduce-timing.cu)

MEASUREMENT INSTRUMENT, the ADR-0373 kind written for the CUDA channel
(a native harness of the class that instrument named for Metal): NOT
repository product code, NOT a wire-42 route -- cuModuleLoad of the
emitters' own .cubin output through the CUDA driver API. One PAIR of
arms per invocation (a fresh process per pair block, the Metal
instrument's fresh-process run), the Metal instrument's exact protocol
constants and input generator:

- PAIRS = 20 interleaved pairs per block; WARMUP = 2 discarded submits
  per arm first.
- Alternating order within the pair sequence (pair p runs arm
  ((p+k) mod 2 == 0) first for k = 0, 1 -- AB on even p, BA on odd p),
  so clock drift cannot favor one arm (the paired-within-run statistic
  of ADR-0358 / the Metal instrument).
- TWO clocks per timed dispatch, both recorded:
  gpu_ns = CUDA-event elapsed around the kernel on the GPU timeline
  (event record -> event record, same stream); host_ns = CLOCK_MONOTONIC
  around submit -> completion (the launch call through the stop event's
  synchronize). The stop event's own host-side record call sits INSIDE
  the host span -- named here, not hidden.
- Input: the Metal instrument's LCG (seed 20261023, xs[i] =
  (lcg_next() >> 8) / 2^24 in [0, 1)), reset per process -- a pair
  block's two arms see the same input, and a cell's input equals the
  input the correctness instrument's runs saw at that shape (pairing
  provenance across records).
- After the pairs: an untimed verified read-back per arm, the
  correctness instrument's exact verify semantics (:sum by observed max
  deviation against the 0.05 bound the Metal instrument set; :max/:min
  bit-for-bit against the double CPU reference in the ordinary value
  domain).
- Positional argv gates refuse out of bound values (workgroup a power of
  two in [32, 1024], elements in [1, 2^24], shared-bytes in [0, 49152],
  non-empty arm labels <= 32 chars, the two arms of a pair must differ,
  the entry must be reduce_<op> for the op being run).

## The run (compile-and-run-log.txt)

- Corpus integrity: the 55 received files' sha256 (54 emitted .cu -- the
  three arms' committed corpora, 18 each -- plus the instrument) are
  IDENTICAL to the local staged/committed listing (diff empty,
  re-derived this tick). No AppleDouble `._*` files transferred.
- Toolchain: instrument OK-instrument (a first session failed to LINK
  -- named, not hidden, below); corpus 54/54 OK-cubin, 0 FAIL-cubin;
  every nvcc diagnostic file 0 bytes.
- Grid: 2 shapes (n = 1000003 and 1048576) x 6 widths (W in 32..1024) x
  3 operators (sum, max, min) x 3 pair types (subgroup/baseline,
  warp-shuffle/baseline, warp-shuffle/subgroup) = 108 pair blocks, one
  fresh process each, plus one smoke block (n=1000003 W=256 op=sum
  subgroup/baseline, rc=0, excluded from the derived table as a
  duplicate of a grid block).
  === cells run: 108  failed cells: 0 ===
- Samples: 4320 timed dispatches in the grid (108 blocks x 20 pairs x 2
  arms; 4360 with the smoke block). Every block has all 20 of its pairs
  complete (0 incomplete).
- Verified read-back inside the measurement: 218/218 verify lines
  ok=1 (216 grid + 2 smoke; 0 lines with ok=0).
  * :max/:min (144 grid verifies): bit_exact_vs_ref=1 in 144/144 --
    rule 2's requirement met inside the timing instrument too.
  * :sum (72 grid verifies): max_abs_vs_ref at most 3.26633453e-05
    (well under the 0.05 bound).

## Derived data (paired-ratios.txt) -- RAW DATA, NOT A SIGN CLAIM

paired-ratios.txt holds the per-block paired-median ratios, the MSL
channel's statistic (median over the 20 within-pair ratios armA/armB on
the named clock; < 1.0 means armA was faster in that pair), derived
from the committed log's own sample lines by the parse in
scratch/derive-cuda-paired-20261025.py (re-runnable against this log;
108 rows, both clocks, per-row min..max spread included). The two
shapes agree closely on every (W, pair) triple (see the file).

NO VERDICT accompanies these numbers. The claim-protocol adoption row
for the CUDA channel -- HONEST LEFT (b), "sign claims channel-scoped; a
CUDA measurement never flips an MSL/WGSL cell" -- is NOT written, so no
rule-2-class sign claim exists for this channel and none is made or
implied here. The :warp-shuffle-reduce vs :subgroup-reduce vs :baseline
speed question -- HONEST LEFT (c) -- is answered by NO record yet; it is
its own row, and it is the row these samples were taken to serve.

## Named defect (not hidden)

The first session of this run failed at the instrument LINK step (the
driver-API symbols cuInit/cuModuleLoad/... undefined: the nvcc compile
line lacked -lcuda); every grid cell of that session returned 127 (no
binary) and produced NO data. The compile line was fixed (-lcuda), the
remote tree wiped and re-transferred (so the sha block covers exactly
the 55 received files), and the committed log is the second session,
which is complete. Nothing from the first session is quoted as data.

## State honesty (the three states)

- IMPLEMENTED (code): scripts/gpu-cuda-reduce-timing.cu -- the
  paired-timing instrument. Measurement instrument, not product code.
- MEASURED: 4360 paired timing samples (gpu_ns + host_ns) on real GPU
  hardware (xavier sm_72) -- the CUDA channel's FIRST timing data -- and
  the correctness verdicts above (re-verified inside the measurement).
- ACCEPTED DESIGN ONLY: the ADR-0373 instrument class and the ADR-0358
  paired-within-run statistic this protocol follows; the claim-protocol
  rules 1-4 remain MSL/WGSL-channel records.
- UNMEASURED, named: every CUDA sign/speed verdict (needs (b), then
  (c)); the clock/thermal regime structure of these blocks (one process
  per block, one session, no regime control -- the paired ratio's
  regime sensitivity is a known MSL-channel hazard and is unexamined
  here); every workgroup row (ADR-0355's 2026-10-25 channel rule: this
  is the instrument channel, not the row's own wire-42 channel, so it
  answers no row; :arm/:unknown stay provisional :measured? false).
- No :measured? flag, workgroup row, :shapes value or selection answer
  moves (rule 4).

## Gates (this slice)

- Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo): GREEN -- 106 tests / 11046
  assertions / 0 failures / 0 errors. The diff touches no .cljk
  namespace under test (scripts/gpu-cuda-reduce-timing.cu is a new
  measurement instrument; docs/evidence is records) -- the gate is a
  regression pin.
- FULL run-tests.cljk: NOT RUN this slice (the tick's run-time budget
  went to the hardware run and this record) -- named so nothing is
  implied. Documented red at base ("Could not find namespace:
  kotoba.form", the W3 port path, ADR-0362), outside this diff, not
  re-verified here. NO green full suite is claimed.
- Evidence hygiene: no POSIX .sh execution file exists anywhere under
  docs/ (checked this tick before commit). The run driver lived in the
  Hermes scratch directory and was never staged.

Evidence: docs/evidence/gpu/cuda-paired-timing-xavier-20261025/
(compile-and-run-log.txt + paired-ratios.txt + this README).
