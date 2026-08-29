// End-to-end test for the first `kotoba/app` vertical slice served by
// runtime/http-service.mjs: a real Node http.Server, real HTTP requests over
// a real socket (global fetch), against a real compiled :js-kotoba-v1 guest
// that holds product semantics and reads its own request body.
//
// What this file is trying to distinguish, stated up front so a green run
// means something:
//
//   * that STATE actually survives across separate HTTP requests -- not that
//     one request produced a plausible-looking answer;
//   * that the BODY is actually parsed INSIDE the guest -- asserted by making
//     the answer depend on values that only appear in the body, and by
//     sending bodies that differ only in a field the guest must read;
//   * that the product RULES are the ones cloud-itonami-app states -- veto
//     beats a satisfied minimum, a decision bound to different content does
//     not count, one actor counts once;
//   * that the host is holding mechanism only -- an app route and a pure
//     route coexist, and the host's own built-ins are unaffected.
//
// The guest is compiled fresh by scripts/approval-queue-e2e.cljs and handed
// in via env, so this proves the real compile -> host -> serve pipeline on
// every run rather than trusting a stale artifact.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createHttpService, ConfigError } from "../../runtime/http-service.mjs";

const here = path.dirname(new URL(import.meta.url).pathname);
const sha256 = p => createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const need = name => {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required (set by scripts/approval-queue-e2e.cljs)`);
  return value;
};

const decidePath = path.resolve(here, "..", "..", "runtime", "http", "route-decide.mjs");
const appPath = need("KOTOBA_HTTP_TEST_APPROVAL_APP");
const decideSha = sha256(decidePath);
const appSha = sha256(appPath);

// The body bound this app was compiled to afford. Kept in one place because
// it is a property of the artifact's fuel, not a free choice per test.
const MAX_BODY = 1024;

let failures = 0;
const check = (label, cond) => {
  if (cond) { console.log(`ok - ${label}`); }
  else { failures += 1; console.error(`NOT OK - ${label}`); }
};

function appConfig() {
  return {
    decide: { module: decidePath, sha256: decideSha },
    // A pure `routes` guest is NOT required for an app to work; this config
    // deliberately carries only the app, so nothing else can be answering.
    routes: [],
    apps: [{
      name: "approval",
      module: appPath,
      sha256: appSha,
      maxStateBytes: 1024,
      routes: [
        { method: "POST", path: "/approvals", event: true, maxBodyBytes: MAX_BODY },
        { method: "GET", path: "/approvals", event: false }
      ]
    }]
  };
}

async function start() {
  const service = await createHttpService(appConfig());
  const address = await service.listen(0);
  return { service, base: `http://127.0.0.1:${address.port}` };
}

const decide = (base, body) => fetch(`${base}/approvals`, {
  method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body)
});
const read = async base => (await fetch(`${base}/approvals`)).json();

// A well-formed eligible decision, so each test varies exactly one thing.
const good = extra => ({
  actor: "alice", decision: "approved", item: "work-1", hash: "sha256-a1",
  person: "true", role: "true", ...extra
});

// ---- 1. the app answers at all, from init() -----------------------------
{
  const { service, base } = await start();
  check("service reports one app mounted", service.appCount === 1);
  const initial = await read(base);
  check("GET /approvals -> the guest's init() state, viewed",
        initial.item === "work-1" && initial.status === "pending");
  check("init() carries the policy: two approvals required",
        initial.required === "2");
  check("init() starts with nothing recorded",
        initial.approved_count === "0" && initial.rejected_count === "0"
        && initial.ignored === "0" && initial.approved_by === "");
  await service.close();
}

// ---- 2. STATE SURVIVES ACROSS REQUESTS ----------------------------------
// The whole point of the slice. Three separate HTTP requests, three separate
// guest instances, one accumulating state.
{
  const { service, base } = await start();

  const first = await decide(base, good({ actor: "alice" }));
  check("POST /approvals -> 200", first.status === 200);
  check("the POST's own answer already reflects the decision",
        (await first.json()).approved_by === "alice");

  const afterFirst = await read(base);
  check("a LATER, SEPARATE request still sees alice",
        afterFirst.approved_by === "alice" && afterFirst.approved_count === "1");
  check("one approval does not meet a minimum of two",
        afterFirst.status === "pending");

  await decide(base, good({ actor: "bob" }));
  const afterSecond = await read(base);
  check("state accumulated across requests: both actors present",
        afterSecond.approved_by === "alice,bob" && afterSecond.approved_count === "2");
  check("the minimum is now met -> approved", afterSecond.status === "approved");
  await service.close();
}

