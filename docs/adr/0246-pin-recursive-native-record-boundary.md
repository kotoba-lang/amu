# ADR 0246: Pin the recursive native record boundary

Status: accepted

Amu pins `kotoba-native` at
`8b1e22c9fb645e38ce16c3f2e24fc10468eba14d`, advancing the portable aggregate
contract to ABI v6. Inline nested records lower to recursively composed,
context-owned one-word pair-chain handles on x86-64 and AArch64. Inline schema
depth is bounded at 32 and the existing execution arena remains bounded at
4,096 pair cells.

The matching verifier pin
`e2c0e3f49bd7828cd187aee6a90ba5e6f2474149` independently re-derives that
depth bound and re-emits a sealed nested-record artifact.

The JDK-free conformance now compiles a source-level nested record, extracts
the native export independently, and executes it with the real W^X loader. The
program constructs inner and outer records, performs chained projections, and
must return `15`. The same source is compiled and verified for the Windows
native profile; Windows hosts additionally execute it through the Windows
loader.

Aggregate variant payloads, indirect calls, varargs, and external linkage
remain explicit fail-closed boundaries. No legacy production fallback is
restored by this admission.
