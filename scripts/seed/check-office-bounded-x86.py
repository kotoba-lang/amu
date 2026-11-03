#!/usr/bin/env python3
"""Compare staged standard and experimental office ELFs on native x86 Linux.

The inputs are six selfhost-compiled single-source browser-entry programs.
This observes CLI snapshots and a synthetic file round trip, not OS storage,
CPL3 isolation, a browser, QEMU, production data, or a release verdict.
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apps', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--small-pair-mutant', type=Path)
    a = p.parse_args()
    assert (platform.system(), platform.machine()) == ('Linux', 'x86_64')
    apps, out = a.apps.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    env = dict(PATH='/nonexistent', KEXE_ALLOW='37,38', KEXE_STACK_BYTES='8388608', KEXE_FUEL='1000000000')
    evidence = {}
    for name, key in [('bunsho', 'b0'), ('hyokeisan', 'c0'), ('zuhyo', 'body')]:
        profiles = {}
        for profile in ('standard-v1', 'office-experiment-v1'):
            image = apps / (name + '-' + profile + '.elf')
            def call(args, expected=0):
                r = subprocess.run([str(image), *args], cwd=out, env=env, capture_output=True, timeout=120)
                assert r.returncode == expected and not r.stderr, (name, profile, args[0], r.returncode, r.stderr[-500:])
                return r.stdout
            initial = call(['init'])
            assert initial.endswith(b'\n')
            edited = call(['step', initial[:-1].decode(), key, 'input', '検証😀'])
            assert edited.endswith(b'\n') and '検証😀'.encode() in edited
            saved = out / (name + '-' + profile + '.snapshot')
            saved.write_bytes(edited[:-1])
            loaded = saved.read_text()
            view = call(['view', loaded])
            assert view.startswith(b'BV2|') and '検証😀'.encode() in view
            protected = call(['protect', loaded])
            assert protected == edited
            assert not call(['protect', 'malformed'], expected=2 if name == 'hyokeisan' else 3)
            profiles[profile] = dict(imageSha256=sha(image.read_bytes()),
                                     outputs=[sha(v) for v in (initial, edited, view, protected)])
        assert profiles['standard-v1']['outputs'] == profiles['office-experiment-v1']['outputs']
        evidence[name] = profiles
        print(name, 'PASS_INIT_EDIT_SYNTHETIC_SAVE_RELOAD_VIEW', flush=True)
    if a.small_pair_mutant:
        image = a.small_pair_mutant.resolve()
        state = (out / 'hyokeisan-standard-v1.snapshot').read_text()
        r = subprocess.run([str(image), 'view', state], cwd=out, env=env, capture_output=True, timeout=120)
        assert r.returncode == 120 and b':arena :pairs' in r.stderr and not r.stdout
        evidence['smallPairControl'] = dict(imageSha256=sha(image.read_bytes()), exit=r.returncode,
                                           stderrSha256=sha(r.stderr))
    (out / 'result.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print('PASS_OFFICE_BOUNDED_X86_PARITY', flush=True)


if __name__ == '__main__':
    main()
