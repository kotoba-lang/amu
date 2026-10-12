# Adopted compiler integration — 2026-10-12

Owner request: integrate only the compiler improvements adopted by this session,
preserve unadopted candidates, and keep the C-or-faster goal paused.

The task branch had diverged from main by hundreds of commits and contained
experiments and unrelated source migrations. Main had no `seed/` compiler.
This integration therefore copies the complete adopted 16-module compiler
closure from `fc49cb2ee6fea1a41a5abbc8ed5b52aaa9f19471`, its source contracts,
the reviewed native bootstrap and its frozen trusted loader. It does not merge
the task branch wholesale or replace current main's `src/`, `bin/`, runtime,
loader, dependency locks or existing workflows.

No mechanical source refactor was performed: all adopted compiler modules are
byte-identical copies, checked against the measured unity digest. The new build
script is bootstrap orchestration of existing native operations, not a new
compiler implementation or language fallback.

The cumulative adopted source includes guarded scalar composition, exact fuel
handling, descriptor-cache proofs, affine writers and other previously qualified
passes, followed by masked XOR, literal-width private-call/prefix specialization,
call-result comparison forwarding, stack operand reuse, signed division by two,
and cached successful bounds-check reuse. Exact source and image identities,
not this abbreviated list, determine the integrated product.

## Verification boundary

- `seed/adoption-20261012.json` binds all source modules, unity order, the native
  bootstrap, trusted loader and historical correctness evidence digests.
- Source unity SHA-256:
  `4461c66ca686dcb57f7cbb1b8e605b50ff7d7574b72f0e71d61d751540da07ba`.
- Adopted native image: 1,718,312 bytes, SHA-256
  `6cbbba96f7e5f3544c0b3343a83dc75c916a1a9321075e5e629d1b746fb7731a`.
- Historical qualification: 39 native images, 483 original paired cases,
  68 fresh generic pairs, 32 bootstrap success pairs. This history is not
  relabeled as a fresh main campaign.
- The integration build runs the pinned native compiler on this exact source
  for three generations; its original raw stdout/stderr and call records are
  preserved separately. Every generated image must match the adopted digest.
- Static PRODUCT host-dependency inventory: all 96 PRODUCT lines unchanged
  against the current-main `src/` and `bin/` baseline. The C loader and Python
  orchestrator are explicit bootstrap infrastructure.
- No fresh performance measurement, release, default CLI replacement,
  whole-component Q9 or C-free build claim is made.

## Preserved candidates and goal

Descriptor witness reuse, conditional-fallthrough vector-view reuse, and bounded
byte lookup remain excluded. Their three original worktrees were left intact;
independent source and patch snapshots with HEAD/digest records are preserved
under the integration task's scratch workspace. No candidate was newly adopted.

The optimization goal remains **paused and unmet**. Round 83 remains the latest
measured adopted source: all 19 workloads, geometric mean Kotoba execution time /
C execution time 2.936403450579294. This exploratory translated-port comparison
uses the upstream Embench driver and formula; it is not a certified official
Kotoba score. There is no minimum-percent adoption cutoff.

Public dated report: <https://kotoba-lang.org/ja/blog/embench-progress-20261012/>
