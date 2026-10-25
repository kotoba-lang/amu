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
rule. The same dominance condition admits an unchanged earlier argument
across a later argument's branch, while rejecting branch-result bases.
Label positions are indexed only for the current function, after
emission; module label IDs may repeat without becoming cross-module edges.

The checker solves fixed and adjacent-length contracts over the complete
call graph. It first propagates candidates from actual constructor/ABI roots
and the canonical paired contract of uncalled private helpers. It then
monotonically removes every candidate with a mismatching incoming call until
stable. This admits rooted mutual recursion without granting an unseeded
cycle authority. No guest instruction is admitted while candidates remain
tentative. Both phases are bounded by the number of candidate entries.

Allocate fresh, zeroed heap tables only after freezing the retained SIR.
M[202]/M[203] name fixed/paired contracts; M[205] caches unchanged-parameter
facts, and M[206] indexes each instruction's function start. M[204] is the
round's change flag. Clear these pointers before module admission. The
otherwise unused FN fuel field records incoming calls only after emission;
emitted source charges and image/IRQ fuel remain unchanged. Static runtime
cells in this range are ignored outside the closed profile with M[197]=0.
Local/source proof-depth bounds and pointer refusals remain unchanged.

Carry device readiness as a separate scalar. Keep the owned DMA base intact
even when a device is absent. Prefer binding a conditional readiness value before evaluating the call's
arguments. The compiler independently proves temporary dominance when a
later argument branches.

The fixed-extent native suite covers disjoint scopes, six-argument readiness,
identity and rooted mutual recursion, forged/computed callers, mixed extents, unseeded
recursion, branch-result pointers and inline argument branches. Compiler
admission, actual QEMU execution, complete kernel boot, live queue/syscall
ABI and physical DMA remain separate verification surfaces.
