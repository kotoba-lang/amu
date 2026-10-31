# ADR 0355: Kototama is the default program target

- Date: 2026-10-14
- Status: Superseded by [ADR 0396](0396-each-public-entry-names-its-own-host-target.md) (2026-10-31, KOTOBA-174)
- Deciders: repository owner
- Related: ADR 0351 (superseded historical native-default decision), Kototama VM program contract

> **Superseded (2026-10-31, KOTOBA-174, ADR 0396).** No current entry selects Kototama for an omitted
> `--target`, and none ever will. Each public entry names its own host target: `bin/amu` uses `aarch64-macos`
> and `bin/x86_64-linux/amu` uses `x86_64-linux`. The compiler roots refuse an omitted target with E2.
> Kototama exists only as the explicit `compile-kototama*` commands. The text below is kept as the record
> of the 2026-10-14 decision.

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
