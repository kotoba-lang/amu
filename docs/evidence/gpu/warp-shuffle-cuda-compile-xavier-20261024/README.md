# JUN-57: the :warp-shuffle-reduce CUDA arm's never-compiled state CLOSES on a real toolchain (2026-10-24)

ONE implementation slice (backlog item 4, JUN-57): the row the previous
record named in its HONEST LEFT -- "The :warp-shuffle-reduce CUDA arm has
still never been compiled ... compiling it on xavier is its own row" --
is that row, taken now. The arm's emitted sources compile on the fleet's
only CUDA host with the real toolchain. NO measurement ran: this is a
compile, and UNMEASURED is unchanged everywhere.

## What compiled (the emitter's bytes, never hand-written)

- Corpus: docs/evidence/gpu-warp-shuffle-reduce-cuda-20261024/shaders/ --
  18 files, the whole admitted row (W in {32,64,128,256,512,1024} x
  :sum/:max/:min), produced by
  scripts/emit-gpu-warp-shuffle-reduce-cuda.cljk (new this tick) through
  the public `accelerator/lower` route -- the same emitter the tests
  drive, never hand-written sources.
- WORKGROUP-SIZE-PARAMETRIC, recorded not assumed: the arm never bakes W
  (W enters only as the admission precondition W >= 32), so the corpus
  holds exactly 3 distinct emissions, 6 files each -- sha256 census:
  35da549a... x 6 (:sum), cd4e1029... x 6 (:max), e47b3820... x 6
  (:min). The 18-file shape mirrors the :subgroup-reduce corpus so the
  two compile records compare cell for cell.
- Determinism, verified live this tick: the emit script ran twice, the
  two sha256 listings of the 18 files diff EMPTY.
- Integrity: the 18 files' sha256 computed locally and the 18 files
  received on xavier are IDENTICAL (diff of the two listings empty). The
  received-side listing is compile-log.txt lines "=== sha256 of the
  received .cu files".

## The toolchain (identity verbatim, compile-log.txt)

Host: xavier (Tailscale), NVIDIA Jetson AGX Xavier, L4T R35.4.1,
Linux 5.10.120-tegra aarch64. Compiler:

    nvcc: NVIDIA (R) Cuda compiler driver
    Copyright (c) 2005-2022 NVIDIA Corporation
    Built on Sun_Oct_23_22:16:07_PDT_2022
    Cuda compilation tools, release 11.4, V11.4.315
    Build cuda_11.4.r11.4/compiler.31964100_0

Command per file (18 files): nvcc -arch=sm_72 -cubin <f> -o <f>.cubin
and nvcc -arch=sm_72 -ptx <f> -o <f>.ptx, run
2026-10-24T23:39:05+0900 (DATE-UTC 2026-10-24T14:39:05Z).

## Result (compile-log.txt is the transcript, verbatim)

- 18/18 OK-cubin, 18/18 OK-ptx, 0 FAIL. 36/36 diagnostics: NONE -- nvcc
  printed nothing (no warnings, no errors) for every file.
- Artifact census: 18 .cubin, 18 .ptx. Every .cubin opens with the ELF
  magic 7f454c46 (od census at the end of compile-log.txt, 18/18).
