# Adopted compiler integration — 2026-10-12

Owner request: integrate only the compiler improvements adopted by this session,
preserve unadopted candidates, and keep the C-or-faster goal paused.

The task branch had diverged from main by hundreds of commits and contained
experiments and unrelated source migrations. Main had no `seed/` compiler.
This integration copies the complete adopted 16-module compiler
closure from `fc49cb2ee6fea1a41a5abbc8ed5b52aaa9f19471`, its source contracts,
the reviewed native bootstrap and its frozen trusted loader. It does not merge
the task branch wholesale or replace current main's `src/`, `bin/`, runtime,
loader, dependency locks or existing workflows.

No mechanical source refactor was performed. Fifteen modules are byte-identical
to the measured source. A one-off safety fix in `90-drv.kotoba` makes every
explicit `--policy` a named E2170 refusal: the unqualified legacy text scanner
cannot authorize an empty allow set through deny fields or comments. This is
not an optimization candidate; `41-a64gen.kotoba` is unchanged. The new build
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
- Current source unity SHA-256:
  `3871578dbc64cb6ce29f8f3e461a90ddaf2e613a60d359cf21b0657f8a4ba3f5`.
  The original measured unity remains recorded in the adoption receipt.
- Current native compiler: 1,717,904 bytes, SHA-256
  `c3b7b6ffb9c39a716791d69e5d2049bb893dbd18eed3432e19c69debc78711cc`.
  This is a safety-fix image, not a newly measured optimization.
- Historical qualification: 39 native images, 483 original paired cases,
  68 fresh generic pairs, 32 bootstrap success pairs. This history is not
  relabeled as a fresh main campaign.
- The integration build runs the pinned native compiler on this exact source
  for three generations; its original raw stdout/stderr and call records are
  preserved separately. Every generated image must match the current pinned digest.
- Static PRODUCT host-dependency inventory: all 96 PRODUCT lines unchanged
  against the current-main `src/` and `bin/` baseline. The C loader and Python
  orchestrator are explicit bootstrap infrastructure.
- Seven explicit-policy inputs are refused without producing an artifact;
  a policy-free source compiles and executes with result 42. All 39 complete
  emitted native images and containers equal the previously qualified outputs.
- The host loader and logs are outside the guest-writable artifacts directory;
  no checkout root is granted. Two outside-scope write probes refused (exit 120),
  created no files and left the host loader and producer unchanged. A native
  self-build job runs on macOS arm64 CI.
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

## Subsequent paused maintenance

The identities above describe the original integration. The follow-up
`seed/check-policy-integration-20261012.json` records the safety-fixed current
compiler after applying explicit-policy refusal to single-file/project `check`.
`seed/adoption-20261012.json` is the current source/bootstrap authority. Main's
optimization module and public loader remain unchanged. The older preservation
source is separately restored under `seed/preserved-20261012/`, with its own
policy-fixed source, bootstrap and qualification. The performance goal remains
paused and no historical timing is relabelled as a new image measurement.
