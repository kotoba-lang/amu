# Darwin diagnostic range reads for large OCI blobs

The diagnostic FS2 E provider accepted only 32-bit starting offsets. The
observed Bonsai `model.safetensors` is 8,595,477,990 bytes, so that bound
cannot address its second half. The Kotoba packager now emits a 34-bit maximum
starting offset, `17179869183` (16 GiB minus one); a single E request remains
limited to 262,144 bytes. This is a bounded diagnostic capability, not a
general 64-bit file interface. A single read may cross the maximum starting
offset; later reads cannot start beyond it.

On a local ARM64 Mac, a source-built candidate packaged `fixture.kotoba`. A
task-owned sparse file had logical length 17,179,869,185 bytes but occupied
24,576 bytes on disk; six single-byte markers were written and the file was
removed after testing. Reads starting at 0, 2^32-1, 2^32, 8,595,477,989,
and 2^34-1 returned the expected distinct marker bytes. Starting at 2^34
trapped; the previous provider accepted 2^32-1 but trapped at 2^32.

A further disposable sparse file with the observed model length
8,595,477,990 bytes occupied 12,288 disk bytes. FS2 F returned that exact
64-bit length. An E read of four bytes starting at 2^32-2 returned all four
distinct markers across the old boundary, and a two-byte read at the file end
returned the expected markers. The file was removed after the test. These
checks use the same signed regression fixture listed below.

A separate real-file regression checked D, A, O, U, E, I, H, M and L; a
small-file E read succeeded, while out-of-file ranges, a count above 262,144,
an oversized decimal offset and a malformed count trapped. The final LLDB
disassembly of the signed test image showed the intended pre-multiplication
bound `0x66666666` and post-multiplication bound `0x3ffffffff` at the changed
instruction words. The emitted Kotoba words are the build input; no assembler
or C compiler was used to build the candidate.

This does not hash a real model, qualify all FS2 operations or the public Mac
runtime, prove stable file identity across range reads, verify OCI descriptors,
perform a transfer, provide crash recovery, or authorize deployment. FS2 E
opens a path on each request, so concurrent replacement or mutation remains a
host-level integrity problem. The user file, existing model and services were
not touched. Test fixtures and signed artifacts are local diagnostics only.

| Artifact | SHA-256 |
| --- | --- |
| candidate source | `c950ca445f96beac3f9e4a574f4625fce9730b85284b88959c60acbe2b4fd0e0` |
| signed candidate packager | `df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5` |
| signed range fixture | `ca663c454e0c400794a791ca98f4c73bd29c20e96461fa678f80ab2148feaffa` |
| signed prior-provider control | `62d1a7b92127a51448ef15968676323c5e9bc20699c3136738b191626b5b9498` |
| signed regression fixture | `4bf0268cb855cd11ade05ef7ccf2b6ebcdac0b12d934568dcb52fbac970939de` |
| Mac bootstrap compiler | `920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6` |
