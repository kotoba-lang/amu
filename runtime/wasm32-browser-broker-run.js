// wasm32-browser broker run page, the trusted host (JUN-353 Phase 2).
// Profile restricted-wasm-v1: this document holds the shared consent host and
// operation broker; a guest never runs here. Every guest module runs in the
// restricted guest shell, which mountRestrictedClientApp mounts in a sandboxed
// iframe (opaque origin, connect-src 'none'), and the shell's Worker. All
// validation, consent and sending are kotoba-client-runtime.js's; this file
// only builds the broker from the run's descriptor, verifies and mounts the
// guest, and reports.
//
// window.kotobaBrokerState() is for the qualification harness: the run in
// progress, how many times the consent dialog has been shown, and whether it
// is open. It reads the dialog; it cannot approve anything.
import {
  clientRuntimeConnectSrc,
  createClientConsentHost,
  createClientOperationBroker,
  mountRestrictedClientApp,
  verifyClientArtifact,
} from "./kotoba-client-runtime.js";

const results = document.getElementById("results");
const container = document.getElementById("guest");
const policy = document.querySelector('meta[http-equiv="Content-Security-Policy"]').content;
const pageConnectSrc = (policy.split(";").map((s) => s.trim()).find((s) => s.startsWith("connect-src ")) || "");

const consentHost = createClientConsentHost();
const dialog = document.querySelector("dialog.kotoba-client-consent");
let shown = 0;
let current = null;
let done = false;
new MutationObserver((records) => {
  for (const r of records) if (r.oldValue === null && dialog.hasAttribute("open")) shown += 1;
}).observe(dialog, { attributes: true, attributeFilter: ["open"], attributeOldValue: true });
window.kotobaBrokerState = () => ({
  done, run: current, dialogs: shown, open: dialog.open,
  allowDisabled: dialog.querySelector("button:last-child").disabled,
  scope: dialog.querySelector(".kotoba-client-consent-scope").textContent,
});

function guestResult(timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { removeEventListener("message", receive); reject(new Error("the guest did not report")); }, timeoutMs);
    function receive(event) {
      const frame = container.querySelector("iframe");
      if (!frame || event.source !== frame.contentWindow || event.origin !== "null"
          || !event.data || event.data.protocol !== "kotoba.wasm32-browser.result.v1") return;
      clearTimeout(timer);
      removeEventListener("message", receive);
      resolve(event.data.result);
    }
    addEventListener("message", receive);
  });
}

async function runOne(run) {
  if (run.runtime.profile !== "restricted-wasm-v1") throw new Error("the broker host runs only restricted-wasm-v1 guests");
  const connectSrc = clientRuntimeConnectSrc(run.runtime, run.requestedCapabilities);
  if (connectSrc !== pageConnectSrc) throw new Error(`page ${pageConnectSrc} is not the descriptor's ${connectSrc}`);
  const broker = createClientOperationBroker({
    runtime: run.runtime,
    requestedCapabilities: run.requestedCapabilities,
    approvedOperations: run.runtime.operations,
    hostSupportedOperations: run.hostSupportedOperations,
    consentHost,
  });
  const bytes = Uint8Array.from(atob(run.guest), (c) => c.charCodeAt(0));
  const artifact = await verifyClientArtifact(bytes, { revision: run.revision, sha256: run.sha256, "max-bytes": 8388608 });
  const before = shown;
  const result = guestResult(run.timeoutMs || 120000);
  const app = await mountRestrictedClientApp({ artifact, container, broker });
  try {
    return Object.assign({}, await result, { dialogs: shown - before });
  } finally {
    app.close();
  }
}

(async () => {
  for (const run of window.KOTOBA_BROKER_RUNS || []) {
    current = run.name;
    let line;
    try {
      line = Object.assign({}, await runOne(run), { name: run.name });
    } catch (e) {
      line = { name: run.name, exit: null, hostError: String((e && e.message) || e) };
    }
    results.textContent += JSON.stringify(line) + "\n";
  }
  current = null;
  done = true;
  document.title = "kotoba-done";
})();
