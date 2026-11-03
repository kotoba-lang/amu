# Diagnostic launchd command mode with a scoped working directory

The later `amu-cli-host-cwd` source candidate composes the same cwd scope
startup with the private CLI host service, leaving `amu-cli-host` unchanged.
It reserves a separate code region for the scope startup and refuses an
occupied FD 3. The host/FS2 and occupied-FD regression cases are defined in
`scripts/seed/check-macos-cli-host-native.py` but have not been built or run
for this candidate. The observations below cover only the earlier
`fs2-cli-stdio-cwd` image; they do not qualify the combined host image,
directory identity binding, model loader, runtime or deployment.

The new explicit `fs2-cli-stdio-cwd` diagnostic packager mode opens the
already selected working directory as FD 3 before installing the existing
scoped FS2 callback. It refuses if FD 3 is occupied, if standard descriptors
are not all open, or if opening the directory fails. It does not change the
public `amu-program` contract or the existing explicit-FD3 mode. The code
is emitted by the Kotoba packager; no shell wrapper is part of the image.

On one local Apple Silicon Mac, the native bootstrap compiled the candidate
packager and the attached synthetic probe. The candidate packager emitted
signed `cwd` and existing-mode control images. Direct execution in a private
test directory read a file and distinguished an absent path. Relative traversal
and an absolute symlink pointing outside the directory trapped without exposing
the target. A pre-opened FD 3 and closed stdout each refused with OS exit 70;
the pre-opened file remained unchanged. Existing explicit-FD3 mode continued to
read the scoped file. A regression covered D, A, O, U, E, I, H, M and L.

Four uniquely named, short-lived user launchd test jobs used the emitted
images. Two `cwd` jobs had different `WorkingDirectory` values and read their
respective file contents. A traversal attempt and the existing-mode control
without inherited FD3 did not disclose the outside file. Both successful jobs
reported exit 0. All four exact jobs were booted out and verified absent.
The signal termination cases did not yield a numeric `last exit code` in the
observer, so the direct execution results above are the refusal evidence.

This is not a production path-security policy: launchd or another trusted
host must select, own and protect an alias-free directory and validate its
identity before execution. `open(".")` does not validate the path used by
launchd to enter it or prevent a concurrent rename. This diagnostic is not a
complete FS2 provider, authenticated bot host, process-tree supervisor,
resource governor, GitHub credential path, selfhost release or Mac mini fleet
qualification. The test observer is one-off and is not operational tooling.

## Follow-up: owner and permission checks

The later candidate fstats the opened directory before guest execution and
requires its owner to equal the effective UID and its full file type/mode to
be exactly directory 0700. On the same local Mac, an owner-matching 0700
directory succeeded. Modes 0755, 0710, 0770, 0777, 1700 and 4700 refused
with OS exit 70 before guest output. A request to set 2700 was cleared by the
filesystem to 0700, so it is not a setgid test. The previous candidate read
the same 0755 directory; the new candidate refused it. A test-only packager
mutant substituted UID 0 for `geteuid`; it refused the caller-owned non-root
directory, while the real candidate succeeded. A true foreign-owned directory
was not tested.

Two unique user launchd jobs also confirmed 0700 success and 0755 refusal;
both were booted out and confirmed absent. These checks do not inspect ACLs,
pin device/inode, validate the path used by launchd, prevent later chmod or
rename by the same principal, enforce process isolation, or qualify the
production runner. macOS ACLs require separate handling.

