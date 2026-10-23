#!/usr/bin/env python3
"""Qualify the loaderless x86_64 artifacts on a native x86_64 Linux kernel.

Input (--bootstrap) is a selfhost-bootstrap.py output produced on arm64 Linux
from the pinned root: S-x86_64.elf (x86_64 static compiler), R-x86_64.elf
(KX64V1 runner) and selfhost-unity.kotoba. No C compiler or loader, no
emulation. Records, natively:

1. X2 = S-x86_64 compiling the closure for x86_64 (cross-built = self-built),
   X3 = X2 again (fixed point);
2. the runtime cases (seed/static-cases.json) as x86_64 static images;
3. hardening: seccomp enforced (default required; a filtered call traps
   SIGSYS), cpu / wall / stack limits;
4. the KX64V1 runner: X2's kx64-v1 compiler payload G1 rebuilds itself
   through R-x86_64 (G1 = G2 = G3);
5. the scalar ELF suite and the aiueos object checks with X2;
6. in every tier, ADR 0371's checks that need a native x86_64 kernel, with
   X2 (ADR0371 below): the static launcher (check-static-launcher.py,
   --format launcher, step 4).

--reuse DIR / --store DIR: content-addressed reuse as in selfhost-bootstrap.py
(scripts/seed/content_reuse.py). Only calls made through reuse.run_cached may
be stood in for, and only on an exact key; the receipt's reuse lists them.
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from content_reuse import Runs  # noqa: E402 (scripts/seed)

ROOT = Path(__file__).resolve().parents[2]
# ADR 0371's native checks: every tier (a minute or two each)
ADR0371 = [("check-static-launcher.py", [])]


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main(boot, out, tier="main", reuse_dir=None, store_dir=None):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "run on native x86_64 Linux"
    out.mkdir(parents=True, exist_ok=False)
    (out / "raw").mkdir()
    calls = []
    # the calls content-addressed reuse may stand in for (exact key only)
    reuse = Runs(out, reuse_dir, store_dir)

    def run(name, argv, env, ok=True, timeout=3600):
        r = subprocess.run(list(map(str, argv)), cwd=out, env={"PATH": "/usr/bin:/bin", **env}, capture_output=True, timeout=timeout)
        (out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        calls.append(dict(name=name, exit=r.returncode))
        if ok:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr[-400:])
        return r

    scope = {"KEXE_CAP_RESOURCES_35": str(out)}
    for name in ("S-x86_64.elf", "R-x86_64.elf", "selfhost-unity.kotoba"):
        shutil.copy2(boot / name, out / name)
    (out / "S-x86_64.elf").chmod(0o755)
    (out / "R-x86_64.elf").chmod(0o755)
    source = out / "selfhost-unity.kotoba"
    paths = [p for p in (ROOT / "seed/X86_64-LINUX-SELFHOST-MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
    assert source.read_bytes() == b"".join((ROOT / p).read_bytes() + b"\n" for p in paths), "source graph differs from this checkout"

    def compile_(prod, src, dst, fmt, name, target="x86_64-linux"):
        run(name, [prod, "compile", src, "--target", target, "--output", dst, "--format", fmt], scope)
        dst.chmod(0o755)
        return pin(dst)

    # 1. fixed point on x86_64
    s_cross = pin(out / "S-x86_64.elf")
    x2 = compile_(out / "S-x86_64.elf", source, out / "X2.elf", "static", "X2")
    assert s_cross == x2, "x86_64 static compiler: cross-built = self-built"
    x3 = None
    if tier != "pr":
        x3 = compile_(out / "X2.elf", source, out / "X3.elf", "static", "X3")
        assert x2 == x3, "x86_64 static fixed point"
    X = out / "X2.elf"

    run("runtime-boundary", [sys.executable, ROOT / "scripts/seed/check-runtime-boundary.py",
                             "--compiler", X, "--output", out / "runtime-boundary"], {})
    runtime_boundary = json.loads((out / "runtime-boundary/runtime-boundary.json").read_text())

    # 2. runtime cases
    results = []
    for case in json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]:
        src = out / f"case-{case['name']}.kotoba"
        src.write_text(case["source"])
        compile_(X, src, out / f"case-{case['name']}.elf", "static", f"case-{case['name']}-compile")
        r = run(f"case-{case['name']}", [out / f"case-{case['name']}.elf"],
                {"KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "1000000", "KEXE_ALLOW": "-"}, ok=False)
        fuel = re.search(rb":remaining ([0-9]+)", r.stdout)
        observed = dict(exit=r.returncode, remainingFuel=int(fuel[1]) if fuel else None)
        assert observed == case["reference"], (case["name"], observed, case["reference"])
        if not case["trap"]:
            assert int(re.search(rb":result (-?[0-9]+)", r.stdout)[1]) == case["result"]
        results.append(dict(name=case["name"], **observed))

    # 3. hardening, natively on x86_64
    probes = {"value": "(defn main [] :i64 42)",
              "spin": "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))",
              "deep": "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"}
    for name, body in probes.items():
        src = out / f"probe-{name}.kotoba"
        src.write_text(f"(ns probe-{name} (:export [main]))\n{body}\n")
        compile_(X, src, out / f"probe-{name}.elf", "static", f"probe-{name}-compile")

    def observe(name, image, env):
        r = run("probe-" + name, [out / f"probe-{image}.elf"], dict(KEXE_STRUCTURED_REPORT="1", **env), ok=False)
        return dict(exit=r.returncode, stderr=r.stderr.decode(errors="replace").strip())
    hardening = dict(seccompDefault=observe("seccomp-default", "value", {}),
                     sandboxProbe=observe("sandbox-probe", "value", dict(KEXE_SANDBOX_PROBE="1")),
                     cpuSeconds1=observe("cpu", "spin", dict(KEXE_CPU_SECONDS="1")),
                     wallSeconds3=observe("wall", "spin", dict(KEXE_WALL_SECONDS="3")),
                     stack1MiB=observe("stack", "deep", {}))
    assert hardening["seccompDefault"]["exit"] == 0, "seccomp must install on this kernel"
    assert hardening["sandboxProbe"]["exit"] == 120 and "SIGSYS" in hardening["sandboxProbe"]["stderr"]
    assert hardening["cpuSeconds1"]["exit"] == 120 and "SIGXCPU" in hardening["cpuSeconds1"]["stderr"]
    assert hardening["wallSeconds3"]["exit"] == 120 and "SIGALRM" in hardening["wallSeconds3"]["stderr"]
    assert hardening["stack1MiB"]["exit"] == 120 and "SIGSEGV" in hardening["stack1MiB"]["stderr"]

    # every tier: ADR 0371's checks; main and full tiers: the KX64V1 runner and the suites
    gens, suites = [], run_suites(out, X, ADR0371)
    if tier != "pr":
        gens, more = kx64_and_suites(run, out, X, source, scope)
        suites.update(more)

    # full tier: the adopted compiler core as an x86_64 static image (JUN-330):
    # X2 builds seed/CORE-STATIC-MANIFEST as X0; X0 rebuilds seed/MANIFEST (the
    # core targets aarch64-macos) to the adoption image (~17 min natively)
    core_x86 = None
    if tier == "full":
        import time
        adoption = json.loads((ROOT / json.loads((ROOT / "seed/compiler-core.json").read_text())["adoptionReceipt"]).read_text())

        def unity_of(manifest, dst):
            ps = [p for p in (ROOT / manifest).read_text().splitlines() if p and not p.startswith("#")]
            dst.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in ps))
            return pin(dst)
        core_static, adopted = out / "core-static-unity.kotoba", out / "adopted-unity.kotoba"
        unity_of("seed/CORE-STATIC-MANIFEST", core_static)
        assert unity_of("seed/MANIFEST", adopted)["sha256"] == adoption["sourceUnitySHA256"], "adopted source drift"
        senv = dict(scope, KEXE_STACK_BYTES="8388608")
        run("X0", [X, "compile", core_static, "--target", "x86_64-linux", "--output", out / "X0.elf", "--format", "static"], senv)
        (out / "X0.elf").chmod(0o755)
        t0 = time.monotonic()
        run("X0-core", [out / "X0.elf", "compile", adopted, "--target", "aarch64-macos", "--output", out / "X0-core.kseed"], senv, timeout=10800)
        seconds = round(time.monotonic() - t0, 1)
        run("X0-extract", [out / "X0.elf", "extract-native", out / "X0-core.kseed", "--symbol", "main", "--output", out / "X0-core.bin"], senv)
        assert pin(out / "X0-core.bin")["sha256"] == adoption["nativeImageSHA256"], "x86_64 core output mismatch"
        core_x86 = dict(X0=pin(out / "X0.elf"), container=pin(out / "X0-core.kseed"), native=pin(out / "X0-core.bin"),
                        coreCompileSeconds=seconds)

    report = dict(status="PASS_NATIVE_X86_64_LOADERLESS", tier=tier, host=[platform.system(), platform.machine(), platform.release()],
                  nativeX86_64Kernel=True, emulation=False, cCompilerOrLoader=False,
                  compiler=dict(crossBuiltOnArm64=s_cross, X2=x2, X3=x3), cases=results, hardening=hardening,
                  runtimeBoundary=runtime_boundary, coreOnX86_64=core_x86,
                  kx64Runner=dict(runner=pin(out / "R-x86_64.elf"), generations=gens), suites=suites,
                  reuse=dict(read=bool(reuse_dir), store=bool(store_dir), steps=[{k: c[k] for k in ("name", "seconds", "key", "reused") if k in c}
                                                                                for c in reuse.calls]),
                  bootstrapReceipt=json.loads((boot / "selfhost-bootstrap.json").read_text())["root"]["image"])
    (out / "x86_64-native.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], tier, "X2", x2["sha256"][:16], len(results), "cases", flush=True)


def kx64_and_suites(run, out, X, source, scope):
    # 4. the KX64V1 runner: the kx64-v1 compiler payload rebuilds itself
    run("G1-kx64", [X, "compile", source, "--target", "x86_64-linux", "--output", out / "G1.kx64", "--format", "kx64-v1"], scope)

    def payload(container, dst):
        header, body = container.read_bytes().split(b"\n\n", 1)
        assert re.fullmatch(rb"KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0", header) and body[0] == 0xE9
        dst.write_bytes(body)
        return pin(dst)
    gens = [dict(native=payload(out / "G1.kx64", out / "G1.bin"), container=pin(out / "G1.kx64"))]
    producer = out / "G1.bin"
    renv = dict(scope, KEXE_COMMAND="1")
    for g in (2, 3):
        run(f"G{g}-kx64", [out / "R-x86_64.elf", producer, 0, 0, "x86_64", "35,37,38,39", "--", "compile", source,
                           "--target", "x86_64-linux", "--output", out / f"G{g}.kx64", "--format", "kx64-v1"], renv)
        gens.append(dict(native=payload(out / f"G{g}.kx64", out / f"G{g}.bin"), container=pin(out / f"G{g}.kx64")))
        producer = out / f"G{g}.bin"
    assert gens[0] == gens[1] == gens[2], "KX64V1 runner fixed point"

    # 5. scalar ELF suite and aiueos object checks with X2
    return gens, run_suites(out, X, [("check-x86_64-scalar.py", []), ("check-x86_64-aiueos-object.py", [])])


def run_suites(out, X, scripts):
    suites = {}
    for script, args in scripts:
        dst = out / script.replace(".py", "")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/seed" / script), "--compiler", str(X), "--output", str(dst), *args],
                           capture_output=True, timeout=3600)
        (out / "raw" / (script + ".log")).write_bytes(r.stdout + r.stderr)
        assert r.returncode == 0, (script, r.stdout[-400:], r.stderr[-400:])
        suites[script] = r.stdout.decode().strip().splitlines()[-1]
    return suites


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path, required=True, help="selfhost-bootstrap.py output (from arm64 Linux)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tier", choices=("pr", "main", "full"), default="full")
    parser.add_argument("--reuse", type=Path, help="content-addressed results to reuse for identical calls; new results are added")
    parser.add_argument("--store", type=Path, help="record content-addressed results without reusing any (full run)")
    args = parser.parse_args()
    assert not (args.reuse and args.store), "--reuse and --store are exclusive"
    store = args.store or args.reuse
    main(args.bootstrap.resolve(), args.output.resolve(), args.tier, args.reuse and args.reuse.resolve(), store and store.resolve())
