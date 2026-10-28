# JUN-57: the :subgroup-reduce CUDA arm's UNCOMPILED state CLOSES on a real toolchain (2026-10-24)

ONE implementation slice (backlog item 4, JUN-57): the arm's named
UNCOMPILED state -- "UNCOMPILED and UNMEASURED: no nvcc exists on the
testing host" -- is closed as to one REAL toolchain, by compiling the
emitter's own bytes on the fleet's only CUDA host. NO measurement ran:
this is a compile, and UNMEASURED is unchanged everywhere.

## What compiled (the emitter's bytes, never hand-written)

- Corpus: docs/evidence/gpu-subgroup-reduce-cuda-20261023/shaders/ --
  18 files, the whole admitted row (W in {32,64,128,256,512,1024} x
  :sum/:max/:min), produced by scripts/emit-gpu-subgroup-reduce-cuda.cljk.
- Determinism, re-verified live this tick: the script was re-run at this
  tree and git status on the corpus directory is EMPTY -- the re-emit is
  byte-identical to the committed bytes.
- Integrity: the 18 files' sha256 computed locally and the 18 files
  received on xavier are IDENTICAL line for line (diff empty). The
  received-side listing is compile-log.txt lines "=== sha256 of the
  received .cu files"; examples:
  4b8e0e9b2ecb6b921a9c7767bef4fbd499df78130777de6cc0366a62f385fcdb
  subgroup-reduce-w1024-max.emitted.cu (same on both sides).

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
2026-10-24T23:18:07+0900.

## Result (compile-log.txt is the transcript, verbatim)

- 18/18 OK-cubin, 18/18 OK-ptx. Zero diagnostics -- nvcc printed nothing
  between the markers (no warnings, no errors).
- Artifact census: 18 .cubin, 18 .ptx. Every .cubin opens with the ELF
  magic (od census at the end of compile-log.txt).
- Every .ptx opens `.target sm_72` and carries the extern-C entry
  `.visible .entry reduce_sum(` / reduce_max( / reduce_min( -- the
  kernel names the KIR's :kernel/name and the CUDA family's own linkage.

## State honesty (the three states)

- IMPLEMENTED (code + test): unchanged -- the emission, its text
  contracts and their tests landed 2026-10-23 and are untouched
  behaviorally.
- NEW HARDWARE FACT, measured 2026-10-24: the arm's emitted row COMPILES
  CLEAN on the real nvcc 11.4 (V11.4.315) on xavier. "Compiled" now
  means this toolchain and no other; this host (the M1 Max) still has no
  nvcc, and the WGSL arm's UNCOMPILED is untouched (no validator here).
- UNMEASURED, unchanged and still the operative claim: NO kernel
  executed this arm on any GPU, no timing exists, no speed claim of any
  kind, no :measured? flag moves, no :shapes value and no workgroup row
  (ADR-0355/0358) moves. The CUDA emitter has no execution path in this
  repository (wire 42 runs Vulkan only; the loader's routes are gone,
  ADR-0355's honest state). A compile is not a measurement.
- PROPOSED: nothing new.

## What moved in the repository

- src/kotoba/compiler/accelerator_subgroup_reduce.cljk: the ns
  docstring's CUDA-arm paragraph gains the dated COMPILED bracket (the
  UNCOMPILED claim kept as written, with its scope named); the WGSL
  paragraph's "the CUDA arm is in the same regime -- no nvcc"
  parenthetical is corrected. PROSE ONLY.
- test/kotoba/compiler/accelerator_subgroup_reduce_test.cljk: the CUDA
  arm section comment gains the same dated bracket. COMMENT ONLY.
- scripts/emit-gpu-subgroup-reduce-cuda.cljk: header comment carries the
  same bracket. COMMENT ONLY.
- docs/adr/0356-gpu-kernel-variant-selection.md (two CUDA-arm state
  lines) and docs/adr/0361-gpu-nvidia-subgroup-reduce.md (one): dated
  UNCOMPILED CLOSED brackets beside the claims as written. DOCS ONLY.
- Historical records are NOT rewritten (the 2026-10-23 NOTES.md "NONE --
  UNCOMPILED" states that slice's state at its own commit; every
  record's own words stand).

## Gate (real runs, this host, route-2 classpath -- the `$(kbb -Spath
-M:test)` subshell is broken at this branch's HEAD, the CHANNEL NOTE in
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
      this diff is prose/comment only, and the touched namespace
      accelerator-subgroup-reduce-test loads green).
   A first run of this gate failed at load ("Cuda is not ISeqable"): the
   patch wire's escape-drift defect stripped the backslashes from the
   two quotes around the nvcc version string inside the ns docstring,
   closing the string early -- named, not hidden; fixed by removing the
   quotes (the identity is quoted verbatim in this record and in
   compile-log.txt), and the docstring's closing quote position was
   then verified programmatically before the green run above.
4. Full suite (run-tests.cljk, same classpath): RED AT BASE, outside
   this diff, at namespace load on `kotoba.form` ("Error: Could not find
   namespace: kotoba.form"; the W3 port path, ADR 0362, the same red
   every recent record names), re-verified live this tick. No green full
   suite is claimed.

## HONEST LEFT (the real remainder after this row)

- The :warp-shuffle-reduce CUDA arm has still never been compiled (its
  prose claims no UNCOMPILED state, so nothing is stale): compiling it
  on xavier is its own row.
- The CUDA arms stay UNEXECUTED and UNMEASURED on every vendor: no
  CUDA execution path exists in this repository; an execution/measurement
  row needs the ADR 0371 provider track (or a native-CUDA harness of the
  ADR-0373 kind) and is its own decision + row.
- The WGSL arm stays UNCOMPILED on this host (no validator).
- The nine :simdgroup-reduce cross-day rows stay 2026-10-25+ rows;
  :arm/:unknown workgroup rows stay provisional (:measured? false).

PUSH STATE: NOT pushed. Blocker-first rule in force -- the hermes/-head
open PRs are re-checked at commit time; while any stands, this commit is
kept locally on bot/amu-gpu-chain and pushes on the first tick after
every hermes/ blocker PR clears. Chain PR #1455 stays the one open chain
PR; no second chain PR opened.
