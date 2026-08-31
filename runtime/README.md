# Kotoba browser runtime

Experimental deny-by-default host for `wasm32-browser-kotoba-v1` modules.

```js
import { instantiateKotoba, normalizeKotobaTrap } from "@kotoba-lang/browser-runtime";

const hosted = await instantiateKotoba(wasmBytes, {
  expectedSha256: reviewedDigest,
  allowCapabilities: [7],
  capCall(id, value) {
    if (id === 7) return value + 1n;
    throw new Error("unimplemented capability");
  }
});

try {
  hosted.instance.exports.main();
} catch (error) {
  console.error(normalizeKotobaTrap(error));
}
```

`instantiateKotoba` also accepts an already-compiled `WebAssembly.Module` in
place of bytes, for hosts that cannot compile at runtime — Cloudflare Workers
admit a module only when it arrives through the bundler as an import. In that
form there are no bytes left to hash, so `expectedSha256` is refused
(`digest-unverifiable`) rather than silently skipped, and `sha256` on the
result is `null`. Verify the identity where the bytes still exist.

The host copies and caps module bytes, verifies an optional SHA-256 identity,
allows only the versioned Kotoba function imports, denies capabilities unless
their numeric IDs are explicitly admitted, and owns a fixed 4,096-cell
immutable pair arena. It exports no pair storage or host pointer. This module
does not grant DOM, network, storage, worker, clock, randomness, or other
ambient browser authority.

For execution outside the document realm, use the static pure-worker entry:

```js
const worker = new Worker(workerEntryUrl, { type: "module" });
worker.postMessage({
  format: "kotoba.worker-request/v1",
  id: "run-1",
  op: "run",
  wasm: wasmBytes,
  expectedSha256: reviewedDigest,
  allowCapabilities: [],
  args: []
});
```

The request is a closed one-shot protocol. IDs and argument counts are bounded,
arguments/results are i64 `bigint` values, overlapping requests fail as busy,
and responses expose stable error classes rather than exception text. Trusted
capability adapters can only be installed in the worker entry at construction;
they cannot arrive in a guest message. See [CSP.md](CSP.md) for the restrictive
HTTP deployment profile.

## IPLD ADL Wasmtime engine

`ipld-adl-wasmtime.c` is the synchronous reference engine for io-ipld's
`ipld-adl-wasm-v1` host port. Build it with
`scripts/build-ipld-adl-wasmtime.cljs`. Each call creates a fresh Wasmtime Store,
admits a core Wasm module with zero imports, and enforces Store fuel, linear
memory, output-byte, and epoch deadline limits. The receipt's fuel and memory
values come from Wasmtime after execution; guest output cannot supply them.

The guest ABI exports `memory`, `adl_alloc(i32) -> i32`, and
`adl_transform(operation, input-pointer, input-length) -> i64`. The returned
i64 packs the output pointer in its high 32 bits and length in its low 32 bits.
Input and output are canonical DAG-CBOR; operation codes are declared in
`ipld-adl-wasmtime.h`. The host grants no WASI, filesystem, network, clock, or
randomness imports. The embedding process and linked Wasmtime remain the TCB.

`kotoba.compiler.ipld-adl/wasmtime-capability` turns that executable into an
io-ipld capability. io-ipld independently re-derives the raw module CID,
checks canonical output, charges measured fuel, and records module/input/output
CIDs. Run `npm run test-ipld-adl-wasmtime` for success plus fuel exhaustion,
timeout, import denial, memory cap, output cap, and projection receipt evidence.

## JVM-free HTTP service host (`http-service.mjs`)

`http-service.mjs` is a multi-route Node `node:http` host for compiled Kotoba
guests, built on the `:js-kotoba-v1` restricted-ESM compile target
(`amu compile --target js`) rather than `wasm32-wasi`. It generalizes
`wasi-service.mjs` in two directions: an arbitrary-size route table instead
of one fixed `POST /v1/run` entry, and request/response bodies carrying
arbitrary syntactically-valid JSON text instead of five fixed i64 decimals.
Startup still seals every module (route guests and the decision core) behind
a pinned sha256 digest read before import, and this host grants every guest
zero capabilities -- no DOM, no fs, no network, no clock -- so a module
declaring a capability requirement is refused at startup, not at request
time.

