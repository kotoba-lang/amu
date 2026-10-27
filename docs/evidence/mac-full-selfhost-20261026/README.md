# Full compiler Mac-only continuation from a pinned Mac seed

This gate starts with two signed Mac images: a full compiler F2 previously
packaged by the Mac-native packager, and the Mac-native packager after its
self-rebuild. Their SHA-256 identities are respectively
`522b3a105a109deec9ce5908407a414fc434b364453b4d89fc1572d1de51cd43`
and
`ce940d5cfce2bb582a18487ba7ecce03a881961fb82bfc4e2d99b0f5ecf67698`.
The [packager bridge record](../mac-packager-selfhost-20261026/README.md)
explains how the first Mac image was bootstrapped. This run launched no Linux
process.

`scripts/seed/check_macos_full_selfhost.py` staged all 47
`seed/FULL-MANIFEST` modules in the same order and byte format as
`selfhost-bootstrap.py`: 3,454,909 source bytes, SHA-256
`24039e0f0ed95eaad39b71cbd9d71f1e38bd440dc8d0b505b3adfb9aeb347f82`.
It held one shared native build slot and passed a private directory grant on
FD3 to each Mac-native process. It compiled that source with the Mac F2
image, extracted the F4 code, packaged it with the Mac packager and signed
the Mach-O. F4 then performed the same work to create F5.

| Observation | F4 | F5 |
| --- | --- | --- |
| Mac compile/pack exit | 0 | 0 |
| `aarch64-macos` container | 3,250,979 bytes; SHA-256 `d6612951d7bb5dfdfe4814a26aae0ad8775dde207f80289de0e39b3ac44046c4` | Same bytes |
| Extracted `main` code | 3,250,952 bytes; SHA-256 `48f724c12ece45c9ba57550932536533a2e340cea27812fb25251678cac97fdd` | Same bytes |
| Unsigned Mac Mach-O | 3,293,184 bytes; SHA-256 `40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4` | Byte-identical |
| Elapsed compile/extract/pack/sign | 93.742 s | 94.430 s |

The F5 signed image passed strict ad hoc signature verification, had no
dylib load command, and passed the passwordless FS2 check/compile gate.
The fixture's static ARM ELF remained 307,712 bytes, SHA-256
`50bf68c6ea23a4b3325e7f29292fb132b90077f1eea15a4306d538190b4e6791`.
Existing-output and `../` output refusals also passed. A different signed
compiler input was rejected by its digest check before an output directory
was created. See [receipt.json](receipt.json) and
[queue-receipt.json](queue-receipt.json).

This establishes a Mac-only continuation for the pinned full Amu compiler
source and bounded diagnostic runtime, including native source-to-executable
rebuild after the Mac seed. It does not establish a Linux-free initial
bootstrap. It also does not qualify complete FS2/source-lock semantics, the
native compiler corpus, AIUEOS image build/boot, release, or physical device
operation.
