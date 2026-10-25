#!/usr/bin/env python3
"""Observe four diagnostic Darwin ABI callbacks and the next full CLI stop.

The observer stages and signs images, but does not compile or package them.
The AArch64 words used by the package are checked against Kotoba source.
"""

import argparse
from collections import Counter
import hashlib
import json
import platform
import re
import resource
import struct
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PINS = {
    'root': ('seed/bootstrap/aarch64-linux-static-root.elf', '285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1'),
    'packager': ('seed/macos-pure-runtime-packager.kotoba', 'e249129414319593a7e04f557b50321e187703b2437e1e4d898e2d5c0c7674b8'),
    'main': ('seed/macos-pure-runtime-main.kotoba', 'd167bd83baaf08d3b0c637ee48eca4e1acf40c2e556f33b4aeb616effa032878'),
    'refusal': ('seed/macos-pure-runtime-refusal.kotoba', 'cf7abb4412380aa555b1ede3f597177a0fb36eb95fcfecd827d23a43dcf89014'),
    'vectorRefusal': ('seed/macos-pure-runtime-vector-refusal.kotoba', '222c425a0fb251f7a9274c8d634a346739e00f10cbcd452f91b004b178e12315'),
    'derivation': ('docs/evidence/mac-pure-runtime-20261026/pure-runtime.s', 'd0a58fe131ee99723b421efbde728c2ad41569ec18068ed94813dfdab74272ab'),
}
ARTIFACT_PINS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'oldFull': ('utf8-full.macho', '31db43821ee84ebbba81a9fbc3587ed5f3a9ce6ea90866bf54573c7376caa847'),
    'packager': ('pure-trial1/pure-packager-v3.elf', '281df6263b06b3fdb4d7e372618fd1b1112514527e42cd393a19998c5c62594c'),
    'full': ('pure-trial1/pure-full-repeat.macho', '3a0a2465b767f57b9960123d2ac12b160304a47681b096cbe954a4252e87846d'),
    'mainRaw': ('pure-trial1/pure-main.raw', 'c9687a0d68c33bea0968f84b023640c6ff49dca722d35ef17f4b082766ee65a5'),
    'refusalRaw': ('pure-trial1/pure-refusal.raw', '92d522e4b86b0c8d878c4a75f5ee705c337dcbe20bebe4801d50f7982f9e968e'),
    'vectorRefusalRaw': ('pure-trial1/pure-vector-refusal.raw', 'efe776d944560dd000ce3c32fecc19ac3c21f495e048b1ca93a196f8167d3cb2'),
    'main': ('pure-trial1/pure-main-v3.macho', 'c8683781dd66766a1b00fe7396ab63d4fae2a96c2adad30ed5fe9956849106fa'),
    'refusal': ('pure-trial1/pure-refusal-v3.macho', '7a79589b03103023db817a93bc5fdc05fac5ac45f9127573c8bb14188d7a1435'),
    'vectorRefusal': ('pure-trial1/pure-vector-refusal.macho', 'dd378783640e2e9675ed530ba1c233d50e4398f10b1b00ad96b66c621f4a9b06'),
}
ADMISSIONS = (
    'build-admission-v5.json',
    'compile-main-admission.json', 'compile-refusal-admission.json',
    'compile-vector-refusal-admission.json',
    'extract-main-admission.json', 'extract-refusal-admission.json',
    'extract-vector-refusal-admission.json',
    'package-full-repeat-admission.json', 'package-main-v3-admission.json',
    'package-refusal-v3-admission.json', 'package-vector-refusal-admission.json',
)
USAGE = b'seed: E1 usage: seed check <file> | seed compile <file> --target aarch64-macos --output <out> | seed extract-native <kseed> --symbol <name> --output <raw>\n'
CALLBACKS = {'conj': (160, 6304), 'assoc': (184, 6312),
             'index': (216, 6924), 'compare': (240, 6760)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, expected):
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f'digest mismatch: {path}')
    return data


