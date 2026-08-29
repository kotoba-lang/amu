/**
 * kotoba.http-service/v1 -- a JVM-free, multi-route HTTP host for compiled
 * Kotoba guests, built on Node's `node:http` and the `:js-kotoba-v1`
 * restricted-ESM compile target (`amu compile --target js`).
 *
 * This generalizes `wasi-service.mjs` (one fixed `POST /v1/run` entry, a
 * request schema locked to 5 i64 args) into a data-driven route table with
 * arbitrary-size JSON string bodies, while keeping the same safety
 * discipline: every guest module is sealed by a pinned sha256 digest read
 * before it is imported, every module must declare zero required
 * capabilities (this host grants nothing -- no DOM, no fs, no network, no
 * clock), request/response bodies are bounded and exactly validated, and
 * concurrency is bounded.
 *
 * ## The decision/mechanism split (mirrors kotoba-lang/mesh's route.kotoba)
 *
 * Which HTTP method+path this host recognises as a built-in (/healthz,
 * /metrics), which outcome a request produces (:health-ok, :answer,
 * :no-answer, :route-not-bound), and which HTTP status an outcome gets are
 * NOT decided by a `cond` in this file. They are decided by
 * `http-route-decide.kotoba`, compiled ahead of time and called on every
 * request. What stays here, and why (same boundary mesh measured,
 * ADR-2608112100): the route TABLE (a collection that grows with the
 * deployment -- the core is handed a boolean saying whether a route is
 * bound, never the table itself), reading the guest's answer out of the
 * restricted-ESM instance, and writing the socket. Those are effects and a
 * growing collection, not a decision.
 *
 * ## Why no Worker thread (unlike wasi-service.mjs)
 *
 * wasi-service.mjs runs each guest call in a `worker_threads.Worker` because
 * a wasm32-wasi module is a black box that could spin forever without a
 * hard OS-level cutoff. A `:js-kotoba-v1` restricted-ESM instance is
 * different: `instantiateKotoba()` opens a fixed fuel budget that is spent,
 * never replenished (see amu/runtime/dom-driver.mjs), so a guest call either
 * returns or traps with `fuel-exhausted` -- it cannot spin the event loop
 * forever. A fresh instance per call (matching dom-driver's own pattern) is
 * therefore both correct and simple: no worker, no postMessage, no
 * serialization boundary for plain strings/i64/bool/keyword values.
 *
 * ## Two kinds of guest: `routes` (pure) and `apps` (stateful)
 *
 * A `routes` entry is the original shape: one export, `:string -> :string`,
 * no state, fresh instance per call.
 *
 * An `apps` entry is a `kotoba/app` in the sense of ADR-2607201300 and
 * ADR-2608261100 -- an application, not an admission predicate. It exports
 * the same three functions `runtime/dom-driver.mjs` drives, with the screen
 * replaced by a socket:
 *
 *     init  ()                 -> state
 *     step  (state, event)     -> next state
 *     view  (state)            -> the answer to send
 *
 * The split is the same one this file already keeps. The GUEST holds the
 * product semantics: what a state is, what an event means, which events
 * change it, and what the state amounts to. The HOST holds mechanism only --
 * the socket, the instantiate, the bytes, and the cell the state lives in
 * between requests. It never reads a field of the state: the state is an
 * opaque JSON string it hands back to the guest unexamined.
 *
 * State is a `:string` for the same reason a fresh instance is made per
 * call: fuel is a per-instance budget, spent and never replenished, so a
 * `:document` or a record is a value inside ONE instance and cannot be
 * handed to the next one. Text is what survives the instance boundary. That
 * makes the guest read its own state and its own request body, which is only
 * possible because `kotoba-lang/json`'s `json_scalar.kotoba` exists
 * (ADR-2608292330) -- see `examples/approval-queue-app.kotoba`.
 *
 * A guest that scans its own body spends fuel per code point, so an app's
 * traversable input is fixed at COMPILE time by `amu compile --fuel N`, not
 * by anything this host can raise later. An app therefore declares
 * `maxBodyBytes`/`maxStateBytes` it was compiled to afford, and this host
 * enforces both -- a body it admits that the guest cannot afford to scan
 * would trap rather than answer.
 *
 * ## What this does NOT do (named explicitly, not silently)
 *
 * - No path parameters / wildcards. Routes are exact (method, path) pairs.
 * - No sessions, cookies, or streaming request/response bodies. An app's
 *   state is ONE cell shared by every caller, not a per-client session.
 * - A `routes` (pure) guest still does no structural JSON parsing: its body
 *   crosses as a validated-syntactically-JSON `:string` and it must do its
 *   own string work. An `apps` guest does exactly that string work, in the
 *   guest, and that is the point of the shape.
 * - No persistence. An app's state lives in memory and starts again from
 *   `init()` when the process restarts.
 */

