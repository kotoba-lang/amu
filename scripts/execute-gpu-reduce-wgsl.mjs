// EXECUTE the WGSL route's reduce arms on a REAL GPU (JUN-58/JUN-59/JUN-60):
// the :subgroup-reduce WGSL arm and the :baseline :reduce WGSL arm, their
// committed emitter bytes, dispatched on this host's Apple GPU through
// Google Chrome's Dawn/Metal WebGPU stack. This closes the arms' UNEXECUTED
// state (first GPU execution) with a CORRECTNESS check against exact CPU
// references -- it is NOT a measurement: no timing is read, no speedup is
// claimed, every :measured? flag and workgroup row is untouched.
//
//   node scripts/execute-gpu-reduce-wgsl.mjs [subgroup-corpus-dir] [baseline-corpus-dir] \
//     > docs/evidence/gpu/wgsl-execute-chrome-20261025/execute-log.txt
//
// Default corpora: docs/evidence/gpu-subgroup-reduce-wgsl-fix-20261025/shaders
// and docs/evidence/gpu-baseline-reduce-wgsl-fix-20261025/shaders (produced by
// scripts/emit-gpu-subgroup-reduce-wgsl.cljk and scripts/emit-gpu-reduce-wgsl.cljk
// -- the emitters' own bytes, never hand-written).
//
// Correctness criterion (exact, order-independent): every input value is an
// integer below 2^24, so + / max / min over any fold order are exact in f32.
// The GPU answer must equal the CPU reference EXACTLY, and the two arms'
// answers at one cell must be equal.
//
// Determinism: cells processed in sorted (shape, W, op) order; the only
// run-varying lines are the self-dating header and the toolchain identity,
// which are the evidence this run happened and on what.

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

console.log('JUN-58/JUN-59/JUN-60 -- WGSL route reduce arms, first GPU execution (correctness, not measurement)');
console.log('run_started=' + new Date().toISOString());
console.log('host: ' + os.platform() + ' ' + os.release() + ' ' + os.arch());
console.log('node: ' + process.version);
console.log('subgroup-corpus: ' + subgroupDir);
console.log('baseline-corpus: ' + baselineDir);

const files = {
  subgroup: (op, w) => fs.readFileSync(path.join(subgroupDir, `subgroup-reduce-w${w}-${op}.emitted.wgsl`), 'utf8'),
  baseline: (op, w) => fs.readFileSync(path.join(baselineDir, `reduce-w${w}-${op}.emitted.wgsl`), 'utf8'),
};

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end('<!doctype html><meta charset=utf-8><title>wgsl-execute</title>');
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
      maxComputeWorkgroupStorageSize: adapter.limits.maxComputeWorkgroupStorageSize,
      maxComputeWorkgroupsPerDimension: adapter.limits.maxComputeWorkgroupsPerDimension,
      maxStorageBufferBindingSize: adapter.limits.maxStorageBufferBindingSize,
    },
  };
});
console.log('toolchain: ' + (toolchain.ua ?? toolchain.err));
console.log('adapter-info: ' + JSON.stringify(toolchain.adapterInfo ?? {}));
console.log('adapter-features: ' + (toolchain.features ?? []).join(','));
console.log('subgroups-feature: ' + (toolchain.hasSubgroups ? 'present' : 'ABSENT'));
console.log('adapter-limits: ' + JSON.stringify(toolchain.adapterLimits ?? {}));
if (!toolchain.hasSubgroups) {
  console.log('VERDICT: NO-EXECUTION -- the adapter has no subgroups feature, the :subgroup-reduce arm cannot run.');
  await browser.close();
  process.exit(2);
}

