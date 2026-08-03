# ADR-0202 — The nbb fast path resolves its dependency closure without a JDK

- Status: accepted
- Date: 2026-08-03
- Related: ADR-0004 (nbb-native wasm32 compile path),
  `com-junkawasaki/root` ADR-2607198300 (no JVM/Node/Rust at run time),
  `com-junkawasaki/root` ADR-2608012050 (content-addressed supply chain)

## Context

`bin/kotoba`'s nbb fast path has never run compiler code on the JVM. Its
*classpath* was another matter: `security-classpath-entry` shelled out to
`clojure -Spath` purely to locate the pinned git dependencies in `~/.gitlibs`.
That one call is what made the whole path need a JDK.

Measured directly, by stubbing `clojure` out and clearing the cache:

```
$ PATH=<no clojure>:$PATH bin/kotoba -M compile probe.kotoba --target aarch64-macos
Error: Could not find namespace: kotoba.artifact.core
```

Two problems in one line. The path needed a JDK it claimed not to need, and
the failure was **fail-open**: `-Spath` failing returned `""`, the caller
carried on with a truncated classpath, and the resolution error surfaced as a
missing namespace from an unrelated file.

The workspace's runtime priority is `kotoba wasm` → `clojurewasm` →
ClojureScript → nbb, with the JVM demoted to a last resort. A compiler
front door that cannot start without a JDK is the first thing in the way of
that, and of any CI job that would rather not provision one.

## Decision

### `deps-lock.edn` records the resolved closure; git alone reproduces it

A `:git/sha` is a content address, so a resolved closure is reproducible from
git without re-deriving it. `kotoba.compiler.nbb.classpath` materializes each
pinned checkout (cloning at the pin if absent) and verifies
`git rev-parse HEAD` against it — a directory named after a commit is not
evidence that it holds that commit.

The lock is bound to `deps.edn`'s digest. Editing a pin without regenerating
the lock is an error, not a silently stale closure.

### The lock records the answer, not the algorithm

Transitive pins genuinely conflict here: the root pins `kotoba-kir` at one
commit and `artifact`, `kotoba-native` and `kotoba-verifier` pin three others.
Choosing between them is `tools.deps`' job. `scripts/lock-classpath.cljs` runs
`clojure -Spath` **once, at authoring time**, and writes down what it decided.

Re-implementing that resolution in nbb would have been the obvious
implementation and the wrong one: a second resolver is a second answer to
disagree with the first, and the disagreement would be silent.

Maven jars are deliberately not in the lock. nbb cannot load a `.jar`, so they
were never part of what this path resolves, and recording machine-local
`~/.m2` paths would make the lock unreproducible for nothing.

### Nothing may return an empty classpath

Both resolvers now return a closure or nothing, and `bin/kotoba` fails with an
explicit message naming the fix. The fallback to `clojure -Spath` remains for a
checkout whose lock has not been regenerated yet — not as a second way of
getting an answer.

## Verification

- **Parity**: the lock-resolved directory set is byte-for-byte the gitlibs
  half of `clojure -Spath`'s output, and `compile --target aarch64-macos`
  produces a **byte-identical** `.kexe` under either resolver.
- **The property**: with `clojure` stubbed to exit 127 and a cold cache,
  `bin/kotoba -M check` and `-M compile --target aarch64-macos` both succeed.
- **Fail-closed**, 11 cases in `test/nbb/classpath.cljs`, run by
  `npm run test-nbb-classpath` on nbb with `--classpath src` and nothing else —
  no JVM in the test for the JVM-free path. A stale lock, an unsupported
  version, an empty lock, a missing lock, a checkout at the wrong commit, and a
  locked path that does not exist are each refused with a `:phase`. The fetch
  path is exercised offline against a `file://` origin.

## Not done

- **CI does not yet run `npm run test-nbb-classpath`**, and no job proves the
  JDK-free property on a runner without a JDK. Both are one edit to
  `.github/workflows/test.yml`, which a token without the `workflow` scope
  cannot push. The edit: add `- run: npm run test-nbb-classpath` beside the
  other `test-nbb-*` steps, and a small job that installs Node but no JDK and
  runs `bin/kotoba -M compile` against a fixture.
- **The `scripts/test-nbb-*.cljs` launchers still call `clojure -Spath`**
  themselves to build the classpath for tests that need the full dependency
  set. They can move to this resolver; out of scope here, and unlike
  `bin/kotoba` they are not the compiler's front door.
- **Everything other than `compile`/`check`** — `sbom`, `attest-release`,
  `verify-release`, `sign`, `run`, `package-ios` — is still JVM-only by
  `bin/kotoba`'s own dispatch. That boundary is unchanged by this ADR and is
  the next thing in the way of a JDK-free release path.
