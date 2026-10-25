# Fresh derivation before independent ISA qualification (JUN-332)

The previous workflow waited for all ARM runtime/label/FS2/live checks before
starting any x86 qualification. In source/image metadata run40226249485,
bootstrap used208s and the ARM independent gates321s, followed by further
FS2/live checks. This is measured scheduling inventory, not a speedup claim.

Complete the unchanged fresh ARM bootstrap and one-compiler derivation first.
Transport their actual current-run artifacts, then run the remaining ARM
checks and the unchanged x86 job in parallel on separate native hosts. Both
ISA jobs retain every original gate, refusal, budget, controller/public and
browser check. All six native executions must succeed; artifact publication
is never a qualification result. Shared-module matrix checks remain required.

The moved one-compiler argv exactly matches the original gate. Concatenating
the derive and ARM phase lists reconstructs the original ARM list exactly.
The x86 phase and complete x86/shared job text are unchanged. Compiler source,
root/public images, case expectations and policy bytes remain unchanged.
The transport adds the actual root and all F generations for ARM's existing
producer identity checks, and restores executable bits after download.

PR/main/full tier selection and uncached full behavior are unchanged. No
previous receipt is reused and no validation check is replaced by a hash.
The20min target remains open until a complete exact-head native run succeeds
and its whole-workflow time is observed.
