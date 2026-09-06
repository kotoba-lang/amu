# ADR 0339 — The DOM reconciler uses the sharing the document plane already had

- Date: 2026-09-06
- Status: Accepted

## Context

`reconcileUiDocument` walked every node of the UI `:document` on every paint.
Nothing was wrong with the walk; what was wrong is that the information needed
to skip most of it was already sitting in the value being walked and was thrown
away at the boundary.

`document-assoc` copies the entry pairs of the map it touches and leaves every
untouched child at **the same reference**:

```js
const output = entries.map(entry => [entry[0], entry[1]]);
if (index < 0) output.push([checkedKey, item]); else output[index] = [checkedKey, item];
```

`entry[1]` is not rebuilt. So after a leaf update the new document shares every
subtree it did not change, and identity between two paints is a content test
that costs a lookup and encodes nothing. `document-sha256` and
`document-canonical-bytes` say the same thing more expensively; for the paint
path the reference is enough and O(changed) rather than O(document).

W4 slice 6 already pinned that both renderers agree after a persistent
`document-assoc` leaf update and that the digests differ. That is the same
fact. It had simply never reached the reconciler.

## Decision

`reconcileUiDocument` remembers, per parent element and index, the document
node it last rendered there, in a module-level `WeakMap`. A slot whose incoming
node is that same object, and whose remembered element is still the child at
that index, is returned without being walked.

Identity, not structural equality. The test is **sound but not complete**: two
structurally equal documents built independently are different objects and are
walked in full. That is the safe direction — skipping too little repaints
something that did not change, skipping too much would serve a stale page. It
also means the win belongs to a guest that passes a subtree through rather than
rebuilding it, which is what `document-assoc` produces and what `view` should
therefore prefer.

## Consequences

What this weakens, stated rather than discovered later: before the memo, every
paint re-applied every attribute and every text, so a subtree that something
outside the reconciler had edited was repaired on the next paint. A skipped
subtree is not. The slot check catches a **replaced** element; it does not catch
an attribute written behind the reconciler's back. That is sound here because
this function owns the container — `dom-driver` attaches its listeners to the
mount and never to guest-named nodes, and the guest cannot name a DOM object at
all — but a caller that shares a container with other code is outside what this
assumes, and the comment on `walk` now says so.

Nothing about the guest changes. No capability is added, no host object crosses
the boundary, and a conforming app still compiles with `requiredCapabilities: []`.

## Evidence

`scripts/test-reconcile-sharing.mjs` (`npm run test-reconcile-sharing`), four
cases, JVM-free under `node --test`. An unchanged subtree is wrapped in a
counting `Proxy`, so "was not walked" is measured as zero property reads rather
than inferred from a timing.

1. an unchanged subtree is not read on the next reconcile — and its changed
   sibling still updates, and the skipped subtree is still on the page
2. a changed subtree is still walked and still updates
3. an equal document built independently is walked, not skipped (identity is
   sound, not complete)
4. the memo is not trusted when the DOM moved underneath it — an externally
   replaced child is repaired

Break-tested in both directions, each turning exactly one case red and no other:
disabling the skip fails case 1; dropping the element-identity half of the
condition and trusting the value alone fails case 4.