def pure_words(source):
    section = source.split(b'(defn- pure-helper-words', 1)[1].split(b'(defn- data-adrp', 1)[0]
    chunks = re.findall(rb'\(append-runtime-words\s+(\d+)\s+\[([^]]+)\]\)', section)
    words = [None] * 211
    for at, body in chunks:
        offset = int(at)
        values = [int(x, 16) for x in re.findall(rb'0x[0-9a-f]+', body)]
        for i, value in enumerate(values):
            if offset+i >= len(words) or words[offset+i] is not None:
                raise ValueError('overlapping pure helper source words')
            words[offset+i] = value
    if [int(at) for at, _ in chunks] != [0, 64, 128, 192] or any(x is None for x in words):
        raise ValueError('incomplete pure helper source words')
    return struct.pack('<211I', *words)


def callsites(raw):
    # Extracted functions can end in byte data after their aligned code.
    words = struct.unpack(f'<{len(raw)//4}I', raw[:len(raw)//4*4])
    found = Counter()
    for left, right in zip(words, words[1:]):
        if right == 0xd63f0200 and left & 0xffc003ff == 0xf9400010:
            found[((left >> 10) & 0xfff) * 8] += 1
    return found


def signed_run(image, output, name, args=()):
    path = output / f'{name}-signed.macho'
    path.write_bytes(image)
    path.chmod(0o755)
    for command in (('/usr/bin/codesign', '--force', '--sign', '-', str(path)),
                    ('/usr/bin/codesign', '--verify', '--strict', str(path))):
        done = subprocess.run(command, capture_output=True, timeout=15)
        if done.returncode:
            raise RuntimeError((command, done.stderr.decode(errors='replace')))
    started = time.time()
    child = subprocess.Popen((str(path), *args), cwd=ROOT,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(timeout=15)
    return ({'name': name, 'args': list(args), 'exit': child.returncode,
             'stdoutHex': stdout.hex(), 'stderrHex': stderr.hex(),
             'signedSha256': sha(path.read_bytes())}, child.pid, started)


def crash(name, pid, started):
    reports = Path.home() / 'Library/Logs/DiagnosticReports'
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        for path in reports.glob(f'{name}-signed.macho-*.ips'):
            if path.stat().st_mtime < started-1:
                continue
            lines = path.read_text().splitlines()
            if len(lines) < 2:
                continue
            report = json.loads('\n'.join(lines[1:]))
            if report.get('pid') != pid:
                continue
            state = report['threads'][report['faultingThread']]['threadState']
            base = next(x['base'] for x in report['usedImages']
                        if f'{name}-signed.macho' in x.get('path', ''))
            return {'signal': report['exception']['signal'],
                    'pcOffset': state['pc']['value']-base,
                    'rawReturnOffset': state['lr']['value']-base-8192,
                    'wire': state['x'][1]['value']}
        time.sleep(.1)
    raise RuntimeError(f'current crash report unavailable: {name}')


def observe(artifacts, output):
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    output.mkdir(parents=True, exist_ok=False)
    sources = {name: pinned(ROOT/path, digest) for name, (path, digest) in SOURCE_PINS.items()}
    data = {name: pinned(artifacts/path, digest)
            for name, (path, digest) in ARTIFACT_PINS.items()}
    admissions = {}
    for name in ADMISSIONS:
        row = json.loads((artifacts/'pure-trial1'/name).read_text())
        if row['schema'] != 'amu.native-build-admission.v1' or row['capacity'] != 2 or row['exit'] != 0:
            raise ValueError(f'failed build admission: {name}')
        admissions[name] = row
    if data['full'] != (artifacts/'pure-trial1/pure-full.macho').read_bytes():
        raise ValueError('full image repeat differs')
    for name, raw_name in (('full', 'fullRaw'), ('main', 'mainRaw'),
                           ('refusal', 'refusalRaw'), ('vectorRefusal', 'vectorRefusalRaw')):
        image, raw = data[name], data[raw_name]
        extent = 16384 * ((8192+len(raw)+16383)//16384)
        if (len(image) != extent+16384 or image[:4] != b'\xcf\xfa\xed\xfe'
                or image[8192:8192+len(raw)] != raw
                or any(image[8192+len(raw):extent])):
            raise ValueError(f'{name}: image/raw extent mismatch')
        if (struct.unpack_from('<4I', image, 12) != (2, 7, 368, 0x00200005)
                or struct.unpack_from('<Q', image, 360)[0] != 1024):
            raise ValueError(f'{name}: Mach-O header mismatch')
        if image[6256:7100] != pure_words(sources['packager']):
            raise ValueError(f'{name}: packaged pure helper differs from Kotoba source')
        if struct.unpack_from('<I', image, 1204)[0] != 0x94000000 | ((6256-1204)//4):
            raise ValueError(f'{name}: pure helper setup not called')
    if (len(data['full']) != len(data['oldFull'])
            or data['full'][8192:] != data['oldFull'][8192:]):
        raise ValueError('full compiler raw code or size changed')
    changed = [i for i, (a, b) in enumerate(zip(data['full'], data['oldFull'])) if a != b]
    if not changed or any(not (1204 <= i < 1208 or 6256 <= i < 7100) for i in changed):
        raise ValueError('unexpected full compiler image change')
    sites = callsites(data['mainRaw'])
    if any(sites[offset] < 1 for offset, _ in CALLBACKS.values()):
        raise ValueError('positive fixture does not call all four callbacks')
    cases, traps = [], {}
    for name, expected in (('main', 42), ('refusal', -5), ('vectorRefusal', -5)):
        case, pid, started = signed_run(data[name], output, 'pure'+name.title())
        if (case['exit'], case['stdoutHex'], case['stderrHex']) != (expected, '', ''):
            raise ValueError(f'{name}: wrong Mac result')
        cases.append(case)
        if expected < 0:
            traps[name] = crash('pure'+name.title(), pid, started)
            if (traps[name]['signal'], traps[name]['pcOffset']) != ('SIGTRAP', 7096):
                raise ValueError(f'{name}: refusal stopped elsewhere')
    noargs, _, _ = signed_run(data['full'], output, 'pureFullNoargs')
    if (noargs['exit'], noargs['stdoutHex'], noargs['stderrHex']) != (2, '', USAGE.hex()):
        raise ValueError('full CLI usage differs')
    cases.append(noargs)
    check, pid, started = signed_run(data['full'], output, 'pureFullCheck',
                                     ('check', 'seed/macos-utf8-main.kotoba'))
    if (check['exit'], check['stdoutHex'], check['stderrHex']) != (-5, '', ''):
        raise ValueError('full CLI did not reach expected FS2 refusal')
    cases.append(check)
    traps['fullCheck'] = crash('pureFullCheck', pid, started)
    if (traps['fullCheck']['signal'], traps['fullCheck']['pcOffset'],
            traps['fullCheck']['rawReturnOffset'], traps['fullCheck']['wire']) != ('SIGTRAP', 1764, 0x2f80, 35):
        raise ValueError('full CLI did not stop at typed FS2 wire 35')
    for name, (_, offset) in CALLBACKS.items():
        altered = bytearray(data['main'])
        struct.pack_into('<I', altered, offset, 0xd4200000)
        case, pid, started = signed_run(altered, output, 'pure'+name.title()+'Trap')
        if (case['exit'], case['stdoutHex'], case['stderrHex']) != (-5, '', ''):
            raise ValueError(f'{name}: mutation did not trap')
        stop = crash('pure'+name.title()+'Trap', pid, started)
        if (stop['signal'], stop['pcOffset']) != ('SIGTRAP', offset):
            raise ValueError(f'{name}: positive fixture missed mutated callback')
        cases.append(case)
        traps[name+'Mutation'] = stop
    receipt = {'schema': 'amu.macos-pure-runtime-probe.v1',
               'status': 'PASS_FOUR_PURE_CALLBACKS_NEXT_FS2_WIRE_35',
               'qualification': 'diagnostic-bootstrap-only',
               'observerSha256': sha(Path(__file__).read_bytes()),
               'sourceSha256': {name: sha(value) for name, value in sources.items()},
               'artifactSha256': {name: sha(value) for name, value in data.items()},
               'admissions': admissions, 'positiveCallsites': dict(sites),
               'pureHelperSha256': sha(pure_words(sources['packager'])),
               'fullImageChangedBytes': len(changed),
               'fullImageRawUnchanged': True, 'fullImageRepeatEqual': True,
               'cases': cases, 'traps': traps,
               'nextBoundary': 'typed_cap_call wire 35 fs/app-data FS2 provider'}
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(observe(args.artifacts, args.output)['status'])
