// experiment: Q8_0 matvec, one thread per 34-byte block, words not bytes; exploring the achievable bandwidth in WGSL
const WG = Number(Deno.args[3] ?? 64);
const code = `
struct M { rows: u32, cols: u32 };
@group(0) @binding(0) var<storage, read> m: M;
@group(0) @binding(1) var<storage, read> w: array<u32>;
@group(0) @binding(2) var<storage, read> x: array<vec4<f32>>;
@group(0) @binding(3) var<storage, read_write> o: array<f32>;
var<workgroup> part: array<f32, ${WG}>;
fn word(i: u32) -> u32 { return w[i]; }
@compute @workgroup_size(${WG})
fn main(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
  let row = wid.x; let t = lid.x;
  let nb = m.cols / 32u;
  let rowByte = row * nb * 34u;
  var acc = 0.0;
  for (var b = t; b < nb; b += ${WG}u) {
    let off = rowByte + b * 34u;            // byte offset of the block
    let wi = off >> 2u;
    let odd = (off & 2u) != 0u;
    let w0 = word(wi);
    let d = unpack2x16float(select(w0, w0 >> 16u, odd)).x;   // scale = low half of the pair holding it
    var s = 0.0;
    let xb = b * 8u;
    for (var j = 0u; j < 8u; j++) {
      // data starts at off+2; the 4 bytes j*4.. are the word at (off+2+4j)
      var q: u32;
      if (odd) { q = word(wi + 1u + j); }
      else { q = (word(wi + j) >> 16u) | (word(wi + j + 1u) << 16u); }
      let qi = vec4<f32>(vec4<i32>(extractBits(vec4<i32>(bitcast<i32>(q)), 0u, 8u).x, extractBits(bitcast<i32>(q), 8u, 8u), extractBits(bitcast<i32>(q), 16u, 8u), extractBits(bitcast<i32>(q), 24u, 8u)));
      s += dot(qi, x[xb + j]);
    }
    acc += d * s;
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
const rows = Number(Deno.args[0] ?? 4096), cols = Number(Deno.args[1] ?? 4096), P = 1;
let seed = 987654321; const rnd = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;
const nb = cols / 32, rowBytes = nb * 34, bytes = new Uint8Array(rows * rowBytes + 8), dv = new DataView(bytes.buffer);
const f16bits = v => { const e = Math.floor(Math.log2(v)); const m = v / 2 ** e - 1; return ((e + 15) << 10) | Math.round(m * 1024); };
const Wd = new Float64Array(rows * cols);
for (let r = 0; r < rows; r++) for (let b = 0; b < nb; b++) {
  const k = 1 + Math.floor(rnd() * 255), d = k / 256, off = r * rowBytes + b * 34;
  dv.setUint16(off, f16bits(d), true);
  for (let i = 0; i < 32; i++) { const q = Math.floor(rnd() * 256) - 128; dv.setInt8(off + 2 + i, q); Wd[r * cols + b * 32 + i] = d * q; }
}
const X = new Float32Array(cols); for (let i = 0; i < cols; i++) X[i] = rnd() - 0.5;
const S = GPUBufferUsage.STORAGE;
const mk = (a, extra = 0) => { const b = dev.createBuffer({ size: Math.max(16, a.byteLength), usage: S | GPUBufferUsage.COPY_DST | extra }); dev.queue.writeBuffer(b, 0, a); return b; };
const bufs = [mk(new Uint32Array([rows, cols])), mk(new Uint32Array(bytes.buffer.slice(0, Math.ceil(bytes.length / 4) * 4))), mk(X), mk(new Float32Array(rows), GPUBufferUsage.COPY_SRC)];
const pipe = await dev.createComputePipelineAsync({ layout: "auto", compute: { module: mod, entryPoint: "main" } });
const bg = dev.createBindGroup({ layout: pipe.getBindGroupLayout(0), entries: bufs.map((b, i) => ({ binding: i, resource: { buffer: b } })) });
const rb = dev.createBuffer({ size: rows * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
const run = n => { const e = dev.createCommandEncoder(); const ps = e.beginComputePass(); ps.setPipeline(pipe); ps.setBindGroup(0, bg); for (let i = 0; i < n; i++) ps.dispatchWorkgroups(rows, 1, 1); ps.end(); return e; };
{ const e = run(1); e.copyBufferToBuffer(bufs[3], 0, rb, 0, rows * 4); dev.queue.submit([e.finish()]); }
await rb.mapAsync(GPUMapMode.READ); const out = new Float32Array(rb.getMappedRange().slice(0));
let maxRel = 0; for (let r = 0; r < rows; r += 13) { let a = 0; for (let k = 0; k < cols; k++) a += Wd[r * cols + k] * X[k]; maxRel = Math.max(maxRel, Math.abs(out[r] - a) / (Math.abs(a) + 1)); }
const N = 100; dev.queue.submit([run(5).finish()]); await dev.queue.onSubmittedWorkDone();
const t0 = performance.now(); dev.queue.submit([run(N).finish()]); await dev.queue.onSubmittedWorkDone(); const ms = (performance.now() - t0) / N;
console.log(JSON.stringify({ wg: WG, rows, cols, maxRel, ms: +ms.toFixed(3), weight_GBps: +((rows * rowBytes / 1e9) / (ms / 1e3)).toFixed(1) }));
