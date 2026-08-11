/**
 * Browser application driver for a Kotoba guest.
 *
 * This is the host half of `state + event -> next-state`. It closes the loop
 * that `reconcileUiDocument` left open: rendering already reached the DOM, but
 * nothing carried a user's click back to the guest, so a `.kotoba` module
 * could draw a page and never respond to it.
 *
 * ## What the guest supplies
 *
 * Three pure exports over `:document` values. None of them is an effect, so a
 * conforming app module compiles with `requiredCapabilities: []` and the host
 * grants nothing:
 *
 *   (defn init [] :document)                       ; initial state
 *   (defn view [state :document] :document)        ; state -> UI document
 *   (defn step [state :document                    ; state + event -> state
 *               target :string kind :string value :string] :document)
 *
 * ## Why this does not widen the guest's authority
 *
 * The guest never names a DOM API, never receives a host object, and never
 * registers a callback. Every listener is owned by this file and attached to
 * the mount container, not to guest-named nodes. What crosses into the guest
 * is three strings; what crosses out is a value the host chooses to render.
 * `no-interop` and t3-confinement are untouched -- an ungranted capability is
 * still absent, because there are no capabilities here at all.
 *
 * ## How an event finds its way back
 *
 * The guest labels a node with `data-k` (see browser-host's `:attrs`
 * allowlist). On an event, the driver walks from `event.target` up to the
 * container looking for the nearest `data-k`, and passes that name -- a
 * guest-chosen string -- as `target`. Nominal identity, never a node handle.
 * An event on an unlabelled subtree is dropped rather than guessed at.
 *
 * ## Why this takes a factory and not an instance
 *
 * A restricted-ESM instance is metered: `instantiateKotoba()` opens with a
 * fixed fuel budget that is spent, never replenished. One instance therefore
 * cannot serve an unbounded session -- measured on the todo example, a shared
 * instance dies of `fuel-exhausted` on the eighth interaction, mid-render.
 *
 * So each interaction gets a fresh instance and its own full budget. That is
 * the fuel model working rather than being worked around: one user action is
 * one bounded, metered computation, and a guest that runs away can spoil that
 * action without wedging the page. It is only sound because the guest is pure
 * -- state is an ordinary `:document` the host holds between interactions, and
 * carries no instance identity, so the instance that computes the next state
 * need not be the one that computed the last.
 *
 * What stays bounded per interaction is `step` plus the `view` that follows
 * it: they share one budget. Measured on the todo example, that budget is not
 * what a growing app hits first -- a `:document` may hold 256 nodes, and a
 * screen exceeds that (`doc-node-limit`) at around seven rows, long before it
 * runs short of fuel. The node budget, not fuel, is today's ceiling on how
 * much one Kotoba screen can show.
 *
 * ## Bounds
 *
 * Event kinds come from a fixed set, `value` is truncated at a byte ceiling,
 * and re-render is skipped when `step` returns the state it was given. A guest
 * that traps takes the dispatch down, not the page: state is left as it was
 * before the interaction and the error is handed to `onError`.
 */

import { reconcileUiDocument } from "./browser-host.mjs";

/** Event kinds a v1 app may observe. Deliberately small and behaviour-free. */
export const DEFAULT_EVENT_KINDS = Object.freeze(["click", "input", "change", "submit"]);

const NOMINAL_ATTRIBUTE = "data-k";
const MAX_VALUE_BYTES = 1024;
const MAX_NOMINAL_BYTES = 128;

class KotobaAppError extends Error {
  constructor(code, message, cause) {
    super(message);
    this.name = "KotobaAppError";
    this.code = code;
    if (cause !== undefined) this.cause = cause;
  }
}

const fail = (code, message, cause) => { throw new KotobaAppError(code, message, cause); };

const utf8Bytes = value => new TextEncoder().encode(value).byteLength;

/**
 * Truncate on a UTF-8 byte budget without splitting a code point. A form field
 * can hold more than the guest's string ceiling, and a split surrogate would
 * be rejected at the guest boundary as an unpaired half.
 */
function boundedString(value, maxBytes) {
  const text = typeof value === "string" ? value : "";
  if (utf8Bytes(text) <= maxBytes) return text;
  let end = text.length;
  while (end > 0) {
    const candidate = text.slice(0, end);
    const last = candidate.charCodeAt(end - 1);
    // Never end on a lone high surrogate.
    if (!(last >= 0xd800 && last <= 0xdbff) && utf8Bytes(candidate) <= maxBytes)
      return candidate;
    end -= 1;
  }
  return "";
}

/** Nearest `data-k` at or above `node`, stopping at (and including) `container`. */
function nominalTarget(node, container) {
  let cursor = node;
  while (cursor && cursor.nodeType !== undefined) {
    if (cursor.nodeType === 1 && typeof cursor.getAttribute === "function") {
      const name = cursor.getAttribute(NOMINAL_ATTRIBUTE);
      if (typeof name === "string" && name !== "") {
        if (utf8Bytes(name) > MAX_NOMINAL_BYTES) return null;
        return name;
      }
    }
    if (cursor === container) return null;
    cursor = cursor.parentNode;
  }
  return null;
}

