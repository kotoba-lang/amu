#!/usr/bin/env python3
"""Bootstrap-only native regression runner; no Node/JVM or external fixture inputs.

Build typed source controls with a selfhost compiler and independently check
meaning, logical fuel charges, first validation placement, and guarded native
read emission. This does not execute an observer compiler or mirror a golden IR.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / 'seed/tests/readonly-loop'
CASES = {
    'framed-diamond': (True, 5, lambda n: 11 + 43 * n),
    'framed-loop-diamond': (True, 5, lambda n: 11 + 43 * n),
    'framed-vector-change': (False, 5, lambda n: 11 if n == 0 else 50 if n == 1 else None),
    'framed-alias': (False, 5, lambda n: 11 + 43 * n),
    'framed-call': (False, 5, lambda n: 44 * (2 ** n - 1) + 11),
    'same-vector-phi': (False, 2, lambda n: 11 + 13 * n),
    'loop-first-read': (False, 2, lambda n: 30 * n),
    'negative-index': (False, 2, lambda n: 11 if n == 0 else None),
    'upper-index': (False, 2, lambda n: 11 if n == 0 else None),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seed', required=True, type=Path)
    ap.add_argument('--loader', required=True, type=Path)
    ap.add_argument('--seed-offset', type=int, default=0)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    out = args.out or Path(tempfile.mkdtemp(prefix='amu-readonly-loop-'))
    out.mkdir(parents=True, exist_ok=True)
    seed, loader = args.seed.resolve(), args.loader.resolve()
    env = dict(os.environ, KEXE_COMMAND='1', KEXE_CAP_RESOURCES_35=str(ROOT) + ':' + str(out.resolve()),
               KEXE_CPU_SECONDS='1800', KEXE_WALL_SECONDS='1800',
               KEXE_STRING_POOL='268435456', KEXE_VECTOR_ITEMS='134217728',
               KEXE_VECTORS='4194304', KEXE_PAIRS='16777216')
    checks, guards = [], []

    def build(case, symbol):
        d = out / case
        d.mkdir(exist_ok=True)
        package, image = d / 'source.kseed', d / (symbol + '.bin')
        steps = []
        if symbol == 'run':
            steps.append(('compile', ['compile', str(SOURCES / (case + '.kotoba')), '--target', 'aarch64-macos', '--output', str(package)]))
        steps.append((symbol + '-extract', ['extract-native', str(package), '--symbol', symbol, '--output', str(image)]))
        for stage, command in steps:
            q = subprocess.run([str(loader), str(seed), str(args.seed_offset), '0', 'aarch64', '35,37,38,39', '--', *command], env=env, capture_output=True, text=True)
            (d / (stage + '.log')).write_text(q.stdout + q.stderr)
            assert q.returncode == 0, (case, stage, q.stdout, q.stderr)
        offset = int(re.search(r':offset (\d+)', q.stdout)[1])
        (d / (symbol + '.offset')).write_text(str(offset) + '\n')
        return image, offset

    def observe(case, image, offset, inputs, fuel, expected, consumed=None):
        e = dict(os.environ, KEXE_STRUCTURED_REPORT='1', KEXE_FUEL=str(fuel))
        e.pop('KEXE_COMMAND', None)
        q = subprocess.run([str(loader), str(image), str(offset), str(len(inputs)), 'aarch64', '-', *map(str, inputs)], env=e, capture_output=True, text=True)
        if expected is None:
            assert q.returncode != 0 and 'KEXE_TRAP' in q.stderr, (case, inputs, fuel, q.stdout, q.stderr)
        else:
            result = re.search(r':result (-?\d+)', q.stdout)
            assert q.returncode == 0 and result and int(result[1]) == expected, (case, inputs, fuel, q.stdout, q.stderr)
        if consumed is not None:
            remaining = re.search(r':remaining (-?\d+)', q.stdout)
            assert remaining and fuel - int(remaining[1]) == consumed, (case, inputs, q.stdout)
        checks.append({'case': case, 'symbol': image.stem, 'inputs': inputs, 'fuel': fuel,
                       'expected': expected, 'expectedConsumed': consumed,
                       'exit': q.returncode, 'stdout': q.stdout, 'stderr': q.stderr})

    for case, (admit, arity, meaning) in CASES.items():
        image, offset = build(case, 'run')
        # Flag-guarded metadata capture, unsigned index bounds, explicit trap,
        # fresh element load. Match the complete contract, not a marker alone.
        raw = image.read_bytes()
        words = struct.unpack('<' + 'I' * (len(raw) // 4), raw[:len(raw) // 4 * 4])
        sites = []
        for i in range(len(words) - 16):
            flag = words[i] & 31
            if words[i] != 0xb5000000 | (13 << 5) | flag or not 22 <= flag <= 28:
                continue
            if words[i + 12] == 0xd2800000 | 32 | flag and words[i + 14] == 0x54000043 and words[i + 15] == 0:
                length = flag - 2
                assert words[i + 13] & 0xff20001f == 0xeb00001f and (words[i + 13] >> 16) & 31 == length
                assert words[i + 16] & 0xffe00c00 == 0xf8600800, (case, hex(words[i + 16]))
                assert 0xd2800000 | flag in words, (case, 'missing entry flag initialization')
                sites.append(i)
        assert bool(sites) == admit, (case, 'expected admission', admit, 'actual guarded reads', sites)
        if admit:
            assert len(sites) >= 4, (case, 'missing guarded reads', sites)
        guards.append({'case': case, 'expectedAdmitted': admit, 'physicalGuardSites': sites})
        for n in [0, 1, 2, 4]:
            want = meaning(n)
            # Source-level loop/backedge charges plus run+walk entry = n+2.
            consumed = n + 2 if want is not None else None
            observe(case, image, offset, [n], 1048576, want, consumed)
        observe(case, image, offset, [4], 1, None, 1)
        walk, walk_offset = build(case, 'walk')
        for handle in [0, 1, -1, 9223372036854775807]:
            for n in [0, 1]:
                inputs = [handle, n] + ([1, 2, 0] if arity == 5 else [])
                # No vector validation may move before the zero-trip branch.
                want = 0 if case == 'loop-first-read' and n == 0 else None
                observe(case, walk, walk_offset, inputs, 1048576, want, 1 if want == 0 else None)
        print('PASS readonly-loop', case, flush=True)
    report = {'status': 'PASS standalone typed native readonly-loop regressions',
              'seedSha256': hashlib.sha256(seed.read_bytes()).hexdigest(),
              'loaderSha256': hashlib.sha256(loader.read_bytes()).hexdigest(),
              'sources': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES.glob('*.kotoba')},
              'controls': checks, 'physicalChecks': guards, 'nativeObservations': len(checks),
              'performanceClaim': False,
              'limits': 'Finite typed meaning/fuel/trap/entry and concrete guarded emission controls; not general equivalence or observer admission proof.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS', len(checks), 'native observations; report', out / 'report.json')


if __name__ == '__main__':
    main()
