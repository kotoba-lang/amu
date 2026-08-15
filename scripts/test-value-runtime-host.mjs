import assert from "node:assert/strict";
import { createValueRuntime, KotobaHostError } from "../runtime/browser-host.mjs";

const cid = `bafyre${"a".repeat(53)}`;
const calls = [];
const runtime = createValueRuntime((operation, payload) => {
  calls.push([operation, payload]);
  switch (operation) {
    case "value/intern": return 17;
    case "value/hydrate": return 18n;
    case "value/resolve": return new Uint8Array([1, 2, 3]);
    case "value/cid-of": return cid;
    case "value/release": return true;
    default: throw new Error(`unexpected operation: ${operation}`);
  }
});

const source = new Uint8Array([9, 8, 7]);
assert.equal(runtime.imports.intern(source), 17n);
assert.equal(runtime.imports.hydrate(cid), 18n);
assert.deepEqual(Array.from(runtime.imports.resolve(17n)), [1, 2, 3]);
assert.equal(runtime.imports["cid-of"](17n), cid);
assert.equal(runtime.imports.release(17n), 1n);
assert.deepEqual(calls.map(([operation]) => operation),
                 ["value/intern", "value/hydrate", "value/resolve",
                  "value/cid-of", "value/release"]);
assert.notEqual(calls[0][1], source, "canonical bytes cross by defensive copy");

assert.throws(() => createValueRuntime().imports.resolve(1n),
              error => error instanceof KotobaHostError &&
                       error.code === "value-runtime-unavailable");
assert.throws(() => runtime.imports.resolve(0n),
              error => error instanceof KotobaHostError &&
                       error.code === "invalid-value-handle");
assert.throws(() => runtime.imports.hydrate("../STORE.edn"),
              error => error instanceof KotobaHostError &&
                       error.code === "invalid-value-cid");
assert.throws(() => createValueRuntime(() => ({capability: true})).imports.intern(source),
              error => error instanceof KotobaHostError &&
                       error.code === "invalid-value-handle");

console.log("VALUE RUNTIME HOST PASS");
