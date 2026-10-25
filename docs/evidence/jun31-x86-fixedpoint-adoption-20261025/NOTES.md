# JUN-31: x86 complete fixed point re-adoption (2026-10-25)

`bin/amu` + `native-product.json` re-adopted to the complete native x86
compiler fixed point measured by the `x86_64-native-receipt` CI artifact of
selfhost-native run `40114082748` (head `c1e7b303f`, PR tier, native Linux
x86_64 runner; no emulation, no C compiler/loader, no JVM/Node).

* **F1 = F2 = F3 byte-identical** (three generations): 8,978,944 B, sha256
  `4b4d743e63888b4dbd968417461a0e2f6ae611f28a714bc3a0efda32f04da281`. F1 = the arm64-built combined compiler `one/F-x86_64.elf`
  transported to x86_64; F2/F3 are its self-rebuilds from the full source
  (`scripts/seed/check-complete-x86.py`,
  `PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD` — receipt copy in this
  directory).
* sourceUnity `ff3f17de0782f521ade6dab6a42b4bb969aaeb225a8f35b7df658b27a1a67401`
  (3,317,891 B) verified equal to the working tree's `seed/FULL-MANIFEST`
  unity at adoption time; `sourceRevision` records the exact source merge
  `9b3418ce47ccb58ec6979bc356f046f9b8cfaf4c` (the only later seed change is
  the root pin pair, which is outside FULL-MANIFEST).
* The receipt's `publicNativeEntry.pinnedCompile` is
  `d9d93e2896184a1eff34a88f79cdfd9d51d96afd2af1f6d1b2020010ebc920bc`, the
  golden the public-product gate expects — the adopted product reproduces it.
* The same run's `qualify-x86_64` failed exactly at
  `check-aiueos-image-native.py:159` `('object bytes changed', 'probe')`:
  the fixed-point producers disagreed with the *previous* committed baseline
  `bin/amu` (full33 candidate `fcad9b63…`). This adoption makes baseline and
  producers the same bytes, which is the measured blocker for that gate.

Next: exact-head CI on the adoption commit must go green
(`check-aiueos-image-native` and the previously skipped steps:
aiueos-boot, kernel-memory, kototama-i64, clock-entropy, native-cdci,
public-native-product, wasm32-browser). M2 desktop input remains blocked on
owner judgment (ADR-0180/0131); JUN-31 acceptance NOT MET (M1 only).
