// wasm32-browser-static/v1 Worker host (JUN-353), and js-browser-static/v1 (ADR 0397): a message
// carrying js (the ES module text `amu compile SRC --target js-browser` produced) instead of bytes or
// module is imported from a Blob URL and run through instantiate(host) -> {memory, start} with the
// same five host functions; a JS module has no JSPI, so its cap is always the refusing one. Its
// memory.buffer is a resizable ArrayBuffer, which TextDecoder refuses to read in Chrome, so the host
// decodes copies of guest bytes (.slice()) on both targets. Static and dependency-free:
// no fetch, no network, no imports. It instantiates one module produced by
// `amu compile SRC --target wasm32-browser` (seed/81 + seed/82: the guest and
// the Kotoba runtime in one module), calls its export start(fuel) and returns
// what the run wrote:
//   {exit, stdout, stderr, wasmTrap, output, report}
// stdout carries the native KEXE_STRUCTURED_REPORT line last
// ({:status :ok :result R :fuel {...}} or {:status :trap :exit 120 :fuel {...}});
// report is that line and output is stdout before it.
//
// Message in: {bytes | module, fuel, allow?, args?, files?, bind?, localStdio?}. bytes is the
// module's bytes (or module an already compiled WebAssembly.Module); allow
// lists the wires the page grants, as KEXE_ALLOW does natively, and only
// 35 (:fs/app-data, read-only), 37 (:io/write), 38 (:cli/args) and
// 39 (:io/write-error) can ordinarily be granted. With localStdio, wire 41
// is additionally available for local input. args is the command line as strings
// (without a program name); files maps absolute paths to strings or
// Uint8Arrays. They are the run's own data, held by the page in this browser:
// the entry ABI (seed/82) reads them, and nothing else. Without allow every
// wire is refused, as in Phase 1.
//
// bind (Phase 2, restricted-wasm-v1 only) lists the wires that the trusted
// host page has bound to one operation of its kotoba.app.client-runtime.v1
// descriptor; 35, 37, 38 and 39 cannot be bound, and 41 cannot be bound when
// localStdio is enabled. The page grants bound wires too, and
// a guest call of a bound wire goes to the shared consent broker
// (kotoba-client-runtime.js) through the restricted guest shell
// (wasm32-browser-restricted-guest.html): this Worker posts
// {cap: {id, wire, payload}} and suspends the guest (JSPI,
// WebAssembly.Suspending) until {capReply: {id, ok, status, content, error}}
// arrives. Without JSPI, or for an unbound wire, cap refuses (-1) without
// posting anything. This Worker holds no network authority: the broker on the
// trusted page validates, asks for consent and sends.
//
// localStdio is a separate, explicit user-side protocol. When true and wire
// 41 is granted in allow, a JSPI-capable Wasm guest can request local stdin:
// {localRead:{id,request}} -> {localReadReply:{id,ok,content}}. Local stdout
// and stderr are also streamed as {localOutput:{fd,bytes}}. These messages
// do not reach a service or grant network authority. Wire 41 cannot at the
// same time be bound to a broker operation. Without JSPI reads fail closed.
// For localStdio, only the last 64 KiB of each stream is retained in the final
// result; stdoutTruncated/stderrTruncated indicate earlier streamed data.
// localOutputAck opts into JSPI backpressure: at most one 64 KiB output
// chunk is in flight, and a negative acknowledgement traps the guest. It
// requires localStdio and JSPI; no unbounded fallback is used in this mode.
//
// Imports (module "kotoba:host"), all i64:
//   write(fd, ptr, len) -> len   fd 1 = stdout, 2 = stderr; other fds -> -9 (EBADF)
//   cap(wire, ptr, len) -> length or -1
//                                an unbound wire -> -1. A bound wire's request
//                                (UTF-8 "METHOD TARGET", then optionally "\n"
//                                and the body; TARGET is resolved against the
//                                declared endpoint's origin by the broker)
//                                goes to the broker; the answer is the length
//                                of "STATUS\n" + the response text, or -1 for
//                                every refusal (undeclared, denied, failed)
//   now() -> nanoseconds since the epoch
//   exit(code)                   ends the run (throws out of the module)
//   input(kind, i, ptr, len, dst, cap) -> length or -1
//                                the entry ABI: kind 0 is argument i (i = -1:
//                                the count), kind 1 the file whose absolute
//                                path is the UTF-8 bytes [ptr, ptr+len); the
//                                bytes are copied to dst only when cap >= the
//                                length. Serves :cli/args and read-only
//                                :fs/app-data (wires 38, 35). kind 2 asks
//                                whether the page grants wire i (1 or 0).
//                                kind 3 copies the last cap answer to dst.
//                                Not a capability: no service is reached.
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
  // "/a/./b/../c" -> "/a/c"; null when not absolute
  function normal(path) {
    if (!path.startsWith("/")) return null;
    const out = [];
    for (const part of path.split("/")) {
      if (part === "" || part === ".") continue;
      if (part === "..") out.pop(); else out.push(part);
    }
    return "/" + out.join("/");
  }
  function inputs(args, files) {
    const enc = new TextEncoder();
    const argv = (args || []).map((a) => enc.encode(String(a)));
    const fs = new Map();
    for (const [k, v] of Object.entries(files || {})) {
      const p = normal(k);
      if (p !== null) fs.set(p, typeof v === "string" ? enc.encode(v) : new Uint8Array(v));
    }
    return { argv, fs };
  }
  async function run(msg) {
    const fuel = msg.fuel || 0;
    const { argv, fs } = inputs(msg.args, msg.files);
    const localStdio = msg.localStdio === true && msg.js === undefined;
    const outputAck = msg.localOutputAck === true;
    const supportsJspi = typeof WebAssembly.Suspending === "function" && typeof WebAssembly.promising === "function";
    if (outputAck && (!localStdio || !supportsJspi)) {
      return { exit: 120, stdout: "", stderr: "", output: "", report: null,
               wasmTrap: "local output acknowledgement requires localStdio and JSPI", capLog: [] };
    }
    const requestedBindings = (msg.bind || []).map(Number);
    if (localStdio && requestedBindings.includes(41)) {
      return { exit: 120, stdout: "", stderr: "", output: "", report: null,
               wasmTrap: "wire 41 cannot be both local stdin and broker-bound", capLog: [] };
    }
    const local = localStdio ? [35, 37, 38, 39, 41] : [35, 37, 38, 39];
    const allow = new Set((msg.allow || []).map(Number).filter((w) => local.includes(w)));
    const bound = new Set((msg.bind || []).map(Number).filter((w) => Number.isInteger(w) && w >= 0 && w < 64 && !local.includes(w)));
    const jspi = msg.js === undefined && (bound.size > 0 || (localStdio && allow.has(41)) || outputAck) && supportsJspi;
    const capLog = [];
    let localReadLogCount = 0, localReadLogTruncated = false;
    let capAnswer = undefined;
    const stdout = [], stderr = [];
    const retained = { 1: 0, 2: 0 }, truncated = { 1: false, 2: false };
    function capture(fd, chunk) {
      const chunks = fd === 1 ? stdout : stderr;
      chunks.push(chunk);
      if (!localStdio) return;
      retained[fd] += chunk.length;
      while (retained[fd] > 65536) {
        const excess = retained[fd] - 65536, first = chunks[0];
        if (first.length <= excess) { chunks.shift(); retained[fd] -= first.length; }
        else { chunks[0] = first.slice(excess); retained[fd] -= excess; }
        truncated[fd] = true;
      }
    }
    let memory = null;
    const answer = (bytes, dst, cap) => {
      if (bytes === undefined) return -1n;
      if (cap >= BigInt(bytes.length) && bytes.length > 0) {
        new Uint8Array(memory.buffer, Number(dst), bytes.length).set(bytes);
      }
      return BigInt(bytes.length);
    };
    const imports = {
      "kotoba:host": {
        write: outputAck ? new WebAssembly.Suspending(async (fd, ptr, len) => {
          if (fd !== 1n && fd !== 2n) return -9n;
          const start = Number(ptr), length = Number(len);
          if (!Number.isSafeInteger(start) || !Number.isSafeInteger(length) || start < 0 || length < 0 ||
              start + length > memory.buffer.byteLength) throw new Error("invalid local output range");
          for (let offset = 0; offset < length; offset += 65536) {
            const chunk = new Uint8Array(memory.buffer, start + offset, Math.min(65536, length - offset)).slice();
            const reply = await self.kotobaLocalOutput(Number(fd), chunk);
            if (!reply || reply.ok !== true) throw new Error("local output refused");
            capture(Number(fd), chunk);
          }
          return len;
        }) : function write(fd, ptr, len) {
          if (fd !== 1n && fd !== 2n) return -9n;
          const chunk = new Uint8Array(memory.buffer, Number(ptr), Number(len)).slice();
          capture(Number(fd), chunk);
          if (localStdio && chunk.length) self.postMessage({ localOutput: { fd: Number(fd), bytes: chunk } });
          return len;
        },
        cap: jspi ? new WebAssembly.Suspending(async (wire, ptr, len) => {
          capAnswer = undefined;
          const w = Number(wire);
          let request;
          try {
            request = new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(memory.buffer, Number(ptr), Number(len)).slice());
          } catch (e) { capLog.push({ wire: w, outcome: "refused", error: "request is not UTF-8" }); return -1n; }
          if (w === 41 && localStdio && allow.has(41)) {
            if (!/^(?:|0|[1-9][0-9]{0,6})$/.test(request) || Number(request || 0) > 1048576) return -1n;
            if (request === "0") { capAnswer = new Uint8Array(); return 0n; }
            const reply = await self.kotobaLocalRead(request);
            if (!reply || reply.ok !== true || typeof reply.content !== "string") return -1n;
            const content = reply.content;
            if (content.length > 1048576) return -1n;
            for (let i = 0; i < content.length; i++) {
              const c = content.charCodeAt(i);
              if (c >= 0xd800 && c <= 0xdbff) {
                if (++i >= content.length || content.charCodeAt(i) < 0xdc00 || content.charCodeAt(i) > 0xdfff) return -1n;
              } else if (c >= 0xdc00 && c <= 0xdfff) return -1n;
            }
            const bytes = new TextEncoder().encode(content);
            const limit = request === "" ? 1048576 : Number(request);
            if (bytes.length > limit + (request === "" ? 0 : 3)) return -1n;
            if (request !== "" && bytes.length > limit) {
              try { new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(0, limit)); return -1n; }
              catch (_) { /* a read may finish the final split code point */ }
            }
            capAnswer = bytes;
            if (localReadLogCount < 256) {
              capLog.push({ wire: 41, outcome: "local", bytes: bytes.length });
              localReadLogCount++;
            } else localReadLogTruncated = true;
            return BigInt(bytes.length);
          }
          const nl = request.indexOf("\n");
          const line = nl < 0 ? request : request.slice(0, nl);
          const m = /^([A-Z]{1,16}) ([^\s]+)$/.exec(line);
          if (!bound.has(w) || !m) {
            capLog.push({ wire: w, outcome: "refused", error: bound.has(w) ? "malformed request" : "wire not bound" });
            return -1n;
          }
          const init = { method: m[1] };
          if (nl >= 0) init.body = request.slice(nl + 1);
          const reply = await self.kotobaCapRequest({ wire: w, payload: { input: m[2], init } });
          if (!reply || reply.ok !== true || typeof reply.content !== "string" || !Number.isSafeInteger(reply.status)) {
            capLog.push({ wire: w, outcome: "refused", error: String((reply && reply.error) || "no response").slice(0, 256) });
            return -1n;
          }
          capAnswer = new TextEncoder().encode(reply.status + "\n" + reply.content);
          capLog.push({ wire: w, outcome: "answered", status: reply.status, bytes: capAnswer.length });
          return BigInt(capAnswer.length);
        }) : function cap(wire, ptr, len) {
          if (bound.size > 0) capLog.push({ wire: Number(wire), outcome: "refused", error: "no JSPI (WebAssembly.Suspending)" });
          return -1n;
        },
        now() { return BigInt(Date.now()) * 1000000n; },
        exit(code) { throw new HostExit(Number(code)); },
        input(kind, i, ptr, len, dst, cap) {
          if (kind === 0n) return i === -1n ? BigInt(argv.length) : answer(argv[Number(i)], dst, cap);
          if (kind === 2n) return allow.has(Number(i)) || bound.has(Number(i)) ? 1n : 0n;
          if (kind === 3n) return answer(capAnswer, dst, cap);
          if (kind !== 1n) return -1n;
          let path;
          try {
            path = new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(memory.buffer, Number(ptr), Number(len)).slice());
          } catch (e) { return -1n; }
          const p = normal(path);
          return p === null ? -1n : answer(fs.get(p), dst, cap);
        },
      },
    };
    let exit = null, wasmTrap = null, runtimeExited = false;
    try {
      if (msg.js !== undefined) {
        const url = URL.createObjectURL(new Blob([msg.js], { type: "text/javascript" }));
        let instance;
        try { instance = (await import(url)).instantiate(imports["kotoba:host"]); }
        finally { URL.revokeObjectURL(url); }
        memory = instance.memory;
        instance.start(BigInt(fuel));
        throw new Error("start returned without exit");
      }
      const instance = msg.module
        ? await WebAssembly.instantiate(msg.module, imports)
        : (await WebAssembly.instantiate(msg.bytes, imports)).instance;
      memory = instance.exports.memory;
      if (jspi) await WebAssembly.promising(instance.exports.start)(BigInt(fuel));
      else instance.exports.start(BigInt(fuel));
      wasmTrap = "start returned without exit";
    } catch (e) {
      if (e instanceof HostExit) { exit = e.code; runtimeExited = true; }
      else wasmTrap = String((e && e.message) || e);
    }
    // A wasm trap outside the runtime's handler (for example stack exhaustion)
    // ends the run as a native signal would: exit 120.
    if (exit === null) exit = 120;
    const out = concat(stdout);
    const cut = out.lastIndexOf("{:status ", out.length - 2);
    // A locally streamed program may end its output without a newline; its
    // separately emitted final runtime report is still the last suffix.
    const last = cut >= 0 && (localStdio ? runtimeExited : (cut === 0 || out[cut - 1] === "\n")) && out.endsWith("}\n");
    const result = { exit, stdout: out, stderr: concat(stderr), wasmTrap, capLog,
                     output: last ? out.slice(0, cut) : out, report: last ? out.slice(cut, -1) : null };
    if (localStdio) Object.assign(result, {stdoutTruncated: truncated[1], stderrTruncated: truncated[2], localReadLogTruncated});
    return result;
  }
  // cap requests in flight: id -> resolve (one at a time: the guest is suspended)
  const pendingCaps = new Map(), pendingLocalReads = new Map(), pendingLocalOutputs = new Map();
  let nextCap = 0;
  self.kotobaCapRequest = (cap) => new Promise((resolve) => {
    const id = "cap-" + (++nextCap);
    pendingCaps.set(id, resolve);
    self.postMessage({ cap: Object.assign({ id }, cap) });
  });
  self.kotobaLocalRead = (request) => new Promise((resolve) => {
    const id = "local-" + (++nextCap);
    pendingLocalReads.set(id, resolve);
    self.postMessage({ localRead: { id, request } });
  });
  self.kotobaLocalOutput = (fd, bytes) => new Promise((resolve) => {
    const id = "output-" + (++nextCap);
    pendingLocalOutputs.set(id, resolve);
    self.postMessage({ localOutput: { id, fd, bytes } });
  });
  let started = false;
  self.onmessage = async (e) => {
    const capReply = e.data && e.data.capReply;
    const localReply = e.data && e.data.localReadReply;
    const outputReply = e.data && e.data.localOutputReply;
    if (capReply || localReply || outputReply) {
      const reply = capReply || localReply || outputReply;
      const pending = capReply ? pendingCaps : localReply ? pendingLocalReads : pendingLocalOutputs;
      const resolve = pending.get(reply.id);
      if (resolve) { pending.delete(reply.id); resolve(reply); }
      return;
    }
    if (started) return;
    started = true;
    self.postMessage(await run(e.data));
  };
}
if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  kotobaWasm32BrowserStaticHost();
}
