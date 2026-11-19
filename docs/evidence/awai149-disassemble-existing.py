"""Read-only disassembly of two previously produced diagnostic artifacts.

This does not generate or inspect an image from the new candidate source.
Usage: python3 awai149-disassemble-existing.py ADI2_HELPER FSTATAT_CONTROL
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path


def disassemble(path, expected_hash, commands):
    artifact = Path(path)
    if artifact.stat().st_size > 1048576:
        raise SystemExit('artifact exceeds diagnostic size limit')
    data = artifact.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise SystemExit('artifact hash mismatch')
    args = ['/Library/Developer/CommandLineTools/usr/bin/lldb', '--batch',
            '-o', f'target create {path}']
    for start, count in commands:
        args += ['-o', f'disassemble --start-address {start} --count {count}']
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=20)
    return result.stdout


def main():
    if len(sys.argv) != 3 or any(not re.fullmatch(r'/[A-Za-z0-9_./-]+', p) for p in sys.argv[1:]):
        raise SystemExit('provide two simple absolute artifact paths')
    old = disassemble(sys.argv[1], '8f8e63db8e32c532f650bb9504ae4dad29c1e7bff79baf6824339dd1b51746aa',
                      [('0x100000400', 50), ('0x100000550', 34)])
    patterns = [r'and\s+w9,\s*w8,\s*#0xf000', r'lsr\s+x11,\s*x10,\s*#4',
                r'and\s+x11,\s*x10,\s*x12', r'csel\s+x11,\s*x12,\s*x11,\s*hi',
                r'mov\s+x24,\s*x20', r'mov\s+x1,\s*x24', r'mov\s+x2,\s*x25']
    if not all(re.search(p, old) for p in patterns):
        raise SystemExit('existing helper disassembly differed')
    strict = disassemble(sys.argv[2], '9dc4fa60e85dcc4d362674187c7bd1d7d3ea74def3d0511dd6f0fa0e4f759190',
                         [('0x100000400', 14)])
    if not all(re.search(p, strict) for p in (r'mov\s+x3,\s*#0x2820',
                                               r'mov\s+x16,\s*#0x1d6',
                                               r'movk\s+x16,\s*#0x2000,\s*lsl\s*#16')):
        raise SystemExit('existing fstatat control disassembly differed')
    print('existing signed artifact literals and fstatat control disassembled as expected')
    print('candidate helper image, branch fixups and runtime behavior not checked')


if __name__ == '__main__':
    main()
