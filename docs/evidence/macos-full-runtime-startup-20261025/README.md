# First bounded Mac execution of the full Amu compiler main

The previously packaged 3,254,848-byte Amu compiler `main` was signed and
launched on Apple Silicon macOS 26.4. With only the writable context it called
a null ABI-v11 `pair_new` pointer and exited SIGSEGV. This branch adds a
diagnostic runtime to the same full main image:

- mapped `pair_new` with the 256 MiB pair and 16 MiB mark arenas;
- wire 38 (`:cli/args`) answering the empty string for a no-argument probe;
- slot 112 `string_equal` for validated code-span strings, with byte-exact
  equality and bounded pair handles. String-pool offsets still trap;
- wire 37 output remains disabled in this probe. Other slots are zero.

The Kotoba fixture `seed/macos-equal-main.kotoba` checks empty, equal,
different-byte and different-length comparisons. The pinned Amu native root
compiled it to `aarch64-macos` and extracted its 516-byte `main`. The same
Kotoba-produced Mach-O packager emitted the fixture and full compiler images.
Signed fixture execution returned 42 with no output. Removing the code-length
store made it trap with no output. The full compiler image launched and
progressed to its next missing function pointer: ABI slot 120,
`string_concat`. The Mac crash report's PC was zero; its return address mapped
to the generated `ldr x16, [x0, #120]; blr x16` callsite at raw offset
`0x22fd80`. The full image's expected SIGSEGV is a measured incomplete
runtime boundary, not compiler success.

The [observer](../../../scripts/seed/check-macos-full-runtime-probe.py)
checks exact source and artifact SHA-256 pins, Mach-O layout, the three
runtime helpers, generated main bytes, build admissions and a byte-identical
repeat image. It signs fresh copies, runs the positive fixture, negative
code-span control and full compiler, then reads only the relevant fields of
that process's macOS crash report to identify the next missing slot. Exact
results and digest pins are in [receipt.json](receipt.json).

The compiler root and packager still ran in a network-disabled ARM Linux
container. Apple `as` was used to derive fixed AArch64 words before they were
put into Kotoba source, but it is not in the image build path. The CLI handler
is an empty-input diagnostic fixture, not an argument broker or trusted
approval. There is no string pool, `string_concat`, full compiler run,
Mac F1=F2=F3, AIUEOS Mac build, or Linux-free build closure yet. JUN-417
remains open; the next runtime requirement is a bounded string pool and
ABI-compatible concat.
