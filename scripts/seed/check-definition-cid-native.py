#!/usr/bin/env python3
"""Stage fixed identity vectors and observe an Amu-built native validator.

The native module owns CBOR/normalized-payload checks, SHA-256 and CIDv1.
Python neither canonicalizes definitions nor emits native formats. This is
identity codec qualification, not checked-frontend, SCC or cache qualification.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ["seed/03-source-sha256.kotoba", "seed/04-definition-cid.kotoba",
           "seed/tests/native-definition-cid.kotoba"]


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    out.mkdir(parents=True, exist_ok=False)
    vectors_path = ROOT / "seed/tests/definition-cid-vectors.json"
    vectors = json.loads(vectors_path.read_text())
    assert len(vectors["vectors"]) == 10
    source = out / "definition-cid.kotoba"
    source.write_bytes(b"(ns seed.definition-cid (:export [main]))\n" +
                       b"\n".join((ROOT / p).read_bytes() for p in MODULES))
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    image = out / "definition-cid.elf"
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_FUEL="1000000000")
    report = dict(schema="amu.native-definition-cid-codec.v1", host=[platform.system(), platform.machine()],
                  compiler=pin(compiler), modules={p: pin(ROOT / p) for p in MODULES},
                  frozenVectors=pin(vectors_path), source=pin(source), calls=[],
                  nativeVerdictAuthority=False, checkedFrontendQualified=False, sccQualified=False,
                  persistentBuildQualified=False, admittedTextProfile="ASCII", emulation=False)

    def run(name, argv, process_env, result=None, cid=None, canonical=None, unexpected_cid=False):
        started = time.monotonic()
        p = subprocess.run(list(map(str, argv)), env=process_env, cwd=out, capture_output=True, timeout=300)
        for stream, raw in [("stdout", p.stdout), ("stderr", p.stderr)]:
            (out / (name + "." + stream)).write_bytes(raw)
        row = dict(name=name, exit=p.returncode, seconds=time.monotonic() - started,
                   stdoutSHA256=hashlib.sha256(p.stdout).hexdigest(), stderrSHA256=hashlib.sha256(p.stderr).hexdigest())
        report["calls"].append(row)
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        assert p.returncode == 0 and not p.stderr, (name, p.returncode, p.stderr[-800:])
        if result is not None:
            assert re.search(rb":result " + str(result).encode() + rb"\b", p.stdout), (name, p.stdout[-1000:])
            actual = re.findall(rb"^b[a-z2-7]+$", p.stdout, re.M)
            if unexpected_cid:
                assert len(actual) == 1, (name, actual)
            else:
                assert actual == ([] if cid is None else [cid.encode()]), (name, actual, cid)
            if canonical is not None:
                assert p.stdout.splitlines()[0] == canonical.encode(), (name, "canonical bytes differ")
        print(json.dumps(row), flush=True)

    run("build", [compiler, "compile", source, "--target", target, "--output", image, "--format", "static"],
        dict(env, KEXE_CAP_RESOURCES_35=str(out), KEXE_ALLOW="35,37,38,39"))
    image.chmod(0o755)
    report["image"] = pin(image)
    execution_env = dict(env, KEXE_ALLOW="37,38", KEXE_STRUCTURED_REPORT="1")
    for vector in vectors["vectors"]:
        run(vector["name"], [image, vector["hex"]], execution_env, 0, vector["cid"])
        run("construct-" + vector["name"], [image, "construct:" + vector["name"]], execution_env,
            0, vector["cid"], vector["hex"])

    pure = vectors["vectors"][0]["hex"]
    effects = next(v["hex"] for v in vectors["vectors"] if v["name"] == "effect-row-two")
    deps = next(v["hex"] for v in vectors["vectors"] if v["name"] == "dependencies-two")
    # Fixed byte edits: no host definition decoder, normalization or hash oracle.
    def replace_once(block, before, after):
        assert block.count(before) == 1, before
        return block.replace(before, after)

    first_pair = "8282626b776c646570656e64656e63696573826376656380"
    desugar = "8282626b777818646573756761722d636f6e74726163742d76657273696f6e8263696e746131"
    one = "82626b7774686f73742f636c6f636b2d6d6f6e6f746f6e6963"
    two = "82626b7769686f73742f68747470"
    dep_names = ["bafyreib4oafkwcwsvzyxjysuwmsb2zigmiece4pihcwzoekssg4fk34cha",
                 "bafyreihzlbfbvi3w24l3n6ofovirnqvyj74zkwtld6pqaor2qg4zk26wgi"]
    dep_one, dep_two = ["8263737472783b" + s.encode().hex() for s in dep_names]
    cases = {
        "empty": "", "odd-hex": pure[:-1], "bad-hex": "zz" + pure[2:],
        "truncated": pure[:-2], "trailing": pure + "00", "wrong-major": "a2" + pure[2:],
        "overlong-array": "9802" + pure[2:], "indefinite-array": "9f" + pure[2:],
        "unknown-normal-tag": replace_once(pure, "82636d617087", "8263666f6f87"),
        "unsorted-map": replace_once(pure, first_pair + desugar, desugar + first_pair),
        "duplicate-map-key": replace_once(pure, desugar, first_pair),
        "extra-sealed-field": replace_once(pure, "82636d617087", "82636d617088") + "8282626b77627a7a8263696e746130",
        "wrong-payload-version": replace_once(pure, "696f6e8263696e746132", "696f6e8263696e746133"),
        "missing-field": replace_once(pure, "6a6566666563742d726f77", "6a6566666563742d726f78"),
        "wrong-effect-type": replace_once(pure, "826373657480", "826376656380"),
        "wire-effect": replace_once(effects, "82626b7769686f73742f68747470", "826373747269686f73742f68747470"),
        "unsorted-effects": replace_once(effects, one + two, two + one),
        "duplicate-effects": replace_once(effects, one + two, two + two),
        "unsorted-dependencies": replace_once(deps, dep_one + dep_two, dep_two + dep_one),
        "duplicate-dependencies": replace_once(deps, dep_two, dep_one),
        "bad-cid-padding": replace_once(deps, dep_names[0].encode().hex(), (dep_names[0][:-1] + "b").encode().hex()),
        "bad-cid-header": replace_once(deps, dep_names[0].encode().hex(), (dep_names[0][:7] + "z" + dep_names[0][8:]).encode().hex()),
        "non-ascii": replace_once(pure, "65636f6e7374", "66636f6ec3a974"),
        "too-deep": "82" * 66 + "636e696c",
    }
    for name, block in cases.items():
        run("refuse-" + name, [image, block], execution_env, 1)
    # Linux argv cannot transport >128KiB; native code checks the exact block,
    # node and depth limits on both sides without using execve as the refusal.
    run("native-boundaries", [image, "native-boundary-tests"], execution_env, 0)
    run("native-encoder-refusals", [image, "native-encoder-refusals"], execution_env, 0)
    run("refuse-no-argument", [image], execution_env, 2)
    run("refuse-extra-argument", [image, pure, pure], execution_env, 2)
    # Each changed validator builds successfully, then actually demonstrates
    # the forbidden acceptance (or fails the paired boundary self-check).
    # A compiler error or an unexecuted mutant is never a detected mutation.
    original = source.read_text()
    mutations = {
        "map-set-order": ("(or (= mode 0) (= last 0) (< (dc-compare D V last item) 0))", "true", "unsorted-map"),
        "dependency-uniqueness": ("(> (string-compare text last) 0)", "true", "duplicate-dependencies"),
        "sealed-field-count": ("(= (dc-at D (dc-child D n 1) 2) 7)", "true", "extra-sealed-field"),
        "minimal-cbor": ("(or (< value minimum) (> value dc-limit))", "(> value dc-limit)", "overlong-array"),
        "complete-block": ("(not= (vector-at D 0) (vector-count V))\n                (not (dc-payload? D V 1))",
                           "false\n                (not (dc-payload? D V 1))", "trailing"),
        "block-bound": ("(> (string-length s) (* dc-limit 2))", "false", None),
        "depth-bound": ("(> depth 64)", "false", None),
    }
    report["mutationControls"] = []
    for name, (old, new, probe) in mutations.items():
        assert original.count(old) == 1, (name, "mutation anchor drift")
        changed = out / ("mutant-" + name + ".kotoba")
        changed.write_text(original.replace(old, new))
        mutant = out / ("mutant-" + name + ".elf")
        run("build-mutant-" + name,
            [compiler, "compile", changed, "--target", target, "--output", mutant, "--format", "static"],
            dict(env, KEXE_CAP_RESOURCES_35=str(out), KEXE_ALLOW="35,37,38,39"))
        mutant.chmod(0o755)
        run("detect-mutant-" + name, [mutant, cases[probe] if probe else "native-boundary-tests"], execution_env,
            0 if probe else 1, unexpected_cid=bool(probe))
        report["mutationControls"].append(dict(removedGuard=name, source=pin(changed), image=pin(mutant),
                                               builtSuccessfully=True, executed=True))
    report.update(status="PASS_NATIVE_DEFINITION_CID_CODEC", positiveVectors=10, nativeEncodedVectors=10,
                  refusalControls=len(cases) + 2, nativeBoundaryPairs=3, nativeEncoderChecks=9,
                  sourceIdentity=vectors["sourceSHA256"])
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
