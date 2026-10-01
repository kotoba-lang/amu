// bootstrap-tooling
// BOOTSTRAP REFERENCE (node + WebAssembly through runtime/browser-host.mjs), not a product path.
// Runs an exported text->text function of a wasm32 kotoba artifact: whole stdin in, whole answer out.
//   node wasm-run.mjs <artifact.wasm> <export> < input > output
import { readFileSync, writeSync } from "node:fs";
const [, , wasm, entry] = process.argv;
const host = await import(new URL("../../runtime/browser-host.mjs", import.meta.url).href);
const h = await host.instantiateKotoba(readFileSync(wasm));
const out = h.instance.exports[entry](readFileSync(0, "utf8"));
let b = Buffer.from(out, "utf8"), off = 0;
while (off < b.length) off += writeSync(1, b, off);
