"""Native whole-prefix label-index semantic and mutation controls.

Python stages source bytes and records actual process results. It emits no
native formats. This unit is not whole compiler/product qualification.
"""
import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(compiler, output):
    assert platform.system() == "Linux"
    architecture = platform.machine()
    assert architecture in ("aarch64", "x86_64")
    target = "aarch64-linux" if architecture == "aarch64" else "x86_64-linux"
    output.mkdir(parents=True, exist_ok=False)
    paths = [p for p in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    assert paths[-1] == "seed/99-entry.kotoba"
    fixture = ROOT / "seed/tests/native-label-index.kotoba"
    unity = output / "label-index.kotoba"
    unity.write_bytes(b"".join((ROOT / path).read_bytes() + b"\n" for path in paths[:-1]) + fixture.read_bytes())
    report = dict(schema="amu.native-label-index-experiment.v1", host=[platform.system(), architecture],
                  officialPerformanceQualified=False, wholeCompilerQualified=False, candidateAdopted=False,
                  sourceModules=len(paths), productionPrefixModules=len(paths) - 1,
                  unitEntryReplacement=paths[-1],
                  sourceBindings={p: pin(ROOT / p) for p in paths[:-1]},
                  fixture=pin(fixture), unity=pin(unity), producer=pin(compiler), loadStart=os.getloadavg(), calls=[])
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(output),
               KEXE_FUEL="10000000000", KEXE_COMMAND="1", KEXE_ALLOW="38")

    def run(name, argv, expected=0, process_env=None):
        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = subprocess.run(list(map(str, argv)), cwd=output, env=process_env or env, capture_output=True, timeout=900)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        row = dict(name=name, exit=result.returncode, seconds=time.monotonic() - started,
                   cpuSeconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                   load=os.getloadavg())
        for suffix, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
            (output / (name + "." + suffix)).write_bytes(raw)
        report["calls"].append(row)
        (output / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        assert result.returncode == expected and not result.stderr, (name, result.returncode, result.stderr[-1000:])
        return row

    image = output / "label-index.elf"
    run("build", [compiler, "compile", unity, "--target", target, "--output", image, "--format", "static"],
        process_env={**env, "KEXE_ALLOW": "35,37,38,39"})
    image.chmod(0o755)
    report["image"] = pin(image)
    run("semantic-anchors-grid-and-malformed", [image])
    run("wrong-mode-failure-control", [image, "fail-control"], 1)
    original = unity.read_text()
    mutations = {
        "duplicate-label": ("(if (= (vector-at out (+ base l)) 0) j -1)", "j"),
        "suffix-query": ("(and (= j 1) (= found 0) (> (glx-base M) 0))", "(and (= found 0) (> (glx-base M) 0))"),
        "accumulator-query": ("(and (= j 1) (= found 0) (> (glx-base M) 0))", "(and (= j 1) (> (glx-base M) 0))"),
        "ccf-window": ("(or (< position (- i 2)) (> position i))", "true"),
        "ccf-reserved-operands": ("(= (gn-sir M position IF-B) 0) (= (gn-sir M position IF-C) 0)", "true"),
        "stale-extent": ("(= (vector-at M base) sn)", "true"),
    }
    report["mutationControls"] = []
    for name, (old, new) in mutations.items():
        assert original.count(old) == 1, name
        changed = original.replace(old, new)
        source = output / ("mutant-" + name + ".kotoba")
        source.write_text(changed)
        mutant = output / ("mutant-" + name + ".elf")
        run("build-mutant-" + name,
            [compiler, "compile", source, "--target", target, "--output", mutant, "--format", "static"],
            process_env={**env, "KEXE_ALLOW": "35,37,38,39"})
        mutant.chmod(0o755)
        run("reject-mutant-" + name, [mutant], 1)
        report["mutationControls"].append(dict(removedGuard=name, source=pin(source), image=pin(mutant),
                                               expectedSemanticExit=1))
    report.update(status="PASS_NATIVE_LABEL_INDEX_SEMANTIC_AND_MUTATION_CONTROLS",
                  anchorsPassed=True, benchmarkExecuted=False, loadEnd=os.getloadavg())
    (output / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--controls-only", action="store_true",
                        help="explicitly select semantic/mutation controls (the only supported mode)")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
