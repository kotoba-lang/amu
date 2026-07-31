# ADR 0193: T8.3 multi-file monomorph admits desugared `__kotoba_*` synthetics

- Status: Accepted
- Date: 2026-08-01
- Depends: ADR 0192 multi-file Component CLI; project/link-source monomorph

## Context

ADR 0192 landed `--target component --source-path` (link → compile-component).
`project/link-source` analyzes each module once (frontend desugars `or`/`and`
into `__kotoba_or_*` / `__kotoba_and_*` bindings), then re-emits a monomorphic
source whose bodies contain those synthetics. The second `frontend/analyze`
pass on the monomorph rejected them with
`symbol uses the reserved __kotoba_ prefix` — so any multi-file project that
used `or`/`and` (e.g. result status bounds) failed even though each module was
valid alone.

## Decision

1. `frontend/analyze` opts gains **`:admit-linked-synthetics?`**. When true,
   skip `reject-reserved-source-symbols!` only. User source without the flag
   still cannot invent `__kotoba_*` names.
2. `compile-project` and CLI multi-file component path pass
   `:admit-linked-synthetics? true` after `link-source`.
3. Per-module first pass inside the linker is unchanged (still rejects reserved
   names in user modules).

## Evidence

- `compile-project-component-admits-linked-or-synthetics`
- `compile-source-path-component-multi-file-with-or` (wasmtime main→1)
- Full suite **778 tests / 6261 assertions** green

## Related

- T8.3 multi-file project kit body; ADR 0192
- Follow-up: re-ship real multi-ns ops kit Components; W4 recursive EDN
