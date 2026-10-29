// experiment: Q8_0 repacked at load time: scales in their own f32 array, int8 quants as aligned vec4<u32>; one thread per block

const WGN = Number(Deno.args[2] ?? 32);
const txt = await Deno.readTextFile(Deno.args[3]);
const part = txt.split(/^\/\/KERNEL /m).slice(1).find(p => p.startsWith("q8-repack-" + WGN + "\n"));
const code = part.slice(part.indexOf("\n") + 1).replace(/^\/\/CHECK.*$/m, "").replace(/^run-exit=.*$/m, "");
const adapter = await navigator.gpu.requestAdapter();
const dev = await adapter.requestDevice({ requiredLimits: { maxStorageBufferBindingSize: 1 << 28 } });
const mod = dev.createShaderModule({ code });
const msgs = (await mod.getCompilationInfo()).messages.filter(m => m.type === "error");
if (msgs.length) { console.log("compile FAIL", msgs[0].message); Deno.exit(1); }
const rows = Number(Deno.args[0] ?? 4096), cols = Number(Deno.args[1] ?? 4096);
let seed = 987654321; const rnd = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;
const nb = cols / 32;
const quants = new Int8Array(rows * nb * 32), scales = new Float32Array(rows * nb), Wd = new Float64Array(rows * cols);
for (let r = 0; r < rows; r++) for (let b = 0; b < nb; b++) {
  const d = (1 + Math.floor(rnd() * 255)) / 256; scales[r * nb + b] = d;
  for (let i = 0; i < 32; i++) { const qq = Math.floor(rnd() * 256) - 128; quants[(r * nb + b) * 32 + i] = qq; Wd[r * cols + b * 32 + i] = d * qq; }
}
const X = new Float32Array(cols); for (let i = 0; i < cols; i++) X[i] = rnd() - 0.5;
const S = GPUBufferUsage.STORAGE;
const mk = (a, extra = 0) => { const b = dev.createBuffer({ size: Math.max(16, a.byteLength), usage: S | GPUBufferUsage.COPY_DST | extra }); dev.queue.writeBuffer(b, 0, a); return b; };
const bufs = [mk(new Uint32Array([rows, cols])), mk(new Uint32Array(quants.buffer)), mk(X), mk(new Float32Array(rows), GPUBufferUsage.COPY_SRC), mk(scales)];
const pipe = await dev.createComputePipelineAsync({ layout: "auto", compute: { module: mod, entryPoint: "main" } });
const bg = dev.createBindGroup({ layout: pipe.getBindGroupLayout(0), entries: bufs.map((b, i) => ({ binding: i, resource: { buffer: b } })) });
const rb = dev.createBuffer({ size: rows * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
const run = n => { const e = dev.createCommandEncoder(); const ps = e.beginComputePass(); ps.setPipeline(pipe); ps.setBindGroup(0, bg); for (let i = 0; i < n; i++) ps.dispatchWorkgroups(rows, 1, 1); ps.end(); return e; };
{ const e = run(1); e.copyBufferToBuffer(bufs[3], 0, rb, 0, rows * 4); dev.queue.submit([e.finish()]); }
await rb.mapAsync(GPUMapMode.READ); const out = new Float32Array(rb.getMappedRange().slice(0));
let maxRel = 0; for (let r = 0; r < rows; r += 13) { let a = 0; for (let k = 0; k < cols; k++) a += Wd[r * cols + k] * X[k]; maxRel = Math.max(maxRel, Math.abs(out[r] - a) / (Math.abs(a) + 1)); }
const N = 100; dev.queue.submit([run(5).finish()]); await dev.queue.onSubmittedWorkDone();
const t0 = performance.now(); dev.queue.submit([run(N).finish()]); await dev.queue.onSubmittedWorkDone(); const ms = (performance.now() - t0) / N;
const gb = rows * nb * 34 / 1e9;   // the same Q8_0 payload as before: 34 bytes a block (repacked: 36 B incl. an f32 scale)
console.log(JSON.stringify({ wg: WGN, kernel: "generated q8-repack", rows, cols, maxRel, ms: +ms.toFixed(3), q8_0_payload_GBps: +(gb / (ms / 1e3)).toFixed(1) }));
