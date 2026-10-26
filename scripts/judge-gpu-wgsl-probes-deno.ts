// JUN-59/JUN-60 -- judge the infinite-neutral probe corpus through Deno's
// bundled wgpu/Naga (a SECOND WGSL front end), for the fix-question slice:
// "is the class-1 refusal a Tint const-eval limit or real spec drift in the
// neutral spelling". The probes need no subgroups, so Naga CAN judge them
// even though it refuses `enable subgroups;` outright (measured 2026-10-25).
//
//   deno run --allow-all --unstable-webgpu \
//     scripts/judge-gpu-wgsl-probes-deno.ts <corpus-dir>
//
// TOOLCHAIN FACT ONLY: shader-creation validation. Nothing executes on a
// GPU; no timing or speedup is claimed; UNMEASURED is unchanged everywhere.
// Deterministic: files processed in sorted order; the only run-varying
// lines are the self-dating header and the toolchain identity.

export {};

interface DenoLike {
  args: string[];
  version: { deno: string; v8: string };
  exit: (code: number) => void;
  readDir: (path: string) => AsyncIterable<{ isFile: boolean; name: string }>;
  readTextFile: (path: string) => Promise<string>;
}
const D = (globalThis as unknown as { Deno: DenoLike }).Deno;

const dir = D.args[0];
if (!dir) {
  console.error('usage: judge-gpu-wgsl-probes-deno.ts <corpus-dir>');
  D.exit(2);
}

console.log('toolchain-2: Deno ' + D.version.deno + ' / V8 ' + D.version.v8
  + ' / bundled wgpu-Naga (deno --unstable-webgpu)');
console.log('run-at: ' + new Date().toISOString());

const gpu = (globalThis as { navigator?: { gpu?: unknown } }).navigator?.gpu;
if (!gpu) {
  console.log('NO navigator.gpu in this Deno build -- Naga judges nothing.');
  D.exit(2);
}

const entries: string[] = [];
for await (const e of D.readDir(dir)) {
  if (e.isFile && e.name.endsWith('.wgsl')) entries.push(e.name);
}
entries.sort();
console.log('corpus: ' + dir);
console.log('files: ' + entries.length + ' (sorted)');

const adapter = await (gpu as {
  requestAdapter: () => Promise<unknown>;
}).requestAdapter();
if (!adapter) {
  console.log('NO WebGPU adapter -- Naga judges nothing.');
  D.exit(2);
}
const device = await (adapter as {
  requestDevice: () => Promise<unknown>;
}).requestDevice();

let clean = 0;
for (const name of entries) {
  const code = await D.readTextFile(dir + '/' + name);
  console.log('--- ' + name + ' (' + new TextEncoder().encode(code).length + ' bytes)');
  try {
    const mod = (device as {
      createShaderModule: (d: { code: string }) => unknown;
    }).createShaderModule({ code });
    const info = await (mod as {
      getCompilationInfo: () => Promise<{
        messages: Array<{ type: string; lineNum: number; linePos: number; message: string }>;
      }>;
    }).getCompilationInfo();
    for (const m of info.messages) {
      console.log('  msg ' + m.type + '@' + m.lineNum + ':' + m.linePos + ' ' + m.message);
    }
    const refused = info.messages.some((m) => m.type === 'error');
    console.log('  compile-info: ' + (refused ? 'error' : 'ok'));
    console.log('  VERDICT: ' + (refused ? 'DOES NOT VALIDATE CLEAN' : 'VALIDATES CLEAN'));
    if (!refused) clean += 1;
  } catch (e) {
    console.log('  THREW: ' + String(e).slice(0, 300));
    console.log('  VERDICT: DOES NOT VALIDATE CLEAN');
  }
}
console.log('===');
console.log('summary (Deno/Naga): ' + entries.length + ' files, ' + clean
  + ' validate clean, ' + (entries.length - clean) + ' do not');
console.log('toolchain-fact only: nothing executed on a GPU, UNMEASURED unchanged.');
