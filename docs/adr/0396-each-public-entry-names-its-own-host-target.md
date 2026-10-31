# ADR 0396 -- each public entry names its own host target (KOTOBA-174)

- Status: Accepted (implemented in this change; native qualification of the new image is separate)
- Date: 2026-10-31
- Deciders: owner, 2026-10-31 (Linear KOTOBA-174, option C, "おすすめで")
- Supersedes: [ADR 0355 "Kototama is the default program target"](0355-kototama-is-the-default-program-target.md).
  ADR 0351 is historical. The other ADR numbered 0355 (GPU vendor dispatch) is unrelated and unchanged.
- Related: kotoba-lang/kotoba-lang#840, whose contract says an omitted target means the host native target.
  KOTOBA-171 is the bounded Mac host CLI, `seed/macos-cli.kotoba`. ADR 0388 covers derived pins.

## Context

kotoba-lang#840 says an omitted `--target` means the host's native target.
amu did not do that consistently, and its documents disagreed with each other and with the code:

- **ADR 0351** (2026-09-24) resolved the host from Node's `process.platform`/`process.arch` in the nbb launcher.
  That launcher is retired (`docs/retired/legacy-public-entry-20261023`), so the ADR describes no current code.
- **ADR 0355** (2026-10-14) made Kototama the default. No current entry does this. Kototama exists only as the explicit
  `compile-kototama*` commands. `drv-target-ok` (`seed/90-drv.kotoba`) accepts only `aarch64-macos`.
  `seed/78-full-entry.kotoba` refuses an omitted target with `E-TARGET` (E2).
- **`CHANGELOG.md`** still described ADR 0351's launcher default as current.
  The legacy `scripts/test-default-target.cljk` asserted ADR 0355's Kototama default. CI does not run it.

The compiled compiler cannot tell which host it runs on. The Mac root and the aarch64-linux root run the same
`F.kseed`, and only their wrappers differ. The x86 compiler is built from the same `sourceUnity`. No runtime answers
a "which target" request. A runtime host identity would be a new ABI for every program (option A). A packager-written
context word would change the adopted core (option B). The owner chose **option C**: each public entry point names its
own host, as KOTOBA-171 already does for the Mac CLI (`seed/macos-cli.kotoba` spawns the root with `--target
aarch64-macos`).

## Decision

1. **An omitted `--target` on a public entry is that entry's fixed host target. There is no Kototama, Wasm or
   other fallback anywhere.**

   | public entry | fixed host | omitted `--target` | explicit `--target` |
   |---|---|---|---|
   | `bin/amu`, `bin/kotoba`, `bin/kotoba-compiler` (Mac CLI, `seed/bootstrap/aarch64-macos/cli.json`) | `aarch64-macos` | compiles for `aarch64-macos` (unchanged, KOTOBA-171) | usage error, exit 2 (unchanged) |
   | `bin/x86_64-linux/amu`, `.../kotoba`, `.../kotoba-compiler` (new; `native-product.json` `hostEntry`) | `x86_64-linux` | read as `compile SRC --target x86_64-linux ...` | exactly the engine-neutral compiler's behaviour |

   Linux ARM64 has no public product entry. Its root (`seed/bootstrap/aarch64-linux-static-root.elf`) stays a root.

2. **The compiler roots stay engine-neutral.**
   - This covers `seed/78-full-entry.kotoba`, `seed/bootstrap/aarch64-macos/amu-full-root.macho`,
     `seed/bootstrap/aarch64-linux-static-root.elf` and the Linux x86_64 compiler `bin/amu-linux-x86_64` (with its
     two `-linux-x86_64` aliases), which is also the CDCI producer.
   - They keep refusing an omitted target with E2.
   - Their explicit-target behaviour is unchanged.
   - `bin/amu-linux-x86_64` is still the `native-product.json` `entry`/`image`, with the same F1=F2=F3 contract.

