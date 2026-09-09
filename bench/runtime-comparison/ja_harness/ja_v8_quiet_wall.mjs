// amu-jit tick 29: quiet-host V8 same-fixture wall for the J-A ratio.
// Mirrors the chicory harness accounting: same sealed kernel.kotoba.wasm,
// pool of 8 instances, rebuild every 256 uses (fixture fuel = 512 calls per
// instance on BOTH hosts), 5 s warmup + 60 s timed, checksum kernel(100).
// No listener, no JFR — pure WebAssembly.Instance call loop (V8 tiered JIT).
import { readFileSync } from 'node:fs';
const bytes = readFileSync(process.argv[2]);
const N = 100n, SLOTS = 8, REBUILD = 256;
const mod = new WebAssembly.Module(bytes);
function pool() { const a = []; for (let i = 0; i < SLOTS; i++) a.push({ inst: new WebAssembly.Instance(mod).exports.kernel, uses: 0 }); return a; }
let p = pool();
console.log('kernel(100)=' + p[0].inst(N));
if (String(p[0].inst(N)) !== '110550153') { console.error('CHECKSUM MISMATCH'); process.exit(1); }
let iters = 0;
const t0 = performance.now();
while (performance.now() - t0 < 5000) {
  for (let i = 0; i < 20000; i++) {
    const s = p[iters % SLOTS];
    if (s.uses >= REBUILD) { s.inst = new WebAssembly.Instance(mod).exports.kernel; s.uses = 0; }
    s.inst(N); s.uses++; iters++;
  }
}
console.log('warmup_iters=' + iters);
const t1 = performance.now();
let rec = 0;
while (performance.now() - t1 < 60000) {
  for (let i = 0; i < 20000; i++) {
    const s = p[iters % SLOTS];
    if (s.uses >= REBUILD) { s.inst = new WebAssembly.Instance(mod).exports.kernel; s.uses = 0; }
    s.inst(N); s.uses++; iters++; rec++;
  }
}
const span = performance.now() - t1;
console.log('recorded_iters=' + rec + ' ns_per_call=' + (span * 1e6 / rec).toFixed(1));
console.log('checksum_after=' + p[0].inst(N));
