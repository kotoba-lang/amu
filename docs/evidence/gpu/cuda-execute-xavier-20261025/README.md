# JUN-57: the :subgroup-reduce and :warp-shuffle-reduce CUDA arms EXECUTE on real GPU hardware for the first time (2026-10-25)

ONE implementation slice (backlog item 4, JUN-57): the row the
warp-shuffle compile record's HONEST LEFT named -- "both CUDA arms stay
UNEXECUTED and UNMEASURED on every vendor ... an execution/measurement
row needs the ADR 0371 provider track (or a native-CUDA harness of the
ADR-0373 kind) and is its own decision + row" -- is that row's execution
half, taken now with the instrument half. The ADR-0373-kind instrument
(measurement instrument, NOT product code, NOT a wire-42 route) loads
the EMITTER'S OWN CUDA output through the CUDA driver API on the
fleet's only CUDA host. VERDICT: EXECUTED-CORRECT -- 72/72 cells answer
exact against the CPU reference. CORRECTNESS ONLY, UNMEASURED: this
instrument records no timing of any kind, no speed claim exists, and no
:measured? flag, workgroup row, :shapes value or selection answer moves
(rule 4).

## The instrument (scripts/gpu-cuda-reduce-verify.cu, new this tick)

The correctness instrument of the ADR-0373 kind for the CUDA channel:
it loads one emitted arm's .cubin (nvcc -arch=sm_72 -cubin of the
committed corpus bytes) with cuModuleLoad, launches reduce_<op> once as
warmup and once as the verification launch, and checks the partials
against a double CPU reference folded over the same padded-lane shape,
with the Metal instrument's exact semantics
(scripts/gpu-subgroup-reduce-metal-measure.m): :sum judged by the
observed max deviation against the 0.05 bound (the tree regrouping
moves the low bits), :max/:min required BIT-FOR-BIT with (float)ref in
the ordinary value domain (rule 2). Input is the Metal instrument's
exact LCG (seed 20261023, xs[i] = (lcg_next() >> 8) / 2^24, [0,1)).
Launch: grid = ceil(n/W), block = W, dynamic shared W/32 floats for the
:warp-shuffle-reduce arm (extern __shared__ scratch) and 0 for the
:subgroup-reduce arm (its __shared__ partials[W] is static, sized from
the emitted W). Every positional gate is a >= test; out-of-bound values
are REFUSED, never clamped. NO `sample` line exists in this instrument:
no CUDA events, no host clock span. The paired-timing protocol
(interleaved pairs, alternating order, warmup discard) and the
claim-protocol adoption row for the CUDA channel stay their own later
rows.

## What ran (host: xavier, Tailscale; compile-and-run-log.txt verbatim)

HOST: xavier USER: root; Linux xavier 5.10.120-tegra aarch64 (NVIDIA
Jetson AGX Xavier, L4T R35.4.1); nvcc: NVIDIA CUDA compiler driver,
Cuda compilation tools, release 11.4, V11.4.315; device=Xavier sm_72
(read by the instrument through the driver API). DATE-UTC
2026-10-25T01:23:55Z.

- Corpus: the COMMITTED emitter bytes, never hand-written:
  docs/evidence/gpu-subgroup-reduce-cuda-20261023/shaders (18) +
  docs/evidence/gpu-warp-shuffle-reduce-cuda-20261024/shaders (18).
  Integrity: the 37 received files' sha256 (36 .cu + the instrument)
  are IDENTICAL to the local listing (diff empty over the 37 content
  files; the extraction also left macOS AppleDouble `._*` metadata
  files in the remote directory -- archive artifacts, not corpus files;
  every glob in the run is a non-dotfile glob, and exactly 36 files
  compiled).
- Toolchain: instrument nvcc -O2 -arch=sm_72 ... -lcuda -> OK-instrument;
  corpus 36/36 OK-cubin, 0 FAIL-cubin, diagnostics NONE.
- Cells: 2 shapes (n = 1000003 and 1048576) x 6 widths (W in 32..1024)
  x 2 arms (:subgroup-reduce, :warp-shuffle-reduce) x 3 operators
  (sum, max, min) = 72 cells, one process per cell.
  === cells run: 72  failed cells: 0 ===
- 72/72 verify lines carry ok=1 (0 lines with ok=0).
  * :max/:min (48 cells): bit_exact_vs_ref=1 in 48/48 -- bit-for-bit
    against the double CPU reference, rule 2's requirement met.
  * :sum (24 cells): max_abs_vs_ref at most 3.26633453e-05 (all well
    under the 0.05 bound); bit-exactness honestly 0 where the tree
    regrouping moved the low bits, reported as data not hidden.

## State honesty (the three states)

- IMPLEMENTED (code): scripts/gpu-cuda-reduce-verify.cu -- the
  correctness instrument. Its "test" is this run itself: an instrument
  that answers ok=1 against a known reference on 72 cells is exercised
  code; there is no .cljk surface to test.
- MEASURED: NOTHING. No timer ran. EXECUTED-CORRECT is a correctness
  verdict, not a measurement; every speed question on the CUDA channel
  is UNMEASURED and this slice claims none.
- ACCEPTED DESIGN ONLY: the ADR-0373 instrument class (quoted above);
  the claim-protocol rules 1-4 remain MSL/WGSL-channel records.
- UNMEASURED, named: every timing/speed fact for the CUDA arms (no
  timer exists in this instrument by design); any CUDA variant-cell
  flip (needs the paired-timing protocol + claim-protocol adoption row,
  its own decision); every workgroup row (the ADR-0358 row channel is
  the wire-42 protocol -- untouched here); :arm and :unknown workgroup
  rows stay provisional (:measured? false).

HONEST LEFT (the real remainder): (a) the :baseline CUDA arm's emission
and the paired-timing protocol (interleaved pairs, alternating order,
CUDA-event gpu-ns + host submit->done ns) of the ADR-0373 kind; (b) the
claim-protocol adoption row for the CUDA channel (sign claims
channel-scoped; a CUDA measurement never flips an MSL/WGSL cell); (c)
the :warp-shuffle-reduce vs :subgroup-reduce speed question itself.

## Gates (this slice)

- The diff touches NO .cljk namespace (scripts/*.cu + docs/evidence
  only). The scoped GPU gate (8 GPU-owned namespaces) and the full
  run-tests.cljk were NOT RUN this slice: the run-time budget expired
  after the hardware run and the record -- named here so nothing is
  implied (the b0fb13700 idiom). The full suite's documented red at
  base ("Could not find namespace: kotoba.form", the W3 port path,
  ADR-0362) is outside this diff and not re-verified here. NO green
  suite is claimed.
- No POSIX .sh execution file exists anywhere under docs/ (this
  record's directory holds this README and one .txt log).

Evidence: docs/evidence/gpu/cuda-execute-xavier-20261025/
(compile-and-run-log.txt + this README).
