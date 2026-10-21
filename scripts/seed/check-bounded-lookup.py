#!/usr/bin/env python3
"""Run independent source behavior controls with the native self-built seed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct

ROOT = Path(__file__).resolve().parents[2]
# The full-image structure golden was audited on the compiler adopted before the same-algorithm m104 adoption.
# It is checked on that compiler (AUDITED); the current adopted compiler is checked by the structural properties
# below and by every behavioural case.
AUDITED = ROOT / 'docs/evidence/same-algo-m104-20261015/previous-bootstrap.bin'
AUDITED_SHA256 = '87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_exports(container, native):
    header, payload = container.read_bytes().split(b'\n\n', 1)
    lines = header.decode().splitlines()
    if lines[0] != f'KSEED1 {len(payload)} {len(lines)-1}' or payload != native.read_bytes():
        raise SystemExit('control payload/container mismatch')
    return payload, {name: (int(offset), int(arity)) for name, offset, arity in map(str.split, lines[1:])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selfbuild-output', type=Path, required=True)
    args = parser.parse_args()
    out = args.selfbuild_output.resolve()
    host = out / 'host'
    artifacts = out / 'artifacts' / 'lookup-controls'
    artifacts.mkdir(exist_ok=False)
    loader = host / 'kexe-loader'
    receipt = json.loads((ROOT / 'seed/adoption-20261017.json').read_text())
    producer = host / 'lookup-producer.bin'
    shutil.copyfile(out / 'artifacts/G2.bin', producer)
    if digest(producer) != receipt['nativeImageSHA256']:
        raise SystemExit('self-built compiler pin mismatch')
    source = artifacts / 'controls.kotoba'
    shutil.copyfile(ROOT / 'seed/tests/bounded-byte-lookup/controls.kotoba', source)
    if digest(AUDITED) != AUDITED_SHA256:
        raise SystemExit('audited compiler pin mismatch')
    pins = {path: digest(path) for path in (loader, producer, source, AUDITED)}
    env = {key: value for key, value in os.environ.items() if not key.startswith('KEXE_')}
    env.update(KEXE_COMMAND='1', KEXE_CAP_RESOURCES_35=str(artifacts),
               KEXE_FUEL='off', KEXE_VECTORS='4194304',
               KEXE_VECTOR_ITEMS='134217728', KEXE_STRING_POOL='268435456',
               KEXE_PAIRS='16777216', KEXE_CPU_SECONDS='1800',
               KEXE_WALL_SECONDS='1800', TMPDIR=str(artifacts))
    container = artifacts / 'controls.kseed'
    native = artifacts / 'controls.bin'
    audited_container = artifacts / 'audited-controls.kseed'
    audited_native = artifacts / 'audited-controls.bin'
    commands = [('', producer, 'compile', [source, '--target', 'aarch64-macos', '--output', container]),
                ('', producer, 'extract-native', [container, '--symbol', 'control', '--output', native]),
                ('audited-', AUDITED, 'compile', [source, '--target', 'aarch64-macos', '--output', audited_container]),
                ('audited-', AUDITED, 'extract-native', [audited_container, '--symbol', 'control', '--output', audited_native])]
    for tag, compiler, command, tail in commands:
        argv = [loader, compiler, '0', '0', 'aarch64', '35,37,38,39', '--', command, *tail]
        result = subprocess.run(list(map(str, argv)), cwd=artifacts, env=env, capture_output=True, timeout=1800)
        (host / ('lookup-' + tag + command + '.stdout')).write_bytes(result.stdout)
        (host / ('lookup-' + tag + command + '.stderr')).write_bytes(result.stderr)
        if result.returncode or any(digest(path) != sha for path, sha in pins.items()):
            raise SystemExit('native control compiler failed or changed its inputs')
    payload, exports = payload_exports(container, native)
    audited, audited_exports = payload_exports(audited_container, audited_native)
    # Pin the independently audited native image, including unchanged refusal bodies, on the audited compiler.
    # The private tree enters the appended lookup; the exported copy retains CMP.
    structure = json.loads((ROOT / 'seed/tests/bounded-byte-lookup/native-structure.json').read_text())
    if (len(audited) != structure['bytes']
            or hashlib.sha256(audited).hexdigest() != structure['sha256']
            or {name: list(value) for name, value in audited_exports.items()} != structure['exports']):
        raise SystemExit('native lookup acceptance/refusal structure changed')
    regions = {}
    for row in structure['regions']:
        region = audited[row['start']:row['end']]
        if hashlib.sha256(region).hexdigest() != row['sha256']:
            raise SystemExit('native lookup structural region mismatch: ' + row['purpose'])
        regions[row['purpose']] = row
    private_word, = struct.unpack_from('<I', audited, 0)
    if private_word >> 26 != 5 or ((private_word & 0x03ffffff) << 2) != structure['lookupCoreOffset']:
        raise SystemExit('private mapped tree did not enter lookup core')
    exposed_word, = struct.unpack_from('<I', audited, audited_exports['exposed'][0])
    if exposed_word != structure['exposedEntryWord']:
        raise SystemExit('exported exposed tree was optimized instead of refused')
    # The same properties on the current adopted compiler's image: the private tree (unchanged apart from its
    # branch) enters a lookup core no longer than the audited one, followed by the 128 audited source-derived table
    # entries; the exported tree is byte-identical to the audited region and is still refused (CMP entry word).
    private_word, = struct.unpack_from('<I', payload, 0)
    target = ((private_word & 0x03ffffff) << 2)
    table_row = regions['128 immutable source-derived tagged table entries']
    core_row = regions['lookup core and alignment']
    table = audited[table_row['start']:table_row['end']]
    table_offset = payload.find(table, target)
    if (private_word >> 26 != 5 or not 0 < target < len(payload) or payload[4:2048] != audited[4:2048]
            or table_offset < 0 or not 0 < table_offset - target <= core_row['end'] - core_row['start']):
        raise SystemExit('current compiler: private mapped tree did not enter the audited lookup')
    exposed_row = regions['exported tree unchanged and refused']
    exposed_word, = struct.unpack_from('<I', payload, exports['exposed'][0])
    if (list(exports['exposed']) != structure['exports']['exposed'] or exposed_word != structure['exposedEntryWord']
            or hashlib.sha256(payload[exposed_row['start']:exposed_row['end']]).hexdigest() != exposed_row['sha256']):
        raise SystemExit('current compiler: exported exposed tree was optimized instead of refused')
    offset, arity = exports['control']
    if arity != 2 or offset % 4 or not 0 <= offset < len(payload):
        raise SystemExit('invalid actual control export')
    cases = json.loads((ROOT / 'seed/tests/bounded-byte-lookup/cases.json').read_text())['cases']
    if len(cases) != 52:
        raise SystemExit('expected 52 independent source controls')
    rows = []
    guest_env = {key: value for key, value in env.items() if not key.startswith('KEXE_')}
    guest_env.update(KEXE_ARENA_USE='1', KEXE_STRUCTURED_REPORT='1',
                     KEXE_CPU_SECONDS='60', KEXE_WALL_SECONDS='60')
    for index, case in enumerate(cases):
        guest_env['KEXE_FUEL'] = str(case['fuel'])
        argv = [loader, native, str(offset), '2', 'aarch64', '37', str(case['mode']), str(case['input'])]
        result = subprocess.run(list(map(str, argv)), cwd=artifacts, env=guest_env, capture_output=True, timeout=65)
        (host / f'lookup-{index}.stdout').write_bytes(result.stdout)
        (host / f'lookup-{index}.stderr').write_bytes(result.stderr)
        value = re.search(rb':status :ok :result (-?\d+)', result.stdout)
        fuel = re.search(rb':fuel \{:initial (\d+) :remaining (\d+)\}', result.stdout)
        arena = {key.decode(): int(value) for key, value in re.findall(rb':([a-z-]+) (\d+)', result.stderr)}
        if (result.returncode or value is None or int(value.group(1)) != case['expected']
                or fuel is None or tuple(map(int, fuel.groups())) != (case['fuel'], case['expectedFuelRemaining'])
                or arena != case['expectedArena']):
            raise SystemExit('source control failed: ' + str(index))
        rows.append({'case': index, 'result': case['expected'], 'fuelRemaining': case['expectedFuelRemaining']})
    report = {'status': 'PASS_NATIVE_SOURCE_LOOKUP_ACCEPTANCE_AND_REFUSAL_CONTROLS', 'cases': len(rows),
              'compilerImageSHA256': digest(producer), 'sourceSHA256': digest(source),
              'performanceMeasurement': False, 'nativeStructureSHA256': digest(native),
              'auditedCompilerImageSHA256': AUDITED_SHA256, 'auditedStructureSHA256': digest(audited_native),
              'currentLookupCoreOffset': target, 'currentTableOffset': table_offset, 'rows': rows}
    (host / 'lookup-controls-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'])


if __name__ == '__main__':
    main()
