#!/usr/bin/env python3
"""Stage exact source locks and observe native reader tests; no host reader."""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def pin(path):
    return dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main(args):
    assert platform.system() == "Linux" and platform.machine() == "aarch64"
    repo = Path(__file__).resolve().parents[1]
    compiler, out = args.compiler.resolve(), args.output.resolve()
    assert pin(compiler)["sha256"] == args.compiler_sha256
    out.mkdir(parents=True, exist_ok=False)
    paths = ["test/kotoba/compiler/native_unicode_reader.kotoba", "src/kotoba/form.kotoba",
             "src/kotoba/compiler/kotoba_reader.kotoba", "src/kotoba/compiler/decimal_bits.kotoba"]
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_STACK_BYTES="8388608",
               KEXE_CAP_RESOURCES_35=":".join(map(str, [repo, out])))
    calls = []

    def run(name, argv, expected=0):
        result = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        (out / (name + ".stdout")).write_bytes(result.stdout)
        (out / (name + ".stderr")).write_bytes(result.stderr)
        calls.append(dict(name=name, exit=result.returncode))
        (out / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
        assert result.returncode == expected, (name, result.returncode, result.stdout[-500:], result.stderr[-1000:])
        if expected == 0:
            assert not result.stderr

    def build(name, root):
        entry = root / paths[0]
        lock, payload, image = [out / (name + extension) for extension in [".ksl", ".kseed", ".elf"]]
        lock.write_text("KSL1\nentry " + str(entry) + "\nroot " + str(root / "src") + "\n" +
                        "".join("file " + pin(root / path)["sha256"] + " " + str(root / path) + "\n" for path in sorted(paths)))
        run(name + "-compile", [compiler, "compile", entry, "--target", "aarch64-macos",
                               "--source-path", root / "src", "--source-lock", lock,
                               "--source-lock-sha256", pin(lock)["sha256"], "--output", payload])
        run(name + "-pack", [compiler, "compile", repo / "seed/x86_64-kx64-runner.kotoba",
                            "--target", "aarch64-linux", "--output", image, "--format", "packed", "--payload", payload])
        image.chmod(0o755)
        return image

    current = build("current", repo)
    run("current-execute", [current])
    previous = None
    if args.previous_reader:
        assert args.previous_reader_sha256 and pin(args.previous_reader)["sha256"] == args.previous_reader_sha256
        previous = out / "previous"
        for path in paths:
            target = previous / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((args.previous_reader if path.endswith("compiler/kotoba_reader.kotoba") else repo / path).read_bytes())
        prior_image = build("previous", previous)
        run("previous-execute-refused", [prior_image], 120)
        assert b"SIGILL" in (out / "previous-execute-refused.stderr").read_bytes()

    report = dict(status="PASS_NATIVE_UNICODE_FORM_READER", compiler=pin(compiler), image=pin(current),
                  inputs={path: pin(repo / path) for path in paths}, calls=calls,
                  previousReader=pin(args.previous_reader) if previous else None,
                  legacyHostExecuted=False, x86Executed=False, wholePublicCLIQualified=False)
    (out / "native-gate.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--compiler-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-reader", type=Path)
    parser.add_argument("--previous-reader-sha256")
    main(parser.parse_args())