// One cell: dispatch the arm, read parts back, fold on the CPU, compare with
// the exact integer reference. Input values (all integers < 2^24, exact f32):
//   sum: x[i] = 1 + (i % 2)   max/min: x[i] = i % 4096
// References are computed on the CPU over the same formula.
async function runCell(code, { w, n, op }) {
  return page.evaluate(async ({ code, w, n, op }) => {
    const gpu = navigator.gpu;
    const adapter = await gpu.requestAdapter();
    const feats = [...(adapter.features ?? [])];
    const subgroups = feats.includes('subgroups');
    const requiredLimits = {
      maxComputeWorkgroupSizeX: adapter.limits.maxComputeWorkgroupSizeX,
      maxComputeInvocationsPerWorkgroup: adapter.limits.maxComputeInvocationsPerWorkgroup,
    };
    const device = subgroups
      ? await adapter.requestDevice({ requiredFeatures: ['subgroups'], requiredLimits })
      : await adapter.requestDevice({ requiredLimits });

    const numParts = Math.ceil(n / w);
    const xBytes = new Uint8Array(n * 4);
    const xf = new Float32Array(xBytes.buffer);
    for (let i = 0; i < n; i++) {
      if (op === 'sum') xf[i] = 1 + (i % 2);
      else xf[i] = i % 4096;
    }
    // exact CPU reference (integer accumulation in double: exact below 2^53)
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

    device.pushErrorScope('validation');
    const mod = device.createShaderModule({ code });
    let pipeline;
    try {
      pipeline = device.createComputePipeline({ layout: 'auto', compute: { module: mod, entryPoint: 'main' } });
    } catch (e) {
      const err = await device.popErrorScope();
      device.destroy();
      return { err: 'pipeline threw: ' + String(e).slice(0, 200), validation: err ? err.message : null };
    }
    const err = await device.popErrorScope();

    const enc = device.createCommandEncoder();
    const pass = enc.beginComputePass();
    pass.setPipeline(pipeline);
    pass.setBindGroup(0, device.createBindGroup({
      layout: pipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: { buffer: xBuf } },
        { binding: 1, resource: { buffer: partsBuf } },
        { binding: 2, resource: { buffer: nBuf } },
      ],
    }));
    pass.dispatchWorkgroups(numParts);
    pass.end();
    enc.copyBufferToBuffer(partsBuf, 0, stage, 0, numParts * 4);
    device.queue.submit([enc.finish()]);

    await stage.mapAsync(GPUMapMode.READ);
    const parts = new Float32Array(stage.getMappedRange().slice(0));
    stage.unmap();

    // CPU fold over the per-workgroup parts (same combine as the arm)
    let ans;
    if (op === 'sum') { ans = 0; for (let j = 0; j < numParts; j++) ans += parts[j]; }
    else if (op === 'max') { ans = -Infinity; for (let j = 0; j < numParts; j++) if (parts[j] > ans) ans = parts[j]; }
    else { ans = Infinity; for (let j = 0; j < numParts; j++) if (parts[j] < ans) ans = parts[j]; }

    const finite = parts.slice(0, numParts).every((v) => Number.isFinite(v));
    device.destroy();
    return {
      validation: err ? err.message : null,
      numParts,
      answer: ans,
      ref,
      ok: ans === ref,
      allPartsFinite: finite,
    };
  }, { code, w, n, op });
}

let cellsOk = 0;
let cellsTotal = 0;
let crossChecked = 0;
let crossOk = 0;
for (const n of SHAPES) {
  for (const w of WS) {
    for (const op of OPS) {
      cellsTotal += 2;
      const s = await runCell(files.subgroup(op, w), { w, n, op });
      const b = await runCell(files.baseline(op, w), { w, n, op });
      const fmt = (r) => r.err
        ? 'ERR ' + r.err
        : `answer=${r.answer} ref=${r.ref} ok=${r.ok ? 1 : 0} parts=${r.numParts} finite=${r.allPartsFinite ? 1 : 0}`;
      console.log(`cell n=${n} w=${w} op=${op} arm=subgroup-reduce ${fmt(s)}`);
      console.log(`cell n=${n} w=${w} op=${op} arm=baseline       ${fmt(b)}`);
      if (!s.err && s.ok) cellsOk++;
      if (!b.err && b.ok) cellsOk++;
      if (!s.err && !b.err) {
        crossChecked++;
        const eq = s.answer === b.answer;
        if (eq) crossOk++;
        console.log(`cross n=${n} w=${w} op=${op} subgroup=${s.answer} baseline=${b.answer} equal=${eq ? 1 : 0}`);
      }
    }
  }
}

console.log(`cells: ${cellsOk}/${cellsTotal} answers exact against the CPU reference`);
console.log(`cross-arm: ${crossOk}/${crossChecked} cells equal between the two arms`);
console.log('run_finished=' + new Date().toISOString());
console.log('VERDICT: ' + (cellsOk === cellsTotal && crossOk === crossChecked
  ? 'EXECUTED-CORRECT (correctness only; UNMEASURED -- no timing read, no speed claim)'
  : 'EXECUTED-WITH-DISAGREEMENT (named cell lines above)'));
await browser.close();
server.close();
