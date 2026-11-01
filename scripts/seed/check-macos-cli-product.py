#!/usr/bin/env python3
"""Observe ordinary native CLI commands and refusals, never compile in Python."""
import argparse
import importlib.util
import hashlib
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
    # KOTOBA-13: the public host stages a locked KSL2 namespace map,
    # verifies every original source digest, then asks the pinned Kotoba
    # compiler to check the rewritten project lock in its private FS2 root.
    project = out / 'locked-project'
    project.mkdir()
    app = project / 'app.kotoba'
    util = project / 'util.kotoba'
    app.write_text('(ns app (:require [util :as u]) (:export [main]))\n(defn main [] :i64 (u/add 41))\n')
    util.write_text('(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n')

    def project_lock(entry, modules, files):
        return ('KSL2\nentry ' + str(entry) + '\n'
                + ''.join('module ' + name + ' ' + str(path) + '\n' for name, path in modules)
                + ''.join('file ' + hashlib.sha256(path.read_bytes()).hexdigest() + ' ' + str(path) + '\n'
                          for path in sorted(files)))

    lock = project / 'project.ksl'
    lock.write_text(project_lock(app, [('app', app), ('util', util)], [app, util]))
    run('locked-project-check', 'check', app, '--source-lock', lock, stdout=b'ok\n')
    project_program = out / 'locked-project-program'
    run('locked-project-compile', 'compile', app, '--source-lock', lock, '-o', project_program.name,
        stdout=('compiled ' + str(project_program) + '\n').encode())
    mac.verify_macho(project_program)
    run('locked-project-native-execute', expected=0, stdout=b'42\n', image=project_program)
    project_program_bytes = project_program.read_bytes()
    run('locked-project-output-collision', 'compile', app, '--source-lock', lock, '-o', project_program.name,
        expected=1, diagnostic=b'EOUTPUT')
    assert project_program.read_bytes() == project_program_bytes
    run('locked-project-wrong-entry', 'check', util, '--source-lock', lock,
        expected=1, diagnostic=b'ELOCK entry does not match')
    run('locked-project-compile-wrong-entry', 'compile', util, '--source-lock', lock, '-o', 'wrong-entry-program',
        expected=1, diagnostic=b'ELOCK entry does not match')
    bad_utf8_lock = project / 'invalid-utf8.ksl'
    bad_utf8_lock.write_bytes(b'KSL2\n\xff\n')
    run('locked-project-invalid-utf8-lock', 'check', app, '--source-lock', bad_utf8_lock,
        expected=1, diagnostic=b'ELOCK source lock must be valid UTF-8')
    legacy = project / 'legacy.cljk'
    legacy.write_text(app.read_text())
    legacy_lock = project / 'legacy.ksl'
    legacy_lock.write_text(project_lock(legacy, [('app', legacy), ('util', util)], [legacy, util]))
    run('locked-project-non-kotoba-path', 'check', legacy, '--source-lock', legacy_lock,
        expected=1, diagnostic=b'ELOCK project files must use canonical .kotoba paths')
    util.write_text(util.read_text() + '\n')
    run('locked-project-changed-source', 'check', app, '--source-lock', lock,
        expected=1, diagnostic=b'EINPUT a locked project source')
    run('locked-project-compile-changed-source', 'compile', app, '--source-lock', lock, '-o', 'changed-source-program',
        expected=1, diagnostic=b'EINPUT a locked project source')
    util.write_text('(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n')

    missing = project / 'missing.kotoba'
    missing.write_text('(ns app (:require [absent :as a]) (:export [main]))\n(defn main [] :i64 (a/value))\n')
    missing_lock = project / 'missing.ksl'
    missing_lock.write_text(project_lock(missing, [('app', missing), ('util', util)], [missing, util]))
    run('locked-project-missing-import', 'check', missing, '--source-lock', missing_lock,
        expected=1, diagnostic=b'E')
    run('compile-default', 'compile', hello.name)
    mac.verify_macho(out / 'hello')
    run('execute-default', expected=0, stdout=b'42\n', image=out / 'hello')
    run('run-source', 'run', hello.name, stdout=b'42\n')
    run('run-artifact', 'run', './hello', stdout=b'42\n')
    # JUN-282: an opt-in run receipt binds source, host images, program and stdout
    run('run-receipt', 'run', hello.name, '--receipt', 'run-receipt.json', stdout=b'42\n')
    receipt = json.loads((out / 'run-receipt.json').read_text())
    assert receipt['schema'] == 'amu.run-receipt.v1' and receipt['exit'] == 0, receipt
    assert receipt['source'] == hashlib.sha256(hello.read_bytes()).hexdigest(), receipt
    assert receipt['stdout'] == hashlib.sha256(b'42\n').hexdigest(), receipt
    assert all(len(receipt[k]) == 64 for k in ('compiler', 'packager', 'program')), receipt
    kept = (out / 'run-receipt.json').read_bytes()
    run('run-receipt-exists', 'run', hello.name, '--receipt', 'run-receipt.json', expected=1, diagnostic=b'ERECEIPT')
    assert (out / 'run-receipt.json').read_bytes() == kept
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
    scoped = source('scoped', '(defn main [] :i64 (arena-scope (+ (arena-scope 40) 2)))')
    run('scoped-result', 'run', scoped.name, stdout=b'42\n')
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
                              ('compile', hello.name, '-o'), ('garbage', hello.name),
                              ('run', hello.name, '--receipt'), ('run', hello.name, '--receipt', 'r.json', 'extra'))):
        run('usage' + str(i), *args, expected=2, diagnostic=b'usage:')
    # removed with the C loader (docs/c-loader-removal.md): refused by name, not as unknown (JUN-282)
    for name in ('measure-runtime', 'package-ios', 'package-macos', 'test'):
        run('removed-' + name, name, hello.name, expected=2, diagnostic=b'EREMOVED ' + name.encode())
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
    isolated = out / 'provenance'
    isolated.mkdir()
    isolated_cli = isolated / 'amu-cli.macho'
    shutil.copy2(cli.resolve(), isolated_cli)
    run('missing-compiler', 'check', hello, expected=70, diagnostic=b'EPROVENANCE', image=isolated_cli)
    for name in ('amu-full-root.macho', 'kotoba-packager-root.macho'):
        shutil.copy2(cli.resolve().parent / name, isolated / name)
        with (isolated / name).open('r+b') as f:
            first_byte = f.read(1)
            f.seek(0)
            f.write(bytes([first_byte[0] ^ 1]))
        run('corrupted-' + name, 'check', hello, expected=70, diagnostic=b'EPROVENANCE', image=isolated_cli)
        shutil.copy2(cli.resolve().parent / name, isolated / name)
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
