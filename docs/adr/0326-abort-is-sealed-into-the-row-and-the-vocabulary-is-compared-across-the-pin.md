# ADR-0326: `:abort` is sealed into the row, and the vocabulary is compared across the pin

- Status: accepted
- Date: 2026-09-03
- Amends: ADR-0300 section 4 ("`:abort` has no keyword the bridge can seal"),
  in place.
- Decided by: kotoba-lang
  `docs/adr/ADR-abort-reaches-the-sealed-effect-row.md`, from
  `lang/surface-status.edn` `:invariants :explicit-errors`.
- Pin advanced: `io.github.kotoba-lang/kotoba-kir`
  `08bdab8b` → `ad6db332` (26 commits).

## What was stuck

On 2026-09-02 two commits decided one question in opposite directions, hours
apart, in two repositories:

| | says |
|---|---|
| kotoba-kir `984a507` | a member of the closed set `control-effects` — today `#{:abort}` — bridges into the sealed row unchanged |
| this repository, ADR-0300 §4 + `definition_identity_test` | `:abort` names no authority, the bridge refuses, the definition gets `:unbridged-effect` |

The consequence was mechanical: this repository's kotoba-kir pin was held at
`08bdab8b`, the commit *before* `984a507`, with the reason written into
`deps.edn` and into `aggregate_abi_test`. Advancing it turned 8 assertions
red. Everything kotoba-kir landed afterwards — the `[:slice T]` boundary
refusal, the alpha-normalization move, a ClojureScript-safe i64 ordering, two
ADR renumberings — was stranded behind an unmade decision. The SLICE-VALUE
stream measured this, declined to adjudicate, and was right to: it is a
language-authority question.

## The ruling, and what it rests on

**`:abort` reaches the sealed row.** kotoba-kir's reading is correct. The
argument is not a preference between two reasonable implementations; it comes
out of `lang/surface-status.edn`:

1. `:explicit-errors` is an `:intentional-security-constraint` whose
   `:widening-path` is `:typed-abort-ability`, and that path lists three named
   **preconditions**. One of them is `:effect-row-integration`. A row member
   that cannot reach a definition identity is not integrated into the row — it
   is refused at the row's boundary. Under the refusal reading, no aborting
   definition can ever be pinned by a package lock or served from a
   definition-keyed cache, which closes the path the precondition exists to
   open. A precondition satisfiable only by removing the feature is not a
   precondition.
2. The `:shielding-axis` is `:control-effect-tracking`. The invariant is that
   no control effect is *untracked*. The definition identity is the last
   boundary the effect crosses; an identity that cannot carry `:abort` is
   exactly where tracking stops.

## What ADR-0300 §4 got right, and what it got wrong

Its two arguments both survive, and neither of them required the refusal:

- **"A CID is never invented for a hole."** Passing `:abort` through invents
  nothing. There is no catalog lookup to get wrong because there is no wire id
  to look up: the keyword *is* the sealed vocabulary. §4 measured that the
  bridge had no *translation* for `:abort` and inferred that there was nothing
  to seal. The inference is the part that was wrong.
- **"A partial identity is not an identity."** Unchanged, and still load
  bearing. `:unbridged-effect`, `:dependency-unavailable`, the `SCANNED n/m`
  floor and the `REFUSED:` listing all remain, for every member that is
  neither `[:cap/call <id>]` nor in `control-effects`. The refusal machinery
  §4 built is not deleted; it is given a correct domain.

The dangerous third option is the one nobody took: **stripping** `:abort`
before bridging. An aborting definition has interface `[:result T E]` where a
pure one has `T`, so stripping gives two different programs one identity and a
lock pinning the pure one admits the aborting one. Both landed commits avoided
it. Sealing is the one that also satisfies the precondition.

**The general shape to watch for**: §4 was a true measurement of a *dependency*
written up as a decision about the *language*. A test that pins what the
pinned version of another repository happens to do will hold that version's
behaviour still, and will hold the pin still with it.

## The assertions, both directions

`an-unbridgeable-effect-row-is-refused-with-a-marker` is replaced by four
tests that keep every direction the old one had:

| claim | how it is discriminating |
|---|---|
| an aborting definition **has** a CID | and its caller does too, so the closure has no hole |
| an aborting and a pure definition have **different** CIDs | kotoba-kir's own suite pins this; here the row that reaches the payload is asserted to hold `:abort`, so the fixture cannot silently stop aborting |
| a keyword **outside** `control-effects` is still refused | reason literal pinned: `not a wire capability call` |
| an unknown **wire id** is a different refusal | reason literal pinned: `has no catalog name` |
| a module with a refused definition still yields no cache material | now built from synthetic KIR, because after the adjudication no compilable source produces an unbridgeable row |
| `SCANNED 0/2` still distinguishes nothing-identified | and `SCANNED 2/2` is now what the aborting fixture reports |

## The check that stops this recurring

`the-sealed-control-effect-vocabulary-agrees-across-the-pin` compares this
repository's own expectation, `#{:abort}`, against
`kotoba.kir.definition-identity/control-effects` **through the `deps.edn`
pin**. It is HYGIENE-1's shape (kotoba-native ADR-0050, kotoba-verifier
ADR-0024): the producer exports the set it branches on, the consumer derives
its own and asserts equality. Neither repository imports the other's answer,
so the comparison is real; and the next divergence is caught by the pin
advance that carries it, rather than by a test stranded behind a pin nobody
dares advance.

It is placed here rather than in kotoba-verifier — the repository HYGIENE-1
used — because kotoba-verifier has no part in definition identity at all. The
consumer that diverged is the one that must compare.

It prints `COMPARED <n>` and refuses an empty set: an empty `control-effects`
would make every control effect unbridgeable again, and a comparison against
nothing is not a comparison.

## Verification

```
java -cp "$(clojure -A:test -Spath)" clojure.main -e \
  "(clojure.test/run-tests 'kotoba.compiler.definition-identity-test)"
  COMPARED 1  sealed control effects against kotoba-kir
```

Red, with `control-effects` no longer agreeing: see the run recorded in the
PR. The break used is the one that matters — a disagreement between the two
repositories, not a broken test.

## What this ADR does not decide

- Whether `control-effects` should ever hold a second member. Nothing today
  proposes one, and adding one is a contract change in kotoba-lang first.
- `:checked-lexical-facet-unwind` is still `:not-met`. Every refusal citing it
  — throw inside `loop`/`doseq`/`dotimes`, in lazy thunks and `fn` literals,
  and in any function whose row carries a `:dataspace/*` operation — stands.
  This decides where a tracked abort may be **recorded**, not where an abort
  may **occur**.
