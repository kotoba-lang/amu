# Full-size Amu `main` packaged for macOS, without a runtime

`seed/macos-large-main-packager.kotoba` removes the 4 KiB generated-function
limit and fixed 16 KiB `__TEXT` extent of the earlier diagnostic packager. It
calculates a 16 KiB-aligned image extent from the extracted function, sets the
Mach-O `__TEXT` and `__LINKEDIT` offsets to that extent, and checks every byte
returned by FS2's write acknowledgement. The FS2 single-value ceiling remains
8 MiB; images whose frame would exceed it refuse with exit 2 before writing.
The previous small-function packager and its execution receipts are unchanged.

On Apple Silicon macOS 26.4, the Kotoba packager produced a 3,260,416-byte
arm64 `MH_EXECUTE` from a 3,254,848-byte Amu full-compiler `main`. The input
was re-extracted with the selfhost-built `F1.elf` and compared byte for byte
before packaging:

| Artifact | SHA-256 |
| --- | --- |
| Full compiler `F1.kseed` | `dec8649a9d095b1f144ecf86dd176a32703a637c4999aa634537978369bc4c18` |
| Matching selfhost `F1.elf` extractor | `1610a3461bed66a17b6c6de7a2bf9f05a37ed60eb012291f0e1e61a7bbf02753` |
| Extracted `main` | `164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e` |
| Kotoba packager source | `112da64149a141659a4c1857e63fdea8904382188e03c99816df36858527fb42` |
| Amu-built packager ELF | `ad09cdae55a174c4560e70c1f1a50065243dbab0cca2cc4e596e860d09cfcb25` |
| Unsigned full-size Mach-O | `520be6af651d71c459fe48a95c99598aba51833a1b9585c66a19d5f21d75a0dc` |

The Kotoba packager was compiled with the pinned ARM Linux Amu root
`285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1`.
Its small 136-byte loop input yielded exactly the existing v3 Mach-O bytes.
Two independent full-size emissions were byte-identical. An 11-byte truncated
function and an 8,373,000-byte function requiring an out-of-budget FS2 frame
both returned 2 without an image. The full-size image was checked for the
complete generated payload and zero padding; `otool -l` showed `__TEXT`
size `0x31c000`, `__LINKEDIT` at that boundary, and `LC_MAIN` at 1024. An
ad-hoc signed copy passed `codesign --verify --strict`; the image has no
`LC_LOAD_DYLIB` or libSystem dependency. The exact readback and signature
digest are in [receipt.json](receipt.json).

`scripts/seed/check-macos-large-main-packager.py` is the host observer. It
pins the compiler, Kotoba source, `F1` input, extracted bytes and unsigned
image; checks the command table, wrapper, payload, padding, positive and
refusal admissions; then signs and verifies a copy. It supplies no compiler,
Mach-O bytes or runtime. The generated image was **not launched**: its
diagnostic wrapper provides only a tiny pure-function fuel context, whereas
the full compiler immediately needs its native context, arenas and capability
runtime. Signing and layout therefore establish packageability, not a
working Mac compiler. These commands still executed in a local Podman Linux
VM. A Darwin-native Kotoba/Amu runtime, actual compiler execution and
self-rebuild, and an entirely Linux-free build/boot/release path remain open
under JUN-417.

To reproduce, stage the pinned `F1.kseed`, `F1.elf`, raw input and this source
in one FS2 `/work` directory. Use the matching `F1.elf` to run `extract-native
/work/F1.kseed --symbol main --output /work/full-compiler-main-reextract.raw`.
Compile this source with the pinned root using `compile ... --target
aarch64-linux --format static`; run the resulting packager with output Mach-O
and raw path arguments. Admit each heavy native command through
`scripts/seed/native_build_queue.py`. Run the observer with the artifact
directory, `F1.kseed`, `F1.elf`, and a new output directory. A public build
must pin the exact source/image hashes in the receipt and replace this Linux
host step with a qualified Mac-native selfhost path before claiming closure.
