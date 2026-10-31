# kernel-dot-f32 / kernel-dequant-dot-ptq1-0 under QEMU against kotoba-compiler/1 (JUN-633 slice 6, ADR 0394)

`run.sh OUT COMPILER [NDOT NDQ]` compiles `dot-native.kotoba` and `dq-native.kotoba` with a native Amu compiler (Mac
root `F2-signed.macho` built from this branch by `check-aiueos-user-macos-native.py`), links them with
`qwen35-matvec.o`, and boots the flat image under `qemu-system-x86_64` TCG. `qwen35-matvec.o` is the committed
kotoba-compiler/1 object of kotoba-lang/kotoba main 4528a70b (`lib/kotoba.aiueos/os/aiueos/kotoba/qwen35-matvec.o`,
SHA-256 0eabd3f8...). Its matvec reaches the same two builtins:

- an F32 (type 0) one-row plan with cols a multiple of 8 and at most 16384 takes `kernel-dot-f32` (scratch, input);
- a PTQ1_0 (type 143) plan with cols at most 16384 takes `kernel-dequant-dot-ptq1-0` (weights, input).

`driver.c` calls both objects on the same data and requires bit-equal answers. It also checks three more things: the
native answer is the f32 word sign-extended from bit 31, the old route's F32 scratch holds the weights' bits, and the
answer matches `ref.c` (the tree in C, SSE, no FMA or contraction; compared modulo NaN payloads, since C may commute a
product's operands).

The data covers ordinary magnitudes, quiet and signalling NaNs with random payloads, ±Inf, ±0, denormals and
magnitudes whose products overflow. Specials appear at 30%, about 0.1%, or (with no NaN or Inf inputs) 30%. PTQ1_0
blocks hold random bytes or valid base-3 bytes, and their fp16 scales cover the normal, subnormal, zero, Inf and NaN
classes. Counts go up to the limits: 16384 elements for the dot and 128 blocks for PTQ1_0.

Each run boots three CPU configurations:

| run | CPU | arm both objects take |
| --- | --- | --- |
| `serial-qemu64.txt` | `-cpu qemu64` | scalar |
| `serial-max.txt` | `-cpu max`, CR4.OSXSAVE and XCR0 = 7 set by the driver | AVX2 |
| `serial-max-noxsave.txt` | `-cpu max`, OSXSAVE left clear | scalar |

Result (2026-10-31, `run.sh OUT F2 20000 8000`, QEMU 10.0.3, zig 0.15.2), the same in all three runs:

- 20000 dot cases and 8000 PTQ1_0 cases: 0 differences, 0 unextended answers, 0 scratch mismatches.
  19126 answers are NaN, and every one matches the old object to the bit.
- 0 mismatches against the C model (19126 of them are NaN in both).
- FNV hash of every native answer: `ea75bcffc0a0934a` in all three runs. So the AVX2 arm and the scalar arm give
  identical bits, NaN payloads included, as TCG models them.
- Guards: 19 of 19 behave as expected. Past each guard the native object raises #UD (`ud2`): a length of 65537 or
  2^63, a null base, count 16385 or 2^62, blocks 129 or 2^60, or a span longer than its window. At the boundary
  (count 16384 with 65536-byte windows; 128 blocks with 3584 and 65536 bytes) it returns. The old object has the same
  guards (its disassembly shows `cmp 0x10000` on both spans and `cmp 0x4000` on the count before `ud2`), but its matvec
  never passes an out-of-range value, so they are not reachable through it.

Mutants (`MUTANT=... run.sh OUT F2 3000 1500`, `mutate.py`; the differential must go red):

- `scalar-reduction`, (l0+l1)+(l2+l3) changed to ((l0+l1)+l2)+l3 in both scalar arms: 286 of 4500 cases differ in
  the qemu64 and max-noxsave runs. The AVX2 run is unaffected (`mutant-scalar-reduction-*.txt`).
- `avx-halves`, the upper half of each block added before the lower half in both AVX2 arms (1 and 16 sites): 329 of
  4500 differ in the max run. The scalar runs are unaffected (`mutant-avx-halves-*.txt`).

Gaps, stated rather than rounded up:

- QEMU TCG emulates SSE and AVX in software. Both objects run the same instruction kinds, so a TCG mismatch with
  hardware in NaN propagation, denormal handling or MXCSR would hit both sides alike, and this differential would not
  see it. Hardware runs (with and without AVX2) are not part of this evidence.
- MXCSR is at its reset value (round to nearest, no FTZ / DAZ). Both arms inherit the caller's MXCSR, as the old
  route's did.
- Only the 1-row plan is exercised on the old side. The matvec row walk is the caller's code, not the builtin's.
