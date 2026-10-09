# Seed 17 continuation: r6m image and acceptance evidence

Measured 2026-10-04 JST on `codex/seed17-continuation`, based on
`agent/dual-runtime-port` at `a93ee4068`. This continues the finished wave's
partially written local work; it does not claim that workflow `wf_fec5ab0e-474`
completed all four assignments. The remote branch still ends at that base,
and the recorded seed remains `seed-r6m`. No `seed-r6n` record was found.

## Rebuilt image

The recorded r6m seed is
`8d3338e10668997e5d74c9a7b49b14af58f65e7e44f62ee7f3cb13b4ade9b796`
(787,232 bytes). The unified image uses 162 objects, including 117 frontend
objects. It includes the source-built frontend, check/project route, seed
compiler and Kotoba refactor library.

The command is 6,043,128 bytes, SHA-256
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`.
All three generations have byte-identical objects, containers, native code
and commands. Generations 2 and 3 compile the complete selected frontend
again through the preceding image's `compile`; they also perform modules,
link and extract-native through that image. The initial generation's
frontend was independently rebuilt from source with the recorded seed and
matched. A separate invocation of `scripts/seed/image/rebuild.sh`, with a
second copy of the snapshotted inputs, reproduced the same command and its
three-generation fixed point.

Native-code SHA-256:
`7aece28711a55b176cf47399a0fef1be67acaad301fe8d58a70f7ad1579263cf`.
Container SHA-256:
`3209d03c099532384ba40ebccb9eafa0fbfe754d58930c33388f45c306c21531`.

## Behaviour

| Check | Measured result |
|---|---|
| check, no policy | 391/391: 358 accepted and 33 refused, matching verdict/text/exit |
| check, grants 35/37/38/39 | 391/391 matching verdict/text/exit |
| check, all catalog capabilities | 391/391 matching verdict/text/exit |
| compile corpus | 300 BEHAVIOUR-SAME; 12 AMU-REFUSES; 27 AMU-ACCEPTS; 49 BOTH-REFUSE; 3 BOTH-OK-DIFF |
| export runs | 875 SAME, 15 DIFF, 0 TIMEOUT; one additional MISSING export |
| kexe seals | 330 valid |
| Embench correctness | 19/19, 114 export runs, 19 valid seals |
| launcher arguments | 34 SAME, 3 DECLARED, 0 DIFF |
| project trees | 48/52 SAME (17 WALL2 trees × 2 = 34/34; 9 CHECKFULL trees × 2 = 14/18) |
| process interposer | six command runs; six loaded probes; six supervisor forks; zero exec/spawn/system/popen |
| static dependencies | libSystem only; grants 3,34,35,37,38,39 |
| product inventory | unchanged: four launchers, 16 nbb entries, 58 PRODUCT files |

The 15 DIFF export runs return closure handles (the reference prints `2`,
the image prints `1` in the inspected cases); handle identity is still a
difference, and no closure invocation equivalence is inferred from this
comparison. The missing export is `->Reading` in
`typed_defrecord_fields`. The 27 AMU-ACCEPTS are additional acceptance where
the reference refused; they are recorded, not promoted to reference parity.

The four project differences are the missing/private qualified-call
diagnostics, each with and without a policy: the reference prints
`main.kotoba`, whereas this image prints its absolute path. Exit codes and
refusal messages agree, but the output is not byte-identical.

Reference compiler: `d2cb84f6e7934a638ae928342e13e96a34d13aa66a3f0170fb91cabf3c5e68e2`,
BOOTSTRAP-REFERENCE, used only by the differential harness. No reference
compiler enters the native image's process tree. Host load was above 30
during qualification; no timing is published as a result.

## Acceptance and remaining work

`scripts/seed/prove-100.sh` runs the image's correctness, refusal, fixed-point
and process checks and preserves PASS/FAIL rows. Full compile parity is a
mandatory separate row: 300 equal programs never pass that full gate.
Historical seed gate records are not substituted for image results.

The image remains below 100%:

- The product still enters through Node/nbb `bin/amu`.
- The source-built product `check-cli` and `aarch64-cli` entry objects are
  absent from this image. The selfbuild scoreboard remains 120/138; this
  continuation does not claim to have resolved `nbb.cli`.
- Twelve compile refusals, closure-handle differences, a missing constructor
  export and the additional accepts remain in the corpus.
- Relative `--source-path`, JSON, locks and some policy modes still report
  declared/stub results. The negative suite records them explicitly.
- `refactor verify` remains a named stub; process wire 20 is not granted.
- The strict exec tracer failed closed: `sudo -n dtruss` requires a password.
  The successful dyld interposer is supplementary evidence, not rule 11's
  complete own-source execution trace.
- Quiet Embench timing is now recorded separately in
  `docs/embench-asher-20261004.md`; it does not close the product-entry or
  own-source execution gates above.

The trace wrapper now fails if it captured no exec events. A simulated
tracer returning success with an empty log was tested and returned exit 2.
The build glue's dependency order was corrected: `project` must compile
before the updated `project-files` which requires it. These are build and
verification changes, not repeated compiler-source refactors; no AST
refactor rule covers them.

Next source work is an AST rule for the 22 anonymous-function literals in
`nbb.cli`, followed by the product `main` entries and a new source scan. The
unfinished Python text-rewrite helper from the wave was not adopted. Wire
40 and the r6n language work also remain separate unfinished tasks.

## Saved evidence and reproduction

Evidence is in `docs/evidence/seed17-continuation/`. `inputs.tgz` preserves
the actual external source trees and scan objects; repository heads alone
were insufficient. Archive SHA-256:
`a49343762c38ed4d92d6dc57b4d0661abc0894bcfc5bd9ee2dbfacacb9bfc136`.
The original input manifest SHA-256 is
`54cf77edc1750b2f05f7f83df83375dabf3964c962a4f97ec36ceb60080c7e9b`.
Original source-root heads and dirty counts are included in the archive.

From this branch, first reproduce the recorded seed (or use a binary whose
hash matches `seed/rungs/r6m.record`) at `build/seed-boot/r6m/seed-1.bin`.
Extract the archive into a fresh directory, then run:

```sh
mkdir -p build/seed17-snapshot
tar -xzf docs/evidence/seed17-continuation/inputs.tgz -C build/seed17-snapshot
zsh scripts/seed/image/rebuild.sh build/seed17-snapshot/inputs build/seed17-replay-new
zsh scripts/seed/prove-100.sh build/seed17-replay-new/g3/amu build/seed17-replay-new
```

The build wrapper rebases path metadata and hashes the copied inputs before
building. A different checkout path changes the baked filesystem scope and
therefore the command hash; all three generations within that build must
still agree. On this Mac native execution needs permission to initialize
the loader's own macOS sandbox. The proof's reference gates additionally
require the pinned bootstrap reference, Embench checkout and exec probe;
their absence produces failures, not passes.
