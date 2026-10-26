#!/usr/bin/env python3
"""Independently run Darwin UTF-8/substring ABI controls and locate the next slot."""

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
SOURCES = {
    'root': ('seed/bootstrap/aarch64-linux-static-root.elf', '285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1'),
    'codepointPackager': ('seed/macos-codepoint-runtime-packager.kotoba', '4cb9dbdded25e9ed2b21c9245369652ec9aeabcf14438c0e157c2f3679298b68'),
    'codepointPositive': ('seed/macos-codepoint-main.kotoba', 'b1382a4ffb83779f69289cae0527170dd0e1c4df9071fa6738d1eead2d7a7a34'),
    'codepointRefusal': ('seed/macos-codepoint-refusal.kotoba', '46eb5990c89064ef473395244ccaacadca3dfcbc9ec155a1288a73146e3d2002'),
    'substringPackager': ('seed/macos-substring-runtime-packager.kotoba', '710742a5d9a1200573eae47c4a9004f8f123d639f53fa6288181ae8f5a9f2250'),
    'substringPositive': ('seed/macos-substring-main.kotoba', 'd27cd0834be449c451f32b15bacc8be5c2e1523db4173d396bc573e424f2a44c'),
    'substringRefusal': ('seed/macos-substring-refusal.kotoba', '6b26421f636a25af659473b3f486d519a00b62ab9959f8d1fde2c3ce986c5ea7'),
}
ARTIFACTS = {
    'fullRaw': ('full-compiler-main.raw', '164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e'),
    'codepointPackager': ('codepoint-packager-final.elf', 'cb3b736e1a2302daf85bed53c3fc32db3c46eb78581af1af397d44d7873263a2'),
    'codepointPositiveKseed': ('codepoint-positive.kseed', '43100fef68837127bd057e70bb3e0e4f843ba0937d5dab7007856f0e1bb726d6'),
    'codepointRefusalKseed': ('codepoint-refusal.kseed', 'd5a3db03cec3dd1de005f8c0332fa686bcd8bd9688106f8d8142fef8914a1934'),
    'codepointPositiveRaw': ('codepoint-positive.raw', '359e343d867bfa124cdb3e48aa814ef2012ffc9683b063a5d870bbda7c2a9cc5'),
    'codepointRefusalRaw': ('codepoint-refusal.raw', '9a53ac58b7e728a3293bf7e2dcbeb2880b6b11f1aaf140831bc5a05ed154afae'),
    'codepointFull': ('codepoint-full-final.macho', '784a4f5aa7696e41a74d49473b369e0d3548015b05e32ce94531a6fbf08bdb69'),
    'codepointPositive': ('codepoint-positive-final.macho', '4b2698aac4a7bd836c76d18e1d46ee2ec41aa89f232cdfa0262efcca5df01fde'),
    'codepointRefusal': ('codepoint-refusal-final.macho', '7b235ff868a252cb7db5268811f2ae9718df5577d57d905fa11cd0d222a7781a'),
    'substringPackager': ('substring-packager.elf', '3bd141bc820474091481822311216ca0259aa82751d3768d9a4dae3e2abe5734'),
    'substringPositiveKseed': ('substring-positive.kseed', '4f6c6c11763c54ec1fe670f4378122a0761992d12e257a6faa5bdd4d483fa025'),
    'substringRefusalKseed': ('substring-refusal.kseed', '76d6c4158384af11b50d945453318bfb851e5130e9d4cc480a4a175920b97ffd'),
    'substringPositiveRaw': ('substring-positive.raw', '539a00397fa8dbfe4735f60f936f1c258700b9d70d15bef60878d23e1a5f5916'),
    'substringRefusalRaw': ('substring-refusal.raw', '68f467d8de53c856cf8d47c40bbb75396463eca0f372bcb1a58f46dd66adade8'),
    'substringFull': ('substring-full-final.macho', '601064617344214b00d466f8e2224275d15247ad1dd933583c1d3155fc79931e'),
    'substringPositive': ('substring-positive-final.macho', '14d76fabbe5d9e6f9c27fd3055cecee7bb201fa7e33e0a383b81d4d3f2f55e93'),
    'substringRefusal': ('substring-refusal-final.macho', '1047be31c3f2839b9a312667b4c75612e33cf22d862e27662dff9887beb6f87d'),
}
HELPERS = {
    'pair': (1408, 1476, 'd03e5dce07efed585c1fdeb653c4fa613861e1bfadc30fecdbe3fea73417920a'),
    'legacyTyped': (1536, 1768, '19eb316c255bf51dd7508bb79da72b2a6ba74a55808baf4090ae333d16544a50'),
    'strings': (2048, 2772, '1d4fb2cabb5b61eb45dea508957d2901c9cfe70076887ecaf1985eb2e1a5625a'),
    'stderr': (2816, 3200, '6fa157aa494ef7f401fb8d3ce099c531bbc5535de7f5ec97b0d15663b837b717'),
    'codepoint': (4096, 4664, '4aa9cdb245b5b4d4dcac42d1bb57744aa1ec2db212b2cfaae6f3f6474494afdc'),
    'substring': (4672, 4940, '6de3f5368aa1a76f44517a7ab08bdb6d3590cd30c7c48731678cc923fb0c466b'),
}
USAGE = b'seed: E1 usage: seed check <file> | seed compile <file> --target aarch64-macos --output <out> | seed extract-native <kseed> --symbol <name> --output <raw>\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, digest):
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError(f'unexpected digest for {path}')
    return data


