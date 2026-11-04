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
