# ADR 0369 — The native kgraph becomes a per-run budget; compiler images bake a larger one

- Date: 2026-10-09
- Status: Accepted (the owner chose option (a) of docs/selfhost-kgraph-capacity-20261008.md; reversible: reverting
  restores the fixed array and regenerates the decisions region).
- Amends: amu `tools/kexe_loader_decisions.kotoba` constant 2 (`KEXE_KGRAPH_CAPACITY`, 4 096: was the size of the datom
  array, is now the default per-run budget), adds constant 27 (`KEXE_KGRAPH_MAX`, 16 777 216: the address-space maximum)
  and budget 7 (kgraph) of the budget verdict; `tools/kexe_loader.c` (the `KEXE_KGRAPH` override, the
  `KEXE_EMBEDDED_KGRAPH` packaged constant, an (entity, attribute) index behind `kgraph_get`); the vendored
  `resources/kotoba/lang/limits.edn` and `kotoba.compiler.limits/table` gain `:profile/native :cells :kgraph` and
  `:kgraph-max` (upstream kotoba-lang `lang/limits.edn` needs the same lines).
- Unchanged: the artifact ABI (`:context-abi :kgraph-capacity 4096` in nbb.cli `compile-native!` and in
  kotoba-verifier's expected context), every context offset, the trap line, the structured report.
- Related: ADR 0364 (the same shape for the vector table), docs/selfhost-kgraph-capacity-20261008.md (the measurement),
  docs/selfhost-compile-twin-spike-20261008.md gap 2, seed/CONTRACT-REQUESTS.md 2026-10-04 SEEDLANG (left this open).

## Context

`KEXE_KGRAPH_CAPACITY 4096u` arrived with the kgraph ops (86df0919b, 2026-07-19) for a 6-datom pilot, copied from the
pair capacity, and stayed the fixed size of the datom array; the decision record said only "kgraph datoms per run".
Since seed rung r6l (2026-10-04) the seed keeps run-time keyword texts in the kgraph (1 datom for a keyword its static
table has, 1 + ceil(code points / 3) otherwise, never retracted), and kotoba-native's Kotoba arms mint label, vreg and
function identities as keywords. So the Kotoba-route compiler needs kgraph datoms in proportion to the code it emits:

- over the 311 corpus programs the compile-twin spike compiles: 417 datoms for the smallest, Pearson r = 0.975 between
  datoms and emitted aarch64 bytes (0.37 against source bytes), about 1.6 datoms per byte above the 417;
- the 8 programs over 4 096: recursive-tree 4 153, kernel_state 4 944, i64_set 5 270, lazy-sequence 8 959,
  approval-queue-app 9 284, sorted_map 12 291, ex_info_round_trip 28 170, typed-closure-parameters 28 285;
- 92-97% of those datoms are the backend's keywords; without them the 8 need 421-912.

`kgraph_get` was a linear scan, and the registry calls it per keyword made and per code point read back:
ex_info_round_trip made 6 022 187 calls scanning 40 093 150 350 datoms.

As a fixed size, 4 096 bounded no resource (24 B a datom) and protected no invariant (generated code does not depend on
it; the bound is checked host-side in `checked_kgraph_assert`).

## Decision

1. The kgraph has the pair arena's shape: the datom array is mapped over `KEXE_KGRAPH_MAX` (address space, touched only
   as asserted); the budget in force defaults to `KEXE_KGRAPH_CAPACITY` (4 096, the ABI's number, so a user artifact
   behaves exactly as before); `KEXE_KGRAPH=<n>` names another for one run, refused by name when zero, not a decimal
   ("KEXE_KGRAPH must be a positive decimal integer") or above the maximum ("KEXE_KGRAPH exceeds the 16777216-datom
   ceiling"), exit 2; a packaged command bakes `KEXE_EMBEDDED_KGRAPH` (a header without it gets the default).
2. `KEXE_KGRAPH_MAX` = 16 Mi datoms: 384 MiB of address space. At ~1.6 datoms per emitted byte that is about 10 MB of
   emitted code in one process, more than the 6.9 MB frontend image itself.
3. `kgraph_get` answers through an (entity, attribute) -> latest-datom hash (open addressing, power-of-two slots >= 2 x
   the budget, mapped private before the fork; 32 KiB at the default budget). Same last-write-wins answer; count and
   entity-at keep their scans.
4. The compiler-hosting images bake 1 048 576 (1 Mi): scripts/seed/launcher/build.sh (native amu), seed/amu-main/build-k.sh,
   seed/amu-front/build.sh (`AF_KGRAPH`), scripts/seed/frontsrc/build-one-src.sh, scripts/seed/emit/build-one.sh,
   scripts/seed/package.sh (`SEED_PKG_KGRAPH`); seed/tests/compile-twin/run.sh runs the guest with the same.
   `scripts/package-command.cljk` (user commands) is unchanged: 4 096.

Why 1 Mi and not 32 768: 32 768 is 16% above the largest corpus program (28 285 datoms for 29.7 KB of code), so a
program with ~35 KB of emitted code would trap again; need grows with code size, not with anything a smaller budget
protects. With the index the cost of a larger budget is address space (24 MiB of datoms and 8 MiB of index at 1 Mi,
touched only as used), and the CPU/wall emergency stops still bound the run. 1 Mi covers ~650 KB of emitted code per
compile.

## Verification (2026-10-09)

- `npm run test-loader-warnings`: clean under -Wall -Wextra -Werror. `gen-loader-decisions.cljk --check`: region up to
  date (regenerated with this change, both ISAs).
- `npm run test-loader-decisions`: classification, region, 4 201 driver cases identical; of the 664 black-box loader
  runs the same 16 differ from the C-decisions loader (0d244a95) as on the unchanged base b9069e213 (17 failures each,
  the 16 plus their summary line): the `KEXE_VECTORS` ceiling text of ADR 0364. Nothing kgraph-related differs.
- `seed/tests/kgraph-capacity/check.sh`: 4 096 datoms answer and 4 097 trap `:budget/cells :arena :kgraph` with no
  override; `KEXE_KGRAPH=4097` admits 4 097 and traps at 4 098; 1 000 000 datoms answer under `KEXE_KGRAPH=1048576`;
  16 777 216 admitted, 16 777 217 / 0 / `1x` refused by name; every answer equals the closed form and, for N = 0 .. 4 097,
  the output and exit status of the loader before this change (which scans).
- Compile twin (seed/tests/compile-twin/run.sh, 52 programs, committed spike): the 4 kgraph programs (i64_set,
  sorted_map, approval-queue-app, kernel_state) go from the kgraph trap to SAME. 43 sampled previously-SAME programs
  stay SAME, and their outputs are byte-identical to the previous loader's. All 8 oracle-fallback outputs equal a
  scanning 65 536-datom loader's byte for byte. Details and timings in docs/selfhost-kgraph-capacity-20261008.md.

## Consequences

The kgraph stops being the wall of the Kotoba-route compiler. The proper fix of the volume is kotoba-native's (not
minting transient identities as keywords: 92-97% of the datoms), and the seed's keyword registry sharing a user
program's datom budget remains (a separate table would need a context slot, an ABI bump). Both are follow-ups, not
taken here. The Windows loader (tools/kexe_loader_windows.c) keeps its fixed array.
