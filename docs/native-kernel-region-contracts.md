# Closed kernel region contracts

This is the full37 engineering candidate. Native x86/controller admission
and public compiler pin adoption remain required before release.

The locked linker retains every function and SIR instruction. Namespace
exports are link interfaces, never additional memory-authority roots. Root
interrupt arguments remain hardware scalars. Literal addresses, pointer
arithmetic, loaded pointers, arbitrary call results and branch results do
not become regions.

A private helper's fixed extent is valid only after every external call
supplies a rooted region of that same extent. Identity recursion can carry
an established contract; an unseeded recursive function cannot establish
one. Retained diagnostics without callers declare explicit base/length
pairs and narrow them with `kernel-subregion`.

Lowering can reuse a local slot in disjoint scopes. For the closed project,
the checker selects the last assignment before a local read and rejects
any control-flow edge from outside that interval into its interior. This
proves that the assignment dominates the read. It does not infer a region
from merged values. The object profile keeps its original single-assignment
rule. Label positions are indexed only for the current function, after
emission; module label IDs may repeat without becoming cross-module edges.

The checker memoizes only completed, successful all-caller fixed-extent
proofs. Its zeroed heap table is allocated after the retained SIR is frozen;
M[202] is its base, indexed by function and one of16 parameter slots. Clear
M[202] before each module admission. Unknown, pending and depth-exhausted
results are never cached. The proof depth bounds and pointer refusals are
unchanged. Static runtime cells in this range are ignored outside the
closed profile with M[197]=0.

Carry device readiness as a separate scalar. Keep the owned DMA base intact
even when a device is absent. Bind a conditional readiness value before
evaluating the call's arguments, so a later argument's branch does not
obscure the earlier base's straight-line temporary provenance.

The fixed-extent native suite covers disjoint scopes, six-argument readiness,
identity recursion, forged/computed callers, mixed extents, unseeded
recursion, branch-result pointers and inline argument branches. Compiler
admission, actual QEMU execution, complete kernel boot, live queue/syscall
ABI and physical DMA remain separate verification surfaces.
