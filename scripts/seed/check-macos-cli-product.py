#!/usr/bin/env python3
"""Observe ordinary native CLI commands and refusals, never compile in Python."""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check(cli, out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    spec = importlib.util.spec_from_file_location("mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    mac.verify_macho(cli)
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    before_tmp = set(Path('/private/tmp').glob('amu-*'))
    calls = []

    def run(name, *args, expected=0, stdout=None, diagnostic=None, image=None):
        start = time.monotonic()
        r = subprocess.run([str(image or cli), *map(str, args)], cwd=out,
                           env={"PATH": "/nonexistent", "LANG": "C", "AMU_TARGET": "bad-target"},
                           capture_output=True, timeout=150)
        for stream in ('stdout', 'stderr'):
            (out / (name + '.' + stream)).write_bytes(getattr(r, stream))
        assert r.returncode == expected, (name, r.returncode, r.stdout, r.stderr)
        if stdout is not None:
            assert r.stdout == stdout, (name, r.stdout)
        if diagnostic is not None:
            assert diagnostic in r.stderr, (name, r.stderr)
        elif expected == 0:
            assert not r.stderr, (name, r.stderr)
        calls.append(dict(name=name, exit=r.returncode, seconds=round(time.monotonic()-start, 3),
                          stdout=mac.pin(out / (name + '.stdout')), stderr=mac.pin(out / (name + '.stderr'))))
        return r

    def source(name, body):
        p = out / (name + '.kotoba')
        p.write_text('(ns hello (:export [main]))\n' + body + '\n')
        return p

    hello = source('hello', '(defn main [] :i64 42)')
    run('check', 'check', hello.name, stdout=b'ok\n')
    run('compile-default', 'compile', hello.name)
    mac.verify_macho(out / 'hello')
    run('execute-default', expected=0, stdout=b'42\n', image=out / 'hello')
    run('run-source', 'run', hello.name, stdout=b'42\n')
    run('run-artifact', 'run', './hello', stdout=b'42\n')
    first = (out / 'hello').read_bytes()
    hello.write_text('(ns hello (:export [main]))\n(defn main [] :i64 43)\n')
    run('changed-source', 'run', hello.name, stdout=b'43\n')
    run('old-artifact-independent', 'run', './hello', stdout=b'42\n')
    run('compile-explicit', 'compile', hello.name, '-o', 'hello43')
    run('run-43-artifact', 'run', 'hello43', stdout=b'43\n')
    assert (out / 'hello43').read_bytes() != first
    run('preserve-output', 'compile', hello.name, '-o', 'hello', expected=1, diagnostic=b'EOUTPUT')
    assert (out / 'hello').read_bytes() == first
    nested = out / 'space 日本語'
    nested.mkdir()
    unicode_source = nested / '試験.kotoba'
    unicode_source.write_bytes(hello.read_bytes())
    run('unicode-check', 'check', unicode_source, stdout=b'ok\n')
    run('unicode-compile', 'compile', unicode_source, '--output', nested / 'native 実行')
    run('unicode-run', 'run', nested / 'native 実行', stdout=b'43\n')
    for i, value in enumerate((0, -1, 256, 9223372036854775807, -9223372036854775808)):
        p = source('integer' + str(i), f'(defn main [] :i64 {value})')
        run('integer' + str(i), 'run', p.name, stdout=f'{value}\n'.encode())
    for name, body in {
        'string': '(defn main [] :string "hello")',
        'bool': '(defn main [] :bool true)',
        'parameter': '(defn main [x :i64] :i64 x)',
        'no-main': '(defn other [] :i64 42)',
        'invalid': '(defn main [] :i64 "bad")',
        'trailing-reader-discard': '(defn main [] :string "bad")\n#_',
    }.items():
        p = source(name, body)
        run('reject-' + name, 'compile', p.name, '-o', name + '.out', expected=1, diagnostic=b'EABI')
        assert not (out / (name + '.out')).exists()
    bad = source('bad', '(defn main [] :i64 "bad")')
    run('check-type-error', 'check', bad.name, expected=1, diagnostic=b'E')
    for i, args in enumerate((('compile', hello.name, '--target', 'x86_64-linux'),
                              ('check', hello.name, '--source-path', '.'),
                              ('run', hello.name, '--source-lock', 'missing'),
                              ('compile', hello.name, '-o'), ('garbage', hello.name))):
        run('usage' + str(i), *args, expected=2, diagnostic=b'usage:')
    for name, path in [('missing', out/'missing.kotoba'), ('directory', nested)]:
        run(name, 'run', path, expected=1, diagnostic=b'EINPUT')
    link = out / 'link.kotoba'
    link.symlink_to(hello)
    run('symlink', 'check', link.name, expected=1, diagnostic=b'EINPUT')
    fifo = out / 'fifo.kotoba'
    os.mkfifo(fifo)
    run('fifo', 'check', fifo.name, expected=1, diagnostic=b'EINPUT')
    big = out / 'big.kotoba'
    with big.open('wb') as f:
        f.truncate(1048577)
    run('oversize', 'check', big.name, expected=1, diagnostic=b'EINPUT')
    for i, at in enumerate((0, 1024, len(first)-1)):
        changed = bytearray(first)
        changed[at] ^= 1
        p = out / ('tampered' + str(i))
        p.write_bytes(changed)
        run('tampered' + str(i), 'run', p.name, expected=1, diagnostic=b'EARTIFACT')
    p = source('args', '(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string (typed-cap-call :cli/args :string :string "0"))] 42))')
    run('guest-argv', 'run', p.name, '--', 'hello 日本語', stdout='hello 日本語42\n'.encode())
    for name, cap, kind, payload in [('fs', ':fs/app-data-bytes', ':bytes', '(bytes-from-vector-i64 [0 70 83 50 0 65 120 0])'),
                                     ('process', ':process/spawn', ':string', '"anything"')]:
        p = source('deny-' + name, f'(defn main [] :i64 (let [r (typed-cap-call {cap} {kind} {kind} {payload})] 42))')
        r = subprocess.run([str(cli), 'run', str(p)], cwd=out, capture_output=True, timeout=150)
        (out / ('denied-' + name + '.stdout')).write_bytes(r.stdout)
        (out / ('denied-' + name + '.stderr')).write_bytes(r.stderr)
        assert r.returncode != 0 and r.stdout != b'42\n', (name, r.returncode, r.stdout, r.stderr)
        calls.append(dict(name='guest-grant-denied-' + name, exit=r.returncode))
    loop = source('loop', '(defn main [] :i64 (loop [i 0] (recur (+ i 1))))')
    run('deadline', 'run', loop.name, expected=124, diagnostic=b'ETIME')
    # Caller-controlled program bytes are recompiled and compared, never exec'd.
    marker = out / 'must-not-execute'
    fake = out / 'untrusted'
    fake.write_bytes(b'#!/bin/sh\ntouch ' + str(marker).encode() + b'\n')
    fake.chmod(0o700)
    run('untrusted-executable', 'run', fake, expected=1, diagnostic=b'EINPUT')
    assert not marker.exists()
    assert set(Path('/private/tmp').glob('amu-*')) == before_tmp, 'private CLI directories leaked'
    result = dict(schema='amu.macos-cli-product-observation.v1', status='PASS_ORDINARY_MACOS_CLI',
                  cli=mac.pin(cli), calls=calls, manualFD3=False, hostedFallback=False,
                  nativeResults=[42,43], nativeBuildRequired=True, independentUserQualified=False)
    (out / 'cli-product.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], len(calls), 'native observations')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cli', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    check(args.cli.resolve(), args.output.resolve())
