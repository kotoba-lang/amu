#!/usr/bin/env python3
"""The static runtimes' durable file replace (wire 35 FSYNC_SEP, RENAME_SEP)
and sleep (wire 7 "sleep <ms>").

Linear JUN-359, JUN-360. seed/76 and seed/77 answer two more :fs/app-data
forms of the capability catalog: FSYNC_SEP fsyncs a file or a directory,
RENAME_SEP renames the last component with each parent opened beneath the
scope. Together with WRITE_SEP they replace a file durably: write a
temporary, fsync it, rename it over the file, fsync the directory. Wire 7
:clock/now also takes "sleep <ms>" (0..60000), a CLOCK_MONOTONIC sleep that
answers the monotonic reading after it; clock_nanosleep is in the seccomp
filter only with wire 7 granted. The checker already admits both wires, so the
product compiler (--compiler, e.g. the bootstrap's F1.elf) builds the guests.

1. The replace: write, fsync, rename, read back; the temporary is gone; a
   rename over an existing file replaces it; a rename between directories of
   the scope; fsync of the scope directory.
2. "0", nothing moved: fsync of a missing file; rename of a missing file; a
   rename to outside the scope; a rename through a symlink that leads out of
   the scope.
3. Sleep: the monotonic reading after "sleep 200" is at least 200 ms later;
   "sleep 0"; traps for 60001, a non-decimal, a missing number, and a wire
   that is not granted.
4. The guest stays sandboxed: control compilers without fsync in the filter,
   and without clock_nanosleep, die of SIGSYS on the first such call, when the
   kernel enforces seccomp.

Python only orchestrates processes and hashes; the runtime and the guests are
Kotoba. Run on Linux, e.g. through the podman machine:
  podman run --platform linux/arm64 --network none -v REPO:REPO -v OUT:OUT \\
    python:3.12-alpine python3 REPO/scripts/seed/check-durable-sleep.py --compiler OUT/F1.elf --output OUT/durable
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
FUEL = "100000000"
NO_FSYNC_RULE = [("(kxrt-allow-nr-at p 82) (kxrt-allow-nr-at p 278)", "(kxrt-allow-nr-at p 278)", 1),
                 ("(kxrt-allow-nr-at p 74) (kxrt-allow-nr-at p 318)", "(kxrt-allow-nr-at p 318)", 1)]
NO_SLEEP_RULE = [("        i8 (if (kxrt-admitted? 7) (kxrt-allow-nr p i7 115) i7)\n", "        i8 i7\n", 1),
                 ("        i8 (if (kxrt-admitted? 7) (kxrt-allow-nr p i7 230) i7)\n", "        i8 i7\n", 1)]

HEAD = ('(ns t (:export [main]))\n'
        '(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n'
        '(defn- clock [s :string] :string (typed-cap-call :clock/now :string :string s))\n'
        '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s "|"))] 0))\n'
        '(defn- decimal [s :string] :i64\n'
        '  (loop [i 0 n 0] (if (= i (string-length s)) n (recur (+ i 1) (+ (* n 10) (- (string-code-point-at s i) 48))))))\n')


def lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fs_guest(scope, outside):
    p = lambda rest: lit(f"{scope}/{rest}")
    steps = [
        f'(fs {p("tmpWRITE_SEPhello")})',
        f'(say (fs {p("tmpFSYNC_SEP")}))',                                  # 1
        f'(say (fs {lit(f"{scope}/tmpRENAME_SEP{scope}/final")}))',          # 1
        f'(say (fs {p("final")}))',                                         # hello
        f'(say (fs {p("tmpEXISTS_SEP")}))',                                 # 0
        f'(fs {p("oldWRITE_SEPold")})', f'(fs {p("newWRITE_SEPnew")})',
        f'(say (fs {lit(f"{scope}/newRENAME_SEP{scope}/old")}))',            # 1
        f'(say (fs {p("old")}))',                                           # new
        f'(fs {p("sub/aWRITE_SEPa")})',
        f'(say (fs {lit(f"{scope}/sub/aRENAME_SEP{scope}/b")}))',            # 1
        f'(say (fs {p("b")}))',                                             # a
        f'(say (fs {lit(f"{scope}FSYNC_SEP")}))',                           # 1
        f'(say (fs {p("missingFSYNC_SEP")}))',                              # 0
        f'(say (fs {lit(f"{scope}/missingRENAME_SEP{scope}/x")}))',          # 0
        f'(say (fs {lit(f"{scope}/finalRENAME_SEP{outside}/stolen")}))',     # 0
        f'(say (fs {lit(f"{scope}/finalRENAME_SEP{scope}/link/stolen")}))',  # 0
        f'(say (fs {p("finalEXISTS_SEP")}))',                               # 1
    ]
    body = " ".join(f"s{k} {x}" for k, x in enumerate(steps))
    return HEAD + "(defn main [] :i64\n  (let [" + body + "]\n    7))\n"


SLEEP = HEAD + ('(defn main [] :i64\n'
                '  (let [t0 (decimal (clock "monotonic")) t1 (decimal (clock "sleep 200")) t2 (decimal (clock "sleep 0"))\n'
                '        a (say (if (>= (- t1 t0) 200000000) "slept" "short")) b (say (if (>= t2 t1) "ok" "back"))]\n'
                '    7))\n')
SLEEP_REQ = HEAD + '(defn main [] :i64 (let [a (say (clock (typed-cap-call 38 :string :string "0")))] 7))\n'
FSYNC_ONLY = HEAD + '(defn main [] :i64 (let [a (say (fs (typed-cap-call 38 :string :string "0")))] 7))\n'


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def unity_text():
    paths = [p for p in (ROOT / SELFHOST).read_text().splitlines() if p and not p.startswith("#")]
    return "".join((ROOT / p).read_text() + "\n" for p in paths), {p: pin(ROOT / p) for p in [SELFHOST, *paths]}


def patched(text, edits):
    for old, new, *count in edits:
        n = count[0] if count else 1
        assert text.count(old) == n, ("patch anchor", old[:60], text.count(old))
        text = text.replace(old, new)
    return text


def main(compiler, output, target, seccomp_if_available=False):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art, raw, scope, outside = output / "artifacts", output / "raw", output / "scope", output / "outside"
    for d in (art, raw, scope, outside, scope / "sub"):
        d.mkdir()
    os.symlink(outside, scope / "link")
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    base_env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": FUEL}
    if seccomp_if_available:
        base_env["KEXE_SECCOMP"] = "if-available"

    def compile_(prod, name, source, tgt):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        r = subprocess.run([str(prod), "compile", str(src), "--target", tgt, "--output", str(out), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)},
                           capture_output=True, timeout=1800)
        (raw / (name + ".compile.stdout")).write_bytes(r.stdout)
        (raw / (name + ".compile.stderr")).write_bytes(r.stderr)
        assert r.returncode == 0 and not r.stderr and b":ok true" in r.stdout, (name, r.returncode, r.stderr[-400:])
        out.chmod(0o755)
        return out

    rows = []

    def case(name, elf, env, args=(), want_exit=0, stdout_is=None, stderr_has=()):
        x = subprocess.run([str(elf), *args], env=dict(base_env, **env), capture_output=True, timeout=120)
        (raw / (name + ".stdout")).write_bytes(x.stdout)
        (raw / (name + ".stderr")).write_bytes(x.stderr)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout[-300:], x.stderr[-300:])
        if stdout_is is not None:
            assert x.stdout.startswith(stdout_is + b"{:status :ok :result 7 "), (name, x.stdout[-300:])
        for s in stderr_has:
            assert s in x.stderr, (name, s, x.stderr[-300:])
        rows.append(dict(name=name, args=list(args), exit=x.returncode,
                         stdout=x.stdout.decode(errors="replace")[:400], stderr=x.stderr.decode(errors="replace")[:400]))

    fs_env = {"KEXE_ALLOW": "35,37,38", "KEXE_CAP_RESOURCES_35": str(scope)}
    fs_elf = compile_(producer, "replace", fs_guest(scope, outside), target)
    case("replace-and-refusals", fs_elf, fs_env, stdout_is=b"1|1|hello|0|1|new|1|a|1|0|0|0|0|1|")
    assert (scope / "final").read_bytes() == b"hello" and not (scope / "tmp").exists() and not (outside / "stolen").exists()
    assert (scope / "old").read_bytes() == b"new" and not (scope / "new").exists() and (scope / "b").read_bytes() == b"a"
    sigill = b":signal :SIGILL"
    fsync_one = compile_(producer, "fsync-one", FSYNC_ONLY, target)
    case("fsync-trailing-bytes", fsync_one, fs_env, args=[f"{scope}/finalFSYNC_SEPx"], want_exit=120, stderr_has=[sigill])

    clock_env = {"KEXE_ALLOW": "7,37,38"}
    case("sleep", compile_(producer, "sleep", SLEEP, target), clock_env, stdout_is=b"slept|ok|")
    req = compile_(producer, "sleep-request", SLEEP_REQ, target)
    for name, arg in [("sleep-over-60000", "sleep 60001"), ("sleep-not-decimal", "sleep 1x"), ("sleep-no-number", "sleep ")]:
        case(name, req, clock_env, args=[arg], want_exit=120, stderr_has=[sigill])
    case("sleep-wire-not-granted", req, {"KEXE_ALLOW": "37,38"}, args=["sleep 1"], want_exit=120, stderr_has=[sigill])

    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    text, unity_pins = unity_text()
    no_fsync = compile_(producer, "control-compiler-no-fsync-rule", patched(text, NO_FSYNC_RULE), host)
    no_sleep = compile_(producer, "control-compiler-no-sleep-rule", patched(text, NO_SLEEP_RULE), host)
    enforced = not seccomp_if_available
    if enforced:
        (scope / "ctl").write_bytes(b"x")
        case("control-no-fsync-rule", compile_(no_fsync, "control-fsync", FSYNC_ONLY, target), fs_env,
             args=[f"{scope}/ctlFSYNC_SEP"], want_exit=120, stderr_has=[b":signal :SIGSYS"])
        case("control-no-sleep-rule", compile_(no_sleep, "control-sleep", SLEEP_REQ, target), clock_env,
             args=["sleep 10"], want_exit=120, stderr_has=[b":signal :SIGSYS"])
    report = dict(status="PASS_DURABLE_SLEEP_RUNTIME", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  imageSeccomp="if-available" if seccomp_if_available else "required", cases=rows,
                  controlCompilers={"no-fsync-rule": {"mutation": "no fsync in the scope's seccomp set, in both runtimes", "pin": pin(no_fsync)},
                                    "no-sleep-rule": {"mutation": "no clock_nanosleep in the seccomp filter, in both runtimes", "pin": pin(no_sleep)}},
                  unity=unity_pins, cCompilerOrLoader=False,
                  notCovered=["durability across a power cut: fsync returning is what is checked, not the device",
                              "a sleep interrupted by a signal (EINTR resumes it with the remaining time)"]
                             + ([] if enforced else ["the seccomp controls: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"]))
    (output / "durable-sleep.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, len(rows), "cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler built from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the images with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
