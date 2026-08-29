// Real-route pressure test for runtime/http-service.mjs -- the second real
// cloud-itonami-app route served over the JVM-free host (ADR-2608760000
// addendum 2), after GET /health (addendum 1).
//
// This route is served over the SAME shared runtime/http/route-decide.mjs
// decide core the synthetic demo and the /health route already use, plus a
// new response guest (examples/cloud-itonami-oauth-resource-route.kotoba)
// carrying the REAL RFC 9728 metadata shape from
// cloud.itonami.app.oauth-resource/metadata*.
//
// What this does NOT prove: that this host's admission decision for
// GET /.well-known/oauth-protected-resource/mcp is
// `oauth_resource_core.kotoba`'s own `oauth-resource-route?` (it isn't --
// see that guest's header). That separate, more precise claim -- the SAME
// core agreeing between the JVM/KIR-interpreter oracle and this repo's
// `:js-kotoba-v1` target across a battery including cross-admission against
// its sibling health core -- is proven by
// scripts/cloud-itonami-oauth-resource-parity.cljs, not here.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createHttpService } from "../../runtime/http-service.mjs";

const here = path.dirname(new URL(import.meta.url).pathname);
const sha256 = p => createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const need = name => {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required (set by scripts/cloud-itonami-oauth-resource-route-e2e.cljs)`);
  return value;
};

const decidePath = path.resolve(here, "..", "..", "runtime", "http", "route-decide.mjs");
const routePath = need("KOTOBA_HTTP_TEST_CLOUD_ITONAMI_OAUTH_RESOURCE_ROUTE");

const ADMITTED = "/.well-known/oauth-protected-resource/mcp";

let failures = 0;
const check = (label, cond) => {
  if (cond) { console.log(`ok - ${label}`); }
  else { failures += 1; console.error(`NOT OK - ${label}`); }
};

const config = {
  decide: { module: decidePath, sha256: sha256(decidePath) },
  routes: [
    { method: "GET", path: ADMITTED, module: routePath, sha256: sha256(routePath),
      export: "oauth-protected-resource", hasBody: false }
  ]
};

{
  const service = await createHttpService(config);
  const address = await service.listen(0);
  const base = `http://127.0.0.1:${address.port}`;

  const res = await fetch(`${base}${ADMITTED}`);
  check(`GET ${ADMITTED} -> 200`, res.status === 200);
  const body = await res.json();

  // The three fields that are REAL fixed constants in
  // cloud.itonami.app.oauth-resource, copied verbatim -- assert them exactly.
  check("resource_name is the real constant",
    body.resource_name === "Itonami Cloud MCP");
  check("bearer_methods_supported is the real constant",
    Array.isArray(body.bearer_methods_supported)
    && body.bearer_methods_supported.length === 1
    && body.bearer_methods_supported[0] === "header");
  check("scopes_supported is the real `scopes` def, in order",
    Array.isArray(body.scopes_supported)
    && body.scopes_supported.join(",") === "mcp:tools,tenant:connect,repository:read,repository:write");

  // The two config-derived fields must be present (RFC 9728 shape) AND must
  // honestly name themselves as not-live rather than carrying an invented
  // plausible value.
  check("resource is present and honestly marked representative",
    typeof body.resource === "string" && body.resource.startsWith("representative-"));
  check("authorization_servers is present and honestly marked representative",
    Array.isArray(body.authorization_servers)
    && body.authorization_servers.length === 1
    && body.authorization_servers[0].startsWith("representative-"));

  // Exactly the five keys metadata* builds -- no more, no less.
  check("body has exactly the five keys metadata* builds",
    JSON.stringify(Object.keys(body).sort())
      === JSON.stringify(["authorization_servers", "bearer_methods_supported",
                          "resource", "resource_name", "scopes_supported"]));

  const wrongMethod = await fetch(`${base}${ADMITTED}`, { method: "POST" });
  check("POST on the admitted path (unregistered) -> 404", wrongMethod.status === 404);

  const truncated = await fetch(`${base}/.well-known/oauth-protected-resource`);
  check("GET the path without /mcp -> 404", truncated.status === 404);

  const trailing = await fetch(`${base}${ADMITTED}/`);
  check("GET the path with a trailing slash -> 404", trailing.status === 404);

  // The sibling route from addendum 1 is NOT registered on this service --
  // proves this config serves its own route, not a catch-all.
  const health = await fetch(`${base}/health`);
  check("GET /health -> 404 (not registered on this service)", health.status === 404);

  await service.close();
}

console.log(`\n${failures === 0 ? "PASS" : "FAIL"}: ${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
