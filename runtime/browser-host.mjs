const MAX_MODULE_BYTES = 1024 * 1024;
const PAIR_CAPACITY = 4096;
const TYPED_SECTION = "kotoba.typed";
const TYPED_ABI_VERSION = 14;
const MIN_TYPED_ABI_VERSION = 5;
const COMPATIBILITY_SECTION = "kotoba.compatibility";
const COMPATIBILITY_VERSION = 1;
const MAX_TYPED_DESCRIPTORS = 64;
const ALLOWED_IMPORTS = new Set([
  "kotoba:cap/call/function",
  "kotoba:heap/pair/function",
  "kotoba:heap/pair-first/function",
  "kotoba:heap/pair-second/function",
  "kotoba:typed/literal/function",
  "kotoba:typed/new/function",
  "kotoba:typed/push-i64/function",
  "kotoba:typed/push-f64/function",
  "kotoba:typed/push-f32/function",
  "kotoba:typed/push-ref/function",
  "kotoba:typed/seal/function",
  "kotoba:typed/assert-ref/function",
  "kotoba:typed/tag/function",
  "kotoba:typed/get-i64/function",
  "kotoba:typed/get-f64/function",
  "kotoba:typed/get-f32/function",
  "kotoba:typed/get-ref/function",
  "kotoba:typed/count/function",
  "kotoba:typed/bool/function",
  "kotoba:typed/bool-value/function",
  "kotoba:typed/equal/function",
  "kotoba:typed/bytes-empty/function",
  "kotoba:typed/assoc-i64/function",
  "kotoba:typed/assoc-f64/function",
  "kotoba:typed/assoc-f32/function",
  "kotoba:typed/assoc-ref/function",
  "kotoba:typed/vector-drop/function",
  "kotoba:typed/vector-at-i64/function",
  "kotoba:typed/vector-assoc-i64/function",
  "kotoba:typed/vector-assoc-in-place-i64/function",
  "kotoba:typed/vector-alloc-i64/function",
  "kotoba:typed/vector-conj-i64/function",
  "kotoba:typed/vector-from-memory-i64/function",
  // A MEMORY import, not a function. The bulk vector path writes its
  // items into a scratch memory the HOST owns and then asks the host to
  // read them back in one call. Importing it is what keeps that inside
  // the profile: validateModule still refuses a module that EXPORTS a
  // memory, and this one is never the guest's to export.
  "kotoba:typed/scratch/memory",
  "kotoba:typed/vector-at-f64/function",
  "kotoba:typed/vector-assoc-f64/function",
  "kotoba:typed/vector-conj-f64/function",
  "kotoba:typed/set-op-i64/function",
  "kotoba:typed/set-op-ref/function",
  "kotoba:typed/set-contains-i64/function",
  "kotoba:typed/set-contains-ref/function",
  "kotoba:typed/set-nth-i64/function",
  "kotoba:typed/set-nth-ref/function",
  "kotoba:typed/map-contains-i64/function",
  "kotoba:typed/map-contains-ref/function",
  "kotoba:typed/map-get-i64/function",
  "kotoba:typed/map-get-ref/function",
  "kotoba:typed/map-entry-at/function",
  "kotoba:typed/map-assoc-ii/function",
  "kotoba:typed/map-assoc-ir/function",
  "kotoba:typed/map-assoc-ri/function",
  "kotoba:typed/map-assoc-rr/function",
  "kotoba:typed/map-dissoc-i64/function",
  "kotoba:typed/map-dissoc-ref/function",
  "kotoba:typed/string-concat/function",
  "kotoba:typed/string-substring/function",
  "kotoba:typed/string-replace-all/function",
  "kotoba:typed/string-contains/function",
  "kotoba:typed/string-split-count/function",
  "kotoba:typed/string-code-point-at/function",
  "kotoba:typed/string-fold-case/function",
  "kotoba:typed/string-upper/function",
  "kotoba:typed/keyword-name/function",
  "kotoba:typed/string-index-new/function",
  "kotoba:typed/string-index-contains/function",
  "kotoba:typed/string-index-get/function",
  "kotoba:typed/string-index-assoc/function",
  "kotoba:typed/disjoint-set-i64-new/function",
  "kotoba:typed/disjoint-set-i64-union/function",
  "kotoba:typed/document-null/function",
  "kotoba:typed/document-bool/function",
  "kotoba:typed/document-i64/function",
  "kotoba:typed/document-f64/function",
  "kotoba:typed/document-string/function",
  "kotoba:typed/document-keyword/function",
  "kotoba:typed/document-symbol/function",
  "kotoba:typed/document-kind/function",
  "kotoba:typed/document-sha256/function",
  "kotoba:typed/document-print/function",
  "kotoba:typed/document-read/function",
  "kotoba:typed/document-edn-print/function",
  "kotoba:typed/document-edn-read/function",
  "kotoba:typed/document-contains/function",
  "kotoba:typed/document-set-contains/function",
  "kotoba:typed/document-vector-at/function",
  "kotoba:typed/document-list-at/function",
  "kotoba:typed/document-map-entry-at/function",
  "kotoba:typed/document-vector-assoc/function",
  "kotoba:typed/document-vector-conj/function",
  "kotoba:typed/document-vector-drop/function",
  "kotoba:typed/document-vector-remove/function",
  "kotoba:typed/document-get/function",
  "kotoba:typed/document-assoc/function",
  "kotoba:typed/document-dissoc/function",
  "kotoba:typed/document-merge/function",
  "kotoba:typed/document-string-value/function",
  "kotoba:typed/document-keyword-value/function",
  "kotoba:typed/document-symbol-value/function",
  "kotoba:typed/document-bool-value/function",
  "kotoba:typed/document-i64-value/function",
  "kotoba:typed/document-f64-value/function",
  "kotoba:typed/keyword-from-string/function",
  "kotoba:typed/symbol-from-string/function",
  "kotoba:typed/cap-call/function",
  "kotoba:typed/xml-path-count/function",
  "kotoba:typed/xml-name-count/function",
  "kotoba:typed/xml-name-text/function",
  "kotoba:typed/xml-path-text/function",
  "kotoba:typed/xml-path-attr/function",
  "kotoba:typed/decimal-f64-parse/function",
  "kotoba:typed/decimal-f64x3-parse/function"
]);

export class KotobaHostError extends Error {
  constructor(code, message, cause) {
    super(message, cause === undefined ? undefined : { cause });
    this.name = "KotobaHostError";
    this.code = code;
  }
}

function reject(code, message, cause) {
  throw new KotobaHostError(code, message, cause);
}

function exactOptions(options) {
  if (options === undefined) return {};
  if (options === null || typeof options !== "object" || Array.isArray(options))
    reject("invalid-options", "browser host options must be an object");
  const allowed = new Set(["allowCapabilities", "capCall", "typedCapCall", "expectedSha256"]);
  for (const key of Object.keys(options))
    if (!allowed.has(key)) reject("invalid-options", `unknown browser host option: ${key}`);
  return options;
}

function admittedCapabilities(value = []) {
  if (!Array.isArray(value) || value.length > 256)
    reject("invalid-policy", "allowCapabilities must be a bounded array");
  const result = new Set();
  for (const id of value) {
    if (!Number.isInteger(id) || id < 0 || id > 255 || result.has(id))
      reject("invalid-policy", "capability ids must be unique integers in [0,255]");
    result.add(id);
  }
  return result;
}

function copiedBytes(source) {
  let view;
  if (source instanceof ArrayBuffer) view = new Uint8Array(source);
  else if (ArrayBuffer.isView(source)) view = new Uint8Array(source.buffer, source.byteOffset, source.byteLength);
  else reject("invalid-module", "Wasm source must be an ArrayBuffer or typed-array view");
  if (view.byteLength < 8 || view.byteLength > MAX_MODULE_BYTES)
    reject("invalid-module", "Wasm source is outside the admitted byte limit");
  return new Uint8Array(view);
}

async function sha256(bytes) {
  if (!globalThis.crypto?.subtle) reject("crypto-unavailable", "Web Crypto SHA-256 is required");
  const digest = new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes));
  return Array.from(digest, byte => byte.toString(16).padStart(2, "0")).join("");
}

function validateDigest(value) {
  if (value !== undefined && (typeof value !== "string" || !/^[0-9a-f]{64}$/.test(value)))
    reject("invalid-digest", "expectedSha256 must be a lowercase SHA-256 digest");
}

function parseTypedMetadata(module) {
  const sections = WebAssembly.Module.customSections(module, TYPED_SECTION);
  if (sections.length === 0) return null;
  if (sections.length !== 1) reject("invalid-typed-metadata", "typed ABI section must be unique");
  const bytes = new Uint8Array(sections[0]);
  let offset = 0;
  let nodes = 0;
  const byte = () => {
    if (offset >= bytes.length) reject("invalid-typed-metadata", "truncated typed ABI section");
    return bytes[offset++];
  };
  const uleb = () => {
    let value = 0;
    let shift = 0;
    for (let index = 0; index < 5; index += 1) {
      const current = byte();
      value += (current & 0x7f) * (2 ** shift);
      if ((current & 0x80) === 0) return value;
      shift += 7;
    }
    reject("invalid-typed-metadata", "oversized typed ABI integer");
  };
  const text = (allowEmpty = false) => {
    const length = uleb();
    if (length > 4096 || offset + length > bytes.length)
      reject("invalid-typed-metadata", "invalid typed ABI text length");
    let decoded;
    try { decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(offset, offset + length)); }
    catch (error) { reject("invalid-typed-metadata", "typed ABI text is not UTF-8", error); }
    offset += length;
    if (!allowEmpty && decoded.length === 0)
      reject("invalid-typed-metadata", "typed ABI names must be non-empty");
    return decoded;
  };
  const descriptor = depth => {
    nodes += 1;
    if (depth > 8 || nodes > 64)
      reject("invalid-typed-metadata", "typed ABI descriptor budget exceeded");
    const tag = byte();
    if (tag <= 3) return Object.freeze(["i64", "string", "keyword", "bool"][tag]);
    if (tag === 11) return Object.freeze(["vector-i64"]);
    if (tag === 12) return "f64";
    if (tag === 13) return "f32";
    if (tag === 14) return Object.freeze(["vector-f64"]);
    if (tag === 15) return Object.freeze(["ref", text()]);
    if (tag === 16 && version >= 10) return Object.freeze(["string-index"]);
    if (tag === 17 && version >= 10) return Object.freeze(["disjoint-set-i64"]);
    if (tag === 18 && version >= 11) return Object.freeze(["document"]);
    if (tag === 19 && version >= 12) return "symbol";
    if (tag === 20 && version >= 13)
      return Object.freeze(["list", descriptor(depth + 1)]);
    if (tag === 21 && version >= 14) return "bytes";
    if (tag === 4) return Object.freeze(["option", descriptor(depth + 1)]);
    if (tag === 5) return Object.freeze(["result", descriptor(depth + 1), descriptor(depth + 1)]);
    if (tag === 7) {
      const count = uleb();
      if (count > 32) reject("invalid-typed-metadata", "typed vector descriptor is oversized");
      return Object.freeze(["vector", Object.freeze(Array.from({ length: count }, () => descriptor(depth + 1)))]);
    }
    if (tag === 8) return Object.freeze(["set", descriptor(depth + 1)]);
    if (tag === 10) return Object.freeze(["map", descriptor(depth + 1), descriptor(depth + 1)]);
    if (tag === 6 || tag === 9) {
      const name = text();
      const count = uleb();
      if (count < 1 || count > 32)
        reject("invalid-typed-metadata", "named typed descriptor member count is invalid");
      const seen = new Set();
      const members = [];
      for (let index = 0; index < count; index += 1) {
        const member = text();
        if (seen.has(member)) reject("invalid-typed-metadata", "typed descriptor members must be unique");
        seen.add(member);
        members.push(Object.freeze([member, descriptor(depth + 1)]));
      }
      return Object.freeze([tag === 6 ? "variant" : "record", name, Object.freeze(members)]);
    }
    reject("invalid-typed-metadata", "unknown typed ABI descriptor tag");
  };
  const version = byte();
  // Every version from MIN_TYPED_ABI_VERSION to the current one is supported, so
  // say that rather than enumerating them. The enumeration had gone wrong: it
  // listed 5..11 explicitly plus TYPED_ABI_VERSION, so when that constant moved
  // 12 -> 13 for the list ABI, version 12 -- the symbol ABI -- stopped being
  // accepted and every module emitting a symbol failed to instantiate with
  // "unsupported Wasm typed ABI version". A range cannot develop that hole.
  if (version < MIN_TYPED_ABI_VERSION || version > TYPED_ABI_VERSION)
    reject("unsupported-typed-abi", "unsupported Wasm typed ABI version");
  const count = uleb();
  if (count > MAX_TYPED_DESCRIPTORS)
    reject("invalid-typed-metadata", "too many typed ABI descriptors");
  const descriptors = Array.from({ length: count }, () => {
    nodes = 0;
    return descriptor(1);
  });
  const literalCount = uleb();
  if (literalCount > 256) reject("invalid-typed-metadata", "too many typed ABI literals");
  const literals = [];
  for (let index = 0; index < literalCount; index += 1) {
    const tag = byte();
    if (tag === 0) literals.push(Object.freeze(["string", text(true)]));
    else if (tag === 1) literals.push(Object.freeze(["keyword", text()]));
    else if (tag === 2 || tag === 3) literals.push(Object.freeze(["bool", tag === 3]));
    else reject("invalid-typed-metadata", "unknown typed ABI literal tag");
  }
  const schemas = new Map();
  const contracts = new Map();
  if (version >= 9) {
    const schemaCount = uleb();
    if (schemaCount > 32) reject("invalid-typed-metadata", "too many application schemas");
    for (let index = 0; index < schemaCount; index += 1) {
      const name = text();
      const digest = text();
      if (!/^:[^/\s]+\/[^\s]+$/u.test(name) || !/^[0-9a-f]{64}$/u.test(digest) || schemas.has(name))
        reject("invalid-typed-metadata", "invalid or duplicate application schema identity");
      nodes = 0;
      schemas.set(name, Object.freeze({ digest, descriptor: descriptor(1) }));
    }
    const contractCount = uleb();
    if (contractCount > 256) reject("invalid-typed-metadata", "too many typed capability contracts");
    for (let index = 0; index < contractCount; index += 1) {
      const id = uleb();
      const request = uleb();
      const result = uleb();
      if (id > 255 || request >= descriptors.length || result >= descriptors.length || contracts.has(id))
        reject("invalid-typed-metadata", "invalid or duplicate typed capability contract");
      contracts.set(id, Object.freeze({ request, result }));
    }
  }
  if (offset !== bytes.length) reject("invalid-typed-metadata", "trailing typed ABI metadata rejected");
  return Object.freeze({
    version,
    descriptors: Object.freeze(descriptors),
    literals: Object.freeze(literals),
    schemas,
    contracts
  });
}

function parseCompatibility(module) {
  const sections = WebAssembly.Module.customSections(module, COMPATIBILITY_SECTION);
  if (sections.length === 0)
    reject("missing-compatibility", "Kotoba compatibility metadata is required");
  if (sections.length !== 1)
    reject("invalid-compatibility", "compatibility section must be unique");
  const bytes = new Uint8Array(sections[0]);
  let offset = 0;
  const byte = () => {
    if (offset >= bytes.length) reject("invalid-compatibility", "truncated compatibility section");
    return bytes[offset++];
  };
  const uleb = () => {
    let value = 0;
    for (let shift = 0; shift <= 28; shift += 7) {
      const part = byte();
      value |= (part & 0x7f) << shift;
      if ((part & 0x80) === 0) return value;
    }
    reject("invalid-compatibility", "oversized compatibility length");
  };
  const text = () => {
    const length = uleb();
    if (length === 0 || length > 256 || offset + length > bytes.length)
      reject("invalid-compatibility", "invalid compatibility text length");
    let value;
    try { value = new TextDecoder("utf-8", { fatal: true }).decode(bytes.slice(offset, offset + length)); }
    catch (error) { reject("invalid-compatibility", "compatibility text is not UTF-8", error); }
    offset += length;
    return value;
  };
  if (byte() !== COMPATIBILITY_VERSION)
    reject("unsupported-compatibility", "unsupported compatibility version");
  const names = ["compiler", "language", "kir", "target", "runtime", "valueAbi", "tenderRole", "tenderContract"];
  const result = Object.fromEntries(names.map(name => [name, text()]));
  if (offset !== bytes.length)
    reject("invalid-compatibility", "trailing compatibility metadata rejected");
  if (result.compiler !== "kotoba-compiler/1" || result.language !== "kotoba.language/safe-v1" ||
      result.tenderRole !== "kototama/component-tender-v1" ||
      result.tenderContract !== "kotoba.capability-host/v1")
    reject("compatibility-mismatch", "compiler, language, or tender contract is unsupported");
  if (!["kotoba-capability-host-v1", "kotoba-browser-host-v1", "kotoba-wasi-host-v1"].includes(result.runtime))
    reject("compatibility-mismatch", "runtime compatibility identity is unsupported");
  return Object.freeze({ version: COMPATIBILITY_VERSION, ...result });
}

function validateModule(module) {
  for (const entry of WebAssembly.Module.imports(module)) {
    const identity = `${entry.module}/${entry.name}/${entry.kind}`;
    if (!ALLOWED_IMPORTS.has(identity))
      reject("forbidden-import", `Wasm import is outside the Kotoba browser profile: ${identity}`);
  }
  const exports = WebAssembly.Module.exports(module);
  if (!exports.some(entry => entry.name === "main" && entry.kind === "function"))
    reject("invalid-module", "Kotoba browser module must export a main function");
  if (exports.some(entry => entry.kind === "memory" || entry.kind === "table" || entry.kind === "global"))
    reject("forbidden-export", "Kotoba browser module may export functions only");
  return Object.freeze({ typedAbi: parseTypedMetadata(module), compatibility: parseCompatibility(module) });
}

