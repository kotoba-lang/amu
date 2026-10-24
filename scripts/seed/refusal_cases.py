"""JUN-364: named capability refusals (seed/refusal-cases.json), natively and as wasm32-browser modules.

Each case is a guest whose one capability call the static runtime refuses. The
runtime writes KEXE_TRAP {:kind :capability :wire W :refusal :NAME}, then traps
as before (SIGILL, exit 120). selfhost-bootstrap.py runs them on aarch64-linux,
check-x86_64-native.py on x86_64-linux, and check-wasm32-browser.py runs their
wasm32-browser modules (refusal-NAME.wasm) in headless Chromium.

Python only writes the sources, starts the processes and compares bytes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "seed/refusal-cases.json"


def load():
    return json.loads(CASES.read_text())


def write_sources(out):
    """The case sources as out/refusal-NAME.kotoba, and the input file; returns the cases."""
    doc = load()
    (out / doc["inputFile"]["name"]).write_text(doc["inputFile"]["text"])
    for case in doc["cases"]:
        (out / f"refusal-{case['name']}.kotoba").write_text(case["source"])
    return doc["cases"]


def check_native(out, compile_, run):
    """compile_(src, dst, name) builds a static image; run(name, argv, env) runs it in out (the
    working directory) and returns the CompletedProcess. Asserts every case's exit and stderr."""
    doc = load()
    trap = doc["trapLine"].encode()
    results = []
    for case in write_sources(out):
        src, dst = out / f"refusal-{case['name']}.kotoba", out / f"refusal-{case['name']}.elf"
        compile_(src, dst, f"refusal-{case['name']}-compile")
        r = run(f"refusal-{case['name']}", [dst], {"KEXE_ALLOW": case["allow"], "KEXE_CAP_RESOURCES_35": str(out),
                                                    "KEXE_FUEL": "1000000", "KEXE_STRUCTURED_REPORT": "1"})
        want = case["stderr"].encode() + trap
        assert r.returncode == 120 and r.stderr == want and b":status :trap" in r.stdout, \
            ("named refusal", case["name"], r.returncode, r.stderr[-400:], want)
        results.append(dict(name=case["name"], exit=r.returncode, stderr=r.stderr.decode()))
    return results


def wasm_runs(modules):
    """The check-wasm32-browser.py runs of the refusal-NAME.wasm modules present in `modules`."""
    return [(f"refusal-{c['name']}", modules / f"refusal-{c['name']}.wasm", dict(allow=c["wasm32"]["allow"]))
            for c in load()["cases"] if (modules / f"refusal-{c['name']}.wasm").exists()]


def check_wasm(lines):
    """lines: check-wasm32-browser.py's result lines by name. Asserts the cases that ran."""
    doc = load()
    results = []
    for c in doc["cases"]:
        line = lines.get(f"refusal-{c['name']}")
        if line is None:
            continue
        want = c["wasm32"]["stderr"] + doc["trapLine"]
        assert line.get("exit") == 120 and (line.get("stderr") or "") == want, ("wasm32 named refusal", c["name"], line, want)
        results.append(dict(name=c["name"], exit=line.get("exit"), stderr=line.get("stderr")))
    return results
