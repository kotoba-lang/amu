# ADR 0295: a lock that needs a JDK to read is not a reproducible build

- Status: accepted
- Date: 2026-09-01

## Decision

`--module-lock` runs on Node. `kotoba.compiler.nbb.module-lock` is the twin of
`kotoba.compiler.module-lock`, `bin/amu` no longer vetoes the flag, and the
`module-lock` subcommand — the one that PRODUCES a lock — routes there too.

The refusal that stood here until today was correct for as long as it lasted.
ADR 0287 sent every project-mode invocation to the JVM because the nbb path
had no linker and dropped `--source-path` / `--module-lock` silently; amu#717
then ported the PATH resolver and left the lock behind, deliberately, because
answering a lock-pinned build out of the path resolver would have dropped the
pinning without saying so. Answering the wrong question quietly is worse than
refusing loudly.

But the consequence had a name. Q9 (`kotoba-lang/kotoba-lang`
`lang/q9-migration.edn`) forbids a JVM build dependency, and `--module-lock`
is the reproducible-inputs path, so **reproducible and JDK-free were mutually
exclusive**. The way to remove a refusal is to remove its reason, not the
refusal.

Both halves were ported rather than only the consumer. Leaving lock production
on the JVM would have moved the JDK one step upstream of every pinned build:
a project could be compiled JDK-free only from a lock some JDK had written.
That is the objection restated, not answered.

### What the port keeps

Every refusal, by its exact message, with `:phase :module-lock` — the same
strings the JVM twin raises, so a caller matching on the message gets one
answer from both routes:

| refusal | message |
|---|---|
| unpinned dependency | `required module is not pinned by the lock` |
| tampered / wrong block | `locked module block does not hash to its CID` |
| absent block | `locked module block is missing from the block store` |
| a CID that is a path | `module CID is not a plain base32 CIDv1` |
| block declares another ns | `locked module declares a different namespace` |
| lock does not pin its root | `module lock does not pin its own root` |
| unknown schema | `unknown module lock schema` |
| empty lock | `module lock must pin at least one module` |
| entry with no CID | `module lock entry must pin a CID` |
| over the module ceiling | `module lock exceeds the project module limit` |
| unreadable block store | `block store is not readable` |
| block store bytes disagree | `existing block has different bytes for its CID` |
| `--module-lock` with no `--blocks` | `--module-lock requires --blocks <dir>` (`:phase :usage`, exit 64) |

Two things the port does NOT do: there is no path fallback for anything the
lock fails to pin, and `--module-lock` and `--source-path` are mutually
exclusive on this route rather than combined. A lock that searched a path for
its gaps would be a lock in name only.

### The digest is the JVM's digest, and that is tested

The CID is assembled here from `node:crypto`'s SHA-256 and
`multiformats.base32` rather than by calling `multiformats.core/cidv1-raw`.
That namespace's ClojureScript branch hashes with `@noble/hashes`, an npm
package Amu does not depend on and which would have to be installed on every
runner for the compiler to start; `multiformats.base32` states in its own
docstring that it carries no hashing or npm dependency, and the remaining
bytes are the two varints `0x01 0x55` and the sha2-256 multihash header
`0x12 0x20`.

A resolver that verified against its own private hash would accept every block
it wrote and reject every lock the other route wrote, while looking exactly
like this one. So `test/nbb/project.cljs` pins the result against vectors the
JVM produced, and the whole-graph `lock-cid` beside them.

### Three changes that are corrections, not ports

1. **`:module-lock` maps to exit 65 and to `:kotoba/module-lock-failed`.** It
   mapped to 70 and `:kotoba/internal-error` on BOTH routes, so a CI job could
   not tell a tampered block store from a compiler crash. `exit-code` lives in
   two files and `phase-codes` in one shared `.cljc`; all three are updated, so
   the routes still answer identically. This is the third instance of the shape
   ADR 0287 recorded for `:project-link` and `:artifact-target`.
2. **`bin/amu` resolves the value of `--blocks` and `--source-path` against the
   caller's directory.** A directory name has neither a separator nor an
   extension, so `resolveCallerPaths`'s spelling heuristic could not see it and
   `--blocks blocks` was resolved against the Amu checkout by the spawn's
   `cwd: root`. The flag says what the next argument is; use it.
3. **`module-lock`'s default `--output` is anchored to the entry module.** The
   JVM twin's default is the bare name `kotoba.modules.edn`, resolved against
   the process CWD — which, through `bin/amu`, is the Amu checkout. This is a
   deliberate divergence from the JVM default and is the only one.

## Evidence boundary

Host: MacBookPro18,4, macOS, `com-junkawasaki/orgs/kotoba-lang/amu` at base
`93c49982be32459b7671d70a308f0b8998b67477`. This workstation ran many
concurrent sessions throughout; no timing is claimed below, only outcomes.

### The measurement that matters: no JVM anywhere

Run with `PATH` containing only symlinks to `node`, `sh`, `cat`, `env` and
`git`, and `JAVA_HOME=/nonexistent`. `command -v clojure` and `command -v java`
both answered ABSENT inside the sandbox, and that is printed by the run itself.

