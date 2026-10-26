# JUN-59/JUN-60: the baseline :reduce WGSL arm's defect is JUDGED by a real toolchain (2026-10-25, pre-fix)

The fix rule's implementation slice for the baseline :reduce WGSL arm
(named "STILL DEFECTIVE, its own later slice" in
docs/evidence/gpu/wgsl-fix-validate-chrome-20261025/README.md) first
judges the DEFECT on the arm's own bytes: the pre-fix corpus is the
emitter's own output before the fix landed, and the SAME real shipping
WGSL validator that refused the :subgroup-reduce arm's old spelling
judges it. NO measurement ran: this is shader-creation validation, and
UNMEASURED is unchanged everywhere.

## What was judged (the emitter's bytes, never hand-written)

- Corpus: docs/evidence/gpu-baseline-reduce-wgsl-20261025/shaders/ --
  18 files, the whole admitted row (W in {32,64,128,256,512,1024} x
  :sum/:max/:min), produced by the NEW scripts/emit-gpu-reduce-wgsl.cljk
  through `accelerator/lower :wgsl-v1 :baseline` (the default output
  path is this pre-fix corpus and stays byte-untouched after the fix).
  Aggregate sha256 over the sorted 18 files:
  7d12f50ba0cd544df7718966ea09cdc7f92b7a39ec27194d732670e42cdf6f4d.
  The :max file at W = 32 opens with the refused spelling verbatim:
  `scratch[lid.x]=select(bitcast<f32>(0xFF800000u),x[i],i<n.value);`
- Instrument: scripts/validate-gpu-subgroup-reduce-wgsl.mjs (unchanged
  in behavior; it gained an optional transcript-title argument so this
  arm's transcript names itself), Node + Playwright, no POSIX shell
  file: per file the WebGPU shader-creation step -- createShaderModule +
  getCompilationInfo (the WGSL front end's own verdict) -- and
  createComputePipeline under a validation error scope (entry point
  `main`), in TWO limit regimes.

## The toolchain (identity verbatim, compile-log.txt)

    run-at: 2026-10-24T16:38:50.851Z (self-dated, fresh process)
    toolchain: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
      AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/155.0.0.0
    adapter-info: {"vendor":"apple","architecture":"metal-3"}
    subgroups: device created WITH subgroups
    default-limits: {"maxComputeWorkgroupSizeX":256,...}
    raised-limits (requiredLimits, adapter maxima):
      {"maxComputeWorkgroupSizeX":1024,
       "maxComputeInvocationsPerWorkgroup":1024,
       "maxComputeWorkgroupStorageSize":32768}

## Result (compile-log.txt is the transcript, verbatim)

    summary DEFAULT limits: 18 files, 4 validate clean, 14 do not
    summary RAISED limits: 18 files, 6 validate clean, 12 do not

- Refusal class 1 (12/18, both regimes, the whole :max/:min row): the
  IEEE-754 infinite neutral `bitcast<f32>(0xFF800000u)` /
  `bitcast<f32>(0x7F800000u)` const-folds and Tint answers
  "value -inf cannot be represented as 'f32'" (error@8:37) -- the SAME
  clause and the SAME class as the :subgroup-reduce arm's pre-fix
  judgment. 24 occurrences in the transcript (12 files x 2 regimes).
- Refusal class 2 (DEFAULT regime only, on the 6 W >= 512 files):
  workgroup_size(512|1024, 1, 1) above the default
  maxComputeWorkgroupSizeX 256 -- a device-limit posture, the known
  requiredLimits note, unchanged. On the :sum row that is the ONLY
  refusal (compile-info ok; those files VALIDATE CLEAN under the raised
  limits); the W >= 512 :max/:min files additionally carry class 1.
- The 4 default-limit clean verdicts are the :sum row at W = 32..256.

## State honesty (the three states)

- TOOLCHAIN FACT (new, self-dated): the 36 front-end verdicts above.
- ACCEPTED DESIGN ONLY, unchanged: the fix rule (no infinite value in
  the arm; clamped-index fill) is the authority the implementation
  slice implements -- docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/.
- STILL DEFECTIVE at the moment of this judgment: the arm as emitted
  here. Its fix and the post-fix judgment are their own slice
  (docs/evidence/gpu/wgsl-baseline-fix-validate-chrome-20261025/).
- UNMEASURED, unchanged and still the operative claim: NO kernel
  executed this arm on any GPU, no timing exists, no speed claim of any
  kind, no :measured? flag and no workgroup row (ADR-0355/0358) moves.
  No WebGPU execution path exists in this repository. Shader validation
  is not a measurement.
