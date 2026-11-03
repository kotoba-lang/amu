#!/usr/bin/env python3
"""Compare large synthetic office states with staged x86 static ELFs.

This measures selected Linux CLI operations, not browser/OS persistence,
QEMU execution, all valid inputs, real migration or production readiness.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def frame(s):
    return str(len(s.encode())) + ':' + s


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apps', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert (platform.system(), platform.machine()) == ('Linux', 'x86_64')
    apps, out = a.apps.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    env = dict(PATH='/nonexistent', KEXE_ALLOW='37,38', KEXE_STACK_BYTES='8388608', KEXE_FUEL='10000000000')
    bunsho = 'BS3|1' + ''.join(map(frame, ['題' * 341 + 'x', 'edit', '32'] + sum((['p', 'x' * 1024] for _ in range(32)), [])))
    def item(prefix, i):
        return (prefix + str(i) + '-').ljust(512, 'x')
    zuhyo = 'ZS1|' + ''.join(map(frame, ['題' * 170 + 'ab', 'edit', '0', '16'] + sum(([item('h', i), item('b', i), item('n', i), 'none'] for i in range(16)), [])))
    edn = lambda value: json.dumps(value, ensure_ascii=False)
    attrs = {':sheet/type': [edn('Spreadsheet')], ':sheet/id': [edn('sheet:book:demo')],
             ':sheet/slug': [edn('demo')], ':sheet/title': [edn('Wide')], ':sheet/revision': ['7'],
             ':sheet/sheetsJson': [edn('[{"sheetId":0,"title":"A"}]')],
             ':sheet/gridJson': [edn(json.dumps({'A': [['1'] * 1600]}, separators=(',', ':')))],
             ':sheet/unknown': [edn('保持')]}
    pull = json.dumps({'ok': True, 'graph': 'bfixture', 'entity': 'sheet:book:demo', 'attrs': attrs}, ensure_ascii=False, separators=(',', ':'))
    results = {}
    for name in ('bunsho', 'hyokeisan', 'zuhyo'):
        observed = {}
        for profile in ('standard-v1', 'office-experiment-v1'):
            image = apps / (name + '-' + profile + '.elf')
            def call(args):
                r = subprocess.run([str(image), *args], cwd=out, env=env, capture_output=True, timeout=180)
                assert r.returncode == 0 and not r.stderr, (name, profile, args[0], r.returncode, r.stderr[-500:])
                return r.stdout
            if name == 'hyokeisan':
                imported = call(['legacy-pull', pull])
                assert imported.endswith(b'\n')
                raw = imported[:-1].decode()
                key = 'c0'
            else:
                raw = bunsho if name == 'bunsho' else zuhyo
                imported = raw.encode()
                key = 'b31' if name == 'bunsho' else 'body'
            assert len(raw.encode()) <= 35000
            view = call(['view', raw])
            assert view.startswith(b'BV2|')
            edited = call(['step', raw, key, 'input', '最後😀'])
            assert '最後😀'.encode() in edited
            protected = call(['protect', raw])
            outputs = [imported, view, edited, protected]
            if name == 'hyokeisan':
                outputs.append(call(['formula-audit', raw]))
            observed[profile] = dict(imageSha256=sha(image.read_bytes()), outputs=[sha(x) for x in outputs], snapshotBytes=len(raw.encode()))
        assert observed['standard-v1']['outputs'] == observed['office-experiment-v1']['outputs']
        results[name] = observed
        print(name, 'PASS_LARGE_PROFILE_PARITY', flush=True)
    (out / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print('PASS_OFFICE_BOUNDED_LARGE_X86', flush=True)


if __name__ == '__main__':
    main()
