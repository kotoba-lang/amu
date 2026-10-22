# Native compiler bootstrap — 2026-10-22

The measured `seed/MANIFEST` lineage now executes as a standalone AArch64
Linux experiment, without a C/JVM/Node compiler or C loader in those native
executions. Public entrypoints still refuse with exit 69: this experiment
does not yet qualify the complete product or build closure.

## Actual native results

- The native experiment recompiled all sixteen adopted core modules to the
  recorded M105 fixed point, raw code SHA-256
  `b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`.
- A subsequent core source revision migrated filesystem IO to mandatory FS2
  frames and acknowledgements, including the project linker's reused binary
  output requests. Its G1 and G2 containers are byte-identical:
  `1f31d3a94e2da099df3b4a4a979ed27e04cd8a32a1b0f0ad929849e65eb551f8`.
  The current native FS2 runtime successfully ran check and byte-file compile
  through that compiler. This revision predates the later byte-read contract
  and document-helper corrections; it is not the current successor's gate.
- All nineteen preserved Embench port sources were freshly compiled by that
  native-generated FS2 compiler. All nineteen resulting native programs ran
  their complete `bench-verify(1)` workload and returned `1`. Source, compiler,
  container and executable identities are in
  [`evidence/native-bootstrap-20261022/`](evidence/native-bootstrap-20261022/).
  This is correctness evidence, not a new timing score or quiet-host claim.
- The FS2 integration fixture round-tripped binary NUL/non-UTF8 bytes and
  historical separator words, and text containing NUL. Missing or wrong
  string/byte acknowledgement markers trapped with exit 70 as required.
  Native C3 exposed an incorrect raw-read request: kind 8 admits write/append,
  while kind 9 admits string-to-bytes read/range. The seed now uses kind 9;
  the owning provider guard was retained.
- A native command-entry experiment returned process exit 1 for an unsupported
  target and for an unknown source symbol, and 0 for successful check. It no
  longer prints a trailing integer status. This entry mode is not yet admitted
  by the public static profile/planner.

## Current successor and remaining admission

[`seed/compiler-core-successor.json`](../seed/compiler-core-successor.json)
pins the evolving source separately from the historical measured/adopted
lineage. It adds byte-document access needed by the canonical native
packager. Generated helper syntax is checked by the actual native compiler;
full document binary digest/order and reader qualification remain open.
Unsupported binary document digest/order is refused, not approximated by
hashing printed text. The driver's generated-source diagnostics must retain
the compile error instead of requesting a filesystem range past the original
source file.

The initial ELF byte materialization still uses a disposable Python
calculator of the canonical native IR builders. That calculator is not the
accepted compiler, packager, controller or qualification verifier. Complete
native regeneration must remove it from the required closure. The public
packager's seal/profile checks are intact; the internal CPU builder probe
does not admit an artifact or grant authority.

The historical core emits the `aarch64-macos` raw AAPCS64 payload. Running it
under the experimental Linux runtime is not Linux-static target admission.
Native static value/profile bounds, sealed artifact verification, complete
compiler/CLI/packager/controller generations, locked project input and dotted
ID/legacy alias imports, default Kototama output and public CLI refusal cases
remain required. The nineteen-workload result must be reproduced with the
final admitted toolchain before main merge. No main merge, Actions setting,
protection setting, service or unrelated WIP has changed.
