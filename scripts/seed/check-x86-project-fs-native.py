#!/usr/bin/env python3
"""Observe explicitly declared FS35/CLI38 project calls and native refusals.

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
import time
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
    parser.add_argument('--derive', action='store_true', help='derive full47 experimental compiler and runner from the pinned native baseline')
    args = parser.parse_args()
    assert (platform.system(), platform.machine()) == ('Linux', 'x86_64')
    compiler, runner, out = args.compiler.resolve(), args.runner.resolve(), args.output.resolve()
    assert sha(compiler.read_bytes()) == args.compiler_sha256
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    observations = []
    derivation = None
    env = dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608')
    original = {p.name: p.read_bytes() for p in (ROOT / 'seed/tests/x86-project-fs').glob('*.kotoba')}

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

    def build(label, files, diagnostic=None):
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
        call(label, [compiler, 'compile', entry, '--target', 'x86_64-linux', '--output', artifact,
                     '--format', 'kx64-v1', '--source-path', root, '--source-lock', lock,
                     '--source-lock-sha256', sha(lock.read_bytes())],
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

    if args.derive:
        baseline = dict(sha256=sha(compiler.read_bytes()), bytes=compiler.stat().st_size)
        paths = [line for line in (ROOT / 'seed/FULL-MANIFEST').read_text().splitlines()
                 if line and not line.startswith('#')]
        assert len(paths) == 60 and 'seed/98-x86_64-project.kotoba' in paths
        replacement = 'seed/experimental/98-x86_64-project-fs-cli.kotoba'
        selected = [(name, replacement if name == 'seed/98-x86_64-project.kotoba' else name) for name in paths]
        full = out / 'full-candidate.kotoba'
        full.write_bytes(b''.join((ROOT / source).read_bytes() + b'\n' for _, source in selected))
        generations = []
        for index in (1, 2, 3):
            image = out / f'candidate-F{index}.elf'
            call(f'derive-F{index}', [compiler, 'compile', full, '--target', 'x86_64-linux',
                                    '--output', image, '--format', 'static'], timeout=900)
            image.chmod(0o700)
            generations.append(dict(sha256=sha(image.read_bytes()), bytes=image.stat().st_size))
            compiler = image
        assert generations[0] == generations[1] == generations[2], 'full47 fixed point'
        runner = out / 'candidate-runner.elf'
        runner_source = out / 'candidate-runner.kotoba'
        runner_source.write_bytes((ROOT / 'seed/x86_64-kx64-runner.kotoba').read_bytes())
        call('derive-runner', [compiler, 'compile', runner_source,
                              '--target', 'x86_64-linux', '--output', runner, '--format', 'kx64-runner'], timeout=900)
        runner.chmod(0o700)
        derivation = dict(baseline=baseline, generations=generations, sourceUnitySHA256=sha(full.read_bytes()),
                          selectedSources=[dict(module=name, source=source,
                                                sha256=sha((ROOT / source).read_bytes())) for name, source in selected])

    image = build('declared', original)
    base = out / 'scope'
    base.mkdir()
    def execute(label, target, allow, expected=0, resource_scope=None):
        scope = base if resource_scope is None else resource_scope
        custom = dict(env, KEXE_ALLOW=allow, KEXE_STRUCTURED_REPORT='1', KEXE_FUEL='10000000',
                      KEXE_CAP_RESOURCES_35=str(scope))
        return call(label, [runner, image, 0, 0, 'x86_64', allow, '--', target], custom, expected)
    passed = execute('roundtrip-clock-fs', base, '7,35,38')
    match = re.search(rb':result ([0-9]+)\b', passed.stdout)
    assert match, passed.stdout
    clock_ms = int(match[1])
    assert abs(clock_ms - int(time.time() * 1000)) <= 10000, clock_ms
    clock_refusal_scope = out / 'clock-refusal-scope'
    clock_refusal_scope.mkdir()
    missing_clock = execute('ungranted-clock', clock_refusal_scope, '35,38', 120,
                            resource_scope=clock_refusal_scope)
    assert b'KEXE_CAP {:wire 7 :refused :not-granted}' in missing_clock.stderr
    assert not list(clock_refusal_scope.iterdir()), 'clock refusal reached filesystem effects'
    missing = execute('ungranted-fs', base, '7,38', 120)
    assert b'KEXE_CAP {:wire 35 :refused :not-granted}' in missing.stderr
    missing_cli = execute('ungranted-cli', base, '7,35', 120)
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
        ('unsupported-wire', b':fs/app-data', b':io/write', b'E7101')]:
        files = dict(original)
        files['io.kotoba'] = files['io.kotoba'].replace(old, new)
        build(label, files, diagnostic)
    files = dict(original)
    files['entry.kotoba'] = files['entry.kotoba'].replace(
        b'(:capabilities [:clock/now :cli/args])', b'(:capabilities [:cli/args])')
    build('missing-clock-declaration', files, b'E2176')
    report = dict(status='PASS_EXPERIMENTAL_NATIVE_PROJECT_CLOCK7_FS35_CLI38',
                  compilerSHA256=sha(compiler.read_bytes()), runnerSHA256=sha(runner.read_bytes()),
                  sources={name: sha(data) for name, data in original.items()}, derivation=derivation,
                  observations=observations, publicProductAdopted=False)
    (out / 'evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], flush=True)

if __name__ == '__main__':
    main()
