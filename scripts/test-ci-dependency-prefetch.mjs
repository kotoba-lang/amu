import assert from "node:assert/strict";
import test from "node:test";

import {
  isTransientDependencyFailure,
  parseArguments,
  prefetchDependencies,
} from "./ci-dependency-prefetch.mjs";

function sink() {
  return { write() {} };
}

test("classifies only bounded transient fetch failures", () => {
  for (const message of [
    "HTTP response code: 429",
    "The requested URL returned error: 503",
    "Connection reset by peer",
    "SSL certificate problem: self signed certificate",
  ]) {
    assert.equal(isTransientDependencyFailure(message), true, message);
  }
  for (const message of [
    "Could not find artifact example:missing:jar:1.0",
    "Could not find artifact example:missing:jar:502",
    "Invalid git sha deadbeef",
    "Version conflict in dependency graph",
  ]) {
    assert.equal(isTransientDependencyFailure(message), false, message);
  }
});

test("retries a transient failure and preserves the requested basis", () => {
  const calls = [];
  const waits = [];
  const results = [
    { status: 1, stdout: "", stderr: "HTTP response code: 429" },
    { status: 0, stdout: "prepared\n", stderr: "" },
  ];

  prefetchDependencies({
    alias: "test",
    run(args) {
      calls.push(args);
      return results.shift();
    },
    wait(delay) { waits.push(delay); },
    stdout: sink(),
    stderr: sink(),
  });

  assert.deepEqual(calls, [["-P", "-M:test"], ["-P", "-M:test"]]);
  assert.deepEqual(waits, [1000]);
});

test("fails immediately for deterministic dependency errors", () => {
  let calls = 0;
  assert.throws(
    () => prefetchDependencies({
      run() {
        calls += 1;
        return { status: 1, stdout: "", stderr: "Could not find artifact x:y:jar:1" };
      },
      wait() { assert.fail("deterministic failures must not wait"); },
      stdout: sink(),
      stderr: sink(),
    }),
    /not retryable/,
  );
  assert.equal(calls, 1);
});

test("stops after the bounded transient retry budget", () => {
  let calls = 0;
  assert.throws(
    () => prefetchDependencies({
      attempts: 3,
      delaysMs: [1, 2],
      run() {
        calls += 1;
        return { status: 1, stdout: "", stderr: "Connection timed out" };
      },
      wait() {},
      stdout: sink(),
      stderr: sink(),
    }),
    /attempt 3\/3 after transient retries/,
  );
  assert.equal(calls, 3);
});

test("accepts base or one safe alias", () => {
  assert.deepEqual(parseArguments([]), {});
  assert.deepEqual(parseArguments(["--alias", "native-run"]), { alias: "native-run" });
  assert.throws(() => parseArguments(["--alias", "test:run"]), /usage:/);
  assert.throws(() => parseArguments(["--unknown"]), /usage:/);
});
