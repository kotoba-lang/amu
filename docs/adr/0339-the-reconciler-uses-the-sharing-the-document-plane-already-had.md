# ADR 0339 — The DOM reconciler skips a slot whose content it already holds

- Date: 2026-09-06 (revised the same day; see "What this document said first")
- Status: Accepted

## Context

`reconcileUiDocument` walked every node of the UI `:document` on every paint.
Nothing was wrong with the walk. What was wrong is that the information needed
to skip most of it was already in the value being walked, and was dropped at
the boundary.

## What this document said first, and why it was wrong

The first version of this ADR proposed comparing document nodes by **identity**,
on the measured grounds that `document-assoc` copies only the entry pairs of the
map it touches and leaves every untouched child at the same reference:

```js
const output = entries.map(entry => [entry[0], entry[1]]);   // entry[1] is not rebuilt
```

That is true of the **state** and false of the **paint**. `dom-driver` gives
every interaction a fresh guest instance, and its own docstring says why: a
restricted-ESM instance is metered, and a shared one dies of `fuel-exhausted`
on the eighth interaction of the todo example. `dom_app_driver_test` pins the
consequence at 200 instantiations under load. Two paints therefore never share
an object, and an identity memo could not fire **once** through the shipped
driver. It was correct, tested, and unreachable.

That is worth writing down rather than quietly replacing, because the mistake
was not in the mechanism. It was in never asking whether the input it needed
could occur.

## Decision

Key each slot by **content**, not by reference.

`describeUiNode` reads the four things the reconciler renders from — tag,
attributes, text, children — and builds a key from exactly those, composed
bottom-up from the children's keys. `walk` returns without touching the DOM
when the incoming node's key equals the one that slot was last rendered from
and the remembered element is still the child at that index. Descriptions are
memoised per reconcile, so each node is described once however deep it sits.

Content survives what identity cannot: a document built by a second instance
keys the same as the one the first instance built, which is the case that
actually occurs.

**The bound is what makes it affordable.** Keying a tree means walking it, which
is the cost the memo exists to avoid — except that a `:document` holds at most
256 nodes. The work is bounded by admission rather than by hope, and what is
skipped is DOM work, which is the expensive half.

Two smaller consequences fall out. The key is **length-prefixed**, so no tag,
attribute or text can spell another node's key. And because keying reads the
tag and the attributes for the whole tree before anything is rendered, a denied
tag, a denied attribute name or a denied URL scheme now rejects the whole
reconcile before any element is touched — the guarantee the old comment claimed
per node, now total over the tree.

## Consequences

Stated rather than left to be discovered: before any memo, every paint
re-applied every attribute and every text, so anything edited underneath the
reconciler was repaired by accident on the next paint. **Now a skipped subtree
is not descended at all, so nothing inside it is repaired** — not an attribute,
not a text, not a replaced child. The slot check only guards the level the paint
actually reaches. This is a stronger cost than the identity version had, because
content keys skip strictly more.

It is sound for the caller this exists for: `dom-driver` owns its mount,
attaches listeners to the container rather than to guest-named nodes, and the
guest cannot name a DOM object at all. A caller that shares a container with
other code is outside what `reconcileUiDocument` assumes, and there is a test
that pins that limit rather than leaving it to be found.

Nothing about the guest changes. No capability is added, no host object crosses
the boundary, and a conforming app still compiles with `requiredCapabilities: []`.

## Evidence

`scripts/test-reconcile-sharing.mjs` (`npm run test-reconcile-sharing`), seven
cases, JVM-free under `node --test`. **Every document in it is built
independently**, the way a second instance would build it — the case the first
design could not serve. DOM writes are recorded, so "did no work" is measured
rather than inferred from a timing.

1. an unchanged subtree costs no DOM work, even rebuilt from scratch — only
   `text:two` reaches the DOM when only the heading changed
2. an identical document costs nothing at all
3. a changed attribute is not mistaken for an unchanged node
4. the key cannot be spelled by another node's content
5. a changed subtree is still walked and still updates
6. what the memo gives up: this reconciler must be the only writer
7. a denied attribute rejects before any element is touched

Break-tested, each break checked against what it turned red:

- skipping without comparing the key fails 5 of the 7
- dropping the length prefix fails case 4 and nothing else — `tag "p" text "ab"`
  and `tag "pa" text "b"` concatenate to the same characters, so the second
  would be read as the first and the DOM would keep `<p>ab</p>`

⚠ Case 4 did not discriminate on its first writing: an earlier version of it
stayed green with the prefixes removed, which made it a test of nothing. It was
rewritten around an actual collision pair and then failed as intended.
