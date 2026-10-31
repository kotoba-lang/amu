#!/usr/bin/env python3
"""Run wasm32-browser-static/v1 modules in headless Chromium and check them (JUN-353).

The modules are what `F compile SRC --target wasm32-browser` produced (seed/81,
seed/82). Python only orchestrates: it copies the static page and Worker host
(runtime/wasm32-browser-static-run.html, runtime/wasm32-browser-static-host.js)
next to a generated runs.js holding the modules, starts the browser with the
DevTools protocol on a pipe (--remote-debugging-pipe: no port, no network),
opens the page, waits for its title to become "kotoba-done" and reads the
result lines from the DOM. No Node, npm or Playwright.

Standalone: check-wasm32-browser.py --modules DIR --output OUT [--browser PATH]
checks DIR/case-NAME.wasm against seed/static-cases.json (result, trap and
remaining fuel, as the native cases are checked) and DIR/probe-spin.wasm,
DIR/probe-deep.wasm and DIR/probe-entry.wasm when present (see PROBES).
When DIR/probe-cap.wasm is present it also runs the consent broker's
qualification (Phase 2, profile restricted-wasm-v1; see BROKER_RUNS): the
trusted page runtime/wasm32-browser-broker-run.html holds the vendored
kotoba-client-runtime.js, and the guests run in its restricted guest shell.

run_modules is also the harness of applications' own browser checks (for
example kumitate's fixture selftest): each run may carry the entry ABI's
inputs (allow, args, files; runtime/wasm32-browser-static-host.js).

An application's module: check-wasm32-browser.py --app MODULE.wasm --output OUT
[--allow 35,37,38,39] [--file MOUNT=DIR].. [-- ARGS..] runs it once with those
inputs (every file under DIR is readable at MOUNT/<its relative path>; nothing
is writable), writes OUT/app.json and the run's output (stdout without the
report line) to OUT/output, prints the report line and exits 0 when the run
ended with :status :ok and exit 0.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "runtime/wasm32-browser-static-run.html"
HOST = ROOT / "runtime/wasm32-browser-static-host.js"
CASES = ROOT / "seed/static-cases.json"
FUEL = 1000000
BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")


def find_browser(explicit=None):
    for name in ([explicit] if explicit else []) + [os.environ.get("KOTOBA_BROWSER")] + list(BROWSERS):
        if name and shutil.which(name):
            return shutil.which(name)
    return None


class Pipe:
    """The DevTools protocol over --remote-debugging-pipe (fd 3 in, fd 4 out, NUL-separated JSON)."""

    def __init__(self, browser, profile):
        to_r, self.to_w = os.pipe()
        self.from_r, from_w = os.pipe()

        def fds():
            # dup first: dup2 onto the same number would keep close-on-exec
            a, b = os.dup(to_r), os.dup(from_w)
            os.dup2(a, 3)
            os.dup2(b, 4)
        args = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking", "--disable-sync",
                "--remote-debugging-pipe", f"--user-data-dir={profile}", "about:blank"]
        if os.geteuid() == 0 or os.environ.get("KOTOBA_BROWSER_NO_SANDBOX") == "1":
            args.insert(1, "--no-sandbox")
        # os.pipe() fds are not inheritable; dup2 makes 3 and 4 inheritable in the child only
        self.log = open(Path(profile) / "browser.log", "w+b")
        self.proc = subprocess.Popen(args, preexec_fn=fds, close_fds=False,
                                     stdout=subprocess.DEVNULL, stderr=self.log)
        os.close(to_r)
        os.close(from_w)
        self.buf, self.next_id = b"", 0
        self.events = []  # protocol events (messages without an id), in arrival order

    def call(self, method, params=None, session=None, timeout=60):
        self.next_id += 1
        msg = dict(id=self.next_id, method=method, params=params or {})
        if session:
            msg["sessionId"] = session
        os.write(self.to_w, json.dumps(msg).encode() + b"\0")
        end = time.time() + timeout
        while time.time() < end:
            while b"\0" in self.buf:
                raw, self.buf = self.buf.split(b"\0", 1)
                reply = json.loads(raw)
                if "id" not in reply:
                    self.events.append(reply)
                    continue
                if reply.get("id") == self.next_id:
                    if "error" in reply:
                        raise RuntimeError((method, reply["error"]))
                    return reply["result"]
            if not select.select([self.from_r], [], [], max(0.0, end - time.time()))[0]:
                break
            chunk = os.read(self.from_r, 1 << 16)
            if not chunk:
                raise RuntimeError(("browser closed the pipe", self.stderr_tail()))
            self.buf += chunk
        raise TimeoutError((method, self.stderr_tail()))

    def send(self, method, params=None, session=None):
        """A command whose reply is not waited for (it is dropped when it arrives)."""
        self.next_id += 1
        msg = dict(id=self.next_id, method=method, params=params or {})
        if session:
            msg["sessionId"] = session
        os.write(self.to_w, json.dumps(msg).encode() + b"\0")

    def stderr_tail(self):
        self.log.flush()
        self.log.seek(0)
        return self.log.read().decode(errors="replace")[-3000:]

    def close(self):
        try:
            self.call("Browser.close", timeout=10)
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        os.close(self.to_w)
        os.close(self.from_r)


def run_modules(browser, out, runs, timeout=300):
    """runs: [(name, wasm path)] or [(name, wasm path, {fuel?, allow?, args?, files?})].
    Returns (browser version, {name: result line})."""
    page_dir = out / "page"
    page_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(PAGE, page_dir / PAGE.name)
    shutil.copy(HOST, page_dir / HOST.name)
    data = [dict(dict(name=r[0], fuel=FUEL, wasm=base64.b64encode(Path(r[1]).read_bytes()).decode()), **(r[2] if len(r) > 2 else {}))
            for r in runs]
    (page_dir / "runs.js").write_text("window.KOTOBA_RUNS = " + json.dumps(data) + ";\n")
    with tempfile.TemporaryDirectory(prefix="kotoba-browser-") as profile:
        pipe = Pipe(browser, profile)
        try:
            version = pipe.call("Browser.getVersion")
            target = pipe.call("Target.createTarget", dict(url=(page_dir / PAGE.name).as_uri()))["targetId"]
            session = pipe.call("Target.attachToTarget", dict(targetId=target, flatten=True))["sessionId"]
            end, text = time.time() + timeout, None
            while time.time() < end:
                r = pipe.call("Runtime.evaluate", dict(
                    expression="document.title === 'kotoba-done' ? document.getElementById('results').textContent : null",
                    returnByValue=True), session)
                text = r.get("result", {}).get("value")
                if text is not None:
                    break
                time.sleep(0.2)
            if text is None:
                raise TimeoutError("the page did not finish")
        finally:
            pipe.close()
    lines = [json.loads(l) for l in text.splitlines() if l.strip()]
    return dict(product=version.get("product"), protocol=version.get("protocolVersion")), {l["name"]: l for l in lines}


def observe(line):
    """The native report's fields from a result line (exit, status, result, remaining fuel)."""
    stdout = line.get("stdout") or ""
    fuel = re.search(r":remaining ([0-9]+)", stdout)
    status = re.search(r":status :([a-z]+)", stdout)
    result = re.search(r":result (-?[0-9]+)", stdout)
    return dict(exit=line.get("exit"), status=status and status[1], result=int(result[1]) if result else None,
                remainingFuel=int(fuel[1]) if fuel else None)


