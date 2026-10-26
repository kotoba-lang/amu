#!/usr/bin/env python3
"""Observe Darwin bytes copy, UTF-8 construction and the next full CLI boundary."""

import argparse
import hashlib
import json
import platform
import resource
import struct
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'root': ('seed/bootstrap/aarch64-linux-static-root.elf', '285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1'),
    'bytesPackager': ('seed/macos-bytes-runtime-packager.kotoba', '4bae37428b2f1d38ab1eb140521b47f31846f863037e53389907bd1a9e91ae86'),
    'bytesMain': ('seed/macos-bytes-main.kotoba', '90ed5277f9a3ba0d3e2b17063a5a261efecf243d2fbc6069cfdd5e021a0331fe'),
    'bytesRefusal': ('seed/macos-bytes-refusal.kotoba', 'b4343ec3bb883c73f1cce196d85f25fd46470e3d9fdc96fb6c84b24d0b894c0a'),
    'utf8Packager': ('seed/macos-utf8-runtime-packager.kotoba', '9f7ecb9a48d67c1cf3877ffab1d899d200ac01507c2224991267005cc77d5072'),
    'utf8Main': ('seed/macos-utf8-main.kotoba', '1984165d9cb3a66133f47168df5a6adb22437e6eb06d80d07dcc2b9260c2e4fc'),
    'utf8Refusal': ('seed/macos-utf8-refusal.kotoba', '3be443586075c09dff530ae3c2b8ee05915804230737bb8175f2d0698b98eaa1'),
}
ARTIFACTS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'bytesPackager': ('bytes-packager.elf', '632db682a89f46801cb4ec6e50284455be60fade88e3a198a4c2eeb74dc0d952'),
    'utf8Packager': ('utf8-packager.elf', '7c5f749453762ff1db0c5d55380ea4e8bacf23b6361919f6a89e644877ca9dea'),
    'bytesMainKseed': ('bytes-main.kseed', 'fbf1af9d65cb54d6c7dfb2629a8b2c6e4c9cc0494fd60d79b8fa99c42eded12b'),
    'bytesRefusalKseed': ('bytes-refusal.kseed', '3e686234ade133233d7a75a8b855692f710d0c6e18dd37753daf0b8c0f14ef3c'),
    'utf8MainKseed': ('utf8-main.kseed', '682ab427170c444bd1550384024ed5c988df96edfa520d68795502028c8ef5b5'),
    'utf8RefusalKseed': ('utf8-refusal.kseed', '7c5fbd5e2bf5dbe5431c3a84091c1b14f4c7c08efb6dde153c1e29f9dbf5c996'),
    'bytesMainRaw': ('bytes-main.raw', 'e92c9a137d326fcb179763c9b6f51eddf97e279eb05fd9e3b3e1141864fd33d8'),
    'bytesRefusalRaw': ('bytes-refusal.raw', '6965425a152da52b8ae8cccbb0d3460ecceaa8e737456eb2cd4d8a97af7aae1d'),
    'utf8MainRaw': ('utf8-main.raw', '6aaa5e8a82a35d9b9a2a98dc260da6dee88ff184273bcab45a98866a264ffa3b'),
    'utf8RefusalRaw': ('utf8-refusal.raw', '634c3238797029d3885f209e3b12caedbacc6cefd0d09dc8b5251d69e20799de'),
    'full': ('utf8-full.macho', '31db43821ee84ebbba81a9fbc3587ed5f3a9ce6ea90866bf54573c7376caa847'),
    'bytesMain': ('utf8-bytes-main.macho', '4ccdcc89584f7f9bec5962f19370543948b2797fcb9f601302f2798e06ebeec8'),
    'bytesRefusal': ('utf8-bytes-refusal.macho', '65bc9dd5e3966152e574325cb405e5310d2220c84a325b826a6d04298391db88'),
    'utf8Main': ('utf8-main.macho', 'd42e1b05338874d9335f0ac9102047fdac104701da9c258529422986669beb8b'),
    'utf8Refusal': ('utf8-refusal.macho', '692c86253c9011d0dc596b0061b36ba026199edde7a660326e040da0783e992a'),
}
ADMISSIONS = (
    'compile-bytes-packager-admission.json', 'compile-bytes-main-admission.json',
    'compile-bytes-refusal-admission.json', 'extract-bytes-main-admission.json',
    'extract-bytes-refusal-admission.json', 'package-bytes-full-admission.json',
    'package-bytes-main-admission.json', 'package-bytes-refusal-admission.json',
    'compile-utf8-packager-admission.json', 'compile-utf8-main-admission.json',
    'compile-utf8-refusal-admission.json', 'extract-utf8-main-admission.json',
    'extract-utf8-refusal-admission.json', 'package-utf8-full-admission.json',
    'package-utf8-main-admission.json', 'package-utf8-refusal-admission.json',
    'package-utf8-bytes-main-admission.json', 'package-utf8-bytes-refusal-admission.json',
    'package-utf8-full-repeat-admission.json',
)
USAGE = b'seed: E1 usage: seed check <file> | seed compile <file> --target aarch64-macos --output <out> | seed extract-native <kseed> --symbol <name> --output <raw>\n'
HELPER_SHA = '1cbb73d57a2a44133b72b7f6249e4c40a72306561b10e0991ce5a6ab8bee2d27'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, digest):
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError(f'digest mismatch: {path}')
    return data