def word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def check_image(image, raw, *, substring, grant):
    text = 16384 * ((8192 + len(raw) + 16383) // 16384)
    if (len(image) != text + 16384 or image[:4] != b'\xcf\xfa\xed\xfe'
            or image[8192:8192+len(raw)] != raw or any(image[8192+len(raw):text])):
        raise ValueError('Mach-O/raw extent mismatch')
    if (struct.unpack_from('<4I', image, 12) != (2, 7, 368, 0x00200005)
            or struct.unpack_from('<Q', image, 360)[0] != 1024
            or struct.unpack_from('<4Q', image, 128) != (0x100000000, text, 0, text)):
        raise ValueError('Mach-O header or entry mismatch')
    for name, (start, end, digest) in HELPERS.items():
        if name == 'substring' and not substring:
            continue
        if sha(image[start:end]) != digest:
            raise ValueError(f'{name} helper differs')
    expected = {1176: grant, 3216: 0xf900d260, 3220: 0xf900d661,
                3224: 0x10001b48, 3228: 0xf9004a68, 8192: word(raw, 0)}
    expected.update({3232: 0x10002d08, 3236: 0xf9004668, 3240: 0xd65f03c0}
                    if substring else {3232: 0xd65f03c0})
    for at, value in expected.items():
        if word(image, at) != value:
            raise ValueError(f'ABI instruction differs at {at}')


def signed_run(image, output, name, arguments):
    path = output / (name + '-signed.macho')
    path.write_bytes(image)
    path.chmod(0o755)
    for command in (['/usr/bin/codesign', '--force', '--sign', '-', str(path)],
                    ['/usr/bin/codesign', '--verify', '--strict', str(path)]):
        check = subprocess.run(command, capture_output=True, timeout=15)
        if check.returncode:
            raise RuntimeError((command, check.stderr.decode(errors='replace')))
    started = time.time()
    process = subprocess.Popen([str(path), *arguments], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError(f'{name} timed out')
    return {'name': name, 'args': arguments, 'signedSha256': sha(path.read_bytes()),
            'exit': process.returncode, 'stdoutHex': stdout.hex(),
            'stderrHex': stderr.hex()}, process.pid, started


def missing_slot(name, pid, started, raw, raw_return, slot):
    reports = Path.home() / 'Library/Logs/DiagnosticReports'
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        for path in reports.glob(name + '-signed.macho-*.ips'):
            if path.stat().st_mtime < started - 1:
                continue
            lines = path.read_text().splitlines()
            if len(lines) < 2:
                continue
            report = json.loads('\n'.join(lines[1:]))
            if report.get('pid') != pid:
                continue
            state = report['threads'][report['faultingThread']]['threadState']
            base = report['usedImages'][0]['base']
            at = state['lr']['value'] - base - 8192
            if (report['exception']['signal'] != 'SIGSEGV'
                    or state['pc']['value'] != 0 or at != raw_return
                    or word(raw, at - 8) != 0xf9400000 | (slot // 8 << 10) | 0x10
                    or word(raw, at - 4) != 0xd63f0200):
                raise ValueError(f'{name} did not reach expected slot {slot}')
            return
        time.sleep(.1)
    raise RuntimeError(f'current crash report unavailable for {name}')


def observe(artifacts, output):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Apple Silicon macOS required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for path, digest in SOURCES.values():
        pin(ROOT / path, digest)
    data = {name: pin(artifacts / path, digest)
            for name, (path, digest) in ARTIFACTS.items()}
    for stage in ('codepoint', 'substring'):
        if data[stage+'Full'] != (artifacts / f'{stage}-full-repeat.macho').read_bytes():
            raise ValueError(f'{stage} image repeat differs')
        for name in (f'compile-{stage}-packager-final' if stage == 'codepoint' else 'compile-substring-packager',
                     *(f'{step}-{stage}-{case}' for step in ('compile', 'extract', 'emit') for case in ('positive', 'refusal')),
                     f'emit-{stage}-full', f'emit-{stage}-full-repeat'):
            receipt = json.loads((artifacts / (name + '-admission.json')).read_text())
            if receipt.get('schema') != 'amu.native-build-admission.v1' or receipt.get('exit') != 0:
                raise ValueError(f'native admission failed: {name}')
        for case in ('Positive', 'Refusal', 'Full'):
            raw = data['fullRaw' if case == 'Full' else stage+case+'Raw']
            check_image(data[stage+case], raw, substring=stage == 'substring',
                        grant=0xd2c01808 if case == 'Full' else 0xd2800008)
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for stage in ('codepoint', 'substring'):
        for case, arguments in (('Positive', []), ('Refusal', []), ('Full', []),
                                ('Full', ['check', 'fixture.kotoba'])):
            name = stage + case + ('Args' if arguments else '')
            result, pid, started = signed_run(data[stage+case], output, name, arguments)
            expected = ((42, b'', b'') if case == 'Positive' else
                        (-5, b'', b'') if case == 'Refusal' else
                        (-11, b'', b'') if arguments else
                        (2, b'', USAGE))
            if (result['exit'], bytes.fromhex(result['stdoutHex']),
                    bytes.fromhex(result['stderrHex'])) != expected:
                raise ValueError(f'{name} process result differs')
            if case == 'Full' and arguments:
                at, slot = (0x281f48, 136) if stage == 'codepoint' else (0x2d28, 200)
                missing_slot(name, pid, started, data['fullRaw'], at, slot)
            cases.append(result)
    report = {'schema': 'amu.macos-string-runtime-probe.v1',
              'status': 'PASS_UTF8_SUBSTRING_NEXT_VECTOR_ALLOC',
              'host': [platform.system(), platform.machine(), platform.mac_ver()[0]],
              'sourceSha256': {name: digest for name, (_, digest) in SOURCES.items()},
              'artifactSha256': {name: digest for name, (_, digest) in ARTIFACTS.items()},
              'repeatByteIdentical': True, 'cases': cases,
              'codepointPositiveAndRefusal': True, 'substringPositiveAndRefusal': True,
              'fullNoArgumentUsage': True,
              'nextMissingRuntime': {'slotOffset': 200, 'name': 'vector_alloc',
                                     'rawReturnOffset': 0x2d28},
              'fullCompilerCheckCompleted': False, 'macSelfRebuild': False,
              'linuxFreeBuildClosure': False}
    (output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: check-macos-string-runtime-probe.py ARTIFACT_DIR NEW_OUTPUT_DIR')
    result = observe(Path(sys.argv[1]), Path(sys.argv[2]))
    print(result['status'])