function createHeap() {
  const cells = [];
  const checked = handle => {
    if (typeof handle !== "bigint" || handle <= 0n || handle > BigInt(cells.length))
      reject("invalid-pair-handle", "invalid immutable pair handle");
    return cells[Number(handle - 1n)];
  };
  return {
    imports: Object.freeze({
      pair(first, second) {
        if (cells.length >= PAIR_CAPACITY) reject("heap-exhausted", "immutable pair arena exhausted");
        cells.push(Object.freeze([BigInt.asIntN(64, first), BigInt.asIntN(64, second)]));
        return BigInt(cells.length);
      },
      "pair-first"(handle) { return checked(handle)[0]; },
      "pair-second"(handle) { return checked(handle)[1]; }
    }),
    report() { return Object.freeze({ capacity: PAIR_CAPACITY, used: cells.length }); }
  };
}

function createTypedRuntime(abi, typedCapCall, allow) {
  if (abi === null) return null;
  // Copy mutable Map containers before exposing parsed metadata to callers.
  // Runtime authority must remain sealed even if a consumer mutates the
  // diagnostic `typedAbi.schemas` or `typedAbi.contracts` maps.
  const schemaTable = new Map(abi.schemas ?? []);
  const contractTable = new Map(abi.contracts ?? []);
  const builders = new WeakSet();
  const trustedDescriptors = new WeakSet();
  const trustedValues = new WeakSet();
  // Arrays a LINEAR handle owns, which `vector-assoc-in-place-i64` writes
  // through instead of copying.
  //
  // Every other compound value is frozen, and the freeze is what makes
  // `assertValue` mean something: a value validated once must not become a
  // different value afterwards, or the check happened on something nobody
  // holds any more. That argument needs the value to be REACHABLE from more
  // than one place, and a linear one is not -- the frontend refuses
  // `vector-assoc!` unless the handle is dead after the write
  // (`kotoba.compiler.affine`, superproject ADR-2609010200), so there is no
  // second reference for a mutation to surprise.
  //
  // What this gives up, stated: a module NOT produced by this compiler can
  // import `vector-assoc-in-place-i64` and mutate a value another handle
  // points to. It cannot reach anything outside the guest -- no host object
  // is exposed -- so the blast radius is the guest's own data, which is the
  // same radius as any other way a guest can compute the wrong answer. The
  // frozen default stays for everything else.
  const linearValues = new WeakSet();
  // How many items one vector may hold.
  //
  // 16,384 while every element write copied the whole vector: a bigger vector
  // only bought a bigger copy, so raising it would have made programs slower
  // rather than possible. In-place writes remove that, and the scan skip above
  // removes the other O(length) per operation, so the number can now be set by
  // what the guest needs instead of by what a copy costs.
  //
  // 1,048,576 because that is `torihiki.book`'s default `cap` -- a struct of
  // arrays with a slot per resting order (superproject ADR-2609010200). Chosen
  // against a real program rather than rounded up: a limit nobody's workload
  // explains is a limit nobody can argue with when it is wrong.
  //
  // Still a limit, and still fail-closed. An i64 array of this length is 8 MB
  // per field, which is a real cost a host must be willing to pay, and a guest
  // that asks for more is refused rather than allowed to exhaust the host.
  // 2026-09-01: back to 16384, matching kotoba.kir.value/vector-item-limit.
  // A host that admits a million while the compiler refuses past 16,384 is
  // not more permissive, it is a second bound nobody reads -- the guest is
  // already refused before it arrives, so this one never fires and stops
  // being evidence of anything. Raise both, the native arena and amu's
  // component test together.
  const VECTOR_ITEM_BUDGET = 16384;
  // How many vector items one instance may allocate IN TOTAL.
  //
  // The per-vector budget bounds one value; this bounds the instance. Without
  // it a guest calls `vector-alloc` in a loop and takes 128 KB per call for as
  // long as it likes. It mattered more when one vector could be a million
  // items; it is still the only thing bounding the instance rather than the
  // value.
  //
  // TOTAL, not live: nothing here is freed, and calling it a live budget would
  // promise a reclamation that does not exist. The native arena is bump-only
  // for the same reason, and an instance is the unit that goes away.
  //
  // Eight of the largest vector, because a struct of arrays is several fields
  // over one slot count and `torihiki.book` has more than one. A ninth is
  // refused rather than allowed to exhaust the host.
  const VECTOR_TOTAL_ITEM_BUDGET = VECTOR_ITEM_BUDGET * 8;
  let vectorItemsAllocated = 0;
  const trustDescriptor = descriptor => {
    if (!Array.isArray(descriptor) || trustedDescriptors.has(descriptor)) return;
    trustedDescriptors.add(descriptor);
    for (const item of descriptor) trustDescriptor(item);
  };
  abi.descriptors.forEach(trustDescriptor);
  for (const schema of schemaTable.values()) trustDescriptor(schema.descriptor);
  const resolveDescriptor = descriptor => {
    if (!Array.isArray(descriptor) || descriptor[0] !== "ref") return descriptor;
    const schema = schemaTable.get(descriptor[1]);
    if (schema === undefined)
      reject("invalid-typed-descriptor", "schema reference is outside the sealed table");
    return schema.descriptor;
  };
  const descriptorAt = id => {
    if (!Number.isInteger(id) || id < 0 || id >= abi.descriptors.length)
      reject("invalid-typed-descriptor", "typed descriptor index is out of range");
    return abi.descriptors[id];
  };
  const literalAt = id => {
    if (!Number.isInteger(id) || id < 0 || id >= abi.literals.length)
      reject("invalid-typed-literal", "typed literal index is out of range");
    return abi.literals[id][1];
  };
  const i64 = value => {
    if (typeof value !== "bigint" || BigInt.asIntN(64, value) !== value)
      reject("invalid-typed-value", "typed i64 value is invalid");
    return value;
  };
  const f64 = value => {
    if (typeof value !== "number")
      reject("invalid-typed-value", "typed f64 value is invalid");
    return Number.isNaN(value) ? Number.NaN : value;
  };
  const f32 = value => {
    if (typeof value !== "number" || !Object.is(Math.fround(value), value))
      reject("invalid-typed-value", "typed f32 value is invalid");
    return Number.isNaN(value) ? Number.NaN : value;
  };
  const utf8Length = value => {
    if (typeof value !== "string") reject("invalid-typed-value", "typed string is invalid");
    for (let index = 0; index < value.length; index += 1) {
      const unit = value.charCodeAt(index);
      if (unit >= 0xd800 && unit <= 0xdbff) {
        const next = value.charCodeAt(index + 1);
        if (!(next >= 0xdc00 && next <= 0xdfff))
          reject("invalid-typed-value", "typed string has an unpaired high surrogate");
        index += 1;
      } else if (unit >= 0xdc00 && unit <= 0xdfff) {
        reject("invalid-typed-value", "typed string has an unpaired low surrogate");
      }
    }
    return new TextEncoder().encode(value).byteLength;
  };
  const documentDescriptor = abi.descriptors.find(descriptor =>
    Array.isArray(descriptor) && descriptor[0] === "document");
  const copyDocument = (source, allowShared = false) => {
    const state = { nodes: 0, bytes: 0, seen: new WeakSet(), active: new WeakSet() };
    const text = (value, keyword = false) => {
      if (typeof value !== "string" || (keyword && !value.startsWith(":")))
        reject("invalid-typed-value", keyword ? "document keyword is invalid" : "document string is invalid");
      const size = utf8Length(value);
      if (size > (keyword ? 512 : 65536))
        reject("invalid-typed-value", "document scalar text is oversized");
      state.bytes += size;
      if (state.bytes > 65536) reject("invalid-typed-value", "document UTF-8 budget exceeded");
      return value;
    };
    const walk = (node, depth) => {
      state.nodes += 1;
      if (depth > 8 || state.nodes > 256)
        reject("invalid-typed-value", "document depth or node budget exceeded");
      if (!Array.isArray(node) || Object.getPrototypeOf(node) !== Array.prototype ||
          (!allowShared && state.seen.has(node)))
        reject("invalid-typed-value", "document must be an acyclic unshared array tree");
      if (state.active.has(node))
        reject("invalid-typed-value", "document must be acyclic");
      state.seen.add(node);
      state.active.add(node);
      const finish = value => { state.active.delete(node); return value; };
      const tag = node[0];
      if (tag === "null" && node.length === 1) return finish(Object.freeze(["null"]));
      if (node.length !== 2 || typeof tag !== "string")
        reject("invalid-typed-value", "document node shape is invalid");
      const payload = node[1];
      if (tag === "bool") {
        if (typeof payload !== "boolean") reject("invalid-typed-value", "document bool is invalid");
        return finish(Object.freeze([tag, payload]));
      }
      if (tag === "i64") return finish(Object.freeze([tag, i64(payload)]));
      if (tag === "f64") {
        if (typeof payload !== "number" || !Number.isFinite(payload))
          reject("invalid-typed-value", "document f64 must be finite");
        return finish(Object.freeze([tag, payload]));
      }
      if (tag === "string") return finish(Object.freeze([tag, text(payload)]));
      if (tag === "keyword") return finish(Object.freeze([tag, text(payload, true)]));
      if (tag === "symbol") {
        if (typeof payload !== "string" || payload.length === 0 ||
            /[\s,\[\]{}()"',;`~^\\]/u.test(payload) || utf8Length(payload) > 512)
          reject("invalid-typed-value", "document symbol is invalid");
        return finish(Object.freeze([tag, text(payload)]));
      }
      if (tag === "vector" || tag === "list") {
        if (!Array.isArray(payload) || Object.getPrototypeOf(payload) !== Array.prototype || payload.length > 32)
          reject("invalid-typed-value", "document sequence is invalid or oversized");
        if (!allowShared && state.seen.has(payload))
          reject("invalid-typed-value", "document arrays cannot be shared");
        state.seen.add(payload);
        return finish(Object.freeze([tag, Object.freeze(payload.map(item => walk(item, depth + 1)))]));
      }
      if (tag === "set") {
        if (!Array.isArray(payload) || Object.getPrototypeOf(payload) !== Array.prototype || payload.length > 32)
          reject("invalid-typed-value", "document set is invalid or oversized");
        if (!allowShared && state.seen.has(payload))
          reject("invalid-typed-value", "document arrays cannot be shared");
        state.seen.add(payload);
        const items = payload.map(item => walk(item, depth + 1));
        for (let index = 1; index < items.length; index += 1)
          if (compareDocument(items[index - 1], items[index], false) >= 0)
            reject("invalid-typed-value", "document set items are duplicate or noncanonical");
        return finish(Object.freeze([tag, Object.freeze(items)]));
      }
      if (tag === "map") {
        if (!Array.isArray(payload) || Object.getPrototypeOf(payload) !== Array.prototype || payload.length > 32)
          reject("invalid-typed-value", "document map is invalid or oversized");
        if (!allowShared && state.seen.has(payload))
          reject("invalid-typed-value", "document arrays cannot be shared");
        state.seen.add(payload);
        let previous = null;
        const entries = payload.map(entry => {
          if (!Array.isArray(entry) || Object.getPrototypeOf(entry) !== Array.prototype ||
              entry.length !== 2 || (!allowShared && state.seen.has(entry)))
            reject("invalid-typed-value", "document map entry is invalid or shared");
          state.seen.add(entry);
          let key;
          if (typeof entry[0] === "string") key = Object.freeze(["keyword", text(entry[0], true)]);
          else if (Array.isArray(entry[0]) && Object.getPrototypeOf(entry[0]) === Array.prototype &&
                   entry[0].length === 2 && entry[0][0] === "keyword") {
            if (!allowShared && state.seen.has(entry[0]))
              reject("invalid-typed-value", "document arrays cannot be shared");
            state.seen.add(entry[0]);
            key = Object.freeze(["keyword", text(entry[0][1], true)]);
          } else key = walk(entry[0], depth + 1);
          if (previous !== null && compareDocumentMapKey(previous, key, false) >= 0)
            reject("invalid-typed-value", "document map keys are duplicate or noncanonical");
          previous = key;
          return Object.freeze([key, walk(entry[1], depth + 1)]);
        });
        return finish(Object.freeze([tag, Object.freeze(entries)]));
      }
      reject("invalid-typed-value", "unknown document tag");
    };
    return walk(source, 0);
  };
  const admitDocument = (source, allowShared = false) => {
    if (documentDescriptor === undefined)
      reject("invalid-typed-operation", "document descriptor is absent");
    const result = copyDocument(source, allowShared);
    const trust = node => {
      trustedValues.add(node);
      if (node[0] === "vector" || node[0] === "list" || node[0] === "set") node[1].forEach(trust);
      else if (node[0] === "map") node[1].forEach(entry => { trust(entry[0]); trust(entry[1]); });
    };
    trust(result);
    return result;
  };
  const constructDocument = source => admitDocument(source, true);
  const assertDocument = value => {
    if (!Array.isArray(value) || !Object.isFrozen(value) || !trustedValues.has(value))
      reject("invalid-typed-value", "forged document value rejected");
    return value;
  };
  // Shared with kotoba-kir value/document-canonical-bytes + kotoba-script docCanonicalBytes.
  // Format: n | b t/f | i <decimal> ; | f <i64-bits-decimal> ; |
  // s <utf8-len> : <bytes> | k <utf8-len> : <keyword-str> | y <utf8-len> : <symbol> |
  // v <count> : <items...> | l <count> : <items...> | e <count> : <items...> |
  // m <count> : ((K <keyword-len> : <keyword-bytes> | D <document-key>) <item>)*
  const documentCanonicalBytes = (node, admitted = true) => {
    const out = [];
    const enc = new TextEncoder();
    const emit = n => out.push(n & 255);
    const emitStr = s => { for (const x of enc.encode(s)) emit(x); };
    const emitLenStr = s => {
      const b = enc.encode(s);
      emitStr(String(b.length));
      emit(58);
      for (const x of b) emit(x);
    };
    const walk = n => {
      n = admitted ? assertDocument(n) : n;
      const t = n[0];
      if (t === "null") { emit(110); return; }
      if (t === "bool") { emit(98); emit(n[1] ? 116 : 102); return; }
      if (t === "i64") { emit(105); emitStr(String(n[1])); emit(59); return; }
      if (t === "f64") {
        const v = Object.is(n[1], -0) ? 0 : n[1];
        const buf = new ArrayBuffer(8);
        const dv = new DataView(buf);
        dv.setFloat64(0, v, true);
        emit(102);
        emitStr(String(dv.getBigInt64(0, true)));
        emit(59);
        return;
      }
      if (t === "string") { emit(115); emitLenStr(n[1]); return; }
      if (t === "keyword") { emit(107); emitLenStr(String(n[1])); return; }
      if (t === "symbol") { emit(121); emitLenStr(String(n[1])); return; }
      if (t === "vector") {
        emit(118); emitStr(String(n[1].length)); emit(58);
        for (const it of n[1]) walk(it);
        return;
      }
      if (t === "list") {
        emit(108); emitStr(String(n[1].length)); emit(58);
        for (const it of n[1]) walk(it);
        return;
      }
      if (t === "set") {
        emit(101); emitStr(String(n[1].length)); emit(58);
        for (const it of n[1]) walk(it);
        return;
      }
      if (t === "map") {
        emit(109); emitStr(String(n[1].length)); emit(58);
        for (const e of n[1]) {
          if (e[0][0] === "keyword") { emit(75); emitLenStr(String(e[0][1])); }
          else { emit(68); walk(e[0]); }
          walk(e[1]);
        }
        return;
      }
      reject("invalid-typed-value", "unknown document tag in canonical encoding");
    };
    walk(node);
    return new Uint8Array(out);
  };
  const documentSha256Hex = node => {
    // Pure sync SHA-256 (Web Crypto is async; wasm typed imports are sync).
    const K = new Uint32Array([
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ]);
    let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
    let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
    const bytes = documentCanonicalBytes(node);
    const l = bytes.length;
    const bitLen = l * 8;
    const withOne = new Uint8Array((l + 9 + 63) & ~63);
    withOne.set(bytes);
    withOne[l] = 0x80;
    const dv = new DataView(withOne.buffer);
    dv.setUint32(withOne.length - 4, bitLen >>> 0, false);
    dv.setUint32(withOne.length - 8, Math.floor(bitLen / 0x100000000), false);
    const rotr = (x, n) => ((x >>> n) | (x << (32 - n))) >>> 0;
    const w = new Uint32Array(64);
    for (let i = 0; i < withOne.length; i += 64) {
      for (let j = 0; j < 16; j++) w[j] = dv.getUint32(i + j * 4, false);
      for (let j = 16; j < 64; j++) {
        const s0 = rotr(w[j - 15], 7) ^ rotr(w[j - 15], 18) ^ (w[j - 15] >>> 3);
        const s1 = rotr(w[j - 2], 17) ^ rotr(w[j - 2], 19) ^ (w[j - 2] >>> 10);
        w[j] = (w[j - 16] + s0 + w[j - 7] + s1) >>> 0;
      }
      let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
      for (let j = 0; j < 64; j++) {
        const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const ch = (e & f) ^ ((~e) & g);
        const t1 = (h + S1 + ch + K[j] + w[j]) >>> 0;
        const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + maj) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0;
      h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0;
    }
    const out = new Uint8Array(32);
    const ov = new DataView(out.buffer);
    [h0, h1, h2, h3, h4, h5, h6, h7].forEach((x, i) => ov.setUint32(i * 4, x, false));
    return Array.from(out).map(b => b.toString(16).padStart(2, "0")).join("");
  };
  const bytesToHex = bytes => Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
  const hexToBytes = s => {
    if (typeof s !== "string") reject("invalid-typed-value", "document-read requires a string");
    if (s.length % 2) reject("invalid-typed-value", "document-read hex length must be even");
    if (s.length > 1048576) reject("invalid-typed-value", "document-read hex exceeds size limit");
    if (!/^[0-9a-f]*$/.test(s)) reject("invalid-typed-value", "document-read hex must be lowercase [0-9a-f]");
    const out = new Uint8Array(s.length / 2);
    for (let i = 0; i < out.length; i++) out[i] = parseInt(s.substr(i * 2, 2), 16);
    return out;
  };
  const documentFromCanonicalBytes = bytes => {
    let i = 0;
    const len = bytes.length;
    const take = () => {
      if (i >= len) reject("invalid-typed-value", "document-read truncated encoding");
      return bytes[i++];
    };
    const takeUntil = sep => {
      const start = i;
      while (i < len && bytes[i] !== sep) i++;
      if (i >= len) reject("invalid-typed-value", "document-read missing terminator");
      const s = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(start, i));
      i++;
      return s;
    };
    const takeLenStr = () => {
      const n = Number(takeUntil(58));
      if (!Number.isInteger(n) || n < 0 || n > 65536)
        reject("invalid-typed-value", "document-read string length out of range");
      if (i + n > len) reject("invalid-typed-value", "document-read truncated string payload");
      const s = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(i, i + n));
      i += n;
      return s;
    };
    const walk = () => {
      const tag = take();
      if (tag === 110) return Object.freeze(["null"]);
      if (tag === 98) {
        const b = take();
        if (b === 116) return Object.freeze(["bool", true]);
        if (b === 102) return Object.freeze(["bool", false]);
        reject("invalid-typed-value", "document-read invalid bool");
      }
      if (tag === 105) return Object.freeze(["i64", BigInt(takeUntil(59))]);
      if (tag === 102) {
        const bits = BigInt(takeUntil(59));
        const buf = new ArrayBuffer(8);
        const dv = new DataView(buf);
        dv.setBigInt64(0, bits, true);
        return Object.freeze(["f64", dv.getFloat64(0, true)]);
      }
      if (tag === 115) return Object.freeze(["string", takeLenStr()]);
      if (tag === 107) {
        const k = takeLenStr();
        if (!k.startsWith(":")) reject("invalid-typed-value", "document-read keyword must start with colon");
        return Object.freeze(["keyword", k]);
      }
      if (tag === 121) return Object.freeze(["symbol", takeLenStr()]);
      if (tag === 118) {
        const n = Number(takeUntil(58));
        if (!Number.isInteger(n) || n < 0 || n > 32)
          reject("invalid-typed-value", "document-read vector count out of range");
        const items = [];
        for (let k = 0; k < n; k++) items.push(walk());
        return Object.freeze(["vector", Object.freeze(items)]);
      }
      if (tag === 108) {
        const n = Number(takeUntil(58));
        if (!Number.isInteger(n) || n < 0 || n > 32)
          reject("invalid-typed-value", "document-read list count out of range");
        const items = [];
        for (let k = 0; k < n; k++) items.push(walk());
        return Object.freeze(["list", Object.freeze(items)]);
      }
      if (tag === 101) {
        const n = Number(takeUntil(58));
        if (!Number.isInteger(n) || n < 0 || n > 32)
          reject("invalid-typed-value", "document-read set count out of range");
        const items = [];
        for (let k = 0; k < n; k++) items.push(walk());
        return Object.freeze(["set", Object.freeze(items)]);
      }
      if (tag === 109) {
        const n = Number(takeUntil(58));
        if (!Number.isInteger(n) || n < 0 || n > 32)
          reject("invalid-typed-value", "document-read map count out of range");
        const entries = [];
        for (let k = 0; k < n; k++) {
          const marker = take();
          let key;
          if (marker === 75) {
            const ks = takeLenStr();
            if (!ks.startsWith(":")) reject("invalid-typed-value", "document-read map keyword key is invalid");
            key = Object.freeze(["keyword", ks]);
          } else if (marker === 68) key = walk();
          else reject("invalid-typed-value", "document-read map entry has invalid key marker");
          entries.push(Object.freeze([key, walk()]));
        }
        return Object.freeze(["map", Object.freeze(entries)]);
      }
      reject("invalid-typed-value", "document-read unknown tag");
    };
    const doc = walk();
    if (i !== len) reject("invalid-typed-value", "document-read trailing bytes");
    // Newly decoded trees must be admitted into the trustedValues set.
    return constructDocument(doc);
  };
  const documentPrint = node => {
    const hex = bytesToHex(documentCanonicalBytes(assertDocument(node)));
    if (hex.length > 65536) reject("invalid-typed-value", "document-print exceeds string byte limit");
    return hex;
  };
  const documentRead = s => {
    if (typeof s !== "string") reject("invalid-typed-value", "document-read requires a string");
    if (s.length > 65536) reject("invalid-typed-value", "document-read string exceeds byte limit");
    return documentFromCanonicalBytes(hexToBytes(s));
  };
  const documentEdnPrint = value => {
    const symbolText = symbol => {
      if (symbol === "nil" || symbol === "true" || symbol === "false" ||
          symbol.startsWith(":") || symbol.startsWith("#") ||
          /^[+-]?[0-9]+$/u.test(symbol) ||
          /^[+-]?(?:(?:[0-9]+\.[0-9]*)|(?:[0-9]*\.[0-9]+)|(?:[0-9]+[eE][+-]?[0-9]+))(?:[eE][+-]?[0-9]+)?$/u.test(symbol))
        reject("invalid-typed-value", "ambiguous document symbol cannot be printed as EDN");
      return symbol;
    };
    const walk = node => {
      node = assertDocument(node);
      const [tag, payload] = node;
      if (tag === "null") return "nil";
      if (tag === "bool") return payload ? "true" : "false";
      if (tag === "i64") return String(payload);
      if (tag === "f64") {
        if (!Number.isFinite(payload)) reject("invalid-typed-value", "non-finite document f64");
        const text = String(payload);
        return /[.eE]/u.test(text) ? text : `${text}.0`;
      }
      if (tag === "string") return JSON.stringify(payload);
      if (tag === "keyword") return payload;
      if (tag === "symbol") return symbolText(payload);
      if (tag === "vector") return `[${payload.map(walk).join(" ")}]`;
      if (tag === "list") return `(${payload.map(walk).join(" ")})`;
      if (tag === "set") return `#{${payload.map(walk).join(" ")}}`;
      if (tag === "map") return `{${payload.map(([key, item]) => `${walk(key)} ${walk(item)}`).join(" ")}}`;
      reject("invalid-typed-value", "unknown document tag for EDN printer");
    };
    const output = walk(value);
    if (utf8Length(output) > 65536)
      reject("invalid-typed-value", "document-edn-print exceeds string byte limit");
    return output;
  };
  const documentEdnRead = input => {
    if (typeof input !== "string" || utf8Length(input) > 65536)
      reject("invalid-typed-value", "document-edn-read input is invalid or oversized");
    const text = input;
    let cursor = 0;
    const fail = message => reject("invalid-typed-value", `document-edn-read ${message}`);
    const whitespace = character =>
      character === " " || character === "\t" || character === "\n" ||
      character === "\r" || character === ",";
    const skip = () => {
      for (;;) {
        while (cursor < text.length && whitespace(text[cursor])) cursor += 1;
        if (text[cursor] !== ";") return;
        while (cursor < text.length && text[cursor++] !== "\n") {}
      }
    };
    const delimiter = character =>
      character === undefined || whitespace(character) || "[]{}()\";".includes(character);
    const quoted = () => {
      cursor += 1;
      let output = "";
      while (cursor < text.length) {
        const character = text[cursor++];
        if (character === "\"") return output;
        if (character === "\n" || character === "\r") fail("newline in string");
        if (character !== "\\") { output += character; continue; }
        if (cursor >= text.length) fail("truncated escape");
        const escaped = text[cursor++];
        const escapes = { b: "\b", t: "\t", n: "\n", f: "\f", r: "\r", "\"": "\"", "\\": "\\" };
        if (Object.prototype.hasOwnProperty.call(escapes, escaped)) {
          output += escapes[escaped];
          continue;
        }
        if (escaped !== "u") fail("unsupported escape");
        const hex = text.slice(cursor, cursor + 4);
        if (!/^[0-9A-Fa-f]{4}$/u.test(hex)) fail("invalid unicode escape");
        output += String.fromCharCode(Number.parseInt(hex, 16));
        cursor += 4;
      }
      fail("unterminated string");
    };
    const token = () => {
      const begin = cursor;
      while (cursor < text.length && !delimiter(text[cursor])) cursor += 1;
      if (begin === cursor) fail("expected token");
      return text.slice(begin, cursor);
    };
    const value = depth => {
      if (depth > 8) fail("depth limit exceeded");
      skip();
      const character = text[cursor];
      if (character === undefined) fail("unexpected end of input");
      if (character === "\"") return ["string", quoted()];
      if (character === "[") {
        cursor += 1;
        const items = [];
        for (;;) {
          skip();
          if (text[cursor] === "]") { cursor += 1; return ["vector", items]; }
          if (items.length >= 32) fail("vector item limit exceeded");
          items.push(value(depth + 1));
        }
      }
      if (character === "(") {
        cursor += 1;
        const items = [];
        for (;;) {
          skip();
          if (text[cursor] === ")") { cursor += 1; return ["list", items]; }
          if (items.length >= 32) fail("list item limit exceeded");
          items.push(value(depth + 1));
        }
      }
      if (character === "{") {
        cursor += 1;
        const entries = [];
        for (;;) {
          skip();
          if (text[cursor] === "}") {
            cursor += 1;
            entries.sort((left, right) => compareDocumentMapKey(left[0], right[0], false));
            for (let index = 1; index < entries.length; index += 1)
              if (compareDocumentMapKey(entries[index - 1][0], entries[index][0], false) === 0)
                fail("duplicate map key");
            return ["map", entries];
          }
          if (entries.length >= 32) fail("map entry limit exceeded");
          const key = value(depth + 1);
          skip();
          if (text[cursor] === "}") fail("map value missing");
          entries.push([key, value(depth + 1)]);
        }
      }
      if (character === "#") {
        cursor += 1;
        if (text[cursor] !== "{") fail("dispatch forms are forbidden");
        cursor += 1;
        const items = [];
        for (;;) {
          skip();
          if (text[cursor] === "}") {
            cursor += 1;
            items.sort((left, right) => compareDocument(left, right, false));
            for (let index = 1; index < items.length; index += 1)
              if (compareDocument(items[index - 1], items[index], false) === 0) fail("duplicate set item");
            return ["set", items];
          }
          if (items.length >= 32) fail("set item limit exceeded");
          items.push(value(depth + 1));
        }
      }
      if (character === ")" || character === "]" || character === "}") fail("unexpected closing delimiter");
      const item = token();
      if (item === "nil") return ["null"];
      if (item === "true") return ["bool", true];
      if (item === "false") return ["bool", false];
      if (/^[+-]?[0-9]+$/u.test(item)) {
        let parsed;
        try { parsed = BigInt(item); } catch (_) { fail("invalid i64"); }
        if (parsed < -9223372036854775808n || parsed > 9223372036854775807n) fail("i64 out of range");
        return ["i64", parsed];
      }
      if (/^[+-]?(?:(?:[0-9]+\.[0-9]*)|(?:[0-9]*\.[0-9]+)|(?:[0-9]+[eE][+-]?[0-9]+))(?:[eE][+-]?[0-9]+)?$/u.test(item)) {
        const parsed = Number(item);
        if (!Number.isFinite(parsed)) fail("invalid or non-finite f64");
        return ["f64", parsed];
      }
      if (item.length > 1 && item[0] === ":") return ["keyword", item];
      if (item[0] === ":") fail("invalid keyword");
      return ["symbol", item];
    };
    skip();
    const document = value(0);
    skip();
    if (cursor !== text.length) fail("trailing forms");
    return constructDocument(document);
  };
    const xmlName = /^[A-Za-z_][A-Za-z0-9_.:-]{0,127}$/u;
  const xmlString = value => {
    if (typeof value !== "string" || utf8Length(value) > 65536)
      reject("invalid-xml", "XML string is invalid or oversized");
    return value;
  };
  const xmlWhitespace = character =>
    character === " " || character === "\t" || character === "\n" || character === "\r";
  const normalizeXmlText = text =>
    xmlString(text.replace(/[ \t\r\n]+/gu, " ").replace(/^ | $/gu, ""));
  const parseBoundedXml = input => {
    const text = xmlString(input);
    let cursor = 0, nodes = 0;
    const output = [];
    const skip = () => { while (cursor < text.length && xmlWhitespace(text[cursor])) cursor += 1; };
    const comment = () => {
      if (!text.startsWith("<!--", cursor)) return false;
      const end = text.indexOf("-->", cursor + 4);
      if (end < 0 || text.slice(cursor + 4, end).includes("--"))
        reject("invalid-xml", "XML comment is invalid");
      cursor = end + 3;
      return true;
    };
    const comments = () => { for (;;) { skip(); if (!comment()) return; } };
    const name = () => {
      const begin = cursor;
      while (cursor < text.length && /[A-Za-z0-9_.:-]/u.test(text[cursor])) cursor += 1;
      const result = text.slice(begin, cursor);
      if (!xmlName.test(result)) reject("invalid-xml", "XML name is invalid");
      return result;
    };
    const element = (depth, parent) => {
      if (depth > 32) reject("invalid-xml", "XML depth limit exceeded");
      if (++nodes > 2048) reject("invalid-xml", "XML node limit exceeded");
      if (text[cursor] !== "<" || ["/", "!", "?"].includes(text[cursor + 1]))
        reject("invalid-xml", "XML element is invalid");
      cursor += 1;
      const tag = name();
      const path = parent ? `${parent}/${tag}` : tag;
      const attributes = Object.create(null);
      let attributeCount = 0, empty = false;
      for (;;) {
        skip();
        if (text.startsWith("/>", cursor)) { cursor += 2; empty = true; break; }
        if (text[cursor] === ">") { cursor += 1; break; }
        const attribute = name();
        if (Object.prototype.hasOwnProperty.call(attributes, attribute))
          reject("invalid-xml", "duplicate XML attribute rejected");
        if (++attributeCount > 32) reject("invalid-xml", "XML attribute limit exceeded");
        skip();
        if (text[cursor++] !== "=") reject("invalid-xml", "XML attribute is invalid");
        skip();
        const quote = text[cursor++];
        if (quote !== "\"" && quote !== "'") reject("invalid-xml", "XML attribute quote is invalid");
        const begin = cursor;
        while (cursor < text.length && text[cursor] !== quote) {
          if (text[cursor] === "<" || text[cursor] === "&")
            reject("invalid-xml", "XML entities and attribute markup are rejected");
          cursor += 1;
        }
        if (cursor >= text.length) reject("invalid-xml", "XML attribute is unterminated");
        attributes[attribute] = xmlString(text.slice(begin, cursor++));
      }
      const record = { path, attributes: Object.freeze(attributes), text: "" };
      output.push(record);
      if (empty) return "";
      const parts = [];
      for (;;) {
        if (text.startsWith("</", cursor)) {
          cursor += 2;
          const closing = name();
          skip();
          if (closing !== tag || text[cursor++] !== ">")
            reject("invalid-xml", "XML closing tag mismatch");
          record.text = normalizeXmlText(parts.join(" "));
          return record.text;
        }
        if (text.startsWith("<!--", cursor)) { comment(); parts.push(" "); continue; }
        if (text[cursor] === "<") { parts.push(element(depth + 1, path)); continue; }
        const begin = cursor;
        while (cursor < text.length && text[cursor] !== "<") cursor += 1;
        if (cursor === begin) reject("invalid-xml", "XML text is invalid");
        parts.push(text.slice(begin, cursor));
      }
    };
    comments();
    if (text.startsWith("<?xml", cursor)) {
      const end = text.indexOf("?>", cursor + 5);
      if (end < 0 || !/^<\?xml\s+version=(?:"1\.[01]"|'1\.[01]')(?:\s+encoding=(?:"(?:UTF-8|utf-8)"|'(?:UTF-8|utf-8)'))?\s*\?>$/u.test(text.slice(cursor, end + 2)))
        reject("invalid-xml", "XML declaration is invalid");
      cursor = end + 2;
    }
    comments();
    if (text.startsWith("<!DOCTYPE", cursor)) {
      const end = text.indexOf(">", cursor + 9);
      if (end < 0 || !/^<!DOCTYPE[ \t\r\n]+html[ \t\r\n]*>$/u.test(text.slice(cursor, end + 1)))
        reject("invalid-xml", "XML doctype is not the sealed XHTML5 declaration");
      cursor = end + 1;
    }
    comments(); element(1, ""); comments(); skip();
    if (cursor !== text.length) reject("invalid-xml", "XML trailing content is rejected");
    return Object.freeze(output.map(node => Object.freeze(node)));
  };
  const xmlPath = path => {
    path = xmlString(path);
    const segments = path.split("/");
    if (segments.length < 1 || segments.length > 32 || segments.some(segment => !xmlName.test(segment)))
      reject("invalid-xml", "XML path is invalid");
    return path;
  };
  const xmlCheckedName = name => {
    name = xmlString(name);
    if (!xmlName.test(name)) reject("invalid-xml", "XML element name is invalid");
    return name;
  };
  const xmlElementName = node => node.path.slice(node.path.lastIndexOf("/") + 1);
  const compareSequence = (types, left, right) => {
    const length = Math.min(left.length, right.length);
    for (let index = 0; index < length; index += 1) {
      const compared = compareValue(types[index], left[index], right[index]);
      if (compared !== 0) return compared;
    }
    return left.length < right.length ? -1 : left.length > right.length ? 1 : 0;
  };
  const compareDocument = (left, right, admitted = true) => {
    const leftBytes = documentCanonicalBytes(left, admitted), rightBytes = documentCanonicalBytes(right, admitted);
    const length = Math.min(leftBytes.length, rightBytes.length);
    for (let index = 0; index < length; index += 1) {
      if (leftBytes[index] < rightBytes[index]) return -1;
      if (leftBytes[index] > rightBytes[index]) return 1;
    }
    return leftBytes.length < rightBytes.length ? -1 : leftBytes.length > rightBytes.length ? 1 : 0;
  };
  const compareDocumentMapKey = (left, right, admitted = true) => {
    if (left[0] === "keyword" && right[0] === "keyword")
      return left[1] < right[1] ? -1 : left[1] > right[1] ? 1 : 0;
    return compareDocument(left, right, admitted);
  };
  const compareValue = (descriptor, left, right) => {
    // Resolve schema refs so set-of-record / set-of-ref elements have a
    // canonical order (T8.3 ADR 0195). assertValue already resolves; compare
    // must too or typed-set-conj of [:ref :record] rejects with
    // "typed value has no canonical order".
    descriptor = resolveDescriptor(descriptor);
    if (descriptor === "f64" || descriptor === "f32") {
      if (Number.isNaN(left) || Number.isNaN(right))
        return Number.isNaN(left) && Number.isNaN(right) ? 0 : Number.isNaN(left) ? 1 : -1;
      return left < right ? -1 : left > right ? 1 : 0;
    }
    if (descriptor === "i64" || descriptor === "string" || descriptor === "keyword" || descriptor === "symbol")
      return left < right ? -1 : left > right ? 1 : 0;
    if (descriptor === "bytes") {
      const length = Math.min(left.byteLength, right.byteLength);
      for (let index = 0; index < length; index += 1) {
        if (left[index] < right[index]) return -1;
        if (left[index] > right[index]) return 1;
      }
      return left.byteLength < right.byteLength ? -1 : left.byteLength > right.byteLength ? 1 : 0;
    }
    if (descriptor === "bool") return left === right ? 0 : left ? 1 : -1;
    const kind = descriptor[0];
    if (kind === "document") return compareDocument(left, right);
    if (kind === "option") {
      if (left[1] !== right[1]) return left[1] ? 1 : -1;
      return left[1] ? compareValue(descriptor[1], left[2], right[2]) : 0;
    }
    if (kind === "result") {
      if (left[0] !== right[0]) return left[0] ? 1 : -1;
      return compareValue(left[0] ? descriptor[1] : descriptor[2], left[1], right[1]);
    }
    if (kind === "variant") {
      const leftIndex = descriptor[2].findIndex(([name]) => name === left[1]);
      const rightIndex = descriptor[2].findIndex(([name]) => name === right[1]);
      return leftIndex === rightIndex
        ? compareValue(descriptor[2][leftIndex][1], left[2], right[2])
        : leftIndex < rightIndex ? -1 : 1;
    }
    if (kind === "vector-i64")
      return compareSequence(Array.from({ length: Math.max(left.length, right.length) - 1 }, () => "i64"),
                             left.slice(1), right.slice(1));
    if (kind === "vector-f64")
      return compareSequence(Array.from({ length: Math.max(left.length, right.length) - 1 }, () => "f64"),
                             left.slice(1), right.slice(1));
    if (kind === "vector") return compareSequence(descriptor[1], left.slice(1), right.slice(1));
    if (kind === "list") {
      const length = Math.max(left[1].length, right[1].length);
      return compareSequence(Array.from({ length }, () => descriptor[1]), left[1], right[1]);
    }
    if (kind === "set") {
      const length = Math.max(left[1].length, right[1].length);
      return compareSequence(Array.from({ length }, () => descriptor[1]), left[1], right[1]);
    }
    if (kind === "map") {
      const length = Math.min(left[1].length, right[1].length);
      for (let index = 0; index < length; index += 1) {
        let compared = compareValue(descriptor[1], left[1][index][0], right[1][index][0]);
        if (compared !== 0) return compared;
        compared = compareValue(descriptor[2], left[1][index][1], right[1][index][1]);
        if (compared !== 0) return compared;
      }
      return left[1].length < right[1].length ? -1 : left[1].length > right[1].length ? 1 : 0;
    }
    if (kind === "record")
      return compareSequence(descriptor[2].map(([, type]) => type), left.slice(1), right.slice(1));
    reject("invalid-typed-value", "typed value has no canonical order");
  };
  const sameDescriptor = (left, right) => {
    if (left === right) return true;
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length)
      return false;
    for (let index = 0; index < left.length; index += 1)
      if (!sameDescriptor(left[index], right[index])) return false;
    return true;
  };
  const sameTrustedDescriptor = (left, right) =>
    left === right || (Array.isArray(left) && trustedDescriptors.has(left) &&
                       sameDescriptor(left, right));
  const assertValue = (descriptor, value,
                       state = { depth: 0, nodes: 0, indirectBytes: 0,
                                 listItems: 0 }) => {
    descriptor = resolveDescriptor(descriptor);
    state.nodes += 1;
    state.depth += 1;
    // ADT value depth raised 8→12 with kir ADR 0025 (structured kv EDN spines)
    if (state.depth > 12 || state.nodes > 64)
      reject("invalid-typed-value", "typed runtime value budget exceeded");
    try {
      if (descriptor === "i64") return i64(value);
      if (descriptor === "f64") return f64(value);
      if (descriptor === "f32") return f32(value);
      if (descriptor === "string") {
        const bytes = utf8Length(value);
        if (bytes > 65536) reject("invalid-typed-value", "typed string is oversized");
        state.indirectBytes += bytes;
        if (state.indirectBytes > 1048576)
          reject("invalid-typed-value", "typed aggregate indirect byte budget exceeded");
        return value;
      }
      if (descriptor === "keyword") {
        if (typeof value !== "string" || !value.startsWith(":"))
          reject("invalid-typed-value", "typed keyword is invalid");
        const bytes = utf8Length(value);
        if (bytes > 512) reject("invalid-typed-value", "typed keyword is invalid");
        state.indirectBytes += bytes;
        if (state.indirectBytes > 1048576)
          reject("invalid-typed-value", "typed aggregate indirect byte budget exceeded");
        return value;
      }
      if (descriptor === "symbol") {
        if (typeof value !== "string" || value.length === 0 ||
            /[\s\[\]{}()"',;`~^\\]/u.test(value) || utf8Length(value) > 512)
          reject("invalid-typed-value", "typed symbol is invalid");
        return value;
      }
      if (descriptor === "bool") {
        if (typeof value !== "boolean") reject("invalid-typed-value", "typed boolean is invalid");
        return value;
      }
      if (descriptor === "bytes") {
        if (!(value instanceof Uint8Array) || value.byteLength > 65536)
          reject("invalid-typed-value", "typed bytes value is invalid or oversized");
        state.indirectBytes += value.byteLength;
        if (state.indirectBytes > 1048576)
          reject("invalid-typed-value", "typed aggregate indirect byte budget exceeded");
        return value;
      }
      const kind = descriptor[0];
      if (kind === "document") return assertDocument(value);
      if (!Array.isArray(value) || !(Object.isFrozen(value) || linearValues.has(value)))
        reject("invalid-typed-value", "compound typed value must be a frozen array");
      if (!trustedValues.has(value))
        reject("invalid-typed-value", "forged compound typed value rejected");
      if (kind === "vector-i64") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length > VECTOR_ITEM_BUDGET + 1)
          reject("invalid-typed-value", "vector-i64 shape or item budget is invalid");
        // Every element, on every operation -- which makes a single element
        // write O(length) even after the copy is gone. Measured before this
        // guard: 20 writes to a 64-item vector scanned 4,032 elements, so
        // removing the copy alone bought nothing at scale. With it: 192.
        //
        // A linear vector is exempt because the scan is redundant for it, not
        // because it is trusted more. It was scanned in full when it entered
        // `linearValues` -- the first write copies a frozen array and that copy
        // goes through this path -- and the ONLY way its contents change
        // afterwards is `vector-assoc-in-place-i64`, which validates the
        // element it writes with `i64(replacement)` before storing it. Every
        // element has been through `i64` exactly as if this loop had run.
        //
        // Shape is still checked on every operation: the descriptor must match
        // and the length must be inside the budget. What is skipped is
        // re-deriving a fact already established per element.
        if (!linearValues.has(value))
          for (let index = 1; index < value.length; index += 1) i64(value[index]);
      } else if (kind === "vector-f64") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length > VECTOR_ITEM_BUDGET + 1)
          reject("invalid-typed-value", "vector-f64 shape or item budget is invalid");
        for (let index = 1; index < value.length; index += 1) f64(value[index]);
      } else if (kind === "string-index") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== 2 ||
            !Array.isArray(value[1]) || !Object.isFrozen(value[1]) || value[1].length > 128)
          reject("invalid-typed-value", "string-index shape or item budget is invalid");
        let keyBytes = 0;
        let previous = null;
        value[1].forEach(entry => {
          if (!Array.isArray(entry) || !Object.isFrozen(entry) || entry.length !== 2 ||
              typeof entry[0] !== "string")
            reject("invalid-typed-value", "string-index entry is invalid");
          keyBytes += utf8Length(entry[0]); i64(entry[1]);
          if (previous !== null && previous >= entry[0])
            reject("invalid-typed-value", "string-index keys are duplicated or non-canonical");
          previous = entry[0];
        });
        if (keyBytes > 65536)
          reject("invalid-typed-value", "string-index aggregate key budget exceeded");
      } else if (kind === "disjoint-set-i64") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== 3 ||
            !Array.isArray(value[1]) || !Object.isFrozen(value[1]) ||
            !Array.isArray(value[2]) || !Object.isFrozen(value[2]) ||
            value[1].length !== value[2].length || value[1].length > 128)
          reject("invalid-typed-value", "disjoint-set-i64 shape or item budget is invalid");
        const size = value[1].length;
        value[1].forEach(parent => { parent = i64(parent); if (parent < 0n || parent >= BigInt(size))
          reject("invalid-typed-value", "disjoint-set-i64 parent is out of range"); });
        value[2].forEach(rank => { rank = i64(rank); if (rank < 0n || rank > BigInt(size))
          reject("invalid-typed-value", "disjoint-set-i64 rank is out of range"); });
        for (let start = 0; start < size; start += 1) {
          let current = start;
          let remaining = size + 1;
          while (Number(value[1][current]) !== current) {
            if (--remaining === 0)
              reject("invalid-typed-value", "disjoint-set-i64 parent cycle rejected");
            current = Number(value[1][current]);
          }
        }
      } else if (kind === "option") {
        if (!sameTrustedDescriptor(value[0], descriptor) || typeof value[1] !== "boolean" ||
            value.length !== (value[1] ? 3 : 2))
          reject("invalid-typed-value", "generic option shape or descriptor is invalid");
        if (value[1]) assertValue(descriptor[1], value[2], state);
      } else if (kind === "result") {
        if (typeof value[0] !== "boolean" || value.length !== 2)
          reject("invalid-typed-value", "parametric result shape is invalid");
        assertValue(value[0] ? descriptor[1] : descriptor[2], value[1], state);
      } else if (kind === "variant") {
        const member = descriptor[2].find(([name]) => name === value[1]);
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== 3 || member === undefined)
          reject("invalid-typed-value", "variant shape, descriptor, or tag is invalid");
        assertValue(member[1], value[2], state);
      } else if (kind === "vector") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== descriptor[1].length + 1)
          reject("invalid-typed-value", "heterogeneous vector shape is invalid");
        descriptor[1].forEach((item, index) => assertValue(item, value[index + 1], state));
      } else if (kind === "list") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== 2 ||
            !Array.isArray(value[1]) || !Object.isFrozen(value[1]) ||
            value[1].length > 16384)
          reject("invalid-typed-value", "bounded list shape is invalid");
        state.listItems += value[1].length;
        if (state.listItems > 16384)
          reject("invalid-typed-value", "typed aggregate list item budget exceeded");
        value[1].forEach(item => assertValue(descriptor[1], item, state));
      } else if (kind === "set") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== 2 || !Array.isArray(value[1]) ||
            !Object.isFrozen(value[1]) || value[1].length > 32)
          reject("invalid-typed-value", "typed set shape is invalid");
        value[1].forEach(item => assertValue(descriptor[1], item, state));
        for (let index = 1; index < value[1].length; index += 1)
          if (compareValue(descriptor[1], value[1][index - 1], value[1][index]) >= 0)
            reject("invalid-typed-value", "typed set is duplicated or non-canonical");
      } else if (kind === "map") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== 2 ||
            !Array.isArray(value[1]) || !Object.isFrozen(value[1]) || value[1].length > 31)
          reject("invalid-typed-value", "typed map shape is invalid");
        value[1].forEach(entry => {
          if (!Array.isArray(entry) || !Object.isFrozen(entry) || entry.length !== 2)
            reject("invalid-typed-value", "typed map entry shape is invalid");
          assertValue(descriptor[1], entry[0], state);
          assertValue(descriptor[2], entry[1], state);
        });
        for (let index = 1; index < value[1].length; index += 1)
          if (compareValue(descriptor[1], value[1][index - 1][0], value[1][index][0]) >= 0)
            reject("invalid-typed-value", "typed map keys are duplicated or non-canonical");
      } else if (kind === "record") {
        if (!sameTrustedDescriptor(value[0], descriptor) || value.length !== descriptor[2].length + 1)
          reject("invalid-typed-value", "record shape or nominal descriptor is invalid");
        descriptor[2].forEach(([, type], index) => assertValue(type, value[index + 1], state));
      } else reject("invalid-typed-value", "unknown compound typed value");
      return value;
    } finally { state.depth -= 1; }
  };
  const checkedBuilder = value => {
    if ((typeof value !== "object" && typeof value !== "function") || value === null ||
        !builders.has(value)) reject("invalid-typed-builder", "forged typed builder rejected");
    return value;
  };
  const admitValue = (descriptor, value) => {
    trustedValues.add(value);
    try { return assertValue(descriptor, value); }
    catch (error) { trustedValues.delete(value); throw error; }
  };
  // typedCapCall is the host provider. Guest compounds must be interned
  // through builders; the host inject is allowed to return a new tree.
  // Echoing an already-admitted request still works (http wasm proof).
  const admitHostResult = (descriptor, value) => {
    if (value !== null && typeof value === "object" && trustedValues.has(value))
      return assertValue(descriptor, value);
    if (descriptor === "document" || (Array.isArray(descriptor) && descriptor[0] === "document"))
      return admitDocument(value);
    if (typeof descriptor === "string")
      return assertValue(descriptor, value);
    const kind = Array.isArray(descriptor) ? descriptor[0] : descriptor;
    if (kind === "variant") {
      if (!Array.isArray(value) || value.length !== 3)
        reject("invalid-typed-value", "variant shape, descriptor, or tag is invalid");
      const tag = value[1];
      const member = descriptor[2].find(([name]) => name === tag);
      if (member === undefined)
        reject("invalid-typed-value", "variant shape, descriptor, or tag is invalid");
      const payload = admitHostResult(member[1], value[2]);
      return admitValue(descriptor, Object.freeze([descriptor, tag, payload]));
    }
    if (kind === "record") {
      if (!Array.isArray(value) || value.length !== descriptor[2].length + 1)
        reject("invalid-typed-value", "record shape is invalid");
      const fields = descriptor[2].map(([, type], index) =>
        admitHostResult(type, value[index + 1]));
      return admitValue(descriptor, Object.freeze([descriptor, ...fields]));
    }
    if (kind === "option") {
      if (!Array.isArray(value) || typeof value[1] !== "boolean")
        reject("invalid-typed-value", "generic option shape or descriptor is invalid");
      if (!value[1])
        return admitValue(descriptor, Object.freeze([descriptor, false]));
      const inner = admitHostResult(descriptor[1], value[2]);
      return admitValue(descriptor, Object.freeze([descriptor, true, inner]));
    }
    if (kind === "result") {
      if (!Array.isArray(value) || typeof value[0] !== "boolean" || value.length !== 2)
        reject("invalid-typed-value", "parametric result shape is invalid");
      const inner = admitHostResult(value[0] ? descriptor[1] : descriptor[2], value[1]);
      return admitValue(descriptor, Object.freeze([value[0], inner]));
    }
    return admitValue(descriptor, Array.isArray(value) ? Object.freeze(value) : value);
  };
  const documentEntries = value => {
    value = assertDocument(value);
    if (value[0] !== "map") reject("invalid-typed-operation", "document map required");
    return value[1];
  };
  const documentKey = value => {
    if (typeof value === "string") {
      if (!value.startsWith(":") || utf8Length(value) > 512)
        reject("invalid-typed-value", "document map key is invalid");
      return constructDocument(["keyword", value]);
    }
    return assertDocument(value);
  };
  const documentPosition = (value, key) => {
    const entries = documentEntries(value);
    key = documentKey(key);
    return [entries, key, entries.findIndex(entry => compareDocumentMapKey(entry[0], key) === 0)];
  };
  const documentOption = (type, present, value) => {
    const descriptor = abi.descriptors.find(candidate => Array.isArray(candidate) &&
      candidate[0] === "option" && sameDescriptor(candidate[1], type));
    if (descriptor === undefined) reject("invalid-typed-operation", "document result option descriptor is absent");
    return admitValue(descriptor, Object.freeze(present
      ? [descriptor, true, value] : [descriptor, false]));
  };
  // Two pages, fixed, matching kotoba-wasm's `typed-scratch-pages`. The guest
  // bounds-checks its own bump pointer against that capacity before every
  // bulk write, so a larger or growable memory would silently widen a limit
  // the guest is enforcing on itself.
  const scratch = new WebAssembly.Memory({ initial: 2, maximum: 2 });
  const imports = Object.freeze({
    scratch,
    "cap-call"(id, request) {
      if (!Number.isInteger(id) || id < 0 || id > 255 || !allow.has(id))
        reject("capability-denied", "runtime capability policy denied the typed call");
      const contract = contractTable.get(id);
      if (contract === undefined)
        reject("capability-contract-missing", "typed capability has no sealed contract");
      if (typeof typedCapCall !== "function")
        reject("capability-unimplemented", "no typed host implementation exists for the capability");
      const checkedRequest = assertValue(descriptorAt(contract.request), request);
      const result = typedCapCall(id, checkedRequest, Object.freeze({
        request: descriptorAt(contract.request), result: descriptorAt(contract.result)
      }));
      return admitHostResult(descriptorAt(contract.result), result);
    },
    literal: literalAt,
    "keyword-from-string"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== "keyword" || typeof value !== "string" ||
          value.length === 0 || value[0] === ":" || /[\s\[\]{}()"',;`~^\\]/u.test(value))
        reject("invalid-typed-value", "keyword source text is invalid");
      const result = `:${value}`;
      if (utf8Length(result) > 512) reject("invalid-typed-value", "keyword is oversized");
      return result;
    },
    "symbol-from-string"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== "symbol" || typeof value !== "string" ||
          value.length === 0 || /[\s\[\]{}()"',;`~^\\]/u.test(value) ||
          utf8Length(value) > 512)
        reject("invalid-typed-value", "symbol source text is invalid");
      return value;
    },
    "keyword-name"(descriptorId, value) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "keyword") reject("invalid-typed-operation", "keyword descriptor required");
      value = assertValue(descriptor, value).slice(1);
      return value.slice(value.lastIndexOf("/") + 1);
    },
    new(descriptorId, tag) {
      descriptorAt(descriptorId);
      const builder = Object.freeze({ descriptorId, tag, slots: Object.freeze([]) });
      builders.add(builder);
      return builder;
    },
    "push-i64"(rawBuilder, item) {
      const builder = checkedBuilder(rawBuilder);
      const next = Object.freeze({ ...builder, slots: Object.freeze([...builder.slots, i64(item)]) });
      builders.add(next);
      return next;
    },
    "push-f64"(rawBuilder, item) {
      const builder = checkedBuilder(rawBuilder);
      const next = Object.freeze({ ...builder, slots: Object.freeze([...builder.slots, f64(item)]) });
      builders.add(next);
      return next;
    },
    "push-f32"(rawBuilder, item) {
      const builder = checkedBuilder(rawBuilder);
      const next = Object.freeze({ ...builder, slots: Object.freeze([...builder.slots, f32(item)]) });
      builders.add(next);
      return next;
    },
    "push-ref"(rawBuilder, item) {
      const builder = checkedBuilder(rawBuilder);
      const next = Object.freeze({ ...builder, slots: Object.freeze([...builder.slots, item]) });
      builders.add(next);
      return next;
    },
    seal(descriptorId, rawBuilder) {
      const descriptor = descriptorAt(descriptorId);
      const builder = checkedBuilder(rawBuilder);
      if (builder.descriptorId !== descriptorId)
        reject("invalid-typed-builder", "typed builder descriptor substitution rejected");
      const kind = Array.isArray(descriptor) ? descriptor[0] : descriptor;
      let result;
      if (kind === "option") result = builder.tag === 0
        ? [descriptor, false] : [descriptor, true, ...builder.slots];
      else if (kind === "result") result = [builder.tag === 1, ...builder.slots];
      else if (kind === "variant") {
        const member = descriptor[2][builder.tag];
        if (member === undefined) reject("invalid-typed-builder", "variant tag is out of range");
        result = [descriptor, member[0], ...builder.slots];
      } else if (kind === "vector-i64" || kind === "vector-f64" || kind === "vector" || kind === "record")
        result = [descriptor, ...builder.slots];
      else if (kind === "list")
        result = [descriptor, Object.freeze([...builder.slots])];
      else if (kind === "set") {
        const sorted = [...builder.slots].sort((left, right) => compareValue(descriptor[1], left, right));
        for (let index = 1; index < sorted.length; index += 1)
          if (compareValue(descriptor[1], sorted[index - 1], sorted[index]) === 0)
            reject("invalid-typed-set", "duplicate typed set item rejected");
        result = [descriptor, Object.freeze(sorted)];
      } else if (kind === "map") {
        if (builder.slots.length % 2 !== 0)
          reject("invalid-typed-builder", "typed map builder has an unmatched key");
        const entries = [];
        for (let index = 0; index < builder.slots.length; index += 2)
          entries.push(Object.freeze([builder.slots[index], builder.slots[index + 1]]));
        entries.sort((left, right) => compareValue(descriptor[1], left[0], right[0]));
        for (let index = 1; index < entries.length; index += 1)
          if (compareValue(descriptor[1], entries[index - 1][0], entries[index][0]) === 0)
            reject("invalid-typed-map", "duplicate typed map key rejected");
        result = [descriptor, Object.freeze(entries)];
      } else if (kind === "document") {
        if (builder.tag === -1) result = ["vector", builder.slots];
        else if (builder.tag === -3) result = ["list", builder.slots];
        else if (builder.tag === -4) {
          const items = [...builder.slots].sort(compareDocument);
          for (let index = 1; index < items.length; index += 1)
            if (compareDocument(items[index - 1], items[index]) === 0)
              reject("invalid-typed-set", "duplicate document set item rejected");
          result = ["set", items];
        }
        else if (builder.tag === -2) {
          if (builder.slots.length % 2 !== 0)
            reject("invalid-typed-builder", "document map builder has an unmatched key");
          const entries = [];
          for (let index = 0; index < builder.slots.length; index += 2)
            entries.push([documentKey(builder.slots[index]), assertDocument(builder.slots[index + 1])]);
          entries.sort((left, right) => compareDocumentMapKey(left[0], right[0]));
          for (let index = 1; index < entries.length; index += 1)
            if (compareDocumentMapKey(entries[index - 1][0], entries[index][0]) === 0)
              reject("invalid-typed-map", "duplicate document map key rejected");
          result = ["map", entries];
        } else reject("invalid-typed-builder", "document builder tag is invalid");
        return constructDocument(result);
      } else reject("invalid-typed-builder", "primitive descriptor cannot be constructed");
      return admitValue(descriptor, Object.freeze(result));
    },
    "assert-ref"(descriptorId, value) { return assertValue(descriptorAt(descriptorId), value); },
    tag(descriptorId, value) {
      const descriptor = descriptorAt(descriptorId);
      const checked = assertValue(descriptor, value);
      if (descriptor === "bool") return checked ? 1 : 0;
      if (descriptor[0] === "option") return checked[1] ? 1 : 0;
      if (descriptor[0] === "result") return checked[0] ? 1 : 0;
      if (descriptor[0] === "variant") return descriptor[2].findIndex(([name]) => name === checked[1]);
      reject("invalid-typed-operation", "tag is not defined for this descriptor");
    },
    "get-i64"(descriptorId, value, index) {
      const descriptor = descriptorAt(descriptorId);
      const checked = assertValue(descriptor, value);
      const kind = descriptor[0];
      const item = kind === "option" ? checked[2]
        : kind === "result" ? checked[1]
        : kind === "variant" ? checked[2]
        : checked[index + 1];
      return i64(item);
    },
    "get-f64"(descriptorId, value, index) {
      const descriptor = descriptorAt(descriptorId);
      const checked = assertValue(descriptor, value);
      const kind = descriptor[0];
      const item = kind === "option" ? checked[2]
        : kind === "result" ? checked[1]
        : kind === "variant" ? checked[2]
        : checked[index + 1];
      return f64(item);
    },
    "get-f32"(descriptorId, value, index) {
      const descriptor = descriptorAt(descriptorId);
      const checked = assertValue(descriptor, value);
      const kind = descriptor[0];
      const item = kind === "option" ? checked[2]
        : kind === "result" ? checked[1]
        : kind === "variant" ? checked[2]
        : checked[index + 1];
      return f32(item);
    },
    "get-ref"(descriptorId, value, index) {
      const descriptor = descriptorAt(descriptorId);
      const checked = assertValue(descriptor, value);
      const kind = descriptor[0];
      return kind === "option" ? checked[2]
        : kind === "result" ? checked[1]
        : kind === "variant" ? checked[2]
        : checked[index + 1];
    },
    count(descriptorId, value) {
      const descriptor = descriptorAt(descriptorId);
      const checked = assertValue(descriptor, value);
      if (descriptor === "string") return BigInt(utf8Length(checked));
      if (descriptor[0] === "vector-i64" || descriptor[0] === "vector-f64" || descriptor[0] === "vector" || descriptor[0] === "record")
        return BigInt(checked.length - 1);
      if (descriptor[0] === "list") return BigInt(checked[1].length);
      if (descriptor[0] === "set") return BigInt(checked[1].length);
      if (descriptor[0] === "map") return BigInt(checked[1].length);
      if (descriptor[0] === "string-index") return BigInt(checked[1].length);
      if (descriptor[0] === "disjoint-set-i64") return BigInt(checked[1].length);
      if (descriptor[0] === "document") {
        if (checked[0] !== "map" && checked[0] !== "vector" && checked[0] !== "list" && checked[0] !== "set")
          reject("invalid-typed-operation", "document container required");
        return BigInt(checked[1].length);
      }
      reject("invalid-typed-operation", "count is not defined for this descriptor");
    },
    bool(value) { return value !== 0; },
    // Profile 5 (ADR 0191 A): unbox a sealed JS boolean to an i32 0/1 word.
    // Inverse of `bool` (i32 → externref). Used when aggregates store :bool as
    // a host boolean but the language value profile carries a 0/1 word.
    "bool-value"(value) {
      if (typeof value !== "boolean") reject("invalid-typed-value", "typed boolean is invalid");
      return value ? 1 : 0;
    },
    "bytes-empty"(descriptorId) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "bytes") reject("invalid-typed-operation", "bytes descriptor required");
      return admitValue(descriptor, Object.freeze(new Uint8Array(0)));
    },
    equal(descriptorId, left, right) {
      const descriptor = descriptorAt(descriptorId);
      return compareValue(descriptor, assertValue(descriptor, left), assertValue(descriptor, right)) === 0 ? 1 : 0;
    },
    "string-concat"(descriptorId, left, right) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      const result = assertValue(descriptor, left) + assertValue(descriptor, right);
      if (utf8Length(result) > 65536) reject("invalid-typed-value", "typed string is oversized");
      return result;
    },
    "string-substring"(descriptorId, value, start, end) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      value = assertValue(descriptor, value);
      start = Number(start); end = Number(end);
      const bytes = new TextEncoder().encode(value);
      if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) ||
          start < 0 || start > end || end > bytes.length)
        reject("invalid-typed-operation", "string substring indexes are out of bounds");
      const decoder = new TextDecoder("utf-8", { fatal: true });
      try {
        return decoder.decode(bytes.slice(start, end));
      } catch (_) {
        reject("invalid-typed-operation", "string substring index splits a UTF-8 code point");
      }
    },
    "string-replace-all"(descriptorId, value, needle, replacement) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      value = assertValue(descriptor, value);
      needle = assertValue(descriptor, needle);
      replacement = assertValue(descriptor, replacement);
      if (needle.length === 0)
        reject("invalid-typed-operation", "empty string replacement needle rejected");
      const result = value.split(needle).join(replacement);
      if (utf8Length(result) > 65536) reject("invalid-typed-value", "typed string is oversized");
      return result;
    },
    "string-code-point-at"(descriptorId, value, offset) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      value = assertValue(descriptor, value);
      offset = Number(offset);
      const bytes = new TextEncoder().encode(value);
      if (!Number.isSafeInteger(offset) || offset < 0 || offset >= bytes.length)
        reject("invalid-typed-operation", "string code-point offset is out of bounds");
      const b0 = bytes[offset];
      // A continuation byte (0x80..0xbf) is mid-code-point, not a boundary.
      if (b0 >= 0x80 && b0 < 0xc0)
        reject("invalid-typed-operation", "string code-point offset splits a UTF-8 code point");
      let cp, width;
      if (b0 < 0x80) { cp = b0; width = 1; }
      else if (b0 < 0xe0) { cp = b0 & 0x1f; width = 2; }
      else if (b0 < 0xf0) { cp = b0 & 0x0f; width = 3; }
      else { cp = b0 & 0x07; width = 4; }
      for (let i = 1; i < width; i++) {
        const b = bytes[offset + i];
        if (b === undefined || b < 0x80 || b >= 0xc0)
          reject("invalid-typed-operation", "string contains a malformed UTF-8 sequence");
        cp = (cp << 6) | (b & 0x3f);
      }
      return cp;
    },
    "string-contains"(descriptorId, haystack, needle) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      haystack = assertValue(descriptor, haystack);
      needle = assertValue(descriptor, needle);
      if (needle.length === 0)
        reject("invalid-typed-operation", "empty string search needle rejected");
      return haystack.includes(needle) ? 1 : 0;
    },
    // T4.2: segment count for non-empty separator (non-overlapping), same
    // length as JS String#split for non-regex separators.
    "string-split-count"(descriptorId, haystack, sep) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      haystack = assertValue(descriptor, haystack);
      sep = assertValue(descriptor, sep);
      if (sep.length === 0)
        reject("invalid-typed-operation", "empty string split separator rejected");
      let i = 0;
      let n = 1;
      while (true) {
        const idx = haystack.indexOf(sep, i);
        if (idx < 0) return n;
        i = idx + sep.length;
        n += 1;
      }
    },
    "string-fold-case"(descriptorId, value) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      value = assertValue(descriptor, value);
      const result = value.toLowerCase();
      if (utf8Length(result) > 65536) reject("invalid-typed-value", "typed string is oversized");
      return result;
    },
    "string-upper"(descriptorId, value) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor !== "string") reject("invalid-typed-operation", "string descriptor required");
      value = assertValue(descriptor, value);
      const result = value.toUpperCase();
      if (utf8Length(result) > 65536) reject("invalid-typed-value", "typed string is oversized");
      return result;
    },
    "assoc-i64"(descriptorId, value, index, replacement) {
      return assoc(descriptorId, value, index, i64(replacement));
    },
    "assoc-f64"(descriptorId, value, index, replacement) {
      return assoc(descriptorId, value, index, f64(replacement));
    },
    "assoc-f32"(descriptorId, value, index, replacement) {
      return assoc(descriptorId, value, index, f32(replacement));
    },
    "assoc-ref"(descriptorId, value, index, replacement) {
      return assoc(descriptorId, value, index, replacement);
    },
    "vector-drop"(descriptorId, value, rawCount) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64" && descriptor[0] !== "vector-f64")
        reject("invalid-typed-operation", "vector-drop requires a homogeneous vector");
      const checked = assertValue(descriptor, value);
      const count = i64(rawCount);
      if (count < 0n || count > BigInt(checked.length - 1))
        reject("invalid-typed-operation", "vector-drop count is out of range");
      const start = Number(count) + 1;
      return admitValue(descriptor, Object.freeze([descriptor, ...checked.slice(start)]));
    },
    "vector-at-i64"(descriptorId, value, rawIndex) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64")
        reject("invalid-typed-operation", "vector-at requires vector-i64");
      const checked = assertValue(descriptor, value);
      const index = i64(rawIndex);
      if (index < 0n || index >= BigInt(checked.length - 1))
        reject("invalid-typed-operation", "vector-i64 index is out of range");
      return i64(checked[Number(index) + 1]);
    },
    "vector-assoc-i64"(descriptorId, value, rawIndex, replacement) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64")
        reject("invalid-typed-operation", "vector-assoc requires vector-i64");
      const checked = assertValue(descriptor, value);
      const index = i64(rawIndex);
      if (index < 0n || index >= BigInt(checked.length - 1))
        reject("invalid-typed-operation", "vector-i64 assoc index is out of range");
      const result = [...checked];
      result[Number(index) + 1] = i64(replacement);
      return admitValue(descriptor, Object.freeze(result));
    },
    // The same operation as vector-assoc-i64, lowered to a store.
    //
    // `vector-assoc-i64` above does `[...checked]` and freezes the result, so
    // one element write costs a copy of the whole vector. That is why a struct
    // of arrays could not be written in Kotoba: an order book has about a
    // million slots per field and a write per order (ADR-2609010200).
    //
    // The guest only reaches this through `vector-assoc!`, which the frontend
    // refuses unless the handle is dead after the write. The KIR interpreter
    // treats `vector-assoc` and `vector-assoc!` as ONE operation for the same
    // reason, so the reference semantics cannot drift from this lowering.
    //
    // The FIRST write to a frozen vector copies -- everything the copying path
    // built is frozen and a frozen array cannot be written, silently in sloppy
    // mode and loudly in strict, and a silent no-op here is a store that did
    // not happen. Every later write to that result is in place. So a vector
    // allocated once and written N times costs one copy rather than N.
    // `(vector-alloc n)` -- n zeros.
    //
    // `vector-new` is variadic, so a million-slot struct of arrays would need
    // a million arguments in source and the literal limit refuses that long
    // before the item budget does. Correct, and it left no way to allocate one
    // at all.
    //
    // Admitted LINEAR from birth: nothing else holds it, so the first write
    // does not have to copy a frozen array before it can store. Allocating and
    // writing N times now costs zero copies rather than one.
    "vector-alloc-i64"(descriptorId, rawCount) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64")
        reject("invalid-typed-operation", "vector-alloc requires vector-i64");
      const count = i64(rawCount);
      if (count < 0n || count > BigInt(VECTOR_ITEM_BUDGET))
        reject("invalid-typed-value", "vector-i64 item budget exceeded");
      vectorItemsAllocated += Number(count);
      if (vectorItemsAllocated > VECTOR_TOTAL_ITEM_BUDGET)
        reject("invalid-typed-value", "typed vector total item budget exceeded");
      const items = new Array(Number(count) + 1);
      items[0] = descriptor;
      items.fill(0n, 1);
      linearValues.add(items);
      return admitValue(descriptor, items);
    },
    "vector-assoc-in-place-i64"(descriptorId, value, rawIndex, replacement) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64")
        reject("invalid-typed-operation", "vector-assoc! requires vector-i64");
      const checked = assertValue(descriptor, value);
      const index = i64(rawIndex);
      if (index < 0n || index >= BigInt(checked.length - 1))
        reject("invalid-typed-operation", "vector-i64 assoc index is out of range");
      let target = checked;
      if (!linearValues.has(target)) {
        target = [...checked];
        linearValues.add(target);
      }
      target[Number(index) + 1] = i64(replacement);
      return admitValue(descriptor, target);
    },
    "vector-conj-i64"(descriptorId, value, item) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64")
        reject("invalid-typed-operation", "vector-conj requires vector-i64");
      const checked = assertValue(descriptor, value);
      if (checked.length > VECTOR_ITEM_BUDGET) reject("invalid-typed-value", "vector-i64 item budget exceeded");
      return admitValue(descriptor, Object.freeze([...checked, i64(item)]));
    },
    // The bulk counterpart of vector-conj-i64: the guest has already written
    // `count` i64s into the scratch memory at `offset`, and this reads them
    // back as one value instead of one host call per item.
    //
    // Missing until 2026-08-29, which made every vector kit in amu's
    // conformance suite fail with `forbidden-import` -- kotoba-wasm c7d3514
    // replayed the emitter half of this path without the host half.
    "vector-from-memory-i64"(descriptorId, offset, count) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-i64")
        reject("invalid-typed-operation", "vector-from-memory requires vector-i64");
      const items = Number(count);
      const start = Number(offset);
      // Same item budget as vector-conj-i64, so the two ways of building the
      // same value cannot disagree about how large it may be.
      if (!Number.isInteger(items) || items < 0 || items > 16384)
        reject("invalid-typed-value", "vector-i64 item budget exceeded");
      const span = items * 8;
      if (!Number.isInteger(start) || start < 0 || start + span > scratch.buffer.byteLength)
        reject("invalid-typed-operation", "vector-from-memory range is outside the scratch memory");
      const view = new DataView(scratch.buffer);
      const result = new Array(items + 1);
      result[0] = descriptor;
      for (let index = 0; index < items; index += 1)
        result[index + 1] = view.getBigInt64(start + index * 8, true);
      return admitValue(descriptor, Object.freeze(result));
    },
    "vector-at-f64"(descriptorId, value, rawIndex) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-f64")
        reject("invalid-typed-operation", "vector-at-f64 requires vector-f64");
      const checked = assertValue(descriptor, value);
      const index = i64(rawIndex);
      if (index < 0n || index >= BigInt(checked.length - 1))
        reject("invalid-typed-operation", "vector-f64 index is out of range");
      return f64(checked[Number(index) + 1]);
    },
    "vector-assoc-f64"(descriptorId, value, rawIndex, replacement) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-f64")
        reject("invalid-typed-operation", "vector-assoc-f64 requires vector-f64");
      const checked = assertValue(descriptor, value);
      const index = i64(rawIndex);
      if (index < 0n || index >= BigInt(checked.length - 1))
        reject("invalid-typed-operation", "vector-f64 assoc index is out of range");
      const result = [...checked];
      result[Number(index) + 1] = f64(replacement);
      return admitValue(descriptor, Object.freeze(result));
    },
    "vector-conj-f64"(descriptorId, value, item) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "vector-f64")
        reject("invalid-typed-operation", "vector-conj-f64 requires vector-f64");
      const checked = assertValue(descriptor, value);
      if (checked.length >= 16385) reject("invalid-typed-value", "vector-f64 item budget exceeded");
      return admitValue(descriptor, Object.freeze([...checked, f64(item)]));
    },
    "set-op-i64"(descriptorId, value, operation, item) {
      return setOperation(descriptorId, value, operation, i64(item));
    },
    "set-op-ref"(descriptorId, value, operation, item) {
      return setOperation(descriptorId, value, operation, item);
    },
    "set-contains-i64"(descriptorId, value, item) {
      return setContains(descriptorId, value, i64(item)) ? 1 : 0;
    },
    "set-contains-ref"(descriptorId, value, item) {
      return setContains(descriptorId, value, item) ? 1 : 0;
    },
    "set-nth-i64"(descriptorId, value, rawIndex) {
      return setNth(descriptorId, value, i64(rawIndex), /*i64Item*/ true);
    },
    "set-nth-ref"(descriptorId, value, rawIndex) {
      return setNth(descriptorId, value, i64(rawIndex), /*i64Item*/ false);
    },
    "map-contains-i64"(descriptorId, value, key) {
      return mapContains(descriptorId, value, i64(key)) ? 1 : 0;
    },
    "map-contains-ref"(descriptorId, value, key) {
      return mapContains(descriptorId, value, key) ? 1 : 0;
    },
    "map-get-i64"(descriptorId, value, key) { return mapGet(descriptorId, value, i64(key)); },
    "map-get-ref"(descriptorId, value, key) { return mapGet(descriptorId, value, key); },
    "map-entry-at"(descriptorId, value, index) { return mapEntryAt(descriptorId, value, i64(index)); },
    "map-assoc-ii"(descriptorId, value, key, item) {
      return mapAssoc(descriptorId, value, i64(key), i64(item));
    },
    "map-assoc-ir"(descriptorId, value, key, item) {
      return mapAssoc(descriptorId, value, i64(key), item);
    },
    "map-assoc-ri"(descriptorId, value, key, item) {
      return mapAssoc(descriptorId, value, key, i64(item));
    },
    "map-assoc-rr"(descriptorId, value, key, item) {
      return mapAssoc(descriptorId, value, key, item);
    },
    "map-dissoc-i64"(descriptorId, value, key) {
      return mapDissoc(descriptorId, value, i64(key));
    },
    "map-dissoc-ref"(descriptorId, value, key) { return mapDissoc(descriptorId, value, key); },
    "string-index-new"(descriptorId) {
      const descriptor = descriptorAt(descriptorId);
      if (descriptor[0] !== "string-index") reject("invalid-typed-operation", "string-index descriptor required");
      return admitValue(descriptor, Object.freeze([descriptor, Object.freeze([])]));
    },
    "string-index-contains"(descriptorId, value, key) {
      const [,, index] = stringIndexEntry(descriptorId, value, key); return index < 0 ? 0 : 1;
    },
    "string-index-get"(descriptorId, value, key) {
      const [, checked, index] = stringIndexEntry(descriptorId, value, key);
      const optionDescriptor = abi.descriptors.find(candidate =>
        Array.isArray(candidate) && candidate[0] === "option" && candidate[1] === "i64");
      if (optionDescriptor === undefined) reject("invalid-typed-operation", "i64 option descriptor is absent");
      return admitValue(optionDescriptor, Object.freeze(index < 0
        ? [optionDescriptor, false] : [optionDescriptor, true, checked[1][index][1]]));
    },
    "string-index-assoc"(descriptorId, value, key, item) {
      const [descriptor, checked, index] = stringIndexEntry(descriptorId, value, key);
      item = i64(item);
      if (index < 0 && checked[1].length >= 128)
        reject("invalid-typed-value", "string-index item budget exceeded");
      const entries = [...checked[1]];
      const entry = Object.freeze([key, item]);
      if (index < 0) entries.push(entry); else entries[index] = entry;
      entries.sort((left, right) => left[0] < right[0] ? -1 : left[0] > right[0] ? 1 : 0);
      return admitValue(descriptor, Object.freeze([descriptor, Object.freeze(entries)]));
    },
    "disjoint-set-i64-new"(descriptorId, rawSize) {
      const descriptor = descriptorAt(descriptorId), size = i64(rawSize);
      if (descriptor[0] !== "disjoint-set-i64" || size < 0n || size > 128n)
        reject("invalid-typed-operation", "disjoint-set-i64 size is out of range");
      const parents = Object.freeze(Array.from({length: Number(size)}, (_, index) => BigInt(index)));
      const ranks = Object.freeze(Array.from({length: Number(size)}, () => 0n));
      return admitValue(descriptor, Object.freeze([descriptor, parents, ranks]));
    },
    "disjoint-set-i64-union"(descriptorId, value, rawLeft, rawRight) {
      const descriptor = descriptorAt(descriptorId), checked = assertValue(descriptor, value);
      if (descriptor[0] !== "disjoint-set-i64") reject("invalid-typed-operation", "disjoint-set-i64 descriptor required");
      const size = checked[1].length, left = i64(rawLeft), right = i64(rawRight);
      if (left < 0n || right < 0n || left >= BigInt(size) || right >= BigInt(size))
        reject("invalid-typed-operation", "disjoint-set-i64 index is out of range");
      const root = raw => { let current = Number(raw); for (let fuel = size + 1; fuel > 0; fuel -= 1) {
        const parent = Number(checked[1][current]); if (parent === current) return current; current = parent;
      } reject("invalid-typed-value", "disjoint-set-i64 parent cycle rejected"); };
      const leftRoot = root(left), rightRoot = root(right);
      const optionDescriptor = abi.descriptors.find(candidate => Array.isArray(candidate) &&
        candidate[0] === "option" && sameDescriptor(candidate[1], descriptor));
      if (optionDescriptor === undefined) reject("invalid-typed-operation", "disjoint-set option descriptor is absent");
      if (leftRoot === rightRoot)
        return admitValue(optionDescriptor, Object.freeze([optionDescriptor, false]));
      let child = rightRoot, parent = leftRoot;
      if (checked[2][leftRoot] < checked[2][rightRoot]) { child = leftRoot; parent = rightRoot; }
      const parents = [...checked[1]], ranks = [...checked[2]];
      parents[child] = BigInt(parent);
      if (checked[2][leftRoot] === checked[2][rightRoot]) ranks[parent] += 1n;
      const result = admitValue(descriptor, Object.freeze([descriptor, Object.freeze(parents), Object.freeze(ranks)]));
      return admitValue(optionDescriptor, Object.freeze([optionDescriptor, true, result]));
    },
    "document-null"(descriptorId) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return constructDocument(["null"]);
    },
    "document-bool"(descriptorId, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor || typeof item !== "boolean")
        reject("invalid-typed-operation", "document bool requires its descriptor and boolean");
      return constructDocument(["bool", item]);
    },
    "document-i64"(descriptorId, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return constructDocument(["i64", i64(item)]);
    },
    "document-f64"(descriptorId, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor || !Number.isFinite(item))
        reject("invalid-typed-operation", "document f64 must be finite");
      return constructDocument(["f64", item]);
    },
    "document-string"(descriptorId, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return constructDocument(["string", item]);
    },
    "document-keyword"(descriptorId, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return constructDocument(["keyword", item]);
    },
    "document-symbol"(descriptorId, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return constructDocument(["symbol", item]);
    },
    "document-kind"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return `:${assertDocument(value)[0]}`;
    },
    "document-sha256"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return documentSha256Hex(assertDocument(value));
    },
    "document-print"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return documentPrint(value);
    },
    "document-read"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return documentRead(value);
    },
    "document-edn-print"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return documentEdnPrint(value);
    },
    "document-edn-read"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return documentEdnRead(value);
    },
    "document-contains"(descriptorId, value, key) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      return documentPosition(value, key)[2] < 0 ? 0 : 1;
    },
    "document-set-contains"(descriptorId, value, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); item = assertDocument(item);
      if (value[0] !== "set") reject("invalid-typed-operation", "document set required");
      return value[1].some(candidate => compareDocument(candidate, item) === 0) ? 1 : 0;
    },
    "document-vector-at"(descriptorId, value, rawIndex) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); const index = i64(rawIndex);
      if (value[0] !== "vector") reject("invalid-typed-operation", "document vector required");
      const ok = index >= 0n && index < BigInt(value[1].length);
      return documentOption(documentDescriptor, ok, ok ? value[1][Number(index)] : undefined);
    },
    "document-list-at"(descriptorId, value, rawIndex) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); const index = i64(rawIndex);
      if (value[0] !== "list") reject("invalid-typed-operation", "document list required");
      const ok = index >= 0n && index < BigInt(value[1].length);
      return documentOption(documentDescriptor, ok, ok ? value[1][Number(index)] : undefined);
    },
    "document-map-entry-at"(descriptorId, value, rawIndex) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); const index = i64(rawIndex);
      if (value[0] !== "map") reject("invalid-typed-operation", "document map required");
      const ok = index >= 0n && index < BigInt(value[1].length);
      if (!ok) return documentOption(documentDescriptor, false, undefined);
      const [key, item] = value[1][Number(index)];
      return documentOption(documentDescriptor, true,
        constructDocument(["vector", [key, item]]));
    },
    "document-vector-assoc"(descriptorId, value, rawIndex, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); const index = i64(rawIndex); item = assertDocument(item);
      if (value[0] !== "vector") reject("invalid-typed-operation", "document vector required");
      if (index < 0n || index >= BigInt(value[1].length))
        reject("invalid-typed-operation", "document vector index out of range");
      const output = [...value[1]]; output[Number(index)] = item;
      return constructDocument(["vector", output]);
    },
    "document-vector-conj"(descriptorId, value, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); item = assertDocument(item);
      if (value[0] !== "vector") reject("invalid-typed-operation", "document vector required");
      if (value[1].length >= 32) reject("invalid-typed-value", "document vector item budget exceeded");
      return constructDocument(["vector", [...value[1], item]]);
    },
    "document-vector-drop"(descriptorId, value, rawCount) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); const count = i64(rawCount);
      if (value[0] !== "vector") reject("invalid-typed-operation", "document vector required");
      if (count < 0n || count > BigInt(value[1].length))
        reject("invalid-typed-operation", "document vector drop out of range");
      return constructDocument(["vector", value[1].slice(Number(count))]);
    },
    "document-vector-remove"(descriptorId, value, rawIndex) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); const index = i64(rawIndex);
      if (value[0] !== "vector") reject("invalid-typed-operation", "document vector required");
      if (index < 0n || index >= BigInt(value[1].length))
        reject("invalid-typed-operation", "document vector index out of range");
      return constructDocument(["vector", value[1].filter((_, itemIndex) => itemIndex !== Number(index))]);
    },
    "document-get"(descriptorId, value, key) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      const [entries,, index] = documentPosition(value, key);
      return documentOption(documentDescriptor, index >= 0, index >= 0 ? entries[index][1] : undefined);
    },
    "document-assoc"(descriptorId, value, key, item) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      const [entries, checkedKey, index] = documentPosition(value, key);
      item = assertDocument(item);
      if (index < 0 && entries.length >= 32)
        reject("invalid-typed-value", "document map item budget exceeded");
      const output = entries.map(entry => [entry[0], entry[1]]);
      if (index < 0) output.push([checkedKey, item]); else output[index] = [checkedKey, item];
      output.sort((left, right) => compareDocumentMapKey(left[0], right[0]));
      return constructDocument(["map", output]);
    },
    "document-dissoc"(descriptorId, value, key) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      const [entries,, index] = documentPosition(value, key);
      if (index < 0) return assertDocument(value);
      return constructDocument(["map", entries.filter((_, itemIndex) => itemIndex !== index)
        .map(entry => [entry[0], entry[1]])]);
    },
    "document-merge"(descriptorId, left, right) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      const merged = documentEntries(left).map(entry => [entry[0], entry[1]]);
      for (const entry of documentEntries(right)) {
        const index = merged.findIndex(candidate => compareDocumentMapKey(candidate[0], entry[0]) === 0);
        if (index < 0) merged.push([entry[0], entry[1]]); else merged[index] = [entry[0], entry[1]];
      }
      if (merged.length > 32) reject("invalid-typed-value", "document map item budget exceeded");
      merged.sort((a, b) => compareDocumentMapKey(a[0], b[0]));
      return constructDocument(["map", merged]);
    },
    "document-string-value"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); return documentOption("string", value[0] === "string", value[1]);
    },
    "document-keyword-value"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); return documentOption("keyword", value[0] === "keyword", value[1]);
    },
    "document-symbol-value"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); return documentOption("symbol", value[0] === "symbol", value[1]);
    },
    "document-bool-value"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); return documentOption("bool", value[0] === "bool", value[1]);
    },
    "document-i64-value"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); return documentOption("i64", value[0] === "i64", value[1]);
    },
    "document-f64-value"(descriptorId, value) {
      if (descriptorAt(descriptorId) !== documentDescriptor)
        reject("invalid-typed-operation", "document descriptor required");
      value = assertDocument(value); return documentOption("f64", value[0] === "f64", value[1]);
    },
    "xml-path-count"(xml, path) {
      const wanted = xmlPath(path);
      return BigInt(parseBoundedXml(xml).filter(node => node.path === wanted).length);
    },
    "xml-name-count"(xml, name) {
      const wanted = xmlCheckedName(name);
      return BigInt(parseBoundedXml(xml).filter(node => xmlElementName(node) === wanted).length);
    },
    "xml-name-text"(xml, name, index) {
      const wanted = xmlCheckedName(name);
      if (typeof index !== "bigint" || index < 0n || BigInt.asIntN(64, index) !== index)
        reject("invalid-xml", "XML element index is invalid");
      const optionDescriptor = abi.descriptors.find(candidate =>
        Array.isArray(candidate) && candidate[0] === "option" && candidate[1] === "string");
      if (optionDescriptor === undefined)
        reject("invalid-typed-operation", "XML string option descriptor is absent");
      const matches = parseBoundedXml(xml).filter(node => xmlElementName(node) === wanted);
      const present = index < BigInt(matches.length);
      return admitValue(optionDescriptor, Object.freeze(present
        ? [optionDescriptor, true, matches[Number(index)].text]
        : [optionDescriptor, false]));
    },
    "xml-path-text"(xml, path, index) {
      const wanted = xmlPath(path);
      if (typeof index !== "bigint" || index < 0n || BigInt.asIntN(64, index) !== index)
        reject("invalid-xml", "XML element index is invalid");
      const optionDescriptor = abi.descriptors.find(candidate =>
        Array.isArray(candidate) && candidate[0] === "option" && candidate[1] === "string");
      if (optionDescriptor === undefined)
        reject("invalid-typed-operation", "XML string option descriptor is absent");
      const matches = parseBoundedXml(xml).filter(node => node.path === wanted);
      const present = index < BigInt(matches.length);
      return admitValue(optionDescriptor, Object.freeze(present
        ? [optionDescriptor, true, matches[Number(index)].text]
        : [optionDescriptor, false]));
    },
    "xml-path-attr"(xml, path, index, attribute) {
      const wanted = xmlPath(path);
      if (typeof index !== "bigint" || index < 0n || BigInt.asIntN(64, index) !== index)
        reject("invalid-xml", "XML element index is invalid");
      attribute = xmlString(attribute);
      if (!xmlName.test(attribute)) reject("invalid-xml", "XML attribute name is invalid");
      const optionDescriptor = abi.descriptors.find(candidate =>
        Array.isArray(candidate) && candidate[0] === "option" && candidate[1] === "string");
      if (optionDescriptor === undefined)
        reject("invalid-typed-operation", "XML string option descriptor is absent");
      const matches = parseBoundedXml(xml).filter(node => node.path === wanted);
      const present = index < BigInt(matches.length) &&
        Object.prototype.hasOwnProperty.call(matches[Number(index)].attributes, attribute);
      return admitValue(optionDescriptor, Object.freeze(present
        ? [optionDescriptor, true, matches[Number(index)].attributes[attribute]]
        : [optionDescriptor, false]));
    },
    "decimal-f64-parse"(input) {
      if (typeof input !== "string")
        reject("invalid-typed-operation", "decimal input must be a string");
      const optionDescriptor = abi.descriptors.find(candidate =>
        Array.isArray(candidate) && candidate[0] === "option" && candidate[1] === "f64");
      if (optionDescriptor === undefined)
        reject("invalid-typed-operation", "decimal f64 option descriptor is absent");
      const valid = new TextEncoder().encode(input).length <= 64 &&
        /^[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]{1,3})?$/u.test(input);
      const parsed = valid ? Number(input) : Number.NaN;
      return admitValue(optionDescriptor, Object.freeze(Number.isFinite(parsed)
        ? [optionDescriptor, true, parsed]
        : [optionDescriptor, false]));
    },
    "decimal-f64x3-parse"(input) {
      if (typeof input !== "string")
        reject("invalid-typed-operation", "decimal f64x3 input must be a string");
      const optionDescriptor = abi.descriptors.find(candidate => {
        const vector = Array.isArray(candidate) && candidate[0] === "option" ? candidate[1] : null;
        return Array.isArray(vector) && vector[0] === "vector" &&
          vector[1].length === 3 && vector[1].every(type => type === "f64");
      });
      if (optionDescriptor === undefined)
        reject("invalid-typed-operation", "decimal f64x3 option descriptor is absent");
      const bytes = new TextEncoder().encode(input).length;
      const allowed = bytes <= 194 && /^[0-9eE+.\- \t\r\n]+$/u.test(input);
      const stripped = allowed ? input.replace(/^[ \t\r\n]+|[ \t\r\n]+$/gu, "") : "";
      const parts = stripped === "" ? [] : stripped.split(/[ \t\r\n]+/u);
      const decimal = /^[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]{1,3})?$/u;
      const values = parts.map(part => part.length <= 64 && decimal.test(part) ? Number(part) : Number.NaN);
      const present = parts.length === 3 && values.every(Number.isFinite);
      const vectorDescriptor = optionDescriptor[1];
      const vector = present
        ? admitValue(vectorDescriptor, Object.freeze([vectorDescriptor, ...values]))
        : null;
      return admitValue(optionDescriptor, Object.freeze(present
        ? [optionDescriptor, true, vector]
        : [optionDescriptor, false]));
    }
  });
  const assoc = (descriptorId, value, index, replacement) => {
    const descriptor = descriptorAt(descriptorId);
    const checked = assertValue(descriptor, value);
    if (descriptor[0] === "vector-i64") {
      if (!Number.isInteger(index) || index < 0 || index >= checked.length - 1)
        reject("invalid-typed-operation", "vector-i64 assoc index is invalid");
      const result = [...checked];
      result[index + 1] = i64(replacement);
      return admitValue(descriptor, Object.freeze(result));
    }
    const types = descriptor[0] === "vector" ? descriptor[1]
      : descriptor[0] === "record" ? descriptor[2].map(([, type]) => type) : null;
    if (types === null || !Number.isInteger(index) || index < 0 || index >= types.length)
      reject("invalid-typed-operation", "typed assoc index is invalid");
    assertValue(types[index], replacement);
    const result = [...checked];
    result[index + 1] = replacement;
    return admitValue(descriptor, Object.freeze(result));
  };
  const setOperation = (descriptorId, value, operation, item) => {
    const descriptor = descriptorAt(descriptorId);
    if (!Array.isArray(descriptor) || descriptor[0] !== "set")
      reject("invalid-typed-operation", "set operation requires a set descriptor");
    const checked = assertValue(descriptor, value);
    assertValue(descriptor[1], item);
    const found = checked[1].some(existing => compareValue(descriptor[1], existing, item) === 0);
    if (operation === 0) return found;
    let items;
    if (operation === 1) {
      if (found) return checked;
      if (checked[1].length >= 32) reject("invalid-typed-set", "typed set item budget exceeded");
      items = [...checked[1], item].sort((left, right) => compareValue(descriptor[1], left, right));
    } else if (operation === 2) {
      items = checked[1].filter(existing => compareValue(descriptor[1], existing, item) !== 0);
    } else reject("invalid-typed-operation", "unknown typed set operation");
    return admitValue(descriptor, Object.freeze([descriptor, Object.freeze(items)]));
  };
  const setContains = (descriptorId, value, item) => {
    const descriptor = descriptorAt(descriptorId);
    if (!Array.isArray(descriptor) || descriptor[0] !== "set")
      reject("invalid-typed-operation", "set contains requires a set descriptor");
    const checked = assertValue(descriptor, value);
    assertValue(descriptor[1], item);
    return checked[1].some(existing => compareValue(descriptor[1], existing, item) === 0);
  };
  /** T8.3 typed-set-nth: index into sorted set items (KIR ADR 0024 / compiler ADR 0194). */
  const setNth = (descriptorId, value, index, i64Item) => {
    const descriptor = descriptorAt(descriptorId);
    if (!Array.isArray(descriptor) || descriptor[0] !== "set")
      reject("invalid-typed-operation", "set nth requires a set descriptor");
    const checked = assertValue(descriptor, value);
    const items = checked[1];
    if (index < 0n || index >= BigInt(items.length))
      reject("invalid-typed-operation", "set index out of bounds");
    const item = items[Number(index)];
    assertValue(descriptor[1], item);
    return i64Item ? i64(item) : item;
  };
  const checkedMap = (descriptorId, value) => {
    const descriptor = descriptorAt(descriptorId);
    if (!Array.isArray(descriptor) || descriptor[0] !== "map")
      reject("invalid-typed-operation", "map operation requires a map descriptor");
    return [descriptor, assertValue(descriptor, value)];
  };
  const stringIndexEntry = (descriptorId, value, key) => {
    const descriptor = descriptorAt(descriptorId);
    if (!Array.isArray(descriptor) || descriptor[0] !== "string-index" || typeof key !== "string")
      reject("invalid-typed-operation", "string-index operation requires its descriptor and string key");
    if (utf8Length(key) > 65536) reject("invalid-typed-value", "string-index key is oversized");
    const checked = assertValue(descriptor, value);
    return [descriptor, checked, checked[1].findIndex(entry => entry[0] === key)];
  };
  const mapIndex = (descriptorId, value, key) => {
    const [descriptor, checked] = checkedMap(descriptorId, value);
    assertValue(descriptor[1], key);
    return [descriptor, checked,
            checked[1].findIndex(entry => compareValue(descriptor[1], entry[0], key) === 0)];
  };
  const mapContains = (descriptorId, value, key) => mapIndex(descriptorId, value, key)[2] >= 0;
  const mapGet = (descriptorId, value, key) => {
    const [descriptor, checked, index] = mapIndex(descriptorId, value, key);
    const optionDescriptor = abi.descriptors.find(candidate =>
      Array.isArray(candidate) && candidate[0] === "option" &&
      sameDescriptor(candidate[1], descriptor[2]));
    if (optionDescriptor === undefined)
      reject("invalid-typed-operation", "typed map lookup option descriptor is absent");
    return admitValue(optionDescriptor, Object.freeze(index < 0
      ? [optionDescriptor, false]
      : [optionDescriptor, true, checked[1][index][1]]));
  };
  const mapEntryAt = (descriptorId, value, index) => {
    const [descriptor, checked] = checkedMap(descriptorId, value);
    const entryDescriptor = abi.descriptors.find(candidate =>
      Array.isArray(candidate) && candidate[0] === "vector" && candidate[1].length === 2 &&
      sameDescriptor(candidate[1][0], descriptor[1]) && sameDescriptor(candidate[1][1], descriptor[2]));
    const optionDescriptor = abi.descriptors.find(candidate =>
      Array.isArray(candidate) && candidate[0] === "option" &&
      sameDescriptor(candidate[1], entryDescriptor));
    if (entryDescriptor === undefined || optionDescriptor === undefined)
      reject("invalid-typed-operation", "typed map entry option descriptor is absent");
    if (index < 0n || index >= BigInt(checked[1].length))
      return admitValue(optionDescriptor, Object.freeze([optionDescriptor, false]));
    const entry = checked[1][Number(index)];
    const entryValue = admitValue(entryDescriptor,
      Object.freeze([entryDescriptor, entry[0], entry[1]]));
    return admitValue(optionDescriptor, Object.freeze([
      optionDescriptor, true, entryValue]));
  };
  const mapAssoc = (descriptorId, value, key, item) => {
    const [descriptor, checked, index] = mapIndex(descriptorId, value, key);
    assertValue(descriptor[2], item);
    if (index < 0 && checked[1].length >= 31)
      reject("invalid-typed-map", "typed map entry budget exceeded");
    const entries = [...checked[1]];
    const entry = Object.freeze([key, item]);
    if (index < 0) entries.push(entry); else entries[index] = entry;
    entries.sort((left, right) => compareValue(descriptor[1], left[0], right[0]));
    return admitValue(descriptor, Object.freeze([descriptor, Object.freeze(entries)]));
  };
  const mapDissoc = (descriptorId, value, key) => {
    const [descriptor, checked, index] = mapIndex(descriptorId, value, key);
    if (index < 0) return checked;
    return admitValue(descriptor, Object.freeze([
      descriptor, Object.freeze(checked[1].filter((_, itemIndex) => itemIndex !== index))]));
  };
  const vectorDescriptor = abi.descriptors.find(descriptor =>
    Array.isArray(descriptor) && descriptor[0] === "vector-i64");
  const hostVector = items => {
    if (vectorDescriptor === undefined)
      reject("invalid-typed-value", "module does not admit vector-i64 values");
    if (!Array.isArray(items) || items.length > 16384)
      reject("invalid-typed-value", "host vector-i64 input is invalid or oversized");
    return admitValue(vectorDescriptor,
      Object.freeze([vectorDescriptor, ...items.map(i64)]));
  };
  const vectorF64Descriptor = abi.descriptors.find(descriptor =>
    Array.isArray(descriptor) && descriptor[0] === "vector-f64");
  const hostVectorF64 = items => {
    if (vectorF64Descriptor === undefined)
      reject("invalid-typed-value", "module does not admit vector-f64 values");
    if (!Array.isArray(items) || items.length > 16384)
      reject("invalid-typed-value", "host vector-f64 input is invalid or oversized");
    return admitValue(vectorF64Descriptor,
      Object.freeze([vectorF64Descriptor, ...items.map(f64)]));
  };
  const stringIndexDescriptor = abi.descriptors.find(descriptor =>
    Array.isArray(descriptor) && descriptor[0] === "string-index");
  const hostStringIndex = entries => {
    if (stringIndexDescriptor === undefined)
      reject("invalid-typed-value", "module does not admit string-index values");
    if (!Array.isArray(entries) || entries.length > 128)
      reject("invalid-typed-value", "host string-index input is invalid or oversized");
    const canonical = entries.map(entry => {
      if (!Array.isArray(entry) || entry.length !== 2 || typeof entry[0] !== "string")
        reject("invalid-typed-value", "host string-index entry is invalid");
      return Object.freeze([entry[0], i64(entry[1])]);
    }).sort((left, right) => left[0] < right[0] ? -1 : left[0] > right[0] ? 1 : 0);
    return admitValue(stringIndexDescriptor,
      Object.freeze([stringIndexDescriptor, Object.freeze(canonical)]));
  };
  const disjointSetDescriptor = abi.descriptors.find(descriptor =>
    Array.isArray(descriptor) && descriptor[0] === "disjoint-set-i64");
  const hostDisjointSet = size => {
    size = i64(size);
    if (disjointSetDescriptor === undefined || size < 0n || size > 128n)
      reject("invalid-typed-value", "module does not admit requested disjoint-set-i64 value");
    const parents = Object.freeze(Array.from({length: Number(size)}, (_, index) => BigInt(index)));
    const ranks = Object.freeze(Array.from({length: Number(size)}, () => 0n));
    return admitValue(disjointSetDescriptor,
      Object.freeze([disjointSetDescriptor, parents, ranks]));
  };
  const hostDocument = value => {
    if (documentDescriptor === undefined)
      reject("invalid-typed-value", "module does not admit document values");
    return admitDocument(value);
  };
  const values = Object.freeze({
    vectorI64: hostVector,
    vectorF64: hostVectorF64,
    stringIndex: hostStringIndex,
    disjointSetI64: hostDisjointSet,
    document: hostDocument,
    bytes(items) {
      if (!(Array.isArray(items) || ArrayBuffer.isView(items)) || items.length > 16384)
        reject("invalid-typed-value", "host byte input is invalid or oversized");
      return hostVector(Array.from(items, item => {
        if (!Number.isInteger(item) || item < 0 || item > 255)
          reject("invalid-typed-value", "host byte input contains a non-byte value");
        return BigInt(item);
      }));
    }
  });
  return Object.freeze({ imports, values });
}

