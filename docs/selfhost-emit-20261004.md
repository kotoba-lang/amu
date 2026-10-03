# One amu image with a real `check` and a real `compile` (agent EMIT, 2026-10-04)

Question: can a KIR-route object (the big frontend, `amu check`) and source-route objects (the seed compiler, `amu compile`)
be linked by the seed into ONE native image, so that one `amu` binary runs both commands for real? Labels: **M** measured
here, **E** estimate. The host was loaded (1-minute load 12-37 during the runs), so no time here is a result. Stage-0
(`build/native-image/amu-native`, sha256 `d2cb84f6`) is the BOOTSTRAP-REFERENCE oracle of the parity runs only.

## 0. Result

| | measured |
|---|---|
| new command | `seed compile-kir <in.kir> --emit-module --ns NAME --output X.kso`: a KSEEDO1 module object from KIR (90-drv EMIT block) |
| image | `build/emit/amu-one`: 3,401,208 B Mach-O (sha256 `5d25b6af`), guest code 3,190,746 B, libSystem only, wires 3,35,37,38,39 (never 20) |
| how it is built | 20 objects joined by `seed link`: `kotoba.amu-front.check` (frontend, 5,036,490 B object from 2,376,298 B KIR, large-M seed) + 14 seed split modules + amu.cli/refactor/compile/check/main (source route) |
| `check` | **real** (frontend analyze, KIR route): 390/391 corpus programs same verdict, report line and exit status as stage-0 `check`; 1 differs in exit status only (`examples/w1-denial-ceiling`, 65 vs 70). Same as amu-k |
| `compile` (aarch64-macos) | **real** (seed compiler from source, in-process): 263 of the 315 programs stage-0 compiles are BEHAVIOUR-SAME; export runs 645 SAME, 0 DIFF, 5 MISSING; 48 AMU-REFUSES, 22 AMU-ACCEPTS, 54 BOTH-REFUSE, 4 BOTH-OK-DIFF (the 5 missing exports). amu-s (r6f) had 262 / 644 |
| self-reproduction | `amu-one compile <seed unity>` writes a kseed byte-identical to the builder seed's own `seed-2.kseed` (742,066 B, sha256 `d0e402ec`) |
| no host process | under the exec interposer (build/seed/noproc/noproc.dylib, empty PATH): 4 runs (check ok, check refuse, compile crc32, compile the seed unity), 4 interposer loads, 4 supervisor forks, 0 exec/spawn/system/popen |
| `refactor` | still the declared stub of seed/amu-main (exit 69); not counted |

So one image now holds a real `check` AND a real `compile`. It is not yet the 100% of rule 11: the frontend's native code is
the seed's, but its KIR comes from `kir-dump` on the JVM-built classes (BOOTSTRAP-REFERENCE at build time); the frontend is
not compiled from source by the seed (walls: kir.interp floats, refactor, ...); `refactor` is a stub; `compile` writes kseed/v1
and accepts the seed's language, not the big frontend's.

## 1. The object (KSEEDO1) from KIR

The KIR program goes the compile-kir pipeline (kr-lex .. 42-layout at base 0, then `out-blob` instead of `out-build`) and is
written as 60-proj's separate-mode object: `N NAME`, `K 0 <empty union>` (the KIR route keeps keyword texts in its own groups,
no `__r6-kwtab`, no W line), no R line (a KIR program is closed), one `E` line per KIR export through 60-proj's own
`pj-iface-one` (clause offsets, stub template of the checked signature; a type that does not cross is E6017 by name), `L`
lines (literal loads), `X` lines, `C` lines. The text is written from one byte vector: 60-proj's `pj-object` builds a string
in 4 KiB accumulators, which for a 2.4 MB blob (4.8 MB of hex) would copy ~3 GB of string pool (**E**). Nothing in 60-proj or
12-kirread changed (owned by LET); 90-drv calls their functions. The split (seed/split) is regenerated: 12 60-proj helpers are
now public in `seed.proj` because `seed.main` calls them.

## 2. Tests

- `scripts/seed/emit/test.sh <seed>`: **5/5 PASS** (E1 object shape of seed/tests/emit/lib.kir; E2 a source entry linked with it
  runs, 0; E3 control answers 115; E4 3 usage refusals; E5 a refused KIR is refused identically with --emit-module).
- `scripts/seed/emit/same.sh <r6h seed> <EMIT seed>`: **87/87 cases byte-identical** (19 port KIRs, KIR pos/neg, 19 port sources,
  14 split objects, the seed unity + extract-native): the EMIT block changes no other command.
- Seed fixed points (lineage): HEAD `ebbf63f93` (r6i sources) + EMIT = `d1369677` (742,040 B); its large-M profile `1d1fe2c3`
  (742,048 B). The first build on r6h sources + EMIT was `200c6845` (740,856 B), also a fixed point. No rung is recorded for EMIT.

## 3. Reproduce

```
zsh scripts/seed/emit/build-one.sh                       # seeds, KIR (JVM, cached), objects, link, package -> build/emit/amu-one
zsh scripts/seed/emit/test.sh build/emit/b/seed-1.bin
zsh scripts/seed/emit/same.sh build/link/b/seed-1.bin build/emit/b/seed-1.bin
AM_SEED=build/emit/b/seed-1.bin zsh seed/amu-main/parity.sh build/emit/parity-check --check build/emit/amu-one
AM_SEED=build/emit/b/seed-1.bin zsh seed/amu-main/parity.sh build/emit/parity-compile --compile build/emit/amu-one
```

## 4. Open risks

- The KIR of the frontend is BOOTSTRAP-REFERENCE (JVM kir-dump, kotoba-sema `2d7d05d`, agent/f64-front, unmerged); the image is
  labelled so in `amu-one.info`.
- `amu-one` cannot rebuild itself: its entry requires `kotoba.amu-front.check`, which only exists as a KIR object.
- Cross-route calls are checked on i64/string signatures (tests) and on `main [] :i64`; records, keywords and closures across
  the KIR/source boundary are not exercised. Keyword texts: each route keeps its own table (K 0), not a link-wide union.
- The link image is 3.19 MB of 29.6 MB capacity; the build needs the large-M seed for the frontend KIR (TOK 655,360).
- Parity is single representative argument vectors (kbd_exports.py), as in seed/amu-main.
