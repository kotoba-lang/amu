# ADR 0227: parallel phi-copy evidence follows the pinned closure

- Status: accepted
- Date: 2026-08-11
- Machine-readable companion:
  [`0227-pinned-parallel-phi-copy-evidence.edn`](0227-pinned-parallel-phi-copy-evidence.edn)

## Context

Value-position scalar control introduced versioned GMIR/MIR phi values. The
first safe optimization removed frame transport only for single-phi joins;
multi-phi joins retained one slot per value because sequential moves can
destroy sources in a register cycle.

MIR now owns deterministic parallel-copy scheduling. Evidence in Amu is valid
only when its direct native pin and transitive codegen/MIR lock entries name the
matching merged closure. Structural byte production alone is insufficient:
both selected branches must execute as real processes on both native ISAs.

## Decision

Amu pins `kotoba-native` `5e76bd75f22b2045692f38b83b09a5a922275cf6`.
The generated lock binds `kotoba-codegen`
`58b923db72d3a1c984155eb93ebdcffbbe8885f2` and `kotoba-mir`
`30f9afacfc1cbbbb41956f893a9eca0a16934c1b`.

The shared ISA gate constructs one canonical dual-phi GMIR program. It asserts
frame slot count zero, two selected moves, and no spill load/store, then invokes
the final bytes through the production test loader with both branch arguments.
The expected results are three for the then edge and seven for the else edge.
On macOS, both AArch64 and x86-64 loaders are mandatory rather than optional.

Cycle correctness is owned and exhaustively tested by MIR over all 256 source
mappings of each four-register target profile. Amu does not claim that the
current frontend naturally emits every cyclic mapping; its runtime gate proves
the acyclic multi-phi consumer path, while existing native spill encoding tests
cover the temporary operations.

## Consequences

The pinned compiler closure now has measured multi-phi execution without the
former per-phi frame transport. This is a control-flow transport improvement,
not evidence of Rust-wide performance parity, aggregate-value migration, or a
global optimizing register allocator.
