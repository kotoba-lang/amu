# C-free seed runner: measured context-slot usage (JUN-29, 2026-10-19)

Answers open measurement 1 of `native-seed-c-free-runner-surface.md` (which of
the 36 `kexe_context_v11` function slots the compiler payload actually calls on
the `compile --target x86_64-linux` path) and the admission half of open
measurement 2 (can the seed scalar subset express the runner at all). This is
a measurement record; it claims no runner implementation.

## Method (measurement use of the trusted C loader only)

An instrumented COPY of `seed/bootstrap/adopted-loader-20261012.c`
(sha256 `f44b50995a0e45db4be35244da34dd61538a484c7d5ea2f15f7f5a73d9daa8c3`,
the pinned bootstrap source) was built in scratch; the approved loader identity
pins are untouched. Instrumentation: one wrapper per function slot is assigned
at the context fill site (`shared->context.<slot> = hit_<fn>;`), each wrapper
counts then forwards to `checked_<fn>`; counters are MAP_SHARED and printed by
the supervisor after the guest exits. Off unless `KEXE_SLOT_HITS=1`. Counting
at the fill-site wrapper (not inside `checked_*`) excludes loader-internal
calls to shared helpers like `checked_pair_new`.

Non-interference, measured: the instrumented and stock loaders produce
byte-identical `G1.kx64` (sha256
`1ac5a42a089edd5e0a60b683ad0a83d93e0e78c0393b085ee8917cd783ecac64`) for the
same compile, and identical guest stdout on runtime case runs.

Workloads and provenance (all run on macOS arm64, 2026-10-19):

* unity source AS MEASURED: `seed/X86_64-LINUX-SELFHOST-MANIFEST` concat,
  12 modules, 628,698 bytes, sha256
  `11a3ea25e9e8fbe03a9cc9cc9261a684278a5bea80b1547ca98be4710448038f` —
  the manifest state at measurement time. It is NOT the checked-in source
  graph of this tree: re-running `scripts/seed/check-x86_64-selfhost.py`'s
  manifest parse and newline concatenation (the script's own convention,
  join of module bytes + newline) at this commit yields 13 modules,
  637,272 bytes, sha256
  `a11c2f18220501b195c0eb99244775c999bd11643c46588b3cf44bc89854c847`
  (review-finding follow-up: the manifest gained a module after the
  measurement). The slot-hit numbers below bind to the AS-MEASURED pin.
* producer: `seed/bootstrap/adopted-20261012.bin`, sha256
  `6b158aa8654706743462b8a730f189072ba05f364b00af28a3f6d23045add2eb`
  (adoption receipt `seed/adoption-20261012.json` matches). It refuses
  `--target x86_64-linux` ("E2 unsupported target (only aarch64-macos)"), so
  the bridge compiler was built first exactly as
  `scripts/seed/check-x86_64-selfhost.py` does: producer compiles unity to
  `--target aarch64-macos` (41 s), `bridge.bin` extracted, sha256
  `3619e01ea224e81eb50e3709cffaecefcfbfdc115445b6345581373d7486ddf3`.
* grant/wires for every compile run: `35,37,38,39`, `KEXE_FUEL=off`, the
  `scripts/seed` envelope (4194304 / 134217728 / 268435456 / 16777216).