# Probes (optional, when DIR/probe-NAME.wasm exists): fuel exhaustion traps with
# the native report and no fuel left; unbounded recursion exhausts the wasm
# stack, which the host ends as a native signal would (exit 120, no report).
# The entry ABI (probe-entry: read argument 0, read that file, write it, return
# its length) runs twice: with the page's grants it echoes the file; without
# them :cli/args is refused by name, as natively without KEXE_ALLOW.
ENTRY_TEXT = "kotoba \u8a00\u8449 entry\n"
PROBES = {"spin": dict(exit=120, status="trap", remainingFuel=0),
          "deep": dict(exit=120, status=None, remainingFuel=None),
          "entry": dict(exit=0, status="ok", result=len(ENTRY_TEXT.encode())),
          "entry-denied": dict(exit=120, status="trap")}
PROBE_RUNS = {"entry": [("entry", dict(allow=[35, 37, 38, 39], args=["/data/../data/in.txt"], files={"/data/in.txt": ENTRY_TEXT})),
                        ("entry-denied", dict(args=["/data/in.txt"], files={"/data/in.txt": ENTRY_TEXT}))]}


def check_cases(browser, out, modules, cases=None):
    """Run case-NAME.wasm (and probe-NAME.wasm) from `modules`; compare with seed/static-cases.json."""
    cases = cases or json.loads(CASES.read_text())["cases"]
    probe_runs = [(name, m, extra) for m in PROBES if (modules / f"probe-{m}.wasm").exists()
                  for name, extra in PROBE_RUNS.get(m, [(m, {})])]
    probes = [name for name, m, extra in probe_runs]
    t0 = time.time()
    version, lines = run_modules(browser, out, [(c["name"], modules / f"case-{c['name']}.wasm") for c in cases]
                                 + [(f"probe-{n}", modules / f"probe-{m}.wasm", e) for n, m, e in probe_runs])
    seconds = round(time.time() - t0, 3)
    results = []
    for c in cases:
        line = lines.get(c["name"])
        assert line is not None, ("no result", c["name"])
        o = observe(line)
        expected_status = "trap" if c["trap"] else "ok"
        ok = (o["exit"] == c["reference"]["exit"] and o["remainingFuel"] == c["reference"]["remainingFuel"]
              and o["status"] == expected_status and (c["trap"] or o["result"] == c["result"]))
        assert ok, (c["name"], o, c["result"], c["reference"], line)
        results.append(dict(name=c["name"], **o))
    probe_results = []
    for p in probes:
        line = lines[f"probe-{p}"]
        o = observe(line)
        assert all(o[k] == v for k, v in PROBES[p].items()), (p, o, line)
        assert p != "deep" or line.get("wasmTrap"), (p, line)
        assert p != "entry" or line.get("output") == ENTRY_TEXT, (p, line)
        assert p != "entry-denied" or ":wire 38 :refused" in (line.get("stderr") or ""), (p, line)
        probe_results.append(dict(name=p, wasmTrap=line.get("wasmTrap"), **o))
    return dict(browser=version, seconds=seconds, fuel=FUEL, cases=results, probes=probe_results)