export function normalizeKotobaTrap(error) {
  if (error instanceof KotobaHostError)
    return Object.freeze({ kind: "kotoba-host", code: error.code });
  if (error instanceof WebAssembly.RuntimeError)
    return Object.freeze({ kind: "wasm-runtime", code: "guest-trap" });
  return Object.freeze({ kind: "host", code: "unexpected-host-error" });
}

export async function instantiateKotoba(source, rawOptions) {
  const options = exactOptions(rawOptions);
  const allow = admittedCapabilities(options.allowCapabilities);
  validateDigest(options.expectedSha256);
  if (options.capCall !== undefined && typeof options.capCall !== "function")
    reject("invalid-policy", "capCall must be a function");
  if (options.typedCapCall !== undefined && typeof options.typedCapCall !== "function")
    reject("invalid-policy", "typedCapCall must be a function");
  // A pre-compiled module is admitted as well as bytes, because some hosts
  // cannot compile at all. Cloudflare Workers refuse `WebAssembly.compile` at
  // runtime -- a module has to arrive through the bundler as an import -- and
  // measured 2026-08-31 against a deployed Worker, passing bytes there fails
  // with `invalid-module / Wasm compilation failed` no matter what the bytes
  // are. Everything below this point is unchanged: the same import allowlist,
  // the same capability denial, the same typed ABI admission.
  let module;
  let digest = null;
  if (source instanceof WebAssembly.Module) {
    // A Module cannot be hashed: its bytes are gone. Rather than quietly
    // treating an unverifiable identity as a verified one -- which would make
    // `expectedSha256` a field that sometimes checks nothing -- this refuses,
    // and `sha256` on the result is null so no reader mistakes absence for a
    // digest. A caller that needs the identity check must hash the bytes
    // before compiling them, where the bytes still exist.
    if (options.expectedSha256 !== undefined)
      reject("digest-unverifiable",
             "expectedSha256 cannot be checked against a pre-compiled WebAssembly.Module; "
             + "verify the bytes before compiling them");
    module = source;
  } else {
    const bytes = copiedBytes(source);
    digest = await sha256(bytes);
    if (options.expectedSha256 !== undefined && options.expectedSha256 !== digest)
      reject("digest-mismatch", "Wasm module SHA-256 does not match expectedSha256");
    try { module = await WebAssembly.compile(bytes); }
    catch (error) { reject("invalid-module", "Wasm compilation failed", error); }
  }
  const admission = validateModule(module);
  const typedAbi = admission.typedAbi;
  const compatibility = admission.compatibility;
  const typed = createTypedRuntime(typedAbi, options.typedCapCall, allow);
  const heap = createHeap();
  const cap = Object.freeze({
    call(id, value) {
      if (typeof id !== "bigint" || id < 0n || id > 255n || !allow.has(Number(id)))
        reject("capability-denied", "runtime capability policy denied the call");
      if (typeof options.capCall !== "function")
        reject("capability-unimplemented", "no host implementation exists for the capability");
      const result = options.capCall(Number(id), BigInt.asIntN(64, value));
      if (typeof result !== "bigint")
        reject("invalid-capability-result", "capability implementation must return bigint");
      return BigInt.asIntN(64, result);
    }
  });
  let instance;
  try {
    instance = await WebAssembly.instantiate(module, {
      "kotoba:cap": cap,
      "kotoba:heap": heap.imports,
      "kotoba:typed": typed?.imports ?? Object.freeze({})
    });
  } catch (error) {
    if (error instanceof KotobaHostError) throw error;
    reject("instantiation-failed", "Kotoba Wasm instantiation failed", error);
  }
  return Object.freeze({
    module,
    instance,
    sha256: digest,
    typedAbi,
    typedValues: typed?.values ?? null,
    compatibility,
    report: () => Object.freeze({ heap: heap.report() })
  });
}

