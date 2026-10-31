# f32-to-i64-truncating under QEMU against its defined semantics (JUN-633 slice 7, ADR 0395)

`run.sh OUT COMPILER [STRIDE NRAND]` does three things:
- compiles `f2i.kotoba` with a native Amu compiler. Here that is the Mac root `F2-signed.macho`, built from this
  branch by `check-aiueos-user-macos-native.py`;
- links it with `driver.c`, `ref.c` and `entry.S` into a multiboot flat image;
- boots the image under `qemu-system-x86_64` TCG, once with `-cpu qemu64` and once with `-cpu max`.

`f2i.kotoba` exports `kotoba_aiueos_f32_to_i64 [bits]`, which is `(f32-to-i64-truncating (f32-from-bits bits))`.
The object carries the guarded `cvttss2si` sequence of ADR 0395.

`ref.c` is the semantics in integer C, written from the bit pattern alone with no floating-point instruction:
- truncation toward zero;
- NaN, ±Inf and every |x| >= 2^63 other than -2^63 trap.

`driver.c` calls the object through `trapcall`. The #UD gate of `entry.S` abandons a call that reaches `ud2`. Each case
must match the reference, in one of two ways:
- the object returns, and its answer equals the reference integer;
- the object traps, and the reference traps too.

An answer of 0x8000000000000000 for any operand other than -2^63 is counted separately (INDEF).

Cases, all run twice, first with MXCSR = 0x1f80 (reset, round to nearest) and then with 0x5f80 (RC = round up),
because truncation must not depend on the rounding mode:
- 83 named specials:
  - ±0, ±denormals and the smallest normals;
  - ±0.5, ±(1 - 2^-24), ±1, ±1.5, ±2.5, ±3.5;
  - ±Inf;
  - quiet and signalling NaNs with payloads, both signs;
  - ±2^63 and their neighbours, ±2^62, ±2^31, ±2^32 and ±2^24 with their neighbours, and 2^23 (the last fraction
    bit);
  - the finite extremes;
- for every exponent and both signs, the first and the last 8 mantissas (8192 cases);
- a sweep of the 32-bit space with stride STRIDE (default 4099, 1,047,809 cases);
- NRAND uniform random patterns, and NRAND random values with exponents 2^-4 .. 2^66 (default 1,000,000 each).

## Result

Default run, 2026-10-31: `run.sh OUT F2`, QEMU 10.0.3, zig 0.15.2. The object SHA-256 is 17ca9dc6... in every unmutated run.

| run | cases | returned | trapped | diffs | indefinite answers | hash |
|---|---|---|---|---|---|---|
| `serial-qemu64.txt` | 6,112,168 | 5,052,403 | 1,059,765 | 0 | 0 | `360b024beaa801d5` |
| `serial-max.txt` | 6,112,168 | 5,052,403 | 1,059,765 | 0 | 0 | `360b024beaa801d5` |

The FNV hash covers every case's trap flag and answer. It is identical on the two CPU models and under both MXCSR
rounding modes.

## Mutants

Each mutant is `MUTANT=... run.sh OUT F2` with `mutate.py`. The differential must go red, and every mutant does, on
both CPUs:

| mutant | patch | diffs | what goes wrong |
|---|---|---|---|
| `round` | cvttss2si → cvtss2si (`f3 48 0f 2c` → `2d`) | 1,069,570 | 0.99999994 → 1, 1.5 → 2, -1.5 → -2, 2^23 - 0.5 → 2^23 |
| `noguard` | the guard's `jno` → `jmp` | 1,059,765 | every trapping case returns 0x8000000000000000 (INDEF 1,059,765) |
| `exempt` | the -2^63 exemption compares with 0xdf800000 | 8 | -2^63 traps, and -2^64 returns the indefinite |

The output is in `mutant-<name>-<cpu>.txt`.

## Gaps, stated rather than rounded up

- QEMU TCG emulates cvttss2si in software. A TCG difference from hardware in the indefinite value or its boundaries
  would go unseen here. There is no hardware run.
- MXCSR's FTZ / DAZ bits are left clear. With DAZ set, a denormal operand reads as 0, which gives the same answer, 0.
- The aarch64 route is not part of this run. It still saturates out of range (ADR 0395, "Relation to the aarch64
  route").
