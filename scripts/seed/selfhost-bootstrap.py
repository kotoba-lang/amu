#!/usr/bin/env python3
"""Loaderless Amu selfhost bootstrap on arm64 Linux. No C compiler or C loader.

Starts from the pinned Amu-produced aarch64-linux-static compiler
(seed/bootstrap/aarch64-linux-static-root.elf) and records, natively:

1. the Linux selfhost closure rebuilt by the root, then S1 = S2 = S3;
2. S3's aarch64 runner, x86_64 static compiler and x86_64 KX64V1 runner;
3. the adopted compiler core (ADR 0370) from source: S3 builds it as a static
   image C0 (seed/CORE-STATIC-MANIFEST), C0 compiles seed/MANIFEST to G1, and
   G1, G2 run by the aarch64 runner give G2, G3: G1 = G2 = G3 = the adoption
   receipt's image. The historical C-loader-built payload is not used;
4. the runtime case suite (seed/static-cases.json) as static images;
5. the runtime hardening: seccomp enforced, cpu / wall / stack limits;
6. runtime capabilities: wire 3 :hash/sha256 (FIPS vectors, granted and
   refused) and a source found under the second of several scope roots.

Python only orchestrates processes and hashes. Run it on arm64 Linux, for
example: podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT
python:3.12-alpine python3 REPO/scripts/seed/selfhost-bootstrap.py --output OUT
"""
import argparse
import hashlib
import shutil
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
ADOPTED = "seed/MANIFEST"
ROOT_IMAGE = "seed/bootstrap/aarch64-linux-static-root.elf"
ROOT_RECEIPT = "seed/bootstrap/aarch64-linux-static-root.json"
CORE_STATIC = "seed/CORE-STATIC-MANIFEST"
NS, NS_STATIC = "seed/00-ns.kotoba", "seed/00-ns-static.kotoba"
ADOPTION = "seed/adoption-20261017.json"
RUNNER_SRC = "seed/x86_64-kx64-runner.kotoba"
CASES = "seed/static-cases.json"
# 00-ns-static is 00-ns with the static profile's capacities (seed/MEMORY-MAP).
STATIC_CAPACITIES = re.compile(rb"\(def MM-(WORDS|(CODE|FIX|LITB|OUT)-CAP|(FIX|LIT|LITB|EXP|OUT|HEAP)-BASE|HEAP-END) [0-9]+\)")
# The adopted compiler was qualified on a host whose main stack is 8 MiB; the
# runtime's default (1 MiB, the old loader's limit) is too small for it.
ADOPTED_STACK = "8388608"


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unity(manifest, dst):
    paths = [p for p in (ROOT / manifest).read_text().splitlines() if p and not p.startswith("#")]
    dst.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    return {p: pin(ROOT / p) for p in [manifest, *paths]}


