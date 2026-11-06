# Native Darwin TCP SO_NOSIGPIPE control

On one arm64 Mac, macOS 26.3.1 / Darwin 25.3.0, an Amu-compiled Kotoba
packager emitted a loaderless Mach-O test image. Its direct Darwin syscalls
created a loopback TCP socket, set `SO_NOSIGPIPE`, connected to a test peer
which reset the connection, then attempted a one-byte write. Three protected
runs observed carry-set `EPIPE` (errno 32), closed the socket and exited 0.
Three negative controls skipped only the setsockopt syscall and terminated by
SIGPIPE (signal 13). The test observer set the inherited SIGPIPE disposition
to default. No real service, bot, credential or external host was involved.

`control.s` was used to derive the 74 instruction words embedded in the
Kotoba packager; the assembler object was an encoding aid, not the artifact
used to execute the test, and is not an independent verification of those
words. The negative control replaces the setsockopt syscall instruction with
NOP. The test-only Python observer supplies a loopback reset peer and bounds
its own children. Setup-failure handling, short reads/writes, peer identity,
TLS, timeouts, FD inheritance, other macOS versions and the actual capability
provider remain unqualified. In particular, this diagnostic is not an
implementation of wires 43–47 and must not be used as a service.

Packager source SHA-256 `f1354e55509520f6768fda366f31dd77f593d88c87dc1f2578cee2baf8096d61`;
assembly source `aa12841a4316075d5761aa089b39b70a089a1002ce91d17a8560f004e216fa3e`;
observer `96b1160b5d751765a713a92a523d9eb3f0d9bef449658fdc5a90815d5d5ba566`;
signed packager `590c877627191ea859d629f182ee293c347084d9535f8f513b59ae4f2ad26759`;
protected image `ade5d3bf8a997de7409017cf44313c80111181ea457974e469de8d24589736ed`;
negative-control image `3665373362af235155fe62d4dde896d73d9a3b206af458fcd4c611a4085f27e2`.
The bootstrap compiler and diagnostic host match the earlier
[TCP control](../awai153-mac-tcp-control-20261103/).