import fs from "node:fs";
import http from "node:http";
import { createHash } from "node:crypto";

const MAX_CONCURRENCY = 8;
const MAX_BODY_BYTES_CEILING = 65536; // == kotobaArtifact.stringLimits.valueBytes (measured)
const MAX_STATE_BYTES_CEILING = 65536; // same ceiling: state crosses as a :string too
const MAX_ROUTES = 256;
const MAX_APPS = 32;
const ENTRY_NAME = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;
const METHODS = new Set(["GET", "POST"]);

class ConfigError extends Error {
  constructor(message) { super(message); this.name = "ConfigError"; }
}

function sha256Hex(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}

/** Read a module's bytes and refuse to proceed unless they hash to the pinned digest. */
function sealedBytes(path, expectedSha256) {
  if (!/^[0-9a-f]{64}$/.test(expectedSha256 ?? ""))
    throw new ConfigError(`${path}: sha256 must be a sealed lowercase digest`);
  let bytes;
  try { bytes = fs.readFileSync(path); }
  catch (error) { throw new ConfigError(`${path}: cannot read module (${error.message})`); }
  const actual = sha256Hex(bytes);
  if (actual !== expectedSha256)
    throw new ConfigError(`${path}: sealed module digest mismatch (want ${expectedSha256}, got ${actual})`);
  return bytes;
}

/**
 * Load a `:js-kotoba-v1` module, verify it is sealed at the pinned digest,
 * and verify it declares zero required capabilities -- this host grants
 * none, so a module that asks for any is refused rather than silently
 * denied at call time.
 */
async function loadPureModule(path, expectedSha256) {
  sealedBytes(path, expectedSha256);
  const mod = await import(path);
  const artifact = mod?.kotobaArtifact;
  if (!artifact || artifact.schema !== "kotoba-js-artifact/v1")
    throw new ConfigError(`${path}: not a kotoba-js-artifact/v1 module`);
  const caps = artifact.requiredCapabilities;
  if (!Array.isArray(caps) || caps.length !== 0)
    throw new ConfigError(`${path}: this host grants no capabilities; module requires ${JSON.stringify(caps)}`);
  if (typeof mod.instantiateKotoba !== "function")
    throw new ConfigError(`${path}: module does not export instantiateKotoba`);
  return mod;
}

function freshInstance(mod) {
  return mod.instantiateKotoba({});
}

/**
 * Bound a state value the host is about to carry: it must be a string, must
 * fit the app's declared ceiling, and must be syntactically JSON. Returns
 * null when admissible, otherwise a reason.
 *
 * This is the host bounding an opaque value, NOT the host reading it. It
 * never looks at a field: what the state means is entirely the guest's.
 * JSON-parsing it is the same syntactic check already applied to request and
 * response bodies, so a guest cannot hand back bytes the next `step` could
 * not scan.
 */
function admissibleState(value, app) {
  if (typeof value !== "string") return "state-not-a-string";
  const bytes = Buffer.byteLength(value, "utf8");
  if (bytes > app.maxStateBytes) return "state-too-large";
  try { JSON.parse(value); } catch { return "state-not-json"; }
  return null;
}

