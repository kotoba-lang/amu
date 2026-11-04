# Mac FS2 merge candidate observation

On 2026-11-04 a temporary candidate of `seed/macos-fs2-runtime-packager.kotoba`
was composed from the merge tree of branch commit `55f6a7ae` and fetched main
`15aef330f3374b941c4d610979b905ff91af0cd0`. The merge tree contained 16
conflicted paths; only the packager source was manually composed for this
experiment. The candidate source SHA-256 was
`d39954bb3ac3ae5b9c51fba3d756d5afdf9b82877c2ef604172f163ffbe898c5`.
It carries the larger FS2 callback and cwd profile from the draft, the scoped
read callback and program FS35 profile from main, and main's Metal profile and
allocation size. It passed the previously staged compiler's source `check`.

The pinned diagnostic compiler SHA-256
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`
compiled the candidate, and diagnostic bootstrap packager SHA-256
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`
packaged it as a locally signed Mac arm64 Mach-O. Strict signature verification
passed; the signed candidate packager SHA-256 was
`d25ed4dd9f3b4594769cdd94dde0c9d4ab1bc57ed948f46de3328f7827cefb3f`.
These tools are staged diagnostics, not a selfhost compiler closure.

The candidate packager built the fetched-main FS35 test source on the local
Mac. In isolated FD3 scopes, the `fs2-cli-stdio-general` and
`amu-program-fs35` images passed roundtrip, durable, lock and path cases. The
ordinary `amu-program` image trapped on the ungranted roundtrip (`SIGTRAP`),
as expected. The fetched-main `check-scoped-read-macos.py` also passed its
16 scoped-path cases and the source-lock, FS2 and binary-read regressions with
this candidate packager. The script's receipt is a local test artifact; the
Metal profile was not executed.

An earlier Linear update incorrectly named the old `origin/main` candidate as
based on fetched main. That ref remained at `13fa358b`; the error was corrected
in Linear. This document refers to the explicit fetched commit above.

These observations do not resolve the 16-path conflict or establish full
native host behavior, power-loss durability, all runtime modes, the Metal
profile, source-lock reproducibility, generated artifact and pin correctness,
selfhost rebuild, resource governance, or actual Itonami inference and GitHub
storage. The candidate source and all generated images stayed in temporary
space; no production compiler, model or service was installed.

## Existing FS2 operation regression

Using the same signed candidate packager and compiler, a source-derived native
fixture from `awai154-darwin-fs2-existence-20261103/general.kotoba` was built
and run against a fresh private FD3 scope. `D` returned `1` for the regular
file, `0` for a missing file and `?` for a symlink. `A` returned the expected
payload. For a mode-04644 file, `O` returned mode 0644 while `U` returned
04644. The `E` range returned `ayl`; `I`, `H`, `M` and `L` reported success,
and the renamed file was present while the prior name was absent. The signed
fixture image SHA-256 was
`ec12006f4fa0545101ee0c6596b6cc7bf4516d82f4d79e33e88ae2d9af775aac`.
The local diagnostic observer was
`/private/tmp/awai1796-merge-fs2-regression.py` (SHA-256
`06efe017615732a554fc8d52ac03099c3956d47a4e028f5eae7d77bdf705e845`).

This does not cover failure injection for these operations, durable power loss,
concurrent adversarial replacement, process lifetime, a real GitHub archive,
the Metal profile or the full merge/rebuild. All files were task-owned test
fixtures; no production runtime or service was changed.

The review artifact `packager-against-main.patch` records the tested source
candidate against the packager at main commit `15aef330f3374b941c4d610979b905ff91af0cd0`.
Its SHA-256 is `57e2c8b80f8e4be96498b516b39a9442a8610a160e949b1e70941155326d7240`.
Applying it to a separate copy of that exact base reproduced candidate SHA-256
`d39954bb3ac3ae5b9c51fba3d756d5afdf9b82877c2ef604172f163ffbe898c5`.
The patch is an evidence/review artifact and does not update the actual
packager, resolve other conflicts, or establish suitability for current main.

## Metal profile bootstrap (no GPU dispatch)

The diagnostic packager also built `metal-profile-probe.kotoba` using the
`amu-program-metal` profile and the default `amu-program` profile, with the
same synthetic source bundle. On the local Mac the signed Metal-profile image
returned `0`: wire 42 returned a callable bootstrap, its scratch address and
dyld-bound resolver address were nonzero, and one scratch word could be
written and read. The same program in the default profile trapped with
`SIGTRAP` at its ungranted wire. Strict code signature verification passed for
both images. Their respective SHA-256 values were
`4bf979efd6d6e6067423de63898d072b3a3d839e8933bea760dfbda3a6e4526d` and
`985f9bbe88a528d3139b5d09790a391e4529167d9c3c25ce5aef707ab7e8114e`;
the fixture source SHA-256 was
`d2716f17f887d267ac2a2c7eee1c6c79d9500ab99faf86e0b89dd194c31360d8`.
The temporary orchestration script SHA-256 was
`6268d6997db542c8a8c0e9199f275638ab412d912a1400de8f1ff10d5fd7385f`.

The probe does not call the resolver, load a framework, create a Metal device,
execute a GPU kernel or qualify Metal inference, and uses an old diagnostic
compiler rather than a current selfhost build. The complete merge and resource
governor remain unqualified.