// ---- 3. a FRESH process starts from init() again -------------------------
// State is in memory and per-process, exactly as the host header says.
{
  const { service, base } = await start();
  const fresh = await read(base);
  check("a new service does not inherit the previous one's state",
        fresh.approved_by === "" && fresh.status === "pending");
  await service.close();
}

// ---- 4. the BODY is really parsed inside the guest -----------------------
// Two requests differing only in a single body field produce different
// answers, and a field the guest reads by NAME is picked out of a body that
// also contains a nested object and a decoy substring.
{
  const { service, base } = await start();

  await decide(base, good({ actor: "zoe" }));
  const named = await read(base);
  check("the actor name in the answer came from the body, verbatim",
        named.approved_by === "zoe");

  // A nested object and an array precede the wanted key, and one of them
  // contains text that would desynchronise a naive scan.
  const nested = {
    meta: { note: 'has "quotes", a comma, and {braces}', tags: ["actor", "decision"] },
    actor: "quinn", decision: "approved", item: "work-1", hash: "sha256-a1",
    person: "true", role: "true"
  };
  const r = await fetch(`${base}/approvals`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(nested)
  });
  check("a body with a nested object/array before the key -> 200", r.status === 200);
  check("the guest skipped the nested members structurally and read the real actor",
        (await r.json()).approved_by === "zoe,quinn");
  await service.close();
}

// ---- 5. one actor counts once (dedupe by actor) --------------------------
// work_governance.cljc folds approvals into a map keyed by actor; this is
// that fold, in the guest.
{
  const { service, base } = await start();
  await decide(base, good({ actor: "alice" }));
  await decide(base, good({ actor: "alice" }));
  await decide(base, good({ actor: "alice" }));
  const s = await read(base);
  check("three approvals from one actor count once",
        s.approved_count === "1" && s.approved_by === "alice");
  check("the repeats are not counted as ignored either (they were eligible)",
        s.ignored === "0");
  check("one actor cannot satisfy a minimum of two on their own",
        s.status === "pending");
  await service.close();
}

// ---- 6. a decision bound to DIFFERENT CONTENT does not count -------------
// approval_core.kotoba: "Approving revision A must not approve revision B."
{
  const { service, base } = await start();
  const r = await decide(base, good({ actor: "alice", hash: "sha256-DIFFERENT" }));
  check("a decision on another revision -> 200 (refused, not an error)", r.status === 200);
  const s = await read(base);
  check("it did not become an approval", s.approved_count === "0" && s.approved_by === "");
  check("it was IGNORED, i.e. counted rather than silently dropped", s.ignored === "1");

  await decide(base, good({ actor: "alice", item: "work-OTHER" }));
  const s2 = await read(base);
  check("a decision on another work item is ignored too", s2.ignored === "2");
  await service.close();
}

// ---- 7. separation of duties: the submitter may not approve their own ----
{
  const { service, base } = await start();
  await decide(base, good({ actor: "carol" }));           // carol is the submitter
  const s = await read(base);
  check("the submitter's own approval is refused", s.approved_by === "" && s.ignored === "1");

  await decide(base, good({ actor: "alice", person: "false" }));
  check("a non-person actor is refused", (await read(base)).ignored === "2");

  await decide(base, good({ actor: "alice", role: "false" }));
  check("an actor without an eligible role is refused", (await read(base)).ignored === "3");
  await service.close();
}

// ---- 8. VETO BEATS A SATISFIED MINIMUM ----------------------------------
// approval_core.kotoba: "reversing these two branches is the failure this
// ordering exists to prevent."  This is the assertion the deliberate break
// in scripts/approval-queue-e2e.cljs --mutant-* flips.
{
  const { service, base } = await start();
  await decide(base, good({ actor: "alice" }));
  await decide(base, good({ actor: "bob" }));
  check("minimum met -> approved", (await read(base)).status === "approved");

  await decide(base, good({ actor: "dave", decision: "rejected" }));
  const s = await read(base);
  check("the approvals are still there", s.approved_count === "2");
  check("VETO OUTRANKS THE SATISFIED MINIMUM -> rejected", s.status === "rejected");
  check("and the rejecter is named", s.rejected_by === "dave");
  await service.close();
}

