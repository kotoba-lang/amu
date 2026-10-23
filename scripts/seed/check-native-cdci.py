#!/usr/bin/env python3
"""Stage pinned bytes and exercise the native Kotoba CDCI controller.

Python transports files and records process observations. The sealed native
controller alone decides the Amu selfhost / complete24 Kotoba verdict.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = {"PATH": "/nonexistent"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    return sha(path.read_bytes())


def receipt(path, header):
    raw = path.read_bytes()
    body, digest, end = raw.rsplit(b"\n", 2)
    assert end == b"" and raw.startswith(header + b"\n")
    assert sha(body + b"\n").encode() == digest
    return dict(sha256=sha(raw), bodySHA256=digest.decode(), bytes=len(raw))


def main(complete, out):
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    proof = json.loads((complete / "complete-x86.json").read_text())
    assert proof["status"] == "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD"
    out.mkdir(parents=True, exist_ok=False)
    (out / "raw").mkdir()
    calls = []
    cases = json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]
    policy = json.loads((ROOT / "seed/cdci/policy.json").read_text())

    def stage(name):
        root = out / name
        root.mkdir(mode=0o700)
        for role in ("controller", "amu-selfhost", "kotoba-native"):
            src = complete / ("cdci-" + role + ".elf")
            assert pin(src) == proof["cdci"][role]["sha256"]
            shutil.copy2(src, root / (role + ".elf"))
            (root / (role + ".elf")).chmod(0o755)
        assert pin(root / "amu-selfhost.elf") == policy["amuSelfhostGateSHA256"]
        assert pin(root / "kotoba-native.elf") == policy["kotobaNativeGateSHA256"]
        modules = [p for p in (ROOT / "seed/MANIFEST").read_text().splitlines() if p and not p.startswith("#")]
        source = root / "core.kotoba"
        source.write_bytes(b"".join((ROOT / p).read_bytes() + b"\n" for p in modules))
        assert pin(source) == policy["coreSourceSHA256"]
        lock = root / "core.ksl"
        lock.write_text(f"KSL1\nentry {source}\nfile {pin(source)} {source}\n")
        combined = b"".join((ROOT / "seed/cdci" / p).read_bytes() for p in ("entry.kotoba", "runtime.kotoba", "kotoba-gate.kotoba"))
        (root / "kotoba-gate-source.kotoba").write_bytes(combined)
        assert sha(combined) == policy["kotobaGateSourceSHA256"]
        shutil.copy2(complete / "complete-x86.json", root / "provenance.json")
        lines = ["KCGATE1", str(root), pin(root / "kotoba-native.elf"), "24"]
        for i, (case, observed) in enumerate(zip(cases, proof["cases"], strict=True)):
            assert case["name"] == observed["name"]
            src, image = f"case-{i}.kotoba", f"case-{i}.elf"
            (root / src).write_text(case["source"])
            shutil.copy2(complete / ("case-" + case["name"] + ".elf"), root / image)
            (root / image).chmod(0o755)
            assert pin(root / image) == observed["image"]["sha256"]
            lines += [pin(root / src), pin(root / image), src, image,
                      str(0 if case["reference"]["exit"] else case["result"]),
                      str(case["reference"]["exit"]), str(case["reference"]["remainingFuel"])]
        assert len(lines) == 172
        (root / "cases.kcg").write_text("\n".join(lines) + "\n")
        lines = ["KCDCI1", str(root), pin(root / "controller.elf"), pin(root / "amu-selfhost.elf"),
                 pin(source), pin(lock), policy["coreContainerSHA256"], pin(root / "kotoba-native.elf"),
                 "amu-selfhost.elf", "core.kotoba", "core.ksl", "rebuilt.kseed", "kotoba-native.elf",
                 pin(root / "provenance.json"), "provenance.json", sha(combined), "kotoba-gate-source.kotoba",
                 pin(root / "cases.kcg"), "cases.kcg"]
        manifest = root / "controller.kcd"
        manifest.write_text("\n".join(lines) + "\n")
        return root, manifest, lines

    def run(name, argv, expected=0, timeout=60, diagnostic=None):
        started = time.monotonic()
        r = subprocess.run(list(map(str, argv)), env=ENV, cwd=out, capture_output=True, timeout=timeout)
        (out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        row = dict(name=name, exit=r.returncode, seconds=round(time.monotonic() - started, 3),
                   stdoutSHA256=sha(r.stdout), stderrSHA256=sha(r.stderr))
        calls.append(row)
        (out / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        assert r.returncode == expected, (name, r.returncode, r.stderr[-300:])
        if diagnostic:
            assert diagnostic.encode() in r.stderr, (name, r.stderr)
        elif expected == 0:
            assert not r.stderr, (name, r.stderr)
        return row

    # Exercise all actual result/exit/fuel checks before the expensive rebuild.
    root, manifest, lines = stage("gate-positive")
    run("gate-positive", [root / "kotoba-native.elf", root / "cases.kcg", pin(root / "cases.kcg")])
    gate_receipt = receipt(root / "kotoba-gate.receipt", b"KCGATE-R1")

    probes = [("wrong-manifest-pin", None, "CDCI:E2001"),
              ("extra-field", None, "CDCI:E1002"), ("nul-manifest", None, "CDCI:E1002"),
              ("missing-final-lf", None, "CDCI:E1002"),
              ("wrong-core-pin", (4, "0" * 64), "CDCI:E2001"),
              ("substitute-amu-image", (3, "0" * 64), "CDCI:E2001"),
              ("substitute-kotoba-image", (7, "0" * 64), "CDCI:E2001"),
              ("substitute-gate-source", (15, "0" * 64), "CDCI:E2001"),
              ("escaping-path", (9, "../core.kotoba"), "CDCI:E1002"),
              ("wire-control-path", (9, "core_SEP.kotoba"), "CDCI:E1002"),
              ("unknown-root-permissions", None, "CDCI:E1008"),
              ("symlink-source", None, "CDCI:E1003"),
              ("fifo-source", None, "CDCI:E1003"),
              ("non-executable-image", None, "CDCI:E2002"),
              ("existing-output", None, "CDCI:E1006")]
    for name, change, diagnostic in probes:
        root, manifest, lines = stage(name)
        if change:
            lines[change[0]] = change[1]
        raw = ("\n".join(lines) + "\n").encode()
        if name == "extra-field": raw += b"extra\n"
        if name == "nul-manifest": raw = raw.replace(b"KCDCI1", b"KCDCI\0")
        if name == "missing-final-lf": raw = raw[:-1]
        manifest.write_bytes(raw)
        if name == "unknown-root-permissions": root.chmod(0o755)
        if name == "symlink-source":
            (root / "core.kotoba").rename(root / "real.kotoba")
            (root / "core.kotoba").symlink_to("real.kotoba")
        if name == "fifo-source":
            (root / "core.kotoba").unlink()
            os.mkfifo(root / "core.kotoba")
        if name == "non-executable-image": (root / "amu-selfhost.elf").chmod(0o644)
        if name == "existing-output": (root / "rebuilt.kseed").write_bytes(b"preserve")
        digest = "0" * 64 if name == "wrong-manifest-pin" else pin(manifest)
        run(name, [root / "controller.elf", manifest, digest], 2, diagnostic=diagnostic)
        assert not (root / "cdci.receipt").exists()
        assert not (root / "amu.stdout").exists(), (name, "unexpected compiler execution")
    for field, value in ((8, "43"), (9, "1"), (10, "999998")):
        name = "gate-forged-field-" + str(field)
        root, _, _ = stage(name)
        ledger = root / "cases.kcg"
        lines = ledger.read_text().splitlines()
        lines[field] = value
        ledger.write_text("\n".join(lines) + "\n")
        run(name, [root / "kotoba-native.elf", ledger, pin(ledger)], 2, diagnostic="CDCI:E4002")
        assert not (root / "kotoba-gate.receipt").exists()

    # Cancellation must kill the native compiler child without a false receipt.
    root, manifest, _ = stage("parent-death")
    with (out / "raw/cancel.stdout").open("wb") as stdout, (out / "raw/cancel.stderr").open("wb") as stderr:
        p = subprocess.Popen([str(root / "controller.elf"), str(manifest), pin(manifest)], env=ENV, stdout=stdout, stderr=stderr)
        children = []
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and p.poll() is None:
                children = Path(f"/proc/{p.pid}/task/{p.pid}/children").read_text().split()
                if children: break
                time.sleep(0.05)
            assert children, "controller did not start its compiler child"
        finally:
            if p.poll() is None: p.kill()
            p.wait(timeout=10)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            running = [pid for pid in children if Path(f"/proc/{pid}/stat").exists() and Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1][0] != "Z"]
            if not running: break
            time.sleep(0.05)
        assert not running, ("compiler child survived controller death", running)
        assert not (root / "cdci.receipt").exists()

    root, manifest, _ = stage("positive")
    run("controller-positive", [root / "controller.elf", manifest, pin(manifest)], timeout=10900)
    assert pin(root / "rebuilt.kseed") == policy["coreContainerSHA256"]
    controller_receipt = receipt(root / "cdci.receipt", b"KCDCI-R1")
    receipt(root / "kotoba-gate.receipt", b"KCGATE-R1")
    report = dict(status="PASS_NATIVE_KOTOBA_CDCI", host=[platform.system(), platform.machine(), platform.release()],
                  controller=proof["cdci"]["controller"], compiler=proof["generations"][0],
                  policy=policy, controllerReceipt=controller_receipt, gateReceipt=gate_receipt,
                  manifestSHA256=pin(manifest), coreOutputSHA256=pin(root / "rebuilt.kseed"),
                  refusalCount=len(probes)+3, caseCount=24, parentDeathChildCleanup=True,
                  nativeVerdictAuthority=True, CLoader=False, NodeNBBJVMFallback=False)
    (out / "native-cdci.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "24 cases", report["refusalCount"], "refusals; parent-death cleanup", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--complete", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.complete.resolve(), a.output.resolve())
