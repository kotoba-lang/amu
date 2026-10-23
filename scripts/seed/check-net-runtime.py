#!/usr/bin/env python3
"""The static runtime's native TCP wires 43..47 (:net/listen :net/accept
:net/dial :net/read :net/write), on the loopback interface.

Linear JUN-292. seed/76 and seed/77 answer the five wires in the image's own
process with the decisions and refusal names of the removed loader
(tools/kexe_loader_decisions.kotoba ops 10-18, tools/kexe_loader_names.kotoba):
exact granted IPv4 addresses (KEXE_CAP_RESOURCES_43 for listen, _45 for dial),
at most 16 handles, 16384 bytes per read or write, timeouts up to 30000 ms,
a refusal by name on stderr and exit 126. The seccomp filter admits the
socket calls only with one of the wires granted, and socket only as
socket(AF_INET, SOCK_STREAM|SOCK_NONBLOCK|SOCK_CLOEXEC, 0). Two parts:

1. The start-up check, with --compiler (the Amu-produced static compiler
   built from these sources, e.g. S3.elf from selfhost-bootstrap.py). With a
   net wire granted, a malformed scope exits 2; a valid one runs; a scope
   without the grant is ignored. The product checker admits numeric, keyword
   and friendly forms, refuses wrong kinds, and enforces effect ceilings.

2. The wires end to end, compiled by the product compiler unchanged.
   Cases: a loopback round trip (listen, dial, accept, write, read,
   close, end of file), the environmental answers (timeout, refused), every
   refusal name the wires can raise, a request over 65536 bytes, and wires
   that are not granted. Two control compilers show the filter is what holds:
   without the net rules, and with socket asked in another form, the first
   socket call dies of SIGSYS when the kernel enforces seccomp.

Python only orchestrates processes and hashes; the runtime and the guests are
Kotoba. Run on Linux, e.g. through the podman machine:
  podman run --platform linux/arm64 --network none -v REPO:REPO -v OUT:OUT \
    python:3.12-alpine python3 REPO/scripts/seed/check-net-runtime.py --compiler OUT/S3.elf --output OUT/net
On an x86_64 host, give the x86_64 static compiler (S-x86_64.elf) and
--target x86_64-linux; the two control compilers are built for the host.
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
NET = "37,43,44,45,46,47"

# Product admission is part of the source under test; no admission patch.
WIRES = [(43, "LISTEN"), (44, "ACCEPT"), (45, "DIAL"), (46, "READ"), (47, "WRITE")]
# Controls, in both runtimes: no net rules in the filter; socket asked in a
# form the filter does not admit (no SOCK_NONBLOCK|SOCK_CLOEXEC).
NO_NET_RULES = ("(if (kxrt-net-any?) (kxrt-allow-net p i3) i3)", "i3", 2)
OTHER_SOCKET = [("(kxrt-syscall 198 2 526337 0 0 0 0)", "(kxrt-syscall 198 2 1 0 0 0 0)"),
                ("(kxrt-syscall 41 2 526337 0 0 0 0)", "(kxrt-syscall 41 2 1 0 0 0 0)")]

PLAIN = "(ns t (:export [main]))\n(defn main [] :i64 42)\n"
DEFS = ('(defn- listen [s :string] :string (typed-cap-call 43 :string :string s))\n'
        '(defn- accept [s :string] :string (typed-cap-call 44 :string :string s))\n'
        '(defn- dial [s :string] :string (typed-cap-call 45 :string :string s))\n'
        '(defn- rd [s :string] :string (typed-cap-call 46 :string :string s))\n'
        '(defn- wr [s :string] :string (typed-cap-call 47 :string :string s))\n'
        '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s "\\n"))] 0))\n'
        '(defn- sp [a :string b :string] :string (string-concat a (string-concat " " b)))\n'
        '(defn- dbl [s :string k :i64] :string (if (= k 0) s (dbl (string-concat s s) (dec k))))\n')
HEAD = "(ns t (:export [main]))\n" + DEFS
A = "127.0.0.1:{p}"


def guest(body):
    return HEAD + "(defn main [] :i64\n  (let [" + body + "]\n    7))\n"


# listen, dial, accept; write five bytes; read them back; close the dialer;
# read again: end of file; close the accepted connection
ROUND = guest('l (listen "127.0.0.1:{p}") a (say l)\n'
              '        c (dial "127.0.0.1:{p} 1000") b (say c)\n'
              '        s (accept (sp l "1000")) d (say s)\n'
              '        w (wr (sp c "68656c6c6f")) e (say w)\n'
              '        r (rd (sp s "16 1000")) f (say r)\n'
              '        x (wr c) g (say x)\n'
              '        r2 (rd (sp s "16 1000")) h (say r2)\n'
              '        y (wr s) i (say y)')
ACCEPT_TIMEOUT = guest('l (listen "127.0.0.1:{p}") a (say (accept (sp l "50")))')
READ_TIMEOUT = guest('l (listen "127.0.0.1:{p}") c (dial "127.0.0.1:{p} 1000") s (accept (sp l "1000"))\n'
                     '        a (say (rd (sp s "4 50")))')
DIAL_REFUSED = guest('a (say (dial "127.0.0.1:{q} 1000"))')
SIXTEEN = guest('l (listen "127.0.0.1:{p}")\n' + "".join(
    f'        c{k} (dial "127.0.0.1:{{p}} 1000")\n' for k in range(1, 16)) +
    '        a (say c15) z (dial "127.0.0.1:{p} 1000")')


def one(call):
    return guest(f'a (say {call})')


CONN = 'l (listen "127.0.0.1:{p}") c (dial "127.0.0.1:{p} 1000")\n        '
REFUSALS = [
    # (name, source, wire, reason)
    ("listen-not-granted", one('(listen "127.0.0.1:{q}")'), "listen", "address-not-granted"),
    ("listen-malformed", one('(listen "127.0.0.1")'), "listen", "malformed-request"),
    ("listen-bad-octet", one('(listen "127.0.0.256:{p}")'), "listen", "malformed-request"),
    ("listen-two-fields", one('(listen "127.0.0.1:{p} 5")'), "listen", "malformed-request"),
    ("listen-failed", guest('l (listen "127.0.0.1:{p}") m (say (listen "127.0.0.1:{p}"))'), "listen", "listen-failed"),
    ("dial-no-timeout", one('(dial "127.0.0.1:{p}")'), "dial", "malformed-request"),
    ("dial-timeout-budget", one('(dial "127.0.0.1:{p} 30001")'), "dial", "timeout-budget"),
    ("dial-not-granted", one('(dial "127.0.0.2:{p} 10")'), "dial", "address-not-granted"),
    ("dial-handle-budget", SIXTEEN, "dial", "handle-budget"),
    ("accept-out-of-range", one('(accept "17 10")'), "accept", "handle-out-of-range"),
    ("accept-not-open", one('(accept "1 10")'), "accept", "handle-not-open"),
    ("accept-on-connection", guest(CONN + 'a (say (accept (sp c "10")))'), "accept", "handle-not-open"),
    ("read-zero-handle", one('(rd "0 4 10")'), "read", "handle-out-of-range"),
    ("read-byte-budget", guest(CONN + 'a (say (rd (sp c "16385 10")))'), "read", "byte-budget"),
    ("read-timeout-budget", guest(CONN + 'a (say (rd (sp c "4 30001")))'), "read", "timeout-budget"),
    ("read-malformed", guest(CONN + 'a (say (rd (sp c "x 10")))'), "read", "malformed-request"),
    ("write-odd-hex", guest(CONN + 'a (say (wr (sp c "abc")))'), "write", "malformed-request"),
    ("write-upper-hex", guest(CONN + 'a (say (wr (sp c "AB")))'), "write", "malformed-request"),
    ("write-on-listener", guest(CONN + 'a (say (wr (sp l "00")))'), "write", "handle-not-open"),
    ("write-byte-budget", guest(CONN + 'a (say (wr (sp c (string-concat "00" (dbl "00" 14)))))'), "write", "byte-budget"),
]


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
    art, raw = output / "artifacts", output / "raw"
    art.mkdir()
    raw.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    base_env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": FUEL}
    if seccomp_if_available:
        base_env["KEXE_SECCOMP"] = "if-available"

    def compile_(prod, name, source, tgt, success=True):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        r = subprocess.run([str(prod), "compile", str(src), "--target", tgt, "--output", str(out), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)},
                           capture_output=True, timeout=1800)
        (raw / (name + ".compile.stdout")).write_bytes(r.stdout)
        (raw / (name + ".compile.stderr")).write_bytes(r.stderr)
        if success:
            assert r.returncode == 0 and not r.stderr and b":ok true" in r.stdout, (name, r.returncode, r.stderr[-400:])
            out.chmod(0o755)
        return out, r

    def run(name, elf, allow=NET, listen=None, dial=None, extra=None):
        env = dict(base_env, KEXE_ALLOW=allow)
        if listen is not None:
            env["KEXE_CAP_RESOURCES_43"] = listen
        if dial is not None:
            env["KEXE_CAP_RESOURCES_45"] = dial
        env.update(extra or {})
        x = subprocess.run([str(elf)], env=env, capture_output=True, timeout=120)
        (raw / (name + ".stdout")).write_bytes(x.stdout)
        (raw / (name + ".stderr")).write_bytes(x.stderr)
        return x

    # ---- part 1: the start-up check, with the compiler under test ----
    plain, _ = compile_(producer, "plain", PLAIN, target)
    # Use the product compiler, without test-only admission. Check numeric,
    # keyword and friendly spellings, as well as effect ceilings. In particular
    # net/write (wire 47) must not alias the legacy :state effect bit.
    admission_rows = []
    for wire, name in WIRES:
        op = "net/" + name.lower()
        for spelling, expression in (("numeric", f'(typed-cap-call {wire} :string :string "")'),
                                     ("keyword", f'(typed-cap-call :{op} :string :string "")'),
                                     ("friendly", f'({op} "")')):
            body = f'(ns a (:export [main]))\n(defn main [] :i64 (let [x {expression}] 7))\n'
            image, _ = compile_(producer, f'admit-{wire}-{spelling}', body, target)
            admission_rows.append(dict(wire=wire, spelling=spelling, image=pin(image)))
        for ceiling in ("#{}", "#{:state}"):
            body = f'(ns a (:export [main]))\n(defn main [] :i64 {{:effects {ceiling}}} (let [x (typed-cap-call {wire} :string :string "")] 7))\n'
            image, refused = compile_(producer, f'refuse-{wire}-{"pure" if ceiling == "#{}" else "state"}', body, target, success=False)
            assert refused.returncode != 0 and not image.exists() and b"E215" in refused.stderr, (wire, ceiling, refused)
            mask = 1 << (48 if wire == 47 else wire)
            # Static CLI prints the exact mask as detail; the full compiler
            # formats the corresponding effect name. Neither may report state.
            assert op.encode() in refused.stderr or f"detail {mask} ".encode() in refused.stderr, (wire, ceiling, refused.stderr)
            admission_rows.append(dict(wire=wire, ceiling=ceiling, refused=True))
        body = f'(ns a (:export [main]))\n(defn main [] :i64 {{:effects #{{:{op}}}}} (let [x (typed-cap-call {wire} :string :string "")] 7))\n'
        image, _ = compile_(producer, f'own-ceiling-{wire}', body, target)
        admission_rows.append(dict(wire=wire, ceiling=op, image=pin(image)))
    for wire in (43, 44, 45, 46, 47):
        image, refused = compile_(producer, f'wrong-kind-{wire}',
            f'(ns a (:export [main]))\n(defn main [] :i64 (let [x (typed-cap-call {wire} :i64 :i64 0)] 7))\n', target, success=False)
        assert refused.returncode != 0 and not image.exists() and b"E2115" in refused.stderr, (wire, refused)
    knob_rows = []

    def knob(name, allow, listen, dial, want_exit):
        x = run("knob-" + name, plain, allow, listen, dial)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout, x.stderr)
        if want_exit == 0:
            assert b":status :ok :result 42" in x.stdout, (name, x.stdout)
        knob_rows.append(dict(name=name, allow=allow, listen=listen, dial=dial, exit=x.returncode))

    seventeen = ",".join(f"127.0.0.1:{7000 + k}" for k in range(17))
    knob("not-an-address", NET, "x", None, 2)
    knob("no-port", NET, "127.0.0.1", None, 2)
    knob("port-zero", NET, "127.0.0.1:0", None, 2)
    knob("port-65536", NET, None, "127.0.0.1:65536", 2)
    knob("octet-256", NET, "256.0.0.1:80", None, 2)
    knob("three-octets", NET, None, "1.2.3:80", 2)
    knob("trailing-comma", NET, "127.0.0.1:80,", None, 2)
    knob("seventeen-entries", NET, seventeen, None, 2)
    knob("sixteen-entries", NET, ",".join(f"127.0.0.1:{7000 + k}" for k in range(16)), None, 0)
    knob("valid-both", NET, "127.0.0.1:7001,0.0.0.0:7002", "127.0.0.1:7001", 0)
    knob("absent", NET, None, None, 0)
    knob("empty", NET, "", "", 0)
    knob("not-granted-ignored", "37", "x", "y", 0)

    # ---- part 2: the wires, through the unmodified product compiler ----
    text, unity_pins = unity_text()
    admitted = text
    # the test-only compilers run here, so they are built for this host
    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    tc = producer
    c_rules, _ = compile_(producer, "control-compiler-no-net-rules", patched(admitted, [NO_NET_RULES]), host)
    c_socket, _ = compile_(producer, "control-compiler-other-socket", patched(admitted, OTHER_SOCKET), host)

    rows = []
    port = [7100]

    def e2e(name, source, want_exit=0, stdout_is=None, stderr_has=(), prod=tc, allow=NET, grant=True):
        p, q = port[0], port[0] + 1
        port[0] += 2
        elf, _ = compile_(prod, "e2e-" + name, source.format(p=p, q=q), target)
        x = run("e2e-" + name, elf, allow, A.format(p=p) if grant else None,
                f"{A.format(p=p)},{A.format(p=q)}" if grant else None)
        assert x.returncode == want_exit, (name, x.returncode, x.stdout[-300:], x.stderr[-300:])
        if stdout_is is not None:
            assert x.stdout.startswith(stdout_is + b"{:status :ok :result 7 "), (name, x.stdout)
        for s in stderr_has:
            assert s in x.stderr, (name, s, x.stderr[-300:])
        rows.append(dict(name=name, exit=x.returncode, stdout=x.stdout.decode(errors="replace"),
                         stderr=x.stderr.decode(errors="replace"), image=pin(elf)))

    e2e("round-trip", ROUND, stdout_is=b"1\n2\n3\n5\n68656c6c6f\nclosed\n\nclosed\n")
    e2e("accept-timeout", ACCEPT_TIMEOUT, stdout_is=b"timeout\n")
    e2e("read-timeout", READ_TIMEOUT, stdout_is=b"timeout\n")
    e2e("dial-refused", DIAL_REFUSED, stdout_is=b"refused\n")
    trap = b"KEXE_TRAP {:kind :capability :capability :net/"
    for name, source, wire, reason in REFUSALS:
        e2e(name, source, want_exit=126,
            stderr_has=[trap + wire.encode() + b" :reason :net/" + reason.encode() + b"}\n"])
    e2e("request-over-65536", one('(listen (string-concat "1" (dbl "1" 16)))'), want_exit=120,
        stderr_has=[b":signal :SIGILL"])
    e2e("wire-not-granted", one('(listen "127.0.0.1:{p}")'), want_exit=120, allow="37,44,45,46,47",
        stderr_has=[b":signal :SIGILL"])
    e2e("no-scope-granted", one('(listen "127.0.0.1:{p}")'), want_exit=126, grant=False,
        stderr_has=[trap + b"listen :reason :net/address-not-granted}\n"])
    enforced = not seccomp_if_available
    if enforced:
        e2e("control-no-net-rules", ROUND, want_exit=120, prod=c_rules, stderr_has=[b":signal :SIGSYS"])
        e2e("control-other-socket", ROUND, want_exit=120, prod=c_socket, stderr_has=[b":signal :SIGSYS"])
    report = dict(status="PASS_NET_RUNTIME", target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  executionNative=target.split("-")[0] == {"arm64": "aarch64", "AMD64": "x86_64"}.get(platform.machine(), platform.machine()),
                  imageSeccomp="if-available" if seccomp_if_available else "required",
                  checkerAcceptsWires43to47=True, admission=admission_rows, knob=knob_rows, wires=rows,
                  productCompiler=pin(tc),
                  testOnlyCompilers={"admission": "none; product compiler used unchanged",
                                     "controlNoNetRules": pin(c_rules), "controlOtherSocket": pin(c_socket)},
                  unity=unity_pins, cCompilerOrLoader=False,
                  notCovered=[] if enforced else ["the two seccomp controls: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"])
    (output / "net-runtime.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, len(knob_rows), "start-up cases", len(rows), "wire cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compiler", type=Path, required=True, help="an Amu-produced static compiler built from these sources")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="run the images with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve(), args.target, args.seccomp_if_available)
