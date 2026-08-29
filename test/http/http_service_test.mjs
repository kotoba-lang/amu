// End-to-end test for runtime/http-service.mjs: a real Node http.Server,
// real HTTP requests over a real socket (global fetch), against real
// compiled :js-kotoba-v1 guests. Exits non-zero on any assertion failure.
//
// The shipped decision core is loaded from its checked-in location. The
// three fixture guests (a healthy demo, a decision-core double, and a
// capability-requiring probe) are compiled fresh by
// scripts/http-service-e2e.cljs into a tmp dir and handed in via env vars,
// so this proves the real compile -> host -> serve pipeline on every run
// rather than trusting a stale prebuilt binary.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createHttpService, ConfigError } from "../../runtime/http-service.mjs";

const here = path.dirname(new URL(import.meta.url).pathname);
const sha256 = p => createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const need = name => {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required (set by scripts/http-service-e2e.cljs)`);
  return value;
};

const decidePath = path.resolve(here, "..", "..", "runtime", "http", "route-decide.mjs");
const decideDoublePath = need("KOTOBA_HTTP_TEST_DECIDE_DOUBLE");
const probePath = need("KOTOBA_HTTP_TEST_DEMO");
const capPath = need("KOTOBA_HTTP_TEST_CAP");

const decideSha = sha256(decidePath);
const decideDoubleSha = sha256(decideDoublePath);
const probeSha = sha256(probePath);

let failures = 0;
const check = (label, cond) => {
  if (cond) { console.log(`ok - ${label}`); }
  else { failures += 1; console.error(`NOT OK - ${label}`); }
};

function baseConfig(decideOverride) {
  return {
    decide: { module: decidePath, sha256: decideSha, ...decideOverride },
    routes: [
      { method: "GET", path: "/health", module: probePath, sha256: probeSha, export: "health", hasBody: false },
      { method: "POST", path: "/echo", module: probePath, sha256: probeSha, export: "echo", hasBody: true, maxBodyBytes: 65536 }
    ]
  };
}

// ---- 1. real end-to-end dispatch over real HTTP -----------------------
{
  const service = await createHttpService(baseConfig());
  const address = await service.listen(0);
  const base = `http://127.0.0.1:${address.port}`;

  const health = await fetch(`${base}/health`);
  check("GET /health -> 200", health.status === 200);
  check("GET /health body", JSON.stringify(await health.json()) === '{"status":"ok"}');

  const echoBody = JSON.stringify({ a: 1, b: [true, null, "x"] });
  const echo = await fetch(`${base}/echo`, {
    method: "POST", headers: { "content-type": "application/json" }, body: echoBody
  });
  check("POST /echo -> 200", echo.status === 200);
  const echoText = await echo.text();
  check("POST /echo round-trips arbitrary JSON exactly", echoText === echoBody);

  const missing = await fetch(`${base}/nope`);
  check("GET /nope -> 404 (route-not-bound, via the compiled core)", missing.status === 404);
  check("GET /nope error body names not-found", (await missing.json()).error === "not-found");

  const wrongMethod = await fetch(`${base}/health`, { method: "POST" });
  check("POST /health (unregistered method) -> 404", wrongMethod.status === 404);

  const badContentType = await fetch(`${base}/echo`, { method: "POST", body: "{}" });
  check("POST /echo without content-type -> 400", badContentType.status === 400);

  const badJson = await fetch(`${base}/echo`, {
    method: "POST", headers: { "content-type": "application/json" }, body: "{not json"
  });
  check("POST /echo with malformed JSON -> 400", badJson.status === 400);
  check("POST /echo malformed JSON names body-not-json", (await badJson.json()).error === "body-not-json");

  const oversized = await fetch(`${base}/echo`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ x: "a".repeat(70000) })
  });
  check("POST /echo over the byte ceiling -> 413", oversized.status === 413);

  const healthz = await fetch(`${base}/healthz`);
  check("GET /healthz -> 200 (host built-in, unaffected by route table)", healthz.status === 200);

  const metrics = await fetch(`${base}/metrics`);
  const metricsText = await metrics.text();
  check("GET /metrics reports at least one success", /kotoba_http_service_success_total [1-9]/.test(metricsText));

  await service.close();
}

// ---- 2. delegation: swap the decision core, host must FOLLOW it -------
// A host that kept its own hardcoded status `cond` would still answer
// 404/204 here. Only a host that truly calls into the compiled core
// follows the double to 410/200.
{
  const service = await createHttpService(baseConfig({ module: decideDoublePath, sha256: decideDoubleSha }));
  const address = await service.listen(0);
  const base = `http://127.0.0.1:${address.port}`;

  const missing = await fetch(`${base}/nope`);
  check("delegation: unbound route follows the double's 410 (not the shipped core's 404)", missing.status === 410);

  await service.close();
}

// ---- 3. digest mismatch on a route module is refused at startup -------
{
  const tamperedPath = path.join(here, "probe-tampered-copy.mjs");
  fs.writeFileSync(tamperedPath, fs.readFileSync(probePath, "utf8") + "\n// tampered\n");
  let threw = null;
  try {
    await createHttpService({
      decide: { module: decidePath, sha256: decideSha },
      routes: [{ method: "GET", path: "/health", module: tamperedPath, sha256: probeSha, export: "health", hasBody: false }]
    });
  } catch (error) { threw = error; }
  check("digest mismatch on a route module is refused at startup", threw instanceof ConfigError
    && /digest mismatch/.test(threw.message));
  fs.rmSync(tamperedPath);
}

// ---- 4. a module that requires a capability is refused, not silently granted --
{
  const capSha = sha256(capPath);
  let threw = null;
  try {
    await createHttpService({
      decide: { module: decidePath, sha256: decideSha },
      routes: [{ method: "GET", path: "/main", module: capPath, sha256: capSha, export: "main", hasBody: false }]
    });
  } catch (error) { threw = error; }
  check("a module requiring capabilities is refused (this host grants none)", threw instanceof ConfigError
    && /requires \[7\]/.test(threw.message));
}

// ---- 5. the shipped decide core carries a stable source digest --------
// (scripts/http-service-e2e.cljs additionally recompiles route-decide.kotoba
// from source on every run and fails the whole suite if that digest drifts
// from the shipped one -- see its "drift" step.)
{
  const shipped = await import(decidePath);
  const digest = shipped.kotobaArtifact.sourceDigest;
  check("shipped decide core carries a non-empty source digest", typeof digest === "string" && digest.length > 0);
  check("provenance file exists alongside the shipped artifact", fs.existsSync(decidePath + ".provenance.edn"));
}

console.log(`\n${failures === 0 ? "PASS" : "FAIL"}: ${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
