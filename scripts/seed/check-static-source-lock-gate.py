#!/usr/bin/env python3
"""Observe a native Kotoba static source-lock gate; this is not full qualification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import threading
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--compiler", required=True, type=Path)
    p.add_argument("--compiler-sha256", required=True)
    p.add_argument("--target", required=True, choices=("aarch64-linux", "x86_64-linux"))
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    expected_machine = {"aarch64-linux": ("aarch64", "arm64"), "x86_64-linux": ("x86_64", "AMD64")}
    if platform.system() != "Linux" or platform.machine() not in expected_machine[a.target]:
        raise RuntimeError("target requires its matching native Linux host")
    repo = a.repo.resolve(strict=True)
    compiler = a.compiler.resolve(strict=True)
    if digest(compiler) != a.compiler_sha256:
        raise RuntimeError("compiler digest mismatch")
    out = a.output.resolve()
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    root = out / "scope"
    root.mkdir(mode=0o700)
    gate_source = repo / "test/native/amu/test/static_source_lock_gate.kotoba"
    fixture = repo / "test/native/amu/test/fixtures/static_source_lock_good.kotoba"
    gate_source_hash, fixture_hash = digest(gate_source), digest(fixture)
    if any(":" in str(path) or "ARG_SEP" in str(path) for path in (compiler, root)):
        raise RuntimeError("paths cannot contain a grant or spawn delimiter")
    shutil.copyfile(gate_source, root / "gate.kotoba")
    shutil.copyfile(fixture, root / "good.kotoba")
    # The Kotoba gate hashes an embedded literal. Fail before execution if the
    # independently staged fixture no longer matches that literal bytewise.
    gate_text = gate_source.read_text()
    literal = re.search(r'\bsource\s+("(?:[^"\\]|\\.)*")', gate_text)
    if literal is None or json.loads(literal.group(1)).encode("utf-8") != fixture.read_bytes():
        raise RuntimeError("gate fixture literal differs from staged fixture")
    lock = root / "good.ksl"
    source = root / "good.kotoba"
    lock.write_text(f"KSL1\nentry {source}\nfile {digest(source)} {source}\n")
    lock_hash = digest(lock)
    gate = root / "gate.elf"
    env = {"PATH": "/nonexistent", "KEXE_CAP_RESOURCES_35": str(root), "KEXE_STACK_BYTES": "8388608"}
    command = [str(compiler), "compile", str(root / "gate.kotoba"), "--target", a.target,
               "--output", str(gate), "--format", "static"]
    built = subprocess.run(command, env=env, capture_output=True, timeout=240, check=False)
    (out / "build.stdout").write_bytes(built.stdout)
    (out / "build.stderr").write_bytes(built.stderr)
    if built.returncode or built.stderr or b":ok true" not in built.stdout or not gate.is_file():
        raise RuntimeError("gate build failed")
    gate.chmod(0o700)
    run_env = dict(env, KEXE_ALLOW="3,20,35,37,38,39", KEXE_STRUCTURED_REPORT="1",
                   KEXE_CAP_RESOURCES_20=f"{compiler}:{root / 'good.elf'}",
                   KEXE_SPAWN_ENV="KEXE_CAP_RESOURCES_35:KEXE_STACK_BYTES",
                   KEXE_FUEL="100000000")
    run = subprocess.run([str(gate), str(compiler), str(root), a.target, digest(lock)],
                         env=run_env, capture_output=True, timeout=240, check=False)
    (out / "run.stdout").write_bytes(run.stdout)
    (out / "run.stderr").write_bytes(run.stderr)
    if run.returncode or b":status :ok :result 0 " not in run.stdout:
        raise RuntimeError(f"gate refused: exit={run.returncode}; inspect saved logs")
    # The Kotoba gate checks both refusals and absence of output. Child stderr
    # is inherited by the gate; verify that both diagnostics name the target.
    if (run.stderr.count(f"--target {a.target}".encode()) != 2
            or b"--target aarch64-macos" in run.stderr):
        raise RuntimeError("refusal usage does not name the requested target")
    if (root / "bad.elf").exists() or not (root / "good.elf").is_file():
        raise RuntimeError("unexpected gate artifacts")
    # A structured host exit of zero must not hide a nonzero Kotoba result.
    # The gate rejects a digest that is not the fixture lock before spawning.
    negative = subprocess.run([str(gate), str(compiler), str(root), a.target, "0" * 64],
                              env=run_env, capture_output=True, timeout=240, check=False)
    (out / "wrong-digest.stdout").write_bytes(negative.stdout)
    (out / "wrong-digest.stderr").write_bytes(negative.stderr)
    if negative.returncode != 0 or b":status :ok :result 17 " not in negative.stdout:
        raise RuntimeError("wrong-digest negative control did not return result 17")
    if (root / "bad.elf").exists():
        raise RuntimeError("negative control created a refused artifact")
    # Keep the original digest pinned while changing the staged source. The
    # gate should stop at compilation (11), before producing or running ELF.
    changed_root = out / "changed-source"
    changed_root.mkdir(mode=0o700)
    changed_source = changed_root / "good.kotoba"
    changed = fixture.read_bytes().replace(b"(+ 40 2)", b"(+ 40 3)", 1)
    if changed == fixture.read_bytes():
        raise RuntimeError("source mutation anchor missing")
    changed_source.write_bytes(changed)
    changed_lock = changed_root / "good.ksl"
    changed_lock.write_text(f"KSL1\nentry {changed_source}\nfile {fixture_hash} {changed_source}\n")
    changed_env = dict(run_env, KEXE_CAP_RESOURCES_35=str(changed_root),
                       KEXE_CAP_RESOURCES_20=f"{compiler}:{changed_root / 'good.elf'}")
    changed_run = subprocess.run([str(gate), str(compiler), str(changed_root), a.target,
                                  digest(changed_lock)], env=changed_env, capture_output=True,
                                 timeout=240, check=False)
    (out / "changed-source.stdout").write_bytes(changed_run.stdout)
    (out / "changed-source.stderr").write_bytes(changed_run.stderr)
    if (changed_run.returncode != 0 or b":status :ok :result 11 " not in changed_run.stdout
            or (changed_root / "good.elf").exists() or (changed_root / "bad.elf").exists()):
        raise RuntimeError("changed-source negative control did not refuse before output")
    # Bounded stress, not an exhaustive or synchronized proof of interleavings.
    # Atomic renames ensure each read sees either the pinned or changed file.
    race_root = out / "source-swap"
    race_root.mkdir(mode=0o700)
    race_source = race_root / "good.kotoba"
    race_lock = race_root / "good.ksl"
    race_lock.write_text(f"KSL1\nentry {race_source}\nfile {fixture_hash} {race_source}\n")
    race_digest = digest(race_lock)
    race_env = dict(env, KEXE_CAP_RESOURCES_35=str(race_root))
    race_source.write_bytes(fixture.read_bytes())
    reference = race_root / "reference.elf"
    reference_run = subprocess.run([str(compiler), "compile", str(race_source), "--target", a.target,
                                    "--output", str(reference), "--format", "static", "--source-lock",
                                    str(race_lock), "--source-lock-sha256", race_digest],
                                   env=race_env, capture_output=True, timeout=240, check=False)
    (out / "race-reference.stdout").write_bytes(reference_run.stdout)
    (out / "race-reference.stderr").write_bytes(reference_run.stderr)
    if (reference_run.returncode != 0 or reference_run.stderr
            or b":ok true" not in reference_run.stdout or not reference.is_file()):
        raise RuntimeError("source-swap reference compilation failed")
    expected_elf = digest(reference)
    race_rows = []
    lock_bytes = race_lock.read_bytes()
    bad_lock = lock_bytes.replace(fixture_hash.encode(), ("0" * 64).encode(), 1)
    if bad_lock == lock_bytes:
        raise RuntimeError("lock mutation anchor missing")
    races = (("source", race_source, fixture.read_bytes(), changed),
             ("lock", race_lock, lock_bytes, bad_lock))
    for kind, subject, original_bytes, changed_bytes in races:
        race_source.write_bytes(fixture.read_bytes())
        race_lock.write_bytes(lock_bytes)
        for i in range(8):
          subject.write_bytes(original_bytes)
          stopped = threading.Event()
          first_swap = threading.Event()
          swaps = [0]
          errors = []

          def swap_source():
              try:
                  while not stopped.is_set():
                      candidate = race_root / "swap.tmp"
                      candidate.write_bytes(changed_bytes if swaps[0] % 2 == 0 else original_bytes)
                      os.replace(candidate, subject)
                      swaps[0] += 1
                      first_swap.set()
                      time.sleep(0.0005)
              except Exception as error:
                  errors.append(str(error))

          output = race_root / f"{kind}-{i}.elf"
          worker = threading.Thread(target=swap_source)
          worker.start()
          try:
              if not first_swap.wait(timeout=5):
                  raise RuntimeError(f"{kind} swap did not start")
              observed = subprocess.run([str(compiler), "compile", str(race_source), "--target", a.target,
                                         "--output", str(output), "--format", "static", "--source-lock",
                                         str(race_lock), "--source-lock-sha256", race_digest],
                                        env=race_env, capture_output=True, timeout=240, check=False)
          finally:
              stopped.set()
              worker.join()
          (out / f"{kind}-{i}.stdout").write_bytes(observed.stdout)
          (out / f"{kind}-{i}.stderr").write_bytes(observed.stderr)
          if errors or swaps[0] == 0:
              raise RuntimeError(f"source swap failed: {errors}")
          if observed.returncode == 0:
              if (observed.stderr or b":ok true" not in observed.stdout
                      or not output.is_file() or digest(output) != expected_elf):
                  raise RuntimeError(f"{kind} swap accepted a non-pinned output")
          elif (observed.returncode != 1 or b"E6015" not in observed.stderr
                or b":ok true" in observed.stdout or output.exists()):
              raise RuntimeError(f"{kind} swap did not refuse cleanly")
          race_rows.append({"kind": kind, "exit": observed.returncode, "swaps": swaps[0]})
        subject.write_bytes(original_bytes)
    if digest(race_lock) != race_digest:
        raise RuntimeError("source-swap lock changed")
    if (digest(compiler) != a.compiler_sha256 or digest(gate_source) != gate_source_hash
            or digest(fixture) != fixture_hash or digest(root / "gate.kotoba") != gate_source_hash
            or digest(source) != fixture_hash or digest(lock) != lock_hash):
        raise RuntimeError("compiler, gate source, fixture or lock changed during observation")
    report = {"status": "PASS_NATIVE_STATIC_SOURCE_LOCK_GATE", "target": a.target,
              "compiler_sha256": digest(compiler), "gate_sha256": digest(gate),
              "gate_source_sha256": gate_source_hash, "fixture_sha256": fixture_hash,
              "lock_sha256": lock_hash, "wrong_digest_result": 17,
              "changed_source_result": 11, "target_usage_refusals_checked": 2,
              "swap_stress": race_rows,
              "source_swap_reference_sha256": expected_elf,
              "concurrent_swap_qualified": False,
              "public_release_qualified": False}
    (out / "receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
