#!/usr/bin/env python3
"""Observe a bounded Darwin full-compiler startup and its first missing ABI slot."""

import hashlib
import json
import platform
import resource
import struct
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PINS = {
    'root': ('seed/bootstrap/aarch64-linux-static-root.elf', '285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1'),
    'packager': ('seed/macos-full-runtime-probe-packager.kotoba', '8a066756b3eef854371c90fb35c3dc3b494a0fda9ce5788682c4f74dbc9cf0cc'),
    'fixture': ('seed/macos-equal-main.kotoba', 'eb37f468ab7e1818e4f746549f491b2dc086df1c5833545febffd4283a8433a5'),
}
ARTIFACT_PINS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'equalRaw': ('equal-main.raw', 'a5d3d768c88881ad4ef8bf371caaaf1a08102154ce50ac7ab607cf1ce88b5e98'),
    'equalKseed': ('equal-main.kseed', '3ebb70628b18c4d7edb996f25b280a814afcfc883cc40c0e5c3af9f4fe35830a'),
    'packager': ('full-probe-final-packager.elf', 'acf0fc4ba542a3650c72f19fb731348fa65d1970822c33985acab54d0f343353'),
    'fullImage': ('full-final.macho', '7832febd8de86aa1c730b75bce38c94b0fc4a7ea0b1167315274339e40240655'),
    'equalImage': ('equal-final.macho', '6c7f19f7a68f7a1e6c01aa3afac11cb5425752834e620ec80b87eb9fd0978357'),
}
HELPER_SHA = {
    'pair': (1408, 1476, 'd03e5dce07efed585c1fdeb653c4fa613861e1bfadc30fecdbe3fea73417920a'),
    'typed': (1536, 1768, '19eb316c255bf51dd7508bb79da72b2a6ba74a55808baf4090ae333d16544a50'),
    'equal': (1792, 1996, '81d0ae94fc3b6b3eedba330a6aad72141c665125a7da50eac690a6e1a5c8e314'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, expected):
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError(f'unexpected digest for {path}: {sha(raw)}')
    return raw


def word(data, at):
    return struct.unpack_from('<I', data, at)[0]


def check_image(image, raw):
    text = 16384 * ((2048 + len(raw) + 16383) // 16384)
    if len(image) != text + 16384 or image[:4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('Mach-O extent or magic')
    if struct.unpack_from('<4I', image, 12) != (2, 7, 368, 0x00200005):
        raise ValueError('Mach-O header')
    commands, cursor = [], 32
    for _ in range(7):
        kind, length = struct.unpack_from('<II', image, cursor)
        commands.append((kind, length))
        cursor += length
    if commands != [(25, 72)]*4 + [(14, 32), (0x80000028, 24), (50, 24)] or cursor != 400:
        raise ValueError('Mach-O load commands')
    if (struct.unpack_from('<4Q', image, 128) != (0x100000000, text, 0, text)
            or struct.unpack_from('<4Q', image, 200) != (0x100000000+text, 16384, text, 16384)
            or struct.unpack_from('<Q', image, 360)[0] != 1024):
        raise ValueError('Mach-O segment or entry')
    if image[2048:2048+len(raw)] != raw or any(image[2048+len(raw):]):
        raise ValueError('generated main or zero padding')
    for name, (start, end, expected) in HELPER_SHA.items():
        if sha(image[start:end]) != expected:
            raise ValueError(f'{name} runtime helper differs')
    required = {1044: 0xf9001e68, 1156: 0xf9004268,
                1164: 0xf9003a68, 1168: 0xd2800008,
                1200: 0xf100a81f, 1416: 0xd2a0200a}
    for offset, expected in required.items():
        if word(image, offset) != expected:
            raise ValueError(f'ABI instruction differs at {offset}')


def signed_run(image, output, name):
    path = output / (name + '-signed.macho')
    path.write_bytes(image)
    path.chmod(0o755)
    for command in (['/usr/bin/codesign', '--force', '--sign', '-', str(path)],
                    ['/usr/bin/codesign', '--verify', '--strict', str(path)]):
        check = subprocess.run(command, capture_output=True, timeout=10)
        if check.returncode:
            raise RuntimeError((command, check.stderr.decode(errors='replace')))
    started = time.time()
    process = subprocess.Popen([str(path)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError(f'{name} did not terminate within five seconds')
    return {'name': name, 'signedSha256': sha(path.read_bytes()),
            'exit': process.returncode, 'stdoutHex': stdout.hex(),
            'stderrHex': stderr.hex()}, process.pid, started


def crash_callsite(pid, started, raw):
    directory = Path.home()/'Library/Logs/DiagnosticReports'
    deadline = time.monotonic()+5
    while time.monotonic() < deadline:
        for path in directory.glob('full-probe-signed.macho-*.ips'):
            if path.stat().st_mtime < started-1:
                continue
            lines = path.read_text().splitlines()
            if len(lines) < 2:
                continue
            report = json.loads('\n'.join(lines[1:]))
            if report.get('pid') != pid:
                continue
            thread = report['threads'][report['faultingThread']]['threadState']
            base = report['usedImages'][0]['base']
            image_return = thread['lr']['value']-base
            raw_return = image_return-2048
            if (report['exception']['signal'] != 'SIGSEGV' or thread['pc']['value'] != 0
                    or raw_return < 8 or raw_return > len(raw)
                    or word(raw, raw_return-8) != 0xf9403c10
                    or word(raw, raw_return-4) != 0xd63f0200):
                raise ValueError('full compiler did not stop at missing concat slot')
            return {'pc': 0, 'returnImageOffset': image_return,
                    'returnRawOffset': raw_return, 'nextSlotOffset': 120,
                    'nextSlot': 'string_concat'}
        time.sleep(.1)
    raise RuntimeError('current full compiler crash report not yet available')


def observe(artifacts, output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for path, expected in SOURCE_PINS.values():
        pin(ROOT/path, expected)
    data = {name: pin(artifacts/path, expected)
            for name, (path, expected) in ARTIFACT_PINS.items()}
    if data['fullImage'] != (artifacts/'full-final-repeat.macho').read_bytes():
        raise ValueError('full image repeat differs')
    for name in ('equal-compile', 'equal-extract', 'compile-equal-final',
                 'emit-equal-final', 'emit-full-final', 'emit-full-repeat'):
        receipt = json.loads((artifacts/(name+'-admission.json')).read_text())
        if receipt.get('schema') != 'amu.native-build-admission.v1' or receipt.get('exit') != 0:
            raise ValueError(f'native admission failure: {name}')
    check_image(data['equalImage'], data['equalRaw'])
    check_image(data['fullImage'], data['fullRaw'])
    output.mkdir(parents=True, exist_ok=False)
    equal, _, _ = signed_run(data['equalImage'], output, 'equal-fixture')
    no_span = bytearray(data['equalImage'])
    struct.pack_into('<I', no_span, 1192, 0xd503201f)
    missing_span, _, _ = signed_run(no_span, output, 'missing-code-length')
    full, pid, started = signed_run(data['fullImage'], output, 'full-probe')
    if (equal['exit'], equal['stdoutHex'], equal['stderrHex']) != (42, '', ''):
        raise RuntimeError(f'equality fixture failed: {equal}')
    if (missing_span['exit'], missing_span['stdoutHex'], missing_span['stderrHex']) != (-5, '', ''):
        raise RuntimeError(f'code-span control failed: {missing_span}')
    if (full['exit'], full['stdoutHex'], full['stderrHex']) != (-11, '', ''):
        raise RuntimeError(f'full compiler startup differed: {full}')
    next_call = crash_callsite(pid, started, data['fullRaw'])
    result = {'schema': 'amu.macos-full-runtime-startup-probe.v1',
              'status': 'PASS_BOUNDED_FULL_MAIN_STARTUP',
              'host': [platform.system(), platform.machine(), platform.mac_ver()[0]],
              'sourceSha256': {name: value for name, (_, value) in SOURCE_PINS.items()},
              'artifactSha256': {name: value for name, (_, value) in ARTIFACT_PINS.items()},
              'repeatByteIdentical': True, 'cases': [equal, missing_span, full],
              'nextMissingRuntime': next_call,
              'fullCompilerCompleted': False, 'macSelfRebuild': False,
              'trustedUserConsent': False, 'linuxFreeBuildClosure': False}
    (output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: check-macos-full-runtime-probe.py ARTIFACT_DIR NEW_OUTPUT_DIR')
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2]))))
