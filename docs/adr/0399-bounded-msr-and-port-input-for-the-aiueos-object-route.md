# ADR-0399 -- bounded MSR and port-input accesses for the aiueos object route (JUN-600)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-msr.py`).
- Date: 2026-10-31
- Tracking: JUN-600 (paging / MSR intrinsics), JUN-552 (the kernel objects that need them).
- Follows: ADR 0390 (the bit-bounded CR4 / XCR0 writes), ADR 0393 (one block per intrinsic).

## Context

Three AIUEOS kernel objects are still kotoba-compiler/1 objects because the native object route cannot spell them:
`msr-read` and `msr-write` (`rdmsr` / `wrmsr`, called from apic.c, paging.c and process.c) and `pci-config-read` (the
PCI configuration data port 0xcfc, read with `in eax,dx`). kotoba-native's `machine_ir.cljk` emitted them as
`:read-msr`, `:write-msr` and `:in-u32`, with any index and any port.

JUN-600 allows the paging and MSR operations the kernel needs as bounded intrinsics only, with the target and the input
range constrained by the verifier. General inline assembly and arbitrary privileged instructions stay out.

## Decision

Three stubs follow the fused-reduction block, each a block of its own, as ids 32..34:

| id | stub | encoding |
|---|---|---|
| 32 | `kernel-read-msr [index]` | `mov rcx,[index]; rdmsr; shl rdx,32; or rax,rdx`. Returns the 64-bit value. |
| 33 | `kernel-write-msr [index value]` | `mov rcx,[index]; mov rsi,[value]`, the value bound below, then `mov rax,rsi; mov rdx,rsi; shr rdx,32; wrmsr`. Returns the written value, as `:write-msr` did. |
| 34 | `kernel-in-u32 [port]` | `mov rdx,[port]; in eax,dx`. Returns the zero-extended dword. |

### The index and the port are literals in closed lists (E7107, compile time)

`xk-check` reads the operand's writer: it must be an integer literal (`OP-CONST`, 0 <= v < 2^32) and on the list. A
parameter, a let-bound or computed value, or any other literal is refused, and nothing is written. The lists come from
the kernel's callers, not from the architecture:

| MSR (read and write) | why it is listed |
|---|---|
| 0x1b IA32_APIC_BASE | apic.c reads it to check the xAPIC window and writes it back with the global enable |
| 0xc0000080 IA32_EFER | paging.c sets NXE; process.c sets SCE and reads it back |
| 0xc0000081 IA32_STAR | process.c writes and reads back the syscall/sysret selectors |
| 0xc0000082 IA32_LSTAR | process.c writes and reads back the syscall entry point |
| 0xc0000084 IA32_FMASK | process.c writes and reads back the RFLAGS mask |

0xc0000083 IA32_CSTAR, between two listed indices, is not listed: nothing programs the compatibility-mode target.
FS_BASE / GS_BASE / KERNEL_GS_BASE, TSC, PAT and the rest are not listed either: nothing in the kernel reaches them.

| port (in-u32) | why it is listed |
|---|---|
| 0xcfc | the PCI configuration data port; pci.c's configuration reads |

The kernel's `msr-read` / `msr-write` take the index as a run-time argument (the C passes `uint64_t index`, always one
of the five constants). The native objects keep that ABI and select a literal per index:
`(cond (= index 27) (kernel-read-msr 27) ... :else 0)`. So every `rdmsr` / `wrmsr` in the object names its register in
the source, and the run-time index only chooses among them. Per-index exports would have needed C changes, and they
would have bought nothing more.

### The value: bounded at run time where the kernel's use allows

The kernel computes every written value at run time, so there is no literal for the verifier to check, as there is for
ADR 0390's masks. ADR 0390's rule is that a write may only set admitted bits and may clear none. The write stub applies
that rule at run time to the two registers whose kernel use is "OR one bit into the current value":

- IA32_APIC_BASE may only set bit 11 (xAPIC global enable).
- IA32_EFER may only set bit 0 (SCE) and bit 11 (NXE).

The stub reads the current value and requires `value == current | (value & admitted)`. A write that clears any bit, or
sets any other bit, reaches `ud2` before the `wrmsr`. So the object cannot clear LME, move the APIC window, enable
x2APIC or set FFXSR.

Not bounded:
- **STAR, LSTAR and FMASK** take the kernel's selectors, entry address and flag mask whole. The value goes to the
  register as given, and only the CPU's own checks apply (#GP for a non-canonical LSTAR, or a reserved FMASK bit).
- **The read value** is returned exactly, bit 63 included.
- **The port-write side** is outside this ADR. `kernel-out-u8` and `kernel-out-u32` (ids 4..5, ADR 0373) still took
  any port, computed or not. ADR 0400 later gave them literal per-width allowlists.

### Opt-in

Each block is appended only to a source that names its stub or a later one. Earlier blocks come too, so the ids stay
positional. An object that names none of the three keeps its bytes.

## Evidence

- `scripts/seed/check-aiueos-object-msr.py` (wired into mac-selfhost-aiueos.yml) checks:
  - It decodes the three sequences in one object: five reads, five guarded writes, one `in`, and no other `rdmsr`,
    `wrmsr` or `in`.
  - The fused-reduction dot object and the width object are unchanged.
  - It refuses with E7107: CSTAR, TSC and PAT; a parameter index and a computed index; ports 0xcf8 and 0xcfd; a
    parameter port.
  - It refuses with E2103 each stub called with the wrong number of arguments.
  - The same gate fails on main's root (E2101 on `kernel-read-msr`).
- `docs/evidence/msr-in-intrinsics-20261031/` runs it under QEMU (qemu64 and max) against inline-asm C.
  - The five reads are equal.
  - 606 admitted writes match the C write's effect.
  - 72 bound-violating EFER / APIC_BASE writes trap #UD and leave the register unchanged.
  - Ten unlisted indices are refused without a trap.
  - 32768 PCI configuration dwords are equal.
  - A mutant gives 0x80c8 differences.
- All 99 of kotoba's committed native-route objects, from main's `git archive`, recompile byte-identical on this root.
