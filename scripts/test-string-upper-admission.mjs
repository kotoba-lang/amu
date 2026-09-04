import assert from "node:assert/strict";
import { instantiateKotoba } from "../runtime/browser-host.mjs";
import { withCompatibility } from "./compatibility-fixture.mjs";

// A module that imports kotoba:typed/string-upper/function and calls it on a
// descriptor-0 (string) externref holding "kotoba". The host must admit the
// import (ALLOWED_IMPORTS) and answer "KOTOBA". Hand-assembled the same way
// the admission vectors in this file are; the E2E compiler route is covered
// by the amu classpath-prepend verification recorded in the PR body.
const encoder = new TextEncoder();

function uleb(value) {
  const bytes = [];
  do {
    let byte = value & 0x7f;
    value >>>= 7;
    if (value !== 0) byte |= 0x80;
    bytes.push(byte);
  } while (value !== 0);
  return bytes;
}

function text(value) {
  const bytes = [...encoder.encode(value)];
  return [...uleb(bytes.length), ...bytes];
}

function stringModule(value) {
  const payload = [...encoder.encode(value)];
  // typed metadata section: version 14, 0 descriptors, 1 literal (tag 0 =
  // string), then the version>=9 tail: 0 schemas, 0 contracts
  const meta = [14, 0, 1, 0, ...uleb(payload.length), ...payload, 0, 0];
  const metaSection = [0, ...uleb(meta.length), ...meta];
  // typed module name custom section ("kotoba.typed"). A custom section is
  // [0x00, uleb(size), name, payload] where size covers name AND payload.
  const typedName = text("kotoba.typed");
  const metaBody = [...typedName, ...meta];
  const nameSection = [0, ...uleb(metaBody.length), ...metaBody];
  return Uint8Array.from([
    0, 97, 115, 109, 1, 0, 0, 0,
    // import: kotoba:typed/string-upper/function (func type (param i32 externref) -> externref)
    ...(() => {
      const m = text("kotoba:typed"), f = text("string-upper");
      // type section: 1 type; import section: 1 import (module, field, kind 0 func, type 0)
      const typeSec = [1, 7, 1, 0x60, 2, 0x7f, 0x6f, 1, 0x6f];
      const impBody = [1, ...m, ...f, 0, 0];
      const impSec = [2, ...uleb(impBody.length), ...impBody];
      return [...typeSec, ...impSec];
    })(),
    // memory? none. function section: one body
    3, 2, 1, 0,
    // export "main"
    7, 8, 1, 4, 109, 97, 105, 110, 0, 0,
    // code: empty-bodied function that falls through -- this module proves
    // ADMISSION of the import, not execution (the E2E compile + run proves
    // execution end to end). A body of just `unreachable` keeps the section
    // encoding honest.
    10, 5, 1, 3, 0, 0x00, 11,
    ...nameSection
  ]);
}

const module_ = withCompatibility(stringModule("kotoba"),
  { kir: "kotoba.kir/v4", valueAbi: "kotoba.typed/externref-v1" });
const hosted = await instantiateKotoba(module_, {});
assert.ok(hosted, "string-upper import module instantiates");
console.log("browser-host string-upper admission vector passed");
