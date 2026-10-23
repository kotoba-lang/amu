// wasm32-browser-static/v1 Worker host (JUN-353). Static and dependency-free:
// no fetch, no network, no imports. It instantiates one module produced by
// `amu compile SRC --target wasm32-browser` (seed/81 + seed/82: the guest and
// the Kotoba runtime in one module), calls its export start(fuel) and returns
// what the run wrote:
//   {exit, stdout, stderr, wasmTrap}
// stdout carries the native KEXE_STRUCTURED_REPORT line
// ({:status :ok :result R :fuel {...}} or {:status :trap :exit 120 :fuel {...}}).
//
// Imports (module "kotoba:host"), all i64:
//   write(fd, ptr, len) -> len   fd 1 = stdout, 2 = stderr; other fds -> -9 (EBADF)
//   cap(wire, ptr, len) -> -1    every capability is refused in Phase 1; this is
//                                where the shared consent broker
//                                (kotoba-client-runtime.js) plugs in (Phase 2)
//   now() -> nanoseconds since the epoch
//   exit(code)                   ends the run (throws out of the module)
//
// The function is written so that a page can start it as a Worker from a Blob
// (`(${kotobaWasm32BrowserStaticHost})()`), which works from file:// pages, and
// it installs itself when this file is loaded as a Worker script.
"use strict";
function kotobaWasm32BrowserStaticHost() {
  class HostExit {
    constructor(code) { this.code = code; }
  }
  function concat(chunks) {
    let n = 0;
    for (const c of chunks) n += c.length;
    const all = new Uint8Array(n);
    let at = 0;
    for (const c of chunks) { all.set(c, at); at += c.length; }
    return new TextDecoder("utf-8").decode(all);
  }
  async function run(bytes, fuel) {
    const stdout = [], stderr = [];
    let memory = null;
    const imports = {
      "kotoba:host": {
        write(fd, ptr, len) {
          if (fd !== 1n && fd !== 2n) return -9n;
          const chunk = new Uint8Array(memory.buffer, Number(ptr), Number(len)).slice();
          (fd === 1n ? stdout : stderr).push(chunk);
          return len;
        },
        cap(wire, ptr, len) { return -1n; },
        now() { return BigInt(Date.now()) * 1000000n; },
        exit(code) { throw new HostExit(Number(code)); },
      },
    };
    let exit = null, wasmTrap = null;
    try {
      const { instance } = await WebAssembly.instantiate(bytes, imports);
      memory = instance.exports.memory;
      instance.exports.start(BigInt(fuel));
      wasmTrap = "start returned without exit";
    } catch (e) {
      if (e instanceof HostExit) exit = e.code;
      else wasmTrap = String((e && e.message) || e);
    }
    // A wasm trap outside the runtime's handler (for example stack exhaustion)
    // ends the run as a native signal would: exit 120.
    if (exit === null) exit = 120;
    return { exit, stdout: concat(stdout), stderr: concat(stderr), wasmTrap };
  }
  self.onmessage = async (e) => {
    self.postMessage(await run(e.data.bytes, e.data.fuel));
  };
}
if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  kotobaWasm32BrowserStaticHost();
}
