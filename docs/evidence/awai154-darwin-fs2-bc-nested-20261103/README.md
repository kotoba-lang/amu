# Darwin FS2 nested binary writes

The diagnostic Mac B/C byte handler accepts nested ASCII paths under the FD 3
grant instead of only a basename. It validates the full path before opening,
refusing empty and dot components, non-ASCII bytes, paths over 1023 bytes and
components over 255 bytes. Darwin `openat` retains scoped no-follow flags. B
creates or truncates; C appends to an existing file. The reply byte vector is
allocated and filled before the write, preserving the existing acknowledgment
contract. These path rules are stricter than Linux normalization.

On one Mac, an Amu-produced [byte probe](byteprobe.kotoba) sent actual FS2
frames. The [receipt](receipt.json) records a binary B write including NUL and
255, C append, a 4096-byte append, M file sync, T no-replace publication and
M parent sync, with host readback of exact bytes. It also records missing,
symlink, escape, malformed and oversized-path refusals. The old diagnostic
handler trapped on the nested-path control. Separate [O/U/E/F](ou-regression.json),
[H/M](hm-regression.json), [I](i-regression.json) and
[L/T](rename-regression.json) fixtures reran against the same candidate. The
assembly is independent derivation evidence; Kotoba literals are the build
input, checked by the existing word-comparison gate.

This is one host and task-owned local files. A successful fsync call does not
establish power-loss durability. Actual Git processes, GitHub storage,
checkpoint capture/restore, concurrent malicious file replacement, all FS2
operations, independent Macs, bot execution and resource governance remain
unqualified. The diagnostic compiler and bootstrap packager are not a release
closure.
