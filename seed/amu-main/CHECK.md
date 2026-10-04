# `amu check` beyond one namespace and the default policy (agent CHECKFULL, 2026-10-04)

Question: does the native `amu check` answer `--policy`, `--profile` and `--source-path` as stage-0 does, from source,
with no node, nbb or JVM? Labels: **M** measured here, **E** estimate. Oracle: stage-0 `build/native-image/amu-native`
(sha256 `d2cb84f6`, BOOTSTRAP-REFERENCE), never in an amu image's process tree. Host load 15-60 during every run, so no
time on this page is a result.

## Layout

- `src/amu/check_full.kotoba` (ns `amu.check-full`): the command. Stage-0's order and texts (cli.cljk "check"): argv[1] is
  the source; `--policy` read as bounded EDN (bounded-edn read-file: regular file, 8 MiB, UTF-8, the preflight scan, one
  form, the value walk) and canonicalised (capability-names/wire-policy: catalog names to wire ids, stage-0's id table
  measured: 1..42 named, 35 also `:fs/app-data-bytes`); `--profile` over the policy's `:language-profile`; the frontend's
  `analyze` (FRONTSRC objects, from source); the capability half of admission (malformed keys / `:allow` / members,
  missing grants with catalog names); refusal exit statuses by the error's phase (cli/exit-code). `--source-path`: the
  project route over kotoba-lang's guest twins `kotoba.compiler.project-files/load-closed-graph` and
  `kotoba.compiler.project/link-source` (agent WALL2, branch agent/wall2-project-twin 965c5f5), then the frontend over
  the linked unit with `:admit-linked-synthetics?`, refusals attributed to the module's file, ` modules=[..]`.
- `k/amu/check.kotoba` (ns `amu.check`): `run` = `amu.check-full/run` (was seed/amu-front/check.cljk's `main`).
- `src/amu/cli.kotoba`: UTF-8-safe `ends-with` / `basename` (code-point walks; the byte walks trapped on `é.txt`) and
  `readable` (wire 35 EXISTS, which answers "0" outside the loader's scope instead of trapping); `regular-file` /
  `directory` ask it before STAT, so a path outside the scope reads as absent, never SIGILL.
- `src/amu/refactor_io.kotoba`: `kind` asks EXISTS before STAT (same reason); `write-file` writes content that holds
  the text `WRITE_SEP` / `APPEND_SEP` in pieces (WRITE then APPEND, cut one byte into each token), which the loader's
  single-occurrence rule refused with SIGILL.

## Results (**M**)

Image `build/checkfull/unified/amu` (scripts/seed/launcher/build.sh --worktree, LAUNCHER_REFACTOR = kotoba-lang
agent/refactor-cst-twin 289d718, --front build/checkfull/front = WALL2's r6l object closure incl. kotoba.sema and the
project twins; seed r6l 54b87cf6): 6,043,128 B, code 5,819,016 B, sha256 `994fb5ed`, libSystem only, wires 3,34,35,37,38,39.

| suite | result |
|---|---|
| corpus, `check <f>` (391 programs, parity.sh's dirs) | 358 SAME-OK + 33 SAME-REFUSE = **391/391** (exit status too; w1-denial-ceiling 70 now) |
| corpus, `--policy` grants 35,37,38,39 | **391/391** (359 / 32) |
| corpus, `--policy` naming all 42 catalog capabilities | **391/391** (366 / 25) |
| `seed/tests/checkfull/diff.sh` (37 argument cases + 31 policy files x 4 programs) | 150 SAME + 9 SAME-NORM (set order, span) + 5 DECLARED + 9 STUB, 0 DIFF |
| `graph.sh` on WALL2's 17 trees, with and without `--policy` | **34/34** byte-identical |
| `graph.sh` on `seed/tests/checkfull/proj` (9 trees x 2) | 14 SAME, 4 DIFF (the twin does not attribute a refused qualified call to its module: request filed) |
| `launcher/test.sh` | L1 34 SAME + 3 DECLARED, L2 Embench 19/19 (114 runs, 19 seals), L3 0 exec/spawn, L4 PASS |
| `refactor/all.sh` (code with the new refactor_io, seed r6l) | 0 differ in 10 suites (args 31 .. verify 5) |
| `refactor-writesep.sh` (6 files holding the tokens) | 6/6 SAME as bin/amu (answer, status, file); HEAD's image: SIGILL |

STUB (69, never counted): `--source-path` with a relative entry or root (no cwd: the loader has no wire 40 provider),
`--json`, `--module-lock`, `--package-lock`, a policy with `:abac` / `:attributes` / `:information-flow` / `:crypto-*` /
`:hardware-signing-*` keys that would otherwise admit. DECLARED: `--jvm-free` before the source (bin/amu drops it), a
policy that is not a map. Not reproduced: the effect-classification refusal, Clojure-only EDN spellings (`\c`).

## Reproduce

```
zsh seed/tests/checkfull/build.sh                       # test image (check only) on build/rebuild/one1/o
CF_FRONT=build/wall2/graph-run/o zsh seed/tests/checkfull/build.sh build/checkfull/tp   # + the project twins
zsh seed/tests/checkfull/diff.sh build/checkfull/tp/amu build/checkfull/d
zsh seed/tests/checkfull/graph.sh build/checkfull/tp/amu build/checkfull/g build/wall2/graph seed/tests/checkfull/proj
zsh seed/tests/checkfull/corpus.sh build/checkfull/tp/amu build/checkfull/c [seed/tests/checkfull/fx/corpus-policy.edn]
zsh seed/tests/checkfull/refactor-writesep.sh <rf-prefix> build/checkfull/ws    # rf-prefix: scripts/seed/refactor/lib.sh rf_compile
```

`bin/amu check` (nbb) prints the `:kotoba.check/v1` EDN map, not stage-0's human line; this command follows stage-0, as
seed/amu-main/LAUNCHER.md does. WALL2's `nbb.check-cli` Kotoba entry is the native route of the nbb contract.