// --- W4: logical UI :document → real DOM reconcile (host API, not a capability) ---
//
// Exit-gate piece: a guest-built :document can be reconciled into browser DOM
// without becoming a host object in the guest. Handles stay host-side.
// Tag vocabulary is the same shallow UI shape as document_ui_render_test
// (:tag string, optional :text string, optional :children vector).
// Dangerous tags are denied closed. Not the final :ui/commit capability path
// (flat node set + revision); this is the nested-document bridge.

const UI_DOC_TAG_RE = /^[a-z][a-z0-9-]*$/;
const UI_DOC_DENIED_TAGS = new Set([
  "script", "iframe", "object", "embed", "frame", "frameset",
  "base", "link", "meta", "style", "template", "foreignobject"
]);

function uiDocMapEntries(node) {
  if (!Array.isArray(node) || node[0] !== "map" || !Array.isArray(node[1]))
    reject("invalid-ui-document", "UI document root must be a map");
  return node[1];
}

function uiDocGet(node, key) {
  const want = key.startsWith(":") ? key : `:${key}`;
  for (const entry of uiDocMapEntries(node)) {
    if (Array.isArray(entry) &&
        (entry[0] === want ||
         (Array.isArray(entry[0]) && entry[0][0] === "keyword" && entry[0][1] === want)))
      return entry[1];
  }
  return undefined;
}

