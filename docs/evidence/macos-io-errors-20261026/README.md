# Darwin diagnostic I/O error repair

The previous pinned native probe reproduced a read error: with stdin closed
it returned42 and wrote9 bytes, treating EBADF as a successful byte count.
The native Kotoba emitter now tests Darwin carry before CMP changes flags,
and rejects read/write errors or a short write with exit44.

The revised image has no declared dylib and carries explicit empty symbol
and relocation commands, matching the macOS15 loader metadata contract.
Native Amu on this Mac compiled the emitter and the pinned native Kotoba
packager produced it; no Linux process, assembler, JVM, Node or C compiler
participated in the revised build. Header, all28 instructions and the digest
were independently inspected before pinning.

The executed signed image passed stdin echo, EOF43,16-byte bound, closed
stdin44, closed stdout44 and missing-header-flags refusal. Repeated native
emission was byte identical and an empty output path refused. The macos-15
workflow now runs the same source-bound build/execution gate. This is bounded
loader/I/O evidence; full Darwin runtime and release remain unqualified.

Earlier probe fixtures and receipts from the stacked research branches remain
historical, tied to their recorded sources and artifact digests. They are
not substituted for the current full compiler bootstrap or native gate.

All42 `seed/macos-*.kotoba` source fixtures passed native Mac `check`.
That is source admission only, not execution qualification of every prototype.
