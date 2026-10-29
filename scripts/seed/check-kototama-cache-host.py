#!/usr/bin/env python3
"""Stage local cache/admission processes and filesystem observations for a native verdict."""
import argparse
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("receipt_vectors", Path(__file__).with_name("check-kototama-receipt.py"))
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
SIZE = -9000000000000001


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cid(data):
    return "b" + base64.b32encode(bytes([1, 113, 18, 32]) + hashlib.sha256(data).digest()).decode().lower().rstrip("=")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--host", type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--deadline-control", action="store_true")
    a = p.parse_args()
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    compiler, host = out / "compiler.elf", out / "cache-host.elf"
    shutil.copy2(a.compiler, compiler); compiler.chmod(0o755)
    compiler_sha = digest(compiler)
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    root = Path(__file__).resolve().parents[2]
    for source, name in [("seed/cdci/entry.kotoba", "entry.kotoba"), ("seed/cdci/runtime.kotoba", "runtime.kotoba"), ("seed/cache/host.kotoba", "host.kotoba")]:
        shutil.copy2(root / source, out / name)

    def build_host(destination, compiler_pin):
        return subprocess.run([str(compiler), "kototama-cache-host-build", str(out / "entry.kotoba"), str(out / "runtime.kotoba"), str(out / "host.kotoba"),
                               "--compiler-sha256", compiler_pin, "--source-sha256", a.source_sha256, "--output", str(destination)], env=env, capture_output=True, timeout=180)

    if a.host:
        shutil.copy2(a.host, host)
    else:
        built = build_host(host, compiler_sha)
        assert built.returncode == 0, built.stderr[-2000:]
    host.chmod(0o755)
    cache = out / "cache"; cache.mkdir(mode=0o700)
    observations, expected, records = [], [], []

    def observe(name, actual, plan):
        observations.extend(actual); expected.extend(plan)
        records.append(dict(name=name, actual=actual, expected=plan))

    def call(name, body=None, budget=1, root=cache, overrides=None, pin=None, code=0, status=0, spent=1, value=42, marker="CACHE_HIT\n", diagnostic=None, selected=compiler, selected_host=host):
        source = out / (name + ".cbor"); source.write_bytes(r.v.encode(r.v.program(r.v.const(42) if body is None else body)))
        lines = ["KTI64RUN3", str(root), str(source), cid(source.read_bytes()), str(selected), compiler_sha if selected == compiler else digest(selected),
                 a.source_sha256, "x86_64-linux", str(budget), "262144", "0", "0", "0", "0", "none", "allow"]
        for i, v in (overrides or {}).items():
            lines[i] = v
        request = out / (name + ".request"); request.write_text("\n".join(lines) + "\n")
        result = subprocess.run([str(selected_host), str(request), digest(request) if pin is None else pin],
                                env={"PATH": "/nonexistent", "KEXE_ALLOW": "all", "KEXE_FUEL": "9007199254740991"},
                                capture_output=True, timeout=140)
        words = list(struct.unpack("<8q", result.stdout)) if len(result.stdout) == 64 else [0] * 8
        planned = [0] * 8 if code == 2 else [r.MAGIC, status, value if status == 0 else 0, budget, spent, budget - spent, 0, r.STACK]
        want_error = marker.encode() + (f"CDCI:E{diagnostic}\n".encode() if diagnostic else b"")
        actual = [result.returncode, len(result.stdout), *words, len(result.stderr), *result.stderr]
        plan = [code, 0 if code == 2 else 64, *planned, len(want_error), *want_error]
        observe(name, actual, plan)
        (out / (name + ".stdout")).write_bytes(result.stdout); (out / (name + ".stderr")).write_bytes(result.stderr)
        print(name, result.returncode, result.stderr.decode(errors="replace").strip(), flush=True)

    call("miss", marker="CACHE_MISS\n")
    image = cache / "slot-00/image.elf"; binding = cache / "slot-00/binding"
    initial, original_binding = image.read_bytes(), binding.read_bytes()
    call("hit-zero", budget=0, code=70, status=1)
    call("hit-above", budget=2)
    call("hit-max", budget=9007199254740991)
    with open("/dev/full", "wb") as full:
        request = out / "miss.request"
        failed = subprocess.run([str(host), str(request), digest(request)], env={"PATH": "/nonexistent"}, stdout=full, stderr=subprocess.PIPE, timeout=15)
    observe("receipt-relay-write-failure", [failed.returncode, len(failed.stderr), *failed.stderr], [74, 10, *b"CACHE_HIT\n"])
    observe("immutable-code", list(hashlib.sha256(image.read_bytes()).digest()), list(hashlib.sha256(initial).digest()))
    observe("cache-contents", [len(list(cache.iterdir())), len(list(image.parent.iterdir())), image.stat().st_mode & 511, binding.stat().st_mode & 511, len(initial)], [1, 2, 448, 384, SIZE])
    for name, index, val in [("denied", 15, "deny"), ("requested-capability", 11, "1"), ("cached-approval-refused", 12, "1"),
                             ("host-authority", 13, "1"), ("arena", 10, "1"), ("lease-refused", 14, "old-lease"),
                             ("cpu-mismatch", 7, "aarch64-linux"), ("profile-version", 0, "KTI64RUN4")]:
        call(name, overrides={index: val}, code=2, marker="", diagnostic=4401)
    for name, value in [("negative-fuel", "-1"), ("leading-zero-fuel", "01"), ("above-fuel", "9007199254740992")]:
        call(name, overrides={8: value}, code=2, marker="", diagnostic=4101)
    call("small-stack", overrides={9: "159"}, code=2, diagnostic=4401)
    call("above-stack", overrides={9: "262145"}, code=2, marker="", diagnostic=4101)
    call("request-pin", pin="0" * 64, code=2, marker="", diagnostic=4101)
    call("program-cid", overrides={3: "bafyreia"}, code=2, marker="", diagnostic=4104)
    call("compiler-pin", overrides={5: "0" * 64}, code=2, marker="", diagnostic=4104)
    call("compiler-source-pin", overrides={6: "0" * 64}, code=2, marker="", diagnostic=4104)
    locked = os.open(cache, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        call("concurrency", code=2, marker="", diagnostic=4302)
    finally:
        os.close(locked)
    image.write_bytes(initial[:-1] + bytes([initial[-1] ^ 1]))
    call("image-tamper", code=2, diagnostic=4104); image.write_bytes(initial)
    binding.write_bytes(original_binding.replace(b"expression-charge/v1", b"expression-charge/v0"))
    call("binding-tamper", code=2, marker="", diagnostic=4103); binding.write_bytes(original_binding)
    link = out / "hardlink.elf"; os.link(image, link)
    call("hardlink-refused", code=2, diagnostic=4102); link.unlink()
    image.write_bytes(bytes(1048577))
    call("image-size", code=2, diagnostic=1004); image.write_bytes(initial)
    cache.chmod(0o755)
    call("public-cache-refused", code=2, marker="", diagnostic=4102); cache.chmod(0o700)
    # A missing/replaced source or compiler never becomes a cache authorization.
    saved = compiler.read_bytes(); compiler.write_bytes(saved[:-1] + bytes([saved[-1] ^ 1]))
    call("compiler-tamper-on-hit", code=2, marker="", diagnostic=4104); compiler.write_bytes(saved)
    call("fresh-after-denial", budget=0, code=70, status=1)
    call("typed-division-fault", body=r.v.arith("div", r.v.const(1), r.v.const(0)), budget=3, code=70, status=2, spent=3, marker="CACHE_MISS\n")
    call("execution-deadline", body=["loop", [], ["recur", []]], budget=9007199254740991, code=2, marker="CACHE_MISS\n", diagnostic=4402)
    call("fresh-after-timeout", body=["loop", [], ["recur", []]], budget=0, code=70, status=1)
    refusal = out / "compiler-refusal"; refusal.mkdir(mode=0o700)
    call("compiler-refusal", body=["cap", "fs/app-data", []], root=refusal, code=2, marker="CACHE_MISS\n", diagnostic=4204)
    observe("compiler-refusal-cleanup", [len(list(refusal.iterdir()))], [0])
    call("fresh-after-compiler-refusal", root=refusal, marker="CACHE_MISS\n")
    quota = out / "quota"; quota.mkdir(mode=0o700)
    for i in range(16):
        call(f"slot-{i}", body=r.v.const(i), root=quota, value=i, marker="CACHE_MISS\n")
    call("capacity", body=r.v.const(16), root=quota, code=2, marker="CACHE_MISS\n", diagnostic=4301)
    observe("capacity-count", [len(list(quota.iterdir()))], [16])
    if a.deadline_control:
        source = out / "spin.cbor"; source.write_bytes(r.v.encode(r.v.program(["loop", [], ["recur", []]])))
        spin = out / "spin.elf"
        built = subprocess.run([str(compiler), "compile-kototama", str(source), "--target", "x86_64-linux", "--output", str(spin), "--fuel", "9007199254740991", "--profile", "kototama.pure-i64-receipt/v2"], env=env, capture_output=True, timeout=120)
        assert built.returncode == 0, built.stderr
        spin.chmod(0o755)
        call("unapproved-compiler", selected=spin, code=2, marker="", diagnostic=4104)
        # A separately pinned control host admits only this busy test image;
        # the production host above must refuse the identical compiler pin.
        control_host = out / "deadline-host.elf"; built = build_host(control_host, digest(spin))
        assert built.returncode == 0, built.stderr
        control_host.chmod(0o755); deadline = out / "deadline"; deadline.mkdir(mode=0o700)
        call("compile-deadline", root=deadline, selected=spin, selected_host=control_host, code=2, marker="CACHE_MISS\n", diagnostic=4203)
        observe("deadline-cleanup", [len(list(deadline.iterdir()))], [0])
    template = out / "host.kotoba"; saved = template.read_bytes(); template.write_bytes(saved + b"\n")
    refused = build_host(out / "unreviewed-host.elf", compiler_sha)
    observe("factory-source-pin", [refused.returncode, int((out / "unreviewed-host.elf").exists())], [1, 0]); template.write_bytes(saved)
    raw = struct.pack("<" + "q" * len(observations), *observations)
    gate_source = r.gate_source(expected).replace("KOTOTAMA_RECEIPT", "KOTOTAMA_CACHE_HOST")
    gate_source = gate_source.replace("(= actual want)))", "(if (= want -9000000000000001) (and (> actual 0) (<= actual 1048576)) (= actual want))))")
    (out / "gate.kotoba").write_text(gate_source); (out / "observations.bin").write_bytes(raw)
    gate = out / "gate.elf"; env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    built = subprocess.run([str(compiler), "compile", str(out / "gate.kotoba"), "--target", "x86_64-linux", "--output", str(gate), "--format", "static"], env=env, capture_output=True, timeout=180)
    assert built.returncode == 0, built.stderr[-2000:]
    gate.chmod(0o755); positive = subprocess.run([str(gate), str(out / "observations.bin")], env=env, capture_output=True, timeout=30)
    (out / "gate.stdout").write_bytes(positive.stdout); (out / "gate.stderr").write_bytes(positive.stderr)
    corrupt = bytearray(raw); corrupt[0] ^= 1; (out / "corrupt.bin").write_bytes(corrupt)
    negative = subprocess.run([str(gate), str(out / "corrupt.bin")], env=env, capture_output=True, timeout=30)
    (out / "corrupt.stdout").write_bytes(negative.stdout); (out / "corrupt.stderr").write_bytes(negative.stderr)
    report = dict(schema="amu.kototama-local-cache-host-native.v3", profile="kototama.pure-i64-cache/v3", hostTarget="x86_64-linux", records=records,
                  compilerSHA256=compiler_sha, compilerSourceSHA256=a.source_sha256, hostSHA256=digest(host),
                  hostFactorySources={name: digest(out / name) for name in ("entry.kotoba", "runtime.kotoba", "host.kotoba")},
                  verdictExit=positive.returncode, corruptControlExit=negative.returncode, signedRemoteHostQualified=False,
                  status="PASS" if (positive.returncode, negative.returncode) == (0, 1) else "FAIL")
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(records), positive.stdout, positive.stderr, flush=True)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
