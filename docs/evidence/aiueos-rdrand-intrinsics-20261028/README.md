# kernel-rdrand and kernel-rdseed intrinsics (JUN-482, 2026-10-28)

Two zero-argument kernel intrinsics, appended to the table (indices 102 and 103,
`KM-INTR-N` 104; no existing index moves). Each emits
`mov ecx,10; L: rdrand|rdseed rax; jc done; dec ecx; jnz L; xor eax,eax; done`
and returns the 64-bit value, or 0 when the source reported failure ten times in
a row. 0 therefore means "no entropy": callers must fail closed. Only rax and
rcx are used, both scratch in this runtime like the RDTSC and CPUID intrinsics.
The instruction is not guarded by the compiler; executing it on a CPU without
the feature raises #UD, so the caller checks CPUID first (as the desktop does).

Base: kotoba-lang/amu PR 1624 head eba8e3f5c (the kernel-v3 layout); this change
is stacked on it.

## Mac fixed point (Apple Silicon, signed bootstrap chain)

`check-aiueos-user-macos-native.py` with the producer built from the unchanged
PR 1624 head (compiler container `9f42f23c...`, F1 = F2) and, after this change,
48 modules (unity `7393f120e364eb798cdb6c4afeffdc98731746f2cbd225b8b0f9de0a287b8f38`):
F1 container = F2 container = `f9ea3bd0c788875170aa918095f47030cee0e7fceab44d81bd9b67e9b7400d4e`,
signed F2 Mach-O SHA-256 `9d023d997d70824058e4bfa83555f29b30ea1286e75ede702ca543f23211ce4e`,
verdict `PASS_MAC_NATIVE_USER_TARGET_SELFHOST` (`mac-aiueos-user-target.json`).
The whole gate took about 30 s.

## Guest evidence (kotoba-lang/kotoba native desktop, QEMU TCG)

`guest-consent-gate.json`: the consent gate with this compiler. The desktop reads
CPUID, then draws RDRAND twice only if the CPU reports it; the gate asserts both
draws are non-zero and different. Manual negative control on the same image:
`-cpu qemu64` (no RDRAND) gives flags 4 and both draws 0, no crash; `-cpu max`
gives flags 7 and two different non-zero words.

## Adopted roots (this change repins them, as earlier adoption rounds did)

* Mac root `seed/bootstrap/aarch64-macos/amu-full-root.macho`: signed F2
  `9d023d99...`; `root.json` fullSource `7393f120...`, container `f9ea3bd0...`.
  `check-aiueos-user-macos-native.py` with no explicit images (descriptor mode)
  passes: F1 = F2 = `f9ea3bd0...`.
* Linux candidates produced by that compiler with `check-macos-cross-linux-candidates.py`
  (`MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED`): ARM root `ad2a1ab7...` and x86 compiler
  `e68153f6...`, copied to `seed/bootstrap/aarch64-linux-static-root.elf` and `bin/amu`;
  `native-product.json` and `aarch64-linux-static-root.json` updated. `check-native-identities.py`
  passes (preflight only). The cross gate passes again against the new pins.
* The Linux candidates were **not** executed on their native ISAs here; that is the CI's job.

## The kernel-v1/v2 parity reference had to be re-baselined

Adding an intrinsic changes every kernel image: the runtime library compiles one
stub function per intrinsic into the text (about 86 bytes each; the v1 fixture
`main = 42` grew 172 bytes, p_filesz 10518 to 10690, 507 bytes differ). So the
kernel-v3 gate's "v1/v2 byte-identical under the new compiler" check cannot hold
against a reference compiler with the old intrinsic table (CI run 40557093102
failed there with "v1 changed under the new compiler"). Control: the unchanged
PR 1624 compiler (a50e174f...) produces the same bytes as the old reference, so
the difference comes from the table, not from other changes.

`seed/bootstrap/aarch64-macos/amu-kernel-v2-reference.macho` is now the
compiler built from main (07577ea62, before the v3 layout) plus exactly this
intrinsic patch (F1 = F2 container `d160b1fb...`, signed `dbe0936d...`). With it:
v1 and v2 fixture images are byte-identical to the new compiler's, and it
refuses `x86_64-aiueos-kernel-v3` (exit 2). This keeps the gate's meaning (the
layout change does not alter v1/v2 output) and drops its accidental dependency
on the intrinsic count. The previously qualified kernel-v1/v2 image bytes do
change for any kernel built after this commit.

## Local runs of every mac-root step (Apple Silicon)

PASS_MAC_NATIVE_USER_TARGET_SELFHOST (descriptor mode), PASS_MAC_NATIVE_USER_V3_LOCAL_CALL_ELF,
PASS_MAC_NATIVE_V5_LAYOUT_CANDIDATE, PASS_MAC_NATIVE_KERNEL_V3_GUEST_ARTIFACT,
PASS_MAC_CORE_ADOPTION_FIXED_POINT, PASS_MAC_NATIVE_EXEC_SMOKE,
MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED (ARM `ad2a1ab7...`, x86 `e68153f6...`).

## Not shown

* No stuck-source test: QEMU's RDRAND cannot be made to return a constant here.
  The failure path (CF clear ten times) is covered only by reading the emitted
  bytes: 17 bytes, `jc` +6 lands after `xor`, `jnz` -10 lands on the rdrand.
* RDSEED is emitted and compiles (F1 = F2) but no guest ran it.
* The old kernel-v3 compiler digest 4350f3ba is not the fixed point of PR 1624's
  head (that is `a50e174f...`, rebuilt here).
* The full native CDCI, the controller and the refusal corpus were not run locally.
