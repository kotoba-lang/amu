// Same kernel as kernel.rs, run by both node (after tsc) and deno (directly).
// Every intermediate stays below 2**47, inside the exact-integer range of a
// double, so the JavaScript result is identical to the i64 engines.
function kernel(n: number): number {
  const v1 = n * 48271 + 1;
  const x1 = v1 - Math.trunc(v1 / 2147483647) * 2147483647;
  const v2 = x1 * 48271 + 1;
  const x2 = v2 - Math.trunc(v2 / 2147483647) * 2147483647;
  const v3 = x2 * 48271 + 1;
  const x3 = v3 - Math.trunc(v3 / 2147483647) * 2147483647;
  const v4 = x3 * 48271 + 1;
  const x4 = v4 - Math.trunc(v4 / 2147483647) * 2147483647;
  const v5 = x4 * 48271 + 1;
  const x5 = v5 - Math.trunc(v5 / 2147483647) * 2147483647;
  const v6 = x5 * 48271 + 1;
  const x6 = v6 - Math.trunc(v6 / 2147483647) * 2147483647;
  const v7 = x6 * 48271 + 1;
  const x7 = v7 - Math.trunc(v7 / 2147483647) * 2147483647;
  const v8 = x7 * 48271 + 1;
  return v8 - Math.trunc(v8 / 2147483647) * 2147483647;
}

const host = globalThis as any;
const argv: string[] = host.Deno ? host.Deno.args : host.process.argv.slice(2);

function positiveArg(index: number, name: string): number {
  const value = Number(argv[index]);
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

const n = positiveArg(0, "n");
const calls = positiveArg(1, "calls");
const warmup = positiveArg(2, "warmup");
let result = 0;
for (let i = 0; i < warmup; i += 1) result = kernel(n);
const started = process_hrtime();
for (let i = 0; i < calls; i += 1) result = kernel(n);
const elapsed = process_hrtime() - started;
console.log(
  `{"format":"kotoba.runtime-sample/v1","calls":${calls},"warmupCalls":${warmup},` +
    `"elapsedNanoseconds":${elapsed},"result":${result}}`,
);

function process_hrtime(): number {
  return host.process?.hrtime?.bigint
    ? Number(host.process.hrtime.bigint())
    : Math.round(performance.now() * 1e6);
}
