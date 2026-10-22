# Seed bootstrap lineage: reproducing every rung from the committed R0 seed (2026-10-02)

Owner HOUSE. `scripts/seed/bootstrap.sh` rebuilds the whole seed lineage from one committed binary and checks every
fixed-point hash that `seed/rungs/*.record` recorded. After the C loader (`tools/kexe_loader.c`, built by `cc`) is
built, only the loader and the seeds run: no node, JVM, nbb, or stage-0 (the optional `--stage0-r0` route is the one
exception and is labelled BOOTSTRAP in its output). Gate G5 covers the same property for the packaged seed.

## What is committed

| file | content |
|---|---|
| `seed/bootstrap/seed-r0.bin` | the R0 seed (fixed point of the R0 sources), 187,186 bytes, sha256 `fe2c20aefa02f4f91f5b8394c8ad8a31e75325242050aaf7964b0eab73a39dd6` |
| `seed/bootstrap/seed-r0.offset` | `0` (offset of `main`, as `extract-native` prints it) |
| `seed/bootstrap/SHA256SUMS` | checked first by `bootstrap.sh` (`shasum -a 256 -c`) |
| `seed/rungs/rN.record` | per rung: `unity_commit` (the git commit whose `seed/MANIFEST` sources are the rung), `unity_sha256`, `seed1_sha256`, `seed1_bytes`, for a rung whose sources use their own new language also `bridge_commit` and `bridge_sha256`; plus the gate table and the Embench timings |

The binary is the same bytes as `fe2c20ae...` in `r0.record` (`seed1_sha256`). It is a build artifact kept in git only so
that the chain has a root that needs no JVM; it is 0.19 MB and is replaced only by a new, reviewed R0-style root (never
by a rung).

## The chain

For each record in rung order the seed built so far compiles the rung's unity source (rebuilt from git, not from the
working tree), then the result compiles it again:

```
seed-r0.bin (committed)
  r0: compile(unity of c23ff79ab, 4840 lines)         = seed-r0.bin               (R0 is its own fixed point)
  r1: bridge  = seed-r0 compile(unity of 69b32c614)   = 0f6497a3..., 296,168 bytes (R1 features written in the R0 language)
      seed-1  = bridge  compile(unity of 9daea87db)   = c0526b73..., 291,392 bytes
      seed-2  = seed-1  compile(unity of 9daea87db)   = seed-1                     (fixed point, == r1.record)
  head: seed-A = seed-r1 compile(working tree unity); seed-B = A compile; seed-C = B compile;  A == B == C
```

Why a bridge: from R1 on the seed sources are written in the language the rung adds (`case`, `->`, `when`, records);
the previous seed cannot read them. The bridge unity is a commit whose sources use the new features' implementation but
are still written in the previous language, so the previous seed compiles it into a seed that understands the new
language, which then compiles the real sources. A rung that needs no bridge simply has no `bridge_*` lines.

## Running it

```
zsh scripts/seed/bootstrap.sh                 # every recorded rung, then the head (the working tree); about 3 s
zsh scripts/seed/bootstrap.sh --no-head       # recorded rungs only (the committed lineage; no working tree involved)
zsh scripts/seed/bootstrap.sh --upto r1
zsh scripts/seed/bootstrap.sh --commit C      # head unity from commit C
zsh scripts/seed/bootstrap.sh --stage0-r0     # also the stage-0 routes below (about 37 s, one stage-0 compile of ~30 s of it)
```

Work directory: `build/seed-boot/` (`SEED_BOOT`; it must lie under the wire-35 scope, the repository). Every stage prints
bytes, sha256 and seconds. Exit 0 only when every recorded hash is reproduced (unity sha256 of the git sources, bridge
sha256, fixed point seed-1 == seed-2, seed-1 sha256 and size) and the head is a fixed point. The head hash is compared
with the last record and reported as "differs" when the sources moved on; it is never an error, because the next rung's
record is what pins it (`scripts/seed/gates.sh --rung rN` then `scripts/seed/rung-report.sh --record rN --commit C
[--bridge B]`).