// ---- 9. an actor name the guest cannot render is refused, not served -----
// The guest's answer must stay valid JSON; a name carrying a quote is
// ignored rather than producing a body the host would reject.
{
  const { service, base } = await start();
  const r = await decide(base, good({ actor: 'ev"il' }));
  check("a decision from a non-simple actor -> 200", r.status === 200);
  const s = await r.json();
  check("it was ignored", s.ignored === "1" && s.approved_by === "");
  const raw = await (await fetch(`${base}/approvals`)).text();
  check("the served body is still valid JSON", (() => { try { JSON.parse(raw); return true; } catch { return false; } })());

  await decide(base, good({ actor: "a,b" }));
  check("a name containing the list separator is refused too",
        (await read(base)).ignored === "2");
  await service.close();
}

// ---- 10. the guest enforces its own state ceiling -----------------------
// A decision that would push the rendered state past the guest's own
// state-limit is ignored rather than growing the host's cell without bound.
{
  const { service, base } = await start();
  // 20 distinct 69-byte actor names against a 1024-byte state ceiling: the
  // list alone would reach ~1400 bytes, so the guest must start refusing
  // partway through. Sized to CROSS the bound -- an earlier version used 12
  // and landed at ~990 bytes, where nothing was refused and the "every
  // refusal was counted" assertion below passed on 0 === 0 while measuring
  // nothing at all.
  let admitted = 0;
  let refused = 0;
  for (let i = 0; i < 20; i += 1) {
    const actor = `actor-${String(i).padStart(2, "0")}-${"n".repeat(60)}`;
    const before = await read(base);
    await decide(base, good({ actor }));
    const after = await read(base);
    if (after.approved_count !== before.approved_count) admitted += 1; else refused += 1;
  }
  check("some long-named actors were admitted", admitted > 0);
  check("and the guest refused the rest rather than growing without bound", refused > 0);
  const s = await read(base);
  check("every refusal was counted as ignored", refused > 0 && Number(s.ignored) === refused);
  check("the accumulated list stayed inside the guest's own ceiling",
        Buffer.byteLength(s.approved_by, "utf8") < 1024);
  await service.close();
}

// ---- 11. GET does not mutate; host built-ins unaffected -----------------
{
  const { service, base } = await start();
  await decide(base, good({ actor: "alice" }));
  const a = await read(base);
  const b = await read(base);
  const c = await read(base);
  check("repeated GETs are stable (a read is not an event)",
        JSON.stringify(a) === JSON.stringify(b) && JSON.stringify(b) === JSON.stringify(c));

  const healthz = await fetch(`${base}/healthz`);
  check("GET /healthz -> 200 (host built-in, unaffected by the app)", healthz.status === 200);

  const missing = await fetch(`${base}/nope`);
  check("GET /nope -> 404 via the compiled decision core", missing.status === 404);

  const wrongMethod = await fetch(`${base}/approvals`, { method: "DELETE" });
  check("DELETE /approvals -> 404 (method not registered)", wrongMethod.status === 404);
  await service.close();
}

// ---- 12. the host's bounds on an app route ------------------------------
{
  const { service, base } = await start();

  const noType = await fetch(`${base}/approvals`, { method: "POST", body: "{}" });
  check("POST without content-type -> 400", noType.status === 400);

  const badJson = await fetch(`${base}/approvals`, {
    method: "POST", headers: { "content-type": "application/json" }, body: "{not json"
  });
  check("POST with malformed JSON -> 400", badJson.status === 400);

  const oversized = await fetch(`${base}/approvals`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ x: "a".repeat(MAX_BODY + 500) })
  });
  check("POST over this app's declared body bound -> 413", oversized.status === 413);

  const stillFine = await read(base);
  check("none of those rejections disturbed the state", stillFine.ignored === "0");
  await service.close();
}

// ---- 13. config floors: the host refuses rather than guessing ------------
{
  const reject = async (label, mutate) => {
    const config = appConfig();
    mutate(config);
    try { await createHttpService(config); check(label, false); }
    catch (error) { check(label, error instanceof ConfigError); }
  };
  await reject("an app module with a wrong sha256 is refused at startup",
               c => { c.apps[0].sha256 = "0".repeat(64); });
  await reject("an app naming an export the module lacks is refused at startup",
               c => { c.apps[0].step = "nosuchexport"; });
  await reject("an app whose maxStateBytes is out of range is refused",
               c => { c.apps[0].maxStateBytes = 0; });
  await reject("an app route colliding with a pure route is refused",
               c => {
                 c.routes = [{ method: "GET", path: "/approvals", module: appPath,
                               sha256: appSha, export: "view", hasBody: false }];
               });
}

console.log(failures === 0 ? "approval_queue_test: PASS" : `approval_queue_test: FAIL (${failures})`);
process.exit(failures === 0 ? 0 : 1);
