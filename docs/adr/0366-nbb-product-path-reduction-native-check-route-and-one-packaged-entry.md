# ADR 0366 — nbb product path: a native `check` route, one packaged native entry, flags measured by reachability

- Date: 2026-10-04 (agent BOUNDARY)
- Status: Accepted. Reversible per part (each part below is one revert).
- Related: docs/selfhost-priority.md rules 8-11; docs/selfhost-bootstrap-boundary-20261001.md (snapshot 56);
  docs/selfhost-status-20261004.md 2.8 (58, +2 from 15d9fcccf: `check_cli`, `aarch64_packaged_cli`);
  seed/amu-front/README.md (the native check, 382/391); ADR 0365 (the opt-in seed backend).

## Context

Rule 10: the PRODUCT counts of `scripts/selfhost-wall/bootstrap-boundary.sh` must not grow. They grew 56 -> 58 when
15d9fcccf split the minimal reach set into `nbb/check_cli` and `nbb/aarch64_packaged_cli`, two nbb entries with no
`:kotoba` reading. Since then a native check exists (`build/compose/amu-front`, the kotoba-sema frontend compiled by the
seed; no node/nbb/JVM in its process tree, measured by COMPOSE). The question was which of the two entries can leave the
product path now, what the native route can carry, and how to keep the count honest.

## Decision

1. **Retire `nbb/aarch64_packaged_cli`.** Its two targets (`aarch64-linux-static`, `aarch64-aiueos-kernel-v1`) are served
   by `nbb/x86_64_cli`, which already carried the ELF64 / PE32+ / linux-static packagers; it now picks the ISA emitter
   from the target's backend (AArch64 only for those two names, any other AArch64 target is refused by name and stays on
   `nbb/aarch64_cli`, whose closure still has no packager). bin/amu, bin/kotoba and scripts/test-linux-static-handlers.cljk
   route the pair there. The packagers remain in exactly one entry's closure.
2. **A native `check` route, opt-in.** `AMU_FRONT=<absolute path of amu-front>` makes bin/amu answer
   `amu check <one file>` (no flag: one module, the default no-grant policy) by spawning that binary alone, with
   `check <absolute file>` and an empty environment. Its report is `amu check`'s HUMAN line (stdout `ok profile=..
   effects=.. exports=..`, exit 0; refusal on stderr, exit 65), the stage-0 JVM CLI's default, NOT the EDN the nbb route
   prints (definition CIDs and the admission record are not computed natively). Any other `check` (`--source-path`,
   `--policy`, `--package-lock`, `--json`, ...) stays on nbb. A native run that neither accepts nor refuses (trap, budget,
   a file outside the binary's baked wire-35 scope: exit 66) is exit 70 naming the bootstrap route: never a silent
   fallback in another format. Unset, nothing changes.
3. **`;; bootstrap-tooling` is a measured claim.** Three src files that no launcher route loads are flagged:
   `kotoba/compiler/cli.cljk` (the JVM CLI: main of the BOOTSTRAP-REFERENCE stage-0 native image),
   `lang_conformance.cljk` and `lang_native_conformance.cljk` (conformance runners used by tests only). Reachability:
   the host require closure (every reader branch) of every `src/kotoba/compiler/nbb/*_cli.cljk` over the launcher's
   locked classpath (`reach-minimal.py --full --host`): 95 src files reached, none of these three; no
   `requiring-resolve` names them. Four further unreached files (`fuel_estimate`, `host_profile`, `ipld_adl`,
   `value_codec`) are product LIBRARIES not yet wired to a command, so they are NOT flagged.
4. **Gate.** `scripts/selfhost-wall/boundary-gate.sh`: EFFECTIVE union = the boundary union + every flagged src file a
   launcher route still reaches (counted back as PRODUCT and listed); PASS needs effective union <= 55 and nbb entries
   <= 16. Ceilings only move down, in the commit that lowers the count.

## Measurements (2026-10-04, this worktree; no timings are claimed)

| | before | after |
|---|---:|---:|
| bootstrap-boundary.sh PRODUCT union | 58 | **54** |
| boundary-gate EFFECTIVE union (+ flagged-but-reached) | 59 (derived: seed_backend was already flagged and reached) | **55** |
| nbb-only entry points (`nbb/*_cli.cljk`) | 17 | **16** |
| src files with unguarded host tokens | 13 | 10 |

- The gate found one flagged file the launcher reaches: `nbb/seed_backend.cljk` (ADR 0365, `;; bootstrap-tooling`, required
  by `nbb/cli` under `#?(:cljs)` for every native compile). It is counted back; that is why the effective union is 55, and
  it is filed in seed/CONTRACT-REQUESTS.md. Break-it: flagging `nbb/x86_64_cli` leaves the effective union at 55 (53 + 2).
- Part 1, byte for byte against the previous route (probe program, sha256 of artifact + provenance + compile report):
  aarch64-linux-static, aarch64-aiueos-kernel-v1 (object and `--artifact image`), aarch64-macos, x86_64-linux-static
  identical; `amu worker --target aarch64-linux-static` artifact identical; `extract-native` ok.
- Part 2: the 19 Embench ports, `AMU_FRONT=build/compose/amu-front bin/amu check` vs the nbb route: 19/19 same exit status
  and same export list. scripts/test-native-check-route.mjs 16/16 (rule, fake binary: argv, empty environment, 0/65/70;
  real binary: one accepted, one refused). scripts/test-amu-launcher.mjs passes.

## What this does not do

- `check_cli` stays PRODUCT: the native check covers one file under the default policy, misses 9/391 corpus programs
  (seed/amu-front/README.md section 3), prints the human report only, and stops at ~248 KB of source (pair arena; agent
  ARENA). It can be flagged once amu-front covers `--source-path`, `--policy` and `--json` and a differential through
  bin/amu over the whole corpus agrees; then the route becomes the default and `check_cli` a bootstrap reference.
- No packaged compile runs natively: the seed emits aarch64-macos only; the linux-static and aiueos packagers have no
  Kotoba/seed implementation yet. Part 1 removes an entry, not the nbb dependency of those two targets.
- bin/amu itself is still node (4 launchers stay PRODUCT): on the native route the process tree is node (launcher) +
  amu-front, without nbb. Rule 11 needs a native launcher.
