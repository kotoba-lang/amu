#!/usr/bin/env python3
"""Observe the offline filter with a separately built no-filter mutant.

The host must permit basic socket creation, so a refusal from the worker is
not mistaken for an inherited host restriction. No network connection is made.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import socket
import struct
import subprocess


def read_one(proc):
    ready, _, _ = select.select([proc.stdout], [], [], 20)
    assert ready, 'worker timed out'
    return proc.stdout.read(1)


def probe(image):
    proc = subprocess.Popen([str(image)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={'PATH': '/nonexistent'}, bufsize=0)
    try:
        ready, _, _ = select.select([proc.stdout], [], [], 20)
        assert ready and proc.stdout.readline() == b'fune-private-root-ready\n'
        for op, size in ((b'F', 0), (b'P', 0o755)):
            proc.stdin.write(op + struct.pack('>HI', 3, size) + b'app')
            assert read_one(proc) == b'K'
        spec = b'FPS\x01' + struct.pack('>HHH', 1, 0, 1) + b'/' + struct.pack('>I', 4) + b'/app'
        proc.stdin.write(b'T' + struct.pack('>HI', 2, len(spec)) + spec)
        assert read_one(proc) == b'D'
        proc.stdin.write(b'N')
        result = read_one(proc)
        if result == b'K':
            proc.stdin.write(b'X')
        stdout, stderr = proc.communicate(timeout=20)
        return proc.returncode, result, stdout, stderr
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=20)


def main(worker, mutant, output):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64') and os.geteuid() != 0
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(worker) != digest(mutant)
    for family in (socket.AF_UNIX, socket.AF_INET, socket.AF_INET6):
        with socket.socket(family, socket.SOCK_STREAM):
            pass
    good, negative = probe(worker), probe(mutant)
    assert good == (0, b'K', b'', b''), good
    assert negative[0] == 2 and not negative[1] and not negative[2] and b'FREFUSE:24' in negative[3], negative
    result = {'status': 'PASS_FUNE_OFFLINE_FILTER_OBSERVATION', 'workerSHA256': digest(worker),
              'negativeControlSHA256': digest(mutant), 'hostSocketCreation': 'allowed',
              'workerAndForkSocketCreation': 'refused', 'mutantDetected': True,
              'ioUringAttributionIndependentlyQualified': False,
              'socketEscapeResistanceQualified': False, 'fullSyscallPolicyQualified': False}
    with output.open('x') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(result['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--negative-control', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.worker.resolve(), args.negative_control.resolve(), args.output.resolve())
