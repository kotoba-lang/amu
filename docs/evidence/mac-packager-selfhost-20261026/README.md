# Mac packager self-rebuild diagnostic

The 47-module full Amu compiler F2 ran on Apple Silicon Mac and compiled
`seed/macos-fs2-runtime-packager.kotoba` to an `aarch64-macos` container.
That same Mac compiler extracted its `main` code. The packager source SHA-256
is `22e03a24b9b2bb2d45552799bbe2284030a19d27212ca84c9bdc8fec8831fce0`.

| Artifact or result | Observation |
| --- | --- |
| Mac-compiled packager container | 38,838 bytes; SHA-256 `7716f3f7bbdbbbc2ead5fa75731ab1f92764698ab47334c49dd8b0fe52b0e312` |
| Mac-extracted packager code | 38,809 bytes; SHA-256 `391dcde64fc44033c555632213b6cd8f654f4d83f188d4d0dc3402ebc942ff33` |
| `main` entry within code | offset 34,980; arity 0 |
| One-time Amu-built Linux ARM packager | SHA-256 `3ff8a0382fb850f2b0e0281ac52e02bbcda053420342a9504d72713d54d5a744` |
| One-time unsigned Mac packager bridge | 65,536 bytes; SHA-256 `895a5d571711f31ea9e9ca7f1b45a97aa08a9123081c2db48ce6e2d51f5858eb` |
| Signed Mac packager bridge | SHA-256 `14022d47804c251f5095502b7b29fab747736e1e84258a1fdd08d04c8038d4ca` |
| Mac packager F1 and F2 unsigned | Both byte-identical to the unsigned bridge, SHA-256 `895a5d571711f31ea9e9ca7f1b45a97aa08a9123081c2db48ce6e2d51f5858eb` |
| Full compiler F2 Mach-O emitted by Mac packager | 3,293,184 bytes; SHA-256 `40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4`, byte-identical to the earlier ARM Linux producer's unsigned image |

The first attempted bridge entered the raw code at offset zero and stopped at
a compiler-generated bounds trap. LLDB located the stop at image offset
`0x202c`. The extracted `main` entry is offset 34,980 within that code,
so the final Kotoba source branches there for this exact packager raw length.
Compiling the final source again left its raw length and entry offset
unchanged. The final packager produced itself twice on Mac; both unsigned
images match the one-time bridge byte for byte. Its Mac-produced full
compiler image passed `codesign --verify --strict`, had no dylib load
commands, and passed the passwordless single-file FS2 check/compile,
existing-output refusal, and traversal refusal gate. The compiled ELF
remained SHA-256
`50bf68c6ea23a4b3325e7f29292fb132b90077f1eea15a4306d538190b4e6791`.

`scripts/seed/check_macos_packager_selfhost.py` repeats the Mac-only portion
without screen sharing or a password. It pins the source, signed input
images and raw code; compiles and extracts the packager on Mac; runs two
packager generations; compares their unsigned bytes; packages F2 on Mac;
signs that image and calls `check_macos_fs2_bc.py`. A different signed
compiler image was rejected by its digest check before execution. The gate
needs a one-time signed Mac packager input, a signed Mac F2 compiler, and its
extracted F2 raw code supplied as files. The gate itself launches no Linux
process. Ad hoc code signatures are checked for validity; their signed file
hashes are not the cross-generation equality criterion.

This proves a bounded Mac-native packager execution and self-rebuild fixed
point from a Linux-built bridge. It does not remove the initial Linux ARM
bootstrap or qualify a full Linux-free source-to-executable release path.
Complete FS2/source-lock handling, native corpus, AIUEOS build/boot and
physical qualification remain open.
