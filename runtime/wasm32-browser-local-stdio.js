// User-side local stdin queue for wasm32-browser-static-host.js. It does not
// handle broker messages, grant capabilities, fetch, or authenticate workers.
// The embedding application owns the Worker, validates its artifact and
// descriptor, and is responsible for handling streamed output/backpressure.
"use strict";
function createKotobaLocalStdio(worker, options = {}) {
  const max = options.maxQueuedBytes === undefined ? 1048576 : options.maxQueuedBytes;
  if (!worker || typeof worker.postMessage !== "function" || typeof worker.addEventListener !== "function" ||
      !Number.isSafeInteger(max) || max < 1 || max > 1048576 || typeof options.onOutput !== "function") {
    throw new Error("invalid local stdio configuration");
  }
  let queued = new Uint8Array(), pending = null, ended = false, disposed = false;
  const encoder = new TextEncoder(), decoder = new TextDecoder("utf-8", {fatal: true});
  function reply(id, ok, content = "") { worker.postMessage({localReadReply: {id, ok, content}}); }
  function drain() {
    if (!pending || disposed) return;
    const n = pending.request === "" ? null : Number(pending.request);
    if ((n === null && !ended) || (n !== 0 && queued.length === 0 && !ended)) return;
    let count = n === null ? queued.length : Math.min(n, queued.length);
    while (count > 0 && count < queued.length && (queued[count] & 0xc0) === 0x80) count++;
    const content = decoder.decode(queued.subarray(0, count));
    queued = queued.slice(count);
    const id = pending.id;
    pending = null;
    reply(id, true, content);
  }
  function onMessage(event) {
    const data = event.data;
    if (data && data.localRead) {
      const {id, request} = data.localRead;
      if (typeof id !== "string" || !/^local-[1-9][0-9]*$/.test(id) || typeof request !== "string" ||
          !/^(?:|0|[1-9][0-9]{0,6})$/.test(request) || Number(request || 0) > 1048576) {
        if (typeof id === "string") reply(id, false);
        return;
      }
      if (pending) { reply(id, false); return; }
      pending = {id, request};
      drain();
    } else if (data && data.localOutput) {
      const {fd, bytes} = data.localOutput;
      if ((fd !== 1 && fd !== 2) || !(bytes instanceof Uint8Array)) throw new Error("invalid local output");
      options.onOutput(fd, bytes.slice());
    }
  }
  worker.addEventListener("message", onMessage);
  return Object.freeze({
    write(text) {
      if (disposed || ended || typeof text !== "string") throw new Error("local input is closed");
      if (text.length > max) throw new Error("local input queue full");
      for (let i = 0; i < text.length; i++) {
        const c = text.charCodeAt(i);
        if (c >= 0xd800 && c <= 0xdbff) {
          if (++i >= text.length || text.charCodeAt(i) < 0xdc00 || text.charCodeAt(i) > 0xdfff) throw new Error("invalid unicode");
        } else if (c >= 0xdc00 && c <= 0xdfff) throw new Error("invalid unicode");
      }
      const bytes = encoder.encode(text);
      if (queued.length + bytes.length > max) throw new Error("local input queue full");
      const next = new Uint8Array(queued.length + bytes.length);
      next.set(queued); next.set(bytes, queued.length); queued = next;
      drain();
    },
    end() { if (disposed) throw new Error("local input disposed"); ended = true; drain(); },
    dispose() {
      if (disposed) return;
      if (pending) { reply(pending.id, false); pending = null; }
      disposed = true; queued = new Uint8Array();
      worker.removeEventListener("message", onMessage);
    },
  });
}
