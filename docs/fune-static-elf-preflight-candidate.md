# Static ARM64 ELF preflight candidate (JUN-777)

The worker's single-use `A` diagnostic inspects the executable named in an
already committed FPS1 spec. It reopens the path beneath the frozen root with
`openat2` confinement, compares the reopened inode to the retained executable
descriptor, and reads from that descriptor. It reports `K` for this bounded
subset: a 64-bit little-endian AArch64 ET_EXEC ELF, 64-byte ELF header, at
most 128 56-byte program headers, at least one load segment, and an entry
point backed by an executable segment's file bytes. Inputs must be between 64
bytes and 1 MiB. Dynamic/interpreter program headers, writable-and-executable
load segments, invalid load extents or alignment, malformed headers, read
failures and inode mismatches refuse. This subset excludes dynamic binaries,
scripts, static PIE and ELF files beyond the bound.

The diagnostic uses the worker's single post-commit read slot, so `A` and a
subsequent `O` execution cannot currently be combined in one worker session.
The diagnostic does not execute the file or authenticate its source. It is an
additional bounded preflight, not a complete ELF verifier: the kernel still
validates an executable at `execveat`, and a successful `A` is not permission
to launch. It does not qualify untrusted images, memory isolation, ELF segment
overlap rules, UID/GID semantics, interpreter handling, or a general workload
runtime. Production execution remains restricted to the existing pinned
fixtures.

The ARM64 observer `scripts/seed/check-fune-static-elf.py` stages a native
test ELF and observes direct and nested paths, malformed headers, missing
interpreter restrictions, invalid segment bounds and alignment, entry outside
file-backed code, and denied `pread`. A separately debug-built mutant that
omits the interpreter check accepts the corresponding invalid input, proving
that case distinguishes the control. These observers do not authenticate the
supplied worker or control images. They do not run the staged executable.
