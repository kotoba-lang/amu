# ADR-0380 -- the aiueos object route gains external symbols and data sections

- Status: **proposed**. Nothing here changes a seed, an artifact or a pin.
- Date: 2026-10-29
- Tracking: JUN-556 (D), JUN-551 (the zig cc inventory), JUN-548, JUN-417.
- Follows: ADR 0373 (bounded kernel memory windows), ADR-0219/0220 in the
  kotoba repository (C-free waves 1 and 2).

## Context

`seed/74-x86_64-aiueos-object.kotoba` emits one ELF64 ET_REL with exactly seven
sections (`"" .text .data .rela.text .symtab .strtab .shstrtab`), up to eight
public functions, one private 80-byte context in `.data`, and one relocation per
export (the shim's `lea r9,[rip+.data]`). The consumer,
`verify-kotoba-kernel-object.py` in the kotoba repository, refuses anything else.

The 2026-10-29 inventory of `build-uefi.sh` (JUN-551) counted 40 `zig cc` calls.
Of the 31 C files that are neither assembly nor generated, about 28 cannot move
to this route as it is, because they need one of:

| need | files (count from a regex pass; approximate) |
|---|---|
| calls to functions of other objects | kernel/main.c (272 distinct), pci.c (55), process.c (42), scheduler.c (10), framebuffer.c (9) |
| writable globals | pci.c (137), tls13.c (34), scheduler.c (23), main.c (21), acpi.c (13) |
| `const` tables | pci.c (14), tls13.c (4), uefi/*.c (2 each) |

Argument counts above five (JUN-556 E) are a separate limit and not decided here.

## Decision (proposed): three slices, each admitted fail-closed

### D1 -- undefined function symbols, from a declared list

A source names the foreign functions it may call. No new syntax in the shared
frontend: the object route already appends a library of private stub functions
(ADR 0373) and replaces their call sites with inline bytes. D1 uses the same
mechanism with one more family.

* A private function named `extern-<symbol>` with a body of `0` and 0..5
  `:i64` parameters is an extern declaration. The backend replaces its call
  site with `call rel32` (`E8 00000000`) and records an `R_X86_64_PLT32`
  relocation, addend -4, against an undefined GLOBAL NOTYPE symbol `<symbol>`.
* The declared set is closed: at most 16 externs per object, each name unique,
  matching `[a-z_][a-z0-9_]*`, never one of the object's own exports.
* The call follows the System V convention the route already uses for its
  entry; the callee is the linker's business and is **unverified** by this
  route. The verifier checks only that every undefined symbol is a declared
  one and that every relocation against it is a PLT32 -4 at a `call` opcode.
* An extern call needs the same rooted-base/paired-length admission as the
  memory windows for any pointer argument the checker can see (E7106); an
  extern that takes a pointer must say so in its declaration parameters
  (`ptr`/`len` suffix names, as the windows do).

### D1 call sequence (decided 2026-10-29, corrected the same day after reading seed/70)

The first version of this section proposed a 34-byte wrapper that aligned rsp and
stashed r9. Reading the shared emitter (`seed/70-x86_64-linux.kotoba`) shows that
was more than the code needs; the code, not the earlier text, is the authority:

* **Alignment is already guaranteed.** The shim does `sub rsp,8; call entry`, the
  prologue is `push rbp; mov rbp,rsp; sub rsp,frame`, and `xg-frame` rounds the
  frame to a multiple of 16. rsp is 16-byte aligned at every call site in a body.
* **r9 is the one real hazard.** The fuel charge (`xg-fuel`) reads the context as
  `mov rax,[r9+8]`, and System V lets a callee destroy r9. But the prologue
  already stores r9 at `[rbp-8]` (`4c 89 4d f8`), so restoring it costs one load.

So an extern call is the arguments loaded as for a local call (`xg-call-args`:
rdi, rsi, rdx, rcx, r8), then

    call <symbol>        ; e8 00 00 00 00, R_X86_64_PLT32, addend -4
    mov  r9, [rbp-8]     ; 4c 8b 4d f8

and the result is saved as any call result is. Assembled independently (Apple
clang 21, `-target x86_64-unknown-linux-gnu`, Intel syntax, `ext` undefined):
9 bytes `e8 00 00 00 00 4c 8b 4d f8`, one relocation, type 4 (PLT32), addend -4,
at offset 1. Nothing executed it; the `native-cross` CI job must run an object
that calls through it before D1 is claimed.

An extern takes at most **five** arguments. The route's own convention passes the
sixth and later on the stack from `[rsp]`, while System V puts the sixth in r9;
the two differ, so an extern with six or more would be called wrongly. This is a
limit of D1, separate from JUN-556 E.

Rejected: aligning rsp at each call (unneeded); a second `lea r9,[rip+ctx]` with a
PC32 relocation after each call (one more relocation per call site).

### D2 -- `.rodata`

`def` takes literals only (native.micro-infer packs a 729-entry matrix into
nibbles for that reason). D2 adds an eighth section `.rodata` filled from a
`(def-bytes NAME "...")` form handled by the backend, readable only through
`kernel-load-u8` / `-u32` windows whose base is the `.rodata` symbol and whose
length is the literal size. The table is addressed with `lea reg,[rip+sym]` and
a PC32 relocation against the local `.rodata` symbol. Size cap: 64 KiB per
object until a larger case is measured.

### D3 -- writable globals (`.data` beyond the context, `.bss`)

A fixed number of named cells (u8/u16/u32/u64) in `.bss`, zero-initialised, and
a `.data` initialiser form for the few that are not zero. Access is through the
same windows. Each is a LOCAL OBJECT symbol; none is exported. The 80-byte
private context stays first and unchanged.

### D4 -- MMIO, port and privileged-instruction intrinsics (added 2026-10-29)

Reading `ioapic.c`, `apic.c`, `smp.c` and `loader.c` (JUN-556) showed that D1-D3
do not reach even the small stateful kernel files: they use `volatile` MMIO at a
fixed physical address, `outb`, `pause`, `cpuid`, `mov cr4`, `xgetbv`/`xsetbv`.
The route has no intrinsic for any of them (ports come from the locked-project
route's kernel suffix only). D4 adds them in the style of the memory windows:

* each is a private stub whose call the backend replaces with inline bytes;
* an MMIO access names its base as a literal in the declaration and a bounded
  register offset, and traps (ud2) outside it, as the windows do;
* port and control-register forms take a literal port or register, never a
  computed one; `cpuid`/`xgetbv`/`xsetbv`/`pause` are fixed sequences;
* the verifier recognises exactly these byte sequences and refuses any other
  privileged opcode in `.text` (`out`, `in`, `mov cr*`, `wrmsr`, `rdmsr`
  excepted where an existing Kotoba extern already owns them).

The first file this can reach is `apic.c` (D1 plus one MMIO window). It sits on
the interrupt path, so replacing it needs a QEMU/OVMF boot on a Linux host
before anything is claimed. Order: D1, D3, D4, then E.

## What the verifier must change

`verify-kotoba-kernel-object.py` and the pin ledger (`local-changes.json`) move
together with the seed, so the order is: seed change, then verifier change, then
the receipt-driven pin adoption path the Mac gate already uses. Concretely:

1. Section list: seven sections stay the default; `.rodata` and `.bss` are
   allowed only when the object's declaration says so.
2. Symbol table: undefined symbols are allowed only for names in the declared
   list and only as GLOBAL NOTYPE; every other undefined symbol stays a refusal.
3. Relocations: PLT32/-4 against a declared extern at a `call`, PC32/-4 against
   the context or `.rodata`/`.bss` symbols at a `lea`; nothing else.
4. Negative controls, one per refusal: an undeclared extern, a ninth export,
   a `.rodata` write, an out-of-window `.bss` read, an extern named like an
   export, a relocation of an unknown type.

## What this does not show

* No code is written. D1 is estimated at a few hundred lines in seed/74 plus
  the verifier; D2 and D3 are larger because the window tiers must learn a
  symbolic base.
* Even with D1-D3, `uefi/*.c` cannot use this route: the UEFI entry uses the
  Microsoft x64 convention and the route emits System V. That is the loader
  decision (JUN-551 A/B/C), and the `.S` files have no Kotoba output path at
  all.
* The linkers (`ld.lld`, `lld-link`) stay: their replacement is
  `package-aiueos-boot`, which today covers only the ordinary transition.
* The counts in the context table come from a regex pass and need a per-file
  review before a slice is scoped.

## Order

D1 first. It unlocks the callers with the largest external counts (main.c,
process.c, scheduler.c) only after D3 gives them state, so the first measurable
result is a small file that calls out and holds no globals; the inventory has
none, which is itself the finding: **D1 alone replaces zero files**, D1+D3
replace the small stateful kernel files, and the large ones need all three.