# ---- the consent broker (Phase 2, profile restricted-wasm-v1) ----
# A guest's kotoba:host/cap call of a wire the trusted host page has bound to a
# declared operation goes to the shared broker (runtime/kotoba-client-runtime.js,
# vendored byte-for-byte; runtime/kotoba-client-runtime.pin.json). The page is
# served from 127.0.0.1 (module scripts do not load from file://), and the
# guest runs in the restricted guest shell (a sandboxed iframe, connect-src
# 'none') and its Worker. Every https request of the page and of its attached
# frames and workers is held at the request stage (DevTools Fetch domain) and
# recorded; the declared fixture endpoint is answered by this harness, so no
# request ever leaves the machine, and anything else is failed. Each consent
# dialog first gets a synthetic Allow click (isTrusted false), which must not
# approve or send; then the run's plan: "deny" (a click on Deny) or "allow" (a
# press and release dispatched through DevTools Input, which the browser marks
# isTrusted; automation, not a person's click).
BROKER_PAGE = ROOT / "runtime/wasm32-browser-broker-run.html"
BROKER_JS = ROOT / "runtime/wasm32-browser-broker-run.js"
BROKER_RUNTIME = ROOT / "runtime/kotoba-client-runtime.js"
BROKER_PIN = ROOT / "runtime/kotoba-client-runtime.pin.json"
GUEST_SHELL = ROOT / "runtime/wasm32-browser-restricted-guest.html"
SERVICE = "https://service.invalid"
FIXTURE_BODY = '{"id":"abc","fixture":true}\n'
CAP_WIRE = 45  # the probes' wire (:net/dial): any catalogued wire the runtime does not serve itself can be bound
READ_OP = {"capability": "test/fixture-read", "service": "fixture-service", "operation": "read", "consent": "each-operation",
           "data-categories": ["fixture-item-id"], "endpoint": {"origin": SERVICE, "method": "GET", "path": "/v1/items/:id"}}


