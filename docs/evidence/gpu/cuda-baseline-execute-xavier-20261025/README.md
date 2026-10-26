# JUN-57: the :baseline CUDA arm's bytes EXECUTE on real GPU hardware -- VERDICT EXECUTED-CORRECT, 36/36 cells (2026-10-25)

ONE implementation slice: the first half of the CUDA execute record's
HONEST LEFT (a) -- "the :baseline CUDA arm's emission and the
paired-timing protocol" -- is taken now: the emission half. The
:baseline arm's corpus is emitted from the emitter (never hand-written),
compiles clean with the real nvcc and PASSES the same ADR-0373-kind
correctness instrument on the fleet's CUDA host. With this, all three
CUDA arms of the reduce row (:subgroup-reduce, :warp-shuffle-reduce,
:baseline) are EXECUTED-CORRECT on the same hardware from emitter bytes
-- the comparison arms the paired-timing protocol will need exist and
verify. CORRECTNESS ONLY, UNMEASURED: this instrument records no timing
of any kind, no speed claim exists, and no :measured? flag, workgroup
row, :shapes value or selection answer moves (rule 4).

## The emission (scripts/emit-gpu-baseline-reduce-cuda.cljk, new)

- Corpus: docs/evidence/gpu-baseline-reduce-cuda-20261025/shaders/ (18
  files, W in {32..1024} x {sum, max, min}), the emitter's own bytes via
  (accelerator/lower kir :cuda-v1 :baseline) -- the ADR-0002 v1
  emission (accelerator.cljk's emit-cuda :baseline/:reduce path).
- The arm is WORKGROUP-SIZE-PARAMETRIC (W never enters the bytes: the
  fold reads blockDim.x, the scratch is `extern __shared__ float s[]`
  sized at launch), so the six width files of one operator are
  byte-identical -- 3 distinct sha256 over the 18 files, recorded in the
  corpus NOTES.md. Determinism re-checked this tick: a second emit run
  produced byte-identical files.
- At launch the arm takes W*4 bytes of DYNAMIC shared memory (the
  instrument's <shared-bytes> argument), 128..4096 across the row.

## What ran (host: xavier, Tailscale; compile-and-run-log.txt verbatim)

HOST: xavier USER: root; Linux xavier 5.10.120-tegra aarch64 (NVIDIA
Jetson AGX Xavier, L4T R35.4.1); nvcc: NVIDIA CUDA compiler driver,
Cuda compilation tools, release 11.4, V11.4.315; device=Xavier sm_72
(read by the instrument through the driver API). DATE-UTC
2026-10-25T01:41:34Z.

- Corpus integrity: the 19 received files' sha256 (18 corpus .cu + the
  instrument, gpu-cuda-reduce-verify.cu unchanged from the 2026-10-25
  CUDA execute slice) are IDENTICAL to the local committed listing
  (diff empty, re-derived from the log's own sha block). This tick's
  transfer carried no macOS AppleDouble `._*` files (COPYFILE_DISABLE),
  so the remote tree is exactly 19 .cu files.
- Toolchain: instrument OK-instrument; corpus 18/18 OK-cubin, 0
  FAIL-cubin; every nvcc diagnostic file 0 bytes.
- Cells: 2 shapes (n = 1000003 and 1048576) x 6 widths (W in 32..1024)
  x 3 operators (sum, max, min) x 1 arm = 36 cells, one process per
  cell (the instrument's LCG resets per process, so a cell's input is
  the same input the earlier arms' runs saw at that shape -- pairing
  provenance for the later timing row). Launch: grid = ceil(n/W),
  block = W, shared-bytes = W*4.
  === cells run: 36  failed cells: 0 ===
- 36/36 verify lines carry ok=1 (0 lines with ok=0).
  * :max/:min (24 cells): bit_exact_vs_ref=1 in 24/24 -- bit-for-bit
    against the double CPU reference, rule 2's requirement met.
  * :sum (12 cells): max_abs_vs_ref at most 3.26633453e-05 (all well
    under the 0.05 bound the Metal instrument set; bit-exactness
    honestly 0 where the tree regrouping moved the low bits).
- Instrument semantics unchanged from the CUDA execute slice: the
  Metal instrument's exact LCG (seed 20261023), the same padded-lane
  double CPU reference, :sum by deviation bound, :max/:min bit-for-bit,
  positional argv >= gates that REFUSE out-of-bound values.

## State honesty (the three states)

- IMPLEMENTED (code + record): scripts/emit-gpu-baseline-reduce-cuda.cljk
  and the corpus. The arm itself was already implemented (the ADR-0002
  v1 emission) -- this row gives it a corpus and hardware execution.
- MEASURED: NOTHING. No timer ran. EXECUTED-CORRECT is a correctness
  verdict, not a measurement; every speed question on the CUDA channel,
  including the :baseline arm's own speed, is UNMEASURED and this slice
  claims none.
- ACCEPTED DESIGN ONLY: the ADR-0373 instrument class; the
  claim-protocol rules 1-4 remain MSL/WGSL-channel records.
- UNMEASURED, named: every timing/speed fact for the CUDA arms
  (including :baseline); any CUDA variant-cell flip (needs the
  paired-timing protocol + the claim-protocol adoption row for this
  channel); every workgroup row (the ADR-0358 row channel is the
  wire-42 protocol -- untouched here; :arm/:unknown stay provisional
  :measured? false).

HONEST LEFT (the real remainder): (a-rest) the paired-timing protocol
(interleaved pairs, alternating order, CUDA-event gpu-ns + host
submit->done ns) of the ADR-0373 kind -- all three comparison arms now
execute and verify on this host; (b) the claim-protocol adoption row
for the CUDA channel (sign claims channel-scoped; a CUDA measurement
never flips an MSL/WGSL cell); (c) the :warp-shuffle-reduce vs
:subgroup-reduce vs :baseline speed question itself.

## Gates (this slice)

- Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo): GREEN -- 106 tests / 11046
  assertions / 0 failures / 0 errors, exit 0 (the real-spawn glslang
  16.6.0 version line present in the output). The diff touches no .cljk
  namespace under test (scripts/emit-gpu-baseline-reduce-cuda.cljk is a
  new emitter driver; docs/evidence is records) -- the gate runs as the
  standing GPU-owned check.
- FULL run-tests.cljk: NOT RUN this slice (the tick's run-time budget
  went to the hardware run and this record) -- named so nothing is
  implied. Documented red at base ("Could not find namespace:
  kotoba.form", the W3 port path, ADR-0362), outside this diff, not
  re-verified here. NO green full suite is claimed.
- Evidence hygiene: no POSIX .sh execution file exists anywhere under
  docs/ (checked this tick before commit).

Evidence: docs/evidence/gpu/cuda-baseline-execute-xavier-20261025/
(compile-and-run-log.txt + this README) and
docs/evidence/gpu-baseline-reduce-cuda-20261025/ (NOTES.md + shaders/
18 files).
