# Compile twin gap: the kgraph capacity (2026-10-08)

Gap 2 of `docs/selfhost-compile-twin-spike-20261008.md`: on the Kotoba route the compiler itself, running as a guest, traps
`KEXE_TRAP {:kind :budget :reason :budget/cells :arena :kgraph}` on 8 programs (`kgraph-8.txt`). This note says what fills
the table, how much each program needs, whether 4096 is a resource bound, and what each way out moves. Nothing decided was
changed: `tools/kexe_loader_decisions.kotoba`, `KEXE_KGRAPH_CAPACITY` and the artifact ABI's `:kgraph-capacity 4096` are
as they were.

## Method

- `seed/tests/kgraph-capacity/loader-variant.sh <capacity> <out> [indexed]` builds an investigation copy of
  `tools/kexe_loader.c` with another capacity. With `KEXE_KGRAPH_REPORT` set it prints a census after every guest run
  (`KGRAPH {:used .. :kw-entities .. :kw-static .. :kw-chunks .. :other ..}`) and, on a completed run, the number of
  `kgraph_get` calls and datoms they scanned; `KEXE_KGRAPH_DUMP=<file>` writes the text of every registered keyword.
  `indexed` answers `kgraph_get` through an (e, a) hash instead of the linear scan (same answers).
- `rerun.sh` re-runs the compile-twin guest (`spike.bin` from `seed/tests/compile-twin/run.sh`) under such a loader and
  classifies against the host kexe run.sh left behind; `census.sh` runs the guest only, over a list.
- Two spikes: the committed one (`base`), and a measurement variant (`fb`, not committed) whose `lower!` falls back to
  `kotoba.kir.lowering/lower-base` on `kotoba.kir/oracle-unavailable`, so that oracle-gap programs reach the backend.
  Both linked by seed r6m `8d3338e1` against `build/seed17/front0`.

## 1. What fills the table

The frontend never calls `kgraph-assert!` itself. The datoms are seed rung r6l's run-time keyword registry
(`seed/tests/r6b/srclib/r6b-lib.kotoba`, `__r6-kwreg`): every `keyword-from-string` / `document-keyword-value` registers
its text in the loader kgraph, once per distinct keyword: 1 datom if the module's static `__r6-kwtab` has it (value -1),
else 1 + ceil(code points / 3). Nothing is retracted; the kgraph is not reset by `arena-scope`.

Measured on all 8 (`fb` spike, 65536-datom loader): `:other 0` (no datom that is not the registry), no keyword text
registered twice, and 92-97% of the datoms are identities minted by kotoba-native's Kotoba arms
(`machine_ir.cljk` at kotoba-native `752cdf2`: `keyword-ns-name`, `rename-labels`, the `kotoba.gmir.label/`,
`kotoba.gmir.vreg/`, `kotoba.native.kernel-memory/`, `kotoba.native.internal.self-tail/`, `kotoba.native.function/`
sites; 12 `keyword-from-string` calls). The longest are `rename-labels`' function-local labels, which concatenate the
whole old label onto the function's namespace, e.g. `:kotoba.native.local.13.bulk/kotoba.native.self-tail.28.kotoba.mir.label.fuel-present`
(85 code points, 30 datoms).

| program | datoms | static kw | dynamic kw | of which backend | backend datoms | without backend kw |
|---|---:|---:|---:|---:|---:|---:|
| bench/runtime-comparison/kernel_state | 4,944 | 401 | 314 | 308 | 4,523 | 421 |
| examples/recursive-tree | 4,153 | 433 | 233 | 222 | 3,679 | 474 |
| seed/tests/conformance/stdlib/i64_set | 5,270 | 435 | 263 | 252 | 4,782 | 488 |
| test/nbb/fixtures/lazy-sequence | 8,959 | 449 | 491 | 479 | 8,441 | 518 |
| examples/approval-queue-app | 9,284 | 471 | 541 | 508 | 8,650 | 634 |
| seed/tests/conformance/stdlib/sorted_map | 12,291 | 442 | 607 | 588 | 11,766 | 525 |
| seed/tests/conformance/abort/ex_info_round_trip | 28,170 | 480 | 1,643 | 1,582 | 27,258 | 912 |
| test/nbb/fixtures/typed-closure-parameters | 28,285 | 476 | 1,648 | 1,590 | 27,389 | 896 |

