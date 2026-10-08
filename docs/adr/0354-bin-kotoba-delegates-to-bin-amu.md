# ADR 0354 — `bin/kotoba` delegates every compiler command to `bin/amu`

- Date: 2026-10-09
- Status: Accepted
- Deciders: owner (2026-10-09, superproject ADR-2610082200 W0)
- Related: ADR 0250 (`bin/amu` is the canonical launcher; `bin/kotoba`
  delegates to it), ADR 0348 (the module linker is one namespace on both
  hosts), ADR 0347 (the JVM route is removed), ADR 0350 (linked closures on the
  JVM-free route).

## Context

ADR 0250 recorded `bin/kotoba` as the compatibility launcher whose compiler
commands delegate to `bin/amu`. It never did. It kept its own copy of amu's
route table, and the copy drifted:

- `bin/amu` removed its project-mode guard once the module linker became one
  namespace on both hosts (ADR 0348). `bin/kotoba` still sent every
  invocation carrying `--source-path` or `--module-lock` past the nbb route,
  and after ADR 0347 that meant a refusal.
- `test`, `definition-cids`, `module-lock` and the package commands, which
  `bin/amu` serves on the nbb route, were refused by `bin/kotoba` for the same
  reason.

Measured 2026-10-09 while counting how much of the stack below the kotoba app
is pure Kotoba (superproject ADR-2610082200 §16): `kotoba -M check <entry>
--source-path <dir>` answered "has no implementation on the nbb/native route"
for 930 of 930 files, while `amu check <entry> --source-path <dir>` linked the
same graphs. `~/.local/bin/kotoba` points at this launcher, so that is the
command people and agents reach first.

## Decision

`bin/kotoba -M <command> ...` spawns `bin/amu -M <command> ...` in the caller's
directory with the caller's environment and exits with its status. Help and
the missing-boundary refusal stay in `bin/kotoba`. Its private route table,
target defaulting, classpath resolution and nbb spawning are deleted: one
route table, one target rule, one refusal text.

## Evidence

- `scripts/test-nbb-test.cljk` gains two checks on the template-module fixture
  it already links: `bin/kotoba -M check --source-path` answers `:ok true`,
  and `bin/kotoba -M test --source-path` runs 3/3. Against the previous
  `bin/kotoba` both fail with the JVM-route refusal (16 checks: 14 pass, 2
  fail); with this change 16/16 pass.
- `scripts/test-default-target.cljk` (33/33), `scripts/test-nbb-wasm32.cljk`
  (54 cases) and `scripts/test-nbb-release-and-emitters.cljk` (20 cases), which
  compare the two launchers, pass unchanged.
- `bin/kotoba -M test` on kotoba-lang/kototama `src/kototama/admission.kotoba`
  runs 27/27 across `:jvm-kir`, `:js` and `:wasm`; before, the command was
  refused.

## Consequences

- A command added to `bin/amu` is available through `bin/kotoba` the same day.
- `bin/kotoba`'s usage text is still its own and can lag `bin/amu`'s; the
  behaviour cannot.
