# Mac full-unity compiler probe

The 47 paths in `seed/FULL-MANIFEST` were concatenated in manifest order with
one newline after each file, exactly as `scripts/seed/selfhost-bootstrap.py`
stages `full-unity.kotoba`. The staged source was 3,454,909 bytes, SHA-256
`24039e0f0ed95eaad39b71cbd9d71f1e38bd440dc8d0b505b3adfb9aeb347f82`.

The initial signed Mac diagnostic had a 32M vector-item arena. It wrote the
first 262,144 bytes of the full compiler container, then trapped in vector
allocation at image-relative `0x14fc`: item use was 33,320,937 of 33,554,432,
with a 262,170-item response allocation requested. LLDB read this live stop;
the remaining 233,495 items could not fit the response.

The next Amu/Kotoba-generated diagnostic enlarged the item map to 512 MiB
and the two matching item bounds to 64M. Its signed Mac image SHA-256 was
`ec4bb4efc889c43b2d717d2a1e4b190dd125943d195d85e4a82d9d312150946f`.
The exact Kotoba packager source SHA-256 was
`53b71abe8b1a45aade69ac3fdd5965d1b3a90f0e7e2d109774ff483a28b8d244`;
the Amu-built packager ELF SHA-256 was
`0e2be78abfdff3e245be73b32f39c7a64ccfcf55e775dbb45f7ff185a78cfcec`.
The passwordless single-file gate still passed. On Mac it then ran:

```text
compile full-unity.kotoba --target aarch64-macos --output full-f1-64m.kseed
exit 0, 94.471 seconds
{:ok true, :target :aarch64-macos, :output "full-f1-64m.kseed", :bytes 3250979}
```

The resulting 3,250,979-byte container SHA-256 was
`d6612951d7bb5dfdfe4814a26aae0ad8775dde207f80289de0e39b3ac44046c4`.
It was produced by the full compiler running directly on macOS, while that
compiler image had been packaged by an Amu-built ARM Linux producer. The
container has not yet rebuilt or run its own compiler.

`extract-native full-f1-64m.kseed --symbol main` exposed the next ABI gap.
LLDB observed wire 35, kind 9 -> 9, and the exact FS2 A request
`NUL FS2 NUL Afull-f1-64m.kseed NUL`. The adopted Mac core passes that request
as a pair-backed string and requires a byte-vector handle in its response.
Returning the D/A pair response reached `vector-i64-from-bytes`, which trapped
because it received a pair handle. A correctly typed, bounded vector response
was then added in the Kotoba packager. The Amu-built packager source SHA-256
for the next diagnostic was
`86bfb20c647675a7936a319c90d9ff855b72c8ef9026b9e3dbdef62d58ed98af`;
its ELF SHA-256 was
`a0fcf17286a7215a91678cc93baafcd4bbe8d29a837ca26fdcde86777183a3cb`.
The [kind 9 instruction derivation](../mac-fs2-bc-20261026/fs2-kind9.derivation.s)
is a review record, not a build input.

With the new kind 9 response, the signed Mac producer extracted `main` from
the F1 container in 0.068 seconds, returning 3,250,952 raw code bytes with
SHA-256
`48f724c12ece45c9ba57550932536533a2e340cea27812fb25251678cac97fdd`.
The same unity source compiled independently under the pinned Linux ARM root
produced a byte-identical container (`d6612951...46c4`).

The extracted F1 code was packaged into a separate signed Mac Mach-O
(SHA-256 `757f63a6b29e4c5abf9b39aabadc8b6d1484393759018363a4c3ef6dff020c9b`).
Its passwordless single-file gate passed. F1 then ran on Mac and compiled
the same 47-module unity source to F2 in 96.438 seconds: exit 0, 3,250,979
bytes, SHA-256 `d6612951d7bb5dfdfe4814a26aae0ad8775dde207f80289de0e39b3ac44046c4`.
F1 and F2 containers were byte-identical. Mac `extract-native` on F2 returned
3,250,952 raw bytes, byte-identical to F1 raw.

The F2 raw code was packaged as a separate Mac Mach-O; its unsigned bytes
matched the F1 Mach-O exactly (SHA-256
`40a30d60c8df36d8f72cf1207952a355b1e563e0729fdb02be11b38560b5baa4`).
The separately signed F2 image SHA-256 was
`3dcdaac995fb01a149234e4eb272e78951a33e01904f3adc5c1a33dbff4c6ba2`.
It passed the passwordless single-file gate, then ran on Mac and compiled the
same 47-module unity source to F3 in 94.805 seconds: exit 0, 3,250,979
bytes. F1, F2 and F3 container bytes were identical, SHA-256
`d6612951d7bb5dfdfe4814a26aae0ad8775dde207f80289de0e39b3ac44046c4`.
Mac `extract-native` on each returned identical 3,250,952-byte `main` code,
SHA-256 `48f724c12ece45c9ba57550932536533a2e340cea27812fb25251678cac97fdd`.

This proves Mac execution and F1=F2=F3 container/code parity for the pinned
unity source. The Mac executable images were still packaged by an Amu-built
Linux ARM producer. A Mac-native producer, complete FS2 and native corpus,
AIUEOS build/boot, and release qualification remain open.
