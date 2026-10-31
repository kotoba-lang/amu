# The consent broker for wasm32-browser guests (JUN-353 Phase 2)

A wasm32-browser guest (`F compile SRC --target wasm32-browser`) reaches an
external service only through the shared consent broker,
`kotoba-client-runtime.js`. This follows the workspace contract for Kotoba
end-user apps: consent for each operation, declared endpoints only, fail
closed, a denial sends no request, and no app-origin proxy.

## What changed

- **`seed/82-wasm32-rt.kotoba`.**
  - At start, the runtime asks the page for a grant of every wire 0..63
    (`input(2, wire)`), not only 35, 37, 38 and 39.
  - A granted wire that the runtime does not serve itself, called with a
    `:string` request, goes to `kotoba:host/cap`. A non-negative answer is the
    response's length, and the runtime copies the response into the string
    pool (`input(3, ..)`). A negative answer is refused by name, as before.
  - With no grant, nothing changes: the 24 cases and the Phase 1 and Phase 3
    probes give the same result, trap and remaining fuel.
- **`runtime/wasm32-browser-static-host.js`** (the Worker host) takes `bind`:
  the wires that the trusted page has bound.
  - It grants those wires.
  - It suspends the guest while a call is in flight (JSPI,
    `WebAssembly.Suspending` and `WebAssembly.promising`), and posts the
    request out of the Worker.
  - An unbound wire is refused (-1), and so is every wire when JSPI is
    absent. Without `bind` the host behaves as before.
- **`runtime/kotoba-client-runtime.js`** is the KOTOBA-159 reviewed revision,
  copied byte for byte: kotoba-lang/kotoba
  `lib/kotoba.wasmWebcomponent/src/kotoba-client-runtime.js` @
  `6f74fe21760a1c752a05340ffb52e69a38877874`, sha256
  `4e6ef6eea88641b20c490692d271ce57891e53e01fcc5c303135a325b2f5b693`. The
  pin, with the SRI, is in `runtime/kotoba-client-runtime.pin.json`.
- **`runtime/wasm32-browser-broker-run.html` and `.js`** are the trusted host
  page.
  - It imports the broker under an import map `integrity` equal to the pin.
  - It builds the broker and consent host from each run's descriptor, and
    refuses any profile but `restricted-wasm-v1`.
  - It checks that its static `connect-src` equals
    `clientRuntimeConnectSrc(descriptor)`.
  - It verifies the guest shell (`verifyClientArtifact`) and mounts it
    (`mountRestrictedClientApp`).
- **`runtime/wasm32-browser-restricted-guest.html`** is the guest shell. It
  runs inside the sandboxed iframe under `connect-src 'none'`. It starts the
  Worker, maps a bound wire to its selector, and moves one
  `kotoba.client.operation.v1` message per call over the transferred port.
- **Protocol.**
  - Request: `METHOD TARGET`, then optionally a newline and the body. The
    broker resolves `TARGET` against the declared endpoint's origin.
  - Answer: `STATUS`, a newline, then the response text.
  - Every refusal, including undeclared, denied and failed, traps the guest
    with `KEXE_CAP {:wire N :refused :wasm32-browser}`.

## Profile

Consent is enforceable only under `restricted-wasm-v1` (KOTOBA-159 finding 1,
High, still open for `trusted-page-v1`). The page that holds the broker never
runs guest code. The guest's module runs in a Worker inside a sandboxed iframe
(an opaque origin, `allow-scripts` only) and can reach the outside only
through its fixed `kotoba:host` imports. That is why the broker host refuses
every other profile.

## Qualification (CI: `qualify-x86_64`, the image's google-chrome)

`scripts/seed/check-wasm32-browser.py --modules DIR` runs the broker's runs
when `DIR/probe-cap.wasm` is present. The pr tier of `selfhost-bootstrap.py`
compiles `probe-cap` (one call of wire 45, then the answer is written) and
`probe-cap-twice` (two calls) with F.

**Setup.**
- The page is served from 127.0.0.1, because module scripts do not load from
  `file://`.
- The browser is driven over the DevTools pipe. There is no Node, npm or
  Playwright.
- Every https request of the page is held at the request stage (`Fetch`) and
  recorded. Frames and workers are also auto-attached and observed where
  their target type allows.
- Only the declared fixture endpoint (`https://service.invalid`) is answered,
  and only in runs that plan an approval. Any other request is failed.
  Nothing leaves the machine.

**What is qualified**, all six runs and their checks:

| run | broker reached | dialogs | https requests | outcome |
|---|---|---|---|---|
| `cap-unbound` | no (the wire is not granted) | 0 | 0 | refused by name |
| `cap-undeclared-operation` | yes: not eligible and supported | 0 | 0 | refused |
| `cap-undeclared-endpoint` | yes: request does not match the declared method/path | 0 | 0 | refused before consent |
| `cap-denied` | yes: not approved | 1 | 0 | refused by name |
| `cap-approved` | yes: answered | 1 | 1 GET `/v1/items/abc` | exit 0, output `200\n` + the fixture |
| `cap-approval-once` | answered, then not approved | 2 | 1 | the second call needs its own dialog |

Each run also checks the following:
- **Every dialog.** It shows the endpoint `https://service.invalid` and the
  action `GET /v1/items/abc`.
- **Synthetic click.** Every dialog first gets a synthetic Allow `.click()`
  after Allow is enabled (`isTrusted` false). It must leave the dialog open
  and send nothing.
- **Sent requests.** A request may only come from the host page, use the
  declared method and path, and carry no `Cookie` or `Authorization` header.

**Negative controls:**
- **In CI.** `cap-approved` is the positive control for both the request
  detector and the click target. A click there does approve and does send,
  so "no request" and "the synthetic click did not approve" in the other runs
  are meaningful.
- **In CI.** The pin check refuses a copy with one byte changed.
- **Locally on 2026-10-31** (Mac arm64, Chrome 156.0.8078.74):
  - `probe-cap` and `probe-cap-twice`, compiled by main's root
    (`amu-full-root.macho`, whose seed/82 refuses every cap), fail the suite.
    `cap-undeclared-operation` never reaches the broker (`capLog` is empty).
  - A broker copy edited to set `ALLOW_ARM_MS = 0` is refused by the harness
    pin check.
  - With the pin check bypassed, the same edited copy fails the page's import
    map integrity: the page never runs (timeout).

## What is not qualified

- **A person's click.** In the approve runs, Allow is pressed through DevTools
  `Input.dispatchMouseEvent`, which the browser marks `isTrusted`. That is
  automation. It proves the path after an approval: one invocation is sent
  directly to the declared endpoint, and nothing more. It is not evidence
  that a person saw and approved the dialog. A manual check with a real click
  is still open.
- **A real service.** The declared endpoint is a fixture answered at the
  request stage. Real DNS, TLS, CORS and redirect behaviour of a provider are
  not exercised. The broker refuses redirects unless they are declared.
- **Browsers without JSPI.** There, a bound wire is refused (fail closed).
  Firefox and Safari are not run.
- **A dedicated wire.** The language catalogue has no service-operation wire.
  A host binds an existing catalogued `:string` wire that the browser runtime
  does not serve itself, and the probes use 45 (`:net/dial`). A dedicated
  wire (for example `:service/call`) is a change to the adopted core (checker,
  projection, driver) and needs an owner-approved adoption round.
- **Product integration.** Building an app's own descriptor, guest shell
  artifact and publication is each product's work (for example kumitate,
  JUN-346). Their wasm module bytes change with this runtime, so a product
  that pins its module must rebuild it.
