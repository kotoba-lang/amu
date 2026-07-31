# ADR 0192: T8.3 multi-file project kit body — component + `--source-path`

- Status: Accepted
- Date: 2026-08-01
- Depends: project/link-source closed graph; compile-component Canonical path

## Context

T8.3 residual lists **multi-file project kit body** next to W4 recursive nested
EDN. CLI previously threw
`component compilation does not accept --source-path yet`, forcing every
Component package to be a single admission skeleton file even when helpers
belong in separate namespaces.

`project/link-source` already produces monomorphic linked source that
`compile-component` admits (verified: `:scalar` lowering, wasmtime `main()→42`).

## Decision

1. **CLI**: `--target component --source-path <roots…>` loads the closed graph,
   links, and calls `compile-component` with the linked source (same opts as
   single-file component: fuel/profile/capability-mode).
2. **`compile-project`**: when target execution is `:component`, route through
   `compile-component` instead of rejecting via `compile-source`.
3. Project digests (`:kotoba.module/*`) attach on the programmatic
   `compile-project` path; CLI multi-file path prioritizes linked-source
   compile with full component-opts.

Honesty:

- Does **not** flip ops kit `:wasm-aot :implemented` (W4 recursive nested EDN
  ADT for kit request/result identity still open).
- Does **not** lift `:schemas` project-mode restrictions of the linker.
- Canonical WAT still owns specialized lowerings (headers-edn-append, …);
  multi-file only supplies admission skeletons across namespaces.

## Evidence

- `compile-source-path-component-multi-file` +
  `compile-project-component-target-multi-file`
- Full suite: **776 tests / 6254 assertions** green
- Live wasmtime multi-file Component `main()→42`

## Related

- T8.3 frontier multi-file project kit body residual
- Follow-up: split provider HTTP reject kit into multi-ns project when useful;
  W4 recursive nested EDN
