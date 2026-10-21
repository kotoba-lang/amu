# scripts/gate: the selfhost acceptance gate

The full description is in `docs/selfhost-gate.md`. The exact command lines follow.

Run every command from the root of an amu checkout that has the pinned nbb
engine (`npm ci --include=dev`, which installs `node_modules/nbb/cli.js`).

amu PR (amu mode, gates g0,g1,g2,s1,s2,s5). Every run needs a macOS arm64 node with `cc` and `git`, because
the farm, S1 and S2 come from the seed tools (`seed/tools/bootstrap.kotoba`, `selfbuild.kotoba`):

```
node node_modules/nbb/cli.js scripts/gate/run.cljk \
  --repo <amu git dir> --base <ref|sha> --head <ref|sha> \
  --out <file.edn> [--work <dir>] [--cache <dir>] [--jobs <n>] [--keep] \
  [--kotoba-lang <kotoba-lang git dir>] [--kotoba-lang-ref <sha>] [--rung r6n] [--gates g0,g1,...] \
  [--lock <repo-relative lock; default seed/selfbuild/integration-lock.edn when the head has it, else deps-lock.edn>]
```

Library PR (consumer mode, gates g0,g1,g2):

```
node node_modules/nbb/cli.js scripts/gate/run.cljk \
  --repo <library git dir> --base <ref|sha> --head <ref|sha> \
  --amu <amu git dir> --amu-ref <amu sha> \
  --out <file.edn> [--work <dir>] [--cache <dir>] [--jobs <n>]
```

Outputs: `<out>` (EDN, `:format :kotoba.selfhost-gate/v1`), `<out>.json` and
`<out>.md` (the summary table, also printed to stdout). The work directory
keeps each side's `measure.edn`, farm and seed logs.

Exit status: `0` PASS, `1` FAIL, `2` the run could not complete. Treat every
non-zero status as a fail.

Pins: there are no pin files to pass. Every input is read from git at the
named commits and recorded in the verdict under `:pins`:

- the amu commit, and the sha256 and `:lock/digest` of its `deps-lock.edn`;
- the nbb pin from `package-lock.json`;
- the kotoba-lang commit (`--kotoba-lang-ref`, default `4d4d188b9c2da2e90d296588a5cc6dbce7a6d80d`), with the sha256 of `lang/selfhost-compiler-grant.edn` and a digest of `lang/compat`;
- the seed: rung, `seed-1.bin` sha256 (checked against `seed/rungs/<rung>.record`), the lineage loader sha256, the adopted seed sha256 and each tool's source and binary sha256;
- the farm: lock path and sha256, the sha256 of the tool's `inputs.txt` (every root commit and tree) and `order.txt`, and the module count;
- the gate's own commit and the sha256 of each of its source files.

`--kotoba-lang` defaults to `~/github/kotoba-lang/kotoba-lang`. That checkout
must contain the `--kotoba-lang-ref` commit. The farm reads the deps-lock
commits from `~/github/kotoba-lang/<repo>` or from `~/.gitlibs`, and the run
fetches them first with the amu dependency prefetch.

Other files:

- `test_gate.cljk` holds the unit checks: `node node_modules/nbb/cli.js scripts/gate/test_gate.cljk`.
- `report_status.cljk` posts a verdict as a commit status: `--verdict <file.edn> --repo OWNER/NAME [--context C] [--dry-run]`. It is optional. A runner that owns the status context does not need it.
