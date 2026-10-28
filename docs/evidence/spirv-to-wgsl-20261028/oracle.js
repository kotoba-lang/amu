// test-time oracle only: does the WGSL pass wgpu's validation? (never part of the product route)
const text = await Deno.readTextFile(Deno.args[0]);
const parts = text.split(/^\/\/KERNEL /m).slice(1);
const adapter = await navigator.gpu.requestAdapter();
const features = [...adapter.features];
const dev = await adapter.requestDevice();
for (const p of parts) {
  const nl = p.indexOf("\n"); const name = p.slice(0, nl); const code = p.slice(nl + 1).replace(/^run-exit=.*$/m, "");
  const info = await dev.createShaderModule({ code }).getCompilationInfo();
  const errs = info.messages.filter(m => m.type === "error");
  console.log(name, errs.length ? "FAIL" : "ok", errs.slice(0, 3).map(m => `L${m.lineNum}: ${m.message}`).join(" | "));
}
