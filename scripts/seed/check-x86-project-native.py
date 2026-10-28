#!/usr/bin/env python3
"""Qualify locked typed project linking through the existing native KX64 runner.

No declaration is trimmed. The Kotoba fixture owns the result and exercises
multi-hop imports, literals in three modules, keyword identity, schema return,
eight arguments, a captured callback and document helpers across modules.
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main(compiler, out, compile_only=False):
    assert platform.system() == 'Linux'
    if not compile_only:
        assert platform.machine() == 'x86_64', 'native x86 Linux required'
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'src/x86_project'
    source.mkdir(parents=True)
    for path in (ROOT / 'seed/tests/x86-project').glob('*.kotoba'):
        shutil.copy2(path, source / path.name)
    entry = source / 'entry.kotoba'
    paths = sorted(source.glob('*.kotoba'))
    lock = out / 'project.ksl'
    lock.write_text('KSL1\nentry ' + str(entry) + '\nroot ' + str(source.parent) + '\n' +
                    ''.join('file ' + pin(p)['sha256'] + ' ' + str(p) + '\n' for p in paths))
    flags = ['--source-path', source.parent, '--source-lock', lock, '--source-lock-sha256', pin(lock)['sha256']]
    env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_CAP_RESOURCES_35=str(out))
    calls = []

    def run(name, args, custom=None, ok=True):
        started = time.monotonic()
        result = subprocess.run(list(map(str, args)), env=env if custom is None else custom,
                                cwd=out, capture_output=True, timeout=900)
        for suffix, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
            (out / (name + '.' + suffix)).write_bytes(data)
        calls.append(dict(name=name, exit=result.returncode, argv=list(map(str, args)),
                          seconds=round(time.monotonic()-started, 3)))
        (out / 'calls.json').write_text(json.dumps(calls, indent=2) + '\n')
        print(name, result.returncode, result.stderr.decode(errors='replace')[:400], flush=True)
        if ok:
            assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr[-1000:])
        return result

    run('check', [compiler, 'check', entry, *flags])
    artifact = out / 'project.kx64'
    run('compile', [compiler, 'compile', entry, '--target', 'x86_64-linux', '--output', artifact,
                    '--format', 'kx64-v1', *flags])
    header, body = artifact.read_bytes().split(b'\n\n', 1)
    match = re.fullmatch(rb'KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0', header)
    assert match and len(body) == int(match[1]) and body[0] == 0xe9
    payload = out / 'project.bin'
    payload.write_bytes(body)
    runner_source = out / 'runner.kotoba'
    shutil.copy2(ROOT / 'seed/x86_64-kx64-runner.kotoba', runner_source)
    runner = out / 'runner.elf'
    run('runner', [compiler, 'compile', runner_source, '--target', 'x86_64-linux',
                   '--output', runner, '--format', 'kx64-runner'])
    runner.chmod(0o755)
    observed = None
    if not compile_only:
        result = run('execute', [runner, payload, 0, 0, 'x86_64', '-'],
                     dict(env, KEXE_STRUCTURED_REPORT='1', KEXE_ALLOW='-'))
        value = re.search(rb':result (-?[0-9]+)', result.stdout)
        assert value and int(value[1]) == 42, result.stdout
        observed = 42

    refusal = out / 'refused.kx64'
    probes = [
        ('wrong-digest', [*flags[:-1], '0'*64], b'E6015'),
        ('missing-lock', ['--source-path', source.parent], b'E6015'),
        ('unlocked', [*flags, '--unpinned'], b'E6015'),
        ('wrong-format', [*flags, '--format', 'static'], b'E1'),
        ('unknown-option', [*flags, '--anything', '1'], b'E1')]
    refusals = []
    for name, options, diagnostic in probes:
        result = run(name, [compiler, 'compile', entry, '--target', 'x86_64-linux', '--output', refusal,
                            '--format', 'kx64-v1', *options], ok=False)
        assert result.returncode in (1, 2) and diagnostic in result.stderr and not refusal.exists(), (name, result.stderr)
        refusals.append(dict(name=name, diagnostic=diagnostic.decode(), noArtifact=True))
    # An unreachable bad declaration must still refuse before any artifact.
    original = (source / 'middle.kotoba').read_bytes()
    (source / 'middle.kotoba').write_bytes(original + b'\n(defn- unused [] :i64 (not-an-operation 1))\n')
    lock.write_text('KSL1\nentry ' + str(entry) + '\nroot ' + str(source.parent) + '\n' +
                    ''.join('file ' + pin(p)['sha256'] + ' ' + str(p) + '\n' for p in paths))
    result = run('unreachable-invalid', [compiler, 'compile', entry, '--target', 'x86_64-linux', '--output', refusal,
        '--format', 'kx64-v1', '--source-path', source.parent, '--source-lock', lock,
        '--source-lock-sha256', pin(lock)['sha256']], ok=False)
    assert result.returncode == 1 and b'E2101' in result.stderr and not refusal.exists()
    refusals.append(dict(name='unreachable-invalid', diagnostic='E2101', noArtifact=True))
    (source / 'middle.kotoba').write_bytes(original)
    report = dict(status='COMPILED_NOT_EXECUTED' if compile_only else 'PASS_LOCKED_X86_PROJECT_NATIVE',
        compiler=pin(compiler), artifact=pin(artifact), runner=pin(runner), result=observed,
        sources={p.name: pin(p) for p in paths}, refusals=refusals,
        emulation=False, nativeX86Qualified=not compile_only, cssomQualified=False, kernelDesktopQualified=False)
    (out / 'x86-project.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--compile-only', action='store_true', help='engineering code generation; never a native execution pass')
    a = p.parse_args()
    main(a.compiler.resolve(), a.output.resolve(), a.compile_only)
