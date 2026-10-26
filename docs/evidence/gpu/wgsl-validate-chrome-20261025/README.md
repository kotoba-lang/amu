# JUN-59/JUN-60: the :subgroup-reduce WGSL arm is JUDGED by a real toolchain (2026-10-25)

ONE implementation slice (backlog item 4): the WGSL arm's named UNCOMPILED
state -- "no WGSL compiler or validator exists on this host" -- is examined
on a REAL shipping WGSL validator. The toolchain now answers, and it does
NOT answer clean: 12 of the 18 emitted sources are REFUSED. The refusal is
the finding. NO measurement ran: this is shader-creation validation, and
UNMEASURED is unchanged everywhere.

## What was judged (the emitter's bytes, never hand-written)

- Corpus: docs/evidence/gpu-subgroup-reduce-wgsl-20261025/shaders/ --
  18 files, the whole admitted row (W in {32,64,128,256,512,1024} x
  :sum/:max/:min), produced by scripts/emit-gpu-subgroup-reduce-wgsl.cljk
  (NEW this tick, the WGSL twin of the MSL/CUDA emit scripts).
- Determinism, re-verified live this tick: the script was re-run and the
  18-file corpus hash is byte-identical (aggregate sha256
  9ec72106bf5ae1bd18a2a675e7eed4b7b01c7354f8f9a37c8e5eb9d3d024732d
  before/after).
