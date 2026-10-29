# SHA-256 crypto instructions: on for compiles, off for benchmarks (JUN-578)

Owner decision, 2026-10-29: nettle-sha256 must not be benchmarked against C with ARMv8 SHA-256 instructions the C
baseline lacks, while real compiles still use the hardware.

## Change

* `seed/41-a64gen.kotoba`: `kb-sha-hw` was the constant `false` (so no compile used the instructions). It is now a function
  that is true unless the process argv contains `--no-crypto-hw`. It gates the same two places as before
  (`sphase-hw?` round path, `srx-hw-ok?` schedule path).
* `seed/78-full-entry.kotoba`: `--no-crypto-hw` is a word flag of `compile` only. `check` with the flag is a usage error
  (exit 2). Other targets accept it and ignore it (no SHA kernel exists there).
* The `--no-crypto-hw` build is the same compiler output as the previous default, byte for byte.

## Evidence (signed Mac Amu, Apple M4, 2026-10-29)

Built from the new source by the pinned Mac root, then by its own output:

* Full compiler: container `5000126e…` for F1 = F2 = F3 on the source before merging main (the previous source's container
  `1bdd51b9…` was reproduced first as the control); after merging main (JUN-371 native cache) the re-pinned source gives
  `18592ff6…` for F1 = F2, and every check below was re-run on that state.
* 18-module core (`seed/MANIFEST`): unity `5b12da97…`, G1 = G2 = G3 native `9b893ba0…`, container `74de9bf3…`
  (`check-macos-core-adoption.py`: `PASS_MAC_CORE_ADOPTION_FIXED_POINT`).
* `official-nettle-sha256.kotoba` compiled three ways: the previous compiler and the new compiler with
  `--no-crypto-hw` give the same kseed (`96a0d911…`); the new default differs (`11585972…`).
* Instruction count in the native part (`sha256h`, `sha256h2`, `sha256su0`, `sha256su1`): default 1/1/1/1 (each in its
  loop), `--no-crypto-hw` and the previous compiler 0/0/0/0.
* Exactness: a test copy of the port with `main` added returns 11 (`bench 5` + 10 × `bench 1`, both verified) in both
  modes on the M4; with the first expected digest byte changed (negative control) both modes return 0.
* `scripts/seed/check-crypto-hw-option-macos-native.py` repeats the nettle-sha256 checks above (counts, exactness in both
  modes, negative control, flag refused by `check`) and is a step of `mac-selfhost-aiueos.yml`.
* Gates run on the regenerated root: `check-aiueos-user-macos-native.py`, `-user-v3-`, `-user-v5-layout-`,
  `-kernel-v3-layout-`, `-layout-rule-`, `check-aiueos-object-windows.py`, `check-macos-core-adoption.py` and
  `check-native-identities.py` (preflight) pass.

## Re-pinned

`bin/amu`, `native-product.json`, the aarch64 Linux root, the Mac root and `root.json` (via
`write-bootstrap-descriptors.py`, source phase then final phase with `--install`), the new adoption receipt
`seed/adoption-crypto-hw-option-20261029.json`, `seed/compiler-core.json` (previous identity retained under
`cryptoHwOptionPreviousIdentity`), `seed/cdci/policy.json` and the literal pins in `seed/cdci/controller.kotoba`
(core source and container).

## Not qualified

* The regenerated `bin/amu` and the ARM root were produced by the Mac cross build; native ARM/x86 execution, the CDCI
  controller (its image identity changes with the new pins; `docs/native-public-entry.md` still lists the previous
  one), cold C0, public aliases and release are pending the native CI. `seed/cdci/policy.json` sets
  `nativeExecutionQualified` to false until then.
* No timing was taken. The published 0.7999 (m93, hardware path on) and the M104 round (scalar) are unchanged.
* The Embench harness in `bench/embench/reproduce-20261015` is unchanged: its m93 and M104 compilers do not have the
  option. A new round must pass `--no-crypto-hw` and record it.
