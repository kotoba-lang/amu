// VALIDATE the :subgroup-reduce WGSL arm's emitted corpus on a REAL WGSL
// toolchain (JUN-59/JUN-60): Google Chrome's Dawn/Tint, driven through
// WebGPU shader creation -- `createShaderModule` + `getCompilationInfo()`
// (the WGSL front end's own verdict) and a `createComputePipeline` under a
// validation error scope (entry point + linkage). That is a TOOLCHAIN fact
// of what validates, not a measurement: no WebGPU execution path exists in
// this repository and no timing or speedup is claimed or implied.
//
//   node scripts/validate-gpu-subgroup-reduce-wgsl.mjs [corpus-dir] \
//     > docs/evidence/gpu/wgsl-validate-chrome-20261025/compile-log.txt
//
// Default corpus-dir: docs/evidence/gpu-subgroup-reduce-wgsl-20261025/shaders
// (produced by scripts/emit-gpu-subgroup-reduce-wgsl.cljk -- the emitter's
// own bytes, never hand-written).
//
// Deterministic: files are processed in sorted order; the transcript's only
// run-varying lines are the self-dating header and the toolchain identity,
// which are the evidence this run happened and on what.
//
// NOTE (the toolchain landscape, measured 2026-10-25): Deno 2.7.14's
// bundled wgpu/Naga REFUSES `enable subgroups;` ("not yet implemented in
// Naga"), so it cannot judge this arm. Chrome's Tint can (the `subgroups`
// WebGPU feature is on its adapter). This harness therefore validates in
// Chrome and names the vehicle in every transcript.

import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const { chromium } = require(path.join(repoRoot, 'node_modules', 'playwright'));

const corpusDir = path.resolve(
  process.argv[2] ?? path.join(repoRoot, 'docs/evidence/gpu-subgroup-reduce-wgsl-20261025/shaders'));

const files = fs.readdirSync(corpusDir).filter((f) => f.endsWith('.wgsl')).sort();

console.log((process.argv[3] ?? 'JUN-59/JUN-60 -- :subgroup-reduce WGSL arm, real-toolchain validation'));
console.log('run-at: ' + new Date().toISOString());
console.log('host: ' + os.platform() + ' ' + os.release() + ' ' + os.arch());
console.log('node: ' + process.version);
console.log('corpus: ' + corpusDir);
console.log('files: ' + files.length + ' (sorted)');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end('<!doctype html><meta charset=utf-8><title>wgsl-validate</title>');
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

// WebGPU is exposed only in secure contexts; 127.0.0.1 is trustworthy.
// channel 'chrome' = the installed Google Chrome (a shipping Dawn/Tint).
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
  const hasSubgroups = feats.includes('subgroups');
  const device = hasSubgroups
    ? await adapter.requestDevice({ requiredFeatures: ['subgroups'] })
    : await adapter.requestDevice();
  const raised = {
    maxComputeWorkgroupSizeX: adapter.limits.maxComputeWorkgroupSizeX,
    maxComputeInvocationsPerWorkgroup: adapter.limits.maxComputeInvocationsPerWorkgroup,
    maxComputeWorkgroupStorageSize: adapter.limits.maxComputeWorkgroupStorageSize,
  };
  return {
    ua: navigator.userAgent,
    adapterInfo: {
      vendor: info.vendor ?? null,
      architecture: info.architecture ?? null,
      description: info.description ?? null,
      device: info.device ?? null,
    },
    features: feats,
    subgroupsFeature: hasSubgroups ? 'device created WITH subgroups' : 'NO subgroups feature',
    defaultLimits: {
      maxComputeWorkgroupSizeX: device.limits.maxComputeWorkgroupSizeX,
      maxComputeInvocationsPerWorkgroup: device.limits.maxComputeInvocationsPerWorkgroup,
      maxComputeWorkgroupStorageSize: device.limits.maxComputeWorkgroupStorageSize,
    },
    raisedLimits: raised,
  };
});
console.log('toolchain: ' + (toolchain.ua ?? toolchain.err));
console.log('adapter-info: ' + JSON.stringify(toolchain.adapterInfo ?? {}));
console.log('adapter-features: ' + (toolchain.features ?? []).join(','));
console.log('subgroups: ' + toolchain.subgroupsFeature);
console.log('default-limits: ' + JSON.stringify(toolchain.defaultLimits ?? {}));
console.log('raised-limits (requiredLimits, adapter maxima): ' + JSON.stringify(toolchain.raisedLimits ?? {}));

