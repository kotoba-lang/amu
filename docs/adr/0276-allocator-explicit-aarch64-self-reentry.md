# ADR 0276: Allocator-explicit AArch64 self reentry

## Decision

Pin kotoba-mir `be01f15d`, kotoba-codegen `54a3f3b1`, and kotoba-native
`821fa0f8`. Eligible AArch64 self-tail edges use the allocator's exact physical
parameter homes and its existing simultaneous-copy scheduler. Native code
branches to an explicit reentry boundary after one-time argument
materialization. The encoder does not infer that boundary from adjacent move
instructions.

Any self-tail site with a backed or incomplete source retains the ordinary
public-ABI tail path. Non-self tail calls and x86-64 are unchanged. Each direct
recur executes the same sealed fuel prefix before branching, and the function
frame is still created once and restored once.

## Rejected shortcut

An encoder-local move-pattern prototype was rejected. A three-argument string
index helper and a smaller two-argument count-down both had one next argument
already in its ABI register. The site matcher declined the partial move group
while a function-wide label still skipped entry materialization, leaving a
stale loop parameter and exhausting fuel. The landed contract instead proves
every optimized site from virtual arguments through physical homes.

## Evidence boundary

MIR, MC, and native validators reject misplaced reentry markers, unestablished
or duplicate homes, non-terminal recur operations, and adversarial internal
label collisions. Swap cycles use the existing frame-backed parallel-copy
temporary. The full Amu suite executes both available macOS ISA loaders and
includes the string-index, count-down, loop-call, and fuel-boundary regressions.

The loop-call hot edge avoids re-executing two entry-home moves; its direct
edge performs two home updates instead of two ABI staging moves followed by
two entry-home moves. This is structural instruction evidence. It is not a
qualified wall-clock improvement and does not establish parity or superiority
against Rust, LLVM, or any broader language set. A sealed seven-run competitive
measurement was rejected by the host-load gate (`load1` 7.52734375 versus the
7.5 limit); its timing samples remain diagnostic only.
