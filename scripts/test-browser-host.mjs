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

const uleb = value => {
  const bytes = [];
  do {
    let byte = value & 0x7f;
    value >>>= 7;
    if (value !== 0) byte |= 0x80;
    bytes.push(byte);
  } while (value !== 0);
  return bytes;
};
const wasmText = value => {
  const bytes = Array.from(new TextEncoder().encode(value));
  return [...uleb(bytes.length), ...bytes];
};
const wasmSection = (id, payload) => [id, ...uleb(payload.length), ...payload];
const wasmBody = instructions => {
  const body = [0, ...instructions, 0x0b];
  return [...uleb(body.length), ...body];
};
const exportFunction = (name, index) => [...wasmText(name), 0, ...uleb(index)];
const typedBulkVectorModule = withCompatibility(Uint8Array.from([
  0,97,115,109,1,0,0,0,
  ...wasmSection(0, [...wasmText("kotoba.typed"), 8,1,11,0]),
  ...wasmSection(1, [
    2,
    0x60,3,0x7f,0x7f,0x7f,1,0x6f,
    0x60,0,1,0x7e,
  ]),
  ...wasmSection(2, [
    2,
    ...wasmText("kotoba:typed"), ...wasmText("vector-from-memory-i64"), 0,0,
    ...wasmText("kotoba:typed"), ...wasmText("scratch"), 2,1,2,2,
  ]),
  ...wasmSection(3, [3,1,1,1]),
  ...wasmSection(7, [
    3,
    ...exportFunction("main", 1),
    ...exportFunction("unaligned", 2),
    ...exportFunction("oversized", 3),
  ]),
  ...wasmSection(10, [
    3,
    ...wasmBody([
      0x41,0, 0x42,42, 0x37,3,0,
      0x41,0, 0x41,0, 0x41,1, 0x10,0, 0x1a,
      0x42,42,
    ]),
    ...wasmBody([
      0x41,0, 0x41,1, 0x41,1, 0x10,0, 0x1a,
      0x42,0,
    ]),
    ...wasmBody([
      0x41,0, 0x41,0, 0x41,0x81,0x80,0x01, 0x10,0, 0x1a,
      0x42,0,
    ]),
  ]),
]), { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });
const typedScratchOnlyModule = withCompatibility(Uint8Array.from([
  0,97,115,109,1,0,0,0,
  ...wasmSection(0, [...wasmText("kotoba.typed"), 8,1,11,0]),
  ...wasmSection(1, [1, 0x60,0,1,0x7e]),
  ...wasmSection(2, [
    1, ...wasmText("kotoba:typed"), ...wasmText("scratch"), 2,1,2,2,
  ]),
  ...wasmSection(3, [1,0]),
  ...wasmSection(7, [1, ...exportFunction("main", 0)]),
  ...wasmSection(10, [1, ...wasmBody([0x42,42])]),
]), { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });
const typedBulkFunctionOnlyModule = withCompatibility(Uint8Array.from([
  0,97,115,109,1,0,0,0,
  ...wasmSection(0, [...wasmText("kotoba.typed"), 8,1,11,0]),
  ...wasmSection(1, [
    2,
    0x60,3,0x7f,0x7f,0x7f,1,0x6f,
    0x60,0,1,0x7e,
  ]),
  ...wasmSection(2, [
    1, ...wasmText("kotoba:typed"), ...wasmText("vector-from-memory-i64"), 0,0,
  ]),
  ...wasmSection(3, [1,1]),
  ...wasmSection(7, [1, ...exportFunction("main", 1)]),
  ...wasmSection(10, [1, ...wasmBody([0x42,42])]),
]), { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });

const hosted = await instantiateKotoba(main42);
assert.equal(hosted.instance.exports.main(), 42n);
assert.match(hosted.sha256, /^[0-9a-f]{64}$/);
assert.deepEqual(hosted.report(), { heap: { capacity: 4096, used: 0 } });
await instantiateKotoba(main42, { expectedSha256: hosted.sha256 });
const typedHosted = await instantiateKotoba(typedMain42);
assert.equal(typedHosted.typedScratchPages, 0);
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
const bulkHosted = await instantiateKotoba(typedBulkVectorModule);
assert.equal(bulkHosted.typedScratchPages, 2);
assert.equal(bulkHosted.instance.exports.main(), 42n);
assert.throws(
  () => bulkHosted.instance.exports.unaligned(),
  error => error instanceof KotobaHostError && error.code === "invalid-typed-operation"
);
assert.throws(
  () => bulkHosted.instance.exports.oversized(),
  error => error instanceof KotobaHostError && error.code === "invalid-typed-operation"
);
assert.deepEqual(WebAssembly.Module.imports(bulkHosted.module).map(({ module, name, kind }) =>
  `${module}/${name}/${kind}`), [
  "kotoba:typed/vector-from-memory-i64/function",
  "kotoba:typed/scratch/memory",
]);
assert.ok(!WebAssembly.Module.exports(bulkHosted.module).some(({ kind }) => kind === "memory"));
await assert.rejects(
  instantiateKotoba(typedScratchOnlyModule),
  error => error instanceof KotobaHostError && error.code === "invalid-module"
);
await assert.rejects(
  instantiateKotoba(typedBulkFunctionOnlyModule),
  error => error instanceof KotobaHostError && error.code === "invalid-module"
);
assert.ok(browserProfile.imports.includes("kotoba:typed/bool-value/function"),
  "ADR 0191 A: typed-bool-value must be host-allowlisted");
assert.ok(browserProfile.imports.includes("kotoba:typed/scratch/memory"));
assert.ok(browserProfile.imports.includes("kotoba:typed/vector-from-memory-i64/function"));


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

assert.equal(browserProfile.format, "kotoba.browser-host/v1");
assert.equal(browserProfile.maxModuleBytes, 1048576);
assert.equal(browserProfile.pairCapacity, 4096);
assert.equal(browserProfile.typedAbiVersion, 14);
assert.equal(browserProfile.typedVectorItemLimit, 16384);
assert.equal(browserProfile.typedScratchPages, 2);
assert.ok(Object.isFrozen(browserProfile));
console.log("browser-host: admission, identity, execution, and denial vectors passed");
