# Fixed-function macOS observation candidate

The existing public Amu CLI does not grant its generated guests filesystem or
process authority. This candidate instead emits a separate, fixed-function
Darwin ARM64 host executable. It accepts no arguments and performs only
`sysctl`, `memorystatus_get_level`, root `statfs64`, stdout `write`, and
`exit`; it does not spawn a command or give a guest a host grant. The program
emits one 56-byte little-endian record as 112 lowercase hexadecimal characters
and a newline. The fields are magic `AOS1`, version 1, physical memory,
swap total/available/used, the kernel memorystatus level, filesystem block
size and non-superuser available blocks. Syscall failure, unexpected sysctl
length, impossible basic values, an extra argument or a short write is refusal.
Consumers must reject partial output and nonzero status.

The syscall numbers are taken from Apple's [XNU syscall declarations](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/syscalls.master).
The structures and numeric MIBs were checked against the local macOS SDK.
The meaning of `memorystatus_level` follows the kernel's
[memorystatus implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_memorystatus.c);
it is not a reservation or a direct measurement of allocatable unified memory.

On one local ARM64 Mac, the native packager produced a signed host image. It
returned a correctly framed record; physical memory matched `sysctl`, the
pressure level matched a near-simultaneous `memory_pressure -Q`, and available
disk matched `df -Pk /` in that sample. An extra argument was refused without
stdout. A separate test-only packager with an invalid hardware MIB produced an
image that exited nonzero with no stdout. The checked-in test-only Python gate
stages, signs and launches the already-built native artifact and verifies the
record and argument refusal; it is not an operational or compiler fallback.

This candidate does not authenticate the machine or output, establish fresh
reservations, control process lifetimes, deploy to a mini, or qualify the
public CLI. It has no receiver integration or OCI delivery yet. The emitted
fixed instructions, platform signing, syscall ABI and production source seal
still require independent review and qualification before use as a host tool.

| Artifact | SHA-256 |
| --- | --- |
| packager source | `d94be93dd451f156016272067565bf184289a35a381dbb53729b657f4e0869ba` |
| signed native packager fixture | `eb9c1b325c0b5becf96c06f96da9d7d725189275b9100ed909b6343b22caca81` |
| signed fixed observer | `ec79cbe947271a633394fb02ce56567328b57d0402738a40306aeaa27039e5b3` |
| signed invalid-MIB control | `404b6ead696aab2aaffdc111807bc855b61c24b9ac63704c81dbf8f9a7ad895e` |
| bootstrap compiler | `920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6` |
