# Darwin loopback TCP syscall control

On one local Darwin 25.3.0 ARM64 host, a diagnostic Mach-O constructed by
`seed/macos-tcp-control-packager.kotoba` used direct Darwin socket, connect,
read, write and close syscalls against a test-only loopback server. The server
received `PING`; a `PONG` reply returned exit 0. A wrong reply, a short reply
and an unbound port returned exit 1. Connecting to a bound but non-listening
port did not finish within one second in this observation; the supervising
test killed and reaped that process. This outcome is host-specific and is not
a portable TCP timeout guarantee.

The control hardcodes 127.0.0.1, accepts a two-byte port on stdin, and has no
network grant checks, intrinsic deadlines, general I/O framing, retry,
listener, handle management or service identity. It is **not** a TCP
capability provider and must not be used to serve a bot or lease. The Python
observer only supplies a local test peer and supervises its own children.
No remote host or existing service was contacted. `derivation.s` and its
assembler object are independent instruction-encoding checks; neither is an
operational dependency of the Kotoba packager.

The first experimental image without `LC_DYLD_INFO_ONLY` segfaulted before its
entry point on this host, including an early-exit control. The successful image
uses the empty load command already used by the fstatat diagnostic. This does
not establish general Mach-O portability.

Source SHA-256:
`6e26b9bb2ecb6eb4d12b6c47002bcdbd22f09f0b9f34f148ee641e9c62e9960e`.
The native bootstrap compiler and diagnostic FS2 packager were respectively
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6` and
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`.
The signed control packager hash was
`649c16104cf01257e98d81f1f6babdfbc1f6c69594a2b9987dca33392d9ccd36`;
the emitted signed control was
`bf658dfc5788c7272e857f106b4057a3d303d9a1f164f6e02e06f8fdfba28ec1`.
The independent assembler object hash was
`33a36c123e1cf58871287fc8284c55becf66fd42b73043c5478475d3a4d58530`.
The observer uses task-specific temporary paths and must be adapted to rerun.
