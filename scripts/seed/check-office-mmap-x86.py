#!/usr/bin/env python3
"""Observe Linux virtual mappings for three synthetic office CLI invocations.

strace observes only child processes. MAP_NORESERVE is virtual reservation,
not committed/resident memory or an AIUEOS user allocation. No production data.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apps', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--strace', type=Path, required=True)
    a = p.parse_args()
    assert (platform.system(), platform.machine()) == ('Linux', 'x86_64')
    apps, out, tracer = a.apps.resolve(), a.output.resolve(), a.strace.resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    env = dict(PATH='/nonexistent', KEXE_ALLOW='37,38', KEXE_STACK_BYTES='8388608', KEXE_FUEL='1000000000')
    result = {}
    for name in ('bunsho', 'hyokeisan', 'zuhyo'):
        profiles = {}
        for profile in ('standard-v1', 'office-experiment-v1'):
            image = apps / (name + '-' + profile + '.elf')
            def call(args, trace=None):
                argv = [str(image), *args]
                if trace is not None:
                    argv = [str(tracer), '-qq', '-e', 'trace=mmap,munmap', '-o', str(trace), *argv]
                r = subprocess.run(argv, cwd=out, env=env, capture_output=True, timeout=120)
                assert r.returncode == 0 and not r.stderr, (name, profile, args[0], r.returncode, r.stderr[-500:])
                return r.stdout
            state = call(['init'])
            assert state.endswith(b'\n')
            cases = {}
            for op, args in [('init', ['init']), ('view', ['view', state[:-1].decode()])]:
                plain = call(args)
                trace = out / (name + '-' + profile + '-' + op + '.trace')
                assert call(args, trace) == plain
                lines = trace.read_text().splitlines()
                allocations = []
                for line in lines:
                    if line.startswith('mmap('):
                        match = re.fullmatch(r'mmap\(NULL, (\d+), .*\) = (0x[0-9a-f]+)', line)
                        assert match and 'MAP_NORESERVE' in line, line
                        allocations.append(int(match.group(1)))
                    else:
                        assert line.startswith('munmap('), line
                cases[op] = dict(stdoutSha256=sha(plain), allocations=len(allocations),
                                 virtualBytes=sum(allocations), largestBytes=max(allocations),
                                 sizes=allocations)
            profiles[profile] = dict(imageSha256=sha(image.read_bytes()), operations=cases)
        for op in ('init', 'view'):
            assert profiles['standard-v1']['operations'][op]['stdoutSha256'] == profiles['office-experiment-v1']['operations'][op]['stdoutSha256']
        result[name] = profiles
        print(name, 'PASS_TRACED_AND_UNTRACED_MATCH', flush=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS_OFFICE_MMAP_OBSERVATION', flush=True)


if __name__ == '__main__':
    main()
