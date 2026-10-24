// MEASURE the WGSL route's reduce arms on a REAL GPU (JUN-55/JUN-58):
// the first TIMING read of the :subgroup-reduce WGSL arm and the :baseline
// :reduce WGSL arm -- the same committed emitter bytes the execute harness
// ran correctness-only (docs/evidence/gpu/wgsl-execute-chrome-20261025).
//
//   node scripts/measure-gpu-reduce-wgsl.mjs [subgroup-corpus-dir] [baseline-corpus-dir] \
//     > docs/evidence/gpu/wgsl-measure-chrome-20261025/measure-log.txt
//
// WHAT IS MEASURED (wall-clock, host clock via performance.now):
//   single : one dispatch per queue submit; time = submit -> onSubmittedWorkDone.
//            End-to-end dispatch latency including submission overhead.
//   batch32: 32 dispatches of the same kernel in one command buffer; the
//            reported value is (submit -> onSubmittedWorkDone) / 32. The
//            per-submit floor is amortized 32x, so this tracks closer to
//            per-dispatch GPU cost than `single` does.
// Both metrics bracket the timed region to submit+completion only: input
// setup, buffer writes, pipeline creation, readback and the CPU fold are all
// OUTSIDE the timed region.
//
// WHAT IS NOT MEASURED: GPU-core timestamps. The harness attempts the
// timestamp-query write path and RECORDS the attempt's outcome in the log.
// If writeTimestamp is unavailable (adapter lacks timestamp-query-inside-passes)
// the log says so and only the wall-clock metrics above exist. Do not read
// these numbers as GPU-core kernel times.
//
// HONESTY SCOPE: this measures the WGSL arms under Chrome's Dawn/Metal stack
// on this host. It does NOT touch any :measured? flag or workgroup row in
// kotoba.compiler.accelerator-targets -- mapping a measurement onto dispatch
// table rows is a separate design slice. It is one run, uncontrolled clocks
// (no thermal/clock-regime control); regime analysis is LEFT.
//
// Sampling: per cell (shape, W, op) the two arms are sampled in the SAME
// round with alternating arm order (even round: subgroup first; odd round:
// baseline first), so each round yields a PAIR. Reported ratios are the
// median of the per-round paired ratios (subgroup/baseline; < 1 means the
// subgroup-reduce arm was faster in that round).
//
// Determinism: cells in sorted (shape, W, op) order; run-varying lines are
// the self-dating header, toolchain identity and the timings themselves.

import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const { chromium } = require(path.join(repoRoot, 'node_modules', 'playwright'));

const subgroupDir = path.resolve(
  process.argv[2] ?? path.join(repoRoot, 'docs/evidence/gpu-subgroup-reduce-wgsl-fix-20261025/shaders'));
const baselineDir = path.resolve(
  process.argv[3] ?? path.join(repoRoot, 'docs/evidence/gpu-baseline-reduce-wgsl-fix-20261025/shaders'));

const WS = [32, 64, 128, 256, 512, 1024];
const OPS = ['sum', 'max', 'min'];
const SHAPES = [1000003, 1048576];
const SINGLE_WARMUP = 3;
const SINGLE_ROUNDS = 11;
const BATCH_K = 32;
const BATCH_WARMUP = 2;
const BATCH_ROUNDS = 7;

console.log('JUN-55/JUN-58 -- WGSL route reduce arms, first TIMING read (wall-clock; GPU-core timestamps attempted and recorded below)');
console.log('run_started=' + new Date().toISOString());
console.log('host: ' + os.platform() + ' ' + os.release() + ' ' + os.arch());
console.log('node: ' + process.version);
console.log('subgroup-corpus: ' + subgroupDir);
console.log('baseline-corpus: ' + baselineDir);
console.log(`protocol: single=${SINGLE_WARMUP}w+${SINGLE_ROUNDS}r batch${BATCH_K}=${BATCH_WARMUP}w+${BATCH_ROUNDS}r per arm per cell; arms paired per round with alternating order`);

const files = {
  subgroup: (op, w) => fs.readFileSync(path.join(subgroupDir, `subgroup-reduce-w${w}-${op}.emitted.wgsl`), 'utf8'),
  baseline: (op, w) => fs.readFileSync(path.join(baselineDir, `reduce-w${w}-${op}.emitted.wgsl`), 'utf8'),
};

