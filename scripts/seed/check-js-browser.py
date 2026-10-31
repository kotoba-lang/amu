#!/usr/bin/env python3
"""Compile and run js-browser-static/v1 modules in headless Chromium (ADR 0397, JUN-706).

A compiler F (the Mac full compiler, or a Linux ELF) compiles the 24 runtime cases
(seed/static-cases.json) and the wasm probes of selfhost-bootstrap.py to both
--target js-browser and --target wasm32-browser. The modules run in headless
Chromium through runtime/js-browser-static-run.html and the shared Worker host
(runtime/wasm32-browser-static-host.js), driven by check-wasm32-browser.py's
DevTools pipe: no Node, npm, nbb or Playwright. The gate requires:

* every js case to return the static case's result, trap and remaining fuel;
* every js case's stdout (the native report included) to equal the wasm module's,
  byte for byte, so the two emitters agree on the same SIR;
* the probes as on wasm: fuel exhaustion traps with no fuel left (spin), unbounded
  recursion ends as a trap outside the handler (deep, exit 120), and the entry ABI
  echoes a page-supplied file only with the page's grants (entry, entry-denied);
* every module to export only instantiate and to name no global or loader
  (FORBIDDEN, scanned outside string literals), with a negative control: the scan
  must refuse a module that calls fetch;
* the float cases to be refused at compile time (E7101) without an artifact.

check-js-browser.py --compiler F --output OUT [--browser PATH]
"""
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "seed/static-cases.json"
FLOAT_CASES = ROOT / "seed/float-cases.json"
PAGE = ROOT / "runtime/js-browser-static-run.html"
HOST = ROOT / "runtime/wasm32-browser-static-host.js"
FORBIDDEN = ("globalThis", "window", "self", "document", "fetch", "XMLHttpRequest", "WebSocket", "importScripts",
             "import(", "eval", "Function", "WebAssembly", "require", "process", "postMessage", "setTimeout")


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/seed" / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


sys.path.insert(0, str(ROOT / "scripts/seed"))  # selfhost-bootstrap imports its siblings, also under python3 -I
WASM = module("check_wasm32_browser", "check-wasm32-browser.py")
BOOT = module("selfhost_bootstrap", "selfhost-bootstrap.py")


def compile_(F, work, src, target, dst, expected=0):
    """Compile work/src with F; the Mac image gets the output-owned FD3 root, an ELF the cap scope."""
    if F.suffix == ".macho":
        mac = module("mac_native", "check-aiueos-user-macos-native.py")
        return mac.native_run(F, work, "compile", src, "--target", target, "--output", dst, expected=expected)
    r = subprocess.run([str(F), "compile", src, "--target", target, "--output", dst], cwd=work, capture_output=True,
                       env=dict(PATH="/usr/bin:/bin", KEXE_CAP_RESOURCES_35=str(work)), timeout=1200)
    if r.returncode != expected:
        raise ValueError(f"{src} -> {target}: exit {r.returncode}: {r.stderr.decode(errors='replace')[-600:]}")
    return r


def code_tokens(text):
    """The module text with every string literal blanked, so the scan reads code only."""
    return re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)


def scan(text):
    """Problems of a js-browser module: forbidden names, imports, or exports other than instantiate."""
    code = code_tokens(text)
    problems = [name for name in FORBIDDEN
                if re.search(r"(?<![A-Za-z0-9_$])" + re.escape(name) + (r"" if name.endswith("(") else r"(?![A-Za-z0-9_$])"), code)]
    if re.search(r"(?m)^\s*import\b", code):
        problems.append("import statement")
    exports = re.findall(r"\bexport\b[^\n]*", code)
    if exports != ['export function instantiate(host){"";']:  # the directive's string is blanked
        problems.append("exports " + repr(exports))
    return problems


def run_js(browser, out, runs, timeout=600):
    """runs: [(name, module path, extra)] for .mjs and .wasm alike; one page, one Worker per run."""
    page_dir = out / "page"
    page_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(PAGE, page_dir / PAGE.name)
    shutil.copy(HOST, page_dir / HOST.name)
    data = []
    for name, path, extra in runs:
        item = dict(name=name, fuel=WASM.FUEL)
        if path.suffix == ".mjs":
            item["js"] = path.read_text()
        else:
            import base64
            item["wasm"] = base64.b64encode(path.read_bytes()).decode()
        data.append(dict(item, **extra))
    (page_dir / "runs.js").write_text("window.KOTOBA_RUNS = " + json.dumps(data) + ";\n")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="kotoba-js-browser-") as profile:
        pipe = WASM.Pipe(browser, profile)
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


