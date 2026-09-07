/**
 * The reconciler does no DOM work for a slot whose content it already holds.
 *
 * The first version of this memo compared document nodes by identity. That
 * could not fire through `dom-driver`: every interaction gets a fresh guest
 * instance (the fuel model -- a shared instance dies of `fuel-exhausted` on
 * the eighth interaction, and `dom_app_driver_test` pins 200 instantiations),
 * so two paints never share an object. These cases are written the way the
 * driver actually behaves: **every document here is built independently**, as
 * a second instance would build it.
 *
 *   node --test scripts/test-reconcile-sharing.mjs
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { reconcileUiDocument, createMockDom } from "../runtime/browser-host.mjs";

const str = value => ["string", value];
const leaf = (tag, text) => ["map", [[":tag", str(tag)], [":text", str(text)]]];
const branch = (tag, kids) => ["map", [[":children", ["vector", kids]], [":tag", str(tag)]]];
const withAttrs = (node, pairs) =>
  ["map", [...node[1], [":attrs", ["map", pairs.map(([n, v]) => [`:${n}`, str(v)])]]]];

/** A DOM whose every write is recorded, so "did no work" is measured. */
const recordingDom = () => {
  const dom = createMockDom();
  const writes = [];
  return {
    writes,
    createContainer: dom.createContainer,
    createTextNode: dom.createTextNode,
    createElement: tag => {
      const el = dom.createElement(tag);
      writes.push(`create:${tag}`);
      const setAttribute = el.setAttribute.bind(el);
      el.setAttribute = (name, value) => { writes.push(`attr:${name}`); setAttribute(name, value); };
      let text = el.textContent;
      Object.defineProperty(el, "textContent", {
        get: () => text,
        set: value => { writes.push(`text:${value}`); text = value; el.childNodes.length = 0; },
        configurable: true
      });
      return el;
    }
  };
};

const textOf = element =>
  element.childNodes?.length ? element.childNodes.map(textOf).join("") : (element.textContent ?? "");

test("an unchanged subtree costs no DOM work, even rebuilt from scratch", () => {
  const dom = recordingDom();
  const container = dom.createContainer();
  const page = label => branch("div", [leaf("h1", label), leaf("p", "unchanged")]);

  reconcileUiDocument(container, page("one"), dom);
  assert.ok(dom.writes.length > 0, "the first reconcile must actually build the page");

  dom.writes.length = 0;
  // A separately built document, as a second guest instance would produce.
  reconcileUiDocument(container, page("two"), dom);

  assert.deepEqual(dom.writes, ["text:two"],
    "only the part that changed may reach the DOM");
  assert.match(textOf(container), /two/);
  assert.match(textOf(container), /unchanged/);
});

test("an identical document costs nothing at all", () => {
  const dom = recordingDom();
  const container = dom.createContainer();
  const page = () => branch("div", [leaf("h1", "same"), leaf("p", "same")]);
  reconcileUiDocument(container, page(), dom);
  dom.writes.length = 0;
  reconcileUiDocument(container, page(), dom);
  assert.deepEqual(dom.writes, [], "a repaint of the same page must touch no element");
});

test("a changed attribute is not mistaken for an unchanged node", () => {
  const dom = recordingDom();
  const container = dom.createContainer();
  const page = cls => branch("div", [withAttrs(leaf("p", "x"), [["class", cls]])]);
  reconcileUiDocument(container, page("a"), dom);
  dom.writes.length = 0;
  reconcileUiDocument(container, page("b"), dom);
  assert.ok(dom.writes.includes("attr:class"), "the attribute must be re-applied when it differs");
});

test("the key cannot be spelled by another node's content", () => {
  const dom = recordingDom();
  const container = dom.createContainer();
  // Without length prefixes both of these key as "l" + "p" + "" + "ab":
  //   tag "p"  text "ab"
  //   tag "pa" text "b"
  // The second would then be read as the one already rendered and the DOM
  // would keep <p>ab</p>. The prefixes are what make the key injective.
  reconcileUiDocument(container, branch("div", [leaf("p", "ab")]), dom);
  assert.equal(container.childNodes[0].childNodes[0].tagName, "P");

  reconcileUiDocument(container, branch("div", [leaf("pa", "b")]), dom);
  assert.equal(container.childNodes[0].childNodes[0].tagName, "PA",
    "a node whose fields concatenate to the same characters is a different node");
  assert.equal(textOf(container), "b");
});

test("a changed subtree is still walked and still updates", () => {
  const dom = recordingDom();
  const container = dom.createContainer();
  reconcileUiDocument(container, branch("div", [leaf("p", "before")]), dom);
  reconcileUiDocument(container, branch("div", [leaf("p", "after")]), dom);
  assert.match(textOf(container), /after/);
  assert.doesNotMatch(textOf(container), /before/);
});

test("what the memo gives up: this reconciler must be the only writer", () => {
  // Stated rather than discovered. Keying by content skips a whole subtree
  // whose content is unchanged, which is the point -- and it means an edit
  // made underneath the reconciler is NOT repaired on the next paint, because
  // the paint never descends that far. Before any memo, every paint re-applied
  // every attribute and every text and so repaired it by accident.
  //
  // This is sound for the shipped caller: `dom-driver` owns its mount, attaches
  // listeners to the container rather than to guest-named nodes, and the guest
  // cannot name a DOM object at all. A caller that shares a container with
  // other code is outside what `reconcileUiDocument` assumes, and this case is
  // here so that limit is written down and fails loudly if it ever moves.
  const dom = recordingDom();
  const container = dom.createContainer();
  const page = () => branch("div", [leaf("p", "mine")]);
  reconcileUiDocument(container, page(), dom);

  const root = container.childNodes[0];
  root.replaceChild(dom.createElement("p"), root.childNodes[0]);
  assert.doesNotMatch(textOf(container), /mine/, "precondition: the DOM really was clobbered");

  dom.writes.length = 0;
  reconcileUiDocument(container, page(), dom);
  assert.deepEqual(dom.writes, [],
    "an unchanged page does no work, so foreign edits under it are not repaired");
  assert.doesNotMatch(textOf(container), /mine/, "and this is what that costs");

  // The slot check still holds where the paint does reach: change the page and
  // the reconciler descends and takes the slot back.
  reconcileUiDocument(container, branch("div", [leaf("p", "ours")]), dom);
  assert.match(textOf(container), /ours/, "a paint that descends repairs what it finds");
});

test("a denied attribute rejects before any element is touched", () => {
  const dom = recordingDom();
  const container = dom.createContainer();
  const bad = branch("div", [leaf("h1", "ok"), withAttrs(leaf("a", "x"), [["href", "javascript:1"]])]);
  assert.throws(() => reconcileUiDocument(container, bad, dom));
  assert.deepEqual(dom.writes, [],
    "keying the tree first makes the whole reconcile reject before it half-applies");
});