function uiDocStringField(node, key, fallback = "") {
  const item = uiDocGet(node, key);
  if (item === undefined) return fallback;
  if (!Array.isArray(item) || item[0] !== "string" || typeof item[1] !== "string")
    reject("invalid-ui-document", `UI document field ${key} must be a string`);
  return item[1];
}

function uiDocChildren(node) {
  const item = uiDocGet(node, "children");
  if (item === undefined) return [];
  if (!Array.isArray(item) || item[0] !== "vector" || !Array.isArray(item[1]))
    reject("invalid-ui-document", "UI document :children must be a vector");
  if (item[1].length > 32)
    reject("invalid-ui-document", "UI document children budget exceeded");
  return item[1];
}

function uiDocTag(node) {
  const tag = uiDocStringField(node, "tag", "");
  if (!tag || !UI_DOC_TAG_RE.test(tag) || UI_DOC_DENIED_TAGS.has(tag))
    reject("invalid-ui-document", `UI document tag is denied or invalid: ${tag || "(missing)"}`);
  return tag;
}

// `:attrs` reaches the DOM reconciler on the same deny-by-default terms the
// rest of this bridge already uses. It is NOT new authority: the W4 UI
// vocabulary already carries `:attrs` and kotoba-lang/html's string renderer
// already emits it (`render-attrs`/`render-attr-entry` in html_document.kotoba),
// so a reconciler that ignored attributes made the two renderers disagree on
// the same guest value -- the dual-renderer parity this bridge exists to hold.
//
// The guest still never names a DOM API, holds a handle, or supplies
// behaviour. An attribute is a string a host may choose to apply; every
// listener is host-owned (see dom-driver.mjs). ADR 0025's exclusions are kept
// literally: no HTML injection (`innerHTML` is never written), no CSS
// evaluation (`style` is denied, not allowlisted), no event handlers (`on*` is
// denied ahead of the allowlist so a future allowlist edit cannot open it).
const UI_ATTR_NAME_RE = /^[a-z][a-z0-9-]*$/;
const UI_ATTR_ALLOWED = new Set([
  "class", "id", "title", "type", "value", "placeholder", "alt", "role",
  "for", "name", "lang", "dir", "tabindex", "hidden", "disabled", "checked",
  "selected", "readonly", "required", "multiple", "maxlength", "rows", "cols",
  "min", "max", "step", "colspan", "rowspan", "width", "height", "href", "src"
]);
// Prefix families carry no behaviour and are the accessibility/nominal-identity
// surface an application actually needs (`data-k` is how dom-driver.mjs routes
// an event back to a guest-chosen name).
const UI_ATTR_ALLOWED_PREFIXES = ["aria-", "data-"];
// Only `href`/`src` carry a URL. Anything that is not same-document, root- or
// dot-relative, https/http, or mailto is denied -- which is what closes
// `javascript:` and `data:` without this file growing a URL parser.
const UI_ATTR_URL_NAMES = new Set(["href", "src"]);
const UI_ATTR_SAFE_URL_RE = /^(?:https?:\/\/|\/|\.{1,2}\/|#|mailto:)/;
const UI_ATTR_MAX_PER_NODE = 32;
const UI_ATTR_MAX_NAME_BYTES = 64;
const UI_ATTR_MAX_VALUE_BYTES = 1024;

// The typed-value reader has its own `utf8Length` bound inside its closure;
// this bridge needs the same measure at module scope. Strings arriving here
// already passed the guest boundary, so this counts bytes and does not
// re-validate surrogate pairing.
const uiUtf8Length = value => new TextEncoder().encode(value).byteLength;

function uiAttrNameAdmitted(name) {
  if (!UI_ATTR_NAME_RE.test(name)) return false;
  if (name.startsWith("on")) return false;
  if (name === "style") return false;
  if (UI_ATTR_ALLOWED.has(name)) return true;
  return UI_ATTR_ALLOWED_PREFIXES.some(prefix =>
    name.startsWith(prefix) && name.length > prefix.length);
}

/**
 * Read the `:attrs` map of a UI document node into [name, value] pairs.
 *
 * A `["bool", …]` value is an HTML boolean attribute (same reading as
 * html_document.kotoba's `bool-attr`): true sets it present with an empty
 * value, false omits it entirely.
 *
 * @returns {Array<[string, string]>} admitted attributes, source order
 */
function uiDocAttrs(node) {
  const item = uiDocGet(node, "attrs");
  if (item === undefined) return [];
  if (!Array.isArray(item) || item[0] !== "map" || !Array.isArray(item[1]))
    reject("invalid-ui-document", "UI document :attrs must be a map");
  const entries = item[1];
  if (entries.length > UI_ATTR_MAX_PER_NODE)
    reject("invalid-ui-document", "UI document :attrs budget exceeded");
  const pairs = [];
  for (const entry of entries) {
    if (!Array.isArray(entry) || entry.length !== 2)
      reject("invalid-ui-document", "UI document :attrs entry must be a pair");
    const key = entry[0];
    const raw = Array.isArray(key) && key[0] === "keyword" ? key[1]
      : typeof key === "string" ? key : null;
    if (raw === null)
      reject("invalid-ui-document", "UI document :attrs key must be a keyword");
    const name = raw.startsWith(":") ? raw.slice(1) : raw;
    if (uiUtf8Length(name) > UI_ATTR_MAX_NAME_BYTES)
      reject("invalid-ui-document", `UI document attribute name too long: ${name}`);
    if (!uiAttrNameAdmitted(name))
      reject("invalid-ui-document", `UI document attribute is denied: ${name}`);
    const valueItem = entry[1];
    if (!Array.isArray(valueItem))
      reject("invalid-ui-document", `UI document attribute ${name} must be a value`);
    let value;
    if (valueItem[0] === "bool") {
      if (valueItem[1] !== true && valueItem[1] !== false)
        reject("invalid-ui-document", `UI document attribute ${name} must be a boolean`);
      if (valueItem[1] === false) continue;
      value = "";
    } else if (valueItem[0] === "string" && typeof valueItem[1] === "string") {
      value = valueItem[1];
    } else {
      reject("invalid-ui-document",
             `UI document attribute ${name} must be a string or boolean`);
    }
    if (uiUtf8Length(value) > UI_ATTR_MAX_VALUE_BYTES)
      reject("invalid-ui-document", `UI document attribute value too long: ${name}`);
    if (UI_ATTR_URL_NAMES.has(name) && !UI_ATTR_SAFE_URL_RE.test(value))
      reject("invalid-ui-document", `UI document attribute ${name} has a denied URL scheme`);
    pairs.push([name, value]);
  }
  return pairs;
}

// Form controls keep a live property that stops tracking its attribute the
// moment a user edits the field (HTML calls it the dirty value flag). Setting
// `value="…"` on an input the user has typed into therefore changes nothing on
// screen -- so a guest that owns the field's contents could never clear it.
// These tags get the property written as well as the attribute.
const UI_VALUE_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);
const UI_CHECKED_TAGS = new Set(["INPUT"]);

