#!/usr/bin/env python3
"""Verify real Darwin argv admission and the next full Amu ABI boundary."""

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
    'packager': ('seed/macos-cli-runtime-packager.kotoba', '33ee54a8a08845b6c26d88d24f29cc07e5c7c6ec5e1d0b65be6ccbf6b9629fad'),
    'cliFixture': ('seed/macos-cli-main.kotoba', 'e00bdb075096665cfeb1ee12f0316a5eae85b7d839fdb290ff2df72d304c42b4'),
    'stderrFixture': ('seed/macos-stderr-main.kotoba', 'c7850316cfc6e801abcbb541febf990064b1a00f27bb13d609c9f397920f1838'),
}
ARTIFACT_PINS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'cliRaw': ('cli-main.raw', '8a5a6db0a4cf65b614ff7acd0f4869e963a0d4582d6893cdc0c7e13c2a401fc4'),
    'stderrRaw': ('stderr-main.raw', 'aca676d4dcb50bdf270235068d1c6aec4d240574ec868b7ed2a612cb5f374a05'),
    'cliKseed': ('cli-main.kseed', 'f949da2ace16645d32e00fbac0e436e3453bfa40dc6d63cc22a2bf686ffa012e'),
    'packager': ('cli-packager-final2.elf', '25cbace006047d8a3d28d0614d7dae5131ec3dfde1cdb13f3e300d0d6b48bd5b'),
    'cliAllowed': ('cli-allowed-final.macho', '2bf0b830c0ddc542b3e399b833a1d5cb96df673dbc7c267a4fbdc156924b9f9f'),
    'cliDenied': ('cli-denied-final.macho', 'c956abaca6dff048006013856a721b00b8efe6a499c314ee0357e182ace55117'),
    'cliWrongGrant': ('cli-wrong-grant-final.macho', '007515650fe54a7877b45d7badf571383290d890447d134defc703b6f6e9e52b'),
    'fullImage': ('full-cli-stderr-final.macho', 'cf1c448e19a3f746557ee23b253cb09b83da4e037eea670ae2506c72341763ed'),
    'stderrControl': ('stderr-control-final.macho', 'b6016a2868c772f9d815855d951e96650d70aef345fe10495a39e42977226839'),
}
HELPER_SHA = {
    'pair': (1408, 1476, 'd03e5dce07efed585c1fdeb653c4fa613861e1bfadc30fecdbe3fea73417920a'),
    'legacyTyped': (1536, 1768, '19eb316c255bf51dd7508bb79da72b2a6ba74a55808baf4090ae333d16544a50'),
    'strings': (2048, 2772, '1d4fb2cabb5b61eb45dea508957d2901c9cfe70076887ecaf1985eb2e1a5625a'),
    'stderr': (2816, 3200, '6fa157aa494ef7f401fb8d3ce099c531bbc5535de7f5ec97b0d15663b837b717'),
    'cli': (3216, 3716, '674fe8fb4ee46a4b5be0407875547e5fc698bb340ab6b8b8b483be8e0affbff0'),
}
CASES = (
    ('cliAllowed', 'cliRaw', 0xd2c00808),
    ('cliDenied', 'cliRaw', 0xd2800008),
    ('cliWrongGrant', 'cliRaw', 0xd2c01008),
    ('fullImage', 'fullRaw', 0xd2c01808),
    ('stderrControl', 'stderrRaw', 0xd2c01008),
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
    for offset, instruction in {1032: 0x94000222, 1156: 0xf9004268,
                                1176: grant, 1200: 0xf900c668,
                                3216: 0xf900d260, 3220: 0xf900d661,
                                3256: 0x17ffff92, 3372: 0x97fffec2}.items():
        if word(image, offset) != instruction:
            raise ValueError(f'ABI instruction differs at {offset}')


def signed_run(image, output, name, args):
    path = output/(name+'-signed.macho')
    path.write_bytes(image)
    path.chmod(0o755)
    for command in (['/usr/bin/codesign', '--force', '--sign', '-', str(path)],
                    ['/usr/bin/codesign', '--verify', '--strict', str(path)]):
        check = subprocess.run(command, capture_output=True, timeout=15)
        if check.returncode:
            raise RuntimeError((command, check.stderr.decode(errors='replace')))
    started = time.time()
    process = subprocess.Popen([str(path), *args], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError(f'{name} did not terminate within eight seconds')
    return {'name': name, 'args': args, 'signedSha256': sha(path.read_bytes()),
            'exit': process.returncode, 'stdoutHex': stdout.hex(),
            'stderrHex': stderr.hex()}, process.pid, started


def missing_slot(name, pid, started, raw):
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
            raw_return = state['lr']['value']-base-4096
            if (report['exception']['signal'] != 'SIGSEGV'
                    or state['pc']['value'] != 0 or raw_return != 0x2910
                    or word(raw, raw_return-8) != 0xf9404810
                    or word(raw, raw_return-4) != 0xd63f0200):
                raise ValueError('full compiler did not reach slot 144')
            return {'nextSlotOffset': 144, 'nextSlot': 'string_code_point_at',
                    'returnRawOffset': raw_return}
        time.sleep(.1)
    raise RuntimeError('current full compiler crash report not available')


def observe(artifacts, output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for path, digest in SOURCE_PINS.values():
        pin(ROOT/path, digest)
    data = {name: pin(artifacts/path, digest)
            for name, (path, digest) in ARTIFACT_PINS.items()}
    if data['fullImage'] != (artifacts/'full-cli-stderr-final-repeat.macho').read_bytes():
        raise ValueError('full image repeat differs')
    for name in ('compile-cli-fixture', 'extract-cli-fixture',
                 'compile-cli-packager-final2', 'emit-full-cli-stderr-final-repeat',
                 *(f'emit-{image}' for image in (
                     'cli-allowed-final', 'cli-denied-final',
                     'cli-wrong-grant-final', 'full-cli-stderr-final',
                     'stderr-control-final'))):
        receipt = json.loads((artifacts/(name+'-admission.json')).read_text())
        if receipt.get('schema') != 'amu.native-build-admission.v1' or receipt.get('exit') != 0:
            raise ValueError(f'native admission failure: {name}')
    for image, raw, grant in CASES:
        check_image(data[image], data[raw], grant)
    for denied in ('cliDenied', 'cliWrongGrant'):
        a, b = bytearray(data['cliAllowed']), bytearray(data[denied])
        a[1176:1180] = b[1176:1180]
        if a != b:
            raise ValueError('CLI grant control changed other image bytes')
    output.mkdir(parents=True, exist_ok=False)
    args = ['check', 'fixture.kotoba']
    observed = []
    for name, arguments in (('cliAllowed', args), ('cliDenied', args),
                            ('cliWrongGrant', args), ('stderrControl', []),
                            ('fullImage', []), ('fullImage', args)):
        label = name + ('-with-args' if name == 'fullImage' and arguments else '-no-args' if name == 'fullImage' else '')
        result, pid, started = signed_run(data[name], output, label, arguments)
        observed.append(result)
        expected = {'cliAllowed': (42, '', ''), 'cliDenied': (-5, '', ''),
                    'cliWrongGrant': (-5, '', ''),
                    'stderrControl': (42, '', b'diagnostic\n'.hex()),
                    'fullImage': (-11, '', '')}[name]
        if (result['exit'], result['stdoutHex'], result['stderrHex']) != expected:
            raise RuntimeError(f'{label} process result differs')
        if name == 'fullImage':
            missing_slot(label, pid, started, data['fullRaw'])
    report = {'schema': 'amu.macos-cli-runtime-probe.v1',
              'status': 'PASS_REAL_ARGV_AND_NEXT_SLOT',
              'host': [platform.system(), platform.machine(), platform.mac_ver()[0]],
              'sourceSha256': {name: digest for name, (_, digest) in SOURCE_PINS.items()},
              'artifactSha256': {name: digest for name, (_, digest) in ARTIFACT_PINS.items()},
              'repeatByteIdentical': True, 'cliGrantOnlyImageDelta': True,
              'cases': observed,
              'nextMissingRuntime': {'slotOffset': 144, 'name': 'string_code_point_at',
                                     'rawReturnOffset': 0x2910},
              'realArgsAdmitted': True, 'fullCompilerCheckCompleted': False,
              'macSelfRebuild': False, 'trustedUserConsent': False,
              'linuxFreeBuildClosure': False}
    (output/'receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: check-macos-cli-runtime-probe.py ARTIFACT_DIR NEW_OUTPUT_DIR')
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2]))))
