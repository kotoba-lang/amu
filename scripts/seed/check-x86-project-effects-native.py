#!/usr/bin/env python3
"""Observe opt-in FS35/CLI38 project effects, native grants and refusals.

An experimental compiler test, not public product/root adoption. Source and
native runtime own admission and filesystem results; Python stages/observes.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--compiler-sha256', required=True)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert (platform.system(), platform.machine()) == ('Linux', 'x86_64')
    compiler, runner, out = args.compiler.resolve(), args.runner.resolve(), args.output.resolve()
    assert sha(compiler.read_bytes()) == args.compiler_sha256
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    observations = []
    derivation = None
    env = dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608')
    original = {p.name: p.read_bytes() for p in (ROOT / 'seed/tests/x86-project-effects').glob('*.kotoba')}

    def call(label, argv, custom=env, expected=0, diagnostic=None, timeout=120):
        result = subprocess.run(list(map(str, argv)), env=custom, cwd=out, capture_output=True, timeout=timeout)
        (out / (label + '.stdout')).write_bytes(result.stdout)
        (out / (label + '.stderr')).write_bytes(result.stderr)
        assert result.returncode == expected, (label, result.returncode, result.stderr[-500:])
        if diagnostic:
            assert diagnostic in result.stderr and b'KEXE_TRAP' not in result.stderr, (label, result.stderr)
        elif expected == 0:
            assert not result.stderr, (label, result.stderr)
        observations.append(dict(name=label, exit=result.returncode,
                                 stdoutSHA256=sha(result.stdout), stderrSHA256=sha(result.stderr)))
        print(label, result.returncode, flush=True)
        return result

    def build(label, files, diagnostic=None, caps='35,38'):
        root = out / label / 'src'
        for name, data in files.items():
            path = root / 'x86_project_fs' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        entry = root / 'x86_project_fs/entry.kotoba'
        lock = out / (label + '.ksl')
        paths = sorted(root.glob('x86_project_fs/*.kotoba'))
        lock.write_text(f'KSL1\nentry {entry}\nroot {root}\n' + ''.join(
            f'file {sha(p.read_bytes())} {p}\n' for p in paths))
        artifact = out / (label + '.kx64')
        options = [] if caps is None else ['--project-capabilities', caps]
        call(label, [compiler, 'compile', entry, '--target', 'x86_64-linux', '--output', artifact,
                     '--format', 'kx64-v1', '--source-path', root, '--source-lock', lock,
                     '--source-lock-sha256', sha(lock.read_bytes()), *options],
             expected=1 if diagnostic else 0, diagnostic=diagnostic)
        if diagnostic:
            assert not artifact.exists()
            return None
        header, payload = artifact.read_bytes().split(b'\n\n', 1)
        match = re.fullmatch(rb'KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0', header)
        assert match and len(payload) == int(match[1]) and payload[0] == 0xe9
        image = out / (label + '.bin')
        image.write_bytes(payload)
        return image

    build('no-opt-in', original, b'E7101', caps=None)
    build('missing-cli', original, b'E7101', caps='35')
    image = build('declared', original)
    entry = out / 'declared/src/x86_project_fs/entry.kotoba'
    root = out / 'declared/src'
    lock = out / 'declared.ksl'
    reordered = out / 'reordered.kx64'
    call('option-before-lock', [compiler, 'compile', entry, '--target', 'x86_64-linux',
         '--project-capabilities', '35,38', '--output', reordered, '--format', 'kx64-v1',
         '--source-path', root, '--source-lock', lock, '--source-lock-sha256', sha(lock.read_bytes())])
    assert reordered.read_bytes() == (out / 'declared.kx64').read_bytes()
    args = [compiler, 'compile', entry, '--target', 'x86_64-linux', '--format', 'kx64-v1',
            '--source-path', root, '--source-lock', lock, '--source-lock-sha256', sha(lock.read_bytes())]
    for label, options in [
        ('unsorted', ['--project-capabilities', '38,35']),
        ('duplicate-wire', ['--project-capabilities', '35,35']),
        ('out-of-range', ['--project-capabilities', '48']),
        ('leading-zero', ['--project-capabilities', '035']),
        ('trailing-comma', ['--project-capabilities', '35,']),
        ('duplicate-flag', ['--project-capabilities', '35', '--project-capabilities', '38'])]:
        refused = out / (label + '.kx64')
        call(label, [*args, '--output', refused, *options], expected=2, diagnostic=b'E1')
        assert not refused.exists()
    net = dict(original)
    net['io.kotoba'] = b"""(ns x86-project-fs.io (:export [roundtrip]) (:capabilities [:net/write]))
(defn roundtrip [base :string] :bool (= (typed-cap-call 47 :string :string base) "x"))
"""
    build('network-not-opted-in', net, b'E7101', caps='38')
    network = build('network-opted-in', net, caps='38,47')
    net_env = dict(env, KEXE_ALLOW='38', KEXE_STRUCTURED_REPORT='1', KEXE_FUEL='10000000')
    denied = call('network-ungranted', [runner, network, 0, 0, 'x86_64', '38', '--', 'unused'], net_env, 120)
    assert b'KEXE_CAP {:wire 47 :refused :not-granted}' in denied.stderr
    base = out / 'scope'
    base.mkdir()
    def execute(label, target, allow, expected=0):
        custom = dict(env, KEXE_ALLOW=allow, KEXE_STRUCTURED_REPORT='1', KEXE_FUEL='10000000',
                      KEXE_CAP_RESOURCES_35=str(base))
        return call(label, [runner, image, 0, 0, 'x86_64', allow, '--', target], custom, expected)
    passed = execute('roundtrip', base, '35,38')
    assert re.search(rb':result 42\b', passed.stdout)
    missing = execute('ungranted-fs', base, '38', 120)
    assert b'KEXE_CAP {:wire 35 :refused :not-granted}' in missing.stderr
    missing_cli = execute('ungranted-cli', base, '35', 120)
    assert b'KEXE_CAP {:wire 38 :refused :not-granted}' in missing_cli.stderr
    outside = out / 'outside'
    outside.mkdir()
    refused = execute('outside-scope', outside, '35,38')
    assert re.search(rb':result 91\b', refused.stdout) and not list(outside.iterdir())
    os.symlink(outside, base / 'escape', target_is_directory=True)
    refused = execute('symlink-escape', base / 'escape', '35,38')
    assert re.search(rb':result 91\b', refused.stdout) and not list(outside.iterdir())
    for label, old, new, diagnostic in [
        ('missing-declaration', b'(:capabilities [:fs/app-data])', b'', b'E2176'),
        ('empty-declaration', b'(:capabilities [:fs/app-data])', b'(:capabilities [])', b'E2176'),
        ('mismatched-declaration', b'(:capabilities [:fs/app-data])', b'(:capabilities [:cli/args])', b'E2176'),
        ('unsupported-wire', b':fs/app-data', b':io/write', b'E7101')]:
        files = dict(original)
        files['io.kotoba'] = files['io.kotoba'].replace(old, new)
        build(label, files, diagnostic)
    report = dict(status='PASS_NATIVE_PROJECT_EFFECTS_FS35_CLI38',
                  compilerSHA256=sha(compiler.read_bytes()), runnerSHA256=sha(runner.read_bytes()),
                  sources={name: sha(data) for name, data in original.items()}, derivation=derivation,
                  observations=observations, publicProductAdopted=False)
    (out / 'evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], flush=True)

if __name__ == '__main__':
    main()