/**
 * Apply admitted attributes to an element and remove the ones this render
 * dropped. Without the removal half, a reconciled element would accumulate
 * every attribute any earlier state ever set.
 */
function applyUiAttrs(element, pairs) {
  if (typeof element.setAttribute !== "function" ||
      typeof element.removeAttribute !== "function")
    reject("dom-unavailable", "DOM setAttribute/removeAttribute required for :attrs");
  const wanted = new Map(pairs);
  const present = typeof element.getAttributeNames === "function"
    ? element.getAttributeNames() : [];
  for (const name of present) {
    // Only attributes this bridge could have written are removable; anything
    // the host page put on its own mount point is left alone.
    if (!wanted.has(name) && uiAttrNameAdmitted(name)) element.removeAttribute(name);
  }
  for (const [name, value] of wanted) {
    if (typeof element.getAttribute === "function" &&
        element.getAttribute(name) === value) continue;
    element.setAttribute(name, value);
  }
  const tag = element.tagName;
  if (UI_VALUE_TAGS.has(tag)) {
    // Absent `:value` means the guest is not controlling this field, so its
    // property is left exactly as the user left it.
    const value = wanted.has("value") ? wanted.get("value")
      : present.includes("value") ? "" : undefined;
    // Compare before writing: assigning `value` unconditionally would move the
    // caret to the end on every keystroke of a controlled field.
    if (value !== undefined && element.value !== value) element.value = value;
  }
  if (UI_CHECKED_TAGS.has(tag)) {
    const checked = wanted.has("checked") ? true
      : present.includes("checked") ? false : undefined;
    if (checked !== undefined && element.checked !== checked) element.checked = checked;
  }
}

