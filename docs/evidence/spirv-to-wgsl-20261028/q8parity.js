// test-time oracle only: the generated kdot-f32-r1 WGSL on synthetic Q8_0 data against an f64 sum
const text = await Deno.readTextFile(Deno.args[0]);
const part = text.split(/^\/\/KERNEL /m).slice(1).find(p => p.startsWith("kdot-f32-r1\n"));
const code = part.slice(part.indexOf("\n") + 1).replace(/^run-exit=.*$/m, "");
const adapter = await navigator.gpu.requestAdapter();
const dev = await adapter.requestDevice({ requiredLimits: { maxStorageBufferBindingSize: 1 << 28 } });
const mod = dev.createShaderModule({ code });
const msgs = (await mod.getCompilationInfo()).messages.filter(m => m.type === "error");
if (msgs.length) { console.log("compile FAIL", msgs[0].message); Deno.exit(1); }
const rows = Number(Deno.args[1] ?? 64), cols = Number(Deno.args[2] ?? 1024), P = Number(Deno.args[3] ?? 3);
let seed = 987654321; const rnd = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;
const nb = cols / 32, rowBytes = nb * 34, bytes = new Uint8Array(rows * rowBytes + 8);
const dv = new DataView(bytes.buffer);
const f16bits = v => { const e = Math.floor(Math.log2(v)); const m = v / 2 ** e - 1; return ((e + 15) << 10) | Math.round(m * 1024); };
const W = new Float64Array(rows * cols);   // dequantised f64 weights
for (let r = 0; r < rows; r++) for (let b = 0; b < nb; b++) {
  const k = 1 + Math.floor(rnd() * 255), d = k / 256, off = r * rowBytes + b * 34;
  dv.setUint16(off, f16bits(d), true);
  for (let i = 0; i < 32; i++) { const q = Math.floor(rnd() * 256) - 128; dv.setInt8(off + 2 + i, q); W[r * cols + b * 32 + i] = d * q; }
}
const X = new Float32Array(P * cols); for (let i = 0; i < X.length; i++) X[i] = rnd() - 0.5;
const wordsW = new Uint32Array(bytes.buffer.slice(0, Math.ceil(bytes.length / 4) * 4));
const meta = new Uint32Array([rows, cols, 8, P, 1, 1, 0, 0]);   // type 8 = Q8_0; input_per_expert 1, pad0 1, pad1 0
const S = GPUBufferUsage.STORAGE;
const mk = (a, extra = 0) => { const b = dev.createBuffer({ size: Math.max(16, a.byteLength), usage: S | GPUBufferUsage.COPY_DST | extra }); dev.queue.writeBuffer(b, 0, a); return b; };
const bufs = [mk(meta), mk(wordsW), mk(X), mk(new Float32Array(P * rows), GPUBufferUsage.COPY_SRC), mk(new Uint32Array(P))];
const pipe = await dev.createComputePipelineAsync({ layout: "auto", compute: { module: mod, entryPoint: "main" } });
const bg = dev.createBindGroup({ layout: pipe.getBindGroupLayout(0), entries: bufs.map((b, i) => ({ binding: i, resource: { buffer: b } })) });
const rb = dev.createBuffer({ size: P * rows * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
const enc = dev.createCommandEncoder(); const pass = enc.beginComputePass(); pass.setPipeline(pipe); pass.setBindGroup(0, bg);
pass.dispatchWorkgroups(rows, P, 1); pass.end(); enc.copyBufferToBuffer(bufs[3], 0, rb, 0, P * rows * 4); dev.queue.submit([enc.finish()]);
await rb.mapAsync(GPUMapMode.READ); const out = new Float32Array(rb.getMappedRange().slice(0));
let maxRel = 0, maxAbs = 0;
for (let p = 0; p < P; p++) for (let r = 0; r < rows; r++) {
  let a = 0; for (let k = 0; k < cols; k++) a += W[r * cols + k] * X[p * cols + k];
  const g = out[p * rows + r]; maxAbs = Math.max(maxAbs, Math.abs(g - a)); maxRel = Math.max(maxRel, Math.abs(g - a) / (Math.abs(a) + 1));
}

const N = 100, run = n => { const e = dev.createCommandEncoder(); const ps = e.beginComputePass(); ps.setPipeline(pipe); ps.setBindGroup(0, bg); for (let i = 0; i < n; i++) ps.dispatchWorkgroups(rows, P, 1); ps.end(); return e.finish(); };
dev.queue.submit([run(5)]); await dev.queue.onSubmittedWorkDone();
const t0 = performance.now(); dev.queue.submit([run(N)]); await dev.queue.onSubmittedWorkDone(); const ms = (performance.now() - t0) / N;
console.log(JSON.stringify({ rows, cols, positions: P, maxRel, maxAbs, ms_per_dispatch: +ms.toFixed(3), weight_GBps: +((rows * rowBytes / 1e9) / (ms / 1e3)).toFixed(1) }));
