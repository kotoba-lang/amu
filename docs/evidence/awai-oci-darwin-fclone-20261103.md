# Darwin clone-and-hold diagnostic

The Linux fune candidate uses a sealed memfd snapshot across digest and
consumption. Darwin FS2 E reopens a pathname on each range read and does not
provide that guarantee. As a possible Darwin building block, the test-only
`seed/macos-fclonefile-control-packager.kotoba` emits a loaderless ARM64 test
program. It invokes `fclonefileat` on an already-open source FD 3 and a
pre-opened destination directory FD 4, with `CLONE_NOFOLLOW_ANY` and
`CLONE_RESOLVE_BENEATH`, and returns only success or failure. It is not an
FS2 provider, model installer or production security boundary.

On local macOS 26.3.1, with a task-owned directory on the APFS data volume, a
test observer created a sparse source of logical size 8,595,477,990 bytes and
wrote synthetic markers. The Amu-generated native program cloned it. The
observer opened the clone read-only, unlinked its name, then changed the
original source's markers. Reads from the still-open clone FD retained both
old markers and a write through that FD was refused. The source occupied less
than 10 MiB of allocated blocks; no real model was read or copied. Test files
and the directory were removed afterward.

The program refused an existing destination without changing its contents,
a destination under a symlinked parent, and `../escape`. LLDB decoded the
emitted program and confirmed syscall 517 and flag value `0x18`. The test
observer—not the test program—opened the FDs, validated fixture types,
removed the clone's name and supplied the private directory. A separate
earlier libc diagnostic observed the same clone-and-hold behavior; neither
uses C source or a C compiler to build the native test program.

This is one host and one filesystem, with no concurrent writes during the
clone syscall. It does not establish an authenticated source, race-free
directory ownership, ACL handling, malicious same-user isolation, disk-space
reservation, crash cleanup, memory use for a real nonsparse model, a SHA-256
digest, or fune V/W/X compatibility. In particular, opening a path to hash it
and later reopening it for consumption is not made safe by this test. A real
provider must enforce these boundaries and fail closed when clone is unavailable.

| Artifact | SHA-256 |
| --- | --- |
| test-only packager source | `41ba40d3d2b9257b3317f2ad2600f52cfeb39047d36b13f1e71102494a7caaa1` |
| signed test packager | `1623f2a4ae91495238c30ff56a0bfd3533d4766445266bbc7dfa9ab1aaaf98ce` |
| signed native clone control | `57b2184d68e4ce5cff0eeb07eb4f886fce6cd0fa7dc8106dccc098ce5df294c2` |
| Mac bootstrap compiler | `920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6` |
