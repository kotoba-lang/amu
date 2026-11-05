# Darwin FS2 H/M diagnostic candidate

The diagnostic Mac FS2 handler adds H and M operations. H parses one to six
octal digits, masks to 0777, and calls `fchmod` on an FD3-scoped, no-follow
opened descriptor. M calls `fsync` on a similarly opened file or directory.
The root directory is handled by duplicating the grant. Response arena space is
checked before mutation, and failed opens report the framed boolean `0`.
Malformed modes trap before mutation. These operations do not make the partial
provider a complete or qualified filesystem implementation.

The [receipt](receipt.json) records an Amu-produced Mac probe sending actual
FS2 frames on macOS 26.3.1 against task-owned fixtures. File, directory and
root sync returned `1`; mode changes were checked against host metadata.
Missing files, symlinks, symlinked parents and escape paths returned `0`;
invalid and overlong octal modes trapped without changing the test file.
The [O/U and E/F regression](ou-regression.json) reran against the same
candidate. Its probe source is [here](../awai154-darwin-fs2-ou-20261103/probe.kotoba).
The assembly derivation is review evidence; the Kotoba instruction vector is
the build input. The separate word-comparison gate checks the derivation.

An `fsync` success is not proof of power-loss durability. Disk failure,
concurrent mutation, alternate identity permission denial, I/L/T and other
FS2 forms, actual Git checkpoint, production bot, independent Macs, governor,
and the release closure remain unqualified. The diagnostic compiler and
packager pins are not a production selfhost qualification.
