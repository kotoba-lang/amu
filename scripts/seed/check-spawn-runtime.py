#!/usr/bin/env python3
"""The static runtime's wire 20 (:process/spawn), through the spawn helper.

Linear JUN-292. When wire 20 is granted, seed/76 and seed/77 fork one helper
before the limits and the seccomp filter (a child of the sandboxed process
would inherit both). The helper keeps its own copy of the grant, decides every
request with tools/linux_static_handlers.kotoba ops 33..42, and runs the
program; the guest frames requests on a pipe and reads answers on another.
The checker admits wire 20, so the product compiler (--compiler, e.g. S3.elf
from selfhost-bootstrap.py) builds every guest here. Three parts:

1. The grant at start: malformed program lists, names and lookup values exit
   2; valid ones run; a grant without the wire is ignored.
2. The wire end to end:
   - answers "<exit>\\n<stdout>": arguments, an exit code, a signal (-1);
   - the child: stdin at end of file, only the granted variables, only fds
     0..2 open, no_new_privs set, no 64 MiB address-space limit, the
     :fs/app-data scope root as its working directory, SIGPIPE at its default;
   - the stdin payload (JUN-357): the bytes after STDIN_SEP reach the child's
     stdin, ARG_SEP inside them included; the first STDIN_SEP ends the argv
     part; 40 KiB read whole, or left unread by a child that exits or sleeps;
   - lookup by name;
   - every refusal the helper can be driven to: program-not-granted,
     path-lookup-denied, argv-budget, output-budget, timeout, exec-failed;
   - plain traps: an empty program, a request over 65536 bytes, a wire that
     is not granted.
3. The guest stays sandboxed: a control compiler whose filter has no read
   rule for the helper's answer fd dies of SIGSYS on the first answer, when
   the kernel enforces seccomp. A control compiler that does not restore
   SIGPIPE in the child (the helper ignores it) shows the child ignoring it.

Python only orchestrates processes and hashes; the runtime and the guests are
Kotoba. Run on Linux, e.g. through the podman machine:
  podman run --platform linux/arm64 --network none -v REPO:REPO -v OUT:OUT \\
    python:3.12-alpine python3 REPO/scripts/seed/check-spawn-runtime.py --compiler OUT/S3.elf --output OUT/spawn
On an x86_64 host, give the x86_64 static compiler (S-x86_64.elf) and
--target x86_64-linux; the control compiler is built for the host.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = "seed/X86_64-LINUX-SELFHOST-MANIFEST"
FUEL = "100000000"
S = "ARG_SEP"
T = "STDIN_SEP"
NO_READ_RULE = ("(if (> (kxrt-gl 2096) 2) (kxrt-allow-read-fd p i4 (kxrt-gl 2096)) i4)", "i4", 2)
NO_SIGPIPE_RESET = ("        dfl (kxrt-signal 13 q)\n", "        dfl 0\n", 2)
SIGPIPE_BIT = "m=$(grep SigIgn /proc/self/status | cut -f2); echo $(( (0x$m >> 12) & 1 ))"

PLAIN = "(ns t (:export [main]))\n(defn main [] :i64 42)\n"
HEAD = ('(ns t (:export [main]))\n'
        '(defn- spawn [s :string] :string (typed-cap-call :process/spawn :string :string s))\n'
        '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n'
        '(defn- dbl [s :string k :i64] :string (if (= k 0) s (dbl (string-concat s s) (dec k))))\n')


def guest(*requests):
    body = " ".join(f'a{k} (say (spawn {r}))' for k, r in enumerate(requests))
    return HEAD + "(defn main [] :i64\n  (let [" + body + "]\n    7))\n"


def lit(*parts):
    return '"' + S.join(parts) + '"'


def lit_in(parts, payload):
    return '"' + S.join(parts) + T + payload + '"'


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
    art, raw, scope = output / "artifacts", output / "raw", output / "scope"
    for d in (art, raw, scope):
        d.mkdir()
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

    def run(name, elf, env):
        x = subprocess.run([str(elf)], env=dict(base_env, **env), capture_output=True, timeout=120)
        (raw / (name + ".stdout")).write_bytes(x.stdout)
        (raw / (name + ".stderr")).write_bytes(x.stderr)
        return x

    # ---- part 1: the grant at start ----
    plain = compile_(producer, "plain", PLAIN, target)
    knob_rows = []

    def knob(name, programs=None, names=None, lookup=None, allow="20,37", want_exit=2):
        env = {"KEXE_ALLOW": allow}
        for k, v in (("KEXE_CAP_RESOURCES_20", programs), ("KEXE_SPAWN_ENV", names), ("KEXE_SPAWN_PATH_LOOKUP", lookup)):
            if v is not None:
                env[k] = v
        x = run("knob-" + name, plain, env)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout, x.stderr)
        if want_exit == 0:
            assert b":status :ok :result 42" in x.stdout, (name, x.stdout)
        knob_rows.append(dict(name=name, programs=programs, names=names, lookup=lookup, allow=allow, exit=x.returncode))

    knob("relative-program", programs="bin/echo")
    knob("root-alone", programs="/")
    knob("empty-segment", programs="/bin//echo")
    knob("dot-segment", programs="/bin/./echo")
    knob("dotdot-segment", programs="/bin/../echo")
    knob("trailing-slash", programs="/bin/echo/")
    knob("empty-entry", programs="/bin/echo::/bin/sh")
    knob("duplicate", programs="/bin/echo:/bin/echo")
    knob("seventeen-programs", programs=":".join(f"/p/{k}" for k in range(17)))
    knob("name-with-equals", programs="/bin/echo", names="A=B")
    knob("empty-name", programs="/bin/echo", names="A::B")
    knob("seventeen-names", programs="/bin/echo", names=":".join(f"N{k}" for k in range(17)))
    knob("lookup-two", programs="/bin/echo", lookup="2")
    knob("lookup-same-base", programs="/bin/echo:/usr/bin/echo", lookup="1")
    knob("valid", programs="/bin/echo:/bin/sh", names="FOO", lookup="0", want_exit=0)
    knob("sixteen-programs", programs=":".join(f"/p/{k}" for k in range(16)), want_exit=0)
    knob("absent", want_exit=0)
    knob("not-granted-ignored", programs="x", names="=", lookup="9", allow="37", want_exit=0)

    # ---- part 2: the wire ----
    rows = []
    grant = "/bin/echo:/bin/sh:/bin/cat:/bin/ls:/usr/bin/env:/bin/pwd:/bin/sleep:/nonexistent/program"

    def e2e(name, source, want_exit=0, stdout_is=None, stdout_has=(), stderr_has=(), prod=None, env=None):
        elf = compile_(prod or producer, "e2e-" + name, source, target)
        e = {"KEXE_ALLOW": "20,37", "KEXE_CAP_RESOURCES_20": grant}
        e.update(env or {})
        x = run("e2e-" + name, elf, e)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout[-300:], x.stderr[-300:])
        if stdout_is is not None:
            assert x.stdout.startswith(stdout_is + b"{:status :ok :result 7 "), (name, x.stdout)
        for s in stdout_has:
            assert s in x.stdout, (name, s, x.stdout[-300:])
        for s in stderr_has:
            assert s in x.stderr, (name, s, x.stderr[-300:])
        rows.append(dict(name=name, exit=x.returncode, stdout=x.stdout.decode(errors="replace"),
                         stderr=x.stderr.decode(errors="replace"), image=pin(elf)))

    e2e("arguments-and-exit", guest(lit("/bin/echo", "hello", "world"), lit("/bin/sh", "-c", "exit 3"),
                                    lit("/bin/sh", "-c", "kill -9 $$")),
        stdout_is=b"0\nhello world\n3\n-1\n")
    e2e("stdin-at-eof", guest(lit("/bin/cat")), stdout_is=b"0\n")
    e2e("stdin-payload", guest(lit_in(["/bin/cat"], "hello\\nworld")), stdout_is=b"0\nhello\nworld")
    e2e("stdin-payload-with-arguments", guest(lit_in(["/bin/sh", "-c", "tr a-z A-Z"], "abc")), stdout_is=b"0\nABC")
    e2e("stdin-payload-holds-arg-sep", guest(lit_in(["/bin/cat"], f"x{S}y")), stdout_is=b"0\nx" + S.encode() + b"y")
    e2e("stdin-payload-empty", guest(lit_in(["/bin/cat"], "")), stdout_is=b"0\n")
    e2e("stdin-sep-ends-argv", guest(f'"/bin/echo{S}a{T}b"'), stdout_is=b"0\na\n")
    e2e("stdin-payload-40k-read", guest(f'(string-concat "/bin/sh{S}-c{S}wc -c{T}" (dbl "0123456789" 12))'),
        stdout_has=[b"40960"])
    e2e("stdin-payload-40k-unread-exit", guest(f'(string-concat "/bin/sh{S}-c{S}exit 0{T}" (dbl "0123456789" 12))'),
        stdout_is=b"0\n")
    e2e("stdin-payload-40k-unread-sleep", guest(f'(string-concat "/bin/sleep{S}1{T}" (dbl "0123456789" 12))'),
        stdout_is=b"0\n")
    # bit 12 of SigIgn is SIGPIPE (13); the rest of the mask is the host's
    e2e("sigpipe-default", guest(lit("/bin/sh", "-c", SIGPIPE_BIT)), stdout_is=b"0\n0\n")
    e2e("only-granted-variables", guest(lit("/usr/bin/env")), stdout_is=b"0\nFOO=bar\n",
        env={"KEXE_SPAWN_ENV": "FOO:MISSING", "FOO": "bar", "BAZ": "qux"})
    e2e("only-stdio-open", guest(lit("/bin/ls", "/proc/self/fd")), stdout_is=b"0\n0\n1\n2\n3\n")
    e2e("no-new-privs", guest(lit("/bin/sh", "-c", "grep NoNewPrivs /proc/self/status")),
        stdout_is=b"0\nNoNewPrivs:\t1\n")
    e2e("no-address-space-limit", guest(lit("/bin/sh", "-c", "ulimit -v")), stdout_is=b"0\nunlimited\n")
    e2e("scope-root-directory", guest(lit("/bin/pwd")), stdout_is=b"0\n" + str(scope).encode() + b"\n",
        env={"KEXE_ALLOW": "20,35,37", "KEXE_CAP_RESOURCES_35": str(scope)})
    e2e("lookup-by-name", guest(lit("echo", "hi")), stdout_is=b"0\nhi\n", env={"KEXE_SPAWN_PATH_LOOKUP": "1"})
    trap = b"KEXE_TRAP {:kind :capability :capability :process/spawn :reason :spawn/"
    for name, source, reason, env in [
        ("program-not-granted", guest(lit("/bin/true")), b"program-not-granted", None),
        ("path-lookup-denied", guest(lit("echo", "hi")), b"path-lookup-denied", None),
        ("lookup-name-not-granted", guest(lit("true")), b"program-not-granted", {"KEXE_SPAWN_PATH_LOOKUP": "1"}),
        ("argv-budget", guest(lit("/bin/echo", *["x"] * 33)), b"argv-budget", None),
        ("argv-bytes-budget", guest(f'(string-concat "/bin/echo{S}" (dbl "x" 12))'), b"argv-budget", None),
        ("output-budget", guest(lit("/bin/sh", "-c", "yes")), b"output-budget", None),
        ("timeout", guest(lit("/bin/sleep", "11")), b"timeout", None),
        ("exec-failed", guest(lit("/nonexistent/program")), b"exec-failed", None),
        ("no-programs-granted", guest(lit("/bin/echo")), b"program-not-granted", {"KEXE_CAP_RESOURCES_20": ""}),
    ]:
        e2e(name, source, want_exit=126, stderr_has=[trap + reason + b"}\n"], env=env)
    e2e("empty-program", guest(lit("", "x")), want_exit=120, stderr_has=[b":signal :SIGILL"])
    e2e("request-over-65536", guest(f'(string-concat "/bin/echo{S}" (dbl "x" 16))'), want_exit=120,
        stderr_has=[b":signal :SIGILL"])
    e2e("wire-not-granted", guest(lit("/bin/echo")), want_exit=120,
        stderr_has=[b"KEXE_CAP {:wire 20 :refused :not-granted}\n", b":signal :SIGILL"],
        env={"KEXE_ALLOW": "37"})

    # ---- part 3: the guest stays sandboxed ----
    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    text, unity_pins = unity_text()
    control = compile_(producer, "control-compiler-no-read-rule", patched(text, [NO_READ_RULE]), host)
    enforced = not seccomp_if_available
    if enforced:
        e2e("control-no-read-rule", guest(lit("/bin/echo", "x")), want_exit=120, prod=control,
            stderr_has=[b":signal :SIGSYS"])
    control_pipe = compile_(producer, "control-compiler-no-sigpipe-reset", patched(text, [NO_SIGPIPE_RESET]), host)
    e2e("control-no-sigpipe-reset", guest(lit("/bin/sh", "-c", SIGPIPE_BIT)), prod=control_pipe, stdout_is=b"0\n1\n")
    report = dict(status="PASS_SPAWN_RUNTIME", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  executionNative=target.split("-")[0] == {"arm64": "aarch64", "AMD64": "x86_64"}.get(platform.machine(), platform.machine()),
                  imageSeccomp="if-available" if seccomp_if_available else "required",
                  grant=grant, knob=knob_rows, wire=rows,
                  controlCompiler={"mutation": "no read rule for the helper's answer fd, in both runtimes", "pin": pin(control)},
                  controlCompilerSigpipe={"mutation": "the child keeps the helper's ignored SIGPIPE, in both runtimes", "pin": pin(control_pipe)},
                  unity=unity_pins, cCompilerOrLoader=False,
                  notCovered=(["spawn/isolation-unavailable and spawn/setup-failed: no case drives close_range, prctl, dup3 or fchdir to fail",
                               "the stdin payload's deadline: a request holds at most 65536 bytes, which a default 64 KiB pipe takes whole, so no case blocks the feeding"]
                              + ([] if enforced else ["control-no-read-rule: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"])))
    (output / "spawn-runtime.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, len(knob_rows), "grant cases", len(rows), "wire cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler built from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the images with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