let okDefault = 0;
let okRaised = 0;
for (const f of files) {
  const code = fs.readFileSync(path.join(corpusDir, f), 'utf8');
  const result = await page.evaluate(async ({ code }) => {
    const gpu = navigator.gpu;
    const adapter = await gpu.requestAdapter();
    const feats = [...(adapter.features ?? [])];
    const subgroups = feats.includes('subgroups');

    async function judge(requiredLimits) {
      const adapter = await gpu.requestAdapter();
      const feats = [...(adapter.features ?? [])];
      const subgroups = feats.includes('subgroups');
      const device = subgroups
        ? await adapter.requestDevice({ requiredFeatures: ['subgroups'], requiredLimits })
        : await adapter.requestDevice({ requiredLimits });
      const mod = device.createShaderModule({ code });
      const info = await mod.getCompilationInfo();
      const msgs = info.messages.map((m) => `${m.type}@${m.lineNum}:${m.linePos} ${m.message}`);
      device.pushErrorScope('validation');
      let pipelineState = 'skipped';
      try {
        device.createComputePipeline({
          layout: 'auto',
          compute: { module: mod, entryPoint: 'main' },
        });
        pipelineState = 'created';
      } catch (e) {
        pipelineState = 'threw: ' + String(e).slice(0, 200);
      }
      const err = await device.popErrorScope();
      return {
        msgs,
        compileInfoStatus: msgs.some((s) => s.startsWith('error@')) ? 'error' : 'ok',
        pipelineState,
        pipelineError: err
          ? `${err.constructor.name}: ${err.message ?? String(err)}`
          : 'none',
      };
    }

    return {
      limitsDefault: await judge(undefined),
      limitsRaised: await judge({
        maxComputeWorkgroupSizeX: adapter.limits.maxComputeWorkgroupSizeX,
        maxComputeInvocationsPerWorkgroup: adapter.limits.maxComputeInvocationsPerWorkgroup,
        maxComputeWorkgroupStorageSize: adapter.limits.maxComputeWorkgroupStorageSize,
      }),
    };
  }, { code });

  const bytes = Buffer.byteLength(code);
  console.log(`--- ${f} (${bytes} bytes)`);
  for (const [label, r] of [['DEFAULT limits', result.limitsDefault], ['RAISED limits', result.limitsRaised]]) {
    console.log(`[${label}] compile-info: ${r.compileInfoStatus}`);
    for (const m of r.msgs) console.log('  msg ' + m);
    console.log(`[${label}] pipeline: ${r.pipelineState}; pipeline-error: ${r.pipelineError}`);
    const clean = r.compileInfoStatus === 'ok'
      && r.pipelineState === 'created'
      && r.pipelineError === 'none';
    console.log(`[${label}] VERDICT: ${clean ? 'VALIDATES CLEAN' : 'DOES NOT VALIDATE CLEAN'}`);
    if (label === 'DEFAULT limits') { if (clean) okDefault += 1; }
    else if (clean) okRaised += 1;
  }
}
console.log('===');
console.log(`summary DEFAULT limits: ${files.length} files, ${okDefault} validate clean, ${files.length - okDefault} do not`);
console.log(`summary RAISED limits: ${files.length} files, ${okRaised} validate clean, ${files.length - okRaised} do not`);
console.log('toolchain-fact only: nothing executed on a GPU, UNMEASURED unchanged.');

await browser.close();
server.close();
process.exit(okRaised === files.length ? 0 : 1);