def selector(op):
    return {k: op[k] for k in ("capability", "service", "operation")}


def descriptor(ops):
    return {"schema": "kotoba.app.client-runtime.v1", "target": "browser", "profile": "restricted-wasm-v1",
            "entry": "index.html", "local-state": {"adapter": "indexeddb", "schema": "kotoba.wasm32-browser.fixture.v1", "version": 1},
            "operations": ops}


OTHER_PATH_OP = dict(READ_OP, endpoint=dict(READ_OP["endpoint"], path="/v1/other/:id"))
# name: (probe module, operations declared, bound selector or None, consent plan, expected)
BROKER_RUNS = {
    "cap-unbound": ("cap", [READ_OP], None, [], dict(exit=120, dialogs=0, requests=0, cap=[])),
    "cap-undeclared-operation": ("cap", [READ_OP], dict(selector(READ_OP), operation="write"), [],
                                 dict(exit=120, dialogs=0, requests=0, cap=["client operation is not eligible and supported"])),
    "cap-undeclared-endpoint": ("cap", [OTHER_PATH_OP], selector(READ_OP), [],
                                dict(exit=120, dialogs=0, requests=0, cap=["request does not match declared service method/path/query"])),
    "cap-denied": ("cap", [READ_OP], selector(READ_OP), ["deny"],
                   dict(exit=120, dialogs=1, requests=0, cap=["client operation was not approved"])),
    "cap-approved": ("cap", [READ_OP], selector(READ_OP), ["allow"],
                     dict(exit=0, dialogs=1, requests=1, cap=["answered"])),
    "cap-approval-once": ("cap-twice", [READ_OP], selector(READ_OP), ["allow", "deny"],
                          dict(exit=120, dialogs=2, requests=1, cap=["answered", "client operation was not approved"])),
}


def pin_matches(data, pin_):
    sri = "sha256-" + base64.b64encode(hashlib.sha256(data).digest()).decode()
    return len(data) == pin_["bytes"] and hashlib.sha256(data).hexdigest() == pin_["sha256"] and sri == pin_["sri"]


def check_broker_pin():
    pin_ = json.loads(BROKER_PIN.read_text())
    data = BROKER_RUNTIME.read_bytes()
    assert pin_matches(data, pin_), ("runtime/kotoba-client-runtime.js is not the pinned reviewed revision", pin_["source"])
    # negative control: one changed byte is not the pin
    assert not pin_matches(bytes([data[0] ^ 1]) + data[1:], pin_)
    assert f'"./kotoba-client-runtime.js": "{pin_["sri"]}"' in BROKER_PAGE.read_text(), "the broker page's import map integrity is not the pin"
    return pin_


def guest_shell(module, bind, revision):
    run = dict(wasm=base64.b64encode(Path(module).read_bytes()).decode(), fuel=FUEL, allow=[37], bind=bind)
    js = lambda v: json.dumps(v).replace("<", "\\u003c")
    html = GUEST_SHELL.read_text()
    assert html.count("/*KOTOBA_RUN*/null") == 1 and html.count("/*KOTOBA_HOST*/null") == 1
    html = html.replace("/*KOTOBA_RUN*/null", js(run)).replace("/*KOTOBA_HOST*/null", js(HOST.read_text()))
    data = html.encode()
    return dict(guest=base64.b64encode(data).decode(), sha256=hashlib.sha256(data).hexdigest(), revision=revision)


