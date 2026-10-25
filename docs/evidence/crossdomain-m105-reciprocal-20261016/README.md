# M105 reciprocal division candidate

Status: **SELFHOST FIXED POINT, CODEGEN, AND EXACT RUNTIME CHECKS; NOT TIMED**.

This record covers one narrow AArch64 compiler intervention. Starting from the
adopted M105 native selfhost image, the modified seed compiler rebuilt itself
through G1, G2, and G3. All three KSEED containers and extracted native images
were byte-identical. No JVM, Node, or Graal compiler fallback was used.

The patched compiler replaces signed division by the positive constant
`1000003` with a hoisted reciprocal and `smulh` on the collections hot path.
The four unrolled loop sites are at `0x330`, `0x360`, `0x390`, and `0x3c0`;
the scalar fast path is at `0x408`. A guarded fallback still contains `sdiv`
at `0x460`. The strings fixture remains byte-identical to the M105 baseline
and retains `sdiv` at `0x154` and `0x228`; this candidate does not improve its
code generation.

The native loader executed both fixtures for all six published inputs with an
initial fuel of 16,777,216. Strings match the suite's result and fuel vectors.
For collections, patched and unmodified M105 outputs match each other in both
result and fuel for all six inputs, and the results match the known answers.
The prior collections fuel vector was stale: it was recorded on 2026-08-30,
before ADR 0353 added constructor debits to the shared fuel budget. Current
M105 and patched fuel is `[198, 200, 202, 212, 230, 232]`; the suite manifest
was refreshed to those executed values. A source-level KIR oracle was not rerun
in this attempt, so the record does not claim an independent oracle replay.

This is exactness and generated-code evidence only. The host was not quiet, and
no timing or performance improvement is claimed. See `reciprocal-codegen.json`
for source and artifact hashes, and the two runtime verification transcripts.
The arithmetic formula check is reproducible with `verify-reciprocal.py`; its
captured result is in `reciprocal-arithmetic-verification.txt`.
Pre-patch artifacts are in
`../crossdomain-m105-baseline-codegen-20261016/`.
