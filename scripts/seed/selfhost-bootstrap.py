#!/usr/bin/env python3
"""Loaderless Amu selfhost bootstrap on arm64 Linux. No C compiler or C loader.

The pinned root (seed/bootstrap/aarch64-linux-static-root.elf) is F, the
combined compiler (seed/FULL-MANIFEST: the adopted core plus the Linux
targets) packed as a static image. Tiers (--tier) say how much is re-derived;
every check runs in at least one tier:

pr    1. F rebuilds itself: FULL-MANIFEST -> container, packed -> F' (= root,
         else F' rebuilds itself to the same image and is re-pinned);
      2. F's Linux targets: aarch64 runner, x86_64 static compiler (the Linux
         selfhost closure), x86_64 KX64V1 runner;
      3. F's core route: seed/MANIFEST -> G1 = the adoption receipt's image;
         a packed payload whose main takes arguments is refused (E7105); a
         diagnostic with a source span is named (E2101), not a trap;
      4. the runtime boundary corpus, the runtime cases
         (seed/static-cases.json), hardening and capabilities, all with F.
main  + G1, G2 through the aarch64 runner give G2, G3 (= G1); S3 packs G3 as
        P, which rebuilds the core; the Linux selfhost closure S built by F
        rebuilds itself (S = S').
full  + the deep provenance from source: S builds the core as a static image
        C0 (seed/CORE-STATIC-MANIFEST); C0 compiles seed/MANIFEST to the
        adoption image, and seed/CORE-STATIC-MANIFEST to Kw; S packs Kw as Pw,
        and Pw compiles FULL-MANIFEST to F's own container.

Content-addressed reuse (--reuse DIR / --store DIR, scripts/seed/content_reuse.py)
may stand in only for C0's compile of the core, and only on an exact key. The
receipt's steps and reuse say what ran and what was reused, with the keys.

Python only orchestrates processes and hashes. Run it on arm64 Linux, for
example: podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT
python:3.12-alpine python3 REPO/scripts/seed/selfhost-bootstrap.py --output OUT --tier pr
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
from content_reuse import Runs, pin  # noqa: E402 (scripts/seed)
ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
FULL = "seed/FULL-MANIFEST"
TIERS = ("pr", "main", "full")
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


def unity(manifest, dst):
    paths = [p for p in (ROOT / manifest).read_text().splitlines() if p and not p.startswith("#")]
    dst.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in paths))
    return {p: pin(ROOT / p) for p in [manifest, *paths]}


def main(out, tier, reuse=None, store=None):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    level = TIERS.index(tier)
    out.mkdir(parents=True, exist_ok=False)
    run = Runs(out, reuse, store)
    scope = {"KEXE_CAP_RESOURCES_35": str(out)}
    senv = dict(scope, KEXE_STACK_BYTES=ADOPTED_STACK)
    root_receipt = json.loads((ROOT / ROOT_RECEIPT).read_text())
    assert pin(ROOT / ROOT_IMAGE) == root_receipt["image"], "pinned root image mismatch"
    (out / "root.elf").write_bytes((ROOT / ROOT_IMAGE).read_bytes())
    (out / "root.elf").chmod(0o755)
    (out / "runner.kotoba").write_bytes((ROOT / RUNNER_SRC).read_bytes())
    runner = out / "runner.kotoba"
    full_src, source, adopted_src = out / "full-unity.kotoba", out / "selfhost-unity.kotoba", out / "adopted-unity.kotoba"
    full_pins, source_pins, adopted_pins = unity(FULL, full_src), unity(SELFHOST, source), unity(ADOPTED, adopted_src)
    lines = lambda m: [p for p in (ROOT / m).read_text().splitlines() if p and not p.startswith("#")]
    core = [p.replace(NS, NS_STATIC) for p in lines(ADOPTED) if p != "seed/99-entry.kotoba"]
    assert lines(FULL)[:len(core)] == core, "FULL-MANIFEST's core section differs from seed/MANIFEST"
    adoption = json.loads((ROOT / ADOPTION).read_text())
    assert pin(adopted_src)["sha256"] == adoption["sourceUnitySHA256"], "adopted source drift"

    def compile_(prod, src, dst, target, fmt, name, env=None):
        run.run(name, [prod, "compile", src, "--target", target, "--output", dst] + (["--format", fmt] if fmt else []), env or senv)
        if fmt:
            dst.chmod(0o755)
        return pin(dst)

    def pack(prod, kseed, dst, name):
        run.run(name, [prod, "compile", runner, "--target", "aarch64-linux", "--output", dst, "--format", "packed", "--payload", kseed], senv)
        dst.chmod(0o755)
        return pin(dst)

    # 1. F rebuilds itself
    gens = [dict(name="F1", container=compile_(out / "root.elf", full_src, out / "F1.kseed", "aarch64-macos", None, "F1-compile"),
                 image=pack(out / "root.elf", out / "F1.kseed", out / "F1.elf", "F1-pack"))]
    root_reproduces = gens[0]["image"] == pin(ROOT / ROOT_IMAGE)
    if not root_reproduces:
        # a source change: F1 is this source's compiler; it must rebuild itself
        gens.append(dict(name="F2", container=compile_(out / "F1.elf", full_src, out / "F2.kseed", "aarch64-macos", None, "F2-compile"),
                         image=pack(out / "F1.elf", out / "F2.kseed", out / "F2.elf", "F2-pack")))
        assert gens[1] == dict(gens[0], name="F2"), "combined compiler fixed point mismatch"
    F = out / "F1.elf"

    # 2. F's Linux targets
    built = dict(
        aarch64Runner=compile_(F, runner, out / "R-aarch64.elf", "aarch64-linux", "runner", "R-aarch64", scope),
        x86_64Compiler=compile_(F, source, out / "S-x86_64.elf", "x86_64-linux", "static", "S-x86_64", scope),
        x86_64Runner=compile_(F, runner, out / "R-x86_64.elf", "x86_64-linux", "kx64-runner", "R-x86_64", scope))

    # 3. F's core route, the packed refusal and a named diagnostic
    compile_(F, adopted_src, out / "G1.kseed", "aarch64-macos", None, "G1-compile")
    run.run("G1-extract", [F, "extract-native", out / "G1.kseed", "--symbol", "main", "--output", out / "G1.bin"], senv)
    assert pin(out / "G1.bin")["sha256"] == adoption["nativeImageSHA256"], "F's core route differs from the adoption image"
    adopted_gens = [dict(generation=1, producedBy="F", native=pin(out / "G1.bin"), container=pin(out / "G1.kseed"))]
    (out / "arity1.kotoba").write_text("(ns arity1 (:export [main]))\n(defn main [x :i64] :i64 x)\n")
    compile_(F, out / "arity1.kotoba", out / "arity1.kseed", "aarch64-macos", None, "arity1-compile")
    r = run.run("arity1-pack", [F, "compile", runner, "--target", "aarch64-linux", "--output", out / "arity1.elf",
                                "--format", "packed", "--payload", out / "arity1.kseed"], senv, success=False)
    assert r.returncode == 1 and b"E7105" in r.stderr and not (out / "arity1.elf").exists(), "packed arity refusal"
    arity_refusal = dict(exit=r.returncode, stderr=r.stderr.decode().strip())
    # JUN-334: a diagnostic with a source span reads the whole file (no RANGE request, which the runtime refuses)
    (out / "undefined.kotoba").write_text("(ns undefined (:export [main]))\n(defn main [] :i64 (nope-fn))\n")
    r = run.run("diagnostic-span", [F, "check", out / "undefined.kotoba"], senv, success=False)
    assert r.returncode == 1 and b"E2101 unknown or unsupported form 'nope-fn'" in r.stderr, ("named diagnostic", r.returncode, r.stderr[-300:])
    diagnostic = dict(exit=r.returncode, stderr=r.stderr.decode().strip())

    # JUN-325: the shared call/function-value boundary corpus, including the
    # packed route, through F
    run.run("runtime-boundary", [sys.executable, ROOT / "scripts/seed/check-runtime-boundary.py",
                                 "--compiler", F, "--output", out / "runtime-boundary",
                                 "--payload", out / "G1.kseed"], {})
    runtime_boundary = json.loads((out / "runtime-boundary/runtime-boundary.json").read_text())

    # 4. runtime cases as static images against the pinned loader results
    results = []
    for case in json.loads((ROOT / CASES).read_text())["cases"]:
        src = out / f"case-{case['name']}.kotoba"
        src.write_text(case["source"])
        compile_(F, src, out / f"case-{case['name']}.elf", "aarch64-linux", "static", f"case-{case['name']}-compile", scope)
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

    # hardening, natively
    probes = {"value": "(defn main [] :i64 42)",
              "spin": "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))",
              "deep": "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"}
    for name, body in probes.items():
        src = out / f"probe-{name}.kotoba"
        src.write_text(f"(ns probe-{name} (:export [main]))\n{body}\n")
        compile_(F, src, out / f"probe-{name}.elf", "aarch64-linux", "static", f"probe-{name}-compile", scope)

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

    # capabilities: wire 3 and multiple KEXE_CAP_RESOURCES_35 roots
    roots = [out / "cap-missing", out / "cap-a", out / "cap-b"]
    for d in roots[1:]:
        d.mkdir()
    vectors = {"abc": None, "": None, "x" * 200: None}
    body = "\n".join(f'(if (string=? (typed-cap-call :hash/sha256 :string :string "{t}") "{hashlib.sha256(t.encode()).hexdigest()}") {1 << i} 0)'
                     for i, t in enumerate(vectors))
    (roots[2] / "hash.kotoba").write_text(f"(ns hash-check (:export [main]))\n(defn main [] :i64 (+ {body}))\n")
    cap_env = {"KEXE_CAP_RESOURCES_35": ":".join(map(str, roots))}
    run.run("cap-compile", [F, "compile", roots[2] / "hash.kotoba", "--target", "aarch64-linux", "--output", roots[2] / "hash.elf",
                            "--format", "static"], cap_env)
    (roots[2] / "hash.elf").chmod(0o755)
    granted = run.run("cap-hash-granted", [roots[2] / "hash.elf"], {"KEXE_ALLOW": "3"}, success=False)
    refused = run.run("cap-hash-refused", [roots[2] / "hash.elf"], {"KEXE_ALLOW": "37"}, success=False)
    outside = run.run("cap-outside-roots", [F, "compile", roots[2] / "hash.kotoba", "--target", "aarch64-linux",
                                            "--output", roots[1] / "x.elf", "--format", "static"],
                      {"KEXE_CAP_RESOURCES_35": str(roots[1])}, success=False)
    assert granted.returncode == 7, ("sha256 vectors", granted.returncode)
    assert refused.returncode == 120 and b"SIGILL" in refused.stderr
    assert outside.returncode != 0 and not (roots[1] / "x.elf").exists()
    capabilities = dict(sha256Vectors=len(vectors), granted=granted.returncode, refused=refused.returncode,
                        scopeRoots=len(roots), sourceUnderRoot=3, outsideRootsExit=outside.returncode)

    # main: the runner, the packed core and the Linux selfhost closure
    packed = closure = None
    if level >= 1:
        renv = dict(scope, KEXE_COMMAND="1", KEXE_STACK_BYTES=ADOPTED_STACK)
        payload = out / "G1.bin"
        for g in (2, 3):
            prefix = [out / "R-aarch64.elf", payload, 0, 0, "aarch64", "35,37,38,39", "--"]
            container, native = out / f"G{g}.kseed", out / f"G{g}.bin"
            run.run(f"G{g}-compile", prefix + ["compile", adopted_src, "--target", "aarch64-macos", "--output", container], renv)
            run.run(f"G{g}-extract", prefix + ["extract-native", container, "--symbol", "main", "--output", native], renv)
            assert pin(native)["sha256"] == adoption["nativeImageSHA256"], "adopted fixed point mismatch (runner)"
            adopted_gens.append(dict(generation=g, producedBy="runner", native=pin(native), container=pin(container)))
            payload = native
        P = out / "P-aarch64.elf"
        pack(F, out / "G3.kseed", P, "P-pack")
        compile_(P, adopted_src, out / "P.kseed", "aarch64-macos", None, "P-compile")
        run.run("P-extract", [P, "extract-native", out / "P.kseed", "--symbol", "main", "--output", out / "P.bin"], senv)
        assert pin(out / "P.bin")["sha256"] == adoption["nativeImageSHA256"], "packed compiler output mismatch"
        assert pin(out / "P.kseed") == adopted_gens[-1]["container"], "packed compiler container mismatch"
        packed = dict(image=pin(P), container=pin(out / "P.kseed"), native=pin(out / "P.bin"))
        s1 = compile_(F, source, out / "S.elf", "aarch64-linux", "static", "S", scope)
        s2 = compile_(out / "S.elf", source, out / "S2.elf", "aarch64-linux", "static", "S2", scope)
        assert s1 == s2, "Linux selfhost closure fixed point mismatch"
        closure = dict(S=s1)

    # full: the deep provenance of the core from source
    provenance = None
    if level >= 2:
        ns, ns_static = ((ROOT / p).read_bytes() for p in (NS, NS_STATIC))
        strip = lambda b: STATIC_CAPACITIES.sub(b"", b"".join(l for l in b.splitlines(True) if not l.startswith(b";; seed/00-ns-static")
                                                             and not l.startswith(b";; CORE-STATIC") and not l.startswith(b";; (CODE, FIX")))
        assert strip(ns) == strip(ns_static), "00-ns-static differs from 00-ns beyond the static capacities"
        S = out / "S.elf"
        core_static_src = out / "core-static-unity.kotoba"
        core_static_pins = unity(CORE_STATIC, core_static_src)
        c0 = compile_(S, core_static_src, out / "C0.elf", "aarch64-linux", "static", "C0")
        # C0's code is unoptimized: each of its compiles of the core takes ~30 min
        # on an Apple-silicon VM and over an hour on a hosted arm64 runner. Only
        # these calls may be reused, on an exact key (--reuse).
        run.run_cached("C0-core", [out / "C0.elf", "compile", adopted_src, "--target", "aarch64-macos", "--output", out / "C0-core.kseed"],
                       senv, [out / "C0-core.kseed"], timeout=10800)
        run.run_cached("C0-extract", [out / "C0.elf", "extract-native", out / "C0-core.kseed", "--symbol", "main", "--output", out / "C0-core.bin"],
                       senv, [out / "C0-core.bin"], timeout=3600)
        assert pin(out / "C0-core.bin")["sha256"] == adoption["nativeImageSHA256"], "C0's core differs from the adoption image"
        run.run_cached("C0-Kw", [out / "C0.elf", "compile", core_static_src, "--target", "aarch64-macos", "--output", out / "Kw.kseed"],
                       senv, [out / "Kw.kseed"], timeout=10800)
        pw = pack(S, out / "Kw.kseed", out / "Pw.elf", "Pw-pack")
        compile_(out / "Pw.elf", full_src, out / "Pw-F.kseed", "aarch64-macos", None, "Pw-F")
        assert pin(out / "Pw-F.kseed") == gens[0]["container"], "F from the C0 lineage differs from F"
        provenance = dict(coreStatic=dict(sourceGraph=core_static_pins, C0=c0), core=pin(out / "C0-core.bin"),
                          Kw=pin(out / "Kw.kseed"), Pw=pw, F=pin(out / "Pw-F.kseed"))

    report = dict(status="PASS_LOADERLESS_SELFHOST_BOOTSTRAP", tier=tier, capabilities=capabilities,
                  host=[platform.system(), platform.machine(), platform.release()],
                  root=dict(image=pin(ROOT / ROOT_IMAGE), receipt=root_receipt),
                  sourceGraph=dict(full=full_pins, selfhost=source_pins), generations=gens, rootReproduces=root_reproduces,
                  built=built,
                  adopted=dict(sourceGraph=adopted_pins, runnerStackBytes=int(ADOPTED_STACK), generations=adopted_gens, packed=packed,
                               arityRefusal=arity_refusal, expectedNativeImage=adoption["nativeImageSHA256"]),
                  diagnostic=diagnostic, closure=closure, provenance=provenance,
                  cases=results, hardening=hardening, runtimeBoundary=runtime_boundary,
                  steps=[dict(name=c["name"], seconds=c["seconds"], **({"reused": c["reused"]} if "reused" in c else
                                                                     dict(ran=True, **({"key": c["key"]} if "key" in c else {}))))
                         for c in run.calls],
                  reuse=dict(read=bool(reuse), store=bool(store), reused=[dict(name=c["name"], **c["reused"]) for c in run.calls if "reused" in c]),
                  cCompilerOrLoader=False, JVMNodeOrGraalFallback=False, emulation=False)
    (out / "selfhost-bootstrap.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], tier, "F", gens[-1]["image"]["sha256"][:16], "root reproduces" if root_reproduces else "root differs (re-pin to F1)",
          "adoption image", len(results), "cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tier", choices=TIERS, default="full", help="pr, main or full (default: everything)")
    parser.add_argument("--reuse", type=Path, help="content-addressed results to reuse for identical calls; new results are added")
    parser.add_argument("--store", type=Path, help="record content-addressed results without reusing any (full run)")
    a = parser.parse_args()
    assert not (a.reuse and a.store), "--reuse and --store are exclusive"
    main(a.output.resolve(), a.tier, a.reuse and a.reuse.resolve(), (a.store or a.reuse) and (a.store or a.reuse).resolve())
