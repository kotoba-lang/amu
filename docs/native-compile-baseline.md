# Native compile baseline: selfhost, Embench, public CLI

Tracking: [AWAI-66](https://linear.app/kotobalabs/issue/AWAI-66),
[AWAI-64](https://linear.app/kotobalabs/issue/AWAI-64),
[AWAI-24](https://linear.app/kotobalabs/issue/AWAI-24).

Use one qualified Amu-produced compiler identity for compiler self-rebuilding,
all 19 Embench workload builds, and public `amu compile` / `kotoba compile`.
Keep the complete project, import, lock, Definition-CID, target, capability,
resource and named-refusal contracts. The native-only owner contract in
[selfhost-priority](selfhost-priority.md) applies to the entire build,
materialization, packaging and execution closure. This document does not
qualify an artifact or enable a gate.

## Existing evidence to preserve

The [59-module native CLI record](evidence/native-selfhost-closure-20261019/README.md)
records actual self-rebuilding and G2=G3 identity. Its execution uses a C loader.
The [M105 seed record](evidence/embench-xgboost-width2-20261017/selfhost-rebuild-report.json)
records G1=G2=G3 for a different, 16-module compiler closure.
The [M104 Embench reproduction package](../bench/embench/reproduce-20261015/README.md)
pins a third compiler/source round and all 19 workload sources and artifacts.
Keep the separate compiler hashes and generation relations; do not combine
these receipts into a new full-product or C-free result.

The former [C-free interpreter spike](../scripts/seed/cfree-runner-spike/README.md)
produced a raw image through a C-loader-hosted builder. Its separate addition
evaluation used a JVM interpreter. Preserve both measurements without treating
them as a standalone compiler. Current native implementation remains open.

## Lock-aware check is not lock-aware compile

The combined `kotoba.compiler.selfhost-cli` delegates semantic/project commands
to `native-cli` and build commands to `seed/main`. The latter has no
`--module-lock` or `--blocks` parser in this source snapshot. Its positional
parser can consume the source and `--output` while leaving trailing lock
arguments uninterpreted. Such a result cannot establish compilation of the
requested pinned graph.

The [pure dispatch module](../src/kotoba/compiler/selfhost_route.kotoba) makes
the boundary explicit:

| Request | Route |
| --- | --- |
| `check`, `check-entry`, other project commands | Existing native project CLI; its own argument validation still applies |
| `modules` with lock/block options | Native project resolver |
| `modules` without lock/block options | Existing seed build-order listing |
| `compile`, `compile-kir`, `link`, `extract-native` without lock options | Existing seed builder |
| Those four builder commands with lock/block options | Exit 65, `E-SELFHOST-LOCKED-BUILD`, before entering the builder |

The scanner recognizes both separate lock options and attempted `--name=value`
spellings. It does not interpret a known option's value as another option:
for example, `--output --module-lock` remains an output value at this boundary.
The selected command implementation still validates that value. A later real
lock option is still detected. This guard neither drops a lock nor changes the
original argv handed to a supported command. It adds no fallback and no
permanent restriction on the intended compiler: implement and qualify locked
compilation before replacing the explicit refusal.

## Required qualification

1. Build the complete canonical compiler and its required tooling with Amu
   selfhost. Record exact source/lock/Definition-CID pins and compiler/packager
   artifact digests. Linux CDCI artifacts are standalone loaderless
   `x86_64-linux-static` ELF; other targets need their own declared qualification.
2. Rebuild the same complete pinned graph through successive compiler
   generations. Compare the declared fixed-point generations and actual
   artifacts. Preserve positive/refusal/resource/authority coverage and the
   exact process/build/packaging provenance, with no forbidden host dependencies.
3. With that compiler, compile all 19 complete Embench workloads and execute
   their original correctness and accounting checks. A workload subset or
   renamed target is insufficient. Performance needs separate quiet-host
   evidence; compilation alone supplies no score.
4. Use that same compiler identity through public `amu compile` and
   `kotoba compile` on real locked imports. Run missing/tampered/stale lock and
   source-path, unsupported target, policy and resource refusals. Do not remove
   options or shrink the public API to make the build pass.
5. Review and merge only after those required native runs. Record merged source,
   produced artifacts, runtime qualification and deployed state separately.

The [compile-route fixture](../test/fixtures/selfhost/compile_route.kotoba)
contains six test exports covering 72 route decisions, including all four
builder commands, locked `modules`, missing/inline lock forms, option values
and lock-like filenames. Each `test-*` must return 1; `main` must return 0.

Also execute the newly built combined CLI, not just that pure fixture:

- For each of the four builder commands, append `--module-lock /missing/lock`
  and separately `--blocks /missing/blocks` to a normal source/output invocation.
  Require exit 65 and `E-SELFHOST-LOCKED-BUILD`; the output path must remain absent.
  Repeat with inline forms and with the lock option missing its value.
- Confirm locked `modules`, `check` and `check-entry` retain the original
  locked-project success and missing/tampered-block refusals. Their diagnostics
  must not be replaced by the locked-builder diagnostic.
- Keep unlocked builder output, exports, target and named-refusal parity, and
  verify argv values that look like lock options do not trigger the guard.

These new sources and cases have not been compiled or executed through a
qualified native compiler. The fixture is not registered with a historical
C/JVM/Node runner. Do not count source checks, an unrun corpus, a missing CI
registration or this guard as completion of the native compile baseline.
