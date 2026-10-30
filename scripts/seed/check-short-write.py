#!/usr/bin/env python3
"""Short writes for wire 35: the WRITE/APPEND forms and the KPV1 private-store frames (AWAI-52).

The seccomp fault gates (check-fs2-fault-injection.py, check-private-store-fault-injection.py)
refuse a whole write(2). This gate makes the kernel accept part of one: the guest runs with
RLIMIT_FSIZE at 14 bytes and SIGXFSZ ignored, so a 37-byte write first returns a short count and
the runtime's retry then gets EFBIG. Every form must refuse, and the gate pins the torn prefix it
leaves (`old`/`journal` starts as "orig\\n" except for the private create):

  form             limited                         unlimited (control)
  private create   exit 2, "0 1", 14 bytes of TEXT  exit 0, TEXT
  private append   exit 2, "0 1", "orig\\n" + 9      exit 0, "orig\\n" + TEXT
  WRITE_SEP        trap 120, 14 bytes of TEXT       exit 0, TEXT (WRITE truncates first)
  APPEND_SEP       trap 120, "orig\\n" + 9           exit 0, "orig\\n" + TEXT

No seccomp profile or container is needed: Python sets the limit in the child and observes.
The runtime and the guests are Kotoba. Run on Linux arm64 with the pinned static root:

  python3 scripts/seed/check-short-write.py --compiler seed/bootstrap/aarch64-linux-static-root.elf --output OUT
"""
import argparse
import hashlib
import json
import platform
import resource
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "seed/tests/private-store/probe.kotoba"
RUNNER = ROOT / "seed/x86_64-kx64-runner.kotoba"
TEXT = "x" * 36 + "\n"   # 37 bytes
LIMIT = 14
GUEST = ('(ns t (:export [main]))\n'
         '(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n'
         '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s "|"))] 0))\n'
         '(defn- arg [i :i64] :string (typed-cap-call :cli/args :string :string (string-from-i64 i)))\n'
         '(defn main [] :i64 (let [r (say (fs (arg 0)))] 7))\n')


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def limited():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))


def build(producer, art):
    cenv = {"PATH": "/nonexistent", "KEXE_STACK_BYTES": "8388608", "KEXE_CAP_RESOURCES_35": str(art)}
    (art / "probe.kotoba").write_bytes(PROBE.read_bytes())
    (art / "runner.kotoba").write_bytes(RUNNER.read_bytes())
    (art / "guest.kotoba").write_text(GUEST)
    for step, argv in [("probe", ["compile", art / "probe.kotoba", "--target", "aarch64-linux", "--output", art / "probe.elf", "--format", "static"]),
                       ("guest", ["compile", art / "guest.kotoba", "--target", "aarch64-macos", "--output", art / "guest.kseed"]),
                       ("pack", ["compile", art / "runner.kotoba", "--target", "aarch64-linux", "--output", art / "guest.elf",
                                 "--format", "packed", "--payload", art / "guest.kseed"])]:
        r = subprocess.run([str(producer), *map(str, argv)], cwd=art, env=cenv, capture_output=True, timeout=1800)
        assert r.returncode == 0 and not r.stderr, (step, r.returncode, r.stderr[-400:])
    for name in ("probe.elf", "guest.elf"):
        (art / name).chmod(0o755)
    return art / "probe.elf", art / "guest.elf"


def main(compiler, output):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on Linux arm64"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    probe, guest = build(producer, art)
    penv = {"PATH": "/usr/bin:/bin", "KEXE_ALLOW": "35,37,38,39", "KEXE_CAP_RESOURCES_35": str(output)}
    genv = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "100000000",
            "KEXE_ALLOW": "35,37,38", "KEXE_CAP_RESOURCES_35": str(output)}
    head = TEXT[:LIMIT - 5]
    # name -> (argv builder, env, staged content, limited (exit, journal), unlimited (exit, journal))
    cases = {
        "private create": (lambda f: [probe, "C", f, TEXT], penv, None, (2, TEXT[:LIMIT]), (0, TEXT)),
        "private append": (lambda f: [probe, "A", f, "orig\n", TEXT], penv, "orig\n", (2, "orig\n" + head), (0, "orig\n" + TEXT)),
        "WRITE_SEP": (lambda f: [guest, f"{f}WRITE_SEP{TEXT}"], genv, "orig\n", (120, TEXT[:LIMIT]), (0, TEXT)),
        "APPEND_SEP": (lambda f: [guest, f"{f}APPEND_SEP{TEXT}"], genv, "orig\n", (120, "orig\n" + head), (0, "orig\n" + TEXT)),
    }
    results = []
    for name, (argv, env, staged, short, control) in cases.items():
        for mode, (want_exit, want_disk) in (("limited", short), ("unlimited", control)):
            # numbered, not named: a directory called WRITE_SEP-... would put a second token in the request
            directory = output / f"case{len(results)}"
            directory.mkdir(mode=0o700)
            path = directory / "journal"
            if staged is not None:
                path.write_text(staged)
                path.chmod(0o600)
            x = subprocess.run(list(map(str, argv(path))), env=env, capture_output=True, text=True, timeout=30,
                               preexec_fn=limited if mode == "limited" else None)
            on_disk = path.read_text() if path.exists() else None
            assert (x.returncode, on_disk) == (want_exit, want_disk), (name, mode, x.returncode, x.stdout[-200:], x.stderr[-200:], on_disk)
            if name.startswith("private"):
                assert x.stdout == ("0 1 \n" if want_exit else "1 1 \n") and not x.stderr, (name, mode, x.stdout, x.stderr)
            elif want_exit:
                assert ":status :trap" in x.stdout and x.stdout.split("{:status", 1)[0] == "", (name, mode, x.stdout[:200])
            else:
                assert x.stdout.split("{:status", 1)[0] == TEXT + "|", (name, mode, x.stdout[:200])
            results.append(dict(form=name, mode=mode, exit=x.returncode, journal=on_disk))
    report = dict(status="PASS_SHORT_WRITE", limitBytes=LIMIT, results=results, compiler=pin(compiler),
                  probe=pin(probe), guest=pin(guest), host=[platform.system(), platform.machine(), platform.release()],
                  notCovered=["a power cut: a write the kernel accepted is what is checked, not the device",
                              "a short write followed by success: RLIMIT_FSIZE makes the retry fail with EFBIG"])
    (output / "short-write.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], " ".join(f"{r['form'].replace(' ', '-')}/{r['mode']}={r['exit']}" for r in results), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve())
