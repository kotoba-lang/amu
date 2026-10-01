# Native lists of aggregate handles (design and result, 2026-10-01)

Premise (owner, 2026-10-01): the product must not need nbb, Node or the JVM. The first gap in
`docs/selfhost-native-gaps-20261001.md` was that `[:list [:ref :form/r]]` -- the type of `:kids` in the
recursive Form record every selfhost guest walks -- was not a native type, so no Form-based module (vx, ds, tm,
definition-identity, the value codec, and therefore the self-built compiler) could be compiled by the native
backend. This note records the design that closes it, what was changed in which repository, and what the
result is measured to be.

## 1. What the existing lowering already does

A typed list is **not** a new representation. Native has one "word arena" (the vector arena of the kexe
context, ABI v11):

- `kotoba.native.machine-ir/normalize-surface-operations` rewrites `typed-list-new` to a chain of
  `vector-conj` over `vector-new-empty`, `typed-list-conj` to `vector-conj`, `typed-list-nth` to `vector-at`.
  `vector-count` already walks the carrier, so no count head exists (the same arena serves `[:set T]`,
  `:vector-i64` and, since 2026-09-25, `:bytes`).
- The items are 64-bit words. The loader never inspects an item: `vector_conj` copies a vector and appends a
  word, `vector_at` returns the word.
- A record, a variant, an option/result and a heterogeneous vector are each **one word** (aggregate ABI v7/v8:
  a pair-chain / `pair(ordinal,payload)` handle in the context pair arena). `[:ref q]` is that word, named.

So a list whose items are aggregate handles needs no new lowering, no new context slot and no new loader code:
the items are words already. What held it back was four *admission predicates* that spelled the word universe
out as scalars plus an inline record and never listed "a handle":

| layer | repo / file | what refused |
|---|---|---|
| admission walk | osaho `kotoba.kir/native-handle-type?`, the `typed-list-*` arms of `only-native-word-typed-features?` | `native-word-value-type?` admits `[:list T]` only for word-like `T` or a scalar record; `:ref` is neither, and `native-handle-type?` had no `:list` arm |
| verifier | kotoba-verifier `native-scalar-record-type?`, `native-handle-type?`, the three `typed-list-*` arms | the same, re-derived independently (that independence is deliberate, so it is widened independently) |
| lowering gate | kotoba-native `aggregate-abi/scalar-record-type?` (both the `:default` and the `:kotoba` twin) | already admitted `:list` and `:ref` as record fields; did not list `:vector-i64` / `:bytes` |
| codegen | kotoba-native `machine-ir`, aarch64 / x86-64 | nothing to change for lists: the ISA-specific code is below `vector-conj` / `vector-at` |

## 2. The change

All widening is of the *aggregate member universe*, in the four predicates above, and nothing else:

1. **`[:list T]` where T is a handle** (osaho `native-handle-type?` gains a `:list` arm that threads the
   coinductive `seen` set, so `[:kids [:list [:ref :form/r]]]` inside `:form/r` terminates; the `typed-list-new`,
   `typed-list-conj`, `typed-list-nth` arms test `native-handle-type?` instead of `native-word-value-type?`).
   Verifier: the same arm, plus `native-scalar-record-type?` admits a `[:list handle]` field and a `[:ref q]`
   field, and a `typed-list-nth` over `[:list [:ref q]]` denotes `[:ref q]` (so `record-get` over a list item
   verifies, directly or through a `let`).
2. **`:bytes` and `:vector-i64` as a record member or list item** (gap 2, the part that blocks the Form record's
   `:data :bytes` field). They are context-owned vector-arena handles, one word, living in the call context for
   the same extent as the pair cells that point at them. They stay *non-exportable inside an aggregate*: the
   loader's boundary codec builds only top-level handles (`native-export-codec-types`), so an export still takes
   no list and no record. Variant payloads are deliberately **not** widened (kotoba-native's own tests pin
   `[:variant ... [:blob :bytes]]` refused).
3. **`record-assoc`** (found by running vx: the Form frontend updates records functionally). Lowered by
   rebuilding the record: `(record-assoc T r f v)` => a `record-new` of `record-get`s of the other fields and
   `v`. In a module whose records are pair chains (`normalize-scalar-record-boundary`) it is the same chain
   rebuild `hetero-vector-assoc` already used; in a scalar-replaced module it is a `record-new` over
   `record-get`s of a symbol operand. The verifier admits it exactly where `record-get` is admitted (the
   operand's declared schema is the schema being updated) plus a verified replacement.
4. **Verifier parity for two things native already lowered**: the `:document` operation family
   (`native-document-operation-arities`, 22 heads the verifier did not list) and binary i64 `min`/`max`.

Not changed, on purpose:

- `[:set T]` of handles: membership would compare cells, not values (`kotoba.kir` already says so for typed sets
  of handles). Refused, with a test.
- Structural equality over handles (`record-equal`, `hetero-vector-equal`).
- Exports: an exported function still takes/returns only the host-validated boundary set.

## 3. Ownership, budgets, cost

- **Ownership.** Nothing is freed: pair cells, vector entries and vector items are arena-allocated and live
  until the run ends (ABI v11). A list of handles therefore cannot dangle.
- **Cost.** `typed-list-conj` copies (`vector-conj` is persistent), so building a list of n items is O(n^2)
  item words and n vector-table entries. The loader's default budgets (4096 table entries, 65536 item words)
  are too small for a real Form walk; `KEXE_VECTORS` / `KEXE_VECTOR_ITEMS` raise them (maxima 4M entries and
  128M words, address space, not memory). `guest-run.sh` now sets 4M / 128M (`GUEST_VECTORS`,
  `GUEST_VECTOR_ITEMS`). The product consequence is real: a self-built compiler wants an amortised-append list
  (a builder with a capacity), which is a separate, ABI-visible step -- recorded as follow-up, not done here.
- **Aliasing.** `vector-conj` never mutates its operand, so an item list shared between two records is safe.

## 4. Evidence

- osaho `test/kotoba/kir_native_aggregate_list_test.cljk` (admission, both directions);
  kotoba-verifier `test/kotoba/verifier_aggregate_list_test.cljk` (the same, re-derived, refusal literals
  pinned); kotoba-native `machine_ir_test.cljk` (the Form-shaped record lowers for x86-64 and aarch64; `record-assoc`
  in both record modes; an undeclared field is refused by name).
- A probe module (recursive record with `[:list [:ref]]`, `:bytes`, `:string`, `record-assoc`, a call, a
  `let`-bound update, a list item projected through `record-get`) compiled for aarch64-macos and **executed by the
  kexe loader**: it answers the value the reference computes (`8021` for input `5`).
- `scripts/selfhost-wall/native-gaps.sh` over `vx.cljk`: the 193 + 33 + 21 + ... refused functions (every one
  through `:form/r` / `:vx/env`) are gone; the module compiles (`guest-run.sh --native-only --resolve` prints
  `native`). See `docs/selfhost-native-gaps-20261001.md` for the table after the change.

## 5. Still open (not hidden by this change)

- `[:option :bytes]`, `[:option :vector-i64]`, `[:result :bytes :document]` as handles (cc/vc/oa/oat guests).
- `record-get` over a `:bytes` field *value used as a feature* in a few shapes (`record-get` feature of cc).
- `typed-cap-call` with a non-generic type pair (vc).
- An amortised list builder (section 3).
- wasm: kotoba-wasm still lacks `typed-list-conj`; this change is native-only.
