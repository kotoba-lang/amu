#!/usr/bin/env python3
"""Verify separate Darwin stdout/stderr grants and the no-arg full Amu CLI."""

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
    'packager': ('seed/macos-stderr-runtime-packager.kotoba', '1133f5678b693b5c50a08e472d398de5604d63978907970bacd5850e960de569'),
    'stderrFixture': ('seed/macos-stderr-main.kotoba', 'c7850316cfc6e801abcbb541febf990064b1a00f27bb13d609c9f397920f1838'),
    'stdoutFixture': ('seed/macos-io-main.kotoba', 'e8c575e4e4e47980e82b250d13e43230c4a0996554e61f57df5b0696617e011a'),
}
ARTIFACT_PINS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'concatRaw': ('concat-main.raw', 'f1d28074744d0ab49b9c522297e2dda788f7846134725a6de9bf45159cd59d15'),
    'stderrRaw': ('stderr-main.raw', 'aca676d4dcb50bdf270235068d1c6aec4d240574ec868b7ed2a612cb5f374a05'),
    'stdoutRaw': ('stdout-main.raw', 'b8999afcfe0ab0a2198471475dfa55109e6bf2a0749e32de138e0f244b560e9c'),
    'stderrKseed': ('stderr-main.kseed', '86ea7bba2baea877a1f6afe60f731481191cc6dc7b67a934283edbc37417417a'),
    'stdoutKseed': ('stdout-main.kseed', '3cc65f8ed2b4439ed8733be692076e9aa2d511cc876b3a0fbaa9b4a274715ab9'),
    'packager': ('stderr-packager-final2.elf', '815675a9c7afaef77e21b4622950b5b5a9df10fb8f1054e5a67a4e7b7e7f344a'),
    'stderrAllowed': ('stderr-stderr-final.macho', 'fab3f472a7adf01f276181b852182be4a65d0f933ce71cd7bd915c9638601770'),
    'stderrWrongGrant': ('stderr-stdout-deny-final.macho', '5d11d173d876dea8469c5ff05667b047a1fd218b0d0f411f19cf361d29475eef'),
    'stdoutAllowed': ('stdout-stdout-final.macho', '2393858d603f8f6ec7ce4cacb3adcd5ef8df26520bda90fb8018669086d00b84'),
    'stdoutWrongGrant': ('stdout-stderr-deny-final.macho', '9d9147045b7a9b335e6ce5bb31fab755751dd679e78a7fe46dc0f54f5bd3420a'),
    'concat': ('concat-deny-final.macho', '7f3c95e7c84f654e33a890ec9f118a5027c4966c4ce81060fad5b5a80f529a17'),
    'fullDenied': ('full-deny-final.macho', '0504d2c63e907de73b4e91cf521ba38134aab78a8aaf0a10f26c4539350b2eb4'),
    'fullAllowed': ('full-stderr-final.macho', 'e79d63ed14cfc78c73bbb31d0b2c9ee2f1e26d16e2dcfddd4553f4844e67bb6f'),
    'linuxOracle': ('linux-root-noargs-oracle.json', 'f013b0c88f784666ad1534b18b38ec4292a1368325f3e84bb1c225f790fc854a'),
}
HELPER_SHA = {
    'pair': (1408, 1476, 'd03e5dce07efed585c1fdeb653c4fa613861e1bfadc30fecdbe3fea73417920a'),
    'legacyTyped': (1536, 1768, '19eb316c255bf51dd7508bb79da72b2a6ba74a55808baf4090ae333d16544a50'),
    'strings': (2048, 2772, '1d4fb2cabb5b61eb45dea508957d2901c9cfe70076887ecaf1985eb2e1a5625a'),
    'stderr': (2816, 3200, '6fa157aa494ef7f401fb8d3ce099c531bbc5535de7f5ec97b0d15663b837b717'),
}
CASES = (
    ('stderrAllowed', 'stderrRaw', 0xd2c01008),
    ('stderrWrongGrant', 'stderrRaw', 0xd2c00408),
    ('stdoutAllowed', 'stdoutRaw', 0xd2c00408),
    ('stdoutWrongGrant', 'stdoutRaw', 0xd2c01008),
    ('concat', 'concatRaw', 0xd2800008),
    ('fullDenied', 'fullRaw', 0xd2800008),
    ('fullAllowed', 'fullRaw', 0xd2c01008),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, digest):
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError(f'unexpected digest for {path}')
    return data


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def check_image(image, raw, grant):
    text = 16384*((4096+len(raw)+16383)//16384)
    if len(image) != text+16384 or image[:4] != b'\xcf\xfa\xed\xfe':
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
            raise ValueError(f'{name} helper differs')
    expected = {1152: 0x10003408, 1156: 0xf9004268,
                1176: grant, 1200: 0xf900c668,
                1212: 0xf100081f if len(raw) == 3254848 else 0xf100a81f,
                1232: 0xd2800040 if len(raw) == 3254848 else 0xd2800540,
                2824: 0x17fffebe, 2940: 0x97ffff2e}
    for offset, instruction in expected.items():
        if word(image, offset) != instruction:
            raise ValueError(f'ABI instruction differs at {offset}')


def signed_run(image, output, name):
    path = output/(name+'-signed.macho')
    path.write_bytes(image)
    path.chmod(0o755)
    for command in (['/usr/bin/codesign', '--force', '--sign', '-', str(path)],
                    ['/usr/bin/codesign', '--verify', '--strict', str(path)]):
        check = subprocess.run(command, capture_output=True, timeout=15)
        if check.returncode:
            raise RuntimeError((command, check.stderr.decode(errors='replace')))
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
            'stderrHex': stderr.hex()}


