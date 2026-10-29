#!/usr/bin/env python3
"""Stage immutable code/fresh-context observations; Amu's native gate judges them."""
import argparse
import base64
import hashlib
import importlib.util
import json
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("receipt_vectors", Path(__file__).with_name("check-kototama-receipt.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
PROFILE = "kototama.pure-i64-cache/v3"
CONTEXT = 0x003343343649544B


def cid(codec, data):
    return "b" + base64.b32encode(bytes([1, codec, 18, 32]) + hashlib.sha256(data).digest()).decode().lower().rstrip("=")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", type=Path, required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64", "x86_64")
    target = "x86_64-linux" if platform.machine() == "x86_64" else "aarch64-linux"
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    compiler = out / "compiler.elf"; shutil.copy2(a.compiler, compiler); compiler.chmod(0o755)
    compiler_sha = hashlib.sha256(compiler.read_bytes()).hexdigest()
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(out), "KEXE_STACK_BYTES": "8388608"}
    observations, expected, records, cached = [], [], [], {}
    zero = None

    def record(name, actual, plan):
        observations.extend(actual); expected.extend(plan)
        records.append(dict(name=name, actual=actual, expected=plan))

    for c in r.vectors():
        if c["name"].startswith("invalid-budget-"):
            continue  # textual CLI budgets belong to v2; v3 has a bounded binary context.
        cache_id = hashlib.sha256(c["wire"] + str([c.get(k) for k in ("existing", "profile", "target", "extra")]).encode()).hexdigest()
        if cache_id not in cached:
            n = len(cached); src, dst = out / f"{n:03d}.cbor", out / f"{n:03d}.elf"
            src.write_bytes(c["wire"])
            if c.get("existing"):
                dst.write_bytes(struct.pack("<q", 42))
            args = [str(compiler), "compile-kototama-cache", str(src), "--target", c.get("target", target),
                    "--output", str(dst), "--compiler-sha256", compiler_sha, "--source-sha256", a.source_sha256,
                    "--profile", c.get("profile", PROFILE), *c.get("extra", [])]
            built = subprocess.run(args, env=env, capture_output=True, timeout=120)
            (out / f"{n:03d}-compile.stdout").write_bytes(built.stdout)
            (out / f"{n:03d}-compile.stderr").write_bytes(built.stderr)
            lines = built.stdout.decode(errors="replace").splitlines()
            key = bytes.fromhex(lines[-3]) if built.returncode == 0 else bytes(32)
            cached[cache_id] = (dst, built, lines, key)
            if built.returncode == 0:
                dst.chmod(0o755)
                binding = ("\n".join(lines[:-3]) + "\n").encode()
                fixed_binding = ("\n".join(["KTI64CACHE3", cid(113, c["wire"]), compiler_sha, a.source_sha256, target,
                                           "kototama.vm/program-v1", "canonical-dag-cbor/ascii-bounded-v1", "i64-wrap/v1", "expression-charge/v1",
                                           PROFILE, "stdin72-receipt64/v3", "baseline-isa", "adopted-core-default", "imports-empty", "entry-zero-arity"]) + "\n").encode()
                # Reference hashes only stage fixed expectations. The native
                # verdict compares all observed bytes, including CID and key.
                pairs = [(lines[1].encode(), cid(113, c["wire"]).encode()),
                         (lines[-2].encode(), cid(85, dst.read_bytes()).encode()),
                         (hashlib.sha256(binding).digest(), hashlib.sha256(fixed_binding).digest()),
                         (key, hashlib.sha256(fixed_binding).digest())]
                for index, (actual, planned) in enumerate(pairs):
                    record(f"binding-{n}-{index}", list(actual), list(planned))
        dst, built, lines, key = cached[cache_id]
        context_denied = int(c["fuel"]) < 0 or int(c["fuel"]) > 9007199254740991
        refuse = c.get("refuse", False) and not context_denied
        data = struct.pack("<5q", CONTEXT, int(c["fuel"]), 262144, 0, 0) + key
        code, raw, error = -999, b"", b""
        if built.returncode == 0:
            guest = subprocess.run([str(dst)], input=data, env={"PATH": "/nonexistent", **c.get("guestEnv", {})}, capture_output=True, timeout=10)
            code, raw, error = guest.returncode, guest.stdout, guest.stderr
        words = list(struct.unpack("<8q", raw)) if len(raw) == 64 else [0] * 8
        plan = [0] * 8 if refuse or context_denied else [r.MAGIC, c["status"], c.get("result", 0), int(c["fuel"]), c["spent"], int(c["fuel"]) - c["spent"], 0, r.STACK]
        record(c["name"], [built.returncode, code, len(raw), *words, len(error)],
               [1 if refuse else 0, -999 if refuse else 76 if context_denied else 70 if c["status"] else 0, 0 if refuse or context_denied else 64, *plan, 0])
        if c["name"] == "const-budget-zero":
            zero = (dst, key)
        print(c["name"], built.returncode, code, flush=True)
    image, key = zero
    for name, budget, stack, arena, authority, magic, key_bytes, tail in [
        ("negative-budget", -1, 262144, 0, 0, CONTEXT, key, b""),
        ("above-budget", 9007199254740992, 262144, 0, 0, CONTEXT, key, b""),
        ("small-stack", 1, 159, 0, 0, CONTEXT, key, b""),
        ("above-stack", 1, 262145, 0, 0, CONTEXT, key, b""),
        ("arena", 1, 262144, 1, 0, CONTEXT, key, b""),
        ("authority", 1, 262144, 0, 1, CONTEXT, key, b""),
        ("wrong-magic", 1, 262144, 0, 0, CONTEXT ^ 1, key, b""),
        ("wrong-key", 1, 262144, 0, 0, CONTEXT, bytes(32), b""),
        ("trailing", 1, 262144, 0, 0, CONTEXT, key, b"x")]:
        data = struct.pack("<5q", magic, budget, stack, arena, authority) + key_bytes + tail
        guest = subprocess.run([str(image)], input=data, env={"PATH": "/nonexistent"}, capture_output=True, timeout=10)
        record(name, [guest.returncode, len(guest.stdout), len(guest.stderr)], [76, 0, 0])
    for n in [0, 1, 39, 40, 71]:
        guest = subprocess.run([str(image)], input=data[:n], env={"PATH": "/nonexistent"}, capture_output=True, timeout=10)
        record(f"truncated-{n}", [guest.returncode, len(guest.stdout), len(guest.stderr)], [76, 0, 0])
    packed = lambda xs: struct.pack("<" + "q" * len(xs), *xs)
    (out / "observations.bin").write_bytes(packed(observations))
    (out / "gate.kotoba").write_text(r.gate_source(expected).replace("KOTOTAMA_RECEIPT", "KOTOTAMA_CACHE_ABI"))
    gate = out / "gate.elf"
    built = subprocess.run([str(compiler), "compile", str(out / "gate.kotoba"), "--target", target, "--output", str(gate), "--format", "static"], env=env, capture_output=True, timeout=180)
    assert built.returncode == 0, built.stderr[-2000:]
    gate.chmod(0o755)
    positive = subprocess.run([str(gate), str(out / "observations.bin")], env=env, capture_output=True, timeout=30)
    (out / "gate.stdout").write_bytes(positive.stdout); (out / "gate.stderr").write_bytes(positive.stderr)
    corrupt = bytearray(packed(observations)); corrupt[0] ^= 1
    (out / "corrupt.bin").write_bytes(corrupt)
    negative = subprocess.run([str(gate), str(out / "corrupt.bin")], env=env, capture_output=True, timeout=30)
    (out / "corrupt.stdout").write_bytes(negative.stdout); (out / "corrupt.stderr").write_bytes(negative.stderr)

    def mutation_verdict(name, executable, context, record_name, receipt):
        mutant = out / (name + ".elf"); mutant.write_bytes(executable); mutant.chmod(0o755)
        ran = subprocess.run([str(mutant)], input=context, env={"PATH": "/nonexistent"}, capture_output=True, timeout=10)
        changed = []
        for item in records:
            actual = item["actual"]
            if item["name"] == record_name:
                if receipt:
                    words = list(struct.unpack("<8q", ran.stdout)) if len(ran.stdout) == 64 else [0] * 8
                    actual = [0, ran.returncode, len(ran.stdout), *words, len(ran.stderr)]
                else:
                    actual = [ran.returncode, len(ran.stdout), len(ran.stderr)]
            changed.extend(actual)
        path = out / (name + ".bin"); path.write_bytes(packed(changed))
        verdict = subprocess.run([str(gate), str(path)], env=env, capture_output=True, timeout=30)
        (out / (name + ".stdout")).write_bytes(verdict.stdout); (out / (name + ".stderr")).write_bytes(verdict.stderr)
        return verdict.returncode

    code = bytearray(image.read_bytes())
    needle = bytes.fromhex("498b4128490b41304885c00f85") if target == "x86_64-linux" else struct.pack("<III", 0xF94014E9, 0xF94018EA, 0xAA0A0129)
    site = code.find(needle); assert site >= 0
    if target == "x86_64-linux":
        code[site + 11:site + 17] = b"\x90" * 6
    else:
        struct.pack_into("<I", code, site + 12, 0xD503201F)
    admission = mutation_verdict("admission-removed", code, struct.pack("<5q", CONTEXT, 1, 262144, 0, 1) + key, "authority", False)
    code = bytearray(image.read_bytes())
    needle = bytes.fromhex("498b410848ffc849894108") if target == "x86_64-linux" else struct.pack("<III", 0xF94004F0, 0xF1000610, 0xF90004F0)
    site = code.find(needle); assert site >= 0
    if target == "x86_64-linux":
        code[site + 4:site + 7] = b"\x90" * 3
    else:
        struct.pack_into("<I", code, site + 4, 0xF1000210)
    metering = mutation_verdict("metering-removed", code, struct.pack("<5q", CONTEXT, 0, 262144, 0, 0) + key, "const-budget-zero", True)
    report = dict(schema="amu.kototama-cache-abi-native.v3", compilerSHA256=compiler_sha, compilerSourceSHA256=a.source_sha256, target=target,
                  records=records, distinctExecutables=len(cached), verdictExit=positive.returncode,
                  corruptControlExit=negative.returncode, cacheHostQualified=False,
                  admissionRemovalControlExit=admission, meteringRemovalControlExit=metering,
                  status="PASS" if (positive.returncode, negative.returncode, admission, metering) == (0, 1, 1, 1) else "FAIL")
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(records), positive.stdout, positive.stderr, flush=True)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