/**
 * Reconcile a logical UI :document into a DOM container element.
 *
 * @param {Element} container mount point (existing host element; not replaced)
 * @param {Array} doc guest :document value (map with :tag / optional :text / :children)
 * @param {{createElement?: Function, createTextNode?: Function}} [dom]
 *        DOM factory; defaults to globalThis.document. Tests may inject a mock.
 * @returns {Element} the element reconciled as container's first element child
 */
export function reconcileUiDocument(container, doc, dom = {}) {
  if (container == null || typeof container !== "object")
    reject("invalid-ui-document", "reconcile container is required");
  const createElement = dom.createElement
    || (typeof globalThis.document?.createElement === "function"
      ? globalThis.document.createElement.bind(globalThis.document) : null);
  const createTextNode = dom.createTextNode
    || (typeof globalThis.document?.createTextNode === "function"
      ? globalThis.document.createTextNode.bind(globalThis.document) : null);
  if (typeof createElement !== "function" || typeof createTextNode !== "function")
    reject("dom-unavailable", "DOM createElement/createTextNode required for reconcile");

  const ensureChild = (parent, index, tag) => {
    const existing = parent.childNodes?.[index];
    const tagUpper = tag.toUpperCase();
    if (existing && existing.nodeType === 1 && existing.tagName === tagUpper)
      return existing;
    const el = createElement(tag);
    if (existing) {
      if (typeof parent.replaceChild === "function") parent.replaceChild(el, existing);
      else reject("dom-unavailable", "DOM replaceChild required");
    } else if (typeof parent.appendChild === "function") {
      parent.appendChild(el);
    } else {
      reject("dom-unavailable", "DOM appendChild required");
    }
    return el;
  };

  const trimAfter = (parent, keep) => {
    while ((parent.childNodes?.length ?? 0) > keep) {
      const last = parent.childNodes[parent.childNodes.length - 1];
      if (typeof parent.removeChild === "function") parent.removeChild(last);
      else reject("dom-unavailable", "DOM removeChild required");
    }
  };

  const walk = (parent, index, node) => {
    const tag = uiDocTag(node);
    // Read attributes before touching the DOM: a denied name or URL scheme
    // must reject the whole reconcile, not leave a half-applied element.
    const attrs = uiDocAttrs(node);
    const el = ensureChild(parent, index, tag);
    applyUiAttrs(el, attrs);
    const text = uiDocStringField(node, "text", "");
    const kids = uiDocChildren(node);
    if (kids.length === 0) {
      // Leaf: textContent is the single source of truth (clears element children).
      if (el.textContent !== text) el.textContent = text;
      return el;
    }
    // Branch: ignore :text; reconcile element/text children from the vector only.
    for (let i = 0; i < kids.length; i++) walk(el, i, kids[i]);
    trimAfter(el, kids.length);
    return el;
  };

  const root = walk(container, 0, doc);
  trimAfter(container, 1);
  return root;
}

