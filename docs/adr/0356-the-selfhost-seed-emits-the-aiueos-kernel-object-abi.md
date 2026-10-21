# 0356 — the selfhost seed emits the aiueos kernel object ABI

Date: 2026-10-18

## Decision

The native seed x86 route grows a second output shape: `compile SOURCE
--target x86_64-aiueos-kernel-v1 --output NEW_OBJ [--fuel POSITIVE_BUDGET]`
emits the linkable aiueos kernel **object** ABI — the exact shape aiueos's
fail-closed `os/aiueos/scripts/verify-kotoba-kernel-object.py` admits. This
is the first `x86_64-aiueos-kernel-v1` artifact produced by a selfhost-built
compiler (Linear JUN-30, slice 1).

Shape: ELF64 ET_REL/EM_X86_64 with no program headers and exactly the seven
sections `"" .text .data .rela.text .symtab .strtab .shstrtab`; one public
GLOBAL FUNC in `.text`; one private 80-byte freestanding context in `.data`;
exactly one `R_X86_64_PC32` addend `-4` relocation of the wrapper's
`lea r9,[rip+.data]` against the `.data` symbol. The wrapper mirrors
`kotoba.native.elf64/package-kernel-object`: load the private context,
replenish the per-call fuel word at `context+8`, `sub rsp,8`, call the local
Kotoba entry, `add rsp,8`, `ret`. The export name is the source's own single
export — the symbol is never silently renamed.

Admission is the x86_64-linux profile-0 scalar subset with a different export
rule: exactly one exported defn, any name, at most five scalar parameters,
scalar result; capabilities refuse; `main` carries no special meaning. The
shared check stage may refuse a shape first (E21xx); either stage refusing is
fail-closed.

## Status

Implemented and gate-verified in this change (see `scripts/seed/check-x86_64-aiueos-object.py`).
Evidence measured 2026-10-18 on aarch64-macos:

- `build-x86_64-linux.py` PASS with the new module in `X86_64-LINUX-MANIFEST`
  and `X86_64-LINUX-SELFHOST-MANIFEST` (G1/G2 identity preserved).
- `scripts/seed/check-x86_64-linux.py` PASS (55 programs, 14 refusals, the
  adopted AArch64 route byte-identical to the bootstrap compiler).
- `scripts/seed/check-x86_64-aiueos-object.py` PASS (4 objects, 15 refusals),
  and one emitted probe object passes aiueos's
  `verify-kotoba-kernel-object.py` (`AIUEOS_KOTOBA_OBJECT_OK
  export=kotoba_aiueos_probe imports=0 relocations=1`).

## Non-claims

- This is the **object** route only. The kernel **image** route (boot shim,
  ISR region, sealed fuel) and `BOOTX64.EFI` packaging are not implemented in
  the seed.
- No emitted object has run in a kernel. Linking and ABI admission are not
  execution (aiueos ADR-0220's rule).
- The kernel-object entry allowlist and the per-entry fuel-tier table from
  `kotoba.native.elf64` are not ported: the public symbol is the source's
  export name and `--fuel` names the bound. A production object must still be
  built through the product route's allowlist/tier rules.
- No whole-product selfhost claim: the seed closure still runs through the
  pinned trusted C loader (JUN-29) and refuses project/KIR/float routes.