// COOP/COEP: cross-origin isolation lifts Chrome's performance.now clamp to
// the finest available resolution; no subresources are fetched, so
// require-corp costs nothing here.
const server = http.createServer((req, res) => {
  res.writeHead(200, {
    'content-type': 'text/html',
    'cross-origin-opener-policy': 'same-origin',
    'cross-origin-embedder-policy': 'require-corp',
  });
  res.end('<!doctype html><meta charset=utf-8><title>wgsl-measure</title>');
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({
  channel: 'chrome',
  headless: true,
  args: ['--enable-unsafe-webgpu'],
});
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${port}/`);

const toolchain = await page.evaluate(async () => {
  const gpu = navigator.gpu;
  if (!gpu) return { err: 'no navigator.gpu' };
  const adapter = await gpu.requestAdapter();
  if (!adapter) return { err: 'no adapter' };
  const feats = [...(adapter.features ?? [])].sort();
  const info = adapter.info ?? {};

  // observed performance.now resolution (min positive delta over 20k reads)
  let res = Infinity;
  let last = performance.now();
  for (let i = 0; i < 20000; i++) {
    const t = performance.now();
    const d = t - last;
    last = t;
    if (d > 0 && d < res) res = d;
  }

  // attempt the GPU timestamp write path; RECORD the outcome either way
  let tsAttempt;
  if (!feats.includes('timestamp-query')) {
    tsAttempt = 'UNAVAILABLE -- adapter has no timestamp-query feature';
  } else {
    const want = ['subgroups', 'timestamp-query'];
    const device = await adapter.requestDevice({ requiredFeatures: want });
    try {
      const qs = device.createQuerySet({ type: 'timestamp', count: 2 });
      const mod = device.createShaderModule({
        code: `@group(0) @binding(0) var<storage, read_write> x: array<f32>;
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) { x[gid.x] = x[gid.x] * 2.0; }`,
      });
      const pipeline = device.createComputePipeline({ layout: 'auto', compute: { module: mod, entryPoint: 'main' } });
      const buf = device.createBuffer({ size: 256 * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
      device.queue.writeBuffer(buf, 0, new Float32Array(256));
      const bind = device.createBindGroup({
        layout: pipeline.getBindGroupLayout(0),
        entries: [{ binding: 0, resource: { buffer: buf } }],
      });
      device.pushErrorScope('validation');
      try {
        const enc = device.createCommandEncoder();
        const pass = enc.beginComputePass();
        pass.setPipeline(pipeline);
        pass.setBindGroup(0, bind);
        pass.writeTimestamp(qs, 0);
        pass.dispatchWorkgroups(4);
        pass.writeTimestamp(qs, 1);
        pass.end();
        const resolve = device.createBuffer({ size: 16, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC });
        enc.resolveQuerySet(qs, 0, 2, resolve, 0);
        device.queue.submit([enc.finish()]);
        const verr = await device.popErrorScope();
        tsAttempt = verr
          ? 'UNAVAILABLE -- writeTimestamp rejected: ' + verr.message.slice(0, 200)
          : 'AVAILABLE -- writeTimestamp accepted (GPU-core timestamps possible)';
      } catch (e) {
        await device.popErrorScope();
        tsAttempt = 'UNAVAILABLE -- writeTimestamp threw: ' + String(e).slice(0, 200);
      }
    } catch (e) {
      tsAttempt = 'UNAVAILABLE -- timestamp setup threw: ' + String(e).slice(0, 200);
    }
    device.destroy();
  }

  return {
    ua: navigator.userAgent,
    adapterInfo: {
      vendor: info.vendor ?? null,
      architecture: info.architecture ?? null,
      description: info.description ?? null,
      device: info.device ?? null,
    },
    features: feats,
    hasSubgroups: feats.includes('subgroups'),
    adapterLimits: {
      maxComputeWorkgroupSizeX: adapter.limits.maxComputeWorkgroupSizeX,
      maxComputeInvocationsPerWorkgroup: adapter.limits.maxComputeInvocationsPerWorkgroup,
      maxWorkgroupsPerDimension: adapter.limits.maxComputeWorkgroupsPerDimension,
    },
    crossOriginIsolated: self.crossOriginIsolated === true,
    perfNowResolutionMs: res === Infinity ? null : res,
    tsAttempt,
  };
});
console.log('toolchain: ' + (toolchain.ua ?? toolchain.err));
console.log('adapter-info: ' + JSON.stringify(toolchain.adapterInfo ?? {}));
console.log('adapter-features: ' + (toolchain.features ?? []).join(','));
console.log('subgroups-feature: ' + (toolchain.hasSubgroups ? 'present' : 'ABSENT'));
console.log('adapter-limits: ' + JSON.stringify(toolchain.adapterLimits ?? {}));
console.log('cross-origin-isolated: ' + (toolchain.crossOriginIsolated ? 'yes' : 'no'));
console.log('perf-now-resolution-ms: ' + toolchain.perfNowResolutionMs);
console.log('gpu-timestamp-write: ' + toolchain.tsAttempt);
if (!toolchain.hasSubgroups) {
  console.log('VERDICT: NO-EXECUTION -- the adapter has no subgroups feature, the :subgroup-reduce arm cannot run.');
  await browser.close();
  server.close();
  process.exit(2);
}

// One cell-pair: check correctness once per arm, then sample both arms in
// paired rounds (alternating order) for the single and batch32 metrics.
async function measureCell(subCode, baseCode, { w, n, op }) {
  return page.evaluate(async ({ subCode, baseCode, w, n, op }) => {
    const gpu = navigator.gpu;
    const adapter = await gpu.requestAdapter();
    const feats = [...(adapter.features ?? [])];
    const requiredFeatures = ['subgroups'];
    if (feats.includes('timestamp-query')) requiredFeatures.push('timestamp-query');
    const requiredLimits = {
      maxComputeWorkgroupSizeX: adapter.limits.maxComputeWorkgroupSizeX,
      maxComputeInvocationsPerWorkgroup: adapter.limits.maxComputeInvocationsPerWorkgroup,
    };
    const device = await adapter.requestDevice({ requiredFeatures, requiredLimits });

    const numParts = Math.ceil(n / w);
    const xBytes = new Uint8Array(n * 4);
    const xf = new Float32Array(xBytes.buffer);
    for (let i = 0; i < n; i++) {
      if (op === 'sum') xf[i] = 1 + (i % 2);
      else xf[i] = i % 4096;
    }
    let ref;
    if (op === 'sum') {
      ref = 0;
      for (let i = 0; i < n; i++) ref += 1 + (i % 2);
    } else if (op === 'max') {
      ref = 0;
      for (let i = 0; i < n; i++) if (i % 4096 > ref) ref = i % 4096;
    } else {
      ref = 4095;
      for (let i = 0; i < n; i++) if (i % 4096 < ref) ref = i % 4096;
    }

    const xBuf = device.createBuffer({ size: n * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
    const partsBuf = device.createBuffer({ size: numParts * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC });
    const nBuf = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    const stage = device.createBuffer({ size: numParts * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
    device.queue.writeBuffer(xBuf, 0, xBytes);
    device.queue.writeBuffer(nBuf, 0, new Uint32Array([n, 0, 0, 0]));

    const mkPipeline = (code) => {
      const mod = device.createShaderModule({ code });
      return device.createComputePipeline({ layout: 'auto', compute: { module: mod, entryPoint: 'main' } });
    };
    const pipelines = { subgroup: mkPipeline(subCode), baseline: mkPipeline(baseCode) };
    const binds = {};
    for (const arm of ['subgroup', 'baseline']) {
      binds[arm] = device.createBindGroup({
        layout: pipelines[arm].getBindGroupLayout(0),
        entries: [
          { binding: 0, resource: { buffer: xBuf } },
          { binding: 1, resource: { buffer: partsBuf } },
          { binding: 2, resource: { buffer: nBuf } },
        ],
      });
    }

    // one dispatch, k times in one pass; returns elapsed ms for the whole
    // submit (not divided here -- caller divides for batch32)
    const runDispatches = async (arm, k) => {
      const enc = device.createCommandEncoder();
      const pass = enc.beginComputePass();
      pass.setPipeline(pipelines[arm]);
      pass.setBindGroup(0, binds[arm]);
      for (let i = 0; i < k; i++) pass.dispatchWorkgroups(numParts);
      pass.end();
      const t0 = performance.now();
      device.queue.submit([enc.finish()]);
      await device.queue.onSubmittedWorkDone();
      return performance.now() - t0;
    };

    // correctness check (outside all timing): one dispatch + readback + fold
    const checks = {};
    for (const arm of ['subgroup', 'baseline']) {
      await runDispatches(arm, 1);
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(partsBuf, 0, stage, 0, numParts * 4);
      device.queue.submit([enc.finish()]);
      await stage.mapAsync(GPUMapMode.READ);
      const parts = new Float32Array(stage.getMappedRange().slice(0));
      stage.unmap();
      let ans;
      if (op === 'sum') { ans = 0; for (let j = 0; j < numParts; j++) ans += parts[j]; }
      else if (op === 'max') { ans = -Infinity; for (let j = 0; j < numParts; j++) if (parts[j] > ans) ans = parts[j]; }
      else { ans = Infinity; for (let j = 0; j < numParts; j++) if (parts[j] < ans) ans = parts[j]; }
      checks[arm] = { answer: ans, ref, ok: ans === ref };
    }

    // warmups (unrecorded)
    for (const arm of ['subgroup', 'baseline']) {
      for (let i = 0; i < 3; i++) await runDispatches(arm, 1);
      for (let i = 0; i < 2; i++) await runDispatches(arm, 32);
    }

    // paired rounds, alternating arm order
    const single = { subgroup: [], baseline: [] };
    for (let r = 0; r < 11; r++) {
      const order = r % 2 === 0 ? ['subgroup', 'baseline'] : ['baseline', 'subgroup'];
      for (const arm of order) single[arm].push(await runDispatches(arm, 1));
    }
    const batch = { subgroup: [], baseline: [] };
    for (let r = 0; r < 7; r++) {
      const order = r % 2 === 0 ? ['subgroup', 'baseline'] : ['baseline', 'subgroup'];
      for (const arm of order) batch[arm].push((await runDispatches(arm, 32)) / 32);
    }

    device.destroy();
    return { checks, single, batch };
  }, { subCode, baseCode, w, n, op });
}

const median = (a) => {
  const s = [...a].sort((x, y) => x - y);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const fmt3 = (v) => v.toFixed(3);
const fmt4 = (v) => v.toFixed(4);

let pairsTotal = 0;
let singleSubFaster = 0;
let batchSubFaster = 0;
let allChecked = 0;
let allCheckOk = 0;

for (const n of SHAPES) {
  for (const w of WS) {
    for (const op of OPS) {
      let r;
      try {
        r = await measureCell(files.subgroup(op, w), files.baseline(op, w), { w, n, op });
      } catch (e) {
        console.log(`cell-error n=${n} w=${w} op=${op} ${String(e).slice(0, 300)}`);
        continue;
      }
      for (const arm of ['subgroup', 'baseline']) {
        const c = r.checks[arm];
        allChecked++;
        if (c.ok) allCheckOk++;
        console.log(`check n=${n} w=${w} op=${op} arm=${arm} answer=${c.answer} ref=${c.ref} ok=${c.ok ? 1 : 0}`);
        console.log(`raw n=${n} w=${w} op=${op} arm=${arm} single_ms=${r.single[arm].map(fmt3).join(',')} batch${32}_ms=${r.batch[arm].map(fmt4).join(',')}`);
        console.log(`time n=${n} w=${w} op=${op} arm=${arm} single_median_ms=${fmt3(median(r.single[arm]))} single_rounds=${r.single[arm].length} batch32_median_ms=${fmt4(median(r.batch[arm]))} batch32_rounds=${r.batch[arm].length}`);
      }
      const singleRatios = r.single.subgroup.map((v, i) => v / r.single.baseline[i]);
      const batchRatios = r.batch.subgroup.map((v, i) => v / r.batch.baseline[i]);
      const sr = median(singleRatios);
      const br = median(batchRatios);
      pairsTotal++;
      if (sr < 1) singleSubFaster++;
      if (br < 1) batchSubFaster++;
      console.log(`pair n=${n} w=${w} op=${op} single_paired_ratio=${fmt3(sr)} batch32_paired_ratio=${fmt3(br)} rounds=${singleRatios.length}/${batchRatios.length}`);
    }
  }
}

console.log(`checks: ${allCheckOk}/${allChecked} arm answers exact against the CPU reference`);
console.log(`aggregate pairs=${pairsTotal} single_subgroup_faster=${singleSubFaster} batch32_subgroup_faster=${batchSubFaster} (paired-median ratio < 1)`);
console.log('run_finished=' + new Date().toISOString());
console.log('VERDICT: ' + (allCheckOk === allChecked
  ? 'MEASURED-WALLCLOCK -- timings above are wall-clock submit-to-completion on this host (GPU-core timestamps: see gpu-timestamp-write line). CORRECTNESS ALSO VERIFIED per cell. NO :measured? flag or workgroup row is flipped by this log.'
  : 'MEASURED-WITH-CHECK-DISAGREEMENT -- named check lines above fail; do not trust timings at those cells'));
await browser.close();
server.close();
