# Try Kotoba / Amu on an Apple Silicon Mac

`bin/amu` is a native ARM64 Mach-O built and rebuilt by Amu selfhost.
`bin/kotoba` and `bin/kotoba-compiler` resolve to that same executable.
No Linux VM, Rosetta, Node, JVM, C compiler or hosted launcher is needed.
The native Kotoba packager emits the runnable Mach-O; macOS `codesign`
adds its required ad-hoc signature.

This is a bounded native first run, not qualification of the complete Mac
runtime, all CLI commands or an independent-user release. The existing
Linux starter's fuel/capability expectations are Linux runtime checks and
must not be claimed as Mac results.

## Get and verify the native entry

Use a new checkout so existing work is preserved:

```sh
git clone https://github.com/kotoba-lang/amu.git amu-mac
cd amu-mac
git rev-parse HEAD
test "$(uname -s)" = Darwin
test "$(uname -m)" = arm64
file bin/amu
shasum -a 256 bin/amu seed/bootstrap/aarch64-macos/kotoba-packager-root.macho
codesign --verify --strict bin/amu
codesign --verify --strict seed/bootstrap/aarch64-macos/kotoba-packager-root.macho
otool -L bin/amu
```

Expected compiler SHA-256:
`361f32e1adc9665d11986fc8e6053dcd3ace4efde5f28a8d885850b11a7dab92`.
Expected packager SHA-256:
`45d1271c70ce2e4fb33113af25278c23af20f007a618e82782222f4b72e215f8`.
`file` must identify ARM64 Mach-O and `otool -L` must list no dylibs.
Stop on a digest or signature mismatch. Source/image pins and fixed-point
scope are in `seed/bootstrap/aarch64-macos/root.json`.

## Check, compile, package and execute

Run this from the checkout. The work directory is private and separate
from the repository. FD3 explicitly grants that directory to the native
compiler and packager; it does not grant the rest of the filesystem.

```sh
AMU="$PWD/bin/amu"
PACKAGER="$PWD/seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"
TRIAL=$(mktemp -d "${TMPDIR:-/tmp/}amu-mac-first-run.XXXXXX")
cd "$TRIAL"
printf '(ns hello (:export [main]))\n(defn main [] :i64 42)\n' > hello.kotoba
"$AMU" check hello.kotoba 3< .
"$AMU" compile hello.kotoba --target aarch64-macos --output hello.kseed 3< .
"$AMU" extract-native hello.kseed --symbol main --output hello.raw 3< .
```

For this literal program, extraction prints `:offset 0, :length 12, :arity 0`.
Use that native-reported offset (0) in the packager:

```sh
"$PACKAGER" hello-unsigned.macho hello.raw fs2-cli-stdio-general 0 3< .
cp hello-unsigned.macho hello.macho
chmod 700 hello.macho
codesign --force --sign - hello.macho
codesign --verify --strict hello.macho
./hello.macho 3< .
echo "$?"
```

The program returns its integer through the process exit status: **42**.
It does not print `42`. If your shell uses `set -e`, temporarily disable it
while observing this intentionally nonzero exit status.

Change `42` to `43` in `hello.kotoba`, then repeat compile, extract, package,
copy, sign and execute. Extraction still reports offset 0 for this fixture;
the native program must now exit **43**. Compiling only creates a `.kseed`
container; running that container directly is not a supported Mac command.

## Pinned input and refusal checks

KSL1 uses a virtual absolute source name. `/hello.kotoba` here refers to the
FD3 directory's `hello.kotoba`, not the host filesystem root. The lock file
and output names remain basenames:

```sh
SOURCE_SHA=$(shasum -a 256 hello.kotoba | cut -d ' ' -f 1)
printf 'KSL1\nentry /hello.kotoba\nfile %s /hello.kotoba\n' "$SOURCE_SHA" > hello.ksl
LOCK_SHA=$(shasum -a 256 hello.ksl | cut -d ' ' -f 1)
"$AMU" check /hello.kotoba --source-lock hello.ksl --source-lock-sha256 "$LOCK_SHA" 3< .
"$AMU" compile /hello.kotoba --target aarch64-macos --output pinned.kseed \
  --source-lock hello.ksl --source-lock-sha256 "$LOCK_SHA" 3< .
"$AMU" check /hello.kotoba --source-lock hello.ksl \
  --source-lock-sha256 0000000000000000000000000000000000000000000000000000000000000000 3< .
```

The last command must exit 1 with `E6015`. Omitting `--target` from compile
must exit 1 with `E2` and create no output. Do not suppress these refusals.

Current limitation ([KOTOBA-169](https://linear.app/kotobalabs/issue/KOTOBA-169)):
slash-containing output or source-lock names can trigger SIGTRAP in the Mac
runtime instead of a named refusal. Use basename output/lock names within
FD3. Arbitrary paths and a complete Mac filesystem API are not supported.

## Report a trial or a small fix

Record the checkout revision, macOS/CPU, compiler and packager hashes,
commands, exits 42 and 43, and sanitized diagnostics. Search existing
[Amu issues](https://github.com/kotoba-lang/amu/issues) before filing a public
report. Do not include home-directory paths, usernames, secrets or unrelated
logs. Identify the result as Mac native first-run observation; it is not
an independent qualification when performed by the author or their agent.

For a small reproducible fix, use a separate branch, explain before/after
behavior, include positive and refusal verification, and open an Amu PR
linking the issue. Keep capability, compiler/runtime and release changes
outside a documentation-only fix. If you cannot push, provide the patch,
commands and a ready-to-use issue/PR body instead of claiming submission.

Maintainers can observe all three actual aliases, source/image pins,
pinned check/compile, wrong-lock and missing-target refusals, native package
signatures and 42 → 43 using:

```sh
python3 scripts/seed/check-public-macos-product.py --output /a/new/private/output-directory
```

Python only stages bytes and records native processes in that check. It
does not compile, emit machine code or supply a runtime fallback.
