// scripts/test-native-check-route.mjs -- BOOTSTRAP-TOOL test of bin/amu's native `check` route (ADR 0366).
//
//   node scripts/test-native-check-route.mjs [path/to/amu-front]
//
// 1. the routing rule (`nativeCheckRoute`): which invocations AMU_FRONT takes and which stay on nbb;
// 2. end to end with a FAKE amu-front (a shell script that records its argv and environment): bin/amu
//    spawns only it, with `check <absolute file>` and an empty environment, and passes its exit status
//    0/65 through; any other status is exit 70 naming the bootstrap route;
// 3. with a real amu-front (argument or AMU_FRONT), one accepted and one refused program.
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const amu = path.join(root, "bin", "amu");
const { nativeCheckRoute } = require(amu);
let n = 0;
const ok = (name) => { n += 1; console.log(`ok ${n} ${name}`); };

const yes = { exists: () => true };
const no = { exists: () => false };
assert.deepEqual(nativeCheckRoute(["check", "/a.kotoba"], {}, yes), {}); ok("unset AMU_FRONT: nbb route");
assert.deepEqual(nativeCheckRoute(["check", "/a.kotoba"], { AMU_FRONT: "" }, yes), {}); ok("empty AMU_FRONT: nbb route");
assert.deepEqual(nativeCheckRoute(["check", "/a.kotoba"], { AMU_FRONT: "/bin/f" }, yes), { binary: "/bin/f" }); ok("single-file check: native");
for (const args of [["check", "/a.kotoba", "--source-path", "/s"], ["check", "/a.kotoba", "--policy", "/p.edn"],
                    ["check", "/a.kotoba", "--json"], ["check", "--json"], ["compile", "/a.kotoba"], ["check"]]) {
  assert.deepEqual(nativeCheckRoute(args, { AMU_FRONT: "/bin/f" }, yes), {});
  ok(`out of domain stays on nbb: ${args.join(" ")}`);
}
assert.match(nativeCheckRoute(["check", "/a.kotoba"], { AMU_FRONT: "rel/f" }, yes).reason, /absolute path/); ok("relative AMU_FRONT refused");
assert.match(nativeCheckRoute(["check", "/a.kotoba"], { AMU_FRONT: "/bin/f" }, no).reason, /existing/); ok("missing AMU_FRONT refused");

// Under /private/tmp when it exists: a packaged amu-front reads only inside the wire-35 scope baked into it
// (build/compose/amu-front.info: the repo, amu-embench, /private/tmp, /tmp), and macOS's os.tmpdir() is not in it.
const base = fs.existsSync("/private/tmp") ? "/private/tmp" : os.tmpdir();
const dir = fs.realpathSync(fs.mkdtempSync(path.join(base, "native-check-")));
const log = path.join(dir, "argv");
const fake = path.join(dir, "fake-front");
fs.writeFileSync(fake, `#!/bin/sh\nprintf '%s|' "$@" > ${log}\nenv | grep -c -E '^(PATH|HOME|AMU_FRONT|NODE_[A-Z_]*)=' >> ${log}\necho "ok fake"\nexit 0\n`, { mode: 0o755 });
const src = path.join(dir, "p.kotoba");
fs.writeFileSync(src, "(ns p {:kotoba/export [main]})\n(defn main [] :i64 1)\n");
const run = (env, cwd = dir) => spawnSync(process.execPath, [amu, "check", "p.kotoba"],
  { cwd, encoding: "utf8", env: { ...process.env, AMU_FRONT: fake, ...env } });
let r = run({});
assert.equal(r.status, 0); assert.equal(r.stdout, "ok fake\n");
assert.equal(fs.readFileSync(log, "utf8"), `check|${src}|0\n`); ok("fake: argv is check <absolute file>, no PATH/HOME/AMU_FRONT/NODE_* in its environment, exit 0");
fs.writeFileSync(fake, `#!/bin/sh\necho "error: refused" >&2\nexit 65\n`, { mode: 0o755 });
r = run({}); assert.equal(r.status, 65); assert.equal(r.stderr, "error: refused\n"); ok("fake: refusal exit 65 passes through");
fs.writeFileSync(fake, `#!/bin/sh\nexit 134\n`, { mode: 0o755 });
r = run({}); assert.equal(r.status, 70); assert.match(r.stderr, /did not answer \(exit 134\).*unset AMU_FRONT/); ok("fake: trap is exit 70 naming the bootstrap route");

const real = process.argv[2] || process.env.AMU_FRONT_REAL;
if (real && fs.existsSync(real)) {
  r = spawnSync(process.execPath, [amu, "check", src], { encoding: "utf8", env: { ...process.env, AMU_FRONT: real } });
  assert.equal(r.status, 0, r.stderr); assert.match(r.stdout, /^ok profile=default effects=#\{\} exports=\[main\]\n$/); ok("real amu-front: accepted");
  const bad = path.join(dir, "bad.kotoba");
  fs.writeFileSync(bad, "(ns bad {:kotoba/export [main]})\n(defn main [] :i64 (+ 1 \"x\"))\n");
  r = spawnSync(process.execPath, [amu, "check", bad], { encoding: "utf8", env: { ...process.env, AMU_FRONT: real } });
  assert.equal(r.status, 65); assert.match(r.stderr, /^error: subset-reject at /); ok("real amu-front: refused");
} else {
  console.log("# no real amu-front given: steps 3 skipped (pass build/compose/amu-front)");
}
fs.rmSync(dir, { recursive: true, force: true });
console.log(`1..${n}`);
