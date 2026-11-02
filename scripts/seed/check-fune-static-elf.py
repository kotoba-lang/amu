#!/usr/bin/env python3
"""Observe the worker's static ELF parser; no workload is executed here."""
import argparse
import ctypes
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


def deny_pread():
    code = (f.Filter * 4)(f.Filter(0x20, 0, 0, 0), f.Filter(0x15, 0, 1, 67),
                          f.Filter(0x06, 0, 0, 0x00050001), f.Filter(0x06, 0, 0, 0x7fff0000))
    program = f.Program(len(code), code)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        os._exit(125)


def main(worker, mutant, fixture, second_fixture, output):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64') and os.geteuid() != 0
    data = fixture.read_bytes()
    assert hashlib.sha256(data).hexdigest() == f.OUTPUT_EXPECTED
    second = second_fixture.read_bytes()
    assert hashlib.sha256(second).hexdigest() == f.EXPECTED and second != data
    ph = struct.unpack_from('<Q', data, 32)[0]
    base = struct.unpack_from('<Q', data, ph + 16)[0]
    first_filesz = struct.unpack_from('<Q', data, ph + 32)[0]

    def changed(offset, value, fmt):
        b = bytearray(data)
        struct.pack_into(fmt, b, offset, value)
        return bytes(b)

    cases = [('valid', data, True), ('truncated', data[:63], False),
             ('magic', changed(0, 0, '<B'), False), ('class', changed(4, 1, '<B'), False),
             ('endianness', changed(5, 2, '<B'), False), ('type', changed(16, 3, '<H'), False),
             ('machine', changed(18, 62, '<H'), False), ('header-size', changed(52, 63, '<H'), False),
             ('ph-entry-size', changed(54, 55, '<H'), False), ('ph-count', changed(56, 129, '<H'), False),
             ('ph-offset', changed(32, len(data)-1, '<Q'), False),
             ('interpreter', changed(ph+112, 3, '<I'), False), ('dynamic', changed(ph+112, 2, '<I'), False),
             ('write-execute', changed(ph+4, 7, '<I'), False),
             ('file-overrun', changed(ph+8, len(data), '<Q'), False),
             ('file-exceeds-memory', changed(ph+40, 1, '<Q'), False),
             ('invalid-align', changed(ph+48, 3, '<Q'), False),
             ('entry-outside', changed(24, 1, '<Q'), False)]
    bss = bytearray(data)
    struct.pack_into('<Q', bss, ph + 40, first_filesz + 4096)
    struct.pack_into('<Q', bss, 24, base + first_filesz)
    cases.append(('entry-in-bss', bytes(bss), False))

    def invoke(binary, image, nested=False, preexec=None, after=b'X'):
        spec = f.spec([b'/bin/app' if nested else b'/app'])
        prefix = f.frame(b'M', 'bin', 0) if nested else b''
        prefix += f.frame(b'F', 'bin/app' if nested else 'app', len(image), image)
        prefix += f.frame(b'P', 'bin/app' if nested else 'app', 0o755)
        wire = prefix + b'T' + struct.pack('>HI', 3 if nested else 2, len(spec)) + spec + b'A' + after
        return subprocess.run([str(binary)], input=wire, capture_output=True,
                              env={'PATH': '/nonexistent'}, preexec_fn=preexec, timeout=35)

    observations = []
    for name, image, valid in cases:
        proc = invoke(worker, image)
        if valid:
            assert proc.returncode == 0 and proc.stdout == f.READY + b'KKDK' and not proc.stderr, (name, proc.returncode, proc.stderr)
        else:
            assert proc.returncode == 2 and proc.stdout == f.READY + b'KKD' and b'FREFUSE:28' in proc.stderr, (name, proc.returncode, proc.stdout, proc.stderr)
        observations.append({'case': name, 'accepted': valid})
    nested = invoke(worker, data, True)
    assert nested.returncode == 0 and nested.stdout == f.READY + b'KKKDK' and not nested.stderr
    observations.append({'case': 'nested-path', 'accepted': True})
    other = invoke(worker, second)
    assert other.returncode == 0 and other.stdout == f.READY + b'KKDK' and not other.stderr
    observations.append({'case': 'second-executable', 'accepted': True})
    followed = invoke(worker, data, after=b'O')
    assert followed.returncode == 2 and followed.stdout == f.READY + b'KKDK' and b'FREFUSE:15' in followed.stderr
    observations.append({'case': 'preflight-then-output', 'accepted': False})
    denied = invoke(worker, data, preexec=deny_pread)
    assert denied.returncode == 2 and denied.stdout == f.READY + b'KKD' and b'FREFUSE:28' in denied.stderr
    observations.append({'case': 'pread-denied', 'accepted': False})
    assert hashlib.sha256(worker.read_bytes()).digest() != hashlib.sha256(mutant.read_bytes()).digest()
    control = invoke(mutant, changed(ph+112, 3, '<I'))
    assert control.returncode == 0 and control.stdout == f.READY + b'KKDK' and not control.stderr, 'interpreter-check mutant did not accept the control'
    report = {'status': 'PASS_FUNE_STATIC_ELF_OBSERVATION', 'workerSHA256': hashlib.sha256(worker.read_bytes()).hexdigest(),
              'fixtureSHA256': hashlib.sha256(data).hexdigest(), 'cases': observations,
              'secondFixtureSHA256': hashlib.sha256(second).hexdigest(),
              'mutantSHA256': hashlib.sha256(mutant.read_bytes()).hexdigest(), 'interpreterMutantDetected': True,
              'executionAuthorized': False, 'untrustedWorkloadIsolationQualified': False}
    with output.open('x') as file:
        json.dump(report, file, indent=2)
        file.write('\n')
    print(report['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--mutant', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--second-fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.worker.resolve(), args.mutant.resolve(), args.fixture.resolve(), args.second_fixture.resolve(), args.output.resolve())
