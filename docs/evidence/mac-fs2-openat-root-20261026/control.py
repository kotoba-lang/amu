#!/usr/bin/env python3
"""One-time Darwin openat ABI control, outside the Amu product build graph."""

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess


SOURCE = Path(__file__).with_name('openat-control.s')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(program, name, path, passed_fds, expected, shown_path=None):
    done = subprocess.run([str(program), path], pass_fds=passed_fds,
                          capture_output=True, timeout=10, check=False)
    row = {'case': name, 'path': shown_path if shown_path is not None else path,
           'exit': done.returncode, 'meaning':
               'read-K' if expected == 42 else errno.errorcode[expected],
           'stdoutHex': done.stdout.hex(), 'stderrHex': done.stderr.hex()}
    if done.returncode != expected or done.stdout or done.stderr:
        raise AssertionError((row, expected))
    return row


def main(output):
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise RuntimeError('Apple Silicon macOS required')
    if errno.errorcode.get(107) != 'ENOTCAPABLE':
        raise RuntimeError('Darwin capability errno mapping changed')
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    program = output / 'openat-control.macho'
    command = ['/usr/bin/clang', '-arch', 'arm64',
               '-mmacosx-version-min=13.0', '-nostdlib', '-Wl,-e,_main',
               '-o', str(program), str(SOURCE), '-lSystem']
    subprocess.run(command, check=True, capture_output=True, timeout=30)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(program)],
                   check=True, capture_output=True, timeout=15)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(program)],
                   check=True, capture_output=True, timeout=15)
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
        raise RuntimeError('control process must pass its root as FD 3')
    try:
        cases = [
            run(program, 'root-file', 'ok.txt', (fd,), 42),
            run(program, 'nested-file', 'sub/ok.txt', (fd,), 42),
            run(program, 'file-symlink', 'file-link', (fd,), errno.ELOOP),
            run(program, 'directory-symlink', 'dir-link/ok.txt', (fd,), errno.ELOOP),
            run(program, 'parent-escape', '../outside.txt', (fd,), 107),
            run(program, 'absolute-path', str(root / 'ok.txt'), (fd,), 107,
                '<granted-root>/ok.txt'),
            run(program, 'absent-file', 'absent.txt', (fd,), errno.ENOENT),
        ]
    finally:
        os.close(fd)
    cases.append(run(program, 'absent-grant', 'ok.txt', (), errno.EBADF))
    wrong = os.open(root / 'ok.txt', os.O_RDONLY)
    if wrong != 3:
        os.close(wrong)
        raise RuntimeError('control process must pass wrong grant as FD 3')
    try:
        cases.append(run(program, 'regular-file-grant', 'ok.txt', (wrong,),
                         errno.ENOTDIR))
    finally:
        os.close(wrong)

    mutations = []
    source_text = SOURCE.read_text()
    for name, original, replacement, path in (
        ('without-resolve-beneath', 'mov x2, #0x1004', 'mov x2, #0x0004',
         '../outside.txt'),
        ('without-no-follow-any', 'movk x2, #0x2100', 'movk x2, #0x0100',
         'file-link'),
    ):
        if source_text.count(original) != 1:
            raise AssertionError(('mutation source drift', name))
        mutant_source = output / (name + '.s')
        mutant_source.write_text(source_text.replace(original, replacement))
        mutant = output / (name + '.macho')
        mutant_command = command.copy()
        mutant_command[mutant_command.index(str(program))] = str(mutant)
        mutant_command[mutant_command.index(str(SOURCE))] = str(mutant_source)
        subprocess.run(mutant_command, check=True, capture_output=True, timeout=30)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(mutant)],
                       check=True, capture_output=True, timeout=15)
        grant = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        if grant != 3:
            os.close(grant)
            raise RuntimeError('mutation descriptor must occupy FD 3')
        try:
            observed = run(mutant, name, path, (grant,), 42)
        finally:
            os.close(grant)
        mutations.append({'name': name, 'sourceSha256': sha(mutant_source),
                          'signedProgramSha256': sha(mutant), 'observed': observed})

    receipt = {
        'schema': 'amu.darwin-openat-root-fd-control.v1',
        'status': 'PASS_ROOT_FD_BENEATH_SYMLINK_REFUSAL',
        'host': {'os': platform.system(), 'arch': platform.machine(),
                 'macOS': platform.mac_ver()[0]},
        'assemblySha256': sha(SOURCE), 'observerSha256': sha(Path(__file__)),
        'signedProgramSha256': sha(program),
        'flags': ['O_RESOLVE_BENEATH', 'O_NOFOLLOW_ANY', 'O_NONBLOCK', 'O_CLOEXEC'],
        'cases': cases, 'mutations': mutations,
        'qualification': 'one-time syscall control; not an Amu-built provider',
        'productProviderImplemented': False,
    }
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output.resolve())
