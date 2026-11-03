# Diagnostic launchd command mode with a scoped working directory

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