Unlike `wasi-service.mjs`, request handling does not run in a
`worker_threads.Worker`. A wasm32-wasi module is a black box that could spin
forever without a hard OS-level cutoff, which is why wasi-service isolates
each call in its own worker. A `:js-kotoba-v1` restricted-ESM instance
carries a fixed, non-replenishing fuel budget instead (see
`instantiateKotoba()` in `dom-driver.mjs`): a guest call either returns or
traps with `fuel-exhausted`, so it cannot hold the event loop open. A fresh
instance per call (the same pattern dom-driver already uses) is therefore
both correct and simpler -- no worker thread, no `postMessage`, no
serialization boundary for the plain strings/i64/bool/keyword values that
cross directly as JS values.

### The decision/mechanism split

Which HTTP method+path this host treats as a route, which outcome a request
produces, and which HTTP status that outcome maps to are not decided by a
`cond` inside `http-service.mjs`. They are decided by
`runtime/http/route-decide.kotoba`, compiled ahead of time to
`runtime/http/route-decide.mjs` and called on every request -- mirroring the
decision/mechanism boundary `kotoba-lang/mesh`'s `route.kotoba` draws for its
JVM+Chicory-hosted router (ADR-2608112100). What stays in the `.mjs` host,
and why: the route TABLE itself (a collection that grows as routes are
added -- the decision core is only ever handed a boolean saying whether a
route is bound, never the table), reading a guest's return value out of its
restricted-ESM instance, and writing the socket. Those are effects and a
growing collection, not a decision. The shipped `route-decide.mjs` is
committed alongside its `.provenance.edn`/`.inputs.edn`/`.manifest.edn`
sidecars; `scripts/http-service-e2e.cljs` recompiles the `.kotoba` source
fresh on every run and fails loudly if the shipped artifact has drifted from
it.

### What this does NOT do

Named explicitly, not left to be discovered by absence:

- No path parameters or wildcards -- routes are exact `(method, path)` pairs.
- No sessions, cookies, or streaming request/response bodies.
- No structural JSON parsing *inside* the guest. A request/response body
  crosses the host/guest boundary as a validated-syntactically-JSON
  `:string`; a guest that wants specific fields must do its own string work
  today (or, once `kotoba-lang/json` has a `.kotoba` port, use that).

This is a foundational host library, not an application: no product routes
are ported here, and no capability package (e.g. a future
`capability-http-serve`) is introduced by it -- every guest this host loads
runs with zero granted capabilities.

Run `node scripts/http-service-e2e.cljs`-style orchestration via
`node node_modules/nbb/cli.js scripts/http-service-e2e.cljs`, which
recompiles the decision core and two fixture guests fresh, then drives
`test/http/http_service_test.mjs` -- a real `node:http` server answering
real `fetch` requests over a real socket -- through health/echo/404/
malformed-body/oversize-body/delegation/digest-mismatch/capability-refusal
assertions.

`kotoba.compiler.core/compile-ipld-adl-source` removes the need to author this
guest ABI as WAT. Its fail-closed source profiles accept exactly four pure
Kotoba functions. `:pure-identity-v1` preserves bytes with total validators;
`:pure-closed-v1` additionally lowers literal true/false validators and
per-operation identity or `(bytes)` results (the latter becomes canonical
DAG-CBOR empty bytes, `0x40`). Both emit the three ABI exports above, fixed
bounded memory, and no imports. Any body outside that implemented source slice
is rejected rather than being mislabeled as another transform.

For distributed execution, pass an Ed25519 `:executor-key` and a
`:receipt-sink` to `wasmtime-capability`. The adapter snapshots the admitted
runner bytes, executes that snapshot, and emits a closed
`kotoba.ipld-adl-execution-receipt/v1` binding the runner SHA-256,
module/input/output CIDs, operation, engine version, declared limits, and
measured fuel/memory/output. `verify-execution-receipt!` checks its canonical
hash, signer trust/revocation, Ed25519 signature, schema, resource inequalities,
and an explicit `:trusted-runner-sha256` allowlist (obtain the expected value
with `runner-sha256`). Private key material is closure-local and is never
included in the capability or receipt.
