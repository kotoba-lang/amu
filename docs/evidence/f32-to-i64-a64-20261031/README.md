# f32-to-i64-truncating on aarch64 hardware against the x86 run's reference (JUN-633, ADR 0398)

`run-a64.sh OUT COMPILER [STRIDE NRAND THREADS]` does the following:
- compiles `../f32-to-i64-20261031/f2i.kotoba`, the x86 run's source, with a native Amu compiler for
  `--target aarch64-macos`. Here the compiler is the Mac root `F2-signed.macho` built from this branch;
- cuts `kotoba_aiueos_f32_to_i64` out with `extract-native`;
- runs the same differential twice:
  - natively on the Mac, built with clang;
  - natively on Linux arm64 in the local podman machine, a static musl build from `zig cc` run in `debian:12-slim`.

  The podman machine is an Apple Hypervisor (applehv) VM, so this is not emulation.

The payload carries seed/41's guarded sequence (ADR 0398):

```
fmov s0,wX ; movz xD,#0xdf00,lsl #16 ; fmov s1,wD ; fcmp s0,s1 ; b.lt trap ; fneg s1,s1 ; fcmp s1,s0 ; b.gt ok ;
trap: brk #0 ; ok: fcvtzs xD,s0
```

## Harness

- **The reference.** `../f32-to-i64-20261031/ref.c` is unchanged: ADR 0395's semantics in integer C, written from
  the bit pattern alone.
- **Cases and order.** `driver-a64.c` copies the x86 `driver.c`'s cases and their order: 83 specials, the first and
  last 8 mantissas of every exponent and sign, a STRIDE sweep, then NRAND random patterns and NRAND random values with
  the same LCG. Its FNV hash over each case's trap flag and answer is therefore comparable with the x86 hash.
- **The two passes.** The x86 run sets MXCSR to round-to-nearest, then round-up. Here FPCR.RMode is set the same
  way: RN, then RP (`FPCR 400000`).
- **Calling the payload.** `call-a64.S` calls it as the runner does:
  - x0 is the sign-extended f32 word;
  - x7 is a context whose fuel (`[x7,#8]`) is reset before each call;
  - `[x7,#384]` (code_base) is the mapped payload. `f32-from-bits` reads its table through it.
- **Traps.** A trap is caught by a SIGTRAP / SIGILL / SIGSEGV / SIGBUS handler that resumes the caller. It counts as a
  trap only when it is SIGTRAP at the guard's `brk #0`. Any other trap is BADTRAP, which must be 0, and also counts
  as a difference.
- **INDEF** counts 0x8000000000000000 answers for operands other than -2^63, and must be 0.
- **Threads.** The sweep runs on THREADS worker threads per 2^22-case block. The main thread then checks and hashes
  the block in order, so the order matches the x86 run.

## Result

Tools: Apple M1 Max, macOS 26.4 (Darwin 25.4.0), Apple clang 21.0.0, zig 0.15.2. Podman 5.6.0 runs a
Linux 6.15.10-200.fc42.aarch64 machine. The payload `f2i.bin` has SHA-256 `89a93e26...` in every unmutated run. The
final root of this branch emits the same bytes.

Default run, 2026-10-31: `run-a64.sh OUT F2`.

| run | cases | returned | trapped | diffs | indefinite | bad traps | hash |
|---|---|---|---|---|---|---|---|
| `default-macos.txt` | 6,112,168 | 5,052,403 | 1,059,765 | 0 | 0 | 0 | `360b024beaa801d5` |
| `default-linux.txt` | 6,112,168 | 5,052,403 | 1,059,765 | 0 | 0 | 0 | `360b024beaa801d5` |
| x86 QEMU (`../f32-to-i64-20261031/serial-*.txt`) | 6,112,168 | 5,052,403 | 1,059,765 | 0 | 0 | - | `360b024beaa801d5` |

**Cross-ISA:** the hash is identical to the x86 object's. Over every case, both ISAs agree on which operands trap and
on every returned answer.

Exhaustive run: in progress; recorded in a follow-up commit on this branch.

## Mutants

Each mutant is `MUTANT=... run-a64.sh OUT F2`, which patches the payload with `mutate-a64.py`. The differential must go
red, and every mutant does, on both OSes:

| mutant | patch | diffs | what goes wrong |
|---|---|---|---|
| `noguard` | the guard's `brk #0` → `nop` | 1,059,765 | every trapping case returns `fcvtzs`'s saturated answer (INDEF 522,142). These are the main root's answers |
| `round` | `fcvtzs` → `fcvtns` (`9e38....` → `9e20....`) | 552,186 | 0.99999994 → 1, 1.5 → 2, -1.5 → -2, 2^23 - 0.5 → 2^23 |
| `edge` | the -2^63 check's `b.lt` → `b.le` | 4 | -2^63 traps (once in the specials and once in the edges, in each pass) |

The output is in `mutant-<name>-<os>.txt`. The noguard count equals the x86 noguard mutant's count, which is the
number of trapping cases.

## Gaps, stated rather than rounded up

- One CPU model, the M1 Max, in two OS environments. Other aarch64 implementations are not run.
- FPCR.FZ (flush-to-zero) and DN are left clear. With FZ set, a denormal compares and truncates as 0, which gives the
  same answer, 0.
- The harness calls one extracted function directly. A whole-program trap is covered by `check-a64-f2i.py`: packaged,
  signed Mac programs die by SIGTRAP.
- `f64-to-i64-truncating` (code 32) is not covered. It still saturates on aarch64 (ADR 0398).
