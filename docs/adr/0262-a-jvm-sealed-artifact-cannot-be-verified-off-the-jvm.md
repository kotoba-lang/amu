# 0262 — A JVM-sealed artifact cannot be verified off the JVM

Status: accepted
Date: 2026-08-21

## Context

`kotoba/compiler/ios_aot.clj` became `.cljc`. Two edits: `.getBytes` behind an
`ascii-bytes` reader conditional (the same shape `kotoba.native.aarch64` and
`.elf64` already use), and the `byte-array` return value made `:clj`-only.

The JVM shape is deliberately unchanged. `:object` is written straight to a
file by `cli` and read as bytes by the existing tests, so making the namespace
portable must not alter what a JVM caller receives. On ClojureScript `:object`
is the `object-vector` — already unsigned ints, and already the value
`:object-sha256` is computed from.

## Decision

Drive `package` end to end on both runtimes from a captured artifact
(`test/fixtures/ios-aot-artifact.edn`, 2 KB), in
`kotoba.compiler.portable-surface-test`. Loading is not evidence: `(.getBytes
s c)` compiles under cljs and fails only when executed.

Both edits were verified to discriminate. Truncating the `ascii-bytes` cljs
branch fails one assertion; making `object` unconditionally `byte-array` fails
to resolve the symbol. Restoring gives 6 tests / 14 assertions green with no
JVM. The full JVM suite is 1,115 tests / 8,369 assertions, 140/140 namespaces.

## What the fixture exposed

The fixture is a real sealed artifact rather than a hand-built stand-in
because `verify-artifact!` re-emits the machine code and re-runs the KIR
oracle before `package` is reached; a hand-written value cannot survive that.

Feeding it to the verifier under nbb is rejected with **`native artifact
oracle value rejected`**. The cause is not the packager:

- `:value` is the i64 oracle the verifier recomputes and compares.
- The fixture was printed by `pr-str` on the JVM, where an i64 prints `42`.
- The ClojureScript KIR interpreter answers with a BigInt, and `(= 42n 42)`
  is false.

So **there is no round-trip today that preserves an i64 across the two
runtimes**. `lang/value-codec.edn` specifies a canonical value encoding;
`kotoba.artifact.core` does not implement one. Until it does, a JVM-sealed
artifact cannot be verified off the JVM — which is a precondition for any
claim that verification is reproducible by a third party without a JVM.

The test restores the dropped type at read time and says why. That is scoped
to the transport, not a workaround in the code under test.

## A measurement that was wrong before it was reported

The first comparison showed `emit-program` producing 48 bytes on the JVM and
100 on nbb for identical KIR, which reads as a backend divergence. It was not.
`clojure -Spath` resolves `kotoba-native` from a pinned git dep
(`95fd4b19`, `~/.gitlibs`) while the hand-built nbb classpath pointed at the
working checkout `orgs/kotoba-lang/kotoba-native`. Two different sources.

On identical sources the two runtimes emit **byte-identical** code. The
docstring of `portable-surface-test` already prescribes
`nbb --classpath "src:test:$(clojure -Spath -M:test)"` — deriving the nbb
classpath from the JVM one is what makes the comparison mean anything.

The `orgs/` checkout and the dependency amu actually builds against are not
the same code. A reader who opens `orgs/kotoba-lang/kotoba-native` is not
reading what compiled the artifact.

## Consequences

- 18 `.clj` files remain in `src`: file I/O, byte/charset, crypto, JSON. Each
  needs `IFilesystem`, a canonical JSON choice, or a cljs crypto provider —
  design, not mechanical porting.
- The fixture will go stale if the artifact schema, the fuel ABI or the
  context ABI changes. That is a real check, not a maintenance tax: it fails
  loudly rather than silently verifying nothing.