/** The value an event carries, if the element it happened on has one. */
function eventValue(event) {
  const target = event?.target;
  if (target && typeof target.value === "string")
    return boundedString(target.value, MAX_VALUE_BYTES);
  if (target && target.checked !== undefined)
    return target.checked ? "true" : "false";
  return "";
}

/**
 * Mount a Kotoba guest as a live application in a DOM container.
 *
 * @param {object} options
 * @param {() => {init:Function, view:Function, step:Function}} options.instantiate
 *        makes a fresh instance, e.g. `() => module.instantiateKotoba(grants)`.
 *        Called once per interaction; see the note on fuel above.
 * @param {Element} options.container mount point; not replaced
 * @param {object} [options.dom] DOM factory override (tests inject a mock)
 * @param {string[]} [options.eventKinds] subset of DEFAULT_EVENT_KINDS
 * @param {Function} [options.onError] called with a KotobaAppError instead of
 *        throwing out of a listener, where nothing could catch it
 * @param {Function} [options.onRender] called after each successful render
 * @returns {{state:Function, dispatch:Function, render:Function, unmount:Function,
 *            instantiations:Function}}
 */
export function mountKotobaApp({
  instantiate,
  container,
  dom = {},
  eventKinds = DEFAULT_EVENT_KINDS,
  onError,
  onRender
} = {}) {
  if (typeof instantiate !== "function")
    fail("invalid-instance", "instantiate must be a function returning a fresh instance");
  if (container == null || typeof container !== "object")
    fail("invalid-container", "a mount container is required");
  const kinds = [...new Set(eventKinds)];
  for (const kind of kinds) {
    if (!DEFAULT_EVENT_KINDS.includes(kind))
      fail("invalid-event-kind", `event kind is not admitted: ${kind}`);
  }
  if (typeof container.addEventListener !== "function")
    fail("dom-unavailable", "container must accept event listeners");

  let instantiations = 0;

  /**
   * Run `body` against a fresh, fully-fuelled instance. Guest traps -- fuel
   * exhaustion included -- surface as one error kind, so "the app stopped
   * responding" stays distinguishable from "the host is broken".
   */
  const withInstance = body => {
    let instance;
    try {
      instance = instantiate();
      instantiations += 1;
    } catch (error) {
      throw new KotobaAppError("instantiate-failed", "Kotoba app instantiate failed", error);
    }
    for (const name of ["init", "view", "step"]) {
      if (typeof instance?.[name] !== "function")
        fail("invalid-instance", `Kotoba app module must export ${name}`);
    }
    return body(instance);
  };

  const call = (instance, name, ...args) => {
    try {
      return instance[name](...args);
    } catch (error) {
      throw new KotobaAppError("guest-trap", `Kotoba app ${name} trapped`, error);
    }
  };

  const paint = (instance, next) => {
    const root = reconcileUiDocument(container, call(instance, "view", next), dom);
    if (typeof onRender === "function") onRender(root, next);
    return root;
  };

  let state = withInstance(instance => call(instance, "init"));
  let mounted = true;

  const render = () => withInstance(instance => paint(instance, state));

  const dispatch = (target, kind, value = "") => {
    if (!mounted) return false;
    return withInstance(instance => {
      const next = call(instance, "step", state, target, kind,
                        boundedString(value, MAX_VALUE_BYTES));
      // Reference equality is the cheap half of the check; a guest that rebuilt
      // an identical document still re-renders, and reconcile makes that a no-op
      // at the DOM level rather than a visible repaint.
      if (next === state) return false;
      // Paint before committing: a view that traps leaves the previous state
      // in place, so the page keeps matching what the host thinks is true.
      paint(instance, next);
      state = next;
      return true;
    });
  };

  const handler = event => {
    if (!mounted) return;
    try {
      const target = nominalTarget(event?.target, container);
      if (target === null) return;
      dispatch(target, event.type, eventValue(event));
    } catch (error) {
      const wrapped = error instanceof KotobaAppError ? error
        : new KotobaAppError("dispatch-failed", "Kotoba app dispatch failed", error);
      if (typeof onError === "function") onError(wrapped);
      else throw wrapped;
    }
  };

  for (const kind of kinds) container.addEventListener(kind, handler);

  render();

  return {
    state: () => state,
    // How many instances this mount has spent. A test can assert the fuel
    // discipline is actually per-interaction instead of trusting the comment.
    instantiations: () => instantiations,
    dispatch,
    render,
    unmount() {
      if (!mounted) return;
      mounted = false;
      if (typeof container.removeEventListener === "function")
        for (const kind of kinds) container.removeEventListener(kind, handler);
    }
  };
}

export { KotobaAppError };