def source_revision():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    rev = r.stdout.strip()
    assert r.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", rev), "the guest shell's revision is this checkout's commit"
    return rev


class _Quiet(__import__("http.server").server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def check_broker(browser, out, modules, timeout=300):
    """Run BROKER_RUNS with probe-cap.wasm and probe-cap-twice.wasm from `modules`; returns the report."""
    import functools
    import http.server
    import threading
    pin_ = check_broker_pin()
    page_dir = out / "broker-page"
    page_dir.mkdir(parents=True, exist_ok=True)
    for f in (BROKER_PAGE, BROKER_JS, BROKER_RUNTIME):
        shutil.copy(f, page_dir / f.name)
    revision = source_revision()
    runs = []
    for name, (probe, ops, bound, plan, expected) in BROKER_RUNS.items():
        bind = {str(CAP_WIRE): bound} if bound else {}
        runs.append(dict(name=name, runtime=descriptor(ops), requestedCapabilities=sorted({o["capability"] for o in ops}),
                         hostSupportedOperations=[[o["capability"], o["service"], o["operation"]] for o in ops],
                         **guest_shell(modules / f"probe-{probe}.wasm", bind, revision)))
    (page_dir / "broker-runs.js").write_text("window.KOTOBA_BROKER_RUNS = " + json.dumps(runs) + ";\n")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(page_dir)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/{BROKER_PAGE.name}"
    requests, network, consents, sessions = [], [], [], set()
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="kotoba-broker-") as profile:
        pipe = Pipe(browser, profile)
        try:
            version = pipe.call("Browser.getVersion")
            target = pipe.call("Target.createTarget", dict(url="about:blank"))["targetId"]
            session = pipe.call("Target.attachToTarget", dict(targetId=target, flatten=True))["sessionId"]

            # The host page must take all three. An attached frame or worker is asked without waiting: it
            # takes what its target type has (a worker has no Fetch domain) and may already be gone. Their
            # own network barrier is the guest shell's connect-src 'none'; what is recorded for them is
            # observation, not the barrier.
            def instrument(s, kind="page"):
                sessions.add(s)
                for method, params in (("Network.enable", {}),
                                       ("Fetch.enable", dict(patterns=[dict(urlPattern="https://*", requestStage="Request")])),
                                       ("Target.setAutoAttach", dict(autoAttach=True, waitForDebuggerOnStart=False, flatten=True))):
                    (pipe.call if s == session else pipe.send)(method, params, s)
                attached.append(dict(run=state["run"], type=kind))
            state = dict(run=None)
            attached = []
            instrument(session)

            def pump():
                while pipe.events:
                    ev = pipe.events.pop(0)
                    m, p, s = ev.get("method"), ev.get("params", {}), ev.get("sessionId")
                    if m == "Target.attachedToTarget" and p.get("sessionId") not in sessions:
                        instrument(p["sessionId"], p.get("targetInfo", {}).get("type"))
                    elif m == "Network.requestWillBeSent":
                        network.append(dict(run=state["run"], url=p["request"]["url"], type=p.get("type")))
                    elif m == "Fetch.requestPaused":
                        rq = p["request"]
                        rec = dict(run=state["run"], url=rq["url"], method=rq["method"],
                                   headers=sorted(k.lower() for k in rq.get("headers", {})),
                                   fromHostPage=s == session)
                        requests.append(rec)
                        plan = BROKER_RUNS.get(state["run"], (None, None, None, []))[3]
                        if rec["fromHostPage"] and rq["url"] == SERVICE + "/v1/items/abc" and rq["method"] == "GET" and "allow" in plan:
                            pipe.send("Fetch.fulfillRequest", dict(
                                requestId=p["requestId"], responseCode=200, body=base64.b64encode(FIXTURE_BODY.encode()).decode(),
                                responseHeaders=[dict(name="Content-Type", value="text/plain; charset=utf-8"),
                                                 dict(name="Access-Control-Allow-Origin", value="*")]), s)
                        else:
                            pipe.send("Fetch.failRequest", dict(requestId=p["requestId"], errorReason="BlockedByClient"), s)

            def evaluate(expr):
                r = pipe.call("Runtime.evaluate", dict(expression=expr, returnByValue=True), session)
                pump()
                return r.get("result", {}).get("value")
            pipe.call("Page.navigate", dict(url=url), session)
            handled, end, text = 0, time.time() + timeout, None
            while time.time() < end:
                st = evaluate("window.kotobaBrokerState ? window.kotobaBrokerState() : null")
                if st:
                    state["run"] = st["run"]
                    if st["done"]:
                        text = evaluate("document.getElementById('results').textContent")
                        break
                    if st["open"] and st["dialogs"] > handled:
                        handled = st["dialogs"]
                        run, k = st["run"], len([c for c in consents if c["run"] == st["run"]])
                        plan = BROKER_RUNS[run][3]
                        action = plan[k] if k < len(plan) else "deny"
                        while evaluate("window.kotobaBrokerState().allowDisabled") and time.time() < end:
                            time.sleep(0.05)
                        sent = len(requests)
                        evaluate("document.querySelector('dialog.kotoba-client-consent button:last-child').click()")
                        time.sleep(0.4)
                        after = evaluate("window.kotobaBrokerState()")
                        synthetic = dict(stillOpen=after["open"], requestsSent=len(requests) - sent)
                        if action == "allow":
                            box = evaluate("(() => { const r = document.querySelector('dialog.kotoba-client-consent button:last-child')"
                                           ".getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()")
                            for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                                pipe.call("Input.dispatchMouseEvent", dict(type=kind, x=box[0], y=box[1], button="left",
                                                                           buttons=1 if kind == "mousePressed" else 0,
                                                                           clickCount=0 if kind == "mouseMoved" else 1), session)
                        else:
                            evaluate("document.querySelector('dialog.kotoba-client-consent button').click()")
                        consents.append(dict(run=run, action=action, scope=st["scope"], syntheticAllowClick=synthetic))
                time.sleep(0.1)
            if text is None:
                raise TimeoutError(("the broker page did not finish", pipe.stderr_tail()))
        finally:
            pipe.close()
            server.shutdown()
    lines = {l["name"]: l for l in (json.loads(x) for x in text.splitlines() if x.strip())}
    report = []
    for name, (probe, ops, bound, plan, exp) in BROKER_RUNS.items():
        line = lines.get(name)
        assert line is not None and "hostError" not in line, ("broker run", name, line)
        o = observe(line)
        sent = [r for r in requests if r["run"] == name]
        cap = [c["outcome"] if c["outcome"] == "answered" else c.get("error") for c in line.get("capLog") or []]
        shown = [c for c in consents if c["run"] == name]
        answer = "200\n" + FIXTURE_BODY
        ok = (o["exit"] == exp["exit"] and line.get("dialogs") == exp["dialogs"] == len(shown)
              and len(sent) == exp["requests"] and cap == exp["cap"]
              and all(c["syntheticAllowClick"] == dict(stillOpen=True, requestsSent=0) for c in shown)
              and all(f"Endpoint: {SERVICE}" in c["scope"] and "Action: GET /v1/items/abc" in c["scope"] for c in shown)
              and all(r["fromHostPage"] and r["url"] == SERVICE + "/v1/items/abc" and r["method"] == "GET"
                      and not {"cookie", "authorization"} & set(r["headers"]) for r in sent))
        if exp["exit"] == 0:
            ok = ok and o["status"] == "ok" and o["result"] == len(answer.encode()) and line.get("output") == answer
        elif exp["dialogs"] < 2:
            ok = ok and o["status"] == "trap" and f":wire {CAP_WIRE} :refused" in (line.get("stderr") or "")
        else:
            ok = ok and o["status"] == "trap" and (line.get("output") or "").startswith(answer)
        assert ok, (name, o, exp, cap, sent, shown, line)
        report.append(dict(name=name, probe=probe, bound=bound, plan=plan, consentDialogs=shown, httpsRequests=sent,
                           capLog=line.get("capLog"), **o))
    leaked = [r for r in requests if not r["fromHostPage"] or r["run"] not in BROKER_RUNS]
    assert not leaked, ("an https request outside the host page's broker", leaked)
    return dict(browser=dict(product=version.get("product"), protocol=version.get("protocolVersion")),
                seconds=round(time.time() - t0, 3), profile="restricted-wasm-v1", broker=pin_["source"] | dict(sha256=pin_["sha256"]),
                runs=report, networkRequests=network, attachedTargets=attached,
                notQualified=("a person's click: approvals here are DevTools-dispatched input (isTrusted true, automation); "
                              "a real service endpoint: the declared fixture endpoint is answered at the request stage, "
                              "so nothing leaves the machine"))


