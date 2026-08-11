# ADR 0239: pin bounded kernel memory through machine IR

## Context

Amu's kernel targets and real-loader table already execute bounded u8/u32
memory operations. Their native implementation previously used the recursive
legacy emitters and downstream tests matched allocator-specific byte sequences.

## Decision

Pin `kotoba-native` at `7b708fcabb61d763c4e1d3ad8a6998b188582c76`
and regenerate `deps-lock.edn`. This closure carries bounded u8/u32 loads and
stores and subregion derivation through GMIR, MIR, selected MC, and final target
layout.

Downstream encoding tests match the closed memory-instruction shape and private
address scratch register while permitting the allocator to choose the value
register. Runtime behavior remains qualified by the real-loader table on both
AArch64 and x86-64.

## Consequences

Bounded kernel memory is no longer a production legacy-emitter gap. Runtime
handles, capabilities, strings, privileged operations, and escaping aggregates
remain explicit migration families.
