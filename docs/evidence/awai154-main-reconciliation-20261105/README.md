# Darwin FS2 integration candidate after main merge

This candidate combines PR #1796 head `5c6c9213` with main `d41d3cbe`.
The manually reconciled packager source has SHA-256
`cc371bb7a0af8a7f0c6ccc65b2eb8e649adea034f81274122034d14685f34d92`.
The original PR's derivation gate still expected the older 184-word D/A
helper. It now checks the 188-word error-distinguishing helper against its
own derivation and relocation slots 27 and 183. The gate passed for D/A,
B/C, lock and E/F/O/U/H/I/L/M/T on one Darwin ARM64 host.

A strictly signature-verified CI-produced diagnostic compiler from an
earlier run, SHA-256
`703709f8bc10efe3b50ac23e5a80e48655049891bf66b13211745ce9aeb9fe50`,
checked and compiled the candidate. An existing diagnostic bootstrap packager
with SHA-256 `f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`
produced an ad-hoc signed candidate packager with SHA-256
`28aa2445711083523adef3cfed0d5b9031b85e2ad258ff760af8680a340d9378`.

On one Mac, the main scoped-read diagnostic passed 16 KFR1 cases, the KSL1
control, a pre-existing FS2 A read and an exact binary read. A separate
isolated FD3 fixture sampled D/A, O and U metadata including mode 04644,
bounded E, I, H, M, L and missing-source lookup. Another test confirmed that
T refused an existing destination and a symlink parent, published to a new
name, and L replaced an existing destination. A final diagnostic packaged
one existing FS35 roundtrip entry in the explicit `amu-program-fs35` and
default `amu-program` profiles: the explicit profile returned 0, whereas the
default trapped without writing. The test directories were task-owned; the
short processes were limited to three CPU seconds, without a hard memory cap.

These are bounded local diagnostics using a prior compiler and bootstrap, not
the native self-rebuild or the merged compiler's qualification. They do not
cover Metal execution, all FS2 error paths, power-loss durability, all
concurrency and identity races, a GitHub roundtrip or a resource governor.
Generated pins must be regenerated and verified with the repository-native
route after the resource governor is qualified. The PR remains draft.