def run_app(browser, out, module, allow, mounts, args):
    """One application module with the entry ABI's inputs; see the module doc."""
    files = {}
    for mount in mounts:
        at, _, local = mount.partition("=")
        assert at.startswith("/") and local, ("--file MOUNT=DIR with an absolute MOUNT", mount)
        root = Path(local).resolve()
        for p in sorted(root.rglob("*")):
            if p.is_file():
                files[at.rstrip("/") + "/" + p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
    t0 = time.time()
    version, lines = run_modules(browser, out, [("app", module, dict(fuel=0, allow=allow, args=args, files=files))])
    line = lines["app"]
    output = line.get("output") or ""
    (out / "output").write_text(output, encoding="utf-8")
    report = dict(status="PASS_WASM32_BROWSER_APP" if line.get("exit") == 0 and (line.get("report") or "").startswith("{:status :ok")
                  else "FAIL_WASM32_BROWSER_APP",
                  browser=version, seconds=round(time.time() - t0, 3), module=dict(path=str(module), sha256=sha256(module)),
                  allow=allow, args=args, files=len(files), exit=line.get("exit"), report=line.get("report"),
                  stderr=line.get("stderr"), wasmTrap=line.get("wasmTrap"),
                  output=dict(bytes=len(output.encode()), sha256=hashlib.sha256(output.encode()).hexdigest()))
    (out / "app.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modules", type=Path, help="directory with case-NAME.wasm")
    ap.add_argument("--app", type=Path, help="one application module, run with the entry ABI's inputs")
    ap.add_argument("--allow", default="", help="--app: the wires the page grants (of 35, 37, 38, 39), comma-separated")
    ap.add_argument("--file", action="append", default=[], help="--app: MOUNT=DIR, read-only files")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--browser", help="Chromium or Chrome executable (default: KOTOBA_BROWSER, then PATH)")
    ap.add_argument("args", nargs="*", help="--app: the module's arguments (after --)")
    a = ap.parse_args()
    assert (a.modules is None) != (a.app is None), "give --modules or --app"
    browser = find_browser(a.browser)
    assert browser, "no Chromium or Chrome found"
    a.output.mkdir(parents=True, exist_ok=True)
    if a.app:
        r = run_app(browser, a.output.resolve(), a.app.resolve(), [int(w) for w in a.allow.split(",") if w], a.file, a.args)
        print(r["status"], r["browser"]["product"], r["report"], r["seconds"], "s")
        sys.exit(0 if r["status"] == "PASS_WASM32_BROWSER_APP" else 1)
    report = dict(status="PASS_WASM32_BROWSER_STATIC_CASES", **check_cases(browser, a.output.resolve(), a.modules.resolve()))
    if (a.modules / "probe-cap.wasm").exists():
        report["broker"] = dict(status="PASS_WASM32_BROWSER_BROKER", **check_broker(browser, a.output.resolve(), a.modules.resolve()))
    (a.output / "wasm32-browser.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["browser"]["product"], len(report["cases"]), "cases", len(report["probes"]), "probes",
          report["seconds"], "s")
    if "broker" in report:
        b = report["broker"]
        print(b["status"], b["profile"], len(b["runs"]), "runs:", " ".join(r["name"] for r in b["runs"]), b["seconds"], "s")
