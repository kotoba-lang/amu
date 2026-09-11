# ADR 0347: The JVM route is removed — Kotoba and the amu native/nbb compiler only

## Status

Accepted (2026-09-11). Owner instruction, same day: 「jvm 経路は除去して,
kotoba, amu native compiler only」. Extends the superproject's
`adr-2609111500` (the `.cljk` rename), which had left the JVM route "broken
by decision, recovered per component"; this ADR decides that it is not
recovered. It is removed, and what it carried is listed here as the port
ledger.

## Decision

1. **No code path in this repository spawns `clojure`, `clj`, `java` or
   `javac` at run time.** `bin/amu` and `bin/kotoba` route every command to
   the nbb entrypoints (`src/kotoba/compiler/nbb/*_cli.cljk`) or refuse with
   exit 64 naming the command and target. `--jvm-free` is accepted and means
   nothing — every invocation is JVM-free — and is kept so the call sites
   that spell it keep working.
2. **The dependency closure comes from `deps-lock.edn`, resolved with git
   alone, always.** The `kbb -Spath` fallback in both launchers is gone.
   The lock now also records the closure the `:test` alias adds
   (`:lock/alias-entries {:test [...]}`), and `print-classpath.cljk --alias
   test` reproduces it; `scripts/lib.cljk`'s `lock-classpath` replaced
   `kbb -Spath [-M:test]` in the seventeen nbb test runners. An alias the
   lock does not carry is a refusal, not an empty classpath.
