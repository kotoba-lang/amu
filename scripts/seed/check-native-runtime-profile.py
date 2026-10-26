#!/usr/bin/env python3
"""Supplemental native profile observations, not a replacement CDCI verdict."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STANDARD, LARGE = 4194304, 67108864


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def vectors(n):
    return ("(ns profile-bound (:export [main]))\n(defn main [] :i64\n"
            f" (loop [i 0] (if (= i {n}) 0\n"
            "  (let [v (vector-alloc 0)] (if (= (vector-count v) 0) (recur (inc i)) 1)))))\n")


def main(compiler, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    target = "aarch64-linux" if platform.machine() == "aarch64" else "x86_64-linux"
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    report = dict(schema="amu.native-runtime-profile-controls.v1", status="running",
                  nativeVerdictAuthority=False, qualificationReplacement=False,
                  wholeCompilerQualified=False, performanceQualified=False,
                  compiler=pin(compiler), observer=pin(Path(__file__)),
                  host=[platform.system(), platform.machine()],
                  sources={p: pin(ROOT / p) for p in paths}, calls=[], mutations=[])
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39",
               KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES="8388608")
    runtime = dict(PATH="/nonexistent", KEXE_ALLOW="-", KEXE_FUEL="1000000000000",
                   KEXE_WALL_SECONDS="300", KEXE_ARENA_USE="1", KEXE_STRUCTURED_REPORT="1")

    def save():
        (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")

    def call(name, argv, run_env):
        start = time.monotonic()
        r = subprocess.run(list(map(str, argv)), cwd=out, env=run_env,
                           capture_output=True, timeout=900)
        for stream, raw in (("stdout", r.stdout), ("stderr", r.stderr)):
            (out / (name + "." + stream)).write_bytes(raw)
        report["calls"].append(dict(name=name, argv=list(map(str, argv)), exit=r.returncode,
                                    seconds=time.monotonic() - start))
        save()
        print(name, r.returncode, flush=True)
        return r

    def build(name, text, profile=None, producer=None, extra=(), expected=True):
        source, image = out / (name + ".kotoba"), out / (name + ".elf")
        source.write_text(text)
        argv = [producer or compiler, "compile", source, "--target", target,
                "--output", image, "--format", "static"]
        if profile is not None:
            argv += ["--runtime-profile", profile]
        r = call("build-" + name, argv + list(extra), env)
        if expected:
            assert r.returncode == 0 and not r.stderr and image.is_file(), (name, r.stderr[-1000:])
            image.chmod(0o700)
            selected = profile or "standard-v1"
            assert f":runtime-profile :{selected}".encode() in r.stdout
            assert f":vector-descriptors {LARGE if selected == 'large-vectors-v1' else STANDARD}".encode() in r.stdout
            return image
        assert r.returncode != 0 and not image.exists(), (name, "accepted invalid profile")

    def observe(name, image):
        r = call(name, [image], runtime)
        fields = dict((k.decode(), int(v)) for k, v in re.findall(rb":([a-z-]+) ([0-9]+)", r.stderr))
        return r, fields

    def bounded(name, n, profile, overflow=False):
        image = build(name, vectors(n), profile)
        r, fields = observe("run-" + name, image)
        limit = LARGE if profile == "large-vectors-v1" else STANDARD
        assert fields.get("vectors") == min(n, limit) and fields.get("vector-items") == 0, (name, fields)
        if overflow:
            assert r.returncode != 0 and b"vector-table-exhausted" in r.stderr, (name, r.returncode)
        else:
            assert r.returncode == 0 and b":status :ok :result 0 " in r.stdout, (name, r.stdout, r.stderr)
        return image

    plain = vectors(1)
    default = build("default", plain)
    standard = build("standard", plain, "standard-v1")
    assert default.read_bytes() == standard.read_bytes(), "omission changed standard profile"
    build("unknown", plain, "large-vectors-v2", expected=False)
    build("empty", plain, "", expected=False)
    build("duplicate", plain, "standard-v1", extra=("--runtime-profile", "large-vectors-v1"), expected=False)
    build("duplicate-identical", plain, "standard-v1", extra=("--runtime-profile", "standard-v1"), expected=False)
    build("missing-value", plain, extra=("--runtime-profile",), expected=False)
    bounded("standard-at-limit", STANDARD, "standard-v1")
    bounded("standard-over-limit", STANDARD + 1, "standard-v1", True)
    bounded("large-cross-standard", STANDARD + 1, "large-vectors-v1")
    bounded("large-at-limit", LARGE, "large-vectors-v1")
    bounded("large-over-limit", LARGE + 1, "large-vectors-v1", True)

    for case in json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]:
        image = build("case-" + case["name"], case["source"], "large-vectors-v1")
        r = call("case-" + case["name"], [image], {**runtime, "KEXE_FUEL": "1000000"})
        remaining = re.search(rb":remaining ([0-9]+)", r.stdout)
        assert dict(exit=r.returncode, remainingFuel=int(remaining[1]) if remaining else None) == case["reference"]
        if case["trap"]:
            assert b":status :trap" in r.stdout
        else:
            assert int(re.search(rb":result (-?[0-9]+)", r.stdout)[1]) == case["result"]

    zero = build("zero-rollback", (ROOT / "seed/tests/native-zero-watermark.kotoba").read_text(), "large-vectors-v1")
    r, _ = observe("zero-rollback", zero)
    assert r.returncode == 0 and b":status :ok :result 0 " in r.stdout
    unity = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths).decode()
    marker = "(mem-u2dec (if (= profile 1) 67108864 4194304))"
    start = unity.index("(defn- xs-profile-prelude ")
    end = unity.index("(defn- xs-command ", start)
    prelude = unity[start:end]
    assert prelude.count(marker) == 1
    changed = unity[:start] + prelude.replace(marker, "(mem-u2dec 4194304)") + unity[end:]
    mutant = build("selection-mutant-compiler", changed)
    bad = build("selection-mutant", vectors(STANDARD + 1), "large-vectors-v1", mutant)
    r, fields = observe("detect-selection-mutant", bad)
    assert r.returncode != 0 and b"vector-table-exhausted" in r.stderr and fields["vectors"] == STANDARD
    report["mutations"].append(dict(name="wrong-profile-selection", builtSuccessfully=True,
                                     executed=True, compiler=pin(mutant), image=pin(bad)))
    # Real unchanged growth-row limit, including the exact-copy fallback.
    region_source = (ROOT / "seed/tests/native-profile-region-bound.kotoba").read_text()
    region = build("region-at-limit-plus-one", region_source, "large-vectors-v1")
    r, fields = observe("region-at-limit-plus-one", region)
    assert r.returncode == 0 and b":status :ok :result 0 " in r.stdout
    assert {key: fields[key] for key in ("regions", "reserved-words", "vectors", "vector-items")} == {
        "regions": STANDARD, "reserved-words": STANDARD * 2,
        "vectors": (STANDARD + 1) * 3, "vector-items": (STANDARD + 1) * 6 - 2}
    region_marker = "(def KXRT-REGIONS 4194304)"
    assert unity.count(region_marker) == 2
    region_mutant = build("region-mutant-compiler", unity.replace(region_marker, "(def KXRT-REGIONS 67108864)"))
    region_bad = build("region-mutant", region_source, "large-vectors-v1", region_mutant)
    r, fields = observe("detect-region-mutant", region_bad)
    assert r.returncode == 0 and b":status :ok :result 0 " in r.stdout
    assert fields["regions"] == STANDARD + 1 and fields["reserved-words"] == (STANDARD + 1) * 2
    report["mutations"].append(dict(name="region-limit-broadening", builtSuccessfully=True,
                                     executed=True, compiler=pin(region_mutant), image=pin(region_bad),
                                     detectedBy="native arena accounting differs from fixed region oracle"))
    bound_marker = "(>= u KXRT-VECTORS)"
    assert unity.count(bound_marker) == 2
    bound_mutant = build("bound-mutant-compiler", unity.replace(bound_marker, "(> u KXRT-VECTORS)"))
    bound_bad = build("bound-mutant", vectors(STANDARD + 1), "standard-v1", bound_mutant)
    r, _ = observe("detect-bound-mutant", bound_bad)
    assert b"vector-table-exhausted" not in r.stderr, "mutant did not remove the expected refusal"
    report["mutations"].append(dict(name="off-by-one-vector-bound", builtSuccessfully=True,
                                     executed=True, compiler=pin(bound_mutant), image=pin(bound_bad),
                                     detectedBy="missing named vector-table refusal"))
    highwater = "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) high (if (> (+ off n) (kxrt-gl 760)) (kxrt-gs 760 (+ off n)) 0) w (kxrt-gs 48 (inc u))"
    without = "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) w (kxrt-gs 48 (inc u))"
    assert unity.count(highwater) == 2
    zero_source = (ROOT / "seed/tests/native-zero-watermark.kotoba").read_text()
    for name, changed in (
            ("missing-watermark", unity.replace(highwater, without)),
            ("relative-watermark", unity.replace("(kxrt-gs 760 (+ off n))", "(kxrt-gs 760 n)")),
            ("last-word", unity.replace("byte-end (+ base (* 8 count))",
                                       "byte-end (+ base (* 8 (if (> count 0) (dec count) 0)))"))):
        mutated = build(name + "-compiler", changed)
        bad = build(name + "-oracle", zero_source, "large-vectors-v1", mutated)
        r, _ = observe("detect-" + name, bad)
        assert r.returncode == 0 and b":status :ok :result 1 " in r.stdout
        report["mutations"].append(dict(name=name, builtSuccessfully=True, executed=True,
                                         compiler=pin(mutated), image=pin(bad),
                                         detectedBy="native zero/rollback oracle returns one"))
    assert all(pin(ROOT / p) == value for p, value in report["sources"].items())
    report.update(status="PASS_NATIVE_PROFILE_OBSERVATIONS", defaultExplicitStandardIdentical=True,
                  regionMutationControlsPending=False, nativeControllerQualificationPending=True)
    save()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
