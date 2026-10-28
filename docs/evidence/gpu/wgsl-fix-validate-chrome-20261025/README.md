# JUN-59/JUN-60: the fix rule is IMPLEMENTED and the re-emitted row JUDGES CLEAN (2026-10-25)

ONE implementation slice (the fixquestion decision's decision point 3,
implementation its own slice): the :subgroup-reduce WGSL arm now emits NO
infinite value in any position, and the whole admitted row is re-judged on
the same real shipping WGSL validator that refused the old spelling --
Google Chrome 155's Dawn/Tint through WebGPU shader creation. The 12
refusals are GONE: 18/18 VALIDATE CLEAN at the raised limits. NO
measurement ran: this is shader-creation validation, and UNMEASURED is
unchanged everywhere.

## What changed in the emitter (the fix rule's letter)

scripts/emit-gpu-subgroup-reduce-wgsl.cljk re-emits from
kotoba.compiler.accelerator-subgroup-reduce/emit-wgsl, which now carries
padded-lane-fill-wgsl instead of the bitcast identity:

- :sum keeps the finite identity in the old select shape:
  `var v:f32=select(0.0,x[i],i<n.value);`
- :max/:min carry the CLAMPED-INDEX FILL:
  `var v:f32=x[min(i,n.value-1u)];` -- every lane holds an in-range
  element (out-of-range lanes duplicate x[n-1]), and max/min idempotence
  keeps the fold exact, legitimate +-Inf input included (ADR-0356 rule
  2's ordinary-value domain).
- THE n=0 CONTRACT (the question the fix decision left to this slice):
  n >= 1 is a CALLER PRECONDITION of this arm. An empty reduce has no
  finite :max/:min answer -- the true neutral is the infinite one this
  arm must not hold -- so n=0 is out of contract and the clamp's
  n.value-1u is exact only under the precondition.
- A runtime-escape spelling stays REJECTED (15.7.3 lets implementations
  treat runtime infinities as indeterminate values and names min/max,
  this arm's combines).

## What was judged (the emitter's bytes, never hand-written)

- Corpus: docs/evidence/gpu-subgroup-reduce-wgsl-fix-20261025/shaders/ --
  18 files, the whole admitted row (W in {32,64,128,256,512,1024} x
  :sum/:max/:min), produced by
  `kbb --backend sci --classpath "src:test:$AMU_KBB_TEST_CLASSPATH" \
     scripts/emit-gpu-subgroup-reduce-wgsl.cljk \
     docs/evidence/gpu-subgroup-reduce-wgsl-fix-20261025/shaders`
  (the script gained an output-dir argument this slice; its DEFAULT path
  keeps the PRE-FIX corpus -- the judged input of the 2026-10-25
  judgment -- byte-untouched).
- Instrument: scripts/validate-gpu-subgroup-reduce-wgsl.mjs, unchanged
  (Node + Playwright, no POSIX shell file): per file the WebGPU
  shader-creation step -- createShaderModule + getCompilationInfo (the
  WGSL front end's own verdict) -- and createComputePipeline under a
  validation error scope (entry point `main`), in TWO limit regimes.

## The toolchain (identity verbatim, compile-log.txt)

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

    summary DEFAULT limits: 18 files, 12 validate clean, 6 do not
    summary RAISED limits: 18 files, 18 validate clean, 0 do not

- The 2026-10-25 refusal class ("value -inf cannot be represented as
  'f32'", was 12/18) is GONE: 0 occurrences of "cannot be represented"
  in the transcript, and compile-info: ok for all 18 files in BOTH
  regimes (36 front-end verdicts).
- The 6 default-limit non-clean verdicts are the KNOWN W >= 512 class
  and nothing else: GPUValidationError "Entry-point uses
  workgroup_size(512|1024, 1, 1) that exceeds the maximum allowed (256,
  256, 64)" -- a device-limit check, not the WGSL front end (whose
  verdict is ok on those same files); clean under the adapter's raised
  limits. The 2026-10-25 operational note (W >= 512 needs
  requiredLimits) is unchanged.
- Determinism: the corpus was produced by the emitter in one run and a
  re-run was verified byte-identical (aggregate sha256
  f3a5b60f7822e88f9cb6721432d118f126a4ebc89343e8b6203aea777e91a9d2
  over the sorted 18 files, before/after) -- same emitter, same bytes.

## State honesty (the three states)

- IMPLEMENTED (NEW this slice): the fix rule's emission
  (padded-lane-fill-wgsl in
  src/kotoba/compiler/accelerator_subgroup_reduce.cljk), the n=0
  contract (n >= 1 precondition), the spelling pins
  (test/kotoba/compiler/accelerator_subgroup_reduce_test.cljk:
  wgsl-each-operator-carries-its-combine-and-padded-lane-fill and the
  mechanical guard wgsl-arm-holds-no-infinite-value-in-any-position),
  and the re-founded cross-arm invariant
  (test/kotoba/compiler/accelerator_test.cljk:
  every-arm-shares-one-operator-meaning -- ONE meaning per operator, TWO
  mechanisms: the infinite neutral where the language allows it, the
  clamped-index fill in this arm).
- ACCEPTED DESIGN ONLY, unchanged: the fix rule as decided
  (docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/) is the
  authority this slice implements; nothing in the decision is re-litigated.
- STILL DEFECTIVE, named: the baseline :reduce WGSL arm
  (accelerator.cljk's wgsl-identity, `select(bitcast<f32>(0xFF800000u),
  ...)`) keeps the refused spelling -- the SAME defect, judged by the
  same clause, and its fix is its own later slice. It is pinned as
  emitted (the every-arm test's :wgsl column) and is not claimed clean.
- TOOLCHAIN FACTS (new, self-dated in compile-log.txt): the 36 + 18
  verdicts above.
- UNMEASURED, unchanged and still the operative claim: NO kernel
  executed this arm on any GPU, no timing exists, no speed claim of any
  kind, no :measured? flag moves, no :shapes value and no workgroup row
  (ADR-0355/0358) moves. No WebGPU execution path exists in this
  repository. Shader validation is not a measurement.

## Verification (runner output, not paraphrase)

- Scoped GPU gate (scratch runner gpu_scoped_gate.cljk, not in the repo;
  classpath route 2, `AMU_KBB_TEST_CLASSPATH` -- route 1
  `kbb -Spath -M:test` fails at the tree root since the merge 7b8f6488
  retired deps.edn), scoped-gate-touched-namespaces.txt:

      Ran 105 tests containing 10966 assertions.
      0 failures, 0 errors.

  (105 tests / 10966 assertions vs the 2026-10-25 pre-fix run's 104 /
  10948: +1 test and +18 assertions, the new no-infinite-value guard's
  6 widths x 3 operators.)
- Full suite (run-tests.cljk, same classpath route): RED AT BASE,
  outside this diff, at namespace load on `kotoba.form` ("Could not find
  namespace: kotoba.form"; the W3 port path documented red at base in
  ADR 0362 and named in every prior tick record), re-verified this tick,
  zero tests run. Full text: full-gate-kbb.txt. No green full suite is
  claimed.

## What moved in the repository

- src/kotoba/compiler/accelerator_subgroup_reduce.cljk: identity-value-
  wgsl is REPLACED by padded-lane-fill-wgsl (the fix rule + n=0
  contract), emit-wgsl's padded-lane load line changes, dated brackets
  beside the live prose.
- test/kotoba/compiler/accelerator_subgroup_reduce_test.cljk: the
  spelling pins become the fix rule's own (+ the mechanical guard test).
- test/kotoba/compiler/accelerator_test.cljk: every-arm-shares-one-
  operator-meaning re-founded (one meaning, two mechanisms).
- scripts/emit-gpu-subgroup-reduce-wgsl.cljk: output-dir argument
  (default unchanged -- the pre-fix corpus path stays byte-untouched).
- docs/adr/0356-gpu-kernel-variant-selection.md,
  docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md: dated
  IMPLEMENTED brackets beside the decided-but-unimplemented claims.
- docs/evidence/gpu-subgroup-reduce-wgsl-fix-20261025/ (NEW): the
  post-fix corpus (18 files).
- docs/evidence/gpu/wgsl-fix-validate-chrome-20261025/ (NEW): this
  README, compile-log.txt (the verbatim validation transcript),
  scoped-gate-touched-namespaces.txt, full-gate-kbb.txt. No POSIX .sh
  file anywhere in the diff (the check-workflows rule).
- UNTOUCHED: docs/evidence/gpu-subgroup-reduce-wgsl-20261025/ and
  docs/evidence/gpu/wgsl-validate-chrome-20261025/ (the pre-fix judgment
  and its corpus, historical records), every :measured? flag, every
  workgroup row.
