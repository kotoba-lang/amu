# ADR 0361 — Native growth regions: amortised list and string builders in the kexe loader

- Date: 2026-10-02
- Status: Accepted (owner decisions of 2026-10-02 for the self-build wave: aarch64-macos first, a `.kexe` run by
  `tools/kexe_loader.c` is the amu binary of milestone 1; the analysis is
  `docs/selfhost-efficiency-analysis-20261002.md`, critical path track 3, item C1).
- Amends: `tools/kexe_loader.c` `checked_vector_conj`, `checked_string_concat`, `checked_arena_enter` /
  `checked_arena_leave`, `intern_vector`. No ABI change (the context struct, the shared struct and every slot are
  unchanged), no compiler change, no change to any answer.
- Related: superproject ADR-2609160044 (arena scopes, ABI v6); the 2026-09-15 tail-append fast paths these extend.

## Context

`typed-list-conj`, `typed-set-conj` and `vector-conj` all lower to the loader's `checked_vector_conj`
(`kotoba.native.machine-ir` `normalize-surface-operations`), and `string-concat` to `checked_string_concat`.
Both append in place only when the operand ends at the top of its arena. Any allocation between two appends moves
the accumulator off the top, and the next append copies the whole accumulator. That is the ordinary shape of a
compiler pass (build a child, conj it onto the parent; print a piece, append it to the output), so a builder of n
items cost O(n^2) words.

Measured 2026-10-02 (aarch64-macos, the loader before this ADR, `KEXE_ARENA_USE=1`):

| workload | before |
|---|---|
| two `[:list :i64]` built in alternation, n = 1 000 / 4 000 each (`scripts/selfhost-wall/guests/list_builder.cljk`) | 1.0 M / 16.0 M item words; n = 16 000 exhausts the 128 M-word arena (`:vector-items-exhausted`) |
| desugar differential guest (`ds_guest_w`, 976 functions), 720 cases (235 KB), the same input 1x / 2x / 4x / 8x | string pool 3.3 / 10.9 / 39.2 / 148.3 MB: quadratic, from re-copying the output accumulator |

The pair heap and the vector table were linear on the same runs. The list case is the one the analysis named. The
string case was found while measuring it and is the larger cost in practice: the compiler emits text.

## Decision

A **growth region** is slack that the copy path reserves. When `checked_vector_conj` must copy an interior slice of
length L, the copy gets capacity 2(L+1) (at least 4 words), and the arena top moves past the whole capacity, so no
later allocation can land in the slack. The region records its **fill**: the end of the longest slice any handle
has claimed. A conj whose slice ends exactly at the fill writes the next word in place and advances the fill.
A conj on an older handle (its slice ends before the fill) finds the word taken and copies into a new region.
`checked_string_concat` does the same for a copied result of at least 256 bytes (capacity 2x). There a region is
found by its fill position through a direct-mapped cache, where a collision only costs a copy.

Safety is the argument the tail append already rests on. Every handle carries its own length, and no handle spans a
region's slack, so a word written at the fill changes nothing that any existing handle reads. A handle therefore
stays an immutable value. Handles minted by every other operation (views, slices, `bytes-concat`, `vector-assoc`,
literals) carry no region and copy on their first conj, exactly as before.

The tables are loader-private address space (`MAP_PRIVATE | MAP_ANONYMOUS`, mapped before the fork, touched only as
regions are made). An arena-scope LEAVE drops the regions created inside the scope, because every handle that could
name one was minted inside the scope and is dead. When the doubled capacity does not fit the run's budget, the copy
falls back to the exact size, so every run that fit before still fits.

`KEXE_NO_GROWTH_REGIONS=1` turns both off, which is the A/B switch. `KEXE_ARENA_USE=1` makes the supervisor print one
EDN line on stderr after the guest exits: the high-water mark of each arena (pairs, string pool, vector table, item
words, their sum in bytes) and what the conj and concat paths did.

## Evidence (after)

| workload | regions off | regions on |
|---|---|---|
| list_builder n = 16 000 | trap, 134 M words | 106 k words, 0.02 s |
| list_builder n = 1 000 000 (2 M appends) | (quadratic) | 6.8 M words (3.4 per item), 0.05 s |
| ds 720 cases x8 (1.88 MB of input): string pool | 148.3 MB | 4.6 MB (32x less; linear: 0.58 / 1.15 / 2.30 / 4.60 MB at 1/2/4/8x) |
| ds x8 peak RSS (`/usr/bin/time -l`) | 703 MB | 594 MB |

The outputs are byte-identical with regions on and off: the ds guest on all 11 differential batches and on the
1x/2x/4x/8x concatenations, and the 720 cases also agree with the host (ds-diff 720/720). Persistence is checked by
`scripts/selfhost-wall/guests/region_persistence.cljk` (answers `ok`). It conjes and concatenates on an older handle
of a region after a newer one exists, and checks that neither handle sees the other's append.

What regions do not change: the vector table still gains one entry per conj (a handle is an immutable (offset,
length) pair), and the pair heap is untouched. On the ds guest the pair heap is now 85% of the peak (28 M pairs =
447 MB at 8x, about 15 pairs per input byte). Reclamation, not copying, is the remaining memory question; see
`docs/selfhost-native-memory-20261002.md`.

## Consequences

- A builder is amortised O(1) words per append whatever the program allocates in between, at the cost of at most 2x
  slack on the regions in use.
- Out of scope, deferred with their targets (owner decision 1): `tools/kexe_loader_windows.c` and the Linux static
  image's runtime keep the copying conj.
- `tools/kexe_loader.c` changes, so its source identity (artifact's native loader hash) changes. The generated
  decisions region is untouched (`gen-loader-decisions.cljk --check` passes).
