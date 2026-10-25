#!/usr/bin/env python3
"""Hermes Python entrypoint for the Hy evidence collector."""
import os
import shutil
import sys
from pathlib import Path


hy_script = Path(__file__).with_name("jvmfree_test_evidence.hy")
hy_bin = os.environ.get("HY_BIN") or shutil.which("hy")
if not hy_bin:
    print("REFUSED Hy interpreter not found: set HY_BIN or install hy", file=sys.stderr)
    raise SystemExit(2)
if not hy_script.is_file():
    print(f"REFUSED Hy script not found: {hy_script}", file=sys.stderr)
    raise SystemExit(2)

os.execvp(hy_bin, [hy_bin, str(hy_script)])