## 1. Compile path (`bridge.bin` compiles unity, `--target x86_64-linux
--format kx64-v1`, 1.0 s) — 10 of 36 slots called

| slot | calls |
|---|---|
| `string_code_point_at` | 14,202,841 |
| `pair_new` | 433,948 |
| `string_substring` | 17,052 |
| `string_equal` | 17,044 |
| `vector_alloc` | 249 |
| `typed_cap_call` | 20 |
| `string_concat` | 23 |
| `string_index_of` | 14 |
| `vector_conj` | 623 |
| `bytes_from_vector` | 5 |

The 24 pinned `cases()` sources compiled through the same path add no slot
outside this set (per-case data: `docs/evidence/jun29-slot-hits-20261019/`).
The producer→bridge compile of the same source (`--target aarch64-macos`) uses
the same 10-slot set, counts within 2 %, so the target back end does not move
the caller set.

## 2. Guest runtime (the 24 pinned cases executed under the x86_64 loader via
Rosetta, `allow "-"`, `KEXE_FUEL=1000000`) — 18 of 36 slots called

Adds to the compile set: `pair_first` (3), `pair_second` (6), `vector_at` (9),
`vector_count` (4), `vector_assoc` (1), `vector_assoc_in_place` (93),
`string_compare` (1), `string_from_utf8` (1). Largest counts:
`vector_assoc_in_place` 93, `vector_at` 9, `vector_alloc` 8.

**Measured union across both surfaces: 18 function slots. Never called in 26
runs: `cap_call`, `kgraph_assert/get/count/entity_at`, `vector_new_empty`,
`vector_drop`, `arena_enter`, `arena_leave`, `string_fold_ascii`,
`string_find_blank`, `string_skip_blank`, `string_index_of_from`,
`string_compare_lines`, `string_find_byte`, `string_append_range`,
`bytes_slice`, `bytes_concat`.**

Caveats the runner must not lose:

* 0 hits is a lower bound over these workloads, not a proof of unreachability.
* The v9/v10 **data** slots (`pair_used_pointer`, `pairs_base`,
  `pair_validated_base`, `vector_used_pointer`, `vectors_base`,
  `vector_items_base`, `code_base`, `code_length`) are read inline by the
  emitted code without a function call; a 0-hit function slot (e.g.
  `pair_first`) does not license removing its data slot. Which emitters read
  which data slots is still open (static, `seed/41-a64gen.kotoba` +
  `seed/7x` emit paths).

## 3. Can the seed scalar subset express the runner? Measured: no

`xg-main` in `seed/70-x86_64-linux.kotoba` routes `--target x86_64-linux`
WITHOUT `--format kx64-v1` to `xg-command`, the standalone scalar ELF profile
(the only profile whose output stands alone; `kx64-v1` containers need a
loader — the chicken-and-egg the C-free runner is meant to break). Empirical
refusals compiling four probes with the bridge compiler:

| probe | result |
|---|---|
| `(defn main [] :i64 (+ 1 2))` | OK, ELF64 ET_EXEC emitted (`7f454c46`) |
| lambda + `invoke` (closure) | refused: `x86 refused function frame=48 kind=4 n=2 rt=1 sir=20`, error 7102 (`xg-refuse-fn`) |
| `(string-length "hello")` | refused: `E7101 unsupported scalar profile or code limit; detail 16` (SIR op 16 = `OP-STR`) |
| `typed-cap-call` | refused at admission: `E2121` |

Source confirmation (`xg-check-sir`, `xg-check-fns`): scalar mode admits only
SIR ops `OP-FN`(1)…`OP-CALL`(13) plus `OP-FUEL`(18), `OP-RET`(19),
`OP-TRAP`(20); functions may not be lambdas/adapters/handles/capabilities/
floats/state, ≤5 scalar params, frame ≤4096; the only export is
`main : () -> i64`; the only I/O is `xg-start`'s fixed stub (call main, write
the 8-byte result to stdout, exit). Ops 14-17 (`OP-RT/OP-CAP/OP-STR/OP-VEC`)
and 21-26 (including `OP-TAB` context dispatch and indirect call) are refused.

The runner minimal slice (container admission + arena pre-map) therefore
**cannot be written in the seed scalar subset**: it needs capability/IO access
(refused), handle-arena operations (refused), and `mmap` before sandbox
installation (no syscall surface exists in the profile at all). The C-free
runner is an explicit dependency on the kernel profile
(`:aiueos-c-free-bare-metal-v1`, ADR 0271 production order; kotoba-lang/aiueos
side, JUN-30/JUN-102), not something the seed compiler subset can bootstrap.
Recorded as a dependency on JUN-29, not worked around.

## 4. What this bounds for the runner

* SCOPE (review finding): the compile-path profile above was taken with
  the AArch64 `bridge.bin` doing the compile. When the C-free runner
  hosts the x86 image (G1/G2/G3 compiler), the same operations route
  through `xr-rt` and the function vtable (`seed/71-x86_64-runtime.kotoba`)
  instead of the AArch64 emitter's inline data-slot accesses, so the
  slot-hit counts are the AArch64 path's and do NOT transfer to the x86
  runtime. Measuring the compiler under the x86 runtime is the open
  follow-up; until then, x86-runtime slot demand may be a superset.
* Runner bootstrap vtable for the seed compile path = the 10 compile-path
  function slots; to also serve general guests on current seed output, 18
  slots (the measured union) + the v9/v10 data slots.
* The remaining 18 function slots can be denied (`SIGILL`/`SIGTRAP` as the
  loader does) unless a later workload proves them reachable.
* Next open measurement: enumerate data-slot reads in the emitters
  (static) — **done, see `native-seed-c-free-runner-data-slots-20261019.md`**
  (aarch64 inline set: version@0=11, fuel@8, 288, 296, 312, 320, 328, 384,
  392; `pair_validated_base`@304 has zero inline readers; the x86-64 `7x`
  path reads only fuel@8 inline). The kernel-profile runner slice admission
  receipt binding (runner/compiler/source-graph/output hashes) is specified
  in the same document §4 (connects JUN-30 / JUN-102).
