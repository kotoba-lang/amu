#!/usr/bin/env python3
"""Observe Amu/Kotoba-emitted Darwin root-FD syscall controls on macOS.

The observer signs copies and runs them. It never builds the Kotoba packager,
assembles AArch64, or edits the positive Mach-O bytes.
"""

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'seed/macos-openat-control-packager.kotoba'
ROOT_IMAGE = ROOT / 'seed/bootstrap/aarch64-linux-static-root.elf'
ROOT_SHA = '285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_words():
    text = SOURCE.read_text()
    section = text.split('(defn- openat-words', 1)[1].split('(defn- body-at', 1)[0]
    literal = section.split('(-> [', 1)[1].split(']', 1)[0]
    words = [int(word, 16) for word in re.findall(r'0x[0-9a-f]+', literal)]
    if len(words) != 39:
        raise ValueError('Kotoba strict control word count changed')
    return struct.pack('<39I', *words)


def signed_copy(source, output):
    shutil.copyfile(source, output)
    output.chmod(0o755)
    for arguments in (('--force', '--sign', '-'), ('--verify', '--strict')):
        subprocess.run(['/usr/bin/codesign', *arguments, str(output)],
                       check=True, capture_output=True, timeout=15)
    return digest(output)


def process_case(program, name, path, expected, fd=None, display=None):
    done = subprocess.run([str(program), path],
                          pass_fds=() if fd is None else (fd,),
                          capture_output=True, timeout=10, check=False)
    row = {'case': name, 'path': path if display is None else display,
           'exit': done.returncode,
           'meaning': 'read-K' if expected == 42 else errno.errorcode[expected],
           'stdoutHex': done.stdout.hex(), 'stderrHex': done.stderr.hex()}
    if done.returncode != expected or done.stdout or done.stderr:
        raise ValueError(f'process case differed: {row}; expected {expected}')
    return row


def observe(artifacts, output):
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise RuntimeError('Apple Silicon macOS required')
    if errno.errorcode.get(107) != 'ENOTCAPABLE' or digest(ROOT_IMAGE) != ROOT_SHA:
        raise ValueError('root image or Darwin errno contract changed')
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    packager = artifacts / 'packager.elf'
    repeat = artifacts / 'packager-repeat.elf'
    if packager.read_bytes() != repeat.read_bytes():
        raise ValueError('Amu packager rebuild differs')
    admission = json.loads((artifacts / 'build-repeat-admission.json').read_text())
    if (admission.get('schema'), admission.get('capacity'), admission.get('exit')) != (
            'amu.native-build-admission.v1', 2, 0):
        raise ValueError('native rebuild was not admitted')
    elf = packager.read_bytes()
    if elf[:4] != b'\x7fELF' or struct.unpack_from('<H', elf, 18)[0] != 183:
        raise ValueError('packager is not an AArch64 ELF')

    literal = source_words()
    images = {}
    strict = (artifacts / 'strict.macho').read_bytes()
    for name in ('strict', 'no-beneath', 'no-nofollow'):
        candidate = artifacts / (name + '.macho')
        image = candidate.read_bytes()
        expected = bytearray(literal)
        if name == 'no-beneath':
            struct.pack_into('<I', expected, 16, 0xd2800082)
        elif name == 'no-nofollow':
            struct.pack_into('<I', expected, 20, 0xf2a02002)
        if (len(image) != 16384 or image[:4] != b'\xcf\xfa\xed\xfe'
                or struct.unpack_from('<4I', image, 12) != (2, 6, 296, 0x00200005)
                or struct.unpack_from('<Q', image, 288)[0] != 1024
                or image[1024:1024+len(expected)] != expected
                or any(image[1024+len(expected):])):
            raise ValueError(f'{name}: Mach-O or Kotoba literal mismatch')
        delta = [i for i, (a, b) in enumerate(zip(strict, image)) if a != b]
        if name != 'strict' and delta != list(range(1024+(16 if name == 'no-beneath' else 20),
                                                   1024+(20 if name == 'no-beneath' else 24))):
            # An immediate may keep some bytes equal, so use a range bound
            # below instead of relying on a particular number of changed bits.
            if not delta or any(i not in range(1024+(16 if name == 'no-beneath' else 20),
                                           1024+(20 if name == 'no-beneath' else 24)) for i in delta):
                raise ValueError(f'{name}: unrelated bytes changed')
        linked = subprocess.run(['/usr/bin/otool', '-L', str(candidate)],
                                check=True, capture_output=True, text=True, timeout=10)
        if 'libSystem' in linked.stdout or '.dylib' in linked.stdout:
            raise ValueError(f'{name}: dynamic library load command')
        signed = output / (name + '-signed.macho')
        images[name] = {'unsignedSha256': digest(candidate),
                        'signedSha256': signed_copy(candidate, signed),
                        'loadLibraries': 0, 'signedPath': signed}

    root = output / 'fixture' / 'root'
    root.mkdir(parents=True)
    (root / 'sub').mkdir()
    (root / 'ok.txt').write_bytes(b'K')
    (root / 'sub' / 'ok.txt').write_bytes(b'K')
    (root.parent / 'outside.txt').write_bytes(b'K')
    (root / 'file-link').symlink_to('ok.txt')
    (root / 'dir-link').symlink_to('sub', target_is_directory=True)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    if fd != 3:
        os.close(fd)
        raise RuntimeError('root grant must occupy FD 3')
    strict_program = images['strict']['signedPath']
    try:
        cases = [
            process_case(strict_program, 'root-file', 'ok.txt', 42, fd),
            process_case(strict_program, 'nested-file', 'sub/ok.txt', 42, fd),
            process_case(strict_program, 'file-symlink', 'file-link', errno.ELOOP, fd),
            process_case(strict_program, 'directory-symlink', 'dir-link/ok.txt', errno.ELOOP, fd),
            process_case(strict_program, 'parent-escape', '../outside.txt', 107, fd),
            process_case(strict_program, 'absolute-path', str(root / 'ok.txt'), 107,
                         fd, '<granted-root>/ok.txt'),
            process_case(strict_program, 'absent-file', 'absent.txt', errno.ENOENT, fd),
            process_case(images['no-beneath']['signedPath'], 'without-beneath',
                         '../outside.txt', 42, fd),
            process_case(images['no-nofollow']['signedPath'], 'without-no-follow-any',
                         'file-link', 42, fd),
        ]
    finally:
        os.close(fd)
    cases.append(process_case(strict_program, 'absent-grant', 'ok.txt', errno.EBADF))
    wrong = os.open(root / 'ok.txt', os.O_RDONLY)
    if wrong != 3:
        os.close(wrong)
        raise RuntimeError('wrong grant must occupy FD 3')
    try:
        cases.append(process_case(strict_program, 'regular-file-grant',
                                  'ok.txt', errno.ENOTDIR, wrong))
    finally:
        os.close(wrong)

    receipt = {'schema': 'amu.macos-kotoba-openat-control.v1',
               'status': 'PASS_AMU_EMITTED_ROOT_FD_CONTROL',
               'qualification': 'diagnostic; FS2 wire 35 not implemented',
               'rootImageSha256': ROOT_SHA,
               'sourceSha256': digest(SOURCE),
               'observerSha256': digest(Path(__file__)),
               'packagerSha256': digest(packager),
               'packagerRepeatEqual': True, 'rebuildAdmission': admission,
               'images': {name: {k: v for k, v in image.items() if k != 'signedPath'}
                          for name, image in images.items()},
               'cases': cases, 'noLinuxFreeProducerClaim': True}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    observe(args.artifacts.resolve(), args.output.resolve())
