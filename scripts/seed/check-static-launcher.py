#!/usr/bin/env python3
"""The static launcher (--format launcher, ADR 0371 step 4), end to end.

--compiler is an Amu-produced static compiler from the current sources (S3.elf
of selfhost-bootstrap.py, S-x86_64.elf on x86_64, or the root once re-pinned).
It runs on this host; --target picks the images' ISA (default: this host's).

1. The receipt functions of tools/static_launcher.kotoba, as a unit test
   (tools/static_launcher_test.kotoba) built with --format static, plus the
   control (CONTROL 1: exactly one case fails).
2. The launcher, tools/static_launcher.kotoba with --format launcher.
3. With --previous-root (the root from before this format): that compiler
   refuses --format launcher, and both compilers emit the same bytes for a
   static guest and for the runner (the launcher text is appended only in
   the new format).
4. Runs through the launcher, each checked against the receipt line and the
   bytes Python sees: a guest alone (ok, a trap, its arguments, its built
   environment, its descriptors, no_new_privs, the wall-time kill, the
   launcher sealed while it waits), and with a scripted provider (python3,
   test scaffolding only): an INFO round trip with the grant on fd 3 and the
   report on fd 4, a provider that crashes, one that lingers after end of
   file (killed after its 5 s grace), and an invalid and an oversized report.
   The guest that calls wire 42 is compiled by the product compiler when it
   admits wire 42 (ADR 0371 step 3), else by the test-only compiler of
   check-gpu-runtime-transport.py (wire 42 admitted in memory, never adopted).
5. Refusals before anything starts: usage, WALL, ALLOW versus the provider,
   unreadable or empty inputs, and images that cannot be executed.

Python only orchestrates processes, pipes and hashes; the launcher, the
guests and the receipt are Kotoba. Run on Linux, e.g. through the podman
machine on macOS (arm64):
  podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT python:3.12-alpine \
    python3 REPO/scripts/seed/check-static-launcher.py --compiler BOOT/S3.elf --output OUT
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = "tools/static_launcher.kotoba"
TEST = "tools/static_launcher_test.kotoba"
RUNNER_SRC = "seed/x86_64-kx64-runner.kotoba"
EXPECT_CALL = re.compile(r"\((expect|expect-i64) \"")
ANSWER = b"Scripted GPU|1.3.0|1024|1"
GRANT = b"{:wires #{42} :artifacts [] :device-bytes 1048576 :submit-timeout-ms 60000 :device 0}\n"

spec = importlib.util.spec_from_file_location("transport", Path(__file__).with_name("check-gpu-runtime-transport.py"))
assert spec is not None and spec.loader is not None
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)

PROVIDER = r'''
import hashlib, os, sys, time
mode = sys.argv[1]
fds = []
for i in range(64):
    try:
        os.fstat(i)
        fds.append(i)
    except OSError:
        pass
grant = b""
while True:
    chunk = os.read(3, 65536)
    if not chunk:
        break
    grant += chunk
if mode == "crash":
    sys.exit(3)

def read_exact(n):
    buf = b""
    while len(buf) < n:
        chunk = os.read(0, n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

requests = []
while True:
    head = read_exact(4)
    if head is None:
        break
    body = read_exact(int.from_bytes(head, "little"))
    requests.append(body.decode())
    answer = ANSWER if body == b"INFO" else b"!gpu/unknown-verb unknown :gpu/compute request"
    os.write(1, len(answer).to_bytes(4, "little") + answer)
report = ("fds=%s grant=%s requests=%s" % (",".join(map(str, fds)), hashlib.sha256(grant).hexdigest(), ",".join(requests))).encode()
if mode == "invalid":
    report = b"\xff\xfe"
if mode == "overflow":
    report = b"x" * 70000
view = memoryview(report)
while view:
    view = view[os.write(4, view):]
if mode == "linger":
    time.sleep(30)
'''.replace("ANSWER", repr(ANSWER))

GUESTS = {
    "hello": '(ns g (:export [main]))\n(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string "hello\\n")] 3))\n',
    "trap": '(ns g (:export [main]))\n(defn main [] :i64 (let [v [10 20]] (vector-at v 2)))\n',
    "args": ('(ns g (:export [main]))\n(defn- arg [i :string] :string (typed-cap-call :cli/args :string :string i))\n'
             '(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string (string-concat (arg "")'
             ' (string-concat "|" (string-concat (arg "0") (string-concat "|" (string-concat (arg "1") "\\n"))))))] 0))\n'),
    # the integer spelling: the test-only compiler admits wire 42 by id only
    "gpu": '(ns g (:export [main]))\n(defn main [] :i64 (string-length (typed-cap-call 42 :string :string "INFO")))\n',
}


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def sha(data):
    return hashlib.sha256(data).hexdigest()


# ---- a small EDN reader for the receipt line ----
def edn(text) -> Any:
    pos = 0

    def ws():
        nonlocal pos
        while pos < len(text) and text[pos] in " ,\n\t":
            pos += 1

    def value():
        nonlocal pos
        ws()
        c = text[pos]
        if c == "{":
            pos += 1
            out = {}
            while True:
                ws()
                if text[pos] == "}":
                    pos += 1
                    return out
                k = value()
                out[k] = value()
        if c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    e = text[pos + 1]
                    if e == "u":
                        buf.append(chr(int(text[pos + 2:pos + 6], 16)))
                        pos += 6
                        continue
                    buf.append({"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}[e])
                    pos += 2
                    continue
                buf.append(text[pos])
                pos += 1
            pos += 1
            return "".join(buf)
        m = re.compile(r"[^\s,{}]+").match(text, pos)
        assert m, text[pos:pos + 40]
        tok = m.group(0)
        pos = m.end()
        if tok == "nil":
            return None
        if tok in ("true", "false"):
            return tok == "true"
        if re.fullmatch(r"-?\d+", tok):
            return int(tok)
        assert tok.startswith(":"), tok
        return tok

    v = value()
    ws()
    assert pos == len(text), ("trailing", text[pos:pos + 40])
    return v


def main(compiler, output, target, previous_root, seccomp_if_available):
    assert platform.system() == "Linux", "run on Linux"
    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    target = target or host
    native = target == host
    output.mkdir(parents=True, exist_ok=False)
    art, raw = output / "artifacts", output / "raw"
    art.mkdir()
    raw.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    calls = []

    def run(name, argv, env, timeout=600, **kw):
        z = subprocess.run(list(map(str, argv)), cwd=art, env=env, capture_output=True, timeout=timeout, **kw)
        (raw / (name + ".stdout")).write_bytes(z.stdout)
        (raw / (name + ".stderr")).write_bytes(z.stderr)
        calls.append(dict(name=name, argv=[str(a).replace(str(art) + "/", "") for a in argv], exit=z.returncode))
        return z

    cenv = {"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}

    def compile_(prod, name, source, fmt="static", tgt=None, success=True):
        src, elf = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        z = run(name + "-compile", [prod, "compile", src, "--target", tgt or target, "--output", elf, "--format", fmt], cenv)
        if success:
            assert z.returncode == 0 and not z.stderr and b":ok true" in z.stdout, (name, z.returncode, z.stderr[-400:])
            elf.chmod(0o755)
        return elf, z

    run_env = {"PATH": "/usr/bin:/bin"}
    if seccomp_if_available:
        run_env["KEXE_SECCOMP"] = "if-available"
    rows = {}

    # 1. the receipt functions
    launcher_src = (ROOT / LAUNCHER).read_text()
    test_src = (ROOT / TEST).read_text()
    head, body = launcher_src.split("\n", 1)
    assert head == "(ns static-launcher (:export [main]))"
    cut = body.index("(defn main [] :i64")
    test_ns, test_body = test_src.split("\n", 1)
    counted = len(EXPECT_CALL.findall(test_body))
    assert counted > 0 and f"(def CASES {counted})" in test_body and test_body.count("(def CONTROL 0)") == 1, counted
    unit = "\n".join([test_ns, body[:cut], test_body])
    units = {}
    for name, source, want_failed in (("receipt-test", unit, 0), ("receipt-control", unit.replace("(def CONTROL 0)", "(def CONTROL 1)"), 1)):
        elf, _ = compile_(producer, name, source)
        z = run(name, [elf], dict(run_env, KEXE_STRUCTURED_REPORT="1", KEXE_FUEL="100000000"))
        lines = z.stdout.decode().splitlines()
        fails = [l for l in lines if l.startswith("FAIL ")]
        assert z.returncode == 0 and f"CASES {counted}" in lines and f"FAILED {want_failed}" in lines and len(fails) == want_failed, (name, lines[-6:])
        if want_failed:
            assert fails[0].startswith("FAIL provider killed, report invalid => "), fails
        units[name] = dict(image=pin(elf), failed=want_failed, failLines=fails)
    rows["receiptUnit"] = dict(casesCounted=counted, **units)

    # 2. the launcher
    launcher, z = compile_(producer, "launcher", launcher_src, fmt="launcher")
    assert b":format :launcher" in z.stdout, z.stdout
    rows["launcherImage"] = pin(launcher)

    # 3. the format is new, and the other formats did not change
    if previous_root:
        old = art / "previous-root.elf"
        old.write_bytes(previous_root.read_bytes())
        old.chmod(0o755)
        _, z = compile_(old, "previous-launcher", launcher_src, fmt="launcher", success=False)
        assert z.returncode == 2 and b"E7100" in z.stderr, (z.returncode, z.stderr[-300:])
        runner_fmt = "runner" if target == "aarch64-linux" else "kx64-runner"
        same = {}
        for name, source, fmt in (("hello", GUESTS["hello"], "static"), ("runner", (ROOT / RUNNER_SRC).read_text(), runner_fmt)):
            a, _ = compile_(producer, "same-new-" + name, source, fmt=fmt)
            b, _ = compile_(old, "same-old-" + name, source, fmt=fmt)
            assert a.read_bytes() == b.read_bytes(), ("format output changed", name)
            same[name] = pin(a)
        rows["unchangedFormats"] = dict(previousRoot=pin(previous_root), previousRootRefusesLauncher="E7100", sameBytes=same)

    # guests
    guests = {name: compile_(producer, "guest-" + name, GUESTS[name])[0] for name in ("hello", "trap", "args")}
    gpu, z = compile_(producer, "guest-gpu", GUESTS["gpu"], success=False)
    gpu_compiler = "product"
    if z.returncode != 0:
        assert b"E2115" in z.stderr, z.stderr[-300:]
        text, _ = transport.unity_text()
        test_compiler, _ = compile_(producer, "test-compiler-wire42", transport.patched(text, transport.ADMISSION), tgt=host)
        gpu, _ = compile_(test_compiler, "guest-gpu-test-compiler", GUESTS["gpu"])
        gpu_compiler = "test-only (wire 42 admitted in memory)"
    provider_py = art / "provider.py"
    provider_py.write_text(PROVIDER)
    grant = art / "grant.edn"
    grant.write_bytes(GRANT)
    tools = {t: shutil.which(t, path="/usr/bin:/bin") for t in ("sleep", "env", "ls", "cat")}
    assert all(tools.values()), tools
    provider = [sys.executable, "-I", "-B", str(provider_py)]

    def launch(name, wall, allow, guest, gargs=(), mode=None, want_exit=0, env=None):
        prov = ["-", "-"] if mode is None else [str(grant), *provider, mode]
        z = run("launch-" + name, [launcher, str(wall), allow, *prov, "--", str(guest), *gargs], env or run_env, timeout=120)
        assert z.returncode == want_exit, (name, z.returncode, z.stdout[-600:], z.stderr[-600:])
        out = z.stdout
        cut = out.rindex(b"{:receipt ")
        relayed, line = out[:cut], out[cut:]
        assert line.endswith(b"}\n") and line.count(b"\n") == 1, line
        r = edn(line.decode())
        g = r[":guest"]
        assert r[":receipt"] == ":kotoba.static-launcher/v1" and r[":wall-seconds"] == wall
        assert r[":launcher"] == {":sha256": sha(launcher.read_bytes())}, r[":launcher"]
        assert g[":sha256"] == sha(Path(guest).read_bytes()) and g[":allow"] == allow
        assert g[":stdout"] == {":bytes": len(relayed), ":sha256": sha(relayed)}, (g[":stdout"], len(relayed))
        if mode is None:
            assert r[":provider"] is None and r[":grant"] is None
        else:
            assert r[":provider"][":sha256"] == sha(Path(sys.executable).resolve().read_bytes())
            assert r[":grant"] == {":sha256": sha(GRANT)}
        rows.setdefault("runs", {})[name] = dict(exit=z.returncode, receipt=line.decode().strip(), stdout=relayed.decode(errors="replace")[-400:],
                                                 stderr=z.stderr.decode(errors="replace")[-400:])
        return r, relayed, z

    # 4a. a guest alone
    r, out, _ = launch("hello", 10, "37,38,39", guests["hello"])
    assert r[":verdict"] == ":ok" and r[":guest"][":exit"] == 0 and out.startswith(b"hello\n"), (r, out)
    assert r[":guest"][":report"][":status"] == ":ok" and r[":guest"][":report"][":result"] == 3
    r, out, z = launch("trap", 10, "37,38,39", guests["trap"], want_exit=1)
    assert r[":verdict"] == ":guest-failed" and r[":guest"][":exit"] == 120 and r[":guest"][":report"][":status"] == ":trap", r
    assert b"KEXE_TRAP {:kind :signal" in z.stderr
    r, out, _ = launch("args", 10, "37,38,39", guests["args"], gargs=("first", "second"))
    assert out.startswith(b"2|first|second\n"), out
    env = dict(run_env, KEXE_FUEL="777777", KEXE_STACK_BYTES="2097152", FOO="bar")
    r, out, _ = launch("environment", 10, "37,38,39", tools["env"], env=env)
    got = set(out.decode().splitlines())
    want = {"KEXE_ALLOW=37,38,39", "KEXE_STRUCTURED_REPORT=1", "KEXE_WALL_SECONDS=10", "KEXE_FUEL=777777", "KEXE_STACK_BYTES=2097152"}
    if seccomp_if_available:
        want.add("KEXE_SECCOMP=if-available")
    assert got == want, (got, want)
    r, out, _ = launch("descriptors", 10, "37,38,39", tools["ls"], gargs=("-1", "/proc/self/fd"))
    assert out.decode().split() == ["0", "1", "2", "3"], out
    r, out, _ = launch("no-new-privs", 10, "37,38,39", tools["cat"], gargs=("/proc/self/status",))
    assert re.search(rb"^NoNewPrivs:\s+1$", out, re.M), out[-400:]
    t0 = time.monotonic()
    r, out, _ = launch("wall", 2, "37,38,39", tools["sleep"], gargs=("30",), want_exit=122)
    took = time.monotonic() - t0
    assert r[":verdict"] == ":timeout" and r[":timed-out"] is True and r[":guest"][":signal"] == 9, r
    assert 1900 <= r[":elapsed-ms"] <= 4000 and took < 6, (r[":elapsed-ms"], took)
    # the launcher is sealed while it waits (a native kernel enforces seccomp)
    p = subprocess.Popen([str(launcher), "10", "37,38,39", "-", "-", "--", tools["sleep"], "2"], cwd=art, env=run_env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    seen = None
    for _ in range(150):
        status = Path(f"/proc/{p.pid}/status").read_text()
        found = re.search(r"^Seccomp:\s+(\d)$", status, re.M)
        seen = found.group(1) if found else None
        if seen == "2":
            break
        time.sleep(0.01)
    so, se = p.communicate(timeout=30)
    (raw / "launch-sealed.stdout").write_bytes(so)
    (raw / "launch-sealed.stderr").write_bytes(se)
    assert p.returncode == 0, (p.returncode, se[-300:])
    if native:
        assert seen == "2", seen
    rows["sealedWhileWaiting"] = dict(seccompField=seen, enforced=native)

    # 4b. with the scripted provider
    r, out, _ = launch("provider", 10, "37,38,39,42", gpu, mode="serve")
    assert r[":verdict"] == ":ok" and r[":guest"][":report"][":result"] == len(ANSWER), r
    pv = r[":provider"]
    assert pv[":exit"] == 0 and pv[":killed"] is False, pv
    assert pv[":report"] == f"fds=0,1,2,3,4 grant={sha(GRANT)} requests=INFO", pv[":report"]
    r, out, _ = launch("provider-descriptors", 10, "37,38,39,42", tools["ls"], gargs=("-1", "/proc/self/fd"), mode="serve")
    assert out.decode().split() == ["0", "1", "2", "3", "4", "5"], out
    r, out, _ = launch("provider-environment", 10, "37,38,39,42", tools["env"], mode="serve")
    assert "KEXE_CAP_RESOURCES_42=3,4" in out.decode().splitlines(), out
    r, out, _ = launch("provider-crash", 10, "37,38,39,42", gpu, mode="crash", want_exit=1)
    assert r[":verdict"] == ":guest-failed" and r[":guest"][":exit"] == 120 and r[":provider"][":exit"] == 3, r
    r, out, _ = launch("provider-linger", 20, "37,38,39,42", gpu, mode="linger", want_exit=1)
    assert r[":verdict"] == ":provider-failed" and r[":guest"][":exit"] == 0, r
    assert r[":provider"][":signal"] == 9 and r[":provider"][":killed"] is True and 4900 <= r[":elapsed-ms"] <= 9000, r
    r, out, _ = launch("provider-invalid-report", 10, "37,38,39,42", gpu, mode="invalid")
    assert r[":provider"][":report"] == ":invalid", r
    r, out, _ = launch("provider-overflow-report", 10, "37,38,39,42", gpu, mode="overflow")
    assert r[":provider"][":report"] == ":overflow", r

    # 5. refusals before anything starts
    empty = art / "empty.edn"
    empty.write_bytes(b"")
    text = art / "not-an-image"
    text.write_text("not an executable\n")
    text.chmod(0o755)
    refusals = {
        "no-arguments": ([], 2, "usage: WALL ALLOW GRANT PROVIDER [ARG ...] -- GUEST [ARG ...]"),
        "no-guest": (["10", "37", "-", "-", "--"], 2, "usage:"),
        "wall-zero": (["0", "37", "-", "-", "--", guests["hello"]], 2, "WALL must be 1..86400 seconds"),
        "wall-over": (["86401", "37", "-", "-", "--", guests["hello"]], 2, "WALL must be"),
        "grant-without-provider": (["10", "37", str(grant), "-", "--", guests["hello"]], 2, "usage:"),
        "provider-args-without-provider": (["10", "37", "-", "-", "x", "--", guests["hello"]], 2, "usage:"),
        "allow-42-without-provider": (["10", "37,42", "-", "-", "--", guests["hello"]], 2, "ALLOW must be"),
        "provider-without-42": (["10", "37", str(grant), *provider, "serve", "--", gpu], 2, "ALLOW must be"),
        "allow-invalid": (["10", "37,,38", "-", "-", "--", guests["hello"]], 2, "ALLOW must be"),
        "allow-over-255": (["10", "256", "-", "-", "--", guests["hello"]], 2, "ALLOW must be"),
        "guest-missing": (["10", "37", "-", "-", "--", art / "missing.elf"], 1, "cannot read an input: guest"),
        "grant-empty": (["10", "37,42", str(empty), *provider, "serve", "--", gpu], 1, "an input is empty or too large: grant"),
        "provider-missing": (["10", "37,42", str(grant), str(art / "missing"), "--", gpu], 1, "cannot read an input: provider"),
        "guest-not-an-image": (["10", "37", "-", "-", "--", text], 1, "a child could not be started: guest"),
        "provider-not-an-image": (["10", "37,42", str(grant), str(text), "--", gpu], 1, "a child could not be started: provider"),
    }
    rows["refusals"] = {}
    for name, (argv, code, message) in refusals.items():
        z = run("refuse-" + name, [launcher, *argv], run_env, timeout=60)
        assert z.returncode == code and not z.stdout and z.stderr.decode().startswith("kexe-launcher: " + message), \
            (name, z.returncode, z.stdout[-200:], z.stderr[-300:])
        rows["refusals"][name] = dict(exit=code, stderr=z.stderr.decode().strip())

    report = dict(status="PASS_STATIC_LAUNCHER", target=target, host=[platform.system(), platform.machine(), platform.release()],
                  executionNative=native, guestSeccomp="if-available" if seccomp_if_available else "required",
                  compiler=pin(compiler), sources={p: pin(ROOT / p) for p in (LAUNCHER, TEST)},
                  gpuGuestCompiler=gpu_compiler, providerScaffolding="python3 " + sys.version.split()[0] + " (test only)",
                  results=rows, calls=calls, cCompilerOrLoader=False,
                  notCovered=["a relay failure (the launcher's stdout closed): the receipt cannot be written either",
                              "the Vulkan provider and its grant format (ADR 0371 steps 5-6); the grant here is opaque bytes"])
    (output / "static-launcher.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, "native" if native else "emulated", f"{counted} receipt cases,",
          len(rows["runs"]), "runs,", len(rows["refusals"]), "refusals", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler built from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], help="image ISA (default: this host's)")
    parser.add_argument("--previous-root", type=Path, help="the root from before --format launcher: byte-identity of the other formats")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="KEXE_SECCOMP=if-available for the launcher and guests (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target,
         args.previous_root.resolve() if args.previous_root else None, args.seccomp_if_available)
