# Darwin FS2 mkdir diagnostic candidate

The Darwin diagnostic handler adds FS2 I. It checks the reply arena before
mutation, bounds the relative path to 1023 bytes and each component to 255,
and refuses empty, `.` and `..` components. For a nested path it opens the
parent beneath the granted FD 3 with no-follow scope, then calls `mkdirat`
with mode 0777 subject to the process umask. An existing entry is not replaced.
The parent descriptor is closed before returning a framed boolean; parent
synchronization is a separate operation. This stricter path acceptance is a
diagnostic candidate and is not claimed to be identical to Linux normalization.

A Mac-native probe sent actual FS2 frames on macOS 26.3.1. The
[receipt](receipt.json) records root-relative, single-component, nested and
leading-slash creation, existing directory/file/symlink, missing and symlinked
parent, traversal, malformed and oversized paths, and extra-tail refusal. The
[H/M](hm-regression.json) and [O/U/E/F](ou-regression.json) probes were rerun
against the same candidate. The probe source is
[here](../awai154-darwin-fs2-ou-20261103/probe.kotoba). The checked-in
assembly is independent word-derivation evidence; the product input is the
Kotoba vector, checked with the existing derivation comparison gate.

This tests one Mac with task-owned fixtures. It does not qualify the complete
FS2 provider, concurrent namespace mutation, permission denial by another
identity, L/T rename, actual Git checkpoint, GitHub, bots, other Macs or the
resource governor. Existing diagnostic compiler and packager artifacts are
not a release closure.
