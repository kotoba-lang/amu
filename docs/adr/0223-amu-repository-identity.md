# 0223 — Amu repository identity

- Status: accepted
- Date: 2026-08-10
- Machine-readable companion:
  [`0223-amu-repository-identity.edn`](0223-amu-repository-identity.edn)

## Context

The repository's public name, `compiler`, described its role but did not give
the Kotoba compiler a stable product identity. Renaming every occurrence of
“compiler” would be unsafe: Clojure namespaces, sealed provenance statements,
cache records, scripts, and user launchers already carry compatibility-visible
identifiers.

## Decision

The canonical repository and product name is **Amu**, hosted at
`kotoba-lang/amu`. The canonical tools.deps coordinate is
`io.github.kotoba-lang/amu`, the workspace path is `orgs/kotoba-lang/amu`, and
`bin/amu` is the named compiler launcher. “Amu” evokes Japanese 「編む」:
weaving admitted Kotoba source, typed KIR, and target artifacts.

This is an identity migration, not a wire-format migration. The
`kotoba.compiler.*` namespaces, `kotoba-compiler/1` cache/compatibility marker,
`:kotoba-compiler/v1` provenance builder, and `bin/kotoba-compiler` launcher
remain supported compatibility APIs. Generic prose may continue to call Amu a
compiler. New repository links and dependencies must use the Amu identity;
GitHub's old repository URL redirect is migration support, not the canonical
address.

## Consequences

- Existing source and sealed artifact readers do not need a coordinated flag
  day.
- New dependency declarations and local-root overrides identify Amu directly.
- A future removal or wire rename requires a separate ADR, compatibility
  window, and migration evidence.
