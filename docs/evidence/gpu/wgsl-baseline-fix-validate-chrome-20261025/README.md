# JUN-59/JUN-60: the baseline :reduce WGSL arm's fix is IMPLEMENTED and the re-emitted row JUDGES CLEAN (2026-10-25)

ONE implementation slice -- the "own later slice" the :subgroup-reduce
WGSL fix named (docs/evidence/gpu/wgsl-fix-validate-chrome-20261025/README.md,
"STILL DEFECTIVE"): the baseline :reduce WGSL arm
(accelerator.cljk's `emit-wgsl`) now emits NO infinite value in any
position, and its whole admitted row is judged -- before the fix (the
defect itself) and after -- on the same real shipping WGSL validator.
The 12 refusals are GONE: 18/18 VALIDATE CLEAN at the raised limits. NO
measurement ran: this is shader-creation validation, and UNMEASURED is
unchanged everywhere.

## What changed in the emitter (the fix rule's letter, both readings)

`wgsl-identity` (the bitcast infinite neutral) is REPLACED by
`wgsl-fill` in src/kotoba/compiler/accelerator.cljk (Kotoba reading and
host reading alike), the same padded-lane-fill rule the
:subgroup-reduce WGSL arm carries:

- :sum keeps the finite identity in the old select shape -- its bytes
  are UNCHANGED by this fix (verified: the :sum corpus files are
  byte-identical before/after):
  `scratch[lid.x]=select(0.0,x[i],i<n.value);`
- :max/:min carry the CLAMPED-INDEX FILL:
  `scratch[lid.x]=x[min(i,n.value-1u)];` -- every lane holds an in-range
  element (out-of-range lanes duplicate x[n-1]), and max/min idempotence
  keeps the fold exact, legitimate +-Inf input included (ADR-0356 rule
  2's ordinary-value domain).
- THE n=0 CONTRACT: n >= 1 is a CALLER PRECONDITION of this arm, the
  same decision as the :subgroup-reduce arm (an empty reduce has no
  finite :max/:min answer -- the true neutral is the infinite one this
  arm must not hold -- so n=0 is out of contract and the clamp's
  n.value-1u is exact only under the precondition).
- A runtime-escape spelling stays REJECTED (15.7.3 lets implementations
  treat runtime infinities as indeterminate values and names min/max,
  this arm's combines).

## What was judged (the emitter's bytes, never hand-written)

- Corpora: docs/evidence/gpu-baseline-reduce-wgsl-20261025/shaders/
  (PRE-fix, the judged input of the pre-fix judgment --
  docs/evidence/gpu/wgsl-baseline-validate-chrome-20261025/ -- kept
  byte-untouched) and docs/evidence/gpu-baseline-reduce-wgsl-fix-20261025/shaders/
  (POST-fix), 18 files each (W in {32,64,128,256,512,1024} x
  :sum/:max/:min), produced by scripts/emit-gpu-reduce-wgsl.cljk.
  Post-fix aggregate sha256 over the sorted 18 files:
  4bef863329ed7e6b8f13acc50c97902595605afd5099f6b2c7d3d0f20f50927e.
  A re-run of the emitter was verified byte-identical (diff -r empty).
- Instrument: scripts/validate-gpu-subgroup-reduce-wgsl.mjs (it gained
  an optional transcript-title argument this slice, default unchanged),
  Node + Playwright, no POSIX shell file: per file createShaderModule +
  getCompilationInfo + createComputePipeline under a validation error
  scope (entry point `main`), in TWO limit regimes.

## Result (compile-log.txt is the transcript, verbatim)

    run-at: 2026-10-24T16:44:35.431Z (self-dated, fresh process)
    toolchain: HeadlessChrome/155.0.0.0 (Google Chrome 155 Dawn/Tint),
      adapter-info {"vendor":"apple","architecture":"metal-3"}
    summary DEFAULT limits: 18 files, 12 validate clean, 6 do not
    summary RAISED limits: 18 files, 18 validate clean, 0 do not

- The refusal class is GONE: 0 occurrences of "cannot be represented"
  in the post-fix transcript, and compile-info: ok for all 18 files in
  BOTH regimes (36 front-end verdicts).
- The 6 default-limit non-clean verdicts are the KNOWN W >= 512 class
  and nothing else: GPUValidationError "Entry-point uses
  workgroup_size(512|1024, 1, 1) that exceeds the maximum allowed (256,
  256, 64)" -- a device-limit check, not the WGSL front end; clean
  under the adapter's raised limits. The W >= 512 needs requiredLimits
  operational note is unchanged.
- Pre-fix judgment on this arm's own corpus (same instrument, same
  toolchain, minutes earlier -- full record in
  docs/evidence/gpu/wgsl-baseline-validate-chrome-20261025/): DEFAULT
  4 clean / 14 do not, RAISED 6 clean / 12 do not; the 12 are the
  whole :max/:min row, "value -inf cannot be represented as 'f32'" at
  error@8:37 -- the same class the :subgroup-reduce arm's old spelling
  drew. The fix is what changed between the two verdicts.

## State honesty (the three states)

- IMPLEMENTED (NEW this slice): the fix rule's emission in the baseline
  :reduce WGSL arm (wgsl-fill in
  src/kotoba/compiler/accelerator.cljk, both readings), the n=0
  contract (n >= 1 precondition), the spelling re-founding
  (test/kotoba/compiler/accelerator_test.cljk:
  every-arm-shares-one-operator-meaning now pins ONE meaning under TWO
  mechanisms with BOTH WGSL arms on the fill, and the NEW mechanical
  guard wgsl-baseline-arm-holds-no-infinite-value-in-any-position is
  the tripwire against the refused spelling's return).
- ACCEPTED DESIGN ONLY, unchanged: the fix rule as decided
  (docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/) is the
  authority this slice implements; nothing in the decision is
  re-litigated.
- CLOSED: the named "STILL DEFECTIVE" item of the 2026-10-25
  :subgroup-reduce fix record. No WGSL arm holds an infinite value in
  any position now.
- TOOLCHAIN FACTS (new, self-dated in compile-log.txt): the 36 + 36
  verdicts of the two judgments.
- UNMEASURED, unchanged and still the operative claim: NO kernel
  executed this arm on any GPU, no timing exists, no speed claim of any
  kind, no :measured? flag moves, no :shapes value and no workgroup row
  (ADR-0355/0358) moves. No WebGPU execution path exists in this
  repository. Shader validation is not a measurement.

## Verification (runner output, not paraphrase)

- Scoped GPU gate (scratch runner gpu_scoped_gate.cljk, not in the
  repo; classpath route 2, `AMU_KBB_TEST_CLASSPATH` -- route 1
  `kbb -Spath -M:test` fails at the tree root since the merge 7b8f6488
  retired deps.edn), scoped-gate-touched-namespaces.txt:

      Ran 106 tests containing 11002 assertions.
      0 failures, 0 errors.

  (106 tests / 11002 assertions vs the pre-fix 105 / 10966: +1 test
  and +36 assertions, the new baseline-arm guard's 6 widths x
  3 operators x 2 assertions.)
- Full suite (run-tests.cljk, same classpath route): RED AT BASE,
  outside this diff, at namespace load on `kotoba.form` ("Could not
  find namespace: kotoba.form"; the W3 port path documented red at
  base in ADR 0362 and named in every prior tick record), re-verified
  this tick, zero tests run. Full text: full-gate-kbb.txt. No green
  full suite is claimed.

## What moved in the repository

- src/kotoba/compiler/accelerator.cljk: wgsl-identity REPLACED by
  wgsl-fill (both readings), the :reduce padded-lane load lines change,
  the identity comment block gains the WGSL exception and the fix
  rule's dated prose.
- src/kotoba/compiler/accelerator_subgroup_reduce.cljk: the two prose
  sites naming the baseline arm's defect gain dated FIXED brackets.
- test/kotoba/compiler/accelerator_test.cljk: every-arm-shares-one-
  operator-meaning re-founded (both WGSL arms on the fill) + the NEW
  mechanical guard wgsl-baseline-arm-holds-no-infinite-value-in-any-position.
- scripts/emit-gpu-reduce-wgsl.cljk (NEW): the baseline row's emit
  script (accelerator/lower :wgsl-v1 :baseline).
- scripts/validate-gpu-subgroup-reduce-wgsl.mjs: optional transcript-
  title argument (default text unchanged).
- docs/evidence/gpu-baseline-reduce-wgsl-20261025/ (NEW): the pre-fix
  corpus (18 files).
- docs/evidence/gpu-baseline-reduce-wgsl-fix-20261025/ (NEW): the
  post-fix corpus (18 files).
- docs/evidence/gpu/wgsl-baseline-validate-chrome-20261025/ (NEW):
  the pre-fix judgment (README, compile-log.txt).
- docs/evidence/gpu/wgsl-baseline-fix-validate-chrome-20261025/ (NEW):
  this README, compile-log.txt (the post-fix validation transcript),
  scoped-gate-touched-namespaces.txt, full-gate-kbb.txt. No POSIX .sh
  file anywhere in the diff (the check-workflows rule).
- UNTOUCHED: every pre-fix judgment record of the :subgroup-reduce arm,
  every :measured? flag, every workgroup row.
