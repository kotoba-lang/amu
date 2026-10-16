# ADR 0355: Kototama is the default program target

- Date: 2026-10-14
- Status: Accepted
- Deciders: repository owner
- Related: ADR 0351 (superseded historical native-default decision), Kototama VM program contract

## Context

The omitted `--target` previously selected the host's native executable
profile. That makes a source program's default artifact depend on the build
machine and operating system. The Kototama program format is an
engine-neutral, content-addressed execution contract with explicit methods,
exports, values, and effects. It is the portable application target analogous
to how EVM bytecode is a portable target for Ethereum applications.

## Decision

`amu compile` and `amu worker` select Kototama when neither `--target` nor
`AMU_TARGET` is supplied. Explicit targets continue to select a specific
backend, including Wasm and native targets. This changes the default only;
it does not claim that all Kototama values, effects, hosts, or OS integrations
are already implemented.

Kototama artifacts carry an explicit export list. External actor messages may
invoke only exported methods; internal calls may reach private helpers. Older
artifacts without an export list retain their historical all-methods-exported
interpretation. The current compiler profile accepts KIR v3 i64 and the
supported KIR v4 `data-i64` value slice. Unsupported floating-point profiles
fail before an artifact is written.

## Consequences

- The default artifact is independent of host ISA and OS.
- Consumers must execute the content-addressed Kototama program through a
  compatible VM implementation; this decision alone does not establish a
  distributed network, consensus, or cross-platform host qualification.
- Wasm and native remain explicit targets for consumers that need those
  artifacts or host-specific integration.