Over the whole 372-program corpus (`fb` spike, guest only): 311 complete, 61 refuse (exit 65), no trap; exactly these 8
need more than 4096. The smallest program needs 417 (358 keywords, the frontend's own vocabulary). Need tracks the
emitted code: Pearson r = 0.975 between datoms and aarch64 code bytes over the 311 (0.37 against source bytes), about
1.6 datoms per code byte above the 417 baseline. So 4096 caps one process at roughly 2-3.5 KB of emitted code.

Legitimate or leak: proportional to the program (no duplicate registration, no growth across phases beyond what each
phase names), so not a leak in the sense of repeated work. But it is the wrong store for what it holds: the backend's
labels are transient per function and live for the process, and they share one table with user `rel`/`query` datoms
(ADR-2607198300), so a seed-compiled user program that makes keywords at run time spends its own datom budget on them.
Not a bug in this repo, and not a correctness bug anywhere; no frontend change was made.

The current committed spike reaches the backend on only 4 of the 8 (i64_set, sorted_map, approval-queue-app,
kernel_state); the other 4 now refuse earlier with `kotoba.kir/oracle-unavailable` (gap 1) using 121-135 datoms. With
the oracle fallback they too exceed 4096.

## 2. Host path, and what the 4096 is

- The host `bin/amu compile` (nbb) does not use the kgraph to compile: its keywords are host values. The kgraph is touched
  on the Kotoba route only by r6l's registry; the 4096 limit appears in self-host only because of that rung.
- Origin: `KEXE_KGRAPH_CAPACITY 4096u` came with the kgraph ops (86df0919b, 2026-07-19, a 6-datom Customer pilot),
  copied from the pair capacity with no measurement; `tools/kexe_loader_decisions.kotoba` constant 2 says only "kgraph
  datoms per run." `kotoba-lang/lang/limits.edn` has a kgraph entry only under `:profile/reference` (osaho's interpreter
  arena, `kotoba.kir/default-kgraph-capacity`); `:profile/native :cells` has pairs, vectors and vector items, not the
  kgraph. r6l's own record (seed/CONTRACT-REQUESTS.md, 2026-10-04 SEEDLANG) left raising it OPEN for the decisions owner.
- Resource: 24 B per datom (96 KiB at 4096; 1.5 MiB at 65536). The real cost is time: `kgraph_get` is a linear scan and
  the registry calls it per keyword creation and per code point decoded. ex_info_round_trip (28,170 datoms): 6,022,187
  gets scanning 40,093,150,350 datoms, 100 s wall; with the (e, a) index the same run is 81 s and writes byte-identical
  output (sorted_map 14.6 s -> 13.7 s, i64_set 8.2 s -> 6.7 s; timings taken with four census runs sharing the machine).
- Verdict under the house rule: as a fixed array size it bounds no resource the guest could exhaust, and it protects no
  invariant: the generated code does not depend on it (the bound is checked in the host's `checked_kgraph_assert`). It is
  a record of the pilot. As a per-run default budget it would be a legitimate bound, which is what the pair arena already
  is: the ABI states `:pair-capacity 4096` while `KEXE_PAIRS` raises the pair budget to 64 Mi per run.

## 3. Options and what they move (measured with loader variants; nothing installed)

| capacity | committed spike (8) | oracle-fallback spike (8) |
|---|---|---|
| 4096 (today) | 4 kgraph trap, 4 oracle-unavailable | 8 kgraph trap |
| 16384 | 4 SAME, 4 oracle-unavailable | 6 SAME, 2 kgraph trap (ex_info_round_trip, typed-closure-parameters) |
| 32768 | 4 SAME, 4 oracle-unavailable | 6 SAME, 2 CODE-DIFF (same two) |
| 65536 | 4 SAME, 4 oracle-unavailable | 6 SAME, 2 CODE-DIFF (same two) |

The two CODE-DIFFs are the fallback's own effect (no sealed oracle `:value`; the guest emits 29,458 / 29,748 B against
the host's 24,486 / 24,776 B): gap 1, not this one.

(a) A per-run kgraph budget, raised for compiler-hosting images only. Map the datom array over a maximum (address
space, as `KEXE_PAIR_MAX`), keep 4096 as the default budget, add an override (`KEXE_KGRAPH`, and
`KEXE_EMBEDDED_KGRAPH` in `scripts/seed/launcher/build.sh`). User artifacts keep `:kgraph-capacity 4096` and the
verifier's expected context unchanged, exactly as `:pair-capacity` does. Moves all 4 current kgraph programs to SAME at
16384, and all 8 past the kgraph at 32768. Consequences: a decision-record change (default + max, with these
measurements) and a `:profile/native :cells :kgraph` entry in limits.edn; and because need grows about 1 datom per code
byte, compiling anything compiler-sized needs millions of datoms, where the linear `kgraph_get` is quadratic, so the
budget should land with the (e, a) index (a mechanism change; measured identical output).

(b) Stop the backend minting transient identities as keywords (kotoba-native, its Kotoba arms: labels, vregs and
function ids as i64 or string forms, or at least `rename-labels` without re-spelling the whole old label). Computed from
the dumps: the 8 would need 421-912 datoms, all under today's 4096 with no loader or ABI change, and need would stop
tracking code size. Cost: a kotoba-native change across the 12 sites and their consumers; not this repo.

(c) Other, in the seed's registry (a rung change): (c1) its own loader table instead of the user-visible kgraph, which
restores the invariant that a program's datom budget is its own (needs a context slot, i.e. an ABI bump); (c2) a denser
encoding, 8 UTF-8 bytes per datom and no -1 marker for static keywords: computed 1,613-11,924 datoms for the 8, so 4
still exceed 4096 (approval-queue-app 3,808 fits; sorted_map 4,960, ex_info 11,874, typed-closure 11,924 do not). Helps,
does not settle.

## Recommendation

(b) is the fix: the compiler's own label bookkeeping should not live in an interning table that never frees, and it
removes 92-97% of the need. Until kotoba-native does it, (a) unblocks the twin, but it is the user's decision: turn the
kgraph into a per-run budget like the pair arena (default 4096, the artifact ABI unchanged), give the compiler-hosting
launcher 32768 or more, and land the (e, a) index with it. (c1) is worth doing independently of both, because the
registry today spends user programs' datom budget.

Not verified: two or more compiles in one process (the registry would grow across them, deduplicated by text); x86-64.
