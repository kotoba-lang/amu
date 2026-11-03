# ADR-0389 -- the aiueos object route reads CPU features: cpuid, rdtsc, rdrand (JUN-633)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-cpu.py`).
- Date: 2026-10-30
- Tracking: JUN-633 (first slice).
- Follows: ADR 0386 (the 16 KiB width block), seed/86's kernel runtime (km-cpu, km-entropy).

## Context

The aiueos kernel C that JUN-554 is moving into Kotoba objects reads the CPU:
- `qwen35_infer.c` probes AVX2 and XSAVE (`cpu_has_avx2`, `prepare_bsp_extended_state`) and times its stages with `lfence; rdtsc`;
- `device_result.c` draws its device nonce from `rdrand`.

The object route (`x86_64-aiueos-kernel-v1`, seed/74) had no way to express any of these. Seed/86's whole-kernel runtime already had them, under these names and with these encodings.

## Decision

Six stubs follow the 16 KiB width block as ids 18..23, named and encoded as seed/86 has them:

| stub | encoding |
|---|---|
| `kernel-cpuid-eax / -ebx / -ecx / -edx [leaf subleaf]` | `mov rax,[leaf]; mov rcx,[subleaf]; push rbx; cpuid; [mov eax,ebx\|ecx\|edx]; pop rbx`. rbx is nonvolatile and is restored. The 32-bit move zero-extends rax. |
| `kernel-rdtsc []` | `lfence; rdtsc; shl rdx,32; or rax,rdx`. The only difference from seed/86: lfence orders the read, as the C it replaces does. |
| `kernel-rdrand []` | `mov ecx,10; L: rdrand rax; jc done; dec ecx; jnz L; xor eax,eax`. 0 means "no entropy", and callers must fail closed. |

- **Opt-in block:** it is appended only to a source that names one of its stubs, together with both width blocks, so the ids stay positional. A source that names none compiles to the bytes it always had. The gate checks that against the pinned 512-byte width object.
- **No base:** none of the six takes a base, so none is a window. The window predicates (`xk-window-k?` and the rooted-base check in `xk-check`) now stop at id 18 instead of at `XK-EXTERN`. A CPU read used as a window base is still refused (E7106), because it is not a rooted region.
- **Caller's duty:** rdrand raises #UD on a CPU without it. The caller checks CPUID.1:ECX[30] first, as the C does. The intrinsic does not hide that.

## Not in this slice

These are still open in JUN-633:
- **Halt-until-interrupt (`sti; hlt; cli`).** It cannot be exercised under the gate's QEMU harness, which has no IDT or timer.
- **CR4 and XCR0 writes.** They must admit only the bits the AVX state needs, so they need a verifier rule, not a free value.
- **f32 operations.** The object route has none. The committed qwen35 objects come from the earlier `kotoba-compiler/1` route.

## Evidence

- `scripts/seed/check-aiueos-object-cpu.py` decodes the six sequences. It checks the unchanged width object and refuses a CPU read as a window base (E7106) and a wrong arity (E2103).
- `docs/evidence/cpu-intrinsics-20261030/` runs the six-export object under QEMU against inline-asm C:
  - 36 cpuid registers over 9 leaves, identical on `-cpu qemu64` and `-cpu max`;
  - rdtsc monotonic over 1000 reads;
  - rdrand non-zero on `max`, and not called on `qemu64`, which lacks it.
- Values that differ by CPU are not claimed beyond these two QEMU models.
