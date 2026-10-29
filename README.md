# Amu

Amu checks canonical Kotoba and compiles it through the adopted compiler
lineage. The public `bin/amu` is an Amu-built, self-rebuilt native Linux
x86_64 executable. `bin/kotoba` and `bin/kotoba-compiler` name that same image.
It has no ELF interpreter or dynamic runtime dependency.

The complete product is `seed/FULL-MANIFEST`: all18 adopted core modules
in a 48-module compiler with native Linux emitters, browser Wasm, bounded
Kototama i64 AOT/receipts, native CDCI/FS2 and the AIUEOS image/EFI route.
The frontend, lowering, optimization and AArch64 backend measured by the
19-workload Embench corpus remain in this lineage. This migration publishes
correctness evidence; it publishes no new performance score.

`compile-kototama` compiles the closed `kototama.pure-i64-aot/v1` profile
from canonical DAG-CBOR into metered scalar native code using that same
core. It has empty guest authority, no heap and a static stack bound.
See [the profile, command and native gate](docs/kototama-i64-aot.md).
The explicit `kototama.pure-i64-receipt/v2` profile also accepts fuel0 and
returns typed failure/spent/remaining receipts with the same closed language
and empty authority. See [its ABI and native qualification](docs/kototama-i64-receipt.md).

## Native compiler use

Start with the [Kotoba / Amu first-run guide](examples/foundation-starter/README.md)
for acquisition and digest checks, a small source change, and explicit fuel
and capability refusals. Its release and host qualification are stated in
the guide; a successful smoke run does not qualify additional platforms.

Run the public executable on native Linux x86_64. No Node/NBB/KBB, JVM,
Clojure, Java, GraalVM, C compiler or C loader is used by this entry.
Other public host platforms remain unqualified.

For a file `hello.kotoba`:

```clojure
(ns hello (:export [main]))
(defn main [] :i64 42)
```

```sh
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$PWD" ./bin/amu check hello.kotoba
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$PWD" ./bin/amu compile hello.kotoba --target x86_64-linux --output hello.elf --format static
chmod 700 hello.elf
KEXE_ALLOW=- KEXE_FUEL=1000000 KEXE_STRUCTURED_REPORT=1 ./hello.elf
```

Use explicit targets. The engine-neutral default remains a language
contract; this native entry currently refuses an omitted compile target
with `E2`. `aarch64-macos` names the adopted AArch64 payload/container
route, not a standalone macOS application. Native Linux image emission
uses `aarch64-linux` or `x86_64-linux` explicitly.

Project inputs retain every declared `--source-path` and an exact KSL1
`--source-lock`. `--source-lock-sha256` additionally binds the lock bytes.
There is no `--unpinned` escape or legacy source-extension fallback.
Unsupported verbs, flags and targets refuse with named diagnostics.
Package/module-CID integration, worker/test/inspect workflows and other
unimplemented public compatibility surfaces remain tracked work.

See [native product and controller scope](docs/native-public-entry.md),
[the product identity](native-product.json), and
[the compiler-core decision](docs/adr/0370-embench-measured-compiler-core.md).

## Native CDCI

The native controller executes exactly two mandatory roles: Amu selfhost
and Kotoba native. The Amu role reproduces the pinned complete core;
the Kotoba role checks every one of the fixed 24 native cases, including
actual result, process exit and remaining fuel. The controller and gate
are Kotoba source, built into loaderless x86_64 ELF by the same compiler.
Input/image substitution and malformed manifests fail closed.

GitHub Actions and Python perform build/test staging, process observation
and artifact transport. The native controller owns its ordered gate
verdict and receipt; it invokes no shell or hosted interpreter. Controller
artifact qualification, workflow completion and service deployment are
recorded separately in the evidence scope.

The earlier `fleet-ci-gates` / `kotoba-authoring` names, C-loader pins and
CLJK/KBB-first conditions are retired. Old launchers and dependency
manifests are preserved as complete, hashed, non-executable historical
[text](docs/retired/legacy-public-entry-20261023/index.json). They are not
fallbacks or current execution instructions. Historical source and corpus
files remain available for complete native ports.

## Architecture and evidence

Kototama defines the computation and authority contract; Amu is its
compiler, and AiueOS is a separate host/OS implementation. Static hosting,
browser execution, native runtime qualification and live services retain
their own boundaries.

- [Selfhost priority and current contract](docs/selfhost-priority.md)
- [Native evidence](docs/evidence/native-cdci-20261023/)
- [Previous workflow retirement](docs/native-cdci-retirement.md)
- [Compiler decisions](docs/adr/)

The complete former README is retained with its digest in the historical
text archive. Its hosted-route claims do not qualify the native product.

The native-only entry refuses `--format platform-linked` with E2. The
optional provider backend source and corpus are retained, but libc/dynamic-
loader execution is excluded from mandatory native CDCI. The static
launcher, complete core, all24 native cases and hardening remain required.
