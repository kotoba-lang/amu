# Combined i64 AOT and AIUEOS native adoption

`source.json` binds source `0815e25a`, the complete31-module unity, native
ARM packed root and public Linux x86 compiler candidate. The source retains
all18 core modules, current call-site/base-length memory hardening, main's
PR1548 i64 AOT frontend and the AIUEOS image/EFI route.

The admitted i64 AOT main root builds native ARM F1=F2. The unmodified
`arm-bootstrap.json` records core reproduction and unchanged24 runtime
cases; `arm-cross-candidate.json` records native cross generation of the
public x86 compiler and all three CDCI executables. The controller and both
gate hashes remain identical to existing pins. `i64-arm.json` records the
native ordered122-case AOT verdict and corrupted-observation refusal.
The image/EFI receipts bind the same complete source and two generations.
The canonical memory admission corpus still passes all27 cases.

These local receipts do not claim x86 execution on ARM. Current execution
acceptance is the terminal exact-head [PR1547 native checks](https://github.com/kotoba-lang/amu/pull/1547/checks)
and merged-main run: independent canonical Pw, native x86 F1=F2=F3 equal to
the public image, both mandatory native CDCI roles, public alias/source-lock
readback, AOT and AIUEOS diagnostics, memory controls and browser Wasm.
The piped memory diagnostics explicitly use Bash's pipefail behavior.

Earlier full30 directories retain their historical source bindings. No full
AIUEOS kernel graph, ISR/live runtime, native media, desktop or input is
qualified by the bounded entry/packaging probes in this PR.
