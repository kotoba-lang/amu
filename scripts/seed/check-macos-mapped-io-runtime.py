#!/usr/bin/env python3
"""Observe the Kotoba-built Darwin mapped-pair plus typed :io/write slice."""

import hashlib
import json
import platform
import resource
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PINS = {
    'root': ('seed/bootstrap/aarch64-linux-static-root.elf', '285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1'),
    'guest': ('seed/macos-io-main.kotoba', 'e8c575e4e4e47980e82b250d13e43230c4a0996554e61f57df5b0696617e011a'),
    'packager': ('seed/macos-mapped-io-runtime-packager.kotoba', '23cd824890c0712e97a0197bcf3dd08b57c0f5065d5ec8cbcadff6990f8c29df'),
}
ARTIFACT_PINS = {
    'guestRaw': ('io-main.raw', 'b8999afcfe0ab0a2198471475dfa55109e6bf2a0749e32de138e0f244b560e9c'),
    'packager': ('packager-v3.elf', '0cfba77685f409ecbb2ae19be4ccc004be879524c95e2005a5de0e102cea8177'),
    'allow': ('io-allow-v3.macho', '8152a478f33865aae9aeccd1c92900aeb3b424f51922c9365322a64621d9eed3'),
    'deny': ('io-deny-v3.macho', 'aad6ca2bd2b960e0dec14761e8638b394f7368bb21d5aa2d7bed0c9ceb965a66'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f'digest mismatch: {path}: {actual}')
    return path.read_bytes()


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def run(command):
    return subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                          timeout=10, check=False)


def signed_and_run(data, output, name):
    path = output / (name + '-signed.macho')
    path.write_bytes(data)
    path.chmod(0o755)
    for command in (['/usr/bin/codesign', '--force', '--sign', '-', str(path)],
                    ['/usr/bin/codesign', '--verify', '--strict', str(path)]):
        result = run(command)
        if result.returncode:
            raise RuntimeError((command, result.stderr.decode(errors='replace')))
    result = run([str(path)])
    return {'name': name, 'signedSha256': digest(path), 'exit': result.returncode,
            'stdoutHex': result.stdout.hex(), 'stderrHex': result.stderr.hex()}


def check_image(image, raw):
    if len(image) != 32768 or len(raw) != 135 or image[:4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('image or generated guest extent')
    if struct.unpack_from('<4I', image, 12) != (2, 7, 368, 0x00200005):
        raise ValueError('Mach-O header')
    cursor = 32
    commands = []
    for _ in range(7):
        kind, length = struct.unpack_from('<II', image, cursor)
        commands.append((kind, length))
        cursor += length
    if commands != [(25, 72)]*4 + [(14, 32), (0x80000028, 24), (50, 24)] or cursor != 400:
        raise ValueError('Mach-O load commands')
    if (struct.unpack_from('<4Q', image, 128) != (0x100000000, 16384, 0, 16384)
            or struct.unpack_from('<4Q', image, 200) != (0x100004000, 16384, 16384, 16384)
            or struct.unpack_from('<Q', image, 360)[0] != 1024):
        raise ValueError('segment or entry contract')
    if image[2048:2183] != raw or any(image[2183:16384]) or any(image[16384:]):
        raise ValueError('guest code, executable padding or zero data')
    required = {
        1044: 0xf9001e68,   # pair_new slot 56
        1096: 0xf9009660,   # mmap pair arena -> context +296
        1140: 0xf9009a60,   # mmap mark arena -> context +304
        1156: 0xf9004268,   # typed_cap slot 128
        1416: 0xd2a0200a,   # 16,777,216-pair bound
        1584: 0xf9400109,   # count through count pointer
        1596: 0xf9409408,   # pair arena base, separate from count pointer
        1616: 0xf101015f,   # output capped at 64 bytes
    }
    for offset, expected in required.items():
        if word(image, offset) != expected:
            raise ValueError(f'ABI word at {offset} differs: {word(image, offset):08x}')


def observe(artifacts, output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Apple Silicon Mac required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for path, sha in SOURCE_PINS.values():
        pinned(ROOT/path, sha)
    paths = {name: artifacts/path for name, (path, _) in ARTIFACT_PINS.items()}
    blobs = {name: pinned(paths[name], sha) for name, (_, sha) in ARTIFACT_PINS.items()}
    if blobs['allow'] != (artifacts/'io-allow-repeat-v3.macho').read_bytes():
        raise ValueError('repeat image differs')
    for name in ('compile-v3', 'emit-allow-v4', 'emit-deny-v4', 'emit-allow-repeat-v4'):
        admission = json.loads((artifacts/(name+'-admission.json')).read_text())
        if admission.get('schema') != 'amu.native-build-admission.v1' or admission.get('exit') != 0:
            raise ValueError(f'native build queue failure: {name}')
    for name, artifact in (('invalid-mode', 'io-invalid-v3.macho'),
                           ('short-input', 'io-short-v3.macho')):
        admission = json.loads((artifacts/(name+'-v4-admission.json')).read_text())
        if (admission.get('schema') != 'amu.native-build-admission.v1'
                or admission.get('exit') != 2 or (artifacts/artifact).exists()):
            raise ValueError(f'packager refusal or output mismatch: {name}')
    raw = blobs['guestRaw']
    if word(raw, 0) != 0xa9bf7bfd:
        raise ValueError('generated guest prologue')
    allow, deny = blobs['allow'], blobs['deny']
    check_image(allow, raw)
    check_image(deny, raw)
    if (word(allow, 1160) != 0xd2c00408 or word(deny, 1160) != 0xd2800008
            or allow[:1160] != deny[:1160] or allow[1164:] != deny[1164:]):
        raise ValueError('grant edge is not the sole difference')
    output.mkdir(parents=True, exist_ok=False)
    cases = [signed_and_run(allow, output, 'allow'),
             signed_and_run(deny, output, 'deny')]
    no_capacity = bytearray(allow)
    struct.pack_into('<I', no_capacity, 1416, 0xd280000a)
    cases.append(signed_and_run(no_capacity, output, 'zero-pair-capacity'))
    no_output = bytearray(allow)
    struct.pack_into('<I', no_output, 1616, 0xf100015f)
    cases.append(signed_and_run(no_output, output, 'zero-output-bound'))
    expected = [(42, b'native\n', b''), (-5, b'', b''),
                (-5, b'', b''), (-5, b'', b'')]
    for case, (code, stdout, stderr) in zip(cases, expected):
        if (case['exit'], bytes.fromhex(case['stdoutHex']),
                bytes.fromhex(case['stderrHex'])) != (code, stdout, stderr):
            raise RuntimeError(f'actual Mac execution differs: {case}')
    receipt = {'schema': 'amu.macos-mapped-io-runtime.v1',
               'status': 'PASS_HOST_DIAGNOSTIC',
               'host': [platform.system(), platform.machine(), platform.mac_ver()[0]],
               'sourceSha256': {name: sha for name, (_, sha) in SOURCE_PINS.items()},
               'artifactSha256': {name: sha for name, (_, sha) in ARTIFACT_PINS.items()},
               'pairArenaBytes': 268435456, 'markArenaBytes': 16777216,
               'guestRawBytes': 135, 'grantWordOffset': 1160,
               'repeatByteIdentical': True,
               'invalidModeRefusedWithoutArtifact': True,
               'shortGuestRefusedWithoutArtifact': True, 'cases': cases,
               'fullCompilerExecuted': False, 'trustedUserConsent': False,
               'linuxFreeBuildClosure': False}
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: check-macos-mapped-io-runtime.py ARTIFACT_DIR NEW_OUTPUT_DIR')
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2]))))
