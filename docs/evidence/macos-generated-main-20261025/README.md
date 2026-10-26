# Amu-generated code executed by macOS

On an Apple Silicon Mac running macOS 26.4, the pinned Amu-built native ARM
compiler (`seed/bootstrap/aarch64-linux-static-root.elf`, SHA-256
`285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1`)
compiled three Kotoba sources with `--target aarch64-macos`:

| Source | Extracted `main` | Mac exit |
| --- | ---: | ---: |
| `seed/macos-generated-main42.kotoba` | 12 bytes | 42 |
| `seed/macos-generated-main43.kotoba` | 12 bytes | 43 |
| `seed/macos-loop-main.kotoba` | 136 bytes | 42 |

The two constant-return artifacts are 34-byte `.kseed` containers. The loop
artifact is 160 bytes; `extract-native --symbol main` reports code offset 60,
length 136, arity 0. The loop charges generated fuel while incrementing its
counter to 42. A repeat compile of the 42 source was byte-identical.

`seed/macos-generated-main-smoke.kotoba` is a Kotoba source packager. It reads
the extracted function through FS2, bounds it to 12..4096 bytes, writes a
16 KiB arm64 Mach-O, and checks the entire FS2 write acknowledgement. Its
eight-instruction entry wrapper at file offset 1024 allocates a 16-byte stack
context, places fuel 1000 at `[x7+8]`, calls the generated code at offset
1056, then passes its return value to the Darwin `exit` syscall. The v3 image
has six load commands: three segments, `LC_LOAD_DYLINKER`, `LC_MAIN`, and
`LC_BUILD_VERSION`. It has no `LC_LOAD_DYLIB` and `otool -L` lists no linked
library. The platform dyld still starts it; the wrapper is diagnostic host
code and provides no general runtime or capabilities.

The unsigned image SHA-256 values are
`6383ec2b8ea71d5f046f75f091eee0ea95acb04b83aa4e497d0b3f97976a724f`,
`0cc1ccca32e97bfd4b96036ef2e10946a8f8358c6d0ba2238deabbac9e30ffa5`,
and `de3c61bf00d32ec5ad82b155292437aba0cbd83636c23e5f08bd7d3e5b2e35ef`
in table order. An 11-byte truncated function was refused with exit 2 and no
image. A second v3 loop image emission was byte-identical. Changing only the
loop wrapper's initial fuel from 1000 to 1, then
signing the modified image, produced a Mac trap (process return code -5)
without output. This is a negative control for the generated fuel charge.

`scripts/seed/check-macos-generated-main-smoke.py` pins the compiler, source,
packager, `.kseed`, raw function, and unsigned image digests. It checks the
Mach-O structure and payload bytes, signs diagnostic copies with macOS
`codesign`, verifies their signatures, and launches all three images plus the
low-fuel control. The observer also checks the exact load-command sequence and
vacated libSystem command bytes. [receipt.json](receipt.json) records the v3
observed results.
Python is a host observer; Kotoba/Amu produced the code and images.

The build used an existing local Podman Linux VM only as a host for the pinned
native Linux ARM compiler and Kotoba packager. The builds were admitted
through `scripts/seed/native_build_queue.py`. This proves a bounded
`aarch64-macos` codegen-to-execution path with pure control flow and fuel. It
does **not** prove a Mac native compiler executable, full Amu runtime, general
relocations, capability calls, Mac self-rebuild, Itonami, AIUEOS daily use, or
Linux-free build closure. Separately, Amu #1574's selfhost full-compiler
`F1.kseed` (SHA-256 `dec8649a9d095b1f144ecf86dd176a32703a637c4999aa634537978369bc4c18`)
was inspected with its matching ARM root
`1610a3461bed66a17b6c6de7a2bf9f05a37ed60eb012291f0e1e61a7bbf02753`.
`extract-native main` returned 3,254,848 bytes (SHA-256
`164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e`)
whose entry immediately reads the runtime context at `x7`; packaging alone
cannot run that compiler. A Darwin runtime and product packaging remain
necessary under JUN-417.

The earlier v2 image declared an unused libSystem load command. A diagnostic
host transformation removing it executed with the same result; the Kotoba
packager now emits those exact v3 bytes. A separate diagnostic
`LC_UNIXTHREAD` image with no dyld command passed code-sign verification but
was killed at launch on this host. This single observation does not establish
whether a dyld-free product route is possible. The accepted v3 proof uses
dyld and no libSystem load command.

Reproduction sequence (with a new artifact directory mounted at `/work` and
`seed/bootstrap` mounted read-only at `/compiler`):

1. Compile the three source files with the pinned root using
   `compile /work/<source>.kotoba --target aarch64-macos --output /work/<stem>.kseed`.
2. Extract each with `extract-native /work/<stem>.kseed --symbol main
   --output /work/<stem>.raw`.
3. Compile the Kotoba packager using `compile
   /work/macos-generated-main-smoke.kotoba --target aarch64-linux --output
   /work/macos-generated-main-smoke-v3.elf --format static`.
4. Run the packager with an output Mach-O and raw function path as its two
   arguments, granting FS2 only the artifact directory. Repeat for all three.
5. On the Mac, run `python3 scripts/seed/check-macos-generated-main-smoke.py
   ARTIFACT_DIR NEW_OUTPUT_DIR` to produce signed diagnostic copies and a
   fresh receipt.