- Every .ptx opens `.target sm_72` and carries the extern-C entry
  `.visible .entry reduce_sum(` / reduce_max( / reduce_min( -- the
  kernel names the KIR's :kernel/name and the CUDA family's own linkage.

## State honesty (the three states)

- IMPLEMENTED (code + test): unchanged -- the emission, its text
  contracts and their tests (accelerator-test's
  warp-shuffle-reduce-variant-lowers-deterministically and
  kernel-variants-refuse-where-not-applicable rows) predate this tick and
  are untouched behaviorally. NEW this tick: the emit script itself
  (scripts/emit-gpu-warp-shuffle-reduce-cuda.cljk), which is evidence
  tooling, not a compiler change.
- NEW HARDWARE FACT, measured 2026-10-24: the arm's emitted row COMPILES
  CLEAN on the real nvcc 11.4 (V11.4.315) on xavier. "Compiled" now
  means this toolchain and no other; this host (the M1 Max) still has no
  nvcc, and the WGSL arm's UNCOMPILED is untouched (no validator here).
- UNMEASURED, unchanged and still the operative claim: NO kernel
  executed this arm on any GPU, no timing exists, no speed claim of any
  kind, no :measured? flag moves, no :shapes value and no workgroup row
  (ADR-0355/0358) moves. The CUDA emitter has no execution path in this
  repository (wire 42 runs Vulkan only). A compile is not a measurement.
- PROPOSED: nothing new.

## What moved in the repository

- src/kotoba/compiler/accelerator.cljk: the kernel-variants docstring's
  :warp-shuffle-reduce paragraph and the emit-cuda-shuffle-reduce
  comment gain the dated COMPILED bracket beside the UNMEASURED claims
  as written. PROSE/COMMENT ONLY.
- docs/adr/0356-gpu-kernel-variant-selection.md: the `:warp-shuffle-reduce`
  | nvidia rows-table row gains the dated bracket in its state cell.
  DOCS ONLY.
- docs/adr/0361-gpu-nvidia-subgroup-reduce.md: the CUDA-ladder
  amendment's UNCOMPILED state line gains the dated bracket, scoped to
  the :warp-shuffle-reduce rung's arm. DOCS ONLY.
- scripts/emit-gpu-warp-shuffle-reduce-cuda.cljk + the corpus under
  docs/evidence/gpu-warp-shuffle-reduce-cuda-20261024/ + this record.
  NEW FILES.
- Historical records are NOT rewritten (the previous record's HONEST
  LEFT "has still never been compiled" states that record's state at its
  own commit; every record's own words stand).

## Gate (real runs, this host, route-2 classpath -- the $(kbb -Spath
-M:test) subshell is broken at this branch's HEAD, the CHANNEL NOTE in
docs/evidence/gpu/simdgroup-reduce-m1max-shape2-w32-measure-20261024.txt
names it)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> TOTAL: 2003 assertions passed, 0 failed (no corpus pair added).
2. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> driver self-test: 17 assertions passed, 0 failed.
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk):
   -> Ran 104 tests containing 10948 assertions. 0 failures, 0 errors.
      scoped: 104 tests, 10948 passed, 0 failed, 0 errors
      (previous tick: 104 tests / 10948 assertions -- counts UNCHANGED,
      this diff is prose/comment/docs plus evidence tooling, and the
      touched namespace accelerator (docstring + emitter comment) loads
      green).
4. Full suite (run-tests.cljk, same classpath): RED AT BASE, outside
   this diff, at namespace load on `kotoba.form` ("Error: Could not find
   namespace: kotoba.form"; the W3 port path, ADR 0362, the same red
   every recent record names), re-verified live this tick. No green full
   suite is claimed.

## HONEST LEFT (the real remainder after this row)

- Both CUDA arms are now COMPILED as to nvcc 11.4 on xavier, and both
  stay UNEXECUTED and UNMEASURED on every vendor: no CUDA execution path
  exists in this repository; an execution/measurement row needs the ADR
  0371 provider track (or a native-CUDA harness of the ADR-0373 kind)
  and is its own decision + row.
- The WGSL arm stays UNCOMPILED on this host (no validator): every
  vendor's WGSL arm is in the same regime.
- The nine :simdgroup-reduce cross-day rows stay 2026-10-25+ rows;
  :arm/:unknown workgroup rows stay provisional (:measured? false).

PUSH STATE: NOT pushed. Blocker-first rule in force -- the hermes/-head
open PRs are re-checked at commit time; this tick they are #1553
(hermes/jun31-pe-shim-align) and #1561
(hermes/jun31-seed-boot-ops-20261024), so this commit is kept locally on
bot/amu-gpu-chain and pushes on the first tick after every hermes/
blocker PR clears. Chain PR #1455 stays the one open chain PR; no second
chain PR opened.
