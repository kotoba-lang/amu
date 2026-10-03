# ADR 0365 — Opt-in `--backend seed` on the native AArch64 route (bootstrap period)

- Date: 2026-10-03
- Status: Accepted (agent INT2, under the owner decision "in the final selfhost the seed backend is LINKED INTO the amu
  image as Kotoba modules and called in-process; during the bootstrap period the nbb/JVM-hosted amu may call the seed
  binary through the process/spawn capability (bootstrap-labelled, opt-in flag, default stays machine_ir)").
  Reversible: without the flag nothing changed; removing the flag removes the route.
- Related: docs/selfhost-seed-merge-20261003.md section 00 (the falsification test F1-F5 that admitted the seed backend,
  and the selector interface `seed compile-kir <in> --output <out> [--metered]`), kotoba-verifier ADR 0052 (the
  recorded-emitter registry), docs/selfhost-seed-backend-integration-20261003.md (the measurements).

## Context

The seed (`seed/`, a Kotoba compiler that is its own fixed point) has a backend that compiles the big compiler's sealed
KIR to AArch64: `seed compile-kir`. Section 00 of the merge page measured it against machine_ir on 315 programs: 0 of
357 exports differ, 0 seed-only traps, metered fuel equal on 347 of 347 comparable exports, 8 documented refusals
(floats, variants, heterogeneous vectors), and documents refused under `--metered`. The owner decided how amu calls it.
What was missing was the call: the amu compile path, the artifact and provenance record of which backend emitted the
code, and a verifier whose re-emission check can re-emit with that backend.

## Decision

1. **Flag.** `amu compile ... --target aarch64-* --backend seed --seed <packaged seed>` (or `AMU_SEED`). `--backend
   machine_ir` or no flag is the default route, unchanged. Any other value is a usage error; `--backend seed` with no
   seed named is a usage error. Only the nbb host serves the seed route; the other readings of `kotoba.compiler.nbb.cli`
   refuse `--backend seed` by name.
2. **Where.** In `compile-native!` (src/kotoba/compiler/nbb/cli.cljk), after the frontend, admission and `ir/lower`:
   the sealed KIR (`ir/native-program kir`, the artifact's `:program`, printed exactly as the artifact prints it) is
   handed to `seed compile-kir`, with `--metered` exactly when the artifact is metered (`--fuel n`, the policy's budget,
   or a metered target profile).
3. **How it runs (bootstrap).** `kotoba.compiler.nbb.seed-backend`, a mechanism-layer module labelled
   `;; bootstrap-tooling`: the seed command is read once, hashed, and written from those same bytes to a private 0700
   copy, which is the only program this route starts. The start has the process/spawn wire's shape: no shell, an
   explicit argv, an empty environment, stdin at EOF, stdout and stderr captured, a wall-clock bound. The packaged seed
   (scripts/seed/package.sh) carries its own wire-35 scope and no spawn grant; the work files go under `/tmp`
   (`AMU_SEED_WORK` overrides), inside that scope.
4. **Fallback.** Any refusal (an `E....` code: E1203 / E2101 / ...) or failure (non-zero exit without a code, no or a
   malformed container, an export of the KIR missing from the container) falls back to machine_ir. The compile report
   then says `:backend {:requested :seed :emitted :machine-ir :fallback {:kind :refused|:failed :code .. :message ..}}`.
   A fallback artifact and its provenance are byte-identical to the default build's.
5. **Record.** When the seed's code is used the artifact carries `:emitter {:name :kotoba-seed :sha256 <sha256 of the
   seed command> :route :bootstrap-process}` (under the artifact seal), the provenance record carries the same
   `:emitter` (under the provenance seal; `kotoba.compiler.provenance`, both readings), and the report says
   `:backend {:requested :seed :emitted :kotoba-seed :emitter ..}`. Exports are `{:offset :arity}`: the container has
   no per-function length (machine_ir's `:length` is read by nothing in amu).
6. **Verification.** The verifier's re-emission check stays byte for byte; it re-emits with the RECORDED emitter
   (kotoba-verifier ADR 0052: `verifier/*emitters*`, sha256 -> emit function). The driver binds the running seed's
   function under its sha256, so a different seed program serves no record. `extract-native` and
   `verify-output-set` / `sign-output-set` take `--seed` for the same purpose; without it a seed-emitted artifact is
   refused by name ("recorded emitter is not available to this verifier"). The driver looks the registry var up with
   `resolve`, so a verifier pin that predates ADR 0052 still loads and verifies every artifact without `:emitter` as
   before (and refuses one with it by its schema check).
7. **Caches.** The verdict cache uses kind `:kotoba.verdict/native-verify-seed` for a seed-emitted artifact (its
   subject, the sealed artifact, also binds the seed's sha256). The worker's artifact-cache key adds the requested
   emitter to the key material only (`:kotoba/emitter`), so the default route's keys are unchanged. Output admission
   (`output_admission.cljk`) admits the one extra provenance key `:emitter` and requires it to equal the artifact's.

## Consequences

- The 19 Embench ports go through the full nbb pipeline with `--backend seed`; the measured result is in the
  integration page (correctness, how many were emitted by the seed, verifier acceptance).
- This is a bootstrap route: node + nbb are in the process tree, and so is the seed process. The final selfhost links
  the seed's backend modules into the amu image and calls them in-process (the 14-namespace seed split shows that link);
  this ADR's spawn module is then deleted, not ported.
- `amu run`, `amu verify` and `amu sign` do not take `--seed` yet: they refuse a seed-emitted artifact by name.
- bin/amu resolves kotoba-verifier from the lock pin (a560612e), which predates ADR 0052; until the pin is advanced (not
  done here: no pin bumps in this wave) the seed route is exercised with the harness classpath
  (scripts/seed-backend/build-wrapper.sh: the lock closure with the verifier worktree). bin/amu with the pinned
  verifier does not run the seed at all: `--backend seed` falls back to machine_ir with the reason "the loaded
  kotoba-verifier has no emitter registry". Advancing the pin is the owner's step.
