import assert from "node:assert/strict";
import {
  KotobaHostError,
  browserProfile,
  instantiateKotoba,
  normalizeKotobaTrap
} from "../runtime/browser-host.mjs";
import { withCompatibility } from "./compatibility-fixture.mjs";

const rawMain42 = Uint8Array.from([
  0,97,115,109,1,0,0,0,
  1,5,1,96,0,1,126,
  3,2,1,0,
  7,8,1,4,109,97,105,110,0,0,
  10,6,1,4,0,66,42,11
]);
const main42 = withCompatibility(rawMain42);

const typedMain42 = withCompatibility(Uint8Array.from([
  0,97,115,109,1,0,0,0,
  0,18,12,107,111,116,111,98,97,46,116,121,112,101,100,5,1,4,0,0,
  1,5,1,96,0,1,126,
  3,2,1,0,
  7,8,1,4,109,97,105,110,0,0,
  10,6,1,4,0,66,42,11
]), { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });
const typedListMain42 = withCompatibility(Uint8Array.from([
  0,97,115,109,1,0,0,0,
  0,20,12,107,111,116,111,98,97,46,116,121,112,101,100,
  13,1,20,3,0,0,0,
  1,5,1,96,0,1,126,
  3,2,1,0,
  7,8,1,4,109,97,105,110,0,0,
  10,6,1,4,0,66,42,11
]), { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });
const typedBytesMain42 = withCompatibility(Uint8Array.from([
  0,97,115,109,1,0,0,0,
  0,19,12,107,111,116,111,98,97,46,116,121,112,101,100,
  14,1,21,0,0,0,
  1,5,1,96,0,1,126,
  3,2,1,0,
  7,8,1,4,109,97,105,110,0,0,
  10,6,1,4,0,66,42,11
]), { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });

const hosted = await instantiateKotoba(main42);
assert.equal(hosted.instance.exports.main(), 42n);
assert.match(hosted.sha256, /^[0-9a-f]{64}$/);
assert.deepEqual(hosted.report(), { heap: { capacity: 4096, used: 0 } });
await instantiateKotoba(main42, { expectedSha256: hosted.sha256 });
const typedHosted = await instantiateKotoba(typedMain42);
assert.deepEqual(typedHosted.typedAbi, {
  version: 5,
  descriptors: [["option", "i64"]],
  literals: [],
  schemas: new Map(),
  contracts: new Map()
});
assert.ok(Object.isFrozen(typedHosted.typedAbi));
const typedListHosted = await instantiateKotoba(typedListMain42);
assert.equal(typedListHosted.typedAbi.version, 13);
assert.deepEqual(typedListHosted.typedAbi.descriptors, [["list", "bool"]]);
const typedBytesHosted = await instantiateKotoba(typedBytesMain42);
assert.equal(typedBytesHosted.typedAbi.version, 14);
assert.deepEqual(typedBytesHosted.typedAbi.descriptors, ["bytes"]);
assert.ok(browserProfile.imports.includes("kotoba:typed/bool-value/function"),
  "ADR 0191 A: typed-bool-value must be host-allowlisted");


await assert.rejects(
  instantiateKotoba(rawMain42),
  error => error instanceof KotobaHostError && error.code === "missing-compatibility"
);

const unsupportedTypedMain42 = typedMain42.slice();
unsupportedTypedMain42[23] = 4;
await assert.rejects(
  instantiateKotoba(unsupportedTypedMain42),
  error => error instanceof KotobaHostError && error.code === "unsupported-typed-abi"
);

await assert.rejects(
  instantiateKotoba(main42, { expectedSha256: "0".repeat(64) }),
  error => error instanceof KotobaHostError && error.code === "digest-mismatch"
);
await assert.rejects(
  instantiateKotoba(main42, { ambientNetwork: true }),
  error => error.code === "invalid-options"
);
await assert.rejects(
  instantiateKotoba(new Uint8Array(1024 * 1024 + 1)),
  error => error.code === "invalid-module"
);

const forbiddenImport = Uint8Array.from([
  0,97,115,109,1,0,0,0,
  1,4,1,96,0,0,
  2,13,1,4,101,118,105,108,4,99,97,108,108,0,0
]);
await assert.rejects(
  instantiateKotoba(forbiddenImport),
  error => normalizeKotobaTrap(error).code === "forbidden-import"
);

// A pre-compiled module, for hosts that cannot compile at runtime. Cloudflare
// Workers admit a module only through the bundler; measured 2026-08-31, passing
// bytes to a deployed Worker fails with `invalid-module / Wasm compilation
// failed` whatever the bytes are.
const preCompiled = await WebAssembly.compile(main42);
const fromModule = await instantiateKotoba(preCompiled, {});
assert.equal(fromModule.instance.exports.main(), 42n);
// Null, not a digest and not a lie: the bytes are gone, so the identity was
// never computed and nothing should read one.
assert.equal(fromModule.sha256, null);
// And an identity that cannot be checked is refused rather than skipped --
// otherwise `expectedSha256` would be a field that sometimes checks nothing.
await assert.rejects(
  instantiateKotoba(preCompiled, { expectedSha256: hosted.sha256 }),
  error => normalizeKotobaTrap(error).code === "digest-unverifiable"
);
// The bytes path keeps checking, so this is a widening and not a hole.
await assert.rejects(
  instantiateKotoba(main42, { expectedSha256: "0".repeat(64) }),
  error => normalizeKotobaTrap(error).code === "digest-mismatch"
);
// Admission is unchanged for a module: a forbidden import is still refused
// after compilation, not only during it.
await assert.rejects(
  WebAssembly.compile(forbiddenImport).then(m => instantiateKotoba(m, {})),
  error => normalizeKotobaTrap(error).code === "forbidden-import"
);

assert.equal(browserProfile.format, "kotoba.browser-host/v1");
assert.equal(browserProfile.maxModuleBytes, 1048576);
assert.equal(browserProfile.pairCapacity, 4096);
assert.equal(browserProfile.typedAbiVersion, 14);
assert.ok(Object.isFrozen(browserProfile));
console.log("browser-host: admission, identity, execution, and denial vectors passed");