3. **How the Linux x86_64 entry names its host.**
   - The compiler reads its command line by fixed position (`seed/70` xg-main, `seed/75` xs-command), and the runtime
     answers argv (wire 38). So the host entry is a separate image of the same complete source:
     `compile <FULL-MANIFEST unity> --target x86_64-linux --output IMAGE --format host-entry`.
   - That image is the `--format static` compiler with one difference: its standard `kxrt-start` sets the argument
     vector through `kxrt-host-argv` (`seed/76`). The host start is spliced from `xs-rt-start` at its one argv
     assignment. If that point is missing or appears twice, the splice yields no start and the build refuses with E7102.
   - Context word 408 stays 0, so the image behaves as static in every other respect.
   - A command line whose first argument is exactly `compile`, that has a source argument, and that has no argument
     exactly `--target` gets `--target x86_64-linux` as its arguments 2 and 3. These are new strings in a private
     anonymous mapping. Every other command line is the process's own.
   - The result is byte-identical to writing `--target x86_64-linux`, which the gates check.
   - Only the build command gains a value. The engine-neutral compiler now accepts `--format host-entry` for
     `--target x86_64-linux`, as it already accepts `static`, `kx64-runner`, `launcher` and `b2`. It builds an image and
     changes no other command line. No entry accepts another target or flag.

4. **Pins.**
   - `native-product.json` gains `hostEntry`, which records the entry, aliases, target, build line and image pin.
   - `write-bootstrap-descriptors.py` installs `H-x86_64.elf` from the Mac cross build as `bin/x86_64-linux/amu`.
   - `check-macos-cross-linux-candidates.py` builds that image and refuses when it equals the compiler image.
   - `repin-derived-pins.py` lists it as a derived pin (ADR 0388).
   - `nativeQualified` is false until native CI qualifies the image. This change does not promote any qualification
     flag.

## Consequences

- `bin/x86_64-linux/amu compile hello.kotoba --output hello --format static` writes the same bytes as
  `bin/amu-linux-x86_64 compile hello.kotoba --target x86_64-linux --output hello --format static`.
- The engine-neutral compiler still refuses the same command line without `--target` (E2).
- The FD3 / `KEXE_CAP_RESOURCES_35` interfaces are unchanged. This decision chooses the target only. It adds no host
  grants, packaging or signing to Linux.
- Every new public host entry must name its host in the same way, with its own image or host program and its own
  gates. A compiler root never gains a host default.
- Each seed change regenerates one more ~10 MiB derived image.

## Evidence

`scripts/seed/check-host-default-target.py` runs natively and uses positive and negative controls:

- **x86_64** (`mac-selfhost-aiueos.yml` `native-cross-x86_64`, on the Mac-produced candidates):
  - The native x86 compiler rebuilds the host entry byte for byte.
  - An omitted target equals an explicit `x86_64-linux` on both images, for `static`, `kx64-v1`, `kx64-runner` and the
    default format.
  - The omitted-target program executes to `:result 42`.
  - No omitted-target output is Wasm or Kototama. Control: the detector flags the explicit `wasm32-browser` output.
  - Explicit command lines give identical results on both images: `aarch64-linux`, unknown targets including
    `kototama`, `--target` in a later position, `check` and usage errors.
  - The compiler refuses `compile SRC` and `compile SRC --output OUT` with E2 and writes nothing. With `--format` and no
    target, the flag is already a usage error (E1).
  - Control: `aarch64-linux` output differs from the omitted-target output.
- **aarch64** (`native-cross-arm64`): the Linux ARM64 root refuses an omitted target with E2 and refuses an unknown
  target. Control: the explicit `aarch64-linux` compile runs to 42.
- **macos** (`mac-root`):
  - The public CLI's omitted-target artifact is Mach-O, and `run` verifies it against a fresh explicit
    `aarch64-macos` recompile. Control: a tampered copy is refused.
  - An explicit `--target` (`aarch64-macos`, `wasm32-browser`, `kototama`, unknown) stays a usage error.
  - The Mac root refuses an omitted target and an unknown target with E2. Control: the explicit `aarch64-macos` compile
    succeeds.
