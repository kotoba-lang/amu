#!/usr/bin/env python3
"""Stage and observe native reply-frame cases; Python does not evaluate Kotoba."""
import argparse
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "seed/darwin-watch-reply.kotoba"
CASES = ROOT / "seed/tests/awai152-darwin-watch/reply-cases.kotoba"
CLI = ROOT / "seed/bootstrap/aarch64-macos/amu-cli.macho"


def main(output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    source = SOURCE.read_text()
    declaration = "(ns amu.darwin-watch-reply (:export [darwin-watch-reply-class]))"
    assert source.count(declaration) == 1
    source = source.replace(declaration, "(ns watch-reply-test (:export [main]))")
    cases = CASES.read_text()
    tail = "\n(defn main [] :i64 (if (test-darwin-watch-reply) 42 7))\n"
    refusal = '"observer/bound-exit-observed" "observer/unknown"'
    assert source.count(refusal) == 1
    mutant = source.replace(refusal, '"observer/bound-exit-observed" "observer/bound-exit-observed"')
    for name, program, expected in (("real", source, b"42\n"), ("mutant", mutant, b"7\n")):
        path = output / (name + ".kotoba")
        path.write_text(program + "\n" + cases + tail)
        result = subprocess.run([str(CLI), "run", str(path)], cwd=output,
                                capture_output=True, timeout=150)
        if result.returncode != 0 or result.stdout != expected or result.stderr:
            raise RuntimeError((name, result.returncode, result.stdout, result.stderr))
        print(name, "sha256", hashlib.sha256(path.read_bytes()).hexdigest(), "output", expected.decode().strip())
    print("PASS_REPLY_CASES native frame classifier; not watcher or governor qualification")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    main(parser.parse_args().output.resolve())
