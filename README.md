# Amu

Amu is the deny-by-default Kotoba compiler. Its core is the measured Embench
compiler lineage pinned in [`seed/compiler-core.json`](seed/compiler-core.json)
and the sixteen canonical sources in [`seed/MANIFEST`](seed/MANIFEST).
Frontend, lowering, optimization and backend behavior grow from that core.

## Current compiler availability

**The C/JVM/Node compiler implementations and their build/launch routes have
been removed in this candidate. A loaderless bootstrap compiler, measured-core
self-rebuild and native FS2 packager now execute successfully.** Fresh native
Embench correctness is 19/19; this is not a new timing score or full public
compiler qualification. Exact identities and limits are recorded in
[native bootstrap progress](docs/native-compiler-bootstrap-progress.md).
The [completion gauge](docs/native-compiler-completion-gates.md) tracks all
acceptance gates through merged main verification and cleanup.

`bin/amu`, `bin/kotoba` and `bin/kotoba-compiler` still report unavailability
with exit 69 until the complete public target/profile, locked import and CLI
closure is qualified. They do not fall back to NBB/KBB, Node, Java/Graal or a
C loader.

See [hosted compiler retirement](docs/native-compiler-retirement.md) for the
complete file inventory, source recovery and pending native admission gates.
The compiler must be produced and rebuilt by Amu selfhost from canonical
`.kotoba`, without C/JVM/Node in its build, packaging or execution closure.

## Native admission

The complete initial compiler, self-rebuild/fixed point, all nineteen Embench
workloads and public dotted-ID/legacy-alias import and CLI behavior must run
through that same native compiler before #1428 is merged to main. Source
ports and historical offline receipts are not native execution evidence.

- [Selfhost priority and acceptance](docs/selfhost-priority.md)
- [Measured compiler-core decision](docs/adr/0370-embench-measured-compiler-core.md)
- [Seed source and historical evidence](seed/README.md)
- [Native CDCI retirement and gaps](docs/native-cdci-retirement.md)

Amu checks and compiles code; grant decides permission; Kototama and OS hosts
enforce runtime authority. Amu and the execution foundations remain separate
repositories. Browser/Wasm output does not authorize a Node compiler host.

Older CLI instructions and hosted implementation details are preserved in
Git at the retirement inventory's preserved commit. They are historical,
not current installation instructions. Existing evidence, test/refusal
corpora and dependency provenance remain available for the native port.
