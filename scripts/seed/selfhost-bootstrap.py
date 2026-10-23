#!/usr/bin/env python3
"""Loaderless Amu selfhost bootstrap on arm64 Linux. No C compiler or C loader.

Starts from the pinned Amu-produced aarch64-linux-static compiler
(seed/bootstrap/aarch64-linux-static-root.elf) and records, natively:

1. the Linux selfhost closure rebuilt by the root, then S1 = S2 = S3;
2. S3's aarch64 runner, x86_64 static compiler and x86_64 KX64V1 runner;
3. the adopted compiler core (ADR 0370) from source: S3 builds it as a static
   image C0 (seed/CORE-STATIC-MANIFEST), C0 compiles seed/MANIFEST to G1, and
   G1, G2 run by the aarch64 runner give G2, G3: G1 = G2 = G3 = the adoption
   receipt's image. The historical C-loader-built payload is not used.
   S3 then packs G3 into a standalone static image (--format packed) that
   rebuilds the same core;
4. the runtime case suite (seed/static-cases.json) as static images;
5. the runtime hardening: seccomp enforced, cpu / wall / stack limits;
6. runtime capabilities: wire 3 :hash/sha256 (FIPS vectors, granted and
   refused) and a source found under the second of several scope roots.

Content-addressed reuse (--reuse DIR) may stand in only for C0's compile of
the core (G1), the one slow call, and only when its key matches: the sha256 of
every file its argv names (C0, rebuilt from S3 on every run, and the unity),
the argv and the full environment. --store DIR records results without reusing
any (the full run). The receipt's steps and reuse say what ran and what was
reused, with the keys. Without either flag everything runs.

Python only orchestrates processes and hashes. Run it on arm64 Linux, for
example: podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT
python:3.12-alpine python3 REPO/scripts/seed/selfhost-bootstrap.py --output OUT
"""
import argparse
import hashlib
import shutil
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
ADOPTED = "seed/MANIFEST"
ROOT_IMAGE = "seed/bootstrap/aarch64-linux-static-root.elf"
ROOT_RECEIPT = "seed/bootstrap/aarch64-linux-static-root.json"
CORE_STATIC = "seed/CORE-STATIC-MANIFEST"
NS, NS_STATIC = "seed/00-ns.kotoba", "seed/00-ns-static.kotoba"
# The selected complete lineage is pinned centrally; older adoption receipts
# remain immutable provenance rather than a second default compiler.
ADOPTION = json.loads((ROOT / "seed/compiler-core.json").read_text())["adoptionReceipt"]
RUNNER_SRC = "seed/x86_64-kx64-runner.kotoba"
CASES = "seed/static-cases.json"
# 00-ns-static is 00-ns with the static profile's capacities (seed/MEMORY-MAP).
STATIC_CAPACITIES = re.compile(rb"\(def MM-(WORDS|(CODE|FIX|LITB|OUT)-CAP|(FIX|LIT|LITB|EXP|OUT|HEAP)-BASE|HEAP-END) [0-9]+\)")
# The adopted compiler was qualified on a host whose main stack is 8 MiB; the
# runtime's default (1 MiB, the old loader's limit) is too small for it.
ADOPTED_STACK = "8388608"
RUN_PATH = "/usr/bin:/bin"
# Bump when the meaning of a reuse record changes.
REUSE_VERSION = 1


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unity(manifest, dst):
    paths = [p for p in (ROOT / manifest).read_text().splitlines() if p and not p.startswith("#")]
    dst.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    return {p: pin(ROOT / p) for p in [manifest, *paths]}


