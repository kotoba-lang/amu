# amu image with the frontend compiled FROM SOURCE, and its self-rebuild (agent FRONTSRC, 2026-10-04)

Question: can the seed compile the big frontend (`kotoba.compiler.frontend.analyze` and its closure) from source, so
that the one-amu image (amu-one, docs/selfhost-emit-20261004.md) no longer needs the JVM `kir-dump`, and can that
image rebuild itself byte for byte? Labels: **M** measured here, **E** estimate. The host was loaded (1-minute load
11-40), so no time on this page is a result. Stage-0 (`build/native-image/amu-native`, sha256 `d2cb84f6`) is used only
as the BOOTSTRAP-REFERENCE oracle of the parity run.

## 0. Result

| | measured |
|---|---|
| image | `build/frontsrc/two/amu-one-src`: 4,969,856 B Mach-O (sha256 `8c88619b`), guest code 4,745,816 B, libSystem only, wires 3,35,37,38,39 (never 20) |
| frontend | 33 modules, 64,457 lines (kotoba.form, frontend.{base .. desugar .. analyze}, kotoba-sema `c2e1343` = agent/walls-arena-f64 at /private/tmp/wt-WALLS-sema, plus their requires) + `seed/amu-front/check.cljk`: every one compiled from source by the seed (separate mode, `--emit-module`). **No kir-dump, no JVM, node or nbb at any step** |
| what unblocked it | the compiler's pair arena: `frontend.desugar` traps `:budget/cells :pairs` at 4 Mi and compiles at 16 Mi (`SEED_PAIRS=16777216`, now the default of `scripts/seed/selfbuild.sh` and of the build below). Nothing else: r6j compiles the whole closure as is |
| self-rebuild | **byte-identical**: `one1` (objects, link and extract by the r6j seed `4b2498ec`) -> `two` (all 53 objects, `modules`, `link`, `extract-native` by one1's own seed driver) -> `three` (by two): objects (sha of list `3ca5da13`), kseed `8a3f338e`, code `62ce87cf`, command `8c88619b` equal in all three. Entry: `seed/frontsrc/amu/main.kotoba` = seed/amu-main's dispatcher + `link`/`modules`/`extract-native` routed to the linked seed driver (request filed to adopt them) |
| `check` (391 corpus programs vs stage-0) | **320 same verdict + line + exit** (293 SAME-OK, 27 SAME-REFUSE), 1 exit status only (`w1-denial-ceiling`, 65 vs 70, as amu-one), **70 AMU-TRAP**, 0 OK-DIFF, 0 REFUSE-DIFF |
| the 70 traps | **all 70** stop at `__r6-trap` (pc located with a SA_SIGINFO copy of the loader; the 3 instructions before it are the TAB bounds check of `(vector-at [0] 1)`): a keyword made at run time (the frontend reading `:alpha` of the checked program) has no text in the seed's static keyword table. Repro: `(keyword-name (keyword-from-string (string-concat "al" "pha")))` traps with r6j. Seed work, filed (CONTRACT-REQUESTS 2026-10-04 FRONTSRC) |
| `compile` (aarch64-macos) | 264 of the 315 programs stage-0 compiles BEHAVIOUR-SAME; export runs 646 SAME, 0 DIFF, 5 MISSING; 47 AMU-REFUSES, 23 AMU-ACCEPTS, 53 BOTH-REFUSE, 4 BOTH-OK-DIFF (amu-one: 263 / 645) |
| no host process | `scripts/seed/frontsrc/test.sh` T6: check, compile crc32 and a link under the exec interposer with an empty PATH: 3 interposer loads, 0 exec/spawn/system/popen, 3 supervisor forks |
| tests | `scripts/seed/frontsrc/test.sh build/frontsrc/two/amu-one-src`: **7/7 PASS** (check ok, 2 refusals, usage 64/64, compile crc32 byte-identical to the seed's kseed + its test export rc=0, modules/emit-module/link/extract-native of a 2-module project exits 42, no host process) |

So the frontend half of rule 11 holds for `check`'s analysis: the native code AND the input of every frontend byte now
come from source through the seed, and the image reproduces itself. It is not yet 100%: 70/391 programs trap on
keyword texts (seed), `refactor` is still the declared stub, compile writes kseed/v1 (CMD), the check driver is
`check.cljk`'s single-namespace analysis (no project route, no `--policy`), packaging still uses cc + the C loader, and
the module list (reach-twins, farm, closure) is prepared by python (BOOTSTRAP-TOOL, labelled).

## 1. Reproduce

```
zsh scripts/seed/frontsrc/build-one-src.sh build/frontsrc/one1                                  # by the r6j seed
zsh scripts/seed/frontsrc/build-one-src.sh --builder build/frontsrc/one1/amu-one-src build/frontsrc/two
zsh scripts/seed/frontsrc/build-one-src.sh --builder build/frontsrc/two/amu-one-src build/frontsrc/three
cmp build/frontsrc/one1/amu-one-src build/frontsrc/two/amu-one-src && cmp build/frontsrc/two/amu-one-src build/frontsrc/three/amu-one-src
zsh scripts/seed/frontsrc/test.sh build/frontsrc/two/amu-one-src
AM_SEED=build/float/seed-1.bin zsh seed/amu-main/parity.sh build/frontsrc/parity --check build/frontsrc/two/amu-one-src --compile build/frontsrc/two/amu-one-src
```

Inputs: git HEAD's seed/ (archived; `882c6e0d7`, r6k sources) and its split, the committed seed/amu-main and
seed/amu-front, the module list of build/walls/{reach,cp}-walls.txt (INTEGRATE's), `amu-one-src.info` records every
root's head and dirty count. The builder seed is r6j's recorded seed (r6k is not recorded yet): its objects and the
r6k split's objects are equal (one1 == two), so the fixed point already holds at one1.

## 2. Walls measured on the way (selfbuild scan, r6j, 16 Mi pairs: 113 / 138 modules OK, was 109)

- `kotoba.compiler.capability-names` E2119 (a `#?(:clj .. :cljs ..)` function with no `:default` has an empty body
  on the Kotoba reading): fixed in amu src (`:default` clauses, no change on clj/cljs). Next: E2102
  `sema/capability-id->name`, which stage-0 refuses too ("constant alias must name a declared constant"): kotoba-sema's
  Kotoba reading of kotoba.sema drops the capability defs. SOURCE wall (kotoba-sema owner + a typed capability-names).
- `kotoba.compiler.project` (1,979 lines): after a scratch `#( )` rewrite (34) and 2 regex literals, E1005 quote
  (109 quoted symbols) plus atoms: a host-dynamic module that needs a port, not a reader patch. Not on amu-one-src's
  path (check.cljk analyzes one namespace).
- These two gate the product entries `nbb.check-cli` / `nbb.aarch64-cli`, which still have no Kotoba `main`.

## 3. Open risks

- 70/391 check programs trap until keyword texts exist at run time (seed); the fix touches the keyword representation
  or the loader context, so it may move every image's bytes (a new rung).
- The entry with the three build routes is a copy (seed/frontsrc/amu/main.kotoba) until seed/amu-main adopts them.
- Parity is one stage-0 run per file and single representative argument vectors (as seed/amu-main).
- Inputs are live worktrees of other repositories (heads recorded, not content hashes).
