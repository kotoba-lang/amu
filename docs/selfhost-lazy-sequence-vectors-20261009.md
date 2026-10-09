# lazy-sequence on the Kotoba route: the vector table (2026-10-09)

`test/nbb/fixtures/lazy-sequence.kotoba` (281 bytes) was the one corpus program the product entry nbb.aarch64-cli refused
on the Kotoba route while the host compiled it: the guest trapped `KEXE_TRAP {:kind :arena :reason
:vector-table-exhausted}` / `:budget/cells :arena :vectors` under `KEXE_VECTORS=67108864` (seed/tests/compile-cli/run.sh,
full corpus run of 2026-10-09: 289 SAME-SHAPE, this one HOST-ONLY).

## 1. What exhausts the table

`KEXE_ARENA_USE` on the real entry (image of that run, 1 Mi kgraph): at the trap 67,108,864 vector handles (the ADR 0364
ceiling, all of it), 128,949,668 vector items (of 134,217,728), 36.4 M pairs, after 189 s. The handle table runs out first;
the item arena was 96% full. For scale, on the same image: seed/tests/r1/feat/01-do-value 118 K handles, sorted_map
(12 KB of source) 6.86 M, seed/tests/conformance/functions/lazy_sequences 893 K. Not proportional to the program.

Bisection by program (variants of the fixture, same image):

| main | handles |
|---|---:|
| `(lazy-first (naturals 42))` | 1.76 M |
| one `lazy-map` over naturals | 4.61 M |
| one `lazy-filter` over naturals | 4.74 M |
| `lazy-map` of `lazy-map` | > 33.5 M (trap at a 32 Mi budget) |
| the fixture (`lazy-filter` of `lazy-map`), filter threshold 37 .. 41 | 67.1 M (trap) at every threshold |

So it is not the number of elements forced (threshold 37 forces one) but the nesting.

Bisection by phase: a probe entry linked against the same objects runs nbb.cli's steps one at a time (analyze, native
admission, effect-row check, `lower!`, `native-program`, the aarch64 emitter, `compatibility-form`,
`definition-identity/describe`, `assemble`). For the two-map variant every step stays under 3.6 M handles except
`definition-identity/describe` and `assemble`, which calls it: both exhaust 32 Mi. `describe` with its permutation
loop cut to the first permutation: 1.25 M.

The cause, in amu's own `src/kotoba/compiler/definition_identity.cljk` (the Kotoba reading of `best-candidate`): a recursive
group's member ordering is the permutation whose group payload has the smallest canonical hex, and the reading built
and encoded the whole payload of every permutation (re-linking every member body, `kir-id/normalize`, CBOR, hex). The
lazy-sequence fixture's desugaring makes a seven-member recursive group (host provenance: group indices 0..6), so
7! = 5,040 payloads; the next largest group in the corpus has 2 members. The host does the same 5,040 encodings and its
GC frees each; on the Kotoba route nothing an iteration allocates is reclaimed (the seed compiles `arena-scope` as `do`,
seed/21-check.kotoba `ck-r6m-arena`), so the whole search stays allocated: an accumulation across iterations, not a
resource the program needs. Raising the vector budget would not have been the fix: the ceiling is already the budget,
and an 8-member group (the host's limit) costs 8x more.

## 2. The fix (amu, `kotoba.compiler.definition-identity`, Kotoba reading only)

`best-candidate` now computes the same choice from one template per member:

1. Across permutations a group payload differs only in `:members`: when the identity encodes it, the dependency vector is
   sorted, the effect row is a set and the interface is the member count. `:members` encodes as the CBOR array of the
   members' encodings, and CBOR items are prefix-free, so the payloads' hex order is the byte order of the members'
   encodings concatenated in arrangement order.
2. A member's encoding depends on the arrangement only through `[:kotoba.definition/group g]` (g = the position of a
   member its body mentions), and g < 10 encodes as the one-character text "g". Unless a mention sits inside a set
   element or a map key, where the identity's sorting could move it, the encoding is a fixed template with holes.
3. Each member is encoded twice (member j at position j, then at j+1 mod n) to find its holes. Every permutation is
   then compared with the best so far by streaming the templates with the holes filled, in the old iteration order and
   with the old tie rule (strictly smaller wins, so the first of equals stays). The chosen arrangement is built with
   `group-candidate` as before.

A mention inside a set or map key, a group of more than 9 members, or templates that do not line up go back to the old
search (`best-candidate-full`, unchanged). The host reading is unchanged.

Measured on the probe (same objects, same budgets):

| program | `describe` handles before | after |
|---|---:|---:|
| one `lazy-map` (4-member group) | 1.17 M | 0.78 M |
| `lazy-map` of `lazy-map` | > 33.5 M (trap) | 1.47 M |
| lazy-sequence fixture (7 members) | trap | 1.24 M |

The whole `compile-native` of the fixture: 6.79 M handles, 7.23 M items, 17.3 M pairs.

Equivalence with the old search: the probe printed `describe` once with the old object (`best-candidate-full` only) and
once with the new one. The output is byte-identical for nine programs with recursive groups of 3 to 6 members. They
include two symmetric cycles, where every rotation ties and the tie rule decides `:group-index`, and a group whose body
holds a set literal. A first version of the comparison stepped past the end of one arrangement before the other and
broke ties wrongly; the 4-cycle with rotation ties caught it. The cycle programs are committed as
`seed/tests/definition-identity-cycles/`. The host comparison of seal and provenance (which carries every
definition's `:cid`, `:group-cid` and `:group-index`) is in section 3.

## 3. Verification (2026-10-09, load average 370-530 during the runs)

- Real entry, full corpus: `seed/tests/compile-cli/run.sh <front> <work>` against the full3 objects with this
  `kotoba.compiler.definition-identity` recompiled; nbb.aarch64-cli built from source, kexe-loader-1mi,
  `KEXE_KGRAPH=1048576`, `KEXE_VECTORS=67108864`. 372 programs: 290 BOTH-ACCEPT with seal, provenance and stdout SAME and
  publication SAME-SHAPE (was 289), 2 SIZE-DIFF, 62 BOTH-REFUSE, 1 BOTH-REFUSE-CLASS-DIFF, 17 HOST-ONLY (was 18).
  Compared with the coordinator's full run of the same entry before the change, 371 rows are identical (the 12
  comparison columns and the guest's message). The one change is lazy-sequence: HOST-ONLY (exit 120, vector table) became
  BOTH-ACCEPT with seal SAME, provenance SAME, stdout SAME, publication SAME-SHAPE.
- The 7 programs of `seed/tests/definition-identity-cycles/` on the same image: all BOTH-ACCEPT, seal, provenance and
  stdout SAME. The first version of the set-literal program used `#{1 2}`: the host refuses that set (its literal is
  `[:set :keyword]`) and the Kotoba frontend accepts it, a frontend difference that predates this change. The program now
  uses `#{:a :b}`.
- `npm run test-loader-decisions`: 17 failures, the same as the base (the 16 `KEXE_VECTORS` ceiling cases of ADR 0364
  and their summary line). `tools/` is unchanged.
- Image: the linked entry is 8,283,601 bytes (was 8,275,577: +8,024), 105,007 under the 8,388,608 extract-native limit.

No budget or ceiling changed; ADR 0364 and 0369 still hold. What remains: the seed does not reclaim `arena-scope`
(21-check `ck-r6m-arena` compiles it as `do`), so any other loop on the Kotoba route that allocates per iteration
accumulates the same way. Reclaiming it there would need a seed rung.