function requireExport(instance, name, modulePath) {
  if (typeof instance?.[name] !== "function")
    throw new ConfigError(`${modulePath}: module does not export ${name}`);
}

/**
 * @param {object} config
 * @param {{module:string, sha256:string}} config.decide
 * @param {Array<{method:string, path:string, module:string, sha256:string,
 *                 export:string, hasBody:boolean, maxBodyBytes?:number}>} config.routes
 */
export async function createHttpService(config) {
  if (!isPlainObject(config)) throw new ConfigError("config must be a plain object");
  if (!isPlainObject(config.decide)) throw new ConfigError("config.decide must be a plain object");
  // `routes` may be empty when the service's routes all come from `apps`.
  // What must not be empty is the SERVICE: a host answering nothing but its
  // own built-ins is a misconfiguration, so that is checked once both
  // sources have been read, rather than requiring either one specifically.
  if (!Array.isArray(config.routes))
    throw new ConfigError("config.routes must be an array");
  if (config.routes.length > MAX_ROUTES)
    throw new ConfigError(`config.routes exceeds the admitted ceiling of ${MAX_ROUTES}`);

  const decideMod = await loadPureModule(config.decide.module, config.decide.sha256);
  {
    const probe = freshInstance(decideMod);
    for (const name of ["route-key", "builtin-kind", "outcome", "answer?", "status-for"])
      requireExport(probe, name, config.decide.module);
  }

  // Cache loaded modules by absolute path so a module shared by several
  // routes (one export per route) is read and digest-checked exactly once.
  const moduleCache = new Map();
  const routeTable = new Map();

  for (const raw of config.routes) {
    if (!isPlainObject(raw)) throw new ConfigError("each route must be a plain object");
    const { method, path, module: modulePath, sha256, export: exportName, hasBody } = raw;
    if (!METHODS.has(method)) throw new ConfigError(`route ${JSON.stringify(raw)}: method must be GET or POST`);
    if (typeof path !== "string" || !path.startsWith("/") || path.length > 256 || path.includes("?"))
      throw new ConfigError(`route ${JSON.stringify(raw)}: path is not an admitted absolute path`);
    if (!ENTRY_NAME.test(exportName ?? ""))
      throw new ConfigError(`route ${path}: export name is not admitted`);
    if (typeof hasBody !== "boolean") throw new ConfigError(`route ${path}: hasBody must be a boolean`);
    const maxBodyBytes = raw.maxBodyBytes ?? MAX_BODY_BYTES_CEILING;
    if (!Number.isInteger(maxBodyBytes) || maxBodyBytes < 1 || maxBodyBytes > MAX_BODY_BYTES_CEILING)
      throw new ConfigError(`route ${path}: maxBodyBytes must be in [1, ${MAX_BODY_BYTES_CEILING}]`);

    let entry = moduleCache.get(modulePath);
    if (entry === undefined) {
      const mod = await loadPureModule(modulePath, sha256);
      entry = { mod, sha256 };
      moduleCache.set(modulePath, entry);
    } else if (entry.sha256 !== sha256) {
      throw new ConfigError(`route ${path}: ${modulePath} was already pinned to a different sha256`);
    }
    requireExport(freshInstance(entry.mod), exportName, modulePath);

    const key = `${method} ${path}`;
    if (routeTable.has(key)) throw new ConfigError(`duplicate route: ${key}`);
    routeTable.set(key, { kind: "pure", method, path, mod: entry.mod, export: exportName, hasBody, maxBodyBytes });
  }

  // -- apps: init/step/view guests whose state the host carries between
  // requests. The host never inspects the state; it only bounds it.
  const apps = [];
  const rawApps = config.apps ?? [];
  if (!Array.isArray(rawApps)) throw new ConfigError("config.apps must be an array");
  if (rawApps.length > MAX_APPS) throw new ConfigError(`config.apps exceeds the admitted ceiling of ${MAX_APPS}`);

  for (const raw of rawApps) {
    if (!isPlainObject(raw)) throw new ConfigError("each app must be a plain object");
    const { name, module: modulePath, sha256 } = raw;
    if (!ENTRY_NAME.test(name ?? "")) throw new ConfigError(`app ${JSON.stringify(name)}: name is not admitted`);
    const initName = raw.init ?? "init";
    const stepName = raw.step ?? "step";
    const viewName = raw.view ?? "view";
    for (const n of [initName, stepName, viewName])
      if (!ENTRY_NAME.test(n)) throw new ConfigError(`app ${name}: export name ${JSON.stringify(n)} is not admitted`);

    const maxStateBytes = raw.maxStateBytes ?? MAX_STATE_BYTES_CEILING;
    if (!Number.isInteger(maxStateBytes) || maxStateBytes < 1 || maxStateBytes > MAX_STATE_BYTES_CEILING)
      throw new ConfigError(`app ${name}: maxStateBytes must be in [1, ${MAX_STATE_BYTES_CEILING}]`);

    let entry = moduleCache.get(modulePath);
    if (entry === undefined) {
      const mod = await loadPureModule(modulePath, sha256);
      entry = { mod, sha256 };
      moduleCache.set(modulePath, entry);
    } else if (entry.sha256 !== sha256) {
      throw new ConfigError(`app ${name}: ${modulePath} was already pinned to a different sha256`);
    }
    {
      const probe = freshInstance(entry.mod);
      for (const n of [initName, stepName, viewName]) requireExport(probe, n, modulePath);
    }

    // Seed the cell by asking the guest, at startup, what a fresh state is.
    // A guest that cannot produce an admissible initial state is a config
    // error, not a runtime surprise on the first request.
    let initial;
    try { initial = freshInstance(entry.mod)[initName](); }
    catch (error) { throw new ConfigError(`app ${name}: ${initName}() trapped (${error.message})`); }
    const app = { name, mod: entry.mod, step: stepName, view: viewName, maxStateBytes, state: null };
    const seeded = admissibleState(initial, app);
    if (seeded !== null) throw new ConfigError(`app ${name}: ${initName}() returned ${seeded}`);
    app.state = initial;

    if (!Array.isArray(raw.routes) || raw.routes.length === 0)
      throw new ConfigError(`app ${name}: routes must be a non-empty array`);
    for (const r of raw.routes) {
      if (!isPlainObject(r)) throw new ConfigError(`app ${name}: each route must be a plain object`);
      const { method, path } = r;
      if (!METHODS.has(method)) throw new ConfigError(`app ${name}: route method must be GET or POST`);
      if (typeof path !== "string" || !path.startsWith("/") || path.length > 256 || path.includes("?"))
        throw new ConfigError(`app ${name}: route path ${JSON.stringify(path)} is not an admitted absolute path`);
      const event = r.event ?? false;
      if (typeof event !== "boolean") throw new ConfigError(`app ${name} route ${path}: event must be a boolean`);
      const maxBodyBytes = r.maxBodyBytes ?? MAX_BODY_BYTES_CEILING;
      if (!Number.isInteger(maxBodyBytes) || maxBodyBytes < 1 || maxBodyBytes > MAX_BODY_BYTES_CEILING)
        throw new ConfigError(`app ${name} route ${path}: maxBodyBytes must be in [1, ${MAX_BODY_BYTES_CEILING}]`);
      const key = `${method} ${path}`;
      if (routeTable.has(key)) throw new ConfigError(`duplicate route: ${key}`);
      routeTable.set(key, { kind: "app", method, path, app, hasBody: event, event, maxBodyBytes });
    }
    apps.push(app);
  }

  if (routeTable.size === 0)
    throw new ConfigError("config must declare at least one route, in routes or apps");

  const metrics = { requests: 0, success: 0, rejected: 0, busy: 0, traps: 0 };
  let active = 0;

  const respond = (response, status, value) => {
    const body = Buffer.from(JSON.stringify(value));
    response.writeHead(status, {
      "content-type": "application/json; charset=utf-8",
      "content-length": body.length,
      "cache-control": "no-store",
      "x-content-type-options": "nosniff"
    });
    response.end(body);
  };

  const readBody = (request, maxBodyBytes) => new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    const timer = setTimeout(() => reject(Object.assign(new Error("body-timeout"), { code: "body-timeout" })), 2000);
    request.on("data", chunk => {
      size += chunk.length;
      if (size > maxBodyBytes) {
        clearTimeout(timer);
        reject(Object.assign(new Error("body-too-large"), { code: "body-too-large" }));
      } else chunks.push(chunk);
    });
    request.on("end", () => { clearTimeout(timer); resolve(Buffer.concat(chunks)); });
    request.on("error", error => { clearTimeout(timer); reject(error); });
  });

  const server = http.createServer(async (request, response) => {
    let requestUrl;
    try { requestUrl = new URL(request.url ?? "/", "http://localhost"); }
    catch { respond(response, 400, { format: "kotoba.http-service-error/v1", error: "bad-request-line" }); return; }
    const method = request.method ?? "GET";
    const path = requestUrl.pathname;

    if (method === "GET" && path === "/healthz") {
      respond(response, 200, { format: "kotoba.http-service-health/v1", status: "ok" });
      return;
    }
    if (method === "GET" && path === "/metrics") {
      const body = Buffer.from(
        `# TYPE kotoba_http_service_requests_total counter\n` +
        `kotoba_http_service_requests_total ${metrics.requests}\n` +
        `# TYPE kotoba_http_service_success_total counter\n` +
        `kotoba_http_service_success_total ${metrics.success}\n` +
        `# TYPE kotoba_http_service_rejected_total counter\n` +
        `kotoba_http_service_rejected_total ${metrics.rejected}\n` +
        `# TYPE kotoba_http_service_busy_total counter\n` +
        `kotoba_http_service_busy_total ${metrics.busy}\n` +
        `# TYPE kotoba_http_service_guest_traps_total counter\n` +
        `kotoba_http_service_guest_traps_total ${metrics.traps}\n` +
        `# TYPE kotoba_http_service_active gauge\n` +
        `kotoba_http_service_active ${active}\n`
      );
      response.writeHead(200, { "content-type": "text/plain; version=0.0.4; charset=utf-8",
                                "content-length": body.length, "cache-control": "no-store" });
      response.end(body);
      return;
    }

    metrics.requests += 1;
    const decideInstance = freshInstance(decideMod);
    const kind = decideInstance["builtin-kind"](method, path);
    if (kind !== ":route") {
      // Reachable only if a caller adds new builtin kinds to the core
      // without adding a matching host branch -- refuse rather than guess.
      metrics.rejected += 1;
      respond(response, 500, { format: "kotoba.http-service-error/v1", error: "unhandled-kind" });
      return;
    }

    const key = decideInstance["route-key"](method, path);
    const route = routeTable.get(key);
    const bound = route !== undefined;

    if (!bound) {
      const outcome = decideInstance["outcome"](":route", false, false);
      const status = Number(decideInstance["status-for"](outcome));
      metrics.rejected += 1;
      respond(response, status, { format: "kotoba.http-service-error/v1", error: "not-found" });
      return;
    }

    if (active >= MAX_CONCURRENCY) {
      metrics.busy += 1;
      respond(response, 503, { format: "kotoba.http-service-error/v1", error: "busy" });
      return;
    }

    let bodyText;
    if (route.hasBody) {
      if (request.headers["content-type"] !== "application/json") {
        metrics.rejected += 1;
        respond(response, 400, { format: "kotoba.http-service-error/v1", error: "content-type-rejected" });
        return;
      }
      let raw;
      try { raw = await readBody(request, route.maxBodyBytes); }
      catch (error) {
        metrics.rejected += 1;
        respond(response, error?.code === "body-too-large" ? 413 : 400,
                { format: "kotoba.http-service-error/v1", error: error?.code ?? "body-read-failed" });
        return;
      }
      try { bodyText = raw.toString("utf8"); JSON.parse(bodyText); }
      catch {
        metrics.rejected += 1;
        respond(response, 400, { format: "kotoba.http-service-error/v1", error: "body-not-json" });
        return;
      }
    }

    active += 1;
    try {
      let result;
      try {
        if (route.kind === "app") {
          const app = route.app;
          // The read-modify-write below is synchronous with no `await`
          // between reading the cell and assigning it, so two concurrent
          // requests cannot interleave inside it. The body `await` already
          // happened above.
          if (route.event) {
            const next = freshInstance(app.mod)[app.step](app.state, bodyText);
            const reason = admissibleState(next, app);
            if (reason !== null) {
              metrics.rejected += 1;
              respond(response, 500, { format: "kotoba.http-service-error/v1", error: reason });
              return;
            }
            app.state = next;
          }
          result = freshInstance(app.mod)[app.view](app.state);
        } else {
          const instance = freshInstance(route.mod);
          result = route.hasBody ? instance[route.export](bodyText) : instance[route.export]();
        }
      } catch (error) {
        metrics.traps += 1;
        metrics.rejected += 1;
        respond(response, 500, { format: "kotoba.http-service-error/v1", error: "guest-trap" });
        return;
      }
      if (typeof result !== "string") {
        metrics.rejected += 1;
        respond(response, 500, { format: "kotoba.http-service-error/v1", error: "guest-response-invalid" });
        return;
      }
      const writtenBytes = Buffer.byteLength(result, "utf8");
      if (writtenBytes > 0) {
        try { JSON.parse(result); }
        catch {
          metrics.rejected += 1;
          respond(response, 500, { format: "kotoba.http-service-error/v1", error: "guest-response-invalid" });
          return;
        }
      }
      const answered = decideInstance["answer?"](BigInt(writtenBytes));
      const outcome = decideInstance["outcome"](":route", true, answered);
      const status = Number(decideInstance["status-for"](outcome));
      metrics.success += 1;
      if (!answered) { response.writeHead(status); response.end(); return; }
      response.writeHead(status, {
        "content-type": "application/json; charset=utf-8",
        "content-length": writtenBytes,
        "cache-control": "no-store",
        "x-content-type-options": "nosniff"
      });
      response.end(result);
    } finally {
      active -= 1;
    }
  });

  server.requestTimeout = 3000;
  server.headersTimeout = 3000;
  server.keepAliveTimeout = 1000;

  return {
    server,
    metrics,
    routeCount: routeTable.size,
    appCount: apps.length,
    listen(port = 0) {
      return new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(port, "127.0.0.1", () => resolve(server.address()));
      });
    },
    close() {
      return new Promise(resolve => server.close(() => resolve()));
    }
  };
}

export { ConfigError };

// Standalone-process entry: `node http-service.mjs` reads
// KOTOBA_HTTP_CONFIG_PATH (a JSON file matching the `config` shape above)
// and KOTOBA_HTTP_PORT, mirroring wasi-service.mjs's env-var-driven start.
if (import.meta.url === `file://${process.argv[1]}`) {
  const configPath = process.env.KOTOBA_HTTP_CONFIG_PATH;
  if (!configPath) throw new Error("KOTOBA_HTTP_CONFIG_PATH is required");
  const port = Number(process.env.KOTOBA_HTTP_PORT ?? "8080");
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const service = await createHttpService(config);
  const address = await service.listen(port);
  process.stderr.write(`kotoba-http-service listening on ${JSON.stringify(address)} with ${service.routeCount} route(s)\n`);
  const shutdown = () => service.close().then(() => process.exit(0));
  process.once("SIGTERM", shutdown);
  process.once("SIGINT", shutdown);
}
