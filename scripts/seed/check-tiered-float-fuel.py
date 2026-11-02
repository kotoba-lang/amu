#!/usr/bin/env python3
"""Observe float results and fuel using a pinned tiered native bootstrap.

This is a bounded F/runner test; it does not claim C0 executed these cases,
complete compiler adoption, CDCI qualification, or performance.
"""
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
    out.mkdir(parents=True, exist_ok=False)
    source = repo / 'seed/x86_64-kx64-runner.kotoba'
    tracked = [receipt_path, producer, source, repo / 'seed/float-cases.json',
               repo / 'seed/static-cases.json', Path(__file__).resolve()]
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

    def compile_payload(name, body):
        source_file = out / (name + '.kotoba')
        source_file.write_text(body)
        container, raw = out / (name + '.kseed'), out / (name + '.bin')
        run(name + '-compile', [producer, 'compile', source_file, '--target', 'aarch64-macos', '--output', container])
        run(name + '-extract', [producer, 'extract-native', container, '--symbol', 'main', '--output', raw])
        return raw

    def execute(name, payload, fuel):
        return run(name, [runner, payload, '0', '0', 'aarch64', '35,37,38,39', '--'],
                   {'KEXE_COMMAND': '1', 'KEXE_STRUCTURED_REPORT': '1', 'KEXE_FUEL': str(fuel), 'KEXE_ALLOW': '-'}, expected=None)

    corpus = repo / 'seed/float-cases.json'
    cases = json.loads(corpus.read_text())['cases']
    if len(cases) != 11:
        raise ValueError('float corpus changed')
    results = []
    for case in cases:
        name = case['name']
        if not re.fullmatch('[a-z0-9-]+', name):
            raise ValueError('invalid case name')
        payload = compile_payload(name, case['source'])
        p = execute(name + '-run', payload, 1000000)
        fuel = re.search(rb':remaining ([0-9]+)', p.stdout)
        result = re.search(rb':result (-?[0-9]+)', p.stdout)
        observed = {'exit': p.returncode, 'remainingFuel': int(fuel[1]) if fuel else None}
        if p.stderr or observed != case['reference'] or case['trap'] or result is None or int(result[1]) != case['result'] or b':status :trap' in p.stdout:
            raise ValueError(('float result/fuel mismatch', name, observed, p.stdout[-500:], p.stderr[-500:]))
        results.append({'name': name, 'observed': observed, 'result': int(result[1]), 'payload': pin(payload)})
        print(name, observed, flush=True)
    static = json.loads((repo / 'seed/static-cases.json').read_text())['cases']
    fuel_case = next(x for x in static if x['name'] == 'string-call')
    if fuel_case['reference']['remainingFuel'] != 999998:
        raise ValueError('fuel-control reference drift')
    payload = compile_payload('fuel-control', fuel_case['source'])
    fuel = execute('fuel-control-run', payload, 1)
    if fuel.returncode != 120 or b':status :trap' not in fuel.stdout or re.search(rb':result (-?[0-9]+)', fuel.stdout):
        raise ValueError(('low-fuel control did not trap', fuel.returncode, fuel.stdout[-500:], fuel.stderr[-500:]))
    bad = out / 'unknown.kotoba'
    bad.write_text('(ns unknown (:export [main]))\n(defn main [] :i64 (does-not-exist 1))\n')
    bad_image = out / 'unknown.kseed'
    bad_result = run('compile-refusal', [producer, 'compile', bad, '--target', 'aarch64-macos', '--output', bad_image], expected=None)
    if bad_result.returncode == 0 or bad_image.exists() or b'E2101' not in bad_result.stderr:
        raise ValueError(('compile negative did not refuse', bad_result.returncode, bad_result.stderr[-500:]))
    if any(pin(p) != before[str(p)] for p in tracked):
        raise ValueError('bootstrap, source, corpus or observer changed during run')
    report = {'status': 'PASS_CURRENT_ARM_FLOAT_RESULT_FUEL', 'host': [platform.system(), platform.machine(), platform.release()],
              'bootstrap': pin(receipt_path), 'compiler': pin(producer), 'runner': pin(runner), 'runnerSource': pin(source),
              'floatCorpus': pin(corpus), 'staticCorpus': pin(repo / 'seed/static-cases.json'),
              'observer': pin(Path(__file__).resolve()), 'cases': results,
              'fuelNegative': {'exit': fuel.returncode, 'stdout': pin(out / 'fuel-control-run.stdout')},
              'compileNegative': {'exit': bad_result.returncode, 'stderr': pin(out / 'compile-refusal.stderr')},
              'calls': rows, 'c0ExecutedCases': False, 'fullNativeCorpusQualified': False, 'publicReleaseReady': False}
    (out / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], len(results), flush=True)


if __name__ == '__main__':
    main()
