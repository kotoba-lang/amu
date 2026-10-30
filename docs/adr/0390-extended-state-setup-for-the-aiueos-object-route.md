# ADR-0390 -- the aiueos object route sets up the AVX extended state, bit-bounded (JUN-633 slice 2)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-xstate.py`).
- Date: 2026-10-30
- Tracking: JUN-633 (slice 2).
- Follows: ADR 0389 (cpuid / rdtsc / rdrand, ids 18..23).

## Context

`qwen35_infer.c`'s `prepare_bsp_extended_state` sets CR4.OSFXSR, OSXMMEXCPT and OSXSAVE, then enables x87, SSE and AVX in XCR0. The live matvec's AVX2 arm depends on that, and `cpu_has_avx2` reads XCR0 back with xgetbv.

seed/86's kernel runtime can write CR0, CR3 and CR4 with any value. An object linked into a C kernel must not get that: JUN-633 asks that the verifier admit only the bits the AVX state needs.

## Decision

Four stubs follow the CPU block, as ids 24..27:

| stub | encoding |
|---|---|
| `kernel-cr4-set-bits [mask]` | `mov rcx,[mask]; mov rax,cr4; or rax,rcx; mov cr4,rax`. Returns the new CR4. |
| `kernel-xcr0-set-bits [mask]` | `mov rsi,[mask]; xor ecx,ecx; xgetbv; or rax,rsi; xsetbv; shl rdx,32; or rax,rdx`. Returns the new XCR0. |
| `kernel-read-cr4 []` | `mov rax,cr4` |
| `kernel-xgetbv []` | `xor ecx,ecx; xgetbv; shl rdx,32; or rax,rdx`. XCR0 only. |

- **Mask rule (E7107):** a write's mask must be a literal, non-zero, with every bit in the admitted set. For CR4 that's 0x40600 (OSFXSR 1<<9, OSXMMEXCPT 1<<10, OSXSAVE 1<<18). For XCR0 it's 0x7 (x87, SSE, AVX). `xk-check` reads the literal through `xk-src`.
  - A parameter, a computed value or any other bit is refused, and nothing is written.
  - The writes only OR, so no bit can be cleared and no other bit can be set from an object.
- **Caller's duty:** xsetbv raises #UD unless CR4.OSXSAVE is set. The caller sets it first, as the C does.
- **Opt-in block:** it is appended only to a source that names one of its stubs, after the earlier blocks, so the ids stay positional. Objects that name none are byte-identical, including ADR 0389's six-intrinsic object.

## Not in this slice

These are still open in JUN-633:
- halt-until-interrupt;
- f32.

## Evidence

- `scripts/seed/check-aiueos-object-xstate.py` decodes the four sequences. It checks the unchanged width object and refuses CR4.PGE, XCR0 bit 3, a parameter mask and a zero mask (E7107).
- `docs/evidence/xstate-intrinsics-20261030/` runs them under QEMU against inline-asm C:
  - `-cpu max`: CR4 and XCR0 read equal, CR4 gains exactly 0x40600, and XCR0 gains exactly 7.
  - `-cpu qemu64` (no XSAVE): CR4 reads equal, and the writes are not attempted.
