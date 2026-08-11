// Mounts examples/todo-app.kotoba as a live application and reports what the
// mount alone can prove. The interaction half is deliberately NOT scripted
// here: browser.spec.mjs clicks and types through Playwright, so the events
// reaching the guest are real trusted browser events, not ones this file
// synthesised.

import { reconcileUiDocument } from "/runtime/browser-host.mjs";
import { mountKotobaApp } from "/runtime/dom-driver.mjs";

const status = document.querySelector("#status");
const report = document.querySelector("#report");

const doc = (tag, attrs) => ["map", [
  [":tag", ["string", tag]],
  [":attrs", ["map", attrs]],
  [":text", ["string", "x"]]
]];

/** @returns {string} the rejection code, or "accepted" if it was not refused */
function denialCode(node) {
  const probe = document.createElement("div");
  try {
    reconcileUiDocument(probe, node);
    return "accepted";
  } catch (error) {
    return error?.code ?? "unknown";
  }
}

try {
  const module = await import("/artifacts/todo-app.mjs");
  const caps = module.kotobaArtifact.requiredCapabilities;
  if (!Array.isArray(caps) || caps.length !== 0)
    throw new Error(`expected an ungranted app, got capabilities ${JSON.stringify(caps)}`);

  const container = document.querySelector("#app");
  const app = mountKotobaApp({
    instantiate: () => module.instantiateKotoba({}),
    container
  });
  if (!container.querySelector('[data-k="add"]'))
    throw new Error("mount did not render the app");

  report.textContent = JSON.stringify({
    format: "kotoba.dom-app-conformance/v1",
    capabilities: caps.length,
    // Attributes reach the DOM...
    labelled: container.querySelectorAll("[data-k]").length > 0 ? "ok" : "missing",
    // ...but the three ADR-0025 exclusions stay closed, checked against a real
    // browser DOM rather than the Node mock.
    handler: denialCode(doc("div", [[":onclick", ["string", "steal()"]]])),
    style: denialCode(doc("div", [[":style", ["string", "position:fixed"]]])),
    url: denialCode(doc("a", [[":href", ["string", "javascript:steal()"]]])),
    safeUrl: denialCode(doc("a", [[":href", ["string", "/docs"]]])),
    mounted: typeof app.unmount === "function" ? "ok" : "missing"
  });
  status.setAttribute("data-result", "passed");
  status.textContent = "mounted";
} catch (error) {
  report.textContent = String(error?.stack ?? error);
  status.setAttribute("data-result", "failed");
  status.textContent = "failed";
}
