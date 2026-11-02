#!/usr/bin/env python3
"""An omitted --target is the entry's own host; the roots still refuse it (KOTOBA-174, ADR 0396).

Each public entry names its own fixed host. The engine-neutral compiler roots
keep refusing an omitted target with E2. Python stages bytes, launches the
native processes and compares what they wrote; Amu does every check, compile
and refusal. Every assertion has a control that would fail if the property
were absent.

--isa x86_64 (native Linux x86_64): the public host entry bin/x86_64-linux/amu
  and the engine-neutral compiler bin/amu-linux-x86_64.
  * with --reproduce, the compiler rebuilds the host entry from the current
    FULL-MANIFEST byte for byte (and the host entry is not the compiler image);
  * omitted target on the host entry == explicit --target x86_64-linux on the
    host entry == explicit on the compiler: exit, stdout, stderr and output
    bytes, for --format static, kx64-v1, kx64-runner and the default format;
  * the omitted-target static program executes natively to :result 42;
  * no omitted-target output is Wasm or Kototama; control: the detector does
    flag the explicit --target wasm32-browser output;
  * explicit command lines (other targets, an unknown target, --target in a
    later position, check, usage errors) are identical on both images;
  * the compiler refuses an omitted target with E2 and writes nothing (with
    --format and no target, the flag itself is already a usage error, E1);
  * an unknown target is refused by both and writes nothing;
  * control: the byte comparison tells x86_64-linux from aarch64-linux output.
--isa aarch64 (native Linux ARM64): there is no public Linux ARM64 entry; the
  root seed/bootstrap/aarch64-linux-static-root.elf refuses an omitted target
  with E2 and an unknown target, while the explicit aarch64-linux compile of the
  same source runs to :result 42 (control).
--isa macos (Apple Silicon): the public CLI bin/amu compiles for aarch64-macos
  with no target; its artifact is Mach-O and `run` verifies it against a fresh
  explicit-aarch64-macos recompile (control: a tampered copy is refused); an
  explicit --target is a usage error there; the root amu-full-root.macho
  refuses an omitted target with E2 and an unknown target, and compiles the
  explicit aarch64-macos target (control).
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = b"(ns hello (:export [main]))\n(defn main [] :i64 42)\n"
WASM = b"\0asm"
ELF = b"\x7fELF"
MACHO = bytes.fromhex("cffaedfe")
# Kototama programs are DAG-CBOR maps (major type 5); no target here emits one.
CBOR_MAP = range(0xa0, 0xc0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": sha(raw)}


def need(cond, message):
    if not cond:
        raise SystemExit("FAIL " + message)


def kind(raw):
    if raw.startswith(WASM):
        return "wasm"
    if raw[:1] and raw[0] in CBOR_MAP:
        return "cbor"
    if raw.startswith(ELF):
        return "elf"
    if raw.startswith(MACHO):
        return "macho"
    return "other"


class Runner:
    """One working directory per image, so relative paths and messages agree."""

    def __init__(self, out):
        self.out = out
        self.calls = []

    def lane(self, name):
        d = self.out / name
        d.mkdir(mode=0o700)
        (d / "hello.kotoba").write_bytes(SOURCE)
        return d

    def run(self, name, image, d, args, env=None, timeout=1200):
        env = env or {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
                      "KEXE_CAP_RESOURCES_35": str(d), "KEXE_STACK_BYTES": "8388608"}
        r = subprocess.run([str(image), *map(str, args)], cwd=d, env=env,
                           capture_output=True, timeout=timeout)
        self.calls.append({"name": name, "image": Path(image).name, "argv": list(map(str, args)),
                           "exit": r.returncode, "stdoutSHA256": sha(r.stdout),
                           "stderrSHA256": sha(r.stderr)})
        return r


def outcome(r, d, output):
    p = d / output if output else None
    raw = p.read_bytes() if p is not None and p.is_file() else None
    return r.returncode, r.stdout, r.stderr, raw


def explicit(args, target="x86_64-linux"):
    """compile SRC REST -> compile SRC --target T REST (the positional form)."""
    return [args[0], args[1], "--target", target, *args[2:]]


def check_x86(compiler, host, out, reproduce):
    need(platform.system() == "Linux" and platform.machine() == "x86_64", "native Linux x86_64 required")
    product = json.loads((ROOT / "native-product.json").read_text())
    need(pin(compiler) == product["image"], "compiler is not the pinned engine-neutral image")
    need(pin(host) == product["hostEntry"]["image"], "host entry is not the pinned image")
    need(product["hostEntry"]["target"] == product["hostEntry"]["omittedTarget"] == "x86_64-linux",
         "descriptor does not name x86_64-linux")
    need(pin(host) != pin(compiler), "control: host entry and compiler are distinct images")
    run = Runner(out)
    report = {"isa": "x86_64", "compiler": pin(compiler), "hostEntry": pin(host)}

    if reproduce:
        d = run.lane("reproduce")
        names = [x for x in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
                 if x and not x.startswith("#")]
        (d / "full-unity.kotoba").write_bytes(b"".join((ROOT / n).read_bytes() + b"\n" for n in names))
        r = run.run("reproduce-host-entry", compiler, d,
                    ["compile", "full-unity.kotoba", "--target", "x86_64-linux",
                     "--output", "H.elf", "--format", "host-entry"],
                    env={"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(d),
                         "KEXE_STACK_BYTES": "8388608"})
        need(r.returncode == 0 and not r.stderr, "native host-entry build failed: " + r.stderr.decode(errors="replace")[-400:])
        need(pin(d / "H.elf") == pin(host), "native x86 compiler does not reproduce the host entry")
        report["reproducedHostEntry"] = pin(d / "H.elf")

    forms = {"static": ["compile", "hello.kotoba", "--output", "a.out", "--format", "static"],
             "kx64-v1": ["compile", "hello.kotoba", "--output", "a.out", "--format", "kx64-v1"],
             "kx64-runner": ["compile", "hello.kotoba", "--output", "a.out", "--format", "kx64-runner"],
             "default-format": ["compile", "hello.kotoba", "--output", "a.out"],
             "bare": ["compile", "hello.kotoba"]}
    results = {}
    for name, args in forms.items():
        a, b, c = run.lane(f"{name}-omitted"), run.lane(f"{name}-explicit"), run.lane(f"{name}-compiler")
        omitted = outcome(run.run(name + "-omitted", host, a, args), a, "a.out")
        on_host = outcome(run.run(name + "-explicit", host, b, explicit(args)), b, "a.out")
        on_compiler = outcome(run.run(name + "-compiler", compiler, c, explicit(args)), c, "a.out")
        need(omitted == on_host == on_compiler,
             f"{name}: omitted target differs from explicit x86_64-linux {omitted[:3]} {on_host[:3]} {on_compiler[:3]}")
        if omitted[3] is not None:
            need(kind(omitted[3]) not in ("wasm", "cbor"), f"{name}: omitted target wrote Wasm or Kototama")
        results[name] = {"exit": omitted[0], "output": None if omitted[3] is None else
                         {"bytes": len(omitted[3]), "sha256": sha(omitted[3]), "kind": kind(omitted[3])}}
    need(results["static"]["exit"] == 0 and results["static"]["output"]["kind"] == "elf",
         "positive: the omitted-target static compile must succeed with an ELF")
    report["omittedEqualsExplicit"] = results

    program = out / "static-omitted/a.out"
    program.chmod(0o700)
    r = run.run("execute-omitted-static", program, out / "static-omitted", [],
                env={"PATH": "/nonexistent", "KEXE_ALLOW": "-", "KEXE_FUEL": "1000000",
                     "KEXE_STRUCTURED_REPORT": "1"}, timeout=60)
    need(r.returncode == 0 and re.search(rb":result 42\b", r.stdout), "omitted-target program did not run to 42")
    report["nativeResult"] = 42

    # detector control: an explicit Wasm request is Wasm, identically on both images
    w1, w2 = run.lane("wasm-host"), run.lane("wasm-compiler")
    wasm_args = ["compile", "hello.kotoba", "--target", "wasm32-browser", "--output", "a.wasm"]
    wh = outcome(run.run("explicit-wasm-host", host, w1, wasm_args), w1, "a.wasm")
    wc = outcome(run.run("explicit-wasm-compiler", compiler, w2, wasm_args), w2, "a.wasm")
    need(wh == wc, "explicit wasm32-browser differs between host entry and compiler")
    need(wh[0] == 0 and wh[3] is not None and kind(wh[3]) == "wasm",
         "control: the Wasm detector must flag an explicit wasm32-browser output")

    # control: the comparison distinguishes targets
    g = run.lane("aarch64-explicit")
    arm = outcome(run.run("explicit-aarch64-host", host, g,
                          explicit(forms["static"], "aarch64-linux")), g, "a.out")
    need(arm[0] == 0 and arm[3] is not None and arm[3] != (out / "static-omitted/a.out").read_bytes(),
         "control: aarch64-linux output must differ from the omitted (x86_64-linux) output")

    # explicit command lines are the compiler's own on the host entry
    same = {"aarch64-linux-static": explicit(forms["static"], "aarch64-linux"),
            "unknown-target": explicit(forms["static"], "x86_64-bogus"),
            "unknown-target-default": explicit(forms["default-format"], "kototama"),
            "target-later": ["compile", "hello.kotoba", "--output", "a.out", "--format", "static",
                             "--target", "x86_64-linux"],
            "check": ["check", "hello.kotoba"],
            "compile-alone": ["compile"],
            "no-arguments": []}
    explicit_results = {}
    for name, args in same.items():
        a, b = run.lane(f"same-{name}-host"), run.lane(f"same-{name}-compiler")
        x = outcome(run.run("same-" + name + "-host", host, a, args), a, "a.out")
        y = outcome(run.run("same-" + name + "-compiler", compiler, b, args), b, "a.out")
        need(x == y, f"explicit command line {name} differs between host entry and compiler")
        explicit_results[name] = x[0]
    for name in ("unknown-target", "unknown-target-default"):
        need(explicit_results[name] != 0 and not (out / f"same-{name}-host/a.out").exists(),
             f"{name} must be refused without output")
    need(explicit_results["check"] == 0, "control: check must succeed")
    report["explicitUnchanged"] = explicit_results

    # the engine-neutral compiler still refuses an omitted target
    report["compilerRefusesOmitted"] = refuse_omitted(run, compiler)
    report["calls"] = run.calls
    return report


# An engine-neutral root refuses an omitted target with E2 (exit 1). With
# --format and no target the flag itself is a usage error (E1, exit 2): the
# root has no target-free --format. Neither writes anything.
REFUSALS = {"bare": (["compile", "hello.kotoba"], 1, b"seed: E2 "),
            "default-format": (["compile", "hello.kotoba", "--output", "a.out"], 1, b"seed: E2 "),
            "static": (["compile", "hello.kotoba", "--output", "a.out", "--format", "static"], 2, b"seed: E1 ")}


def refuse_omitted(run, image):
    seen = {}
    for name, (args, code, marker) in REFUSALS.items():
        d = run.lane(f"refuse-{name}-{Path(image).name}")
        r = run.run(f"refuse-omitted-{name}", image, d, args)
        need(r.returncode == code and marker in r.stderr and b"KEXE_TRAP" not in r.stderr,
             f"{Path(image).name} must refuse an omitted target ({name}) with {marker!r}: {r.returncode} {r.stderr[-200:]}")
        need(not (d / "a.out").exists(), f"{name}: the refusal wrote output")
        seen[name] = {"exit": r.returncode, "diagnostic": marker.decode().strip()}
    return seen


def check_aarch64(root, out):
    need(platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "native Linux ARM64 required")
    descriptor = json.loads((ROOT / "seed/bootstrap/aarch64-linux-static-root.json").read_text())
    need(pin(root) == descriptor["image"], "root is not the pinned aarch64 root")
    run = Runner(out)
    forms = {"static": ["compile", "hello.kotoba", "--output", "a.out", "--format", "static"],
             "default-format": ["compile", "hello.kotoba", "--output", "a.out"]}
    report = {"isa": "aarch64", "root": pin(root), "publicLinuxArm64Entry": None}
    report["rootRefusesOmitted"] = refuse_omitted(run, root)
    d = run.lane("explicit")
    r = run.run("explicit-aarch64-linux", root, d, explicit(forms["static"], "aarch64-linux"))
    need(r.returncode == 0 and (d / "a.out").is_file() and kind((d / "a.out").read_bytes()) == "elf",
         "control: the explicit aarch64-linux compile must succeed")
    (d / "a.out").chmod(0o700)
    r = run.run("execute-explicit", d / "a.out", d, [],
                env={"PATH": "/nonexistent", "KEXE_ALLOW": "-", "KEXE_FUEL": "1000000",
                     "KEXE_STRUCTURED_REPORT": "1"}, timeout=60)
    need(r.returncode == 0 and re.search(rb":result 42\b", r.stdout), "control: explicit program did not run to 42")
    d = run.lane("unknown")
    r = run.run("unknown-target", root, d, explicit(forms["static"], "aarch64-bogus"))
    need(r.returncode != 0 and not (d / "a.out").exists(), "unknown target must be refused without output")
    report["calls"] = run.calls
    return report


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/seed" / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def check_macos(out):
    need((platform.system(), platform.machine()) == ("Darwin", "arm64"), "Apple Silicon required")
    mac = module("mac_native", "check-aiueos-user-macos-native.py")
    cli_descriptor = json.loads((ROOT / "seed/bootstrap/aarch64-macos/cli.json").read_text())
    root_descriptor = json.loads((ROOT / "seed/bootstrap/aarch64-macos/root.json").read_text())
    cli = ROOT / cli_descriptor["entry"]
    root = ROOT / root_descriptor["compiler"]["path"]
    run = Runner(out)
    report = {"isa": "macos", "cli": pin(cli), "root": pin(root)}
    env = {"PATH": "/nonexistent", "LANG": "C"}
    d = run.lane("cli")
    r = run.run("cli-compile-omitted", cli, d, ["compile", "hello.kotoba"], env=env, timeout=150)
    need(r.returncode == 0 and (d / "hello").is_file(), "public CLI omitted-target compile failed")
    raw = (d / "hello").read_bytes()
    need(kind(raw) == "macho", "omitted target on the public CLI must write Mach-O, not Wasm or Kototama")
    r = run.run("cli-run-artifact", cli, d, ["run", "./hello"], env=env, timeout=150)
    need(r.returncode == 0 and r.stdout == b"42\n",
         "run must reproduce the artifact by an explicit aarch64-macos recompile")
    tampered = bytearray(raw)
    tampered[len(tampered) // 2] ^= 1
    (d / "tampered").write_bytes(bytes(tampered))
    (d / "tampered").chmod(0o700)
    r = run.run("cli-run-tampered", cli, d, ["run", "./tampered"], env=env, timeout=150)
    need(r.returncode != 0 and r.stdout != b"42\n", "control: a tampered artifact must be refused")
    for target in ("aarch64-macos", "wasm32-browser", "kototama", "aarch64-bogus"):
        r = run.run("cli-explicit-" + target, cli, d,
                    ["compile", "hello.kotoba", "--target", target, "-o", "x-" + target], env=env, timeout=150)
        need(r.returncode == 2 and not (d / ("x-" + target)).exists(),
             f"public CLI must keep refusing an explicit --target {target} (usage)")
    report["cli"] = {"omittedTarget": "aarch64-macos", "artifact": {"bytes": len(raw), "sha256": sha(raw)}}

    root_dir = run.lane("root")
    r = mac.native_run(root, root_dir, "compile", "hello.kotoba", "--output", "a.kseed", expected=1)
    need(b"seed: E2 " in r.stderr and not (root_dir / "a.kseed").exists(), "Mac root must refuse an omitted target with E2")
    r = mac.native_run(root, root_dir, "compile", "hello.kotoba", "--target", "aarch64-bogus",
                       "--output", "b.kseed", expected=1)
    need(b"seed: E2 " in r.stderr and not (root_dir / "b.kseed").exists(), "Mac root must refuse an unknown target with E2, no output")
    mac.native_run(root, root_dir, "compile", "hello.kotoba", "--target", "aarch64-macos", "--output", "c.kseed")
    need((root_dir / "c.kseed").is_file(), "control: the explicit aarch64-macos root compile must succeed")
    report["rootRefusesOmitted"] = {"E2": True}
    report["calls"] = run.calls
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--isa", choices=("x86_64", "aarch64", "macos"), required=True)
    p.add_argument("--compiler", type=Path, help="x86_64: engine-neutral compiler; aarch64: root")
    p.add_argument("--host", type=Path, help="x86_64: public host entry")
    p.add_argument("--reproduce", action="store_true", help="x86_64: rebuild the host entry natively")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    if a.isa == "x86_64":
        report = check_x86((a.compiler or ROOT / "bin/amu-linux-x86_64").resolve(),
                           (a.host or ROOT / "bin/x86_64-linux/amu").resolve(), out, a.reproduce)
    elif a.isa == "aarch64":
        report = check_aarch64((a.compiler or ROOT / "seed/bootstrap/aarch64-linux-static-root.elf").resolve(), out)
    else:
        report = check_macos(out)
    report.update(schema="amu.host-default-target.v1", status="PASS_HOST_DEFAULT_TARGET",
                  decision="KOTOBA-174", adr="0396", kototamaOrWasmDefault=False,
                  observer=pin(Path(__file__)))
    (out / "host-default-target.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], a.isa, len(report["calls"]), "native calls", flush=True)


if __name__ == "__main__":
    main()
