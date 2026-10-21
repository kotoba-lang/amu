# T2 fast-copy remainder register reuse experiment

Status: **REJECTED; no generated-code effect on the tested workload set.**

## Candidate

The candidate changed `t2-e-msub` to reuse `x17` in a fast copy only when the
T2 remainder-reuse flag is set, neither fused operand is spilled, and the last
machine word is exactly the expected `sdiv` of the quotient operand by
`x17`. This was intended to prove that the divisor remained live in `x17`
while excluding reciprocal lowering. The source patch is retained in
`candidate.patch`.

The candidate selfhost compiler reached a G1=G2=G3 fixed point at
`d9931fc25424b27b944a5421d6970ccc5befc411d0a32dbec23aab0b19d6a3dc` from the
adopted M105 bootstrap. The baseline was built from repository commit
`686309d9a5ef1f4a6f1e575362096794a1841a0f`, with the candidate edit absent;
its G1=G2=G3 image is
`b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`.
Both chains used the pinned native C loader and no JVM, Node, or Graal
fallback.

## Results

Baseline and candidate native code were byte-identical for all 17 existing
`bench/runtime-comparison/kernel*.kotoba` fixtures and all 19 ports in
`bench/embench/ports/`. Full source, KSEED, native-code hashes, sizes, and
entry offsets are in `runtime-codegen-sweep.json` and
`embench-codegen-sweep.json`. No timing was run because identical machine code
cannot test the intended speed hypothesis.

The candidate G3 image compiled `kernel_strings` and `kernel_collections`.
The extracted binaries were also byte-identical to the baseline compiler's
outputs. Native execution of the candidate matched all 12 known result and
fuel pairs with initial fuel `16777216`:

| Fixture | Results for inputs `[0, 1, 2, 199, 200, 201]` | Fuel consumed |
|---|---|---|
| `kernel_strings` | `[95351, 374831, 488388, 147903, 799811, 429739]` | `[75, 84, 93, 138, 75, 84]` |
| `kernel_collections` | `[583979, 314424, 542513, 169665, 416979, 4871]` | `[198, 200, 202, 212, 230, 232]` |

The fixture binaries have SHA-256
`709ea8c6aaec9aa0d0f57d6955fe1cf3e872a62d8bb244be7594bc23d57fccf2`
(`kernel_strings`) and
`b200038d7a48c86e89f08812475acc87555f035ca650fba34d07ca4a56ee828e`
(`kernel_collections`) for both compiler images.

The candidate was reverted. This experiment does not explain or improve the
M104 translated-port C comparison. The next compiler hypothesis should target
a loop whose current generated code demonstrably retains repeated work, such
as the branchy constant-division path already identified in the strings scan;
it must first produce a code difference before spending time on timing.