- Instrument: scripts/validate-gpu-subgroup-reduce-wgsl.mjs (NEW this
  tick; Node + Playwright, no POSIX shell file). Per file it runs the
  WebGPU shader-creation step -- createShaderModule + getCompilationInfo
  (the WGSL front end's own verdict) -- and createComputePipeline under a
  validation error scope (entry point `main`), in TWO limit regimes.

## The toolchain (identity verbatim, compile-log.txt)

Google Chrome 155 (HeadlessChrome/155.0.0.0) on macOS, its Dawn/Tint
WGSL front end driven through WebGPU:

    toolchain: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
      AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/155.0.0.0
    adapter-info: {"vendor":"apple","architecture":"metal-3"}
    subgroups: device created WITH subgroups
    default-limits: {"maxComputeWorkgroupSizeX":256,
      "maxComputeInvocationsPerWorkgroup":256,"maxComputeWorkgroupStorageSize":16384}
    raised-limits (requiredLimits, adapter maxima):
      {"maxComputeWorkgroupSizeX":1024,
       "maxComputeInvocationsPerWorkgroup":1024,
       "maxComputeWorkgroupStorageSize":32768}

Toolchain landscape named in the record (measured 2026-10-25): Deno
2.7.14's bundled wgpu/Naga REFUSES `enable subgroups;` outright
("this enable-extension specifies standard functionality which is not yet
implemented in Naga") and can judge nothing in this arm. Chrome's Tint
carries the `subgroups` WebGPU feature and judges it.

## Result (compile-log.txt is the transcript, verbatim)

    summary DEFAULT limits: 18 files, 4 validate clean, 14 do not
    summary RAISED limits: 18 files, 6 validate clean, 12 do not

Two named refusal classes, both reproduced in the transcript:

1. THE INFINITE NEUTRALS ARE REFUSED (12/18: the :max and :min rows at
   every W, both limit regimes). The arm's identity is the IEEE-754
   bit pattern bitcast<f32>(0xFF800000u) / bitcast<f32>(0x7F800000u)
   (the ns docstring: "no infinity literal exists there either, bitcast
   of the IEEE-754 bits is exact"). The validator const-folds the
   bitcast and answers, at error@9:33 of every refused file:

       error@9:33 value -inf cannot be represented as 'f32'
       (the :min rows: "value inf cannot be represented as 'f32'")

   and the pipeline then fails "[Invalid ShaderModule] is invalid due to
   a previous error". The spelling is pinned to the merged gpuweb
   subgroups proposal + W3C WGSL spec (fetched 2026-10-23) -- so this is
   either a Tint const-eval refusal of a spec-legal constant or a real
   spec-drift defect in the emitter. WHICH ONE is a design decision and
   the NEXT slice; this slice records the refusal, not its fix. The
   tests' spelling pins stand unchanged beside it.

2. WORKGROUP-SIZE DEFAULT LIMITS REFUSE W >= 512 (2/18: w512-sum and
   w1024-sum, DEFAULT regime only). Verbatim:

       GPUValidationError: Entry-point uses workgroup_size(512, 1, 1)
       that exceeds the maximum allowed (256, 256, 64). This adapter
       supports higher maxComputeWorkgroupSizeX of 1024 ...

   This is a LIMIT POSTURE, not a byte defect: under raised limits (the
   adapter's own maxima via requiredLimits) both files VALIDATE CLEAN.
   Operational consequence for any future WGSL route: a workgroup row of
   512/1024 requires the device request to raise
   maxComputeWorkgroupSizeX / maxComputeInvocationsPerWorkgroup.

CLEAN, both regimes (the :sum row at W = 32/64/128/256; at raised limits
also W = 512/1024): the whole emitted text validates and the entry point
`main` links into a compute pipeline with zero messages.

## State honesty (the three states)

- IMPLEMENTED (code + test): unchanged -- the emission, its text
  contracts and their tests landed 2026-10-23 and are untouched
  behaviorally. NEW this tick: the two evidence instruments
  (scripts/emit-gpu-subgroup-reduce-wgsl.cljk,
  scripts/validate-gpu-subgroup-reduce-wgsl.mjs) and this record.
- NEW TOOLCHAIN FACT, taken 2026-10-25 (self-dated run-at
  2026-10-24T15:18:39Z = 2026-10-25 00:18 JST): the arm's emitted row is
  JUDGED by Chrome 155's Dawn/Tint. The arm leaves the UNCOMPILED regime
  with 6 clean and 12 refused, the refusals named verbatim above. The
  old claim ("no WGSL compiler or validator exists on this host") was
  true when written and is now bracketed in the live prose; historical
  records are NOT rewritten.
- UNMEASURED, unchanged and still the operative claim: NO kernel
  executed this arm on any GPU, no timing exists, no speed claim of any
  kind, no :measured? flag moves, no :shapes value and no workgroup row
  (ADR-0355/0358) moves. No WebGPU execution path exists in this
  repository. Shader validation is not a measurement.
- PROPOSED: the fix for refusal class 1 (what the :max/:min identity
  should spell so a shipping validator accepts it) -- no decision taken
  here.

## Verification (runner output, not paraphrase)

- Scoped GPU gate (the GPU-owned test namespaces; scratch runner
  gpu_scoped_gate.cljk, not in the repo; classpath route 2,
  `AMU_KBB_TEST_CLASSPATH` -- route 1 `kbb -Spath -M:test` fails at the
  tree root since the merge 7b8f6488 retired deps.edn),
  scoped-gate-touched-namespaces.txt:

      Ran 104 tests containing 10948 assertions.
      0 failures, 0 errors.

- Full suite (run-tests.cljk, same classpath route): RED AT BASE,
  outside this diff, at namespace load on `kotoba.form` ("Could not find
  namespace: kotoba.form"; the W3 port path documented red at base in
  ADR 0362 and named in every prior tick record), re-verified this tick,
  zero tests run. Full text: full-gate-kbb.txt. No green full suite is
  claimed. This diff changed no behavior: its code changes are two NEW
  scripts and dated comment/docstring/ADR brackets.

## What moved in the repository

- scripts/emit-gpu-subgroup-reduce-wgsl.cljk (NEW): the corpus emitter.
- scripts/validate-gpu-subgroup-reduce-wgsl.mjs (NEW): the instrument.
- docs/evidence/gpu-subgroup-reduce-wgsl-20261025/ (NEW): 18 emitted
  sources (the corpus, committed so the judgment is re-takeable).
- docs/evidence/gpu/wgsl-validate-chrome-20261025/ (NEW): this README,
  compile-log.txt (the verbatim validation transcript), and the two gate
  transcripts (scoped-gate-touched-namespaces.txt, full-gate-kbb.txt).
  No POSIX .sh file anywhere in the diff (the check-workflows rule).
- src/kotoba/compiler/accelerator_subgroup_reduce.cljk,
  src/kotoba/compiler/accelerator.cljk,
  test/kotoba/compiler/accelerator_subgroup_reduce_test.cljk,
  docs/adr/0356-gpu-kernel-variant-selection.md,
  docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md: dated brackets
  beside the UNCOMPILED claims as written. PROSE/DOCS ONLY.
