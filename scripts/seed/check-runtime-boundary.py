#!/usr/bin/env python3
"""JUN-325: guests cannot call or acquire static runtime functions.

Only native Amu compilers compile sources; Python stages bytes, launches
processes and compares receipts. Never execute a previously admitted exploit.
The caller supplies a fresh disposable output directory.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBES = {
    "syscall": "(kxrt-syscall 172 0 0 0 0 0 0)",
    "load64": "(kxrt-load64 4194304)",
    "store64": "(kxrt-store64 4194304 0)",
    "load8": "(kxrt-load8 4194304)",
    "store8": "(kxrt-store8 4194304 0)",
    "ctx": "(kxrt-ctx)",
    "call-main": "(kxrt-call-main 0)",
    "trap": "(kxrt-trap 0)",
    "call-at": "(kxrt-call-at 0 0 0)",
    "exit": "(kxrt-exit 9)",
    "gl": "(kxrt-gl 72)",
    "gs": "(kxrt-gs 72 0)",
    "allow-bit": "(kxrt-allow-bit 20)",
    "map": "(kxrt-map 4096)",
    "slot-56": "(kxrt-slot-56 0 0 0)",
    "fn-ref-invoke": "(invoke (fn-ref kxrt-exit) 42)",
    "fn-ref-alias": "(let [f (fn-ref kxrt-exit)] (invoke f 42))",
    "bare-alias": "(let [f kxrt-exit] (invoke f 42))",
    "fn-ref-only": "(let [f (fn-ref kxrt-exit)] 42)",
    "fn-ref-ctx": "(invoke (fn-ref kxrt-ctx))",
    "fn-ref-slot": "(invoke (fn-ref kxrt-slot-56) 0 0 0)",
    "qualified-call": "(clojure.core/kxrt-exit 42)",
    "qualified-fn-ref": "(invoke (fn-ref clojure.core/kxrt-exit) 42)",
    "nested-call": "(let [f (fn [x] (kxrt-exit x))] (invoke f 42))",
    "allow-mask": '(let [c (kxrt-ctx) a (kxrt-store64 (+ c 16) -1)] (string-length (typed-cap-call :hash/sha256 :string :string "x")))',
}
FORMATS = [("aarch64-linux", "static"), ("aarch64-linux", "runner"),
           ("x86_64-linux", "static"), ("x86_64-linux", "kx64-runner")]
PLAIN = '(ns plain (:export [main]))\n(defn- add [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (let [f (fn-ref add) k 1 g (fn [x] (+ x k))] (+ (invoke f 20) (invoke g 20))))\n'


def pin(p):
    data = p.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def guest(body):
    return f"(ns g (:export [main]))\n(defn main [] :i64 {body})\n"


def main(compiler, output, previous_root, payload, definition_only_root=None):
    assert platform.system() == "Linux", "run on native Linux"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producers = {"new": compiler}
    if previous_root:
        producers["previous"] = previous_root
    if definition_only_root:
        producers["definition-only"] = definition_only_root
    for who, source in list(producers.items()):
        dst = art / f"{who}.elf"
        dst.write_bytes(source.read_bytes())
        dst.chmod(0o755)
        producers[who] = dst
    if payload:
        dst = art / "payload.kseed"
        dst.write_bytes(payload.read_bytes())
        payload = dst
    calls = []

    def compile_(who, name, source, target, fmt):
        src = art / f"{who}-{name}-{target}-{fmt}.kotoba"
        dst = src.with_suffix(".image")
        src.write_text(source)
        argv = [producers[who], "compile", src, "--target", target, "--output", dst, "--format", fmt]
        if fmt == "packed":
            argv += ["--payload", payload]
        r = subprocess.run(list(map(str, argv)), cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)},
                           capture_output=True, timeout=900)
        src.with_suffix(".stdout").write_bytes(r.stdout)
        src.with_suffix(".stderr").write_bytes(r.stderr)
        calls.append(dict(compiler=who, name=name, target=target, format=fmt, exit=r.returncode,
                          diagnostic=r.stderr.decode(errors="replace").strip(), image=pin(dst) if dst.exists() else None))
        (output / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        return r, dst

    formats = FORMATS + ([("aarch64-linux", "packed")] if payload else [])
    refused, positives = [], []
    for target, fmt in formats:
        for name, body in PROBES.items():
            r, dst = compile_("new", name, guest(body), target, fmt)
            # A bare private function symbol is already rejected by name
            # resolution; explicit fn-ref must reach the backend boundary.
            diagnostic = b"E2102" if name == "bare-alias" else b"E7101"
            assert r.returncode != 0 and diagnostic in r.stderr and not dst.exists(), calls[-1]
            refused.append(dict(name=name, target=target, format=fmt, diagnostic=diagnostic.decode()))
        r, dst = compile_("new", "plain", PLAIN, target, fmt)
        assert r.returncode == 0 and not r.stderr and dst.exists(), calls[-1]
        same = None
        if previous_root:
            r, old = compile_("previous", "plain", PLAIN, target, fmt)
            assert r.returncode == 0 and not r.stderr and old.read_bytes() == dst.read_bytes(), calls[-1]
            same = True
        positives.append(dict(target=target, format=fmt, image=pin(dst), sameBytes=same))
    previous = []
    if previous_root:
        for name in ("syscall", "fn-ref-invoke"):
            r, dst = compile_("previous", name, guest(PROBES[name]), "aarch64-linux", "static")
            admitted = r.returncode == 0 and dst.exists()
            if name == "syscall":
                assert admitted, calls[-1]
            else:
                assert admitted or (r.returncode != 0 and b"E7101" in r.stderr and not dst.exists()), calls[-1]
            previous.append(dict(compiler="previous", name=name, admitted=admitted, executed=False))
    if definition_only_root:
        r, dst = compile_("definition-only", "fn-ref-invoke", guest(PROBES["fn-ref-invoke"]), "aarch64-linux", "static")
        assert r.returncode == 0 and dst.exists(), calls[-1]
        previous.append(dict(compiler="definition-only", name="fn-ref-invoke", admitted=True, executed=False))
    # The closest runtime corpus: same result, fuel, and refusals as the
    # repository's immutable expectations. Only the native host ISA executes.
    host_target = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux"}[platform.machine()]
    cases = []
    for case in json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]:
        r, dst = compile_("new", "case-" + case["name"], case["source"], host_target, "static")
        assert r.returncode == 0 and not r.stderr, calls[-1]
        dst.chmod(0o755)
        r = subprocess.run([str(dst)], cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_ALLOW": "-", "KEXE_FUEL": "1000000"}, capture_output=True, timeout=120)
        (art / ("case-" + case["name"] + ".stdout")).write_bytes(r.stdout)
        (art / ("case-" + case["name"] + ".stderr")).write_bytes(r.stderr)
        fuel = re.search(rb":remaining ([0-9]+)", r.stdout)
        observed = dict(exit=r.returncode, remainingFuel=int(fuel[1]) if fuel else None)
        assert observed == case["reference"], (case["name"], observed, case["reference"])
        if case["trap"]:
            assert b":status :trap" in r.stdout, case["name"]
        else:
            assert int(re.search(rb":result (-?[0-9]+)", r.stdout)[1]) == case["result"], case["name"]
        cases.append(dict(name=case["name"], **observed))
    report = dict(status="PASS_RUNTIME_BOUNDARY", compiler=pin(compiler), previousRoot=pin(previous_root) if previous_root else None,
                  host=[platform.system(), platform.machine(), platform.release()], refused=refused, positives=positives,
                  previous=previous, runtimeCases=cases, payload=pin(payload) if payload else None,
                  cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    (output / "runtime-boundary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(refused), "refusals/no-image;", len(cases), "native runtime cases", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous-root", type=Path)
    parser.add_argument("--definition-only-root", type=Path, help="records the fn-ref admission after the definition-position-only fix")
    parser.add_argument("--payload", type=Path, help="KSEED2 payload also exercises the current-main packed format")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.previous_root.resolve() if args.previous_root else None,
         args.payload.resolve() if args.payload else None, args.definition_only_root.resolve() if args.definition_only_root else None)
