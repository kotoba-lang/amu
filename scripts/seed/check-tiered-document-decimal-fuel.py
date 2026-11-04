#!/usr/bin/env python3
"""Qualify document and decimal positives and low-fuel traps with tiered native producers."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import subprocess


def pin(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'bootstrap', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    if platform.system() != 'Linux' or platform.machine() not in ('aarch64', 'arm64'):
        raise ValueError('requires a Linux arm64 execution host')
    repo, boot, out = a.repo.resolve(strict=True), a.bootstrap.resolve(strict=True), a.output.resolve()
    receipt_path = boot / 'selfhost-bootstrap.json'
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('status') != 'PASS_LOADERLESS_SELFHOST_BOOTSTRAP' or receipt.get('tier') not in ('pr', 'main', 'full'):
        raise ValueError('invalid bootstrap status')
    generation = receipt['generations'][-1]
    producer = boot / (generation['name'] + '.elf')
    if pin(producer) != generation['image']:
        raise ValueError('bootstrap F image mismatch')
    for group in (receipt['sourceGraph']['full'], receipt['adopted']['sourceGraph']):
        for name, expected in group.items():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or pin(repo / path) != expected:
                raise ValueError('bootstrap source drift: ' + name)
    c0 = None
    if receipt['tier'] == 'full':
        c0 = boot / 'C0.elf'
        if pin(c0) != receipt['provenance']['coreStatic']['C0']:
            raise ValueError('bootstrap C0 image mismatch')
        for name, expected in receipt['provenance']['coreStatic']['sourceGraph'].items():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or pin(repo / path) != expected:
                raise ValueError('bootstrap C0 source drift: ' + name)
    out.mkdir(parents=True, exist_ok=False)
    source = repo / 'seed/x86_64-kx64-runner.kotoba'
    tracked = [receipt_path, producer, source, repo / 'seed/float-cases.json',
               repo / 'seed/static-cases.json', Path(__file__).resolve()]
    if c0 is not None:
        tracked.append(c0)
    before = {str(p): pin(p) for p in tracked}
    (out / 'runner.kotoba').write_bytes(source.read_bytes())
    env = {'PATH': '/nonexistent', 'KEXE_CAP_RESOURCES_35': str(out), 'KEXE_STACK_BYTES': '8388608'}
    rows = []

    def run(name, args, overrides=None, expected=0):
        e = dict(env)
        if overrides:
            e.update(overrides)
        p = subprocess.run([str(x) for x in args], cwd=out, env=e, capture_output=True, timeout=900)
        (out / (name + '.stdout')).write_bytes(p.stdout)
        (out / (name + '.stderr')).write_bytes(p.stderr)
        if expected is not None and (p.returncode != expected or p.stderr):
            raise RuntimeError((name, p.returncode, p.stderr[-500:]))
        rows.append({'name': name, 'exit': p.returncode, 'stdout': pin(out / (name + '.stdout')),
                     'stderr': pin(out / (name + '.stderr'))})
        return p

    runner = out / 'runner.elf'
    run('runner-compile', [producer, 'compile', out / 'runner.kotoba', '--target', 'aarch64-linux', '--output', runner, '--format', 'runner'])
    runner.chmod(0o700)
    if pin(runner) != receipt['built']['aarch64Runner']:
        raise ValueError('fresh runner differs from bootstrap runner pin')

    def compile_payload(name, body, compiler=producer):
        source_file = out / (name + '.kotoba')
        source_file.write_text(body)
        container, raw = out / (name + '.kseed'), out / (name + '.bin')
        run(name + '-compile', [compiler, 'compile', source_file, '--target', 'aarch64-macos', '--output', container])
        run(name + '-extract', [compiler, 'extract-native', container, '--symbol', 'main', '--output', raw])
        return raw

    def execute(name, payload, fuel):
        return run(name, [runner, payload, '0', '0', 'aarch64', '35,37,38,39', '--'],
                   {'KEXE_COMMAND': '1', 'KEXE_STRUCTURED_REPORT': '1', 'KEXE_FUEL': str(fuel), 'KEXE_ALLOW': '-'}, expected=None)

    fixtures = [("document", repo / "test/fixtures/selfhost/document/native/document_runtime_test.kotoba"), ("decimal", repo / "test/fixtures/selfhost/decimal-literals/native/exact_literals_test.kotoba")]
    for _, source in fixtures:
        before[str(source)] = pin(source)
    def observe(producer_name, compiler, name, source):
        (out / (producer_name + '-' + name + '.kotoba')).write_bytes(source.read_bytes())
        tag = producer_name + '-' + name
        container = out / (tag + '.kseed')
        run(tag + '-compile', [compiler, 'compile', out / (tag + '.kotoba'), '--target', 'aarch64-macos', '--output', container])
        raw = out / (tag + '.bin')
        ex = run(tag + '-extract', [compiler, 'extract-native', container, '--symbol', 'main', '--output', raw])
        match = re.search(rb':offset (\d+), :length (\d+), :arity 0}', ex.stdout)
        if not match or int(match[2]) != raw.stat().st_size: raise ValueError('extract metadata mismatch')
        def invoke(suffix, fuel):
            return run(tag + '-' + suffix, [runner, raw, match[1].decode(), '0', 'aarch64', '35,37,38,39', '--'], {'KEXE_COMMAND':'1', 'KEXE_STRUCTURED_REPORT':'1', 'KEXE_FUEL':str(fuel), 'KEXE_ALLOW':'-'}, expected=None)
        normal = invoke('normal', 1000000000)
        if normal.returncode != 0 or normal.stderr or not re.search(rb':result 31\b', normal.stdout) or b':status :trap' in normal.stdout: raise ValueError((tag, 'normal', normal.returncode, normal.stdout[-400:], normal.stderr[-400:]))
        low = invoke('low-fuel', 1)
        if (low.returncode != 120 or b':status :trap' not in low.stdout or b':remaining 0}' not in low.stdout or
                b':budget/fuel' not in low.stderr or re.search(rb':result (-?[0-9]+)', low.stdout)): raise ValueError((tag, 'fuel', low.returncode, low.stdout[-400:], low.stderr[-400:]))
        print(tag, 'positive and low-fuel pass', flush=True)
        return {'producer':producer_name,'fixture':name,'source':pin(source),'normalExit':normal.returncode,'normalOutput':pin(out/(tag+'-normal.stdout')),'lowFuelExit':low.returncode,'lowFuelOutput':pin(out/(tag+'-low-fuel.stdout'))}
    results = [observe(tag, compiler, name, src) for tag, compiler in ([('F', producer)] + ([('C0', c0)] if c0 is not None else [])) for name,src in fixtures]
    if any(pin(p) != before[str(p)] for p in tracked): raise ValueError('source changed')
    report={'status':'PASS_TIERED_DOCUMENT_DECIMAL_POSITIVE_FUEL','compilerF':pin(producer),'compilerC0':pin(c0) if c0 is not None else None,'bootstrap':pin(receipt_path),'runner':pin(runner),'results':results,'fullCorpusQualified':False,'refusalsQualified':False}
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)

if __name__ == '__main__': main()