Measured on 2026-10-02 (load average 30-50): the whole chain r0, r1 and head (8 seed compiles of 4,840 to 7,300 lines)
takes 2.7 s of wall time; with `--stage0-r0` 37 s.

## The stage-0 routes (`--stage0-r0`): where the lineage came from

The committed binary is also reproducible from the bootstrap-reference compiler (the JVM-built native image
`build/native-image/amu-native`, never in the seed's runtime path):

1. R0: stage-0 compiles the unity of `c23ff79ab` (4840 lines) to `seed-0` (146,455 bytes, a different binary: another
   code generator); seed-0 compiles the same unity to `seed-1`; `seed-1` is byte-identical to `seed-r0.bin`
   (`fe2c20ae...`). Measured, both with the native `extract-native` and with `SEED_EXTRACT=py`.
2. R1: stage-0 compiles the bridge unity of `69b32c614` (7,331 lines) itself (220,775 bytes, `38adac41...`, differs from
   the seed-built bridge `0f6497a3...`); that bridge compiles the unity of `9daea87db` to `c0526b73...`, the same
   fixed point as the seed-built route. So the R1 seed is independent of which compiler built its bridge.

Stage-0 cannot build the R1-language unity itself ("EDN value contains too many nodes" at decode, measured), which is
why the lineage continues from seed binaries only.

## Stage-0 extract limit (build.sh)

Stage-0's `extract-native` refuses a kexe with more than 200,000 EDN nodes (`bounded_edn.cljk` max-nodes; the `:code`
vector has one node per code byte), which a seed unity of about 5.5k lines exceeds. `scripts/seed/lib.sh`
(`seed_stage0_build`, used by `build.sh 0`, `unit.sh` and `bootstrap.sh --stage0-r0`) now falls back to
`scripts/seed/kexe_code.py` (BOOTSTRAP-TOOL: reads `:code` and the symbol offset from the kexe directly) when
`extract-native` answers "too many nodes". `SEED_EXTRACT=py` forces it, `SEED_EXTRACT=native` forbids it. Measured: on
the R0 `seed-0.kexe` the output is byte-identical to `extract-native` (146,455 bytes); on the 7,331-line bridge unity
(compile succeeds, extract-native refuses) the fallback produces a working bridge (see route 2). The stage-0 limit
itself was not changed (it is in stage-0's Clojure source, outside the seed's paths).

## Error table gate (ERR)

`scripts/seed/errors-check.py` (a row of `gates.sh`) compares `seed/HEADS :errors` with the text tables of
`seed/90-drv.kotoba` and with the error codes the modules define locally. First run found 13 gaps; now 65 codes agree:
HEADS gained E1201-E1204 (12-kirread), E4202-E4205 (42-layout), E5002 (50-out) with their constants
(E-KIR-DOC/FIELD/VALUE/HELPER, E-LAYOUT-FIXUP/TARGET/EXPORTS/SIZE, E-OUT-NOSYM; `gen-ns.sh` regenerated `00-ns`), and
the driver prints the texts of E2125-E2128 (before: the code with an empty text). Delimited table-only change in 90-drv.
The seed built from those sources has golden refusal texts for 7 programs that changed from an empty text to the text
(`seed/tests/golden/refusal-r1.txt`, reviewed: only those 7 lines differ from the output of the tagged seed).

## Open risks

- The loader is the working tree's `tools/kexe_loader.c` for every stage, not the loader of the rung's commit; a
  loader change that alters guest behaviour would show up as a hash mismatch (none so far).
- `bootstrap.sh` needs `git` history for `unity_commit` / `bridge_commit`; a shallow clone must fetch those commits.
- A new rung is not "in the lineage" until its record exists; between records the head step is the only check.