3. **The one place a JDK is still used is `scripts/lock-classpath.cljk`, at
   authoring time, to WRITE the lock.** It is tools.deps' resolver, and a
   second resolver written here would be one to disagree with (that
   script's own words). It is not a route: nothing that compiles, tests,
   packages or serves runs through it, and CI runners carry no JDK.
4. **`deps.edn` keeps `:test` as a dependency declaration** (the extra git
   deps the nbb test runners need, which the lock reads) and drops every
   launch alias: `:run`, `:native-run`, `:conformance`, `:runtime-bench`,
   `:native-conformance`, `:fuel-estimate`, `:ipld-adl-conformance`.
5. **The GitHub workflows install no Clojure CLI.** `check-workflows.cljk`
   now refuses a `setup-clojure` step instead of pinning its version. The
   `provider-qualification` and `downstream-murakumo` jobs, `clojure
   -M:test`, and the steps for scripts that cannot run without the JVM
   (below) are removed from `test.yml`.
6. **A script that needed the JVM refuses by name** — `REFUSED
   could-not-answer reason=jvm-route-removed needs=<what> ledger=...`, exit
   2 — rather than failing on a missing `clojure`. A run of one is never
   mistaken for a red test of the thing it used to test.
7. **Scripts whose premise was "the JVM route equals the nbb route" are
   retired** (deleted): `scripts/native-route-parity.cljk` and
   `scripts/test-definition-cid-parity.cljk`. With one route there is no
   second one to be identical to. The claim they protected — the definition
   CID is a content address, not a build identifier — is now carried by the
   nbb route alone and by `scripts/test-definition-cid-cache.cljk` on that
   route.

## What was measured

- Before: at `adb05c20` (main after #935) `bin/amu keygen` and `amu compile
  --target cljs-browser` spawned `kbb -M:run`, and `bin/amu`'s resolver
  fell back to `kbb -Spath` when the lock was stale. After: both exit 64
  with the command named; a stale lock exits 70 naming
  `scripts/lock-classpath.cljk`. The nbb route is unchanged: `kotoba -M
  check`, `amu compile --target wasm32 --policy`, `--target
  x86_64-aiueos-kernel-v1`, `--target js-browser` all produce the same
  artifacts they did.
- `npm run test-nbb-wasm32` (53 cases), `test-nbb-project`,
  `test-nbb-clock-transport`, `test-nbb-http-provider`,
  `test-nbb-fuel-estimate`, `test-nbb-log-provider`,
  `test-nbb-storage-provider`, `test-nbb-portable-tests` (7 namespaces / 56
  tests / 354 assertions), `test-policy-bound-provenance`,
  `test-ci-dependency-prefetch`, `check-workflows` — green on the lock
  resolver with no `clojure` spawned.
- `test-policy-bound-provenance` lost its JVM half: it compiled every
  fixture twice and asserted byte identity between the routes. The assertions
  about the nbb route itself (policy changes provenance and bytes, `--fuel`
  changes bytes, the output set is committed and admitted, a forbidden
  capability and an excessive budget are refused) stay.

## The port ledger — what the JVM route carried and where it stands

JVM CLI commands (`kotoba.compiler.cli`) with no nbb implementation. Each is
a refusal today; each is a port to do, in this order of consequence:

| command | why it matters | status |
|---|---|---|
| `keygen`, `public-key`, `trust-key`, `trust-runtime`, `sign`, `verify-signed`, `verify`, `inspect`, `receipt`, `verify-receipt`, `verify-chain` | the trust plane | **ported 2026-09-11** (ADR 0348, `kotoba.compiler.trust-cli`, `test-nbb-trust`). `receipt.cljk` asked `integer?` of read-back bigints and refused its own receipts on Node; now `guest-integer?` |
| `sbom`, `attest-release`, `verify-release` | release evidence | **ported 2026-09-11**, same namespace; `kotoba.compiler.release` gained a `:cljs` branch (node fs/crypto) with the same refusals. `test-release` (7 refusals) and `test-output-set-publisher-auth` are un-refused and back in CI |
| `package-ios` | iOS static Mach-O object + manifest | **ported 2026-09-11**; `ios-aot/package` was portable, its `:code` and entry offset are narrowed from bigint for `kotoba.object.macho64`'s byte gate. Verified `Mach-O 64-bit object arm64`, links with `runtime/ios/kotoba_ios_host.c` into a static archive locally (Xcode 26.6; the pinned-Xcode-16.2 conformance is CI's macos-14) |
| target `cljs` / `cljs-browser` / `cljs-node` | the ClojureScript-source emitter | **ported 2026-09-11** (`js_cli.cljk` `compile-cljs!`); `backend.cljs` admits bigint literals and prints them as digits. The emitted source is EXECUTED in `test-nbb-release-and-emitters`: `fact 5 = 120`, `fact 10 = 3628800`, `forever` traps on fuel |
| `run`, `measure-runtime` | executing artifacts from the CLI, and the loader identity a receipt's `:runtime` refers to | **blocked**: `kototama.native.executor` is a 1,238-line JVM driver around `tools/kexe_loader.c` -- toolchain identity (compiler resource manifest, dependency files), reproducible double build, argument marshalling for records/variants/strings/regions, supervisor-report validation, bounded process I/O. `jdk-free-native-conformance.cljk` already builds and drives the loader on Node, so the mechanism exists; the port is the driver. `conformance.cljk` refuses on exactly these two |
| `coverage`, `sign-coverage-evidence` | coverage evidence | **blocked**; `kotoba.compiler.coverage` uses `java.nio.file` + `MessageDigest` (136 lines) -- the same shape as the release port |
| the divergent x86-64 aiueos kernel IMAGE | the live-boot GDT/TSS shim lives in the JVM twin of `elf64` | **blocked**, as before (`divergentImageReason` in `bin/amu`); the kernel OBJECT, user image and UEFI application are on the nbb route |

JVM mains and harnesses:

| script | status |
|---|---|
| `scripts/perfgate_qualify.cljk` (JVM main) via `scripts/perfgate-qualify.cljk` | refuses; `runtime-multidomain-suite.mjs` and `postalloc-scheduling-benchmark.mjs` call it |
| `scripts/test-ipld-adl-wasmtime.cljk` (`-M:ipld-adl-conformance`) | refuses |
| `scripts/conformance.cljk` (the CI language-conformance harness) | refuses on `run` / `measure-runtime` only; its signing, receipt, release, inspect, iOS and cljs blocks are carried by `test-nbb-trust`, `test-nbb-release-and-emitters`, `test-release` and `test-output-set-publisher-auth` (all in `test.yml`); its compile coverage by `test-nbb-wasm32` / `test-jdk-free-native` / `test-policy-bound-provenance` |
| `scripts/cloud-itonami-route-parity.cljk` (+ health / oauth-resource parity) | refuses; the Clojure oracle namespaces are `.cljk` and look portable — running them on nbb is the port, unmeasured |
| `kotoba.compiler.backend-qualification` (CI `provider-qualification` job) | job removed; the qualification must move to the nbb route |
| `downstream-murakumo` KIR drift gate (`kbb -M:test:dep` in murakumo) | job removed; murakumo's own suite decides how it runs without a JVM |
| `runtime-comparison.mjs` comparators `clojure`, `clojurescript` | dropped from the default list; adapters kept |

## Consequences

- **Port status after the first day**: `run`, `measure-runtime`, `coverage`
  and `sign-coverage-evidence` remain; the rest is on the nbb route with
  executed evidence. Three defects of one shape surfaced on the way and are
  fixed: `integer?` against a read-back bigint in `receipt`, `backend.cljs`
  and (via `ios-aot`) `macho64`'s byte gate. Any remaining `integer?` on a
  value that crossed the kotoba reader is the same bug waiting. Two launcher
  defects too: `.kexe` was not in `bin/amu`'s path-extension table, and
  `bin/kotoba` spawned the nbb child in the checkout so a relative
  `--output` landed there.
- Every claim of the form "JVM-free" is now trivially true and therefore
  says nothing; the claim that matters is **"implemented on the nbb/native
  route"**, and the refusal at exit 64 is what makes its absence visible.
- The JVM suite (`kbb -M:test`) was the largest body of tests in this
  repository. It is not running. This ADR does not pretend otherwise: the
  count above is the debt, and the nbb-route suites are the coverage that
  exists today.
- `deps.edn` remains the declaration the lock is authored from; a JDK is
  needed once, by whoever regenerates the lock, and by nobody else.
