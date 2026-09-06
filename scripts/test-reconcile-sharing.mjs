/**
 * The reconciler skips a subtree it has already rendered from the same value.
 *
 * `document-assoc` leaves every untouched child at the same reference, so the
 * document plane already carries the information "this part did not change".
 * Before this test that information reached the DOM reconciler and was thrown
 * away: `walk` visited every node on every paint. These cases pin both halves
 * -- that an unchanged subtree is no longer read at all, and that nothing is
 * skipped which could have changed.
 *
 *   node --test scripts/test-reconcile-sharing.mjs
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { reconcileUiDocument, createMockDom } from "../runtime/browser-host.mjs";

const str = value => ["string", value];
const leaf = (tag, text) => ["map", [[":tag", str(tag)], [":text", str(text)]]];
const branch = (tag, kids) => ["map", [[":children", ["vector", kids]], [":tag", str(tag)]]];

/** Counts every property read of a document node and of everything under it. */
const counting = (node, counter) => {
  if (!Array.isArray(node)) return node;
  const inner = node.map(part => counting(part, counter));
  return new Proxy(inner, {
    get(target, key, receiver) { counter.reads += 1; return Reflect.get(target, key, receiver); }
  });
};

const textOf = element =>
  element.childNodes?.length ? element.childNodes.map(textOf).join("") : (element.textContent ?? "");

test("an unchanged subtree is not read on the next reconcile", () => {
  const dom = createMockDom();
  const container = dom.createContainer();
  const counter = { reads: 0 };
  const kept = counting(leaf("p", "unchanged"), counter);

  reconcileUiDocument(container, branch("div", [leaf("h1", "one"), kept]), dom);
  const readsWhenFirstRendered = counter.reads;
  assert.ok(readsWhenFirstRendered > 0, "the first reconcile must actually read the subtree");

  counter.reads = 0;
  // Same child VALUE under a new parent map -- what document-assoc produces.
  reconcileUiDocument(container, branch("div", [leaf("h1", "two"), kept]), dom);

  assert.equal(counter.reads, 0,
    "a subtree the reconciler already rendered from this exact value must not be read again");
  assert.match(textOf(container), /two/, "the sibling that DID change must still be updated");
  assert.match(textOf(container), /unchanged/, "and the skipped subtree must still be on the page");
});

test("a changed subtree is still walked and still updates", () => {
  const dom = createMockDom();
  const container = dom.createContainer();
  reconcileUiDocument(container, branch("div", [leaf("p", "before")]), dom);
  reconcileUiDocument(container, branch("div", [leaf("p", "after")]), dom);
  assert.match(textOf(container), /after/);
  assert.doesNotMatch(textOf(container), /before/);
});

test("an equal document built independently is walked, not skipped", () => {
  const dom = createMockDom();
  const container = dom.createContainer();
  reconcileUiDocument(container, branch("div", [leaf("p", "same")]), dom);
  const counter = { reads: 0 };
  // Structurally equal, different objects: identity is sound, not complete.
  reconcileUiDocument(container, branch("div", [counting(leaf("p", "same"), counter)]), dom);
  assert.ok(counter.reads > 0, "a different object must be walked even when it is equal");
  assert.match(textOf(container), /same/);
});

test("the memo is not trusted when the DOM moved underneath it", () => {
  const dom = createMockDom();
  const container = dom.createContainer();
  const kept = leaf("p", "mine");
  reconcileUiDocument(container, branch("div", [kept]), dom);

  // Something else replaces the element the memo describes. A memo keyed only
  // on the value would hand back an element that is no longer in the tree.
  const root = container.childNodes[0];
  root.replaceChild(dom.createElement("p"), root.childNodes[0]);
  assert.doesNotMatch(textOf(container), /mine/, "precondition: the DOM really was clobbered");

  reconcileUiDocument(container, branch("div", [kept]), dom);
  assert.match(textOf(container), /mine/, "the reconciler must repair a slot it no longer owns");
});
