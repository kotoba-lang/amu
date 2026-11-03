# Darwin FS2 L/T rename diagnostic candidate

The diagnostic Mac handler adds FS2 L (rename with replacement) and T
(no-replace publication). Each source and destination path is validated and
its parent separately opened beneath FD 3 without following symlinks. It uses
`renameatx_np` with `RENAME_NOFOLLOW_ANY`; T additionally requests `RENAME_EXCL`
and never falls back to replacing rename. Response arena space is checked
before mutation, and acquired parent descriptors are closed. Paths retain the
I candidate's 1023-byte limit and refusal of empty or dot components; this is
stricter than Linux path normalization.

The [receipt](receipt.json) records Mac-native FS2 requests on one machine:
existing-destination refusal for T, replacement for L, T publication, final
symlink movement, invalid or escaping paths, symlinked parents and missing
sources. Two independent T processes targeting one name produced exactly one
winner and preserved the losing content. These are bounded local fixtures, not
proof of independent failure domains. The [I](i-regression.json),
[H/M](hm-regression.json), and [O/U/E/F](ou-regression.json) probes were rerun
against the same artifact. Their shared probe source is
[here](../awai154-darwin-fs2-ou-20261103/probe.kotoba). The assembly is
independent derivation evidence; the Kotoba instruction vector is the build
input and is checked by the existing word comparison gate.

A successful rename does not itself guarantee crash durability; the caller
must separately synchronize the affected directory. This diagnostic does not
qualify concurrent malicious parent movement, filesystem failures,
cross-filesystem behavior, alternate identity permissions, the complete FS2
provider, actual Git checkpoint, GitHub, bots, other Macs or resource
governance. The compiler and bootstrap packager are diagnostic artifacts,
not a qualified release closure.