| Follow-up artifact | SHA-256 |
| --- | --- |
| Candidate source | `eebbbd6870d4a90b718aaa0d261770455e6aef6448b7b37b4c1c5c2de7b88961` |
| Signed candidate packager | `c097a95cfa345283a15e9bdce097d2e939f7e2116957db134f4db34a08e6459c` |
| Signed candidate probe | `93fd76f2405d7c2ed0c07463caca08afc9017d0ec82c904c2bd8787f3e6bdda8` |
| UID-substitution mutant source | `e919ab7c56436304e10ae0dc6fb8d84562faf5fdfc2f9c6046a481cad5f4d1b4` |
| Signed mutant packager | `c669f67f79f3d44135ca62f55c64466a7771ba34e409b9e5af2267f050074582` |
| Signed mutant probe | `35fdea2f74de59ffff0d9994eaf6779efde0ee3620d8c665146ece2a23fb5c9e` |

## Follow-up: ACL and filesystem capability

The later candidate first requests volume capabilities and valid/native
attributes on the opened FD. It requires the extended-security capability
and extended-security attribute to be reported as supported, then requests
the directory's extended security attributes. It accepts only the observed
32-byte no-ACL form with the expected returned-attribute mask and empty
reference. Any ACL, unsupported capability, unexpected response shape or
syscall failure refuses. This deliberately narrows the diagnostic to
filesystems that make those claims and return that shape.

On the local APFS test directory, a 0700 no-ACL directory succeeded. A
synthetic `everyone allow list,search` ACL on the same directory caused exit
70 and no guest output, while the previous mode-and-owner candidate accepted
it. Removing the ACL restored success. A test-only mutant requesting an
unsupported capability bit refused the otherwise valid directory. Short-lived
user launchd jobs observed the same 0/70 outcomes and were removed. FS2 D,
A, O, U, E, I, H, M and L regression cases passed without an ACL. A preliminary
packager build refused because its candidate-code size guard had not yet been
increased; the guard was corrected and all results above use the rebuilt source.

An independent one-off macOS `fgetattrlist` observer saw a 32-byte no-ACL
response and a 100-byte ACL-present response, including when the output buffer
was 32 bytes. It also observed the local APFS support/validity bits used by
the candidate. This is not proof for other filesystems, kernel versions, ACL
mutations after the check, device/inode or parent-path pinning, or process
isolation. No real bot, secret, GitHub storage or remote Mac mini was involved.

| ACL follow-up artifact | SHA-256 |
| --- | --- |
| Candidate source | `9d889f1bb638081c47fc4da1473b383dec50626fa7d37ba5ce5b1ceaf7318732` |
| Signed candidate packager | `f9368abfe55929bbde0c64c0ec28b54f5dcc6aa12e4076913797a90a2dd38676` |
| Signed candidate probe | `3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd` |
| Unsupported-capability mutant source | `cc2be4e660842dfc0cf661efb5a26fd5ef0064a25042039d57ec5a736457ca7a` |
| Signed mutant packager | `b0311f12145df2fb8b85397b8cbb62625ff40db7f32a169be7732c1396220b29` |
| Signed mutant probe | `850b836655a7a2e63ee7228cfb530432bbfd4dba5f2109a05c0fa030d354275b` |

| Artifact | SHA-256 |
| --- | --- |
| Candidate packager source | `a5a90267fb8384d09c32f81a4252d6004643d40c15be75c4634f61ae8fdb45b9` |
| Candidate signed packager | `e8f7d2696e3c299436fea69f0eac735b10ddf8432ca8d1577f0425a49d235a8d` |
| Probe source | `5be0d2cb608d8a744b240be11d6114b7049aa4272e84a06cf656437f8c5a5edf` |
| Extracted probe code | `0ae9c76c375949e6f8a2fd9db66f650f8328a579640135b99190e64ae92ca49a` |
| CWD mode signed image | `a50a8e27c7f35676a167eac02e59546b795d3b080614c736efc90a3965986167` |
| Existing mode signed control | `9a72483a161aa3b75682ada6d89c3f100b44fbc1ff8596a80c45788851ff5087` |

Bootstrap SHA-256 was
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`;
the preceding diagnostic packager used to emit this packager was
`4114499dc10bd321070a221f88847b8708565f7d80e87c4ed84b28e599e3c41e`.
