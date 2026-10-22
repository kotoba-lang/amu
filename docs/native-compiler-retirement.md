# Hosted compiler retirement

The owner directed removal of the C/JVM/Node compiler routes on 2026-10-22.
This candidate removes the hosted compiler implementation from `src/`, the
tracked NBB cache, NBB/KBB launch/configuration and npm compiler installation,
the C loaders and embedded compiler wrapper, and hosted compiler build/test
drivers. The Kotoba tools that still built or started a C loader are also
removed: writing the driver in Kotoba did not make its execution native-only.

`bin/amu`, `bin/kotoba`, `bin/kotoba-compiler` and `bin/amu.cmd` now report
compiler unavailability with exit 69. They do not offer a hosted fallback,
search PATH for another compiler, select an arbitrary binary through an
environment variable, or report success for `--help`/`--version`. These are
temporary refusal entrypoints, not the native compiler implementation.

The compiler is the measured Embench lineage pinned in
[`seed/compiler-core.json`](../seed/compiler-core.json), with the historical measured sources
retained and the current FS2 successor pinned separately. Canonical Kotoba compiler/runtime ports,
input/refusal corpora, dependency pins, adoption receipts and historical
Embench measurements remain available. Browser JavaScript runtime output and
C benchmark comparators are separate from the removed compiler host.

[`retirement/hosted-compilers.json`](retirement/hosted-compilers.json) lists
every removed/replaced file with its original commit, Git blob and SHA-256.
The preserved commit is an ancestor of this candidate. Recover an individual
source for port review with `git show <preservedCommit>:<path>`; do not restore
it to the active compiler route. A local task archive preserves the same
original bytes independently. No original checkout, WIP, stash or unrelated
branch is removed by this change.

Documentation, `bench/` and `docs/evidence/` from older experiments contain
historical commands, C sources and payloads. They are retained evidence, not
supported compiler installation or build entrypoints. The saved full-19
offline audit can still verify those receipts; it does not execute the new
compiler. `deps.edn` and its existing lock retain dependency provenance,
including historical alias metadata; they no longer select an installed
hosted compiler implementation in this repository.

A loaderless native bootstrap and measured-core self-rebuild now exist.
The current all-native chain freshly compiled, packaged and ran all nineteen
Embench correctness workloads, without the earlier IR calculator. See
[native-compiler-bootstrap-progress.md](native-compiler-bootstrap-progress.md)
for exact identities and the remaining gates.

Public admission remains open: the current core emits the historical raw
AAPCS64 KSEED format, not the complete public target/profile/artifact surface.
Locked dotted-ID/alias imports, default Kototama output, complete canonical
compiler/CLI dependency ports, owner main/lock/CID integration and whole
refusal/authority/resource/cleanup/controller qualification are required.
Until those gates pass #1428 stays draft, the temporary public launchers still
refuse, and no main merge is performed. No Actions or branch-protection
setting changes are part of this retirement.

The separately held Git `scripts/merge-guard.mjs` and its existing workflow
remain unchanged. This repository-maintenance check is not a compiler host;
removing the Node compiler does not authorize removing that safety guard.
