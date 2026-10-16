# M105 baseline code generation: cross-domain arithmetic

This is a code-generation-only record produced with the adopted native M105 selfhost compiler. It compiles the existing `kernel_strings` and `kernel_collections` fixtures for `aarch64-macos`, extracts native bytes, and disassembles the extracted bytes. It does not run the fixtures, verify their known answers or fuel, or measure performance.

The native output contains the divisor 1000003 as a materialized register operand and retains `sdiv` on the relevant loop paths. In the collections loop, four unrolled iterations each contain `sdiv` (offsets 0x320, 0x340, 0x360, 0x380); the divisor is loaded in the preheader at 0x2f8/0x2fc. The strings disassembly contains loop-path `sdiv` at offsets 0x154 and 0x228. This confirms the reciprocal-lowering candidate reaches current M105 code, while static helper copies are not evidence by themselves.

The exact bootstrap, loader source, fixture sources, KEXE containers, extracted native code, and full `otool -tvV` listings are pinned in `baseline-codegen.json`. The patched selfhost fixed point, generated-code inspection, and exact runtime checks are now recorded in [`crossdomain-m105-reciprocal-20261016`](../crossdomain-m105-reciprocal-20261016/). Paired host-qualified timing remains outstanding.
