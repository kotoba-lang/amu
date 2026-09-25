# ADR 0005: Closed Kotoba module linking

## Status

Accepted.

## Decision

Multiple `.kotoba` source units are linked by the Kotoba compiler before KIR
lowering. A project supplies a closed map from declared namespace symbols to
source text and names one root namespace. No JVM, JavaScript, ClojureScript, or
host module resolver participates in this operation.

For the public JVM CLI, `compile root.kotoba --source-path src` constructs that
closed map from the reachable dependency closure before calling
`compile-project`. Resolution is deterministic: namespace dots become path
separators, hyphens become underscores, and extension priority is `.kotoba`,
`.cljk`, `.cljc`. Every dependency must resolve by real path below the
explicitly supplied source directory and declare exactly the namespace
requested by the graph. The explicitly named root may live outside that source
directory because it is never discovered by namespace. Runtime lookup,
classpath lookup, directory-wide eager
loading, symlink escape, and namespace/path substitution are rejected.

The admitted namespace dependency syntax is deliberately narrow:

```clojure
(ns example.app
  (:require [example.text :as text])
  (:export [welcome]))
```

Imports must use a unique alias. `:refer`, wildcard imports, implicit lookup,
relative paths, and runtime loading are rejected. Since 2026-09-11 (ADR 0346,
proposed) a spec may also bind a template module's type parameters --
`[kotoba.set.union :as ui :with {elem :i64}]` against a module declaring
`(:params [elem])` -- and the linker instantiates that module per binding
before the frontend reads it. Only functions in the
dependency's export vector can be called.

Since 2026-09-25 (ADR 0353 floor `:export-from-publicity`) the export vector
need not be written. A module with no `:export` clause (and no
`:kotoba/export` attr-map key) exports exactly its public top-level
functions, in source order: every `defn` whose name carries no `^:private`.
`defn-` and `defn ^:private` are private; a `def` constant is never exported
(the frontend refuses a constant as an export). An explicit `:export` still
wins and may narrow the set. The linker hands the frontend the derived vector
as the `(:export [...])` clause the author could have written, so both
spellings link to the same source and the same interface; a module whose every
function is private is refused (`project module <ns> exports nothing`).
Closedness is unchanged: the set is still exact, only its spelling moved from
the header to `defn` / `defn-`. The linker rejects missing
source units, namespace/key mismatches, duplicate aliases or dependencies,
unknown qualified calls, cycles, and projects above 256 modules or 1,024 linked
functions.

Project admission also caps the supplied source corpus at 8 MiB UTF-8, the
linked source at 1 MiB UTF-8, reachable dependency edges at 256, dependency
depth at 64, aggregate exported interfaces at 1,024, parsed expression nodes at
200,000, literals at 65,536, and aggregate string-literal payload at 1 MiB
UTF-8. These checks occur while resolving the closed graph, before backend
emission.

Dependencies are visited before consumers and linked into one compiler-private
call graph. Only the root module's exports receive host-visible wrappers. The
ordinary frontend then re-analyzes that complete graph, so type checking,
capability-effect closure, fuel, literal limits, admission policy, and KIR
validation apply across module boundaries rather than trusting per-module
claims.

`compile-project` records a canonical `kotoba.module-graph/v1`, exact source
SHA-256 for every reachable module, and its graph digest. JavaScript manifests
bind the graph digest and source digests to the emitted artifact metadata.
Unreachable entries in the supplied source map do not enter the linked graph.

## Consequences

The first version rejects dependency cycles even though function-level mutual
recursion inside one source unit remains valid. This makes initialization and
graph identity unambiguous. Modules are source-linked, not separately cached;
content-addressed interface and KIR caching can be added later without changing
the closed resolution contract.