def word(data, at):
    return struct.unpack_from('<I', data, at)[0]


def inspect_image(name, image, raw):
    text_bytes = 16384 * ((8192 + len(raw) + 16383) // 16384)
    if (len(image) != text_bytes + 16384 or image[:4] != b'\xcf\xfa\xed\xfe'
            or image[8192:8192+len(raw)] != raw
            or any(image[8192+len(raw):text_bytes])):
        raise ValueError(f'{name}: image/raw extent mismatch')
    if (struct.unpack_from('<4I', image, 12) != (2, 7, 368, 0x00200005)
            or struct.unpack_from('<Q', image, 360)[0] != 1024
            or sha(image[5000:6252]) != HELPER_SHA):
        raise ValueError(f'{name}: header or helper text differs')
    expected = {2096: 0x140002ea, 3224: 0x10001b48,
                3228: 0xf9004a68, 3232: 0x10002d08,
                3236: 0xf9004668, 3240: 0x140001b8,
                5000: 0xd2800168, 5080: 0xaa1f03e0,
                5960: 0xd100c3ff,
                1176: 0xd2c01808 if name == 'full' else 0xd2800008}
    for offset, value in expected.items():
        if word(image, offset) != value:
            raise ValueError(f'{name}: instruction mismatch at {offset}')
    return {'sha256': sha(image), 'rawSha256': sha(raw),
            'helperSha256': sha(image[5000:6252]), 'textBytes': text_bytes}


def signed_run(image, output, name, args):
    executable = output / f'{name}-signed.macho'
    executable.write_bytes(image)
    executable.chmod(0o755)
    for command in (('/usr/bin/codesign', '--force', '--sign', '-', str(executable)),
                    ('/usr/bin/codesign', '--verify', '--strict', str(executable))):
        result = subprocess.run(command, capture_output=True, timeout=15)
        if result.returncode:
            raise RuntimeError((command, result.stderr.decode(errors='replace')))
    started = time.time()
    process = subprocess.Popen((str(executable), *args), cwd=ROOT,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(timeout=15)
    return ({'name': name, 'args': args, 'signedSha256': sha(executable.read_bytes()),
             'exit': process.returncode, 'stdoutHex': stdout.hex(),
             'stderrHex': stderr.hex()}, process.pid, started)


def crash(name, pid, started):
    folder = Path.home() / 'Library/Logs/DiagnosticReports'
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        for path in folder.glob(f'{name}-signed.macho-*.ips'):
            if path.stat().st_mtime < started - 1:
                continue
            lines = path.read_text().splitlines()
            if len(lines) < 2:
                continue
            report = json.loads('\n'.join(lines[1:]))
            if report.get('pid') == pid:
                state = report['threads'][report['faultingThread']]['threadState']
                base = next(x['base'] for x in report['usedImages']
                            if f'{name}-signed.macho' in x.get('path', ''))
                return {'signal': report['exception']['signal'],
                        'pcOffset': state['pc']['value'] - base,
                        'rawReturnOffset': state['lr']['value'] - base - 8192,
                        'wire': state['x'][1]['value']}
        time.sleep(.1)
    raise RuntimeError(f'current crash report unavailable: {name}')


def observe(artifacts, output):
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    output.mkdir(parents=True, exist_ok=False)
    sources = {name: sha(pin(ROOT / path, digest))
               for name, (path, digest) in SOURCES.items()}
    data = {name: pin(artifacts / path, digest)
            for name, (path, digest) in ARTIFACTS.items()}
    admissions = {}
    for name in ADMISSIONS:
        item = json.loads((artifacts / name).read_text())
        if (item['schema'] != 'amu.native-build-admission.v1'
                or item['capacity'] != 2 or item['exit'] != 0):
            raise ValueError(f'build admission failed: {name}')
        admissions[name] = item
    if data['full'] != (artifacts / 'utf8-full-repeat.macho').read_bytes():
        raise ValueError('full image repeat differs')
    pairs = {'full': 'fullRaw', 'bytesMain': 'bytesMainRaw',
             'bytesRefusal': 'bytesRefusalRaw', 'utf8Main': 'utf8MainRaw',
             'utf8Refusal': 'utf8RefusalRaw'}
    images = {name: inspect_image(name, data[name], data[raw])
              for name, raw in pairs.items()}
    cases = []
    traps = {}
    for name, expected in (('bytesMain', 42), ('bytesRefusal', -5),
                           ('utf8Main', 42), ('utf8Refusal', -5)):
        case, pid, started = signed_run(data[name], output, name, [])
        if (case['exit'], case['stdoutHex'], case['stderrHex']) != (expected, '', ''):
            raise ValueError(f'{name}: wrong process result')
        cases.append(case)
        if expected < 0:
            traps[name] = crash(name, pid, started)
    if traps['bytesRefusal']['signal'] != 'SIGTRAP' or traps['bytesRefusal']['pcOffset'] != 0x1728:
        raise ValueError('bytes item refusal did not reach checked helper')
    if traps['utf8Refusal']['signal'] != 'SIGTRAP' or traps['utf8Refusal']['pcOffset'] != 0x1230:
        raise ValueError('malformed UTF-8 did not reach canonical validator')
    noargs, _, _ = signed_run(data['full'], output, 'fullNoargs', [])
    if (noargs['exit'], noargs['stdoutHex'], noargs['stderrHex']) != (2, '', USAGE.hex()):
        raise ValueError('full CLI usage differs')
    cases.append(noargs)
    full, pid, started = signed_run(data['full'], output, 'fullCheck',
                                     ['check', 'seed/macos-utf8-main.kotoba'])
    if (full['exit'], full['stdoutHex'], full['stderrHex']) != (-5, '', ''):
        raise ValueError('full CLI did not reach expected typed FS refusal')
    cases.append(full)
    traps['fullCheck'] = crash('fullCheck', pid, started)
    if (traps['fullCheck']['signal'] != 'SIGTRAP'
            or traps['fullCheck']['pcOffset'] != 0x6e4
            or traps['fullCheck']['rawReturnOffset'] != 0x2f80
            or traps['fullCheck']['wire'] != 35
            or word(data['fullRaw'], 0x2f78) != 0xf9404010
            or word(data['fullRaw'], 0x2f7c) != 0xd63f0200):
        raise ValueError('full CLI did not stop at typed fs/app-data wire 35')
    receipt = {'schema': 'amu.macos-bytes-utf8-probe.v1',
               'status': 'PASS_BYTES_UTF8_NEXT_FS_WIRE_35',
               'qualification': 'diagnostic-bootstrap-only',
               'sourceSha256': sources, 'artifactSha256': {k: sha(v) for k,v in data.items()},
               'imageChecks': images, 'admissions': admissions,
               'fullImageRepeatEqual': True, 'cases': cases,
               'traps': traps, 'nextBoundary': 'typed_cap_call wire 35 fs/app-data'}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(observe(args.artifacts, args.output)['status'])
