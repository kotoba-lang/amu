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
is the next diagnostic gate. Full Mac F1=F2=F3, Linux-free production,
AIUEOS build/boot, and release qualification remain open.
