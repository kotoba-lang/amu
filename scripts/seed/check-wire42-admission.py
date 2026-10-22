#!/usr/bin/env python3
"""Wire 42 (:gpu/compute) admitted by the seed checker, end to end (ADR 0371 step 3).

Uses a selfhost-bootstrap.py output (--bootstrap: S3.elf, R-aarch64.elf and
G3.bin built from the admitting sources) and the producers from before the
round: the static root (--previous-root) and the previous adopted image
(--previous-adopted, the previous receipt's nativeImageSHA256). Checks:

* Before the round, all three spellings are refused with E2115:
  (typed-cap-call :gpu/compute :string :string "INFO"), the friendly
  (gpu/compute "INFO") and the integer (typed-cap-call 42 :string :string ...).
  This holds for both producers.
* After the round, both closures compile all three. The Linux selfhost closure
  is S3 with --format static. The adopted closure is G3 through the C-free
  runner, then extract-native. Each guest runs against the scripted provider
  of check-gpu-runtime-transport.py: KEXE_CAP_RESOURCES_42 plus a grant of
  42. The provider checks the request bytes, and main answers the answer's
  length.
* Still refused with E2115 after the round: the :bytes :bytes and
  :string :bytes shapes of wire 42, (http/post "x"), and wire 43.
* The adopted closure under the C-free runner does not print E2115: for
  every unadmitted capability it fails closed with the runtime's SIGILL trap
  line, exit 120 and no output. This is the same before the round, for
  b10e3813 and 6b158aa8 alike, while admitted wires compile. The script pins
  exactly that reason. It is a known defect of the adopted error path under
  the runner, tracked separately; the static closure names E2115.
* Policies stay closed. On the adopted closure, an explicit --policy is E2170
  for compile and check. On the static compiler, a --policy argument is a
  usage error (E7100, exit 2), as before.

Python only orchestrates processes, pipes and hashes. Run on arm64 Linux.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("transport", Path(__file__).with_name("check-gpu-runtime-transport.py"))
assert spec is not None and spec.loader is not None
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)

FORMS = {
    "keyword": '(typed-cap-call :gpu/compute :string :string "INFO")',
    "friendly": '(gpu/compute "INFO")',
    "integer": '(typed-cap-call 42 :string :string "INFO")',
}
REFUSED = {
    "bytes-bytes": "(bytes-count (typed-cap-call :gpu/compute :bytes :bytes (bytes-from-vector-i64 [1])))",
    "string-bytes": '(bytes-count (typed-cap-call :gpu/compute :string :bytes "INFO"))',
    "http-post": '(string-length (http/post "x"))',
    "wire-43": '(string-length (typed-cap-call 43 :string :string "x"))',
}
ANSWER = b"Scripted GPU|1.3.0|1024|1"


def guest(expr):
    return f"(ns g (:export [main]))\n(defn main [] :i64 (string-length {expr}))\n" if not expr.startswith("(bytes-count") and not expr.startswith("(string-length") \
        else f"(ns g (:export [main]))\n(defn main [] :i64 {expr})\n"


SIGILL_TRAP = b"KEXE_TRAP {:kind :signal :signal :SIGILL}\n"


def adopted_refusal(z, native):
    """The adopted closure's refusal: no artifact, and E2115 or exactly the runtime's SIGILL trap."""
    assert z.returncode != 0 and native is None, (z.returncode, z.stderr[-300:])
    if b"E2115" in z.stderr:
        return "E2115"
    assert z.returncode == 120 and z.stderr == SIGILL_TRAP, (z.returncode, z.stderr[-300:])
    return "trap:SIGILL"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(boot, previous_root, previous_adopted, out):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on arm64 Linux"
    out.mkdir(parents=True, exist_ok=False)
    art = out / "artifacts"
    art.mkdir()
    tools = {}
    for name, src in (("S3", boot / "S3.elf"), ("previous-root", previous_root), ("runner", boot / "R-aarch64.elf"),
                      ("G3", boot / "G3.bin"), ("adopted-before", previous_adopted)):
        dst = art / (name + (".bin" if name in ("G3", "adopted-before") else ".elf"))
        dst.write_bytes(Path(src).read_bytes())
        dst.chmod(0o755)
        tools[name] = dst
    assert sha(tools["S3"]) != sha(tools["previous-root"]), "--previous-root must be the root from before the round"
    previous = json.loads((ROOT / "seed/adoption-20261022.json").read_text())["wire42AdmissionRound"]["previousNativeImageSHA256"]
    assert sha(tools["adopted-before"]) == previous, "--previous-adopted must be the previous receipt's native image"
    calls = []

    def run(name, argv, env, timeout=1800, pass_fds=()):
        z = subprocess.run(list(map(str, argv)), cwd=art, env=env, capture_output=True, timeout=timeout, pass_fds=pass_fds)
        (art / (name + ".stdout")).write_bytes(z.stdout)
        (art / (name + ".stderr")).write_bytes(z.stderr)
        calls.append(dict(name=name, exit=z.returncode))
        return z

    cenv = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}
    renv = dict(cenv, KEXE_COMMAND="1", KEXE_STACK_BYTES="8388608")

    def static_compile(name, prod, source, extra=()):
        src, elf = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        return run(name, [prod, "compile", src, "--target", "aarch64-linux", "--output", elf, "--format", "static", *extra], cenv), elf

    def adopted_compile(name, prod, source, extra=()):
        src, kseed, native = art / (name + ".kotoba"), art / (name + ".kseed"), art / (name + ".bin")
        src.write_text(source)
        prefix = [tools["runner"], prod, 0, 0, "aarch64", "35,37,38,39", "--"]
        z = run(name + "-compile", prefix + ["compile", src, "--target", "aarch64-macos", "--output", kseed, *extra], renv)
        if z.returncode != 0:
            return z, None, None
        x = run(name + "-extract", prefix + ["extract-native", kseed, "--symbol", "main", "--output", native], renv)
        assert x.returncode == 0 and not x.stderr, (name, x.stderr[-300:])
        head = kseed.read_bytes().split(b"\n\n", 1)[0].decode().splitlines()
        exports = {n: (int(p), int(a)) for n, p, a in map(str.split, head[1:])}
        return z, native, exports["main"][0]

    def against_provider(name, argv, env_extra):
        r1, w1 = os.pipe()
        r2, w2 = os.pipe()
        env = dict(env_extra, KEXE_CAP_RESOURCES_42=f"{w1},{r2}")
        p = subprocess.Popen(list(map(str, argv)), cwd=art, env=env, pass_fds=(w1, r2), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.close(w1)
        os.close(r2)
        prov = transport.Provider(r1, w2, [(b"INFO", ANSWER)], "replay")
        prov.start()
        so, se = p.communicate(timeout=120)
        prov.join(timeout=30)
        (art / (name + ".stdout")).write_bytes(so)
        (art / (name + ".stderr")).write_bytes(se)
        calls.append(dict(name=name, exit=p.returncode))
        assert p.returncode == 0 and b":status :ok :result %d" % len(ANSWER) in so, (name, p.returncode, so[-300:], se[-300:])
        assert prov.got == [b"INFO"], (name, prov.got)

    rows = dict(before={}, static={}, adopted={}, refused={}, policy={})
    # 1. before the round: refused by name by both producers
    for form, expr in FORMS.items():
        z, _ = static_compile("before-static-" + form, tools["previous-root"], guest(expr))
        assert z.returncode != 0 and b"E2115" in z.stderr and not (art / ("before-static-" + form + ".elf")).exists(), (form, z.stderr[-300:])
        z, native, _ = adopted_compile("before-adopted-" + form, tools["adopted-before"], guest(expr))
        rows["before"][form] = {"static": "E2115", "adopted": adopted_refusal(z, native)}
    # 2. after the round: compiled by both closures, and run against the provider
    guest_env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "1000000"}
    for form, expr in FORMS.items():
        z, elf = static_compile("static-" + form, tools["S3"], guest(expr))
        assert z.returncode == 0 and not z.stderr, (form, z.stderr[-300:])
        elf.chmod(0o755)
        against_provider("run-static-" + form, [elf], dict(guest_env, KEXE_ALLOW="37,42"))
        rows["static"][form] = sha(elf)
        z, native, offset = adopted_compile("adopted-" + form, tools["G3"], guest(expr))
        assert z.returncode == 0 and not z.stderr and native is not None, (form, z.stderr[-300:])
        against_provider("run-adopted-" + form, [tools["runner"], native, offset, 0, "aarch64", "37,42"], dict(guest_env, KEXE_STACK_BYTES="8388608"))
        rows["adopted"][form] = sha(native)
    # 3. still refused after the round
    for name, expr in REFUSED.items():
        z, _ = static_compile("refused-static-" + name, tools["S3"], guest(expr))
        assert z.returncode != 0 and b"E2115" in z.stderr, (name, z.stderr[-300:])
        z, native, _ = adopted_compile("refused-adopted-" + name, tools["G3"], guest(expr))
        rows["refused"][name] = {"static": "E2115", "adopted": adopted_refusal(z, native)}
    # 4. policies stay closed
    policy = art / "allow-42.edn"
    policy.write_text("{:allow #{[:cap/call 42]}}\n")
    src = art / "policy-guest.kotoba"
    src.write_text(guest(FORMS["keyword"]))
    prefix = [tools["runner"], tools["G3"], 0, 0, "aarch64", "35,37,38,39", "--"]
    for verb in ("compile", "check"):
        argv = prefix + [verb, src, "--target", "aarch64-macos", "--policy", policy] + (["--output", art / "policy.kseed"] if verb == "compile" else [])
        z = run("policy-adopted-" + verb, argv, renv)
        assert z.returncode != 0 and b"E2170" in z.stderr and not (art / "policy.kseed").exists(), (verb, z.returncode, z.stderr[-300:])
        rows["policy"]["adopted-" + verb] = "E2170"
    z, _ = static_compile("policy-static", tools["S3"], guest(FORMS["keyword"]), ["--policy", str(policy)])
    assert z.returncode == 2 and b"E7100" in z.stderr, (z.returncode, z.stderr[-300:])
    rows["policy"]["static"] = "E7100"
    report = dict(status="PASS_WIRE42_ADMITTED", host=[platform.system(), platform.machine(), platform.release()],
                  producers={k: dict(sha256=sha(v), bytes=v.stat().st_size) for k, v in tools.items()},
                  results=rows, sameImageAcrossSpellings=dict(static=len(set(rows["static"].values())) == 1,
                                                              adopted=len(set(rows["adopted"].values())) == 1),
                  calls=calls, cCompilerOrLoader=False)
    (out / "wire42-admission.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "spellings", len(FORMS), "x 2 closures; refused", len(REFUSED), "; policy closed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bootstrap", type=Path, required=True, help="selfhost-bootstrap.py output built from the admitting sources")
    parser.add_argument("--previous-root", type=Path, required=True, help="the static root from before the round")
    parser.add_argument("--previous-adopted", type=Path, required=True,
                        help="the adopted image from before the round (the previous receipt's nativeImageSHA256, a G3.bin)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.bootstrap.resolve(), args.previous_root.resolve(), args.previous_adopted.resolve(), args.output.resolve())
