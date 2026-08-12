import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

const DEFAULT_ATTEMPTS = 3;
const DEFAULT_DELAYS_MS = [1000, 3000];

// Keep this deliberately narrower than "any network-looking failure". A bad
// coordinate, missing artifact, or dependency conflict must fail on the first
// attempt; only failures that a second request can plausibly change are retried.
const TRANSIENT_PATTERNS = [
  /(?:http(?: response)?(?: status)?(?: code)?|status(?: code)?|response(?: code)?|returned error)[ :=]*(?:429|502|503|504)\b/i,
  /connection (?:reset|refused|timed out)/i,
  /read timed out/i,
  /temporary failure in name resolution/i,
  /could not resolve host/i,
  /gnutls recv error/i,
  /ssl_error_syscall/i,
  /ssl certificate problem: self signed certificate/i,
];

export function isTransientDependencyFailure(output) {
  return TRANSIENT_PATTERNS.some((pattern) => pattern.test(output));
}

function sleep(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

export function prefetchDependencies({
  alias,
  attempts = DEFAULT_ATTEMPTS,
  delaysMs = DEFAULT_DELAYS_MS,
  run = (args) => spawnSync("clojure", args, {
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  }),
  wait = sleep,
  stdout = process.stdout,
  stderr = process.stderr,
} = {}) {
  const args = alias ? ["-P", `-M:${alias}`] : ["-P"];

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const result = run(args);
    const out = result.stdout ?? "";
    const err = result.stderr ?? "";
    const output = `${out}\n${err}`;

    if (!result.error && result.status === 0) {
      if (out) stdout.write(out);
      if (err) stderr.write(err);
      stdout.write(`ci-dependency-prefetch: prepared ${alias ? `:${alias}` : "base"} basis\n`);
      return;
    }

    const transient = isTransientDependencyFailure(output);
    const retry = transient && attempt < attempts;
    if (!retry) {
      if (out) stdout.write(out);
      if (err) stderr.write(err);
      if (result.error) stderr.write(`${result.error.message}\n`);
      throw new Error(
        `ci-dependency-prefetch: ${alias ? `:${alias}` : "base"} basis failed ` +
        `on attempt ${attempt}/${attempts}${transient ? " after transient retries" : " (not retryable)"}`,
      );
    }

    const delay = delaysMs[Math.min(attempt - 1, delaysMs.length - 1)] ?? 0;
    stderr.write(
      `ci-dependency-prefetch: transient dependency fetch failure ` +
      `(attempt ${attempt}/${attempts}); retrying in ${delay}ms\n`,
    );
    wait(delay);
  }
}

export function parseArguments(argv) {
  if (argv.length === 0) return {};
  if (argv.length === 2 && argv[0] === "--alias" && /^[a-zA-Z0-9._-]+$/.test(argv[1])) {
    return { alias: argv[1] };
  }
  throw new Error("usage: node scripts/ci-dependency-prefetch.mjs [--alias <name>]");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    prefetchDependencies(parseArguments(process.argv.slice(2)));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
