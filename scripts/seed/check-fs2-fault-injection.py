#!/usr/bin/env python3
"""Fault injection for wire 35: the durable replace (fsync, rename) and the WRITE/APPEND forms (AWAI-52).

check-durable-sleep.py covers the replace (WRITE_SEP, FSYNC_SEP, RENAME_SEP) when the kernel calls
succeed. This gate makes one of them fail, by running the guest in a container under a seccomp
profile that returns an errno for one syscall, and requires the runtime to answer "0" with nothing
replaced:

  --fault none      the control: fsync answers 1, rename answers 1, the file reads "new"
  --fault fsync     fsync(2) -> EIO:     FSYNC_SEP answers 0
  --fault renameat  renameat(2) -> EPERM: RENAME_SEP answers 0, and the file still reads "orig"

The WRITE and APPEND forms answer the written text, or stop the guest (the runtime's fail-closed
trap) when the kernel refuses. Their cases start from a staged `old` = "orig" and do one request
whose text is TEXT[form] (37 bytes):

  --fault write-none   control: "<old>WRITE_SEP<text>" answers the text, the file reads the text
  --fault write        write(2) -> ENOSPC: the guest stops with nothing answered, and the file
                       reads "" (the form opens with O_TRUNC, so a failed WRITE leaves the file
                       truncated; replacing a file durably is the replace's job, not WRITE's)
  --fault append-none  control: "<old>APPEND_SEP<text>" answers the text, the file reads "orig<text>"
  --fault append       write(2) -> ENOSPC: the guest stops, the file still reads "orig"

The container runtime, Python and the compiler write too, so the write fault matches only a 37-byte
write(2) on fd >= 3: the file write of TEXT. The open flags cannot be matched (the runtime opens with
openat2, whose flags are behind a pointer), so WRITE and APPEND share the one write(2) fault.

The guest writes `old` = "orig" and `tmp` = "new", fsyncs `tmp`, renames it over `old`, and reads
`old` back, printing each answer. The image installs its own filter after the outer profile, so the
injected errno is what the runtime sees. Python stages, writes the profiles and observes; the runtime
and the guest are Kotoba. Run on Linux arm64 with the pinned static root, one fault per container:

  python3 scripts/seed/check-fs2-fault-injection.py --write-profile fsync OUT/fsync.json
  podman run --platform linux/arm64 --network none --security-opt seccomp=OUT/fsync.json \\
    -v REPO:/repo:ro -v OUT:/out python:3.12-slim python3 /repo/scripts/seed/check-fs2-fault-injection.py \\
    --compiler /repo/seed/bootstrap/aarch64-linux-static-root.elf --fault fsync --output /out/fsync
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "seed/x86_64-kx64-runner.kotoba"
ERRNO = {"fsync": 5, "renameat": 1, "write": 28}   # EIO, EPERM, ENOSPC
TEXT = {"write": "new" + "-" * 34, "append": "more" + "-" * 33}   # 37 bytes: the length the write fault matches
# case -> (form, injected syscall or None, answers, `old` on disk, exit code; 120 is the runtime trap)
CASES = {"none": ("replace", None, "1|1|new|", "new", 0),
         "fsync": ("replace", "fsync", "0|1|new|", "new", 0),
         "renameat": ("replace", "renameat", "1|0|orig|", "orig", 0),
         "write-none": ("write", None, TEXT["write"] + "|", TEXT["write"], 0),
         "write": ("write", "write", "", "", 120),
         "append-none": ("append", None, TEXT["append"] + "|", "orig" + TEXT["append"], 0),
         "append": ("append", "write", "", "orig", 120)}


def guest(scope, form):
    p = lambda rest: '"' + f"{scope}/{rest}" + '"'
    head = ('(ns t (:export [main]))\n'
            '(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n'
            '(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s "|"))] 0))\n')
    steps = [f'(fs {p("oldWRITE_SEPorig")})', f'(fs {p("tmpWRITE_SEPnew")})',
             f'(say (fs {p("tmpFSYNC_SEP")}))',
             f'(say (fs "{scope}/tmpRENAME_SEP{scope}/old"))',
             f'(say (fs {p("old")}))']
    if form != "replace":
        steps = [f'(say (fs {p("old" + ("WRITE_SEP" if form == "write" else "APPEND_SEP") + TEXT[form])}))']
    return head + "(defn main [] :i64\n  (let [" + " ".join(f"s{k} {x}" for k, x in enumerate(steps)) + "]\n    7))\n"


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def profile(fault):
    rule = {"names": [fault], "action": "SCMP_ACT_ERRNO", "errnoRet": ERRNO[fault]}
    if fault == "write":
        rule["args"] = [{"index": 0, "value": 3, "op": "SCMP_CMP_GE"},
                        {"index": 2, "value": len(TEXT["write"]), "op": "SCMP_CMP_EQ"}]
    return {"defaultAction": "SCMP_ACT_ALLOW", "architectures": ["SCMP_ARCH_AARCH64"], "syscalls": [rule]}


def main(compiler, fault, output):
    form, syscall, want, want_disk, want_exit = CASES[fault]
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64"), "run on Linux arm64"
    output.mkdir(parents=True, exist_ok=False)
    art, scope = output / "artifacts", output / "scope"
    art.mkdir()
    scope.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    (art / "guest.kotoba").write_text(guest(scope, form))
    if form != "replace":
        (scope / "old").write_text("orig")
    (art / "runner.kotoba").write_bytes(RUNNER.read_bytes())
    cenv = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(art), "KEXE_STACK_BYTES": "8388608"}
    for step, argv in [("compile", [producer, "compile", art / "guest.kotoba", "--target", "aarch64-macos", "--output", art / "guest.kseed"]),
                       ("pack", [producer, "compile", art / "runner.kotoba", "--target", "aarch64-linux", "--output", art / "guest.elf",
                                 "--format", "packed", "--payload", art / "guest.kseed"])]:
        r = subprocess.run(list(map(str, argv)), cwd=art, env=cenv, capture_output=True, timeout=1800)
        assert r.returncode == 0 and not r.stderr, (step, r.returncode, r.stderr[-400:])
    image = art / "guest.elf"
    image.chmod(0o755)
    env = {"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": "100000000",
           "KEXE_ALLOW": "35,37", "KEXE_CAP_RESOURCES_35": str(scope)}
    x = subprocess.run([str(image)], env=env, capture_output=True, timeout=120)
    answers = x.stdout.split(b"{:status", 1)[0].decode(errors="replace")
    assert x.returncode == want_exit and answers == want, (fault, x.returncode, answers, x.stderr[-300:])
    on_disk = (scope / "old").read_text()
    assert on_disk == want_disk, (fault, on_disk)
    report = dict(status="PASS_FS2_FAULT_INJECTION", fault=fault, form=form, exit=x.returncode,
                  answers=answers, oldOnDisk=on_disk,
                  compiler=pin(compiler), image=pin(image), runner=pin(RUNNER),
                  injected=None if syscall is None else profile(syscall),
                  host=[platform.system(), platform.machine(), platform.release()],
                  notCovered=["a power cut: an fsync that returns is what is checked, not the device",
                              "faults in the locked create/compare forms and the private store frames",
                              "a short write: the fault refuses the whole write(2), it does not shorten it"])
    (output / "fs2-fault-injection.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], fault, f"exit={x.returncode}", answers, "old=" + on_disk, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write-profile", nargs=2, metavar=("FAULT", "PATH"), help="write the seccomp profile for FAULT and exit")
    p.add_argument("--compiler", type=Path)
    p.add_argument("--fault", choices=tuple(CASES))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.write_profile:
        fault, path = a.write_profile
        assert fault in ERRNO, fault
        Path(path).write_text(json.dumps(profile(fault), indent=2) + "\n")
    else:
        assert a.compiler and a.fault and a.output, "--compiler, --fault and --output are required"
        main(a.compiler.resolve(), a.fault, a.output.resolve())
