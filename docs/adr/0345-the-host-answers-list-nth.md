# ADR 0345: the browser host answers `list-nth`, and the corpus asks all three runtimes

- Status: accepted
- Date: 2026-09-08

## Context

`kotoba-lang/kotoba-lang`'s `lang/compat.edn` recorded, as the reason three
`clojure.string` names were absent:

> `[:list :string]` admits construction (typed-list-new) and vector-count only
> … A list of strings can be built and counted and nothing can be read back out
> of it.

Re-measured against today's compiler (this repository at `9092ee34`, 2026-09-08)
the sentence was half wrong when it was written, and the half that was right was
in a different place than it said.

`vector-at` / `vector-conj` do still refuse a `[:list :string]` -- they are the
bounded-vector operations and a list is a different carrier, so they always
will. The accessor is `typed-list-nth`, and kotoba-sema has carried it since
2026-09-03: `amu check` returned **exit 0** on it. What was missing was the
**lowering**, on both backends:

```
$ amu check   r4.kotoba                                 exit 0
$ amu compile r4.kotoba --target web    --output x.mjs  exit 70  "unsupported KIR node"
$ amu compile r4.kotoba --target wasm32 --output x.wasm exit 70  "typed Wasm operation is not qualified"
```

and for the whole module, reached or not (a two-function reproduction whose
`main` returns 7 and never calls the indexing function is refused on both
targets). So the recorded consequence was true and its stated cause was not:
the gap was a backend gap, not a language one.

## Decision

Two changes here, on top of `kotoba-script` PR (typedListNth) and `kotoba-wasm`
PR (the `list-nth-i64` / `list-nth-ref` intrinsics).

**1. `runtime/browser-host.mjs` answers the two new imports.** `listNth` is
`setNth`'s shape against a `list` descriptor: it checks the descriptor kind,
asserts the carrier, **traps** out of range (`list index out of bounds`) rather
than answering `undefined`, and asserts the item against the item type before
returning it. The two names are added to `ALLOWED_IMPORTS`; kotoba-wasm emits
them conditionally, so a module that does not index a list carries neither and
every module that instantiated before still does.

**2. `resources/kotoba/compiler/typed-value-conformance.edn` gains four cases.**
That corpus is the only place that runs the same source on the KIR reference
interpreter, the web backend and wasm32-through-the-browser-host and requires
all three to agree, which is exactly the shape of a defect that lives in one
backend.

- `:typed-list-nth-i64` and `:typed-list-nth-reference` are both there because
  they are *different lowerings* on wasm32 -- an i64 item calls `list-nth-i64`
  and a reference item calls `list-nth-ref` -- and a corpus covering one would
  pass with the two arms swapped.
- `:list-index-past-the-end` and `:list-index-negative` are `:phase :runtime`
  negatives. Both ends, because a bounds check written as `index >= length`
  alone admits every negative index and still passes a test that only tried the
  high end.

## Evidence

The corpus runner asserts three-way agreement for the positives and three-way
refusal for the negatives, so a green run is a claim about all three runtimes.

End to end through the ordinary project route, with the artifacts RUN rather
than only built:

```
amu compile app.kotoba --source-path <app> --source-path <kotoba-lang>/lang/compat \
  --target wasm32 --output app.wasm     # exit 0
node -> runtime/browser-host.mjs        # main() = "a,bb,ccc", sw() = 1n
amu compile ... --target web --output app.mjs   # exit 0
node -> instantiateKotoba               # main() = "a,bb,ccc", sw() = 1n
```

Broken on purpose, each restored after:

| broken | observed |
|---|---|
| `list-nth-ref` removed from `ALLOWED_IMPORTS` | compile still 0; instantiation `forbidden-import: Wasm import is outside the Kotoba browser profile: kotoba:typed/list-nth-ref/function` |
| the `list-nth-ref` host binding removed, allowlist kept | `instantiation-failed`, `LinkError: Import #52 "kotoba:typed" "list-nth-ref": function import requires a callable` |
| kotoba-wasm's emit arm removed | `--target wasm32` exit 70 `typed Wasm operation is not qualified`; `--target web` still 0 |
| kotoba-script's emit arm removed | `--target web` exit 70 `unsupported KIR operation`; `--target wasm32` still 0 |

## The pin advance brought a second, unrelated gap with it

Advancing `kotoba-wasm` to a main that contains this change also crosses
`2d912bf` (#74), which lowers `document-vector-sort` and emits its import inside
the same `has-document?` block as the rest of the document surface -- so *every*
document-using module now carries it, sorted or not. This host was pinned behind
that commit and did not know the name.

Measured 2026-09-08. `amu`'s full suite at `origin/main` (9092ee34) is **1335
tests, 9603 assertions, 0 failures, 0 errors**. With the two pins advanced and
nothing else, eleven of them fail at INSTANTIATION:

```
KotobaHostError: Wasm import is outside the Kotoba browser profile:
  kotoba:typed/document-vector-sort/function          code: 'forbidden-import'
```

across `document_value`, `document_sha256`, `document_roundtrip`,
`document_edn` and `dataspace_wasm_aot`. So the host learns
`document-vector-sort`, sorting by `compareDocument` -- the same total order the
KIR reference interpreter uses (`value/document-compare`) and the same one this
host already applies when it checks that a document set is sorted and
duplicate-free, so the three runtimes agree on the ORDER and not only on the
multiset. `kotoba-script` has had `docVectorSort` since the same day.

That is the whole of the discrimination evidence for this line: green → advance
the pin → eleven red, each naming that import → add the line → green.

## The out-of-range cases did not fit the corpus, and that is a finding

A CONSTANT out-of-range index never reaches `ir/execute`: `kir/lower` evaluates
the entry to fold it, so the trap arrives from `compile-source`. The corpus's
`:phase :runtime` shape is "compile succeeds, execute throws", so putting the
case there produced

```
ERROR in (shared-negative-corpus-fails-closed) (kir.cljc:1173)
clojure.lang.ExceptionInfo: list-index-out-of-bounds
{:phase :ir, :trap :list-index-out-of-bounds, :index 3, :count 3}
```

which is the right behaviour and the wrong test. `:set-duplicate` and
`:map-duplicate-key` DO fit that shape; the difference is that constant folding
reaches an index bound and does not reach those. The two are asserted in the
test file instead, in two halves:
`a-constant-out-of-range-list-index-is-refused-while-folding` (both routes,
three indices, plus an in-range index that folds to `6` so the refusal is
demonstrably about the range) and
`a-runtime-list-index-reads-in-range-and-traps-out-of-range-on-both-backends`,
which reads the index through an argument the folder cannot see and probes an
exported `at` on web and on wasm32.

## Consequences

- The `kotoba-script` and `kotoba-wasm` pins advance, and `deps-lock.edn` with
  them.
- `kotoba-lang`'s `clojure.string` compat module gains `join`. Its floor moves
  to an amu carrying these pins; an older one refuses that module whole, at
  compile time, with a named message.
- `split` and `split-lines` stay absent, for a reason that is now precise and is
  *not* the one on record: a `[:list T]` can only be constructed with a
  statically known item count (`canonical-list-operations` is exactly
  `#{typed-list-new typed-list-nth}` -- no conj, cons or append; measured), and
  separately `clojure.string/split` takes a `java.util.regex.Pattern`, not a
  string, so a string-separator split is a different function and does not get
  the Clojure name.
