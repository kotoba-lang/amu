#!/usr/bin/env python3
"""Observe the bounded native KIR persistent object/relink candidate.

Python stages fixed sources/fixtures and observes native processes. Checking,
CID/SCC production, object encoding/store validation, emission and relinking
execute in Amu native images. Its modules (04-09) are in FULL-MANIFEST since JUN-584, but
this harness is not a whole Seed compiler cache, a trusted image-binding host, or a CI speedup claim.
"""
import argparse
import hashlib
import json
import platform
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRA = ["seed/04-definition-cid.kotoba", "seed/05-definition-graph.kotoba", "seed/05-checked-definition.kotoba",
         "seed/06-definition-groups.kotoba", "seed/07-definition-objects.kotoba",
         "seed/08-definition-object-emitter.kotoba", "seed/09-definition-build.kotoba",
         "seed/tests/native-definition-object-checks.kotoba", "seed/tests/native-definition-build.kotoba"]


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def function(name, body, params="x"):
    return ("{:name " + name + " :params [" + params + "] :param-types [" +
            (":i64" if params else "") + "] :result :i64 :effects #{} :body " + body + "}")


def module(functions):
    return ("{:format :kotoba.kir/v4 :entry main :exports [main] :effects #{} :functions [" +
            " ".join(functions) + "]}\n")


