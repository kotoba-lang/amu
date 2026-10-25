# AIUEOS native user context v3

This candidate extends the v2 isolated domains and typed live-call gate.
It retains all adopted core modules and the complete locked kernel graph.
It is a mechanism qualification candidate, not a complete OS or scheduler.

The image owns a 0x240000-byte private RW segment and its four-level page
tables. Four 16KiB domain windows contain code RO/X, request RW/NX, an
unmapped stack guard and stack RW/NX. Only the selected domain has user
permissions. Kernel text is supervisor RO/X; private data is supervisor
RW/NX; null is unmapped; CR0.WP is enabled. The kernel stack remains at
context+0x10000..0x20000. The low512GiB identity map uses huge supervisor
NX leaves except the low8MiB refinement. LA57, OSXSAVE or absent NX/SYSCALL
support refuses this initial profile. It initializes legacy x87/SSE state;
extended-state ownership and FPU context switching remain separate work.

The native SYSCALL handler saves user state through RIP-relative stores
before using user R9/RSP, then selects its private context and kernel stack.
Only syscall5 reaches the typed entry. Return RIP/RSP and the complete
104-byte request envelope are checked against the selected domain. Invalid
requests return0 without mutating the private96-byte kernel request.
Invalid return state halts before SYSRET. Privileged flags and private
scratch registers are cleared on return. No user function pointer is used.
Inherited SYSENTER rails are disabled when the CPU advertises SEP.

The profile exclusively owns #UD/#GP/#PF entries, recording the actual
vector, error, CS/RIP/RSP and CR2 before halting. #UD's absent hardware error
is normalized to zero. Root exports conflicting with vectors6/13/14 refuse.
ISR discovery checks the ISR role tag, so ValueRuntime role IDs never
become interrupt vectors. Namespace interfaces remain ordinary link edges.

The larger private segment requires the native PE packager to choose a
non-overlapping preferred loader span from4/16/32MiB. Its segment and image
limits remain bounded; no firmware allocation fallback supplies authority.

Admission/refusal tests run with converged native producers on ARM and
x86. The separate QEMU observer checks actual CPL3/SYSCALL, W^X table
readback, forged R9, invalid request/number, supervisor/NX/guard faults,
privileged OUT and SYSENTER. Guest execution uses QEMU TCG, not native
x86 hardware. Media, desktop/input, preemption, canonical value/token
binding and physical-hardware qualification require independent receipts.
