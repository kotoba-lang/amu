import { readFileSync } from "node:fs";
import { instantiateKotoba } from "../../runtime/browser-host.mjs";

const [artifact, exportName = "scalar", mode, iterationsText = "1", warmupText] =
  process.argv.slice(2);
const iterations = Number(iterationsText);
const warmupIterations = Number(warmupText ?? Math.min(iterations, 1_000));
const { instance } = await instantiateKotoba(readFileSync(artifact));
const workload = instance.exports[exportName];
if (typeof workload !== "function") throw new Error(`Wasm export ${exportName} is absent`);

if (mode === "--once") {
  process.stdout.write(`${JSON.stringify({ checksum: Number(workload(BigInt(iterations))) })}\n`);
} else {
  workload(BigInt(warmupIterations));
  const started = process.hrtime.bigint();
  const result = workload(BigInt(iterations));
  const elapsed = process.hrtime.bigint() - started;
  process.stdout.write(`${JSON.stringify({
    iterations,
    warmupIterations,
    checksum: Number(result),
    elapsedNanoseconds: Number(elapsed),
  })}\n`);
}