def main(args):
    F = args.compiler.resolve(strict=True)
    browser = WASM.find_browser(args.browser)
    if browser is None:
        raise ValueError("no Chromium or Chrome found (--browser or KOTOBA_BROWSER)")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work = out / "work"
    work.mkdir()
    cases = json.loads(CASES.read_text())["cases"]
    probes = {k: v for k, v in BOOT.WASM_PROBES.items() if k in ("spin", "deep", "entry")}
    modules = []
    for case in cases:
        (work / f"case-{case['name']}.kotoba").write_text(case["source"])
        modules.append((f"case-{case['name']}", case))
    for name, body in probes.items():
        (work / f"probe-{name}.kotoba").write_text(f"(ns probe-{name} (:export [main]))\n{body}\n")
        modules.append((f"probe-{name}", None))
    for stem, _ in modules:
        compile_(F, work, f"{stem}.kotoba", "js-browser", f"{stem}.mjs")
        compile_(F, work, f"{stem}.kotoba", "wasm32-browser", f"{stem}.wasm")
    scans = {stem: scan((work / f"{stem}.mjs").read_text()) for stem, _ in modules}
    bad = {k: v for k, v in scans.items() if v}
    if bad:
        raise ValueError(f"module scan: {bad}")
    mutated = (work / "case-string-literal.mjs").read_text().replace("let pc=0", "let pc=0;fetch(\"x\")", 1)
    if "fetch" not in scan(mutated):
        raise ValueError("negative control: the scan accepted a module that calls fetch")
    floats = []
    if FLOAT_CASES.exists():
        for case in json.loads(FLOAT_CASES.read_text())["cases"]:
            (work / f"float-{case['name']}.kotoba").write_text(case["source"])
            r = compile_(F, work, f"float-{case['name']}.kotoba", "js-browser", f"float-{case['name']}.mjs", expected=1)
            if b"E7101" not in r.stderr or (work / f"float-{case['name']}.mjs").exists():
                raise ValueError(f"float case {case['name']} was not refused: {r.stderr[-300:]}")
            floats.append(case["name"])
    runs = []
    for stem, _ in modules:
        extras = WASM.PROBE_RUNS.get(stem[len("probe-"):], [(stem[len("probe-"):], {})]) if stem.startswith("probe-") else [(stem, {})]
        for name, extra in extras:
            key = name if not stem.startswith("probe-") else f"probe-{name}"
            runs.append((f"js:{key}", work / f"{stem}.mjs", extra))
            runs.append((f"wasm:{key}", work / f"{stem}.wasm", extra))
    t0 = time.time()
    version, lines = run_js(browser, out, runs)
    seconds = round(time.time() - t0, 3)
    results = []
    for case in cases:
        js, wasm = lines[f"js:case-{case['name']}"], lines[f"wasm:case-{case['name']}"]
        o = WASM.observe(js)
        status = "trap" if case["trap"] else "ok"
        ok = (o["exit"] == case["reference"]["exit"] and o["remainingFuel"] == case["reference"]["remainingFuel"]
              and o["status"] == status and (case["trap"] or o["result"] == case["result"]))
        if not ok:
            raise ValueError(f"case {case['name']}: {o} expected {case['result']} {case['reference']} ({js})")
        if (js.get("stdout"), js.get("exit")) != (wasm.get("stdout"), wasm.get("exit")):
            raise ValueError(f"case {case['name']}: js and wasm differ: {js} / {wasm}")
        results.append(dict(name=case["name"], **o))
    probe_results = []
    for name, expect in WASM.PROBES.items():
        key = f"js:probe-{name}"
        if key not in lines:
            continue
        line = lines[key]
        o = WASM.observe(line)
        if not all(o[k] == v for k, v in expect.items()):
            raise ValueError(f"probe {name}: {o} expected {expect} ({line})")
        if name == "deep" and not line.get("wasmTrap"):
            raise ValueError(f"probe deep ended without an engine trap: {line}")
        if name == "entry" and line.get("output") != WASM.ENTRY_TEXT:
            raise ValueError(f"probe entry: {line}")
        if name == "entry-denied" and ":wire 38 :refused" not in (line.get("stderr") or ""):
            raise ValueError(f"probe entry-denied: {line}")
        probe_results.append(dict(name=name, engineTrap=line.get("wasmTrap"), **o))
    report = dict(schema="amu.js-browser-target.v1", status="PASS_JS_BROWSER_TARGET", browser=version, seconds=seconds,
                  fuel=WASM.FUEL, compiler=dict(path=str(F), sha256=WASM.sha256(F)), cases=results, probes=probe_results,
                  identicalToWasm32Browser=len(results), floatRefusals=floats,
                  modules={stem: WASM.sha256(work / f"{stem}.mjs") for stem, _ in modules},
                  forbiddenScan=dict(names=list(FORBIDDEN), negativeControl="fetch refused"),
                  nodeOrNbb=False)
    (out / "js-browser.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(results), "cases identical to wasm32-browser,", len(probe_results), "probes,",
          len(floats), "float refusals", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--browser")
    main(p.parse_args())