```
clojure: ABSENT
java:    ABSENT
amu module-lock src/main.cljk --source-path src --blocks blocks --output lock.edn --jvm-free
  -> exit 0, {:ok true ... :root main, :modules 2,
              :lock-cid "bafkreibhyfwgozu7dmqhxz2fq7h2xkhmcnmwie4duqf56hx6v2bjy7szvy"}
amu compile --module-lock lock.edn --blocks blocks --target wasm32 --output out.wasm --jvm-free
  -> exit 0, {:ok true ... :kotoba.compile/inputs :module-lock,
              :lock-cid "bafkreibhyfwgozu7dmqhxz2fq7h2xkhmcnmwie4duqf56hx6v2bjy7szvy"}
WebAssembly.instantiate(out.wasm).exports.run(5n) -> 11n
```

`run` is `(+ 1 (u/twice x))` and `twice` lives in the OTHER module, so `11n` is
evidence the dependency was linked, not that an entry module was admitted
alone. `git` is on that PATH because the deps-lock verifier checks each pinned
checkout's commit; it is not a JVM.

### Byte-for-byte against the JVM route

The same two source files, pinned and compiled once through
`clojure -M:run` and once through the Node route:

| artefact | result |
|---|---|
| `lock.edn` | **byte-identical** |
| block filenames (the CIDs) | **identical** |
| reported `:lock-cid` | identical: `bafkreibhyfwgozu7dmqhxz2fq7h2xkhmcnmwie4duqf56hx6v2bjy7szvy` |
| `out.wasm` | **byte-identical**, sha256 `9b7065359439fb0fa6b8b8b8b777ef7e6c2e196487473da4ad6006863c9d399b` |
| `out.wasm.provenance.edn` | **differs** |

The provenance difference is one field, `:build-metadata-sha256`:
`8c3cd1aba24af56d0e80e4ee86cc968a521cfbc89fcc7bf01832766fd2aa74c4` on the JVM
against `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` on
Node — the latter being sha256 of `{}`. `core/compile-project` threads
`{:module-graph-digest … :module-source-digests … :admit-linked-synthetics?
true}` into `compile-source` as build metadata; the nbb route passes only
`emit-metadata`.

**This is pre-existing and is NOT introduced here.** The same two files
compiled through `--source-path --unpinned` on the JVM and `--source-path` on
Node produce a byte-identical `.wasm` (the same sha256 as above) and provenance
that differs at the same character offset with the same two digests. It arrived
with the path-resolver port and it applies to every linked build on this route,
pinned or not. It is left for whoever owns that port rather than fixed from
here, and it is recorded so nobody reads "artifact parity" as "provenance
parity".

`.inputs.edn` is also not written on the Node route. Its output set is a
two-file commit marker (`output-set/descriptor` requires exactly two entries)
and a third member would make every artifact fail its own verification, so the
same facts — `:kotoba.compile/inputs` and `:lock-cid` — are reported in the
command's stdout map instead. The JVM's own comment calls that file a record
rather than a seal.

### Break/unbreak

Two reverts in an isolated copy, `test/nbb/project.cljs` run against each.
Control: **25 cases, 0 failures** (9 pre-existing, 16 new).

| revert | result |
|---|---|
| `(when-not (= cid actual) …)` → `(when-not (or true (= cid actual)) …)` | `a-block-that-does-not-hash-to-its-cid-is-refused` **FAIL**, by its message: "expected a rejection carrying \"locked module block does not hash to its CID\", got none". The 11 cases before it stayed green; the runner exits on first failure. |
| CID prefix `[0x01 0x55 0x12 0x20]` → `[0x01 0x71 0x12 0x20]` (dag-cbor instead of raw) | `cid-matches-the-jvm-twin` **FAIL** on the first golden vector. This is the control for a self-consistent but wrong digest: every other case still passes, because the resolver agrees with itself. |

Restored: 25 cases, 0 failures.

Two refusals were also exercised through the shipped launcher rather than the
library, with `clojure` shadowed by a marker script:

```
tampered block: exit 65, "locked module block does not hash to its CID",
                no artifact written, marker absent
no --blocks:    exit 64, "--module-lock requires --blocks <dir>", marker absent
```

### Suites

| suite | this branch | base `93c4998` |
|---|---|---|
| `test/nbb/project.cljs` | 25 cases, 0 failed | 9 cases, 0 failed |
| `scripts/test-nbb-wasm32.cljs` | 42 cases, 0 failed | 42 cases, 0 failed |
| `node scripts/test-amu-launcher.mjs` | see below | see below |

## Limits of this evidence

- **Two modules, one edge, one target.** `max-project-modules` is 256; nothing
  near it was tried. Only `wasm32` was compiled from a lock on this route;
  `wasm32-browser`, `wasm32-wasi` and the native targets share
  `resolve-source!` but were not run from a lock.
- **The JVM comparison used one project.** Byte-identity of the artifact is
  measured for that project, not proven in general.
- **No component or `--target js` compile from a lock was run on this route**;
  those still reach `cli.clj`, which is unchanged for them.
- **The provenance divergence above is measured, not fixed.** Any consumer
  that verifies provenance across routes still cannot treat them as one.
- **`--unpinned` is still not enforced on the Node route.** The JVM CLI refuses
  a `--source-path` compile without it (ADR-2608580000 D5); the nbb route never
  did, and this change does not add it. A caller who wants the pinned build is
  now able to get one without a JDK, which is the half this ADR is about.
