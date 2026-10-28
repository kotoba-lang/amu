// experiment: Q8_0 repacked at load time: scales in their own f32 array, int8 quants as aligned vec4<u32>; one thread per block
const WG = Number(Deno.args[2] ?? 64), BPT = Number(Deno.args[3] ?? 1);
const code = `
struct M { rows: u32, cols: u32 };
@group(0) @binding(0) var<storage, read> m: M;
@group(0) @binding(1) var<storage, read> q: array<vec4<u32>>;
@group(0) @binding(2) var<storage, read> x: array<vec4<f32>>;
@group(0) @binding(3) var<storage, read_write> o: array<f32>;
@group(0) @binding(4) var<storage, read> sc: array<f32>;
var<workgroup> part: array<f32, ${WG}>;
fn dq(v: u32, xv: vec4<f32>) -> f32 {
  let qi = vec4<f32>(vec4<i32>(extractBits(bitcast<i32>(v), 0u, 8u), extractBits(bitcast<i32>(v), 8u, 8u), extractBits(bitcast<i32>(v), 16u, 8u), extractBits(bitcast<i32>(v), 24u, 8u)));
  return dot(qi, xv);
}
@compute @workgroup_size(${WG})
fn main(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
  let row = wid.x; let t = lid.x;
  let nb = m.cols / 32u;
  var acc = 0.0;
  for (var b = t; b < nb; b += ${WG}u) {
    let gb = row * nb + b;
    let a = q[gb * 2u]; let c = q[gb * 2u + 1u];
    let xb = b * 8u;
    var s = dq(a.x, x[xb]) + dq(a.y, x[xb + 1u]) + dq(a.z, x[xb + 2u]) + dq(a.w, x[xb + 3u]);
    s += dq(c.x, x[xb + 4u]) + dq(c.y, x[xb + 5u]) + dq(c.z, x[xb + 6u]) + dq(c.w, x[xb + 7u]);
    acc += sc[gb] * s;
  }
  part[t] = acc;
  workgroupBarrier();
  for (var st = ${WG / 2}u; st > 0u; st >>= 1u) { if (t < st) { part[t] += part[t + st]; } workgroupBarrier(); }
  if (t == 0u) { o[row] = part[0]; }
}`;
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
console.log(JSON.stringify({ wg: WG, rows, cols, maxRel, ms: +ms.toFixed(3), q8_0_payload_GBps: +(gb / (ms / 1e3)).toFixed(1) }));