def observe(artifacts, output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for path, digest in SOURCE_PINS.values():
        pin(ROOT/path, digest)
    data = {name: pin(artifacts/path, digest)
            for name, (path, digest) in ARTIFACT_PINS.items()}
    if data['fullAllowed'] != (artifacts/'full-stderr-final-repeat.macho').read_bytes():
        raise ValueError('full image repeat differs')
    for name in ('compile-stderr-fixture', 'extract-stderr-fixture',
                 'compile-stdout-fixture', 'extract-stdout-fixture',
                 'compile-stderr-packager-final2', 'linux-root-oracle',
                 'emit-full-stderr-final-repeat',
                 *(f'emit-{image}' for image in (
                     'stderr-stderr-final', 'stderr-stdout-deny-final',
                     'stdout-stdout-final', 'stdout-stderr-deny-final',
                     'concat-deny-final', 'full-deny-final', 'full-stderr-final'))):
        admission = json.loads((artifacts/(name+'-admission.json')).read_text())
        if admission.get('schema') != 'amu.native-build-admission.v1' or admission.get('exit') != 0:
            raise ValueError(f'native admission failure: {name}')
    for image, raw, grant in CASES:
        check_image(data[image], data[raw], grant)
    for allowed, denied in (('stderrAllowed', 'stderrWrongGrant'),
                            ('stdoutAllowed', 'stdoutWrongGrant'),
                            ('fullAllowed', 'fullDenied')):
        a, b = bytearray(data[allowed]), bytearray(data[denied])
        a[1176:1180] = b[1176:1180]
        if a != b:
            raise ValueError(f'{allowed}/{denied} changed outside the grant')
    oracle = json.loads(data['linuxOracle'])
    if oracle['exit'] != 2 or oracle['stdoutHex'] != '' or not bytes.fromhex(oracle['stderrHex']).startswith(b'seed: E1 usage:'):
        raise ValueError('Linux root no-argument oracle differs')
    output.mkdir(parents=True, exist_ok=False)
    results = {image: signed_run(data[image], output, image) for image, _, _ in CASES}
    expected = {
        'stderrAllowed': (42, '', b'diagnostic\n'.hex()),
        'stderrWrongGrant': (-5, '', ''),
        'stdoutAllowed': (42, b'native\n'.hex(), ''),
        'stdoutWrongGrant': (-5, '', ''),
        'concat': (42, '', ''),
        'fullDenied': (-5, '', ''),
        'fullAllowed': (2, '', oracle['stderrHex']),
    }
    for name, result in results.items():
        if (result['exit'], result['stdoutHex'], result['stderrHex']) != expected[name]:
            raise RuntimeError(f'{name} process result differs')
    report = {'schema': 'amu.macos-stderr-runtime-probe.v1',
              'status': 'PASS_SEPARATE_STDERR_GRANT_AND_NOARG_CLI',
              'host': [platform.system(), platform.machine(), platform.mac_ver()[0]],
              'sourceSha256': {name: digest for name, (_, digest) in SOURCE_PINS.items()},
              'artifactSha256': {name: digest for name, (_, digest) in ARTIFACT_PINS.items()},
              'repeatByteIdentical': True, 'grantOnlyImageDelta': True,
              'linuxNoArgOracle': oracle, 'cases': list(results.values()),
              'fullCompilerNoArgCompleted': True, 'fullCompilerCompileCompleted': False,
              'macSelfRebuild': False, 'trustedUserConsent': False,
              'linuxFreeBuildClosure': False}
    (output/'receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: check-macos-stderr-runtime-probe.py ARTIFACT_DIR NEW_OUTPUT_DIR')
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2]))))
