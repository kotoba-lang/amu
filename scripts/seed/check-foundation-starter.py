#!/usr/bin/env python3
"""Stage starter sources and observe the real public native CLI and guests.

No compiler, evaluator, native image writer, installer or fallback is supplied
by this observer. This smoke check cannot replace complete selfhost/controller
qualification, external-user evidence or benchmark methodology.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples/foundation-starter"


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def host_profile(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise argparse.ArgumentTypeError(
            "use 1–64 lowercase ASCII letters, digits or hyphens; "
            "start with a letter or digit (e.g. linux-x86-64-ubuntu-24-04)"
        )
    return value


def main(output, profile, experimental_arm64=False):
    machine = "aarch64" if experimental_arm64 else "x86_64"
    target = "aarch64-linux" if experimental_arm64 else "x86_64-linux"
    require(platform.system() == "Linux" and platform.machine() == machine,
            f"starter host must be Linux {machine}; no emulation or fallback")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", profile), "invalid host profile label")
    descriptor_path = ROOT / "native-product.json"
    descriptor_pin = pin(descriptor_path)
    descriptor = json.loads(descriptor_path.read_text())
    require(descriptor["host"] == "x86_64-linux", "unexpected public host")
    require(descriptor["entry"] == "bin/amu-linux-x86_64", "unexpected public entry")
    compiler = ROOT / ("seed/bootstrap/aarch64-linux-static-root.elf" if experimental_arm64 else "bin/amu-linux-x86_64")
    compiler_pin = pin(compiler)
    arm_descriptor_path = ROOT / "seed/bootstrap/aarch64-linux-static-root.json"
    arm_descriptor_pin = pin(arm_descriptor_path) if experimental_arm64 else None
    arm_descriptor = json.loads(arm_descriptor_path.read_text()) if experimental_arm64 else None
    require(compiler_pin == (arm_descriptor["image"] if experimental_arm64 else descriptor["image"]),
            "compiler image digest/size mismatch")
    require(not descriptor["legacyRuntimeFallback"], "legacy fallback descriptor refused")
    candidate_path = FIXTURES / "candidate.json"
    candidate_pin = pin(candidate_path)
    candidate = json.loads(candidate_path.read_text())
    require(candidate["schema"] == "amu.foundation-starter.candidate.v1", "unknown starter schema")
    require(candidate["host"] == descriptor["host"], "starter/public host mismatch")
    require(candidate["compilerImage"] == descriptor["image"], "starter/compiler pin mismatch")
    if experimental_arm64:
        require(arm_descriptor["sourceUnity"] == descriptor["sourceUnity"] and
                arm_descriptor["sourceManifest"] == descriptor["sourceManifest"],
                "ARM root and public compiler source differ")
    manifest = ROOT / descriptor["sourceManifest"]
    sources = [line for line in manifest.read_text().splitlines()
               if line and not line.startswith("#")]
    require(len(sources) == descriptor["sourceModuleCount"], "compiler source count mismatch")
    unity = b"".join((ROOT / name).read_bytes() + b"\n" for name in sources)
    require({"bytes": len(unity), "sha256": hashlib.sha256(unity).hexdigest()} ==
            descriptor["sourceUnity"], "compiler source unity mismatch")
    require(candidate["compilerSourceUnity"] == descriptor["sourceUnity"],
            "starter/compiler source pin mismatch")
    output = output.resolve()
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    (output / "raw").mkdir()
    calls = []
    generated = {}
    fixtures = {name: pin(FIXTURES / name) for name in
                ("hello.kotoba", "sum.kotoba", "hash.kotoba")}
    require(candidate["fixtures"] == fixtures, "starter fixture digest/size mismatch")
    compile_env = {"PATH": "/nonexistent", "KEXE_ALLOW": "35,37,38,39",
                   "KEXE_CAP_RESOURCES_35": str(output), "KEXE_STACK_BYTES": "8388608"}

    def call(name, argv, expected, env, stdout_has=(), stderr_has=()):
        result = subprocess.run([str(p) for p in argv], cwd=output, env=env,
                                capture_output=True, timeout=120)
        (output / "raw" / (name + ".stdout")).write_bytes(result.stdout)
        (output / "raw" / (name + ".stderr")).write_bytes(result.stderr)
        require(result.returncode == expected,
                f"{name}: exit {result.returncode}, expected {expected}; see raw logs")
        for token in stdout_has:
            require(token in result.stdout, f"{name}: missing stdout token {token!r}")
        for token in stderr_has:
            require(token in result.stderr, f"{name}: missing stderr token {token!r}")
        calls.append({"name": name, "argv": [str(p) for p in argv],
                      "exit": result.returncode,
                      "stdoutSHA256": hashlib.sha256(result.stdout).hexdigest(),
                      "stderrSHA256": hashlib.sha256(result.stderr).hexdigest()})
        print(f"{name}: exit {result.returncode}", flush=True)
        return result

    def compile_source(name, text):
        source = output / (name + ".kotoba")
        source.write_text(text)
        lock = output / (name + ".ksl")
        lock.write_text(f"KSL1\nentry {source}\nfile {pin(source)['sha256']} {source}\n")
        locked = ["--source-lock", lock, "--source-lock-sha256", pin(lock)["sha256"]]
        call(name + "-check", [compiler, "check", source, *locked], 0, compile_env)
        image = output / (name + ".elf")
        source_pin = pin(source)
        # Compile the same single source under the pinned KSL1 lock.
        call(name + "-compile", [compiler, "compile", source, "--target", target,
                               "--output", image, "--format", "static", *locked], 0, compile_env)
        require(pin(source) == source_pin, f"{name}: staged source changed during compile")
        image.chmod(0o700)
        generated[name] = {"source": pin(source), "lock": pin(lock), "image": pin(image)}
        return source, lock, image

    def run_guest(name, image, value=None, *, fuel=1000000, allow="-", exit_code=0, errors=()):
        result = call(name, [image], exit_code,
                      {"PATH": "/nonexistent", "KEXE_ALLOW": allow,
                       "KEXE_FUEL": str(fuel), "KEXE_STRUCTURED_REPORT": "1"},
                      stderr_has=errors)
        if value is not None:
            match = re.search(rb":result (-?\d+)\b", result.stdout)
            require(match and int(match[1]) == value, f"{name}: unexpected native result")
        return result

    hello = (FIXTURES / "hello.kotoba").read_text()
    source, lock, image = compile_source("hello", hello)
    run_guest("hello-run", image, 42)
    require(hello.count("(+ 40 2)") == 1, "hello edit anchor changed")
    _, _, changed = compile_source("hello-changed", hello.replace("(+ 40 2)", "(+ 40 3)"))
    require(pin(image) != pin(changed), "editing source did not change emitted bytes")
    run_guest("hello-changed-run", changed, 43)
    sum_source = (FIXTURES / "sum.kotoba").read_text()
    _, _, summed = compile_source("sum", sum_source)
    run_guest("sum-run", summed, 55)
    run_guest("sum-low-fuel", summed, fuel=1, exit_code=120,
              errors=(b":budget/fuel",))
    require(sum_source.count("(> i 10)") == 1, "sum edit anchor changed")
    _, _, custom_sum = compile_source("sum-custom", sum_source.replace("(> i 10)", "(> i 20)"))
    run_guest("sum-custom-run", custom_sum, 210)
    _, _, hashed = compile_source("hash", (FIXTURES / "hash.kotoba").read_text())
    run_guest("hash-denied", hashed, exit_code=120,
              errors=(b"KEXE_CAP {:wire 3 :refused :not-granted}",))
    run_guest("hash-local-grant", hashed, 64, allow="3")
    call("lock-digest-denied", [compiler, "check", source, "--source-lock", lock,
                               "--source-lock-sha256", "0" * 64], 1, compile_env,
         stderr_has=(b"E6015",))
    bad_lock_output = output / "wrong-lock-static-refused.elf"
    call("locked-static-wrong-digest", [compiler, "compile", source, "--target", target,
         "--output", bad_lock_output, "--format", "static", "--source-lock", lock,
         "--source-lock-sha256", "0" * 64], 1, compile_env, stderr_has=(b"E6015",))
    require(not bad_lock_output.exists(), "wrong lock digest left an artifact")
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\n")
        changed_output = output / "changed-source-refused.elf"
        call("locked-static-changed-source", [compiler, "compile", source, "--target", target,
             "--output", changed_output, "--format", "static", "--source-lock", lock,
             "--source-lock-sha256", pin(lock)["sha256"]], 1, compile_env, stderr_has=(b"E6015",))
        require(not changed_output.exists(), "changed locked source left an artifact")
    finally:
        source.write_bytes(original)
    refused_output = output / "default-target-refused.elf"
    call("default-target-denied", [compiler, "compile", source, "--output", refused_output],
         1, compile_env, stderr_has=(b"E2",))
    require(not refused_output.exists(), "refused compile left an artifact")
    require(pin(compiler) == compiler_pin and pin(descriptor_path) == descriptor_pin,
            "compiler/descriptor changed during observation")
    if experimental_arm64:
        require(pin(arm_descriptor_path) == arm_descriptor_pin,
                "ARM descriptor changed during observation")
    require(pin(candidate_path) == candidate_pin, "starter manifest changed during observation")
    require(fixtures == {name: pin(FIXTURES / name) for name in fixtures},
            "starter source changed during observation")
    observation = {
        "schema": "amu.foundation-starter.observation.v1",
        "status": "PASS_STARTER_FUNCTIONAL_SMOKE",
        "qualificationReplacement": False, "publicReleaseReady": False,
        "experimentalArm64": experimental_arm64,
        "experimentalArmDescriptor": arm_descriptor_pin,
        "externalUsersObserved": 0,
        "host": {"profile": profile, "system": platform.system(),
                 "machine": platform.machine(), "kernel": platform.release()},
        "compilerImage": compiler_pin,
        # The descriptor revision is historical metadata, not proof that its
        # tree produces the current source unity or compiler image.
        "compilerSourceRevision": None,
        "publicDescriptorSourceRevision": descriptor["sourceRevision"],
        "starterCandidate": candidate_pin,
        "upstreamRevision": candidate["upstreamRevision"],
        "descriptor": descriptor_pin, "sourceUnity": descriptor["sourceUnity"],
        "descriptorQualification": {key: descriptor.get(key) for key in
                                    ("nativePinnedCheckAndCompile", "controllerQualified",
                                     "currentCompilerLinkVerified", "qualificationState")},
        "fixtures": fixtures, "generated": generated, "calls": calls,
        "observer": pin(Path(__file__)),
        "guestPATH": "/nonexistent", "legacyRuntimeFallback": False,
        "compilerEnforcedSourceLockAtCheck": True,
        "compilerEnforcedSourceLockAtStaticELFCompile": True,
        "wrongLockAndChangedSourceStaticCompileRefused": True,
        "scope": ("Experimental ARM root fixture smoke only; not a public ARM CLI. "
                  if experimental_arm64 else "Public CLI fixture smoke only; ") +
                 "Not self-rebuild/controller qualification,"
                 " independent third-party reproduction, OS/network acceptance or a benchmark."}
    (output / "starter-observation.json").write_text(json.dumps(observation, indent=2) + "\n")
    print(observation["status"], "public release qualification remains separate", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new output directory")
    parser.add_argument("--host-profile", type=host_profile, required=True,
                        help="non-identifying host/OS label (lowercase letters, digits, hyphens)")
    parser.add_argument("--experimental-arm64", action="store_true",
                        help="observe the pinned Linux ARM64 root; not a qualified public profile")
    args = parser.parse_args()
    main(args.output, args.host_profile, args.experimental_arm64)