def main(compiler, out, *, mutations=True):
    machine = platform.machine()
    assert platform.system() == "Linux" and machine in ("aarch64", "x86_64")
    compiler = compiler.resolve()
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve()
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    assert paths[-1] == "seed/78-full-entry.kotoba"
    # JUN-584: 04-09 are in FULL-MANIFEST now; add only the test fixtures it does not already carry.
    paths = paths[:-1] + [p for p in EXTRA if p not in paths]
    source = b"\n".join((ROOT / p).read_bytes() for p in paths).decode()
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(out),
               KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000")
    report = dict(schema="amu.native-definition-build.v1", host=[platform.system(), machine],
                  nativeVerdictAuthority=False, productionCompilerClosureChanged=False,
                  productionImageSealBound=False, wholeSeedFrontendQualified=False,
                  wholeCompilerCacheQualified=False, ciPerformanceClaim=False, emulation=False,
                  scope="pure scalar KIR v3/v4, payload-v2 profile6/desugar2, SCC<=8, x86 ELF",
                  compiler=pin(compiler), modules={p: pin(ROOT / p) for p in paths},
                  calls=[], parity=[], mutations=[])

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def call(name, argv, *, code=0, environment=env, exact=True):
        start = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=environment, capture_output=True, timeout=900)
        (out / (name + ".stdout")).write_bytes(p.stdout)
        (out / (name + ".stderr")).write_bytes(p.stderr)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - start,
                   stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(), stderrSHA256=hashlib.sha256(p.stderr).hexdigest())
        report["calls"].append(row)
        save()
        print(json.dumps(row), flush=True)
        if exact:
            assert p.returncode == code, (name, code, p.returncode, p.stdout[-500:], p.stderr[-500:])
        return p

    def build(name, text):
        src = out / (name + ".kotoba")
        src.write_text(text)
        image = out / (name + ".elf")
        target = "aarch64-linux" if machine == "aarch64" else "x86_64-linux"
        call("build-" + name, [compiler, "compile", src, "--target", target, "--output", image, "--format", "static"])
        image.chmod(0o755)
        return image

    producer = build("producer", source)
    seal = pin(producer)["sha256"]  # Observer context only; no trusted production binding claim.
    report["producer"] = pin(producer)
    save()

    def directory(name):
        path = out / name
        path.mkdir(mode=0o700)
        return path

    def invoke(name, text, cache, *, mode="cached", hits=None, code=0, context=seal,
               fuel="1000000", image=producer):
        src, artifact = out / (name + ".kir"), out / (name + ".elf")
        src.write_text(text)
        p = call(name, [image, mode, src, cache, context, artifact, fuel], code=code)
        if code or mode == "controls":
            assert not artifact.exists(), name
            return p
        assert artifact.exists() and not p.stderr, (name, p.stderr)
        if hits is not None:
            assert (f"reused={hits[0]} rebuilt={hits[1]}\n").encode() in p.stdout, (name, p.stdout)
        return artifact

    def execute(name, artifact, expected):
        if machine != "x86_64":
            return  # ARM emits x86 bytes; it does not emulate their execution.
        artifact.chmod(0o755)
        p = call(name + "-execute", [artifact], environment=dict(PATH="/nonexistent"))
        assert not p.stderr and p.stdout == expected.to_bytes(8, "little", signed=True), (name, p.stdout)

    def pair(name, text, cache, hits, expected):
        reference = invoke(name + "-reference", text, cache, mode="reference")
        candidate = invoke(name, text, cache, hits=hits)
        assert reference.read_bytes() == candidate.read_bytes(), name
        execute(name, candidate, expected)
        report["parity"].append(dict(name=name, image=pin(candidate), reused=hits[0], rebuilt=hits[1],
                                     nativeExecution=machine == "x86_64", expectedI64=expected))
        save()
        return candidate

    helper = function("helper", "(if (< x 0) 0 (+ x 2))")
    entry = function("main", "(helper 40)", "")
    base = module([helper, entry])
    cache = directory("cache")
    pair("base-fill", base, cache, (0, 2), 42)
    pair("base-warm", base, cache, (2, 0), 42)
    invoke("native-controls", base, cache, mode="controls")
    pair("rename", module([function("renamed", "(if (< x 0) 0 (+ x 2))"),
                            function("main", "(renamed 40)", "")]), cache, (2, 0), 42)
    pair("reorder", module([entry, helper]), cache, (2, 0), 42)
    pair("unrelated", module([function("unrelated", "(+ x 900)"), entry, helper]), cache, (2, 1), 42)
    pair("leaf-edit", module([function("helper", "(if (< x 0) 0 (+ x 3))"), entry]), cache, (0, 2), 43)
    pair("caller-edit", module([helper, function("main", "(helper 41)", "")]), cache, (1, 1), 43)
    alternate = "0" * 64 if seal != "0" * 64 else "1" * 64
    original = invoke("context-reference", base, cache, mode="reference", context=alternate)
    changed = invoke("context-change", base, cache, hits=(0, 2), context=alternate)
    assert original.read_bytes() == changed.read_bytes()
    execute("context-change", changed, 42)

    dup = directory("duplicates")
    a, b = function("a", "(+ x 2)"), function("b", "(+ x 2)")
    duplicate_b = module([a, b, function("main", "(b 40)", "")])
    pair("duplicate-fill", duplicate_b, dup, (0, 3), 42)
    pair("duplicate-warm", duplicate_b, dup, (3, 0), 42)
    pair("duplicate-call-edit", module([a, b, function("main", "(a 40)", "")]), dup, (2, 1), 42)
    pair("duplicate-reorder", module([b, a, function("main", "(a 40)", "")]), dup, (3, 0), 42)

    cyc = directory("cycle")
    ca, cb = function("a", "(if (= x 0) 40 (b (- x 1)))"), function("b", "(if (= x 0) 41 (a (- x 1)))")
    cm, unused = function("main", "(a 3)", ""), function("unused", "(+ x 9)")
    cycle = module([ca, cb, cm, unused])
    pair("cycle-fill", cycle, cyc, (0, 3), 41)
    pair("cycle-warm", cycle, cyc, (3, 0), 41)
    pair("cycle-reorder", module([unused, cm, cb, ca]), cyc, (3, 0), 41)
    pair("cycle-rename", module([function("north", "(if (= x 0) 40 (south (- x 1)))"),
                                 function("south", "(if (= x 0) 41 (north (- x 1)))"),
                                 function("main", "(north 3)", ""), unused]), cyc, (3, 0), 41)
    pair("cycle-edit", module([ca, function("b", "(if (= x 0) 42 (a (- x 1)))"), cm, unused]), cyc, (1, 2), 42)
    large = directory("scc8")
    ring = [function("f" + str(i), "(if (= x 0) " + str(8 - i) + " (f" + str((i - 1) % 8) + " (- x 1)))") for i in range(8)]
    ringmain = function("main", "(f0 4)", "")
    pair("scc8-fill", module(ring + [ringmain, unused]), large, (0, 3), 4)
    pair("scc8-warm", module(ring + [ringmain, unused]), large, (3, 0), 4)
    ring[4] = function("f4", "(if (= x 0) 99 (f3 (- x 1)))")
    pair("scc8-edit", module(ring + [ringmain, unused]), large, (1, 2), 99)

    snapshot = {p.name: p.read_bytes() for p in cache.iterdir()}
    invoke("wrong-type", module([helper, function("main", "true", "")]), cache, code=1)
    invoke("effects", base.replace(":effects #{}", ":effects #{:fs/app-data}", 1), cache, code=1)
    invoke("forged-checked", base[:-2] + " :checked true}\n", cache, code=1)
    six = ("{:name six :params [a b c d e f] :param-types [:i64 :i64 :i64 :i64 :i64 :i64] "
           ":result :i64 :effects #{} :body (+ a f)}")
    invoke("fresh-target-refusal", module([six, function("main", "(six 1 2 3 4 5 6)", "")]), cache, code=1)
    invoke("fuel-zero", base, cache, code=2, fuel="0")
    assert snapshot == {p.name: p.read_bytes() for p in cache.iterdir()}
    exhausted = invoke("fuel-exhaustion", cycle, cyc, hits=(3, 0), fuel="1")
    if machine == "x86_64":
        exhausted.chmod(0o755)
        p = call("fuel-exhaustion-execute", [exhausted], code=-signal.SIGILL, environment=dict(PATH="/nonexistent"))
        assert not p.stdout and not p.stderr
    missing = directory("missing")
    pair("missing-fill", base, missing, (0, 2), 42)
    next(missing.glob("*.kdo")).unlink()
    pair("missing-rebuild", base, missing, (1, 1), 42)
    damaged = {}
    for name, kind in [("corrupt", "body"), ("checksum", "checksum"), ("permissions", "mode"), ("symlink", "symlink")]:
        d = directory(name)
        pair(name + "-fill", base, d, (0, 2), 42)
        target = next(d.glob("*.kdo"))
        target.chmod(0o600)
        data = target.read_bytes()
        if kind in ("body", "checksum"):
            pos = len(data) - 1 if kind == "body" else 70
            target.write_bytes(data[:pos] + (b"0" if data[pos:pos+1] != b"0" else b"1") + data[pos+1:])
            target.chmod(0o400)
        elif kind == "symlink":
            real = out / "symlink-real.kdo"
            real.write_bytes(data)
            real.chmod(0o400)
            target.unlink()
            target.symlink_to(real)
        before = target.read_bytes()
        invoke(name + "-refusal", base, d, code=1)
        assert target.read_bytes() == before
        damaged[name] = d
    public = directory("public-directory")
    public.chmod(0o755)
    invoke("public-directory-refusal", base, public, code=1)
    assert not list(public.iterdir())

    if mutations:
        controls = [
            ("checksum", '(= (sh-text body) (string-substring record 70 134))', 'true', "checksum"),
            ("permissions", '(= (dco-field metadata 0) (if directory "448" "256"))', 'true', "permissions"),
            ("placeholder", '(dco-zero? code offset width)', 'true', "controls"),
            ("binding", '(= (dcn-binding A R f) binding)',
             '(= (string-substring (dcn-binding A R f) 0 59) (string-substring binding 0 59))', "binding"),
        ]
        for name, old, new, scenario in controls:
            assert source.count(old) == 1, name
            mutant = build("mutant-" + name, source.replace(old, new))
            # Explicitly reuse fixture context to reach the internal guard.
            # Production image binding remains an OPEN gate for this prototype.
            src = out / ("mutant-" + name + ".kir")
            src.write_text(duplicate_b if scenario == "binding" else base)
            artifact = out / ("mutant-" + name + "-output.elf")
            d = dup if scenario == "binding" else damaged.get(scenario, cache)
            mode = "controls" if scenario == "controls" else "cached"
            p = call("detect-" + name, [mutant, mode, src, d, seal, artifact, "1000000"], exact=False)
            if scenario == "controls":
                detected = p.returncode == 1 and not artifact.exists()
            else:
                assert p.returncode == 0 and artifact.exists(), (name, p.stderr)
                detected = (artifact.read_bytes() != (out / "duplicate-fill-reference.elf").read_bytes()
                            if scenario == "binding" else b"reused=2 rebuilt=0" in p.stdout)
            report["mutations"].append(dict(name=name, built=True, executed=True, detected=detected, image=pin(mutant)))
            save()
            assert detected, name
    assert not list(out.glob("*/kotoba-output-*")), "managed staging leak"
    for d in (cache, dup, cyc, large, missing):
        assert all(p.stat().st_mode & 0o777 == 0o400 for p in d.glob("*.kdo"))
    report["status"] = "PASS_NATIVE_DEFINITION_OBJECT_BUILD"
    report["nativeEmittedExecution"] = machine == "x86_64"
    save()
    print(report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-mutations", action="store_true")
    args = parser.parse_args()
    main(args.compiler, args.output, mutations=not args.no_mutations)
