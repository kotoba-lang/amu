# ADR 0348 — The JVM route leaves in dependencies-first order, and the trust plane is the first family off it

- Date: 2026-09-11
- Status: Accepted (in progress — the order is the decision; the sections below record how far it has been walked)
- Owner direction: 「clojure, jvm router に依存しないように 逆トポロジーソート」— remove the
  dependency on `clojure` / the JVM route, in reverse topological order.
- Related: ADR 0347 (the JVM route is removed -- landed the same afternoon from a parallel
  session; this ADR is the order in which its "blocked" ledger empties, and its first
  family), root ADR-2609111500 (the `.cljk` rename, which left the JVM route unable to
  load this compiler at all), ADR 0340 (restricted-ESM targets left the JVM route),
  ADR 0298 (a lock that needs a JDK to read is not reproducible), root ADR-2607198300.

## Context

`bin/amu` has two routes. The Node route answers `check`, `compile`, `definition-cids`,
the package and output-set commands, and the native/EVM/JS targets. Every other command
fell through to `clojure -M:run` and `kotoba.compiler.cli` -- until ADR 0347 removed the
spawn the same afternoon and made the fall-through a refusal by name. Either way a command
on it has no working route anywhere — measured 2026-09-11 morning:
`amu keygen` exit 1, and `test-output-set-publisher-auth` red at its first `keygen`.

The question was not "which command to port next" but "what does each command stand
on, and in what order can those be made portable without porting a dependent before its
dependency". That is a graph question, and it is answered by a script rather than by
reading the code:

```
nbb --classpath . scripts/jvm-route-topology.cljk --probe --output docs/jvm-route-topology.edn
```

It walks every namespace on the compiler's classpath (292 on 42 roots), decides for each
whether the Node host can load it — twins count, the resolver's probe order counts, and
`--probe` replaces the static claim with an actual `require` in a child nbb — computes the
closure `kotoba.compiler.cli` reaches (96 namespaces), and orders the JVM-only part of it
dependencies first. The EDN it writes is the plan; this ADR is the decision to follow it.

## Decision

1. **The order is the graph's, not a judgment.** A leaf (level 1: no JVM-only dependency)
   is ported before anything that requires it. A command leaves the JVM route when every
   JVM-only namespace it reaches is gone from the list.
2. **One implementation per command.** A command that leaves the route is a portable
   namespace that the JVM CLI *delegates to* and a thin Node entrypoint *runs* —
   never a second implementation beside the first. `kotoba.compiler.trust-cli` is the
   pattern: `kotoba.compiler.cli/dispatch!` calls it for the commands in
   `trust-cli/commands`, `kotoba.compiler.nbb.trust-cli` is `(support/execute! …)` and
   nothing else, and `bin/amu` routes the same set.
3. **A leaf keeps its name.** `kotoba.compiler.bounded-edn` is still
   `kotoba.compiler.bounded-edn`; the `:clj` implementation stays byte-for-byte inside its
   reader conditional and the `:cljs` branch is added. Consumers do not move.
4. **The integer representation is part of the leaf, not of the caller.** On Node every
   integer the compiler's reader returns is a bigint. A portable leaf hands that back, and
   every consumer that compares one says so with `kotoba.verifier/guest-integer?` — not
   `integer?`, which is false for a bigint. `bounded-edn` records why the reader is the
   kotoba reader and not `cljs.reader` (a Number cannot hold an i64).
5. **The topology is regenerated, never edited.** `npm run jvm-route-topology`.

## What was measured before deciding

The first leaf refused for a reason that was not in the leaf. With `bounded-edn` and
`atomic-output` portable, an envelope signed on Node, written with `artifact/edn-safe`,
and read back with the kotoba reader was refused by `kotoba.verifier.signing/verify` as
`"signature statement mismatch"` — its validity bounds were bigints and the check was
`integer?`. The same bytes read with `cljs.reader` verified, and lost every i64 in the
artifact. Fixed at the source (kotoba-verifier `f1efb423`, `guest-integer?` public and used
by `sign`/`verify`, three discriminated tests) and pinned here. Rank 4 above is that
measurement written down.

## Walked so far (2026-09-11)

| level | namespace | status |
|---|---|---|
| 1 | `kotoba.compiler.bounded-edn` | **portable** — `bounded-edn-portable-test` (9 refusals, byte ceiling, strict UTF-8) in both suites |
| 1 | `kotoba.compiler.atomic-output` | **portable** — through `nbb.io/write-set!`; `:private?` is that route's default, `:executable?` is set on the descriptor before a byte lands |
| 1 | `kotoba.compiler.receipt`, `coverage-evidence` | were portable by content already; the classifier now reads content, not origin |
| — | `kotoba.compiler.target-names` | lifted out of `cli` so a `--target` reads on either host |
| — | `kotoba.compiler.trust-cli` | **new, portable** — `keygen public-key inspect trust-key trust-runtime sign verify-signed verify receipt verify-receipt verify-chain` |

Commands off the JVM route by this ADR: the eleven above. `scripts/test-nbb-trust.cljk`
runs them through `bin/amu` — 32 checks, every positive with a refused twin naming its
reason and exit code (expired 77, untrusted 77, tampered byte 65, tampered statement 77,
bad integer 64, missing parent 74), and `--jvm-free` on the last one.

Found on the way and fixed on both routes: `:sign` (a malformed key at `public-key`) was in
neither exit-code table and answered 70, "internal compiler error", for a caller's input.
It is 77 now, beside the signature plane's other refusals.

## What remains, in order (from the EDN, `--probe` confirmed)

| level | namespace | refused on Node with | unblocks |
|---|---|---|---|
| 1 | `kotoba.compiler.release` | `java.io.FileInputStream` | `sbom`, `attest-release`, `verify-release` |
| 1 | `kotoba.compiler.coverage` | `java.nio.file.Files` | `coverage` (`sign-coverage-evidence` needs only the leaves already done) |
| 1 | `kotoba.compiler.project-files`, `module-lock` | `java.nio.file.Files` | already have Node ports under `nbb.*` — the honest end state is one namespace each, not two |
| 1 | `kotoba.component.admission`, `kotoba.wasm.tools` | `StandardCharsets` | external repo `kotoba-component` / `kotoba-wasm`; `check`/`compile` on the JVM route |
| 2–3 | `kotoba.component.core`, `.artifact` | same repo | |
| 4 | `kotoba.compiler.core` | the JVM compile driver (930 lines) | `test`; the JVM `check`/`compile` twins |
| 5 | `kotoba.compiler.test-profile` | `clojure.java.shell` | `test` |
| 6 | `kotoba.compiler.cli` | itself | the route |

Not on this list, deliberately: `run` and `measure-runtime` need `kototama.native.executor`
(the `-M:native-run` alias) — a runtime, not a compiler leaf — and `package-ios` /
`package-aiueos-boot` stand only on the two leaves now portable and are a routing change
away, gated on their own end-to-end checks.

## What this does not claim

The `:clj` branches are unchanged but are **unverified since the rename**: `clojure -M:test`
cannot load `.cljk`. Parity between the two hosts is held by the portable tests and by the
byte-identical emission checks, not by the JVM suite. `test-output-set-publisher-auth` now
gets past `keygen`, `trust-key`, `sign-output-set` and `verify-output-set` and stops at its
own `clojure -M -e` parity oracle (line 99) — that line is the JVM route, and it is red for
the same reason as everything else on it.
