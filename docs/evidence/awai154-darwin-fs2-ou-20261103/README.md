# Darwin FS2 O/U diagnostic candidate

`seed/macos-fs2-runtime-packager.kotoba` now routes pair-backed, framed FS2
O and U metadata requests to scoped `fstatat64`. O masks permission bits to
0777 and U includes 07777; regular files, directories and final symlinks
report kinds 0, 1 and 2. The third field is the filesystem block count, as in
the Linux candidate. The existing F diagnostic retains its historical time
field. One-character paths, previously rejected by the F/E frame length check,
are accepted; `/` refers to the inherited root directory for O/U. The
assembly file is an independent derivation; the Kotoba literals are the
packager build input.

The [receipt](receipt.json) records a Mac-native compiler producing a candidate
packager, an existing diagnostic packager wrapping it, and the candidate
wrapping a Kotoba probe. The signed probe actually sends FS2 requests on
macOS 26.3.1 with an inherited FD 3. It checks O/U against ordinary and
setuid/setgid/sticky modes, block counts, directory, root and symlink kinds,
missing and parent-symlink cases, and escape refusal. It also checks F on a
one-character file, E range data and malformed U tails. The earlier diagnostic
packager traps on that one-character F request. A separate word comparison
checks the Kotoba literals against the derivation, except its two relocation
slots. The compiler and bootstrap packager are diagnostic pins, not a
qualified release closure.

This is a partial provider on one Mac. Complete FS2 operations and frame-kind
coverage, denied access under another identity, concurrent path mutation,
actual Git checkpoint, independent Macs, bot, resource governor and release
remain unqualified. Callers still need an exclusively owned tree or an
appropriate race-safe design; metadata alone does not freeze later file use.