class Runs:
    def __init__(self, out):
        self.out, self.calls = out, []
        (out / "raw").mkdir()

    def run(self, name, argv, env, success=True, timeout=3600):
        argv = list(map(str, argv))
        r = subprocess.run(argv, cwd=self.out, env={"PATH": "/usr/bin:/bin", **env}, capture_output=True, timeout=timeout)
        (self.out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (self.out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        self.calls.append(dict(name=name, argv=argv, env=env, exit=r.returncode))
        (self.out / "calls.json").write_text(json.dumps(self.calls, indent=1) + "\n")
        if success:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr.decode(errors="replace"))
        return r


def main(out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    out.mkdir(parents=True, exist_ok=False)
    run = Runs(out)
    scope = {"KEXE_CAP_RESOURCES_35": str(out)}
    root_receipt = json.loads((ROOT / ROOT_RECEIPT).read_text())
    assert pin(ROOT / ROOT_IMAGE) == root_receipt["image"], "pinned root image mismatch"
    producer = out / "root.elf"
    producer.write_bytes((ROOT / ROOT_IMAGE).read_bytes())
    producer.chmod(0o755)
    source = out / "selfhost-unity.kotoba"
    source_pins = unity(SELFHOST, source)

    def compile_(prod, src, dst, target, fmt, name):
        run.run(name, [prod, "compile", src, "--target", target, "--output", dst, "--format", fmt], scope)
        dst.chmod(0o755)
        return pin(dst)

    # 1. the Linux selfhost closure, natively, from the pinned root
    gens = []
    for g in (1, 2, 3):
        image = out / f"S{g}.elf"
        gens.append(dict(name=f"S{g}", producedBy=producer.name, pin=compile_(producer, source, image, "aarch64-linux", "static", f"S{g}")))
        producer = image
    # S2 = S3 is the fixed point. S1 also equals them when the root's code
    # generator matches the source; after a codegen change it differs once,
    # and the root is then re-pinned to S3 (recorded as rootReproduces).
    assert gens[1]["pin"] == gens[2]["pin"], "aarch64 static fixed point mismatch"
    root_reproduces = gens[0]["pin"] == gens[1]["pin"] == pin(ROOT / ROOT_IMAGE)
    S = out / "S3.elf"

    # 2. runners and the x86_64 compiler, from S3
    (out / "runner.kotoba").write_bytes((ROOT / RUNNER_SRC).read_bytes())
    built = dict(
        aarch64Runner=compile_(S, out / "runner.kotoba", out / "R-aarch64.elf", "aarch64-linux", "runner", "R-aarch64"),
        x86_64Compiler=compile_(S, source, out / "S-x86_64.elf", "x86_64-linux", "static", "S-x86_64"),
        x86_64Runner=compile_(S, out / "runner.kotoba", out / "R-x86_64.elf", "x86_64-linux", "kx64-runner", "R-x86_64"))

    # 3. the adopted compiler core from source: C0 (static, from S3) -> G1,
    # then G1 and G2 through the aarch64 runner
    adoption = json.loads((ROOT / ADOPTION).read_text())
    adopted_src = out / "adopted-unity.kotoba"
    adopted_pins = unity(ADOPTED, adopted_src)
    assert pin(adopted_src)["sha256"] == adoption["sourceUnitySHA256"], "adopted source drift"
    ns, ns_static = ((ROOT / p).read_bytes() for p in (NS, NS_STATIC))
    strip = lambda b: STATIC_CAPACITIES.sub(b"", b"".join(l for l in b.splitlines(True) if not l.startswith(b";; seed/00-ns-static")
                                                         and not l.startswith(b";; CORE-STATIC") and not l.startswith(b";; (CODE, FIX")))
    assert strip(ns) == strip(ns_static), "00-ns-static differs from 00-ns beyond the static capacities"
    core_static_src = out / "core-static-unity.kotoba"
    core_static_pins = unity(CORE_STATIC, core_static_src)
    senv = dict(scope, KEXE_STACK_BYTES=ADOPTED_STACK)
    run.run("C0", [S, "compile", core_static_src, "--target", "aarch64-linux", "--output", out / "C0.elf", "--format", "static"], senv)
    (out / "C0.elf").chmod(0o755)
    c0 = pin(out / "C0.elf")
    renv = dict(scope, KEXE_COMMAND="1", KEXE_STACK_BYTES=ADOPTED_STACK)
    adopted_gens = []
    payload = None
    for g in (1, 2, 3):
        prefix, env = ([out / "C0.elf"], senv) if g == 1 else ([out / "R-aarch64.elf", payload, 0, 0, "aarch64", "35,37,38,39", "--"], renv)
        container, native = out / f"G{g}.kseed", out / f"G{g}.bin"
        run.run(f"G{g}-compile", prefix + ["compile", adopted_src, "--target", "aarch64-macos", "--output", container], env)
        run.run(f"G{g}-extract", prefix + ["extract-native", container, "--symbol", "main", "--output", native], env)
        assert pin(native)["sha256"] == adoption["nativeImageSHA256"], "adopted fixed point mismatch"
        adopted_gens.append(dict(generation=g, native=pin(native), container=pin(container)))
        payload = native

    # 4. runtime cases as static images against the pinned loader results
    cases = json.loads((ROOT / CASES).read_text())["cases"]
    results = []
    for case in cases:
        src = out / f"case-{case['name']}.kotoba"
        src.write_text(case["source"])
        compile_(S, src, out / f"case-{case['name']}.elf", "aarch64-linux", "static", f"case-{case['name']}-compile")
        r = run.run(f"case-{case['name']}", [out / f"case-{case['name']}.elf"],
                    dict(KEXE_STRUCTURED_REPORT="1", KEXE_FUEL="1000000", KEXE_ALLOW="-"), success=False)
        fuel = re.search(rb":remaining ([0-9]+)", r.stdout)
        observed = dict(exit=r.returncode, remainingFuel=int(fuel[1]) if fuel else None)
        assert observed == case["reference"], (case["name"], observed, case["reference"])
        if case["trap"]:
            assert b":status :trap" in r.stdout
        else:
            assert int(re.search(rb":result (-?[0-9]+)", r.stdout)[1]) == case["result"]
        results.append(dict(name=case["name"], **observed))

    # 5. hardening, natively
    probes = {"value": "(defn main [] :i64 42)",
              "spin": "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))",
              "deep": "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"}
    for name, body in probes.items():
        src = out / f"probe-{name}.kotoba"
        src.write_text(f"(ns probe-{name} (:export [main]))\n{body}\n")
        compile_(S, src, out / f"probe-{name}.elf", "aarch64-linux", "static", f"probe-{name}-compile")

    def observe(name, image, env):
        r = run.run("probe-" + name, [out / f"probe-{image}.elf"], dict(KEXE_STRUCTURED_REPORT="1", **env), success=False)
        return dict(exit=r.returncode, stderr=r.stderr.decode(errors="replace").strip())
    hardening = dict(
        seccompDefault=observe("seccomp-default", "value", {}),
        sandboxProbe=observe("sandbox-probe", "value", dict(KEXE_SANDBOX_PROBE="1")),
        cpuSeconds1=observe("cpu", "spin", dict(KEXE_CPU_SECONDS="1")),
        wallSeconds3=observe("wall", "spin", dict(KEXE_WALL_SECONDS="3")),
        stack1MiB=observe("stack", "deep", {}))
    assert hardening["seccompDefault"]["exit"] == 0, "seccomp must install on this kernel"
    assert hardening["sandboxProbe"]["exit"] == 120 and "SIGSYS" in hardening["sandboxProbe"]["stderr"]
    assert hardening["cpuSeconds1"]["exit"] == 120 and "SIGXCPU" in hardening["cpuSeconds1"]["stderr"]
    assert hardening["wallSeconds3"]["exit"] == 120 and "SIGALRM" in hardening["wallSeconds3"]["stderr"]
    assert hardening["stack1MiB"]["exit"] == 120 and "SIGSEGV" in hardening["stack1MiB"]["stderr"]

    # 6. capabilities: wire 3 and multiple KEXE_CAP_RESOURCES_35 roots
    roots = [out / "cap-missing", out / "cap-a", out / "cap-b"]
    for r in roots[1:]:
        r.mkdir()
    vectors = {"abc": None, "": None, "x" * 200: None}
    body = "\n".join(f'(if (string=? (typed-cap-call :hash/sha256 :string :string "{t}") "{hashlib.sha256(t.encode()).hexdigest()}") {1 << i} 0)'
                     for i, t in enumerate(vectors))
    (roots[2] / "hash.kotoba").write_text(f"(ns hash-check (:export [main]))\n(defn main [] :i64 (+ {body}))\n")
    cap_env = {"KEXE_CAP_RESOURCES_35": ":".join(map(str, roots))}
    run.run("cap-compile", [S, "compile", roots[2] / "hash.kotoba", "--target", "aarch64-linux", "--output", roots[2] / "hash.elf",
                            "--format", "static"], cap_env)
    (roots[2] / "hash.elf").chmod(0o755)
    granted = run.run("cap-hash-granted", [roots[2] / "hash.elf"], {"KEXE_ALLOW": "3"}, success=False)
    refused = run.run("cap-hash-refused", [roots[2] / "hash.elf"], {"KEXE_ALLOW": "37"}, success=False)
    outside = run.run("cap-outside-roots", [S, "compile", roots[2] / "hash.kotoba", "--target", "aarch64-linux",
                                            "--output", roots[1] / "x.elf", "--format", "static"],
                      {"KEXE_CAP_RESOURCES_35": str(roots[1])}, success=False)
    assert granted.returncode == 7, ("sha256 vectors", granted.returncode)
    assert refused.returncode == 120 and b"SIGILL" in refused.stderr
    assert outside.returncode != 0 and not (roots[1] / "x.elf").exists()
    capabilities = dict(sha256Vectors=len(vectors), granted=granted.returncode, refused=refused.returncode,
                        scopeRoots=len(roots), sourceUnderRoot=3, outsideRootsExit=outside.returncode)

    report = dict(status="PASS_LOADERLESS_SELFHOST_BOOTSTRAP", capabilities=capabilities, host=[platform.system(), platform.machine(), platform.release()],
                  root=dict(image=pin(ROOT / ROOT_IMAGE), receipt=root_receipt), sourceGraph=source_pins,
                  generations=gens, rootReproduces=root_reproduces, built=built,
                  adopted=dict(sourceGraph=adopted_pins, coreStatic=dict(sourceGraph=core_static_pins, image=c0), runnerStackBytes=int(ADOPTED_STACK), generations=adopted_gens,
                               expectedNativeImage=adoption["nativeImageSHA256"]),
                  cases=results, hardening=hardening,
                  cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    (out / "selfhost-bootstrap.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "S2=S3", gens[2]["pin"]["sha256"][:16], "root reproduces" if root_reproduces else "root differs (re-pin to S3)", "adopted G1=G2=G3", len(results), "cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output.resolve())