class Runs:
    def __init__(self, out, reuse=None, store=None):
        self.out, self.calls, self.reuse, self.store = out, [], reuse, store
        (out / "raw").mkdir()

    def _record(self, call):
        self.calls.append(call)
        (self.out / "calls.json").write_text(json.dumps(self.calls, indent=1) + "\n")

    def run(self, name, argv, env, success=True, timeout=3600):
        argv = list(map(str, argv))
        t = time.monotonic()
        r = subprocess.run(argv, cwd=self.out, env={"PATH": RUN_PATH, **env}, capture_output=True, timeout=timeout)
        (self.out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (self.out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        self._record(dict(name=name, argv=argv, env=env, exit=r.returncode, seconds=round(time.monotonic() - t, 1)))
        if success:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr.decode(errors="replace"))
        return r

    def key_material(self, argv, env, outputs):
        """Every input byte of a call: the sha256 of each existing file its argv
        names (the producing image first), the argv and the full environment
        with the output directory written as $OUT, and the declared outputs."""
        norm = lambda v: str(v).replace(str(self.out), "$OUT")
        files = {norm(a): pin(a) for a in map(Path, map(str, argv)) if a.is_absolute() and a.is_file()}
        assert norm(argv[0]) in files, "the producing image must be a file"
        return dict(version=REUSE_VERSION, host=[platform.system(), platform.machine()], argv=[norm(a) for a in argv],
                    env={k: norm(v) for k, v in sorted({"PATH": RUN_PATH, **env}.items())},
                    inputs=files, outputs=sorted(norm(o) for o in outputs))

    def run_cached(self, name, argv, env, outputs, timeout=3600):
        """run(), or the content-addressed result of the identical call. The key
        covers every input byte (key_material); a hit restores the recorded
        outputs and verifies their pins. Anything different reruns the call."""
        material = self.key_material(argv, env, outputs)
        key = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        entry = self.reuse / key if self.reuse else None
        if entry and (entry / "record.json").is_file():
            record = json.loads((entry / "record.json").read_text())
            assert record["key"] == key and record["material"] == material, (name, "reuse record does not match its key")
            for o in outputs:
                stored = entry / Path(o).name
                assert pin(stored) == record["outputs"][Path(o).name], (name, "reused output drift", o)
                shutil.copyfile(stored, o)
            for stream in ("stdout", "stderr"):
                (self.out / "raw" / f"{name}.{stream}").write_bytes((entry / stream).read_bytes())
            assert record["exit"] == 0 and not (entry / "stderr").read_bytes(), name
            reused = dict(key=key, **{"from": record["from"]})
            self._record(dict(name=name, argv=list(map(str, argv)), env=env, exit=0, seconds=0, reused=reused))
            return reused
        r = self.run(name, argv, env, timeout=timeout)
        self.calls[-1]["key"] = key
        if self.store:
            entry = self.store / key
            entry.mkdir(parents=True, exist_ok=True)
            for o in outputs:
                shutil.copyfile(o, entry / Path(o).name)
            (entry / "stdout").write_bytes(r.stdout)
            (entry / "stderr").write_bytes(r.stderr)
            origin = {k: os.environ[k] for k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_EVENT_NAME")
                      if k in os.environ} or "local"
            (entry / "record.json").write_text(json.dumps(dict(key=key, material=material, exit=r.returncode, **{"from": origin},
                                                               outputs={Path(o).name: pin(o) for o in outputs}), indent=1) + "\n")
        return None


def lookup_key():
    """A cache lookup hint for CI, not the reuse key: the script and every
    source and image the reusable calls derive from. The exact per-call key is
    still checked by run_cached."""
    h = hashlib.sha256()
    for p in (Path(__file__).resolve(), ROOT / ROOT_IMAGE):
        h.update(hashlib.sha256(p.read_bytes()).digest())
    for manifest in (SELFHOST, CORE_STATIC, ADOPTED):
        for p in [manifest, *(l for l in (ROOT / manifest).read_text().splitlines() if l and not l.startswith("#"))]:
            h.update(p.encode() + b"\0" + hashlib.sha256((ROOT / p).read_bytes()).digest())
    return h.hexdigest()


def main(out, reuse=None, store=None):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    out.mkdir(parents=True, exist_ok=False)
    run = Runs(out, reuse, store)
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
        # C0's code is unoptimized: its compile of the core takes ~32 min on an
        # Apple-silicon VM and over an hour on a hosted arm64 runner.
        # G1 is the one call content-addressed reuse may stand in for (--reuse):
        # its key is C0's fresh image hash, the unity hash, argv and env. G2, G3
        # are still re-derived from it by the runner on every run.
        call = run.run_cached if g == 1 else (lambda name, argv, env, outputs, timeout: run.run(name, argv, env, timeout=timeout))
        call(f"G{g}-compile", prefix + ["compile", adopted_src, "--target", "aarch64-macos", "--output", container], env,
             [container], timeout=10800 if g == 1 else 3600)
        call(f"G{g}-extract", prefix + ["extract-native", container, "--symbol", "main", "--output", native], env, [native], timeout=3600)
        assert pin(native)["sha256"] == adoption["nativeImageSHA256"], "adopted fixed point mismatch"
        adopted_gens.append(dict(generation=g, native=pin(native), container=pin(container)))
        payload = native

    # 3b. the core as a standalone static image: S3 packs G3's container
    # (--format packed); the packed compiler rebuilds the core to the same
    # container and image. A payload whose main takes arguments is refused.
    P = out / "P-aarch64.elf"
    run.run("P-pack", [S, "compile", out / "runner.kotoba", "--target", "aarch64-linux", "--output", P,
                       "--format", "packed", "--payload", out / "G3.kseed"], scope)
    P.chmod(0o755)
    run.run("P-compile", [P, "compile", adopted_src, "--target", "aarch64-macos", "--output", out / "P.kseed"], senv)
    run.run("P-extract", [P, "extract-native", out / "P.kseed", "--symbol", "main", "--output", out / "P.bin"], senv)
    assert pin(out / "P.bin")["sha256"] == adoption["nativeImageSHA256"], "packed compiler output mismatch"
    assert pin(out / "P.kseed") == adopted_gens[2]["container"], "packed compiler container mismatch"
    (out / "arity1.kotoba").write_text("(ns arity1 (:export [main]))\n(defn main [x :i64] :i64 x)\n")
    run.run("arity1-compile", [P, "compile", out / "arity1.kotoba", "--target", "aarch64-macos", "--output", out / "arity1.kseed"], senv)
    r = run.run("arity1-pack", [S, "compile", out / "runner.kotoba", "--target", "aarch64-linux", "--output", out / "arity1.elf",
                                "--format", "packed", "--payload", out / "arity1.kseed"], scope, success=False)
    assert r.returncode == 1 and b"E7105" in r.stderr and not (out / "arity1.elf").exists(), "packed arity refusal"
    packed = dict(image=pin(P), container=pin(out / "P.kseed"), native=pin(out / "P.bin"),
                  arityRefusal=dict(exit=r.returncode, stderr=r.stderr.decode().strip()))

    # JUN-325: run the shared call/function-value boundary corpus, including
    # this main's packed route, through the freshly selfhost-built compiler.
    run.run("runtime-boundary", [sys.executable, ROOT / "scripts/seed/check-runtime-boundary.py",
                                 "--compiler", S, "--output", out / "runtime-boundary",
                                 "--payload", out / "G3.kseed"], {})
    runtime_boundary = json.loads((out / "runtime-boundary/runtime-boundary.json").read_text())

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
                  adopted=dict(sourceGraph=adopted_pins, coreStatic=dict(sourceGraph=core_static_pins, image=c0), runnerStackBytes=int(ADOPTED_STACK), generations=adopted_gens, packed=packed,
                               expectedNativeImage=adoption["nativeImageSHA256"]),
                  cases=results, hardening=hardening, runtimeBoundary=runtime_boundary,
                  steps=[dict(name=c["name"], seconds=c["seconds"], **({"reused": c["reused"]} if "reused" in c else
                                                                     dict(ran=True, **({"key": c["key"]} if "key" in c else {}))))
                         for c in run.calls],
                  reuse=dict(read=bool(reuse), store=bool(store), reused=[dict(name=c["name"], **c["reused"]) for c in run.calls if "reused" in c]),
                  cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    (out / "selfhost-bootstrap.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "S2=S3", gens[2]["pin"]["sha256"][:16], "root reproduces" if root_reproduces else "root differs (re-pin to S3)", "adopted G1=G2=G3", len(results), "cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reuse", type=Path, help="content-addressed results to reuse for identical calls; new results are added")
    parser.add_argument("--store", type=Path, help="record content-addressed results without reusing any (full run)")
    parser.add_argument("--reuse-lookup-key", action="store_true", help="print the CI cache lookup key and exit")
    a = parser.parse_args()
    if a.reuse_lookup_key:
        print(lookup_key())
        sys.exit(0)
    assert a.output and not (a.reuse and a.store), "--output is required; --reuse and --store are exclusive"
    main(a.output.resolve(), a.reuse and a.reuse.resolve(), (a.store or a.reuse) and (a.store or a.reuse).resolve())
