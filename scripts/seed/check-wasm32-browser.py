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
DIR/probe-deep.wasm and DIR/probe-entry.wasm when present (see PROBES), and
DIR/refusal-NAME.wasm against seed/refusal-cases.json (JUN-364: each refusal is
named on stderr before the trap; scripts/seed/refusal_cases.py).

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

sys.dont_write_bytecode = True
import refusal_cases  # noqa: E402 (scripts/seed)

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
    refusal_runs = refusal_cases.wasm_runs(modules)
    assert len(refusal_runs) == len(refusal_cases.load()["cases"]), ("refusal modules missing", modules)
    t0 = time.time()
    version, lines = run_modules(browser, out, [(c["name"], modules / f"case-{c['name']}.wasm") for c in cases]
                                 + [(f"probe-{n}", modules / f"probe-{m}.wasm", e) for n, m, e in probe_runs]
                                 + refusal_runs)
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
    refusals = refusal_cases.check_wasm(lines)
    assert len(refusals) == len(refusal_runs)
    return dict(browser=version, seconds=seconds, fuel=FUEL, cases=results, probes=probe_results, refusals=refusals)


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
    (a.output / "wasm32-browser.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["browser"]["product"], len(report["cases"]), "cases", len(report["probes"]), "probes",
          len(report["refusals"]), "named refusals", report["seconds"], "s")
