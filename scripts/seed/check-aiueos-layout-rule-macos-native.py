#!/usr/bin/env python3
"""Check the boot packager's layout admission rule on Mac (ADR-0276 part A, JUN-479 b).

A real kernel-v3 guest image is compiled, then its ELF program headers are changed one clause at
a time. The unchanged image and a kernel above the old text ceiling that still fits the budget
are admitted; every other image is refused with E7111. This checks the packager only; it
executes no guest.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_TEXT_CAP = 2 * 1024 * 1024 - 4096    # slot-v4 text ceiling before the rule
NEW_TEXT_CAP = 3 * 1024 * 1024 - 4096    # RW file offset minus the ELF header page


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(args):
    mac = load('mac_user_gate', 'check-aiueos-user-macos-native.py')
    value = load('value_fixture', 'check_aiueos_value_fixture.py')
    descriptor_path = ROOT / 'seed/bootstrap/aarch64-macos/root.json'
    descriptor = json.loads(descriptor_path.read_text())
    report = json.loads((args.mac_build / 'mac-aiueos-user-target.json').read_text())
    rows = report.get('generations', [])
    if (report.get('status') != 'PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
            or report.get('source') != descriptor['fullSource']
            or len(rows) < 2 or rows[-1]['raw'] != rows[-2]['raw']):
        raise ValueError('Mac compiler is not bound to the current fixed point')
    compiler = args.mac_build / f"F{rows[-1]['number']}-signed.macho"
    if mac.verify_macho(compiler) != rows[-1]['signed']:
        raise ValueError('Mac fixed point changed')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'fixture').mkdir()
    source = value.user_source().encode()
    (out / 'fixture/guest.kotoba').write_bytes(source)
    lock = (f'KSL1\nentry /fixture/guest.kotoba\nroot /fixture\n'
            f'file {sha(source)} /fixture/guest.kotoba\n').encode()
    (out / 'guest.ksl').write_bytes(lock)
    mac.native_run(compiler, out, 'compile', '/fixture/guest.kotoba', '--target',
                   'x86_64-aiueos-kernel-v3', '--artifact', 'image', '--output',
                   'guest-v3.elf', '--fuel', '1000000', '--source-path', '/fixture',
                   '--source-lock', 'guest.ksl', '--source-lock-sha256', sha(lock))
    base = (out / 'guest-v3.elf').read_bytes()
    slot = args.user_v5_slot.read_bytes()
    (out / 'user-v5.slot').write_bytes(slot)
    (out / 'font.bin').write_bytes(struct.pack('<II', 0x46554941, 1) + bytes(524288 - 8))
    ph = struct.unpack_from('<Q', base, 32)[0]
    rx_at, rw_at = ph, ph + 56
    rx_size = struct.unpack_from('<Q', base, rx_at + 32)[0]
    if not 77 < rx_size <= OLD_TEXT_CAP:
        raise ValueError('the guest kernel is not below the old text ceiling')
    calls = []

    def attempt(name, raw, admitted):
        (out / (name + '.elf')).write_bytes(raw)
        result = mac.native_run(compiler, out, 'package-aiueos-boot', name + '.elf',
                                '--output', name + '.efi', '--font', 'font.bin',
                                '--user-slot', 'user-v5.slot', '--pci-resources', 'v1',
                                expected=0 if admitted else 1)
        exists = (out / (name + '.efi')).exists()
        if admitted != exists or (not admitted and b'E7111' not in result.stderr):
            raise ValueError(name + (' was refused' if admitted else ' was admitted'))
        calls.append({'name': name, 'admitted': admitted})

    def edits(name, *changes):
        raw = bytearray(base)
        for offset, fmt, value_ in changes:
            struct.pack_into(fmt, raw, offset, value_)
        return name, bytes(raw)

    rx_off, rw_off = (struct.unpack_from('<Q', base, at + 8)[0] for at in (rx_at, rw_at))
    rw_vaddr = struct.unpack_from('<Q', base, rw_at + 16)[0]
    rw_memsz = struct.unpack_from('<Q', base, rw_at + 40)[0]
    attempt('unchanged', base, True)
    # Positive control: text above the old 2 MiB ceiling, inside the budget (the RW offset is 3 MiB).
    wide = OLD_TEXT_CAP + 8192
    attempt(*edits('text-above-old-ceiling', (rx_at + 32, '<Q', wide), (rx_at + 40, '<Q', wide)), True)
    # Negative controls, one clause each.
    attempt(*edits('text-past-rw-offset', (rx_at + 32, '<Q', NEW_TEXT_CAP + 16), (rx_at + 40, '<Q', NEW_TEXT_CAP + 16)), False)
    attempt(*edits('overlap-by-file-offset', (rw_at + 8, '<Q', rx_off + rx_size - 4096)), False)
    attempt(*edits('overlap-by-address', (rx_at + 32, '<Q', rw_vaddr - 0x101000 + 4096),
                   (rx_at + 40, '<Q', rw_vaddr - 0x101000 + 4096)), False)
    attempt(*edits('rw-and-x', (rw_at + 4, '<I', 7)), False)
    attempt(*edits('rx-and-w', (rx_at + 4, '<I', 7)), False)
    attempt(*edits('misaligned-rw', (rw_at + 16, '<Q', rw_vaddr + 16), (rw_at + 24, '<Q', rw_vaddr + 16)), False)
    attempt(*edits('past-budget', (rw_at + 16, '<Q', 0x1000000), (rw_at + 24, '<Q', 0x1000000)), False)
    attempt(*edits('entry-in-rw', (24, '<Q', rw_vaddr)), False)
    attempt(*edits('fixed-region-inside-segment', (rw_at + 40, '<Q', rw_memsz - 4096)), False)
    receipt = {'schema': 'amu.mac-aiueos-layout-rule.v1',
               'status': 'PASS_MAC_NATIVE_LAYOUT_RULE',
               'compiler': mac.pin(compiler), 'baseKernel': {'bytes': len(base), 'sha256': sha(base)},
               'oldTextCap': OLD_TEXT_CAP, 'newTextCap': NEW_TEXT_CAP,
               'calls': calls, 'guestExecution': False, 'releaseQualified': False}
    (out / 'mac-aiueos-layout-rule.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'], receipt['baseKernel']['sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mac-build', type=Path, required=True)
    parser.add_argument('--user-v5-slot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
