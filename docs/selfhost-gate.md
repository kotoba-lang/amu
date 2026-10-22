# Amu selfhost gate (the only CDCI gate for this line)

Tracking: Linear JUN-282 (child of JUN-199), JUN-202. Status: specification; the native controller is not built yet.

## Scope
Per AGENTS.md / docs/selfhost-priority.md (2026-10-22), CDCI is limited to Amu selfhost and Kotoba native as
loaderless `x86_64-linux-static` ELF. This document defines the **Amu selfhost gate only**. The Kotoba native gate,
the old `fleet-ci-gates` / `kotoba-authoring` labels and the JUN-242 `scripts/gate` (nbb/Node host driver, on
`claude/selfhost-ci-gate`) are not part of it. The JUN-242 gate stays on its branch as a historical measurement.

## The gate is an Amu-produced loaderless ELF
The controller and the checks below are Kotoba programs built by Amu selfhost. Its build and execution closure
contains no CLJK/CLJC/CLJS, NBB/KBB, Clojure/JVM/Java/GraalVM, Node, or C compiler/loader/runtime, and no
Python/shell orchestration. Until that controller exists, nothing here counts as a pass.

## Checks (all required; fail closed; an unmeasured check is a FAIL)
1. **Pins** — record source CID, deps-lock digest (`sha256(deps.edn)`), source-path, commit of base and head.
2. **Generations** — selfhost builds g0 (pinned seed), g1, g2, g3 from the head source; g1 = g2 = g3 byte-identical.
   Record each artifact SHA-256.
3. **Closure** — forbidden-process trace over build and execution is empty (node, nbb, kbb, java, clojure,
   graalvm, cc/clang/gcc, loader, python, sh as orchestrator). Record the trace.
4. **Corpus** — the full original public-API, positive, refusal, lock-failure, fuel and authority corpus runs on the
   native artifact. No case removed or shrunk versus base; counts and per-case results recorded.
5. **Execution** — the artifact is actually executed as `x86_64-linux-static` ELF; exit codes and outputs recorded.
6. **Ratchet (diagnostic, not a pass)** — host-coupling markers (`rc-no-arm`, `kotoba-nil`) per changed source file
   must not increase versus base. Carried over from JUN-242 G0; the 2026-10-22 run found +13 files.

## Verdict
PASS only if 1–5 pass and 6 does not regress. Exit 0 = PASS, 1 = FAIL, 2 = could not complete (FAIL).
Source admission, a unit test or a subset fixed point never substitutes for a native, executed result.

## Out of scope
Kotoba native gate; Wasm/browser matrices (generated targets run in the declared host); hosted comparisons.

## Measured blocker (2026-10-22, JUN-282)
The controller must open files, hash, spawn and trace processes. The only freestanding x86_64-linux route the seed
emits (profile 0, standalone scalar ELF) rejects handles/runtime operations and cannot express a runner
(seed/X86_64-LINUX-ABI; docs/native-seed-c-free-runner-expressiveness-20261019.md). The runtime profile (kx64-v1)
runs under the trusted C loader, which the contract excludes from the required path. So only the pure verdict core
(`gate/selfhost_gate_core.kotoba`) can be built now; the measuring side waits on a loaderless runner with file and
process capabilities (JUN-29, amu#1443 line). Until then nothing here is a pass.