/**
 * Minimal DOM mock for Node tests (no linkedom dependency).
 * Enough of Element/Node for reconcileUiDocument.
 */
export function createMockDom() {
  let seq = 0;
  const makeText = data => {
    const node = {
      nodeType: 3,
      nodeName: "#text",
      data: String(data),
      get textContent() { return this.data; },
      set textContent(v) { this.data = String(v); },
      childNodes: []
    };
    return node;
  };
  const makeEl = tag => {
    const childNodes = [];
    const attributes = new Map();
    const listeners = new Map();
    const el = {
      nodeType: 1,
      tagName: String(tag).toUpperCase(),
      id: `mock-${++seq}`,
      childNodes,
      parentNode: null,
      get children() { return childNodes.filter(c => c.nodeType === 1); },
      get textContent() {
        return childNodes.map(c => c.nodeType === 3 ? c.data : c.textContent).join("");
      },
      set textContent(v) {
        childNodes.length = 0;
        if (v !== "") childNodes.push(makeText(v));
      },
      appendChild(child) {
        childNodes.push(child);
        if (child && typeof child === "object") child.parentNode = el;
        return child;
      },
      removeChild(child) {
        const i = childNodes.indexOf(child);
        if (i < 0) throw new Error("not-found");
        childNodes.splice(i, 1);
        if (child && typeof child === "object") child.parentNode = null;
        return child;
      },
      replaceChild(next, prev) {
        const i = childNodes.indexOf(prev);
        if (i < 0) throw new Error("not-found");
        childNodes[i] = next;
        if (next && typeof next === "object") next.parentNode = el;
        if (prev && typeof prev === "object") prev.parentNode = null;
        return prev;
      },
      // Attribute surface used by reconcileUiDocument's `:attrs` support.
      //
      // `value` and `checked` are deliberately NOT mirrored from the
      // attribute. A real form control stops tracking its attribute once the
      // user edits it, and an earlier version of this mock did mirror -- which
      // hid a bug where a guest could never clear a field it owned, right up
      // until the Playwright run caught it in Chromium. A mock that is kinder
      // than the platform is worse than no mock.
      value: "",
      checked: false,
      setAttribute(name, value) {
        attributes.set(String(name), String(value));
      },
      getAttribute(name) {
        return attributes.has(String(name)) ? attributes.get(String(name)) : null;
      },
      removeAttribute(name) {
        attributes.delete(String(name));
      },
      getAttributeNames() { return [...attributes.keys()]; },
      hasAttribute(name) { return attributes.has(String(name)); },
      // Enough of EventTarget for dom-driver.mjs: listeners registered on the
      // container, events dispatched at a descendant and bubbled up. No
      // capture phase, no stopPropagation -- the driver uses neither.
      addEventListener(kind, handler) {
        const bucket = listeners.get(kind) || [];
        bucket.push(handler);
        listeners.set(kind, bucket);
      },
      removeEventListener(kind, handler) {
        const bucket = listeners.get(kind) || [];
        const i = bucket.indexOf(handler);
        if (i >= 0) bucket.splice(i, 1);
      },
      listeners
    };
    return el;
  };
  return Object.freeze({
    createElement: makeEl,
    createTextNode: makeText,
    createContainer: () => makeEl("div"),
    // Dispatch `kind` at `target` and let it bubble, the way a real click on a
    // nested button reaches a container-level listener.
    dispatch: (target, kind, extra = {}) => {
      let node = target;
      while (node) {
        for (const handler of [...(node.listeners?.get(kind) || [])])
          handler({ type: kind, target, currentTarget: node, ...extra });
        node = node.parentNode;
      }
    }
  });
}

export const browserProfile = Object.freeze({
  format: "kotoba.browser-host/v1",
  maxModuleBytes: MAX_MODULE_BYTES,
  pairCapacity: PAIR_CAPACITY,
  typedAbiVersion: TYPED_ABI_VERSION,
  compatibilityVersion: COMPATIBILITY_VERSION,
  imports: Object.freeze(Array.from(ALLOWED_IMPORTS).sort())
});
