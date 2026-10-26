// VALIDATE the infinite-neutral probe corpus on TWO real WGSL toolchains
// (JUN-59/JUN-60 fix-question slice): Google Chrome's Dawn/Tint through
// WebGPU shader creation, then Deno's bundled wgpu/Naga via
// scripts/judge-gpu-wgsl-probes-deno.ts. These are TOOLCHAIN FACTS of what
// validates -- not measurements: no GPU kernel executes, no timing exists,
// and UNMEASURED is unchanged everywhere.
//
//   node scripts/validate-gpu-wgsl-inf-probes.mjs [corpus-dir] \
//     > docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/compile-log.txt
//
// Default corpus-dir:
// docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/probes
//
// Deterministic: files are processed in sorted order; the transcript's only
// run-varying lines are the self-dating headers and the toolchain
// identities, which are the evidence this run happened and on what.

import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const { chromium } = require(path.join(repoRoot, 'node_modules', 'playwright'));

const corpusDir = path.resolve(
  process.argv[2] ?? path.join(
    repoRoot,
    'docs/evidence/gpu/wgsl-inf-neutral-fixquestion-20261025/probes',
  ));
const files = fs.readdirSync(corpusDir).filter((f) => f.endsWith('.wgsl')).sort();

console.log('JUN-59/JUN-60 -- infinite-neutral probes, real-toolchain validation (2 toolchains)');
console.log('run-at: ' + new Date().toISOString());
console.log('host: ' + os.platform() + ' ' + os.release() + ' ' + os.arch());
console.log('node: ' + process.version);
console.log('corpus: ' + corpusDir);
console.log('files: ' + files.length + ' (sorted)');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end('<!doctype html><meta charset=utf-8><title>wgsl-inf-probes</title>');
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
  const info = adapter.info ?? {};
  const device = await adapter.requestDevice();
  return {
    ua: navigator.userAgent,
    adapterInfo: {
      vendor: info.vendor ?? null,
      architecture: info.architecture ?? null,
    },
    defaultLimits: {
      maxComputeWorkgroupSizeX: device.limits.maxComputeWorkgroupSizeX,
      maxComputeInvocationsPerWorkgroup: device.limits.maxComputeInvocationsPerWorkgroup,
    },
  };
});
console.log('toolchain-1: ' + (toolchain.ua ?? toolchain.err));
console.log('adapter-info: ' + JSON.stringify(toolchain.adapterInfo ?? {}));
console.log('default-limits: ' + JSON.stringify(toolchain.defaultLimits ?? {}));

let ok = 0;
for (const f of files) {
  const code = fs.readFileSync(path.join(corpusDir, f), 'utf8');
  const r = await page.evaluate(async ({ code }) => {
    const gpu = navigator.gpu;
    const adapter = await gpu.requestAdapter();
    const device = await adapter.requestDevice();
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
      pipelineError: err ? `${err.constructor.name}: ${err.message ?? String(err)}` : 'none',
    };
  }, { code });

  console.log(`--- ${f} (${Buffer.byteLength(code)} bytes)`);
  console.log(`[Chrome/Tint] compile-info: ${r.compileInfoStatus}`);
  for (const m of r.msgs) console.log('  msg ' + m);
  console.log(`[Chrome/Tint] pipeline: ${r.pipelineState}; pipeline-error: ${r.pipelineError}`);
  const clean = r.compileInfoStatus === 'ok'
    && r.pipelineState === 'created'
    && r.pipelineError === 'none';
  console.log(`[Chrome/Tint] VERDICT: ${clean ? 'VALIDATES CLEAN' : 'DOES NOT VALIDATE CLEAN'}`);
  if (clean) ok += 1;
}
console.log('===');
console.log(`summary (Chrome/Tint): ${files.length} files, ${ok} validate clean, ${files.length - ok} do not`);

await browser.close();
server.close();

console.log('======== Deno/Naga judgment of the same corpus ========');
await new Promise((resolve) => {
  const child = spawn('deno', [
    'run',
    '--allow-all',
    '--unstable-webgpu',
    path.join(repoRoot, 'scripts', 'judge-gpu-wgsl-probes-deno.ts'),
    corpusDir,
  ], { stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout.on('data', (d) => process.stdout.write(d));
  child.stderr.on('data', (d) => process.stderr.write(d));
  child.on('close', (code) => {
    console.log('deno-judge exit code: ' + code);
    resolve();
  });
});
console.log('toolchain-fact only: nothing executed on a GPU, UNMEASURED unchanged.');
