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
`scripts/build-ipld-adl-wasmtime.sh`. Each call creates a fresh Wasmtime Store,
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
