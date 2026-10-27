#!/usr/bin/env python3
"""Read the full Mac compiler's first live FS2 request at the missing callback.

Diagnostic only: LLDB stops at the existing refusal instruction. This tool
neither answers the request nor qualifies an FS2 provider or selfhost image.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


PAIR_LENGTH = ('expression -- (unsigned long long)*(unsigned long long*)'
               '((unsigned long long)*(unsigned long long*)($x0+296)'
               '+($x4-1)*16+8)')
POOL_REQUEST = ('*(unsigned long long*)($x0+0x190)'
                '+~*(unsigned long long*)(*(unsigned long long*)'
                '($x0+0x128)+($x4-1)*16)')
CASES = ('seed/macos-utf8-main.kotoba', 'nonexistent.kotoba')


def observe(image, source):
    expected = b'\0FS2\0D' + source.encode('utf-8') + b'\0'
    command = ['/usr/bin/lldb', '--batch', '-o', 'run',
               '-k', 'register read x0 x1 x2 x3 x4 pc',
               '-k', PAIR_LENGTH,
               '-k', ('memory read --format x --size 1 --count '
                      f'{len(expected)} -- "{POOL_REQUEST}"'),
               '--', str(image), 'check', source]
    done = subprocess.run(command, capture_output=True, text=True,
                          timeout=30, check=False)
    log = done.stdout + done.stderr
    if done.returncode != 0 or 'stop reason = EXC_BREAKPOINT' not in log:
        raise ValueError(f'LLDB did not stop at the missing callback: {log[-1800:]}')
    regs = {key: int(value, 16) for key, value in
            re.findall(r'^\s+(x[0-4]|pc) = (0x[0-9a-f]+)', log, re.MULTILINE)}
    if (regs.get('x1'), regs.get('x2'), regs.get('x3')) != (35, 1, 1):
        raise ValueError(f'wire or kind changed: {regs}')
    if regs['pc'] & 0xfff != 0x6e4:
        raise ValueError(f'expected missing-provider trap changed: {regs}')
    length_match = re.search(r'\(unsigned long long\) \$0 = (\d+)', log)
    if not length_match or int(length_match.group(1)) != len(expected):
        raise ValueError(f'request descriptor length changed: {log[-1800:]}')
    memory = log.split('(lldb) memory read --format x --size 1 --count ', 1)
    if len(memory) != 2:
        raise ValueError('LLDB did not return request memory')
    values = []
    for line in memory[1].splitlines()[1:]:
        if not re.match(r'^0x[0-9a-f]+:', line):
            break
        values.extend(int(value, 16) for value in
                      re.findall(r'\b0x[0-9a-f]{2}\b', line))
    actual = bytes(values)
    if actual != expected:
        raise ValueError(f'FS2 first request changed: {actual.hex()} != {expected.hex()}')
    return {'source': source, 'wire': regs['x1'], 'requestKind': regs['x2'],
            'resultKind': regs['x3'], 'requestBytesHex': actual.hex(),
            'requestLength': len(actual), 'stopPcPageOffset': regs['pc'] & 0xfff}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    image = args.image.resolve()
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    if digest != args.expected_sha256:
        parser.error('image digest differs from the pinned candidate')
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(image)],
                   check=True, capture_output=True, timeout=15)
    cases = [observe(image, source) for source in CASES]
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 'amu.macos-first-fs2-request.v1',
               'status': 'PASS_FIRST_FS2_D_REQUEST',
               'imageSha256': digest, 'qualification': 'diagnostic; no provider',
               'cases': cases}
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
