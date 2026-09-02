# ADR-0326: `:abort` is sealed into the row, and the vocabulary is compared across the pin

- Status: accepted
- Date: 2026-09-03
- Amends: ADR-0300 section 4 ("`:abort` has no keyword the bridge can seal"),
  in place.
- Authority: kotoba-lang
  `docs/adr/ADR-abort-reaches-the-sealed-effect-row.md`, from
  `lang/surface-status.edn` `:invariants :explicit-errors`.
- Relates: the pin advance itself landed first, in
  `c3e48d0e` — see *"Decided twice"* below.

## What was stuck

On 2026-09-02 two commits decided one question in opposite directions, hours
apart, in two repositories:

| | says |
|---|---|
| kotoba-kir `984a507` | a member of the closed set `control-effects` — today `#{:abort}` — bridges into the sealed row unchanged |
| this repository, ADR-0300 §4 + `definition_identity_test` | `:abort` names no authority, the bridge refuses, the definition gets `:unbridged-effect` |

The consequence was mechanical: the kotoba-kir pin was held at `08bdab8b`,
one commit before `984a507`, with the reason written into `deps.edn` and
`aggregate_abi_test`. Advancing turned 8 assertions red, and everything
kotoba-kir landed afterwards was stranded behind an unmade decision.

## Decided twice, in the same direction, by two streams

This is worth recording because it is the most useful thing measured here.

`c3e48d0e` ("Adjudicate the held kotoba-kir pin, and regenerate the lock",
session `016z2K1Y` — the same session that wrote kotoba-kir `984a507`)
advanced the pin and rewrote the eight assertions on 2026-09-03, hours before
this ADR. It reached **the same ruling** by an overlapping but different
route: `lang/code-identity.edn` names `:kotoba.kir/definition-identity` the
`:authority` for what a sealed row contains, so ADR-0300 described that
authority's behaviour rather than owning it.

That reasoning is correct and this ADR does not replace it. What it did not
do, and what this change adds, is the other two thirds of an adjudication:

1. **The ruling is not in the language authority.** A decision recorded only
   in one consumer's `deps.edn` and test file is a decision the next reader of
   `surface-status.edn` cannot find. It is now
   `:effect-row-integration :adjudication` in kotoba-lang, with a slug ADR.
2. **Nothing stopped it recurring.** Both repositories now assert what is
   true today, independently, and the failure mode was never that either was
   wrong — it was that neither could see the other. See below.

Two streams adjudicating the same stall the same way within hours is a
reasonable outcome. Two streams *not knowing they were both doing it* is the
same class of defect as the original disagreement.

## The ruling, and what it rests on

**`:abort` reaches the sealed row.** From `lang/surface-status.edn`:

1. `:explicit-errors` is an `:intentional-security-constraint` whose
   `:widening-path` is `:typed-abort-ability`, and that path lists three named
   **preconditions**. One is `:effect-row-integration`. A row member that
   cannot reach a definition identity is not integrated into the row — it is
   refused at the row's boundary. Under the refusal reading, no aborting
   definition can ever be pinned by a package lock or served from a
   definition-keyed cache, which closes the path the precondition exists to
   open. A precondition satisfiable only by removing the feature is not a
   precondition.
2. The `:shielding-axis` is `:control-effect-tracking`. The invariant is that
   no control effect is *untracked*; the definition identity is the last
   boundary the effect crosses.

## What ADR-0300 §4 got right, and what it got wrong

Both its arguments survive, and neither required the refusal:

- **"A CID is never invented for a hole."** Passing `:abort` through invents
  nothing — there is no catalog lookup to get wrong because there is no wire
  id: the keyword *is* the sealed vocabulary. §4 measured that the bridge had
  no *translation* for `:abort` and inferred there was nothing to seal. The
  inference is the part that was wrong.
- **"A partial identity is not an identity."** Unchanged and still load
  bearing, now reached by a wire id no catalog names — the only remaining
  unbridgeable row, which is why `unbridgeable-module` is synthetic.

The dangerous third option is the one nobody took: **stripping** `:abort`
before bridging, which gives an aborting and a pure definition one identity
while their interfaces differ (`[:result T E]` against `T`).

**The general shape to watch for**: §4 was a true measurement of a
*dependency* written up as a decision about the *language*. A test that pins
what the pinned version of another repository happens to do will hold that
version's behaviour still, and will hold the pin still with it.

## The check that stops this recurring

`the-sealed-control-effect-vocabulary-agrees-across-the-pin` compares this
repository's own expectation, `#{:abort}`, against
`kotoba.kir.definition-identity/control-effects` **through the `deps.edn`
pin**. HYGIENE-1's shape (kotoba-native ADR-0050, kotoba-verifier ADR-0024):
the producer exports the set it branches on, the consumer derives its own and
asserts equality. Neither imports the other's answer — importing would make
them agree by construction and prove nothing — so the next divergence is
caught by the pin advance that carries it.

It is placed here rather than in kotoba-verifier, the repository HYGIENE-1
used, because kotoba-verifier has no part in definition identity at all. The
consumer that diverged is the one that must compare.

`the-two-unbridgeable-reasons-are-different-reasons` pins the other half: the
keyword-outside-the-set refusal (`not a wire capability call`) and the
unknown-wire-id refusal (`has no catalog name`) are pinned by their exact
text, so a change collapsing them into one message is caught. A marker that
cannot say *which* problem it found is halfway back to no marker.

## Verification

```
COMPARED  1  sealed control effects against kotoba-kir
```

Shown red by changing this repository's expectation to `#{:abort :cancel}`:

```
this repository and kotoba-kir disagree about which effect-row members bridge
as themselves.
  only here: #{:cancel}
  only in kotoba-kir: #{}
Adjudicate it (kotoba-lang lang/surface-status.edn :explicit-errors
:widening-path) before advancing the pin.
```

And the pin really was the blocker rather than a wording difference:
`grep -c control-effects src/kotoba/kir/definition_identity.cljc` is **0** at
`08bdab8b` and **7** at `ad6db332`.

## What this ADR does not decide

- Whether `control-effects` should ever hold a second member. Growing it is a
  contract change in kotoba-lang first. Nothing today proposes one.
- `:checked-lexical-facet-unwind` is still `:not-met`. Every refusal citing it
  — throw inside `loop`/`doseq`/`dotimes`, in lazy thunks and `fn` literals,
  and in any function whose row carries a `:dataspace/*` operation — stands.
  This decides where a tracked abort may be **recorded**, not where an abort
  may **occur**.
