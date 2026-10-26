# The :baseline CUDA arm's corpus (2026-10-25)

The emitted :baseline (:reduce) CUDA sources of
scripts/emit-gpu-baseline-reduce-cuda.cljk -- the emitter's own bytes
(accelerator.cljk's emit-cuda :baseline/:reduce path, the ADR-0002 v1
emission), never hand-written. 18 files: W in {32, 64, 128, 256, 512,
1024} x operator in {sum, max, min}.

## Properties (recorded and checked, never assumed)

- WORKGROUP-SIZE-PARAMETRIC: W never enters the bytes. The fold reads
  blockDim.x and the scratch is `extern __shared__ float s[]`, sized at
  launch (the arm needs W*4 bytes of DYNAMIC shared memory -- the verify
  instrument's <shared-bytes> argument). So the six width files of one
  operator are BYTE-IDENTICAL: exactly 3 distinct sha256 over 18 files,
  one per operator (below).
- Deterministic: a second run of the emit script produced byte-identical
  files (sha256 listing diff empty over all 18).
- UNCOMPILED on this host (no nvcc). [COMPILED+EXECUTED 2026-10-25 on
  the fleet's CUDA host xavier -- these exact bytes, sha256-identical,
  compile clean with the real nvcc 11.4 (V11.4.315) at -arch=sm_72 and
  pass the ADR-0373-kind correctness instrument 36/36 cells; the run
  record docs/evidence/gpu/cuda-baseline-execute-xavier-20261025/.]
  CORRECTNESS ONLY: no timing exists anywhere in that run and no speed
  claim is made or implied.

## sha256 per file

    eb5322568fdebf2728a39c967bf776c623aa924b93fbb56b5164379fb2cf8977  baseline-reduce-w{32,64,128,256,512,1024}-sum.emitted.cu
    3b1ccbae3445da8b83d7a0bfeac92f4acf10ba8d100c46411d9ebddc26b68dfd  baseline-reduce-w{32,64,128,256,512,1024}-max.emitted.cu
    5d76a5730bd7c0ede60f8b10cc81f6f4887202d69f705a7ccd760a736e2ff0c4  baseline-reduce-w{32,64,128,256,512,1024}-min.emitted.cu

(one digest per operator; all six width files of that operator share it
-- the parametricity above, as data)

## State

- IMPLEMENTED: the emission (this corpus + its emit script). The arm
  itself was already implemented (accelerator.cljk's emit-cuda
  :baseline/:reduce) -- this row gives it a corpus, a provenance record
  and (2026-10-25) hardware execution.
- MEASURED: nothing (no timer exists in this record's channel).
- No :measured? flag, workgroup row, :shapes value or selection answer
  moves (rule 4).
