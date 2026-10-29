# Amu

Amu checks canonical Kotoba and compiles it through the adopted compiler
lineage. `bin/amu` is an Amu-built, self-rebuilt native **macOS ARM64**
executable. `bin/kotoba` and `bin/kotoba-compiler` name that same Mach-O.
It has no dylib dependency. The unchanged native Linux x86_64 executable
is available explicitly as `bin/amu-linux-x86_64`.

The complete product is `seed/FULL-MANIFEST`: all18 adopted core modules
in a 49-module compiler with native Linux emitters, browser Wasm, bounded
Kototama i64 AOT/receipts/cache, native CDCI/FS2 and the AIUEOS image/EFI route.
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

On an Apple Silicon Mac, use the native CLI directly:

```sh
printf '(ns hello (:export [main]))\n(defn main [] :i64 42)\n' > hello.kotoba
bin/amu check hello.kotoba
bin/amu compile hello.kotoba
bin/amu run hello.kotoba
bin/amu run ./hello
```

`check` prints `ok`. `compile` creates the signed native executable `hello`;
use `-o PATH` or `--output PATH` to choose a new output. Both `run` commands
print `42` and exit zero. Change the source to `43` and run it again.
No FD3, target, source lock, extraction, packaging or signing command is
needed. Existing output files are preserved. Unicode and space-containing
paths work. See the [Mac ARM64 first run](examples/foundation-starter/MACOS-ARM64.md).

This public Mac host chooses its native target and accepts a single canonical
Kotoba source (up to 1 MiB), with one exported `main [] :i64` for compile/run.
Native programs include their source. `run PROGRAM` recompiles that source,
checks the complete generated image and runs the regenerated private image.
Guest filesystem/process capabilities are denied; `run` closes inherited
descriptors >=3 and limits child execution to5 seconds. Arguments follow `--`. Full Mac runtime and independent-user release
qualification remain separate.

The full bootstrap compiler remains available at
`seed/bootstrap/aarch64-macos/amu-full-root.macho` for explicit-target,
FD3-scoped development commands and exact KSL1 project locks. Its omitted
target still refuses `E2`; the public Mac host default does not change that
engine-neutral compiler contract. Unsupported public flags refuse instead
of silently dropping source paths or locks.

Linux users use `bin/amu-linux-x86_64` and the
[pinned Linux starter](examples/foundation-starter/README.md), whose immutable
snapshot retains its original Linux entry. No Node/NBB/KBB, JVM, C compiler,
Linux VM or emulator is used by the Mac CLI.

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
