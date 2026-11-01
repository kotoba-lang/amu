# Try Kotoba / Amu on an Apple Silicon Mac

`bin/amu` is a native ARM64 Mach-O built by Amu selfhost. The
`bin/kotoba` and `bin/kotoba-compiler` aliases use that same native CLI.
Checking, compilation, packaging and host operations run as Amu-built
native code; macOS `codesign` supplies the platform's ad-hoc signature.

## Get and try it

Use a new checkout:

```sh
git clone https://github.com/kotoba-lang/amu.git amu-mac
cd amu-mac
git rev-parse HEAD
bin/amu check examples/foundation-starter/hello.kotoba
bin/amu compile examples/foundation-starter/hello.kotoba
bin/amu run examples/foundation-starter/hello.kotoba
bin/amu run ./hello
./hello
```

`check` prints `ok`. `compile` creates `hello` in the current directory.
Each of the last three commands prints **42** and exits **0**. No `3< ...`,
`--target`, source lock, extraction, packaging or signing command is needed.
No Linux VM, Rosetta, Node, JVM, C compiler or hosted launcher is needed.

To choose an output path, use `-o PATH` or `--output PATH`. Existing output
files are preserved; choose a new path if `EOUTPUT` is reported. Input/output
paths may contain spaces or Unicode. Symlink and nonregular inputs refuse.

Try a source change independently of the checked-in example:

```sh
printf '(ns hello (:export [main]))\n(defn main [] :i64 43)\n' > hello43.kotoba
bin/amu check hello43.kotoba
bin/amu compile hello43.kotoba -o hello43
bin/amu run hello43.kotoba
bin/amu run ./hello43
```

Both `run` commands print **43** and exit0. A previously compiled `hello`
continues to print42 because its own captured source is part of the artifact.
Guest arguments follow `--`: `bin/amu run FILE.kotoba -- ARG...`.

## Current supported scope

The ordinary Mac host accepts a single canonical `.kotoba` source up to1MiB.
Compile/run require exactly one exported `main [] :i64`. Its complete signed
integer result is printed followed by a newline; it is not truncated to an
8-bit process exit code. User stdout/stderr and CLI arguments are available.
Guests receive no filesystem/process grants. `run` closes inherited descriptors
>=3 and applies a5-second execution deadline to its child. Native compiler helpers use a private
source snapshot and exact KSL1 lock, managed inside the CLI.

Native programs embed their source in the signed Mach-O. `run PROGRAM`
recompiles that source with the pinned compiler, compares the complete signed
image, and executes the regenerated private image. An arbitrary executable
or a changed artifact refuses. Do not put secrets in source you distribute.

Unsupported flags/targets and project imports refuse. Complete Darwin runtime,
project/package/resolver parity and independent-user release qualification
remain open. Linux starter fuel/capability results are separate Linux checks.
The low-level `amu-full-root.macho` retains its explicit-target/FD3 interface
for bootstrap development; it is not needed for this first run.

## Verify provenance

```sh
file -L bin/amu
shasum -a 256 bin/amu
codesign --verify --strict bin/amu
otool -L bin/amu
```

Expected CLI SHA-256:
`9bba503de9e1023bb13ce13a41ecc92e5f68effa60553f0b3f39ce6da0d03ca6`.
`file -L` identifies ARM64 Mach-O; `otool -L` lists no dylibs.
The source recipe, image, compiler and packager pins are in
[`cli.json`](../../seed/bootstrap/aarch64-macos/cli.json).
The full compiler/packager selfhost fixed points are separately recorded in
[`root.json`](../../seed/bootstrap/aarch64-macos/root.json).

The CLI verifies the complete compiler and packager SHA-256 before invoking
them. A missing/changed dependency reports `EPROVENANCE`; it does not select
a program from `PATH` or fall back to another host.

## Give this task to an AI agent

Copy this request as-is, choosing a fresh checkout destination:

> Clone https://github.com/kotoba-lang/amu into a new directory, preserving
> all existing work. Read its AGENTS.md and record the commit, macOS version,
> CPU architecture and bin/amu digest. On an arm64 Mac, follow the ordinary
> check/compile/run commands in examples/foundation-starter/MACOS-ARM64.md.
> Confirm ok, then printed42 with exit0 for source and compiled-artifact run.
> Create a separate source returning43 and confirm printed43 with exit0.
> Test an incompatible main return type, an unknown flag and an existing
> output path: each must refuse without overwriting an existing file. Do not
> add FD3, a hosted launcher, JVM/Node/C compiler or a target workaround.
> If a command fails, preserve the exact sanitized reproduction and search
> existing Amu GitHub issues before filing a focused public issue. Include
> revision, platform, digest, command, expected/actual stdout and exit status;
> omit usernames, absolute personal paths, secrets and unrelated logs.
> If a small fix is possible, make it on a separate branch, add meaningful
> native positive/refusal checks, commit/push and open a PR linked to the
> issue. Explain the trigger, resulting behavior, verification and remaining
> limits. Do not merge or claim independent release qualification. If GitHub
> write access is unavailable, return a patch and ready-to-submit issue/PR
> text. Finish with links and a precise distinction between observed,
> fixed locally, CI-passed, submitted and merged states.

Use [Amu issues](https://github.com/kotoba-lang/amu/issues) and
[Amu pull requests](https://github.com/kotoba-lang/amu/pulls) for public reports.
A successful author/maintainer-agent trial is not independent-user evidence.

Maintainers can reproduce the public image and run all ordinary CLI controls:

```sh
python3 scripts/seed/check-public-macos-product.py --output /a/new/output-directory
```

That observer only stages/hashes bytes and observes native processes.
It rebuilds the native CLI, compares every public payload byte, exercises
all three aliases and checks positive/refusal/resource cases.
