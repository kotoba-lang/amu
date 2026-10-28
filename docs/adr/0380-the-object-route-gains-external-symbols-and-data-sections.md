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

### D1 call sequence (decided 2026-10-29; reading seed/74 for JUN-556)

An extern call has two hazards the stub mechanism does not have: the context
register r9 is caller-saved in System V, and the stack alignment at a call site
inside an export depends on the frame size. Decision: a fixed 21-byte wrapper
around every extern call, with the arguments already in rdi, rsi, rdx, rcx, r8:

    mov  r11, rsp          ; 4C 89 DC? (encoding checked by the gate, not here)
    and  rsp, -16
    sub  rsp, 16
    mov  [rsp], r11        ; the unaligned rsp
    mov  [rsp+8], r9       ; the context register
    call <symbol>          ; E8 rel32, R_X86_64_PLT32 -4
    mov  r9, [rsp+8]
    mov  rsp, [rsp]        ; rax (the result) is untouched

No callee-saved register is claimed, so the register allocation of the route is
unchanged; the wrapper is the same bytes at every call site, which keeps the
verifier's rule "exactly this sequence before each PLT32 call" checkable. r9 is
then intact after every call, which is also the answer to the E-side r9
conflict for calls: only the seventh and later argument words still need a
decision (E1/E2/E3), because they go on the stack above this block.

Rejected: restoring r9 with a second `lea r9,[rip+ctx]` and PC32 after each call
(one more relocation per call site, and the symbol table grows with the call
count); aligning every frame to 16 (it changes the bytes of every pinned object).

The encodings above are written for review, not copied from a verified table:
the first gate must assemble them independently and compare, before any seed
change.

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
