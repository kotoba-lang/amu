#!/usr/bin/env python3
"""Independently observe the bounded Darwin vector ABI and next full CLI slot."""

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
    'packager': ('seed/macos-vector-runtime-packager.kotoba', '3a1e7016921b8ccad5757eb75c35420de84fdeebd46fcd9df4d99c2d46e46f6c'),
    'positive': ('seed/macos-vector-main.kotoba', 'b9bd3659f418dac5efe593b60ce071101f881fcbc0050a2e560de2b415e7bf52'),
    'refusal': ('seed/macos-vector-refusal.kotoba', '26b19670a034c618b4cd48694e6c0cc6bed28e17ee35d5f480f2b14c329bc0c2'),
}
ARTIFACTS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'packager': ('vector-packager-v5.elf', '133a693d2296ef22a354fbea5dc77aca0de520093a7af40a977a5e276c490d42'),
    'positiveKseed': ('vector-positive.kseed', '0aa3f3eb846bcf842a50bc19eb01625ebaeb9a74a6585e00c9b9d47cc6ec3b4c'),
    'refusalKseed': ('vector-refusal.kseed', 'ba1a8fbe4899a68377f5983f73fd31d2300226ae9804865aa5662bf8664e576b'),
    'positiveRaw': ('vector-positive.raw', 'f799e5f1d88938aa9eb84636242ea5c7068388ae07bb906fd639225e8baa8ca3'),
    'refusalRaw': ('vector-refusal.raw', '3fa95dd78cf41f44d9facf0e78f33bb322a3689353d5d9de5ae85d76e47fffbc'),
    'full': ('vector-full-v5.macho', '992e7739004a9314f9630907b00e19eb192d5f5c8c225441240dc0cf9e9883e9'),
    'positive': ('vector-positive-v5.macho', 'db16020c722e19f458fa36c92a79adb86ae42dec607c03f863c17b5dc6329b2c'),
    'refusal': ('vector-refusal-v5.macho', 'a1c696745dc5da8ac3b8246cb9404a5a8821ec359ccfd3b7171b472377e3a65c'),
}
ADMISSIONS = (
    'compile-vector-packager-v5-admission.json',
    'compile-vector-positive-admission.json',
    'compile-vector-refusal-admission.json',
    'extract-vector-positive-admission.json',
    'extract-vector-refusal-admission.json',
    'package-vector-full-v5-admission.json',
    'package-vector-positive-v5-admission.json',
    'package-vector-refusal-v5-admission.json',
    'package-vector-full-v5-repeat-admission.json',
)
USAGE = b'seed: E1 usage: seed check <file> | seed compile <file> --target aarch64-macos --output <out> | seed extract-native <kseed> --symbol <name> --output <raw>\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, expected):
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f'digest mismatch: {path}')
    return data


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def inspect_image(name, image, raw):
    text_bytes = 16384 * ((8192 + len(raw) + 16383) // 16384)
    if (len(image) != text_bytes + 16384 or image[:4] != b'\xcf\xfa\xed\xfe'
            or image[8192:8192+len(raw)] != raw
            or any(image[8192+len(raw):text_bytes])):
        raise ValueError(f'{name}: image/raw extent mismatch')
    if (struct.unpack_from('<4I', image, 12) != (2, 7, 368, 0x00200005)
            or struct.unpack_from('<Q', image, 360)[0] != 1024):
        raise ValueError(f'{name}: Mach-O entry mismatch')
    if sha(image[5000:5680]) != '5dad45a211fbad808d89111570d0571e493aad01bdc8bcff3f2ec3ce9497c857':
        raise ValueError(f'{name}: vector helper bytes differ')
    expected = {
        2096: 0x140002e6, 3224: 0x10001b48, 3228: 0xf9004a68,
        3232: 0x10002d08, 3236: 0xf9004668, 3240: 0x140001b8,
        5000: 0xd2800168, 5064: 0xaa1f03e0,
        5256: 0xf9400008, 5384: 0xf9400008,
        5448: 0xf9400008, 5576: 0xf9400008,
        1176: 0xd2c01808 if name == 'full' else 0xd2800008,
        1220: 0xf9410268 if name == 'full' else 0xf95f4668,
    }
    for offset, value in expected.items():
        if word(image, offset) != value:
            raise ValueError(f'{name}: ABI instruction differs at {offset}')
    return {'imageSha256': sha(image), 'rawSha256': sha(raw),
            'textBytes': text_bytes, 'vectorHelperSha256': sha(image[5000:5680])}


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


def crash_report(name, pid, started):
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
                return report
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
        admission = json.loads((artifacts / name).read_text())
        if (admission['schema'] != 'amu.native-build-admission.v1'
                or admission['capacity'] != 2 or admission['exit'] != 0):
            raise ValueError(f'build admission failed: {name}')
        admissions[name] = admission
    if data['full'] != (artifacts / 'vector-full-v5-repeat.macho').read_bytes():
        raise ValueError('full image repeat differs')
    images = {name: inspect_image(name, data[name],
              data['fullRaw' if name == 'full' else name+'Raw'])
              for name in ('full', 'positive', 'refusal')}

    positive, _, _ = signed_run(data['positive'], output, 'vector-positive', [])
    if (positive['exit'], positive['stdoutHex'], positive['stderrHex']) != (42, '', ''):
        raise ValueError('vector positive did not return 42')
    refusal, refusal_pid, refusal_started = signed_run(data['refusal'], output, 'vector-refusal', [])
    if (refusal['exit'], refusal['stdoutHex'], refusal['stderrHex']) != (-4, '', ''):
        raise ValueError('out-of-range vector index did not trap')
    report = crash_report('vector-refusal', refusal_pid, refusal_started)
    refusal_base = next(x['base'] for x in report['usedImages']
                        if 'vector-refusal-signed.macho' in x.get('path', ''))
    refusal_pc = report['threads'][report['faultingThread']]['threadState']['pc']['value']
    if (report['exception']['signal'] != 'SIGILL'
            or refusal_pc - refusal_base != 8192 + 0x58
            or word(data['refusalRaw'], 0x58) != 0):
        raise ValueError('vector refusal was not the compiled inline bound trap')

    noargs, _, _ = signed_run(data['full'], output, 'vector-full-noargs', [])
    if (noargs['exit'], noargs['stdoutHex'], noargs['stderrHex']) != (2, '', USAGE.hex()):
        raise ValueError('full CLI usage differs')
    full, full_pid, full_started = signed_run(
        data['full'], output, 'vector-full-check', ['check', 'seed/macos-vector-main.kotoba'])
    if (full['exit'], full['stdoutHex'], full['stderrHex']) != (-11, '', ''):
        raise ValueError('full CLI did not reach expected next missing slot')
    report = crash_report('vector-full-check', full_pid, full_started)
    full_base = next(x['base'] for x in report['usedImages']
                     if 'vector-full-check-signed.macho' in x.get('path', ''))
    state = report['threads'][report['faultingThread']]['threadState']
    return_offset = state['lr']['value'] - full_base - 8192
    if (report['exception']['signal'] != 'SIGSEGV' or state['pc']['value'] != 0
            or return_offset != 0x2d78
            or word(data['fullRaw'], return_offset - 8) != 0xf940b410
            or word(data['fullRaw'], return_offset - 4) != 0xd63f0200):
        raise ValueError('full CLI did not stop at bytes_from_vector slot 360')
    receipt = {
        'schema': 'amu.macos-vector-runtime-probe.v1',
        'status': 'PASS_VECTOR_NEXT_BYTES_FROM_VECTOR',
        'qualification': 'diagnostic-bootstrap-only',
        'sourceSha256': sources, 'imageChecks': images,
        'admissions': admissions, 'fullImageRepeatEqual': True,
        'cases': [positive, refusal, noargs, full],
        'refusalSignal': 'SIGILL', 'refusalImagePcOffset': 8192 + 0x58,
        'nextMissingSlot': {'name': 'bytes_from_vector', 'offset': 360,
                            'rawReturnOffset': return_offset},
    }
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = observe(args.artifacts, args.output)
    print(result['status'])
