#!/usr/bin/env python3
"""Observe the bounded Darwin concat runtime and the next full-main boundary."""

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
    'packager': ('seed/macos-concat-runtime-packager.kotoba', '15f401aab9eb5603834449a1bc8202d1b62de361a88cea728c1c6514458c0d68'),
    'fixture': ('seed/macos-concat-main.kotoba', 'c06893d5f98d349ca7b6d8d1ebe4c4d8d1ff6f641d12d13592a551ea04abe38c'),
}
ARTIFACT_PINS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'equalRaw': ('equal-main.raw', 'a5d3d768c88881ad4ef8bf371caaaf1a08102154ce50ac7ab607cf1ce88b5e98'),
    'concatRaw': ('concat-main.raw', 'f1d28074744d0ab49b9c522297e2dda788f7846134725a6de9bf45159cd59d15'),
    'concatKseed': ('concat-main.kseed', '3bab0acee4a93048aed17d67fe421fd711701cc4940eb56956d86a19f1f3ae62'),
    'packager': ('concat-packager-final.elf', 'fe4828c03e6ef13ce7efa86bec6af19a69a554f198cbd6423b2dace4bb994a1e'),
    'fullImage': ('full-concat.macho', '505b70f3209aa01cc0e840a7d6967bd71d291857c55a013f26848ecdfd599bc8'),
    'equalImage': ('equal-concat.macho', '6c68c800ce14a04950c309e35a764f9e04f2f863f1dab4663967dc0c74a5443d'),
    'concatImage': ('concat-concat.macho', 'b322b28cfaabfa48a68fed7b7fb5c8d37a8edd89cecea984e24b29c68ec4ffb6'),
}
HELPER_SHA = {
    'pair': (1408, 1476, 'd03e5dce07efed585c1fdeb653c4fa613861e1bfadc30fecdbe3fea73417920a'),
    'typed': (1536, 1768, '19eb316c255bf51dd7508bb79da72b2a6ba74a55808baf4090ae333d16544a50'),
    'strings': (2048, 2772, '1d4fb2cabb5b61eb45dea508957d2901c9cfe70076887ecaf1985eb2e1a5625a'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, digest):
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError(f'unexpected digest for {path}')
    return data


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def check_image(image, raw):
    text = 16384 * ((4096 + len(raw) + 16383) // 16384)
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
    if image[4096:4096+len(raw)] != raw or any(image[4096+len(raw):]):
        raise ValueError('generated main or zero padding')
    for name, (start, end, expected) in HELPER_SHA.items():
        if sha(image[start:end]) != expected:
            raise ValueError(f'{name} runtime helper differs')
    for offset, expected in {1044: 0xf9001e68, 1156: 0xf9004268,
                             1164: 0xf9003a68, 1172: 0xf9003e68,
                             1204: 0x940000d3, 1208: 0x940002d2,
                             1416: 0xd2a0200a}.items():
        if word(image, offset) != expected:
            raise ValueError(f'ABI instruction differs at {offset}')


def signed_run(image, output, name):
    path = output / (name + '-signed.macho')
    path.write_bytes(image)
    path.chmod(0o755)
    for command in (['/usr/bin/codesign', '--force', '--sign', '-', str(path)],
                    ['/usr/bin/codesign', '--verify', '--strict', str(path)]):
        check = subprocess.run(command, capture_output=True, timeout=15)
        if check.returncode:
            raise RuntimeError((command, check.stderr.decode(errors='replace')))
    started = time.time()
    process = subprocess.Popen([str(path)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError(f'{name} did not terminate within eight seconds')
    return {'name': name, 'signedSha256': sha(path.read_bytes()),
            'exit': process.returncode, 'stdoutHex': stdout.hex(),
            'stderrHex': stderr.hex()}, process.pid, started


def crash_state(name, pid, started):
    directory = Path.home()/'Library/Logs/DiagnosticReports'
    deadline = time.monotonic()+8
    while time.monotonic() < deadline:
        for path in directory.glob(name+'-signed.macho-*.ips'):
            if path.stat().st_mtime < started-1:
                continue
            lines = path.read_text().splitlines()
            if len(lines) < 2:
                continue
            report = json.loads('\n'.join(lines[1:]))
            if report.get('pid') != pid:
                continue
            state = report['threads'][report['faultingThread']]['threadState']
            base = report['usedImages'][0]['base']
            return report['exception']['signal'], state, base
        time.sleep(.1)
    raise RuntimeError(f'current {name} crash report not available')


def observe(artifacts, output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for path, digest in SOURCE_PINS.values():
        pin(ROOT/path, digest)
    data = {name: pin(artifacts/path, digest)
            for name, (path, digest) in ARTIFACT_PINS.items()}
    if data['fullImage'] != (artifacts/'full-concat-repeat.macho').read_bytes():
        raise ValueError('full image repeat differs')
    for name in ('compile-concat', 'extract-concat', 'compile-concat-packager-final',
                 'emit-concat-concat', 'emit-equal-concat', 'emit-full-concat',
                 'emit-full-concat-repeat'):
        receipt = json.loads((artifacts/(name+'-admission.json')).read_text())
        if receipt.get('schema') != 'amu.native-build-admission.v1' or receipt.get('exit') != 0:
            raise ValueError(f'native admission failure: {name}')
    for label in ('full', 'equal', 'concat'):
        check_image(data[label+'Image'], data[label+'Raw'])
    output.mkdir(parents=True, exist_ok=False)
    equal, _, _ = signed_run(data['equalImage'], output, 'equal')
    concat, _, _ = signed_run(data['concatImage'], output, 'concat')
    invalid_span = bytearray(data['concatImage'])
    struct.pack_into('<I', invalid_span, 1200, 0xd503201f)
    span, _, _ = signed_run(invalid_span, output, 'missing-code-length')
    no_slot = bytearray(data['fullImage'])
    struct.pack_into('<I', no_slot, 1172, 0xd503201f)
    missing, missing_pid, missing_started = signed_run(no_slot, output, 'missing-concat')
    full, full_pid, full_started = signed_run(data['fullImage'], output, 'full')
    if [(case['exit'], case['stdoutHex'], case['stderrHex'])
            for case in (equal, concat, span, missing, full)] != [
                (42, '', ''), (42, '', ''), (-5, '', ''), (-11, '', ''), (-5, '', '')]:
        raise RuntimeError('Mac runtime cases differed')
    signal, state, base = crash_state('missing-concat', missing_pid, missing_started)
    raw_return = state['lr']['value']-base-4096
    if (signal != 'SIGSEGV' or state['pc']['value'] != 0 or raw_return != 0x22fd80
            or word(data['fullRaw'], raw_return-8) != 0xf9403c10
            or word(data['fullRaw'], raw_return-4) != 0xd63f0200):
        raise ValueError('missing-slot control did not reach string_concat')
    signal, state, base = crash_state('full', full_pid, full_started)
    if (signal != 'SIGTRAP' or state['pc']['value']-base != 1764
            or [reg['value'] for reg in state['x'][1:4]] != [39, 1, 1]):
        raise ValueError('full compiler did not reach typed wire 39')
    result = {'schema': 'amu.macos-concat-runtime-probe.v1',
              'status': 'PASS_BOUNDED_CONCAT_AND_NEXT_WIRE',
              'host': [platform.system(), platform.machine(), platform.mac_ver()[0]],
              'sourceSha256': {name: digest for name, (_, digest) in SOURCE_PINS.items()},
              'artifactSha256': {name: digest for name, (_, digest) in ARTIFACT_PINS.items()},
              'repeatByteIdentical': True,
              'cases': [equal, concat, span, missing, full],
              'nextMissingRuntime': {'wire': 39, 'name': ':io/write-error',
                                     'requestKind': 1, 'resultKind': 1,
                                     'trapImageOffset': 1764},
              'fullCompilerCompleted': False, 'macSelfRebuild': False,
              'trustedUserConsent': False, 'linuxFreeBuildClosure': False}
    (output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: check-macos-concat-runtime-probe.py ARTIFACT_DIR NEW_OUTPUT_DIR')
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2]))))
