#!/usr/bin/env python3
"""Check that fixed-fixture execution fails closed when ELF pread is denied."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import struct
import subprocess

path = Path(__file__).with_name('check-fune-fixture-exec.py')
loader = importlib.util.spec_from_file_location('fune_fixture_test', path)
f = importlib.util.module_from_spec(loader)
loader.loader.exec_module(f)


def invoke(worker, data, preexec=None):
    spec = f.spec([b'/app'])
    wire = (f.frame(b'F', 'app', len(data), data) + f.frame(b'P', 'app', 0o755)
            + b'T' + struct.pack('>HI', 2, len(spec)) + spec + b'OX')
    return subprocess.run([str(worker)], input=wire, capture_output=True, preexec_fn=preexec,
                          env={'PATH': '/nonexistent'}, timeout=35)


def main(worker, mutant, fixture, output):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64') and os.geteuid() != 0
    data = fixture.read_bytes()
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha(fixture) == f.OUTPUT_EXPECTED and sha(worker) != sha(mutant)
    good = invoke(worker, data)
    assert good.returncode == 0 and good.stdout == f.READY + b'KKD' + f.OUTPUT_FRAME and not good.stderr
    denied = invoke(worker, data, f.deny_pread)
    assert denied.returncode == 2 and denied.stdout == f.READY + b'KKD' and b'FREFUSE:28' in denied.stderr
    control = invoke(mutant, data, f.deny_pread)
    assert control.returncode == 0 and control.stdout == f.READY + b'KKD' + f.OUTPUT_FRAME and not control.stderr
    result = {'status': 'PASS_FUNE_ELF_EXEC_OBSERVATION', 'workerSHA256': sha(worker),
              'mutantSHA256': sha(mutant), 'fixtureSHA256': sha(fixture),
              'preadDeniedBeforeExecution': True, 'skipPreflightMutantDetected': True,
              'generalWorkloadQualified': False}
    with output.open('x') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(result['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--mutant', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.worker.resolve(), args.mutant.resolve(), args.fixture.resolve(), args.output.resolve())
