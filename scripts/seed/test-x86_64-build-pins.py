#!/usr/bin/env python3
"""Fault-injection test of orchestration only; never native/selfhost evidence."""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("cross_builder", ROOT / "scripts/seed/build-x86_64-linux.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    rows = []
    for fault in ("unity-source", "active-producer", "active-loader"):
        directory = output / fault

        def fake_child(argv, **kwargs):
            # Stand-ins are restricted to this fresh test directory. The real
            # repository inputs/bootstrap are read for pins and never modified.
            args = list(map(str, argv))
            if args[0] == "clang":
                Path(args[-1]).write_bytes(b"test-only loader")
            else:
                Path(args[-1]).write_bytes(b"test-only stable artifact")
                if fault == "unity-source" and args[-1].endswith("G1.kseed"):
                    (directory / "artifacts/seed-unity.kotoba").write_bytes(b"corrupted during compile")
                if fault == "active-producer" and args[-1].endswith("G2.kseed"):
                    (directory / "artifacts/G1.bin").write_bytes(b"corrupted active producer")
                if fault == "active-loader" and args[-1].endswith("G1.kseed"):
                    (directory / "host/kexe-loader").write_bytes(b"corrupted active loader")
            return subprocess.CompletedProcess(args, 0)

        with patch.object(builder.platform, "system", return_value="Darwin"), \
             patch.object(builder.platform, "machine", return_value="arm64"), \
             patch.object(builder.subprocess, "run", side_effect=fake_child):
            try:
                builder.build(directory)
            except SystemExit as exc:
                assert "changed during native invocation" in str(exc), exc
            else:
                raise AssertionError("mutation was accepted: " + fault)
        assert not (directory / "report.json").exists(), "fault created a PASS receipt"
        calls = json.loads((directory / "host/calls.json").read_text())
        last = calls[-1]
        assert last["invocationInputPins"] != last["inputPinsAfter"]
        rows.append({"fault": fault, "rejected": True, "call": last["name"]})
    record = {"status": "PASS_CROSS_BUILD_MUTATION_REFUSALS", "faults": rows,
              "mockOrchestrationOnly": True, "selfhostEvidence": False}
    (output / "report.json").write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"], len(rows), "faults")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    main(parser.parse_args().output.resolve())
