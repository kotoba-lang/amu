// Real-route pressure test for runtime/http-service.mjs, following
// ADR-2608760000's "Proposed next slice": one real, already-decision-cored
// cloud-itonami-app route (GET /health) served over a real Node http.Server
// and real HTTP requests, using the SAME `runtime/http/route-decide.mjs`
// shared decide core the synthetic demo (test/http/http_service_test.mjs)
// already proves, plus a NEW response guest
// (examples/cloud-itonami-health-route.kotoba) carrying the REAL
// cloud-itonami-app JSON shape.
//
// What this does NOT prove: that this host's admission decision for GET
// /health is `cloud.itonami.app.health_core.kotoba`'s own `health-route?`
// (it isn't -- see that file's header and this route guest's header). That
// separate, more precise claim -- the SAME `health_core.kotoba` source
// agreeing between the JVM/KIR-interpreter oracle and this repo's
// `:js-kotoba-v1` target across a battery of (method, path) inputs -- is
// proven by scripts/cloud-itonami-health-parity.cljs, not here.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createHttpService, ConfigError } from "../../runtime/http-service.mjs";

const here = path.dirname(new URL(import.meta.url).pathname);
const sha256 = p => createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const need = name => {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required (set by scripts/cloud-itonami-health-route-e2e.cljs)`);
  return value;
};

const decidePath = path.resolve(here, "..", "..", "runtime", "http", "route-decide.mjs");
const routePath = need("KOTOBA_HTTP_TEST_CLOUD_ITONAMI_HEALTH_ROUTE");

const decideSha = sha256(decidePath);
const routeSha = sha256(routePath);

let failures = 0;
const check = (label, cond) => {
  if (cond) { console.log(`ok - ${label}`); }
  else { failures += 1; console.error(`NOT OK - ${label}`); }
};

const config = {
  decide: { module: decidePath, sha256: decideSha },
  routes: [
    { method: "GET", path: "/health", module: routePath, sha256: routeSha, export: "health", hasBody: false }
  ]
};

{
  const service = await createHttpService(config);
  const address = await service.listen(0);
  const base = `http://127.0.0.1:${address.port}`;

  const health = await fetch(`${base}/health`);
  check("GET /health -> 200", health.status === 200);
  const body = await health.json();
  check("GET /health body matches the real cloud-itonami-app shape's keys",
    body.ok === true
    && body.service === "cloud-itonami-app"
    && body.schema === "cloud.itonami.app.health.v1"
    && typeof body.store === "string"
    && typeof body["drive-store"] === "string");
  check("GET /health body honestly names its store/drive-store as representative, not live",
    body.store.startsWith("representative-") && body["drive-store"].startsWith("representative-"));

  const wrongMethod = await fetch(`${base}/health`, { method: "POST" });
  check("POST /health (wrong method, unregistered route) -> 404", wrongMethod.status === 404);

  const missing = await fetch(`${base}/nope`);
  check("GET /nope -> 404", missing.status === 404);

  const healthz = await fetch(`${base}/healthz`);
  check("GET /healthz -> 200 (host built-in, distinct from /health)", healthz.status === 200);

  await service.close();
}

console.log(`\n${failures === 0 ? "PASS" : "FAIL"}: ${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
