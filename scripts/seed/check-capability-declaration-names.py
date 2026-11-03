#!/usr/bin/env python3
"""Namespace capability declarations name every admitted wire (KOTOBA-173).

The checker admits `:entropy/draw` (wire 23) and `:sys/cwd` (wire 40), but the
declaration table (`pj-r5b-wire`, 60-proj) and the diagnostic name tables
(`drv-r5b-wire` / `drv-r5b-wname`, 90-drv) did not list them: a module that
declared and called `:entropy/draw` got E2176 for its own declaration, and
naming wire 23 in that message crashed the checker (SIGILL).

Runs the source-locked `check` of one-function modules with a Linux arm64 static
compiler and requires, for each of the two wires and the `:clock/now` control:
declared + called passes; called under a declaration that omits it is refused
with E2176 naming the capability. Linux arm64 only (podman or CI).
"""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

CALLS = {
    ':entropy/draw': '(string-length (typed-cap-call :entropy/draw :string :string "2"))',
    ':sys/cwd': '(string-length (typed-cap-call :sys/cwd :string :string ""))',
    ':clock/now': '(string-length (typed-cap-call :clock/now :string :string "wall"))',
}


def check(compiler, out, name, source):
    root = out / name / 'src'
    (root / 'r').mkdir(parents=True)
    module = root / 'r' / 'm.kotoba'
    module.write_text(source + '\n')
    lock = out / (name + '.ksl')
    lock.write_text(f'KSL1\nentry {module}\nroot {root}\nfile {hashlib.sha256(module.read_bytes()).hexdigest()} {module}\n')
    r = subprocess.run([str(compiler), 'check', str(module), '--source-path', str(root), '--source-lock', str(lock),
                        '--source-lock-sha256', hashlib.sha256(lock.read_bytes()).hexdigest()],
                       capture_output=True, timeout=600,
                       env=dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_CAP_RESOURCES_35=str(out)))
    return dict(case=name, exit=r.returncode, stdout=r.stdout.decode(errors='replace')[-300:],
                stderr=r.stderr.decode(errors='replace')[-300:])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--compiler', type=Path, required=True, help='seed/bootstrap/aarch64-linux-static-root.elf')
    p.add_argument('--compiler-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if (platform.system(), platform.machine()) not in {('Linux', 'aarch64'), ('Linux', 'arm64')}:
        raise SystemExit('run on Linux arm64')
    if hashlib.sha256(a.compiler.read_bytes()).hexdigest() != a.compiler_sha256:
        raise SystemExit('compiler digest mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    results = []
    for cap, call in CALLS.items():
        slug = cap.strip(':').replace('/', '-')
        declared = check(a.compiler, a.output, slug + '-declared',
                         f'(ns r.m (:export [main]) (:capabilities [{cap}])) (defn main [] :i64 {call})')
        assert declared['exit'] == 0 and declared['stderr'] == '', declared
        omitted = check(a.compiler, a.output, slug + '-omitted',
                        f'(ns r.m (:export [main]) (:capabilities [:cli/args])) (defn main [] :i64 {call})')
        text = str(omitted['stderr']) + str(omitted['stdout'])
        assert omitted['exit'] != 0 and 'E2176' in text and cap in text, omitted
        results += [declared, omitted]
        print(cap, 'declared ok; omitted refused E2176', flush=True)
    (a.output / 'receipt.json').write_text(json.dumps(dict(
        schema='amu.capability-declaration-names.v1', issue='KOTOBA-173',
        compiler=dict(path=str(a.compiler), sha256=a.compiler_sha256), results=results), indent=1) + '\n')
    print('PASS_CAPABILITY_DECLARATION_NAMES')


if __name__ == '__main__':
    main()
