# ADR 0354 — Kototama is the default program target

- Date: 2026-10-13
- Status: Accepted
- Supersedes: ADR 0351 for `amu compile` only

## Context

Amu's omitted compile target selected a host-native artifact, while Wasm was
the explicitly selected portable path. That made the OS/ISA backend the
default execution contract and left Kototama as a separate runtime concept.
The platform direction is now Kototama: Amu emits a versioned,
engine-neutral Kototama program block by default, and host engines own
execution.

## Decision

1. `amu compile <source>` defaults to `kototama` and emits a canonical
   DAG-CBOR program block plus provenance sidecar. `AMU_TARGET` and an
   explicit `--target` continue to select another backend.
2. Native, Wasm, Script and EVM targets remain explicit deployment formats.
   No compiler route silently changes a Kototama target into one of them.
3. `amu worker` remains host-native by default because it starts a host-bound
   compiler service. This exception does not affect compile output selection.
4. The current Kototama emitter accepts the checked i64 KIR slice and rejects
   unsupported forms. The output format and target declaration do not prove
   execution support, cross-platform qualification, or distributed operation.

## Consequences

- A default compile has no OS or ISA in its target profile.
- Programs that need a native executable or Wasm module name that target.
- macOS/Windows execution requires a compatible Kototama engine on those
  hosts; Amu's emitted artifact alone is not runtime qualification.
