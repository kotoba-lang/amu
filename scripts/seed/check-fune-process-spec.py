#!/usr/bin/env python3
"""Observe FPS1 argv/env/cwd in a test-only digest-pinned executable.

The control worker pins the stack-observing fixture; the mutant additionally
drops all extra arguments and environment. Neither is a release artifact.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess

MODULE = Path(__file__).with_name('check-fune-fixture-exec.py')
loader = importlib.util.spec_from_file_location('fune_fixture_test', MODULE)
fixture_test = importlib.util.module_from_spec(loader)
loader.loader.exec_module(fixture_test)


def observe(worker, fixture, args, env, expected_args=None, expected_env=None):
    f = fixture_test
    spec = f.spec(args, env, b'/work')
    wire = (f.frame(b'M', 'work', 0) + f.frame(b'F', 'app', len(fixture), fixture)
            + f.frame(b'P', 'app', 0o755) + f.frame(b'P', 'work', 0o755)
            + b'T' + (4).to_bytes(2, 'big') + len(spec).to_bytes(4, 'big') + spec + b'OX')
    proc = subprocess.run([str(worker)], input=wire, capture_output=True,
                          env={'PATH': '/nonexistent'}, timeout=35)
    actual_args = args if expected_args is None else expected_args
    actual_env = env if expected_env is None else expected_env
    expected = (b''.join(b'A:' + x[:1024] + b'\n' for x in actual_args)
                + b''.join(b'E:' + x[:1024] + b'\n' for x in actual_env) + b'C:/work\n')
    frame = b'K\x07' + len(expected).to_bytes(4, 'big') + expected
    return (proc.returncode == 0 and proc.stdout == f.READY + b'KKKKD' + frame and not proc.stderr)


def main(worker, mutant, fixture, output):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64') and os.geteuid() != 0
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(worker) != sha(mutant)
    binary = fixture.read_bytes()
    cases = [('mixed', [b'/app', b'hello', b'', '世界'.encode()], [b'X=1', b'EMPTY=', b'OTHER=a=b']),
             ('counts', [b'/app'] + [b''] * 255, [b''] * 128),
             ('large-arg', [b'/app', b'z' * 65000], [b'X=1'])]
    for name, args, env in cases:
        assert observe(worker, binary, args, env), name
    assert observe(mutant, binary, cases[0][1], cases[0][2], [b'/app'], []), 'argument-drop mutant did not run as expected'
    assert not observe(mutant, binary, cases[0][1], cases[0][2]), 'argument-drop mutant was not detected'
    report = {'status': 'PASS_FUNE_PROCESS_SPEC_OBSERVATION', 'workerSHA256': sha(worker),
              'mutantSHA256': sha(mutant), 'fixtureSHA256': sha(fixture),
              'cases': [x[0] for x in cases], 'argumentDropMutantDetected': True,
              'generalWorkloadQualified': False}
    with output.open('x') as file:
        json.dump(report, file, indent=2)
        file.write('\n')
    print(report['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--mutant', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.worker.resolve(), args.mutant.resolve(), args.fixture.resolve(), args.output.resolve())
