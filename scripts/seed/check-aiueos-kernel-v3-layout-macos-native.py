#!/usr/bin/env python3
"""Check candidate kernel-v3 ELF/EFI layout using the signed Mac selfhost image.

The v3 single-kernel package is a layout candidate. Slot-v4 remains refused
until the guest maps its 256 KiB user region and implements the typed ABI.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = b'(ns layout-probe (:export [main]))\n(defn main [] :i64 42)\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_mac():
    spec = importlib.util.spec_from_file_location(
        'mac_user_gate', HERE / 'check-aiueos-user-macos-native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def image_layout(raw, address):
    if len(raw) < 176 or raw[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('kernel is not ELF64')
    ph = struct.unpack_from('<Q', raw, 32)[0]
    rx, rw = (struct.unpack_from('<IIQQQQQQ', raw, ph + i * 56)
              for i in range(2))
    if (struct.unpack_from('<Q', raw, 24)[0] != 0x101000
            or rx[:5] != (1, 5, 4096, 0x101000, 0x101000)
            or not 77 < rx[5] == rx[6] <= (2097152 if address >= 0x300000 else 1048576) - 4096
            or rw[:5] != (1, 6, address - 0x100000, address, address)
            or rw[5] != rw[6] or rw[7] != 4096
            or rw[2] + rw[5] > len(raw)):
        raise ValueError('kernel segment boundary changed')
    return {'rx': rx, 'rw': rw}


def main(args):
    mac = load_mac()
    descriptor_path = ROOT / 'seed/bootstrap/aarch64-macos/root.json'
    descriptor = json.loads(descriptor_path.read_text())
    report_path = args.mac_build / 'mac-aiueos-user-target.json'
    report = json.loads(report_path.read_text())
    rows = report.get('generations', [])
    if (report.get('status') != 'PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
            or report.get('source') != descriptor['fullSource']
            or report.get('bootstrapDescriptor') != mac.pin(descriptor_path)
            or len(rows) < 2 or rows[-1]['container'] != rows[-2]['container']
            or rows[-1]['raw'] != rows[-2]['raw']
            or rows[-1]['unsigned'] != rows[-2]['unsigned']):
        raise ValueError('Mac compiler is not bound to the current fixed point')
    compiler = args.mac_build / f"F{rows[-1]['number']}-signed.macho"
    if mac.verify_macho(compiler) != rows[-1]['signed']:
        raise ValueError('Mac fixed point changed')
    old = ROOT / descriptor['compiler']['path']
    if mac.verify_macho(old) != {key: descriptor['compiler'][key]
                                 for key in ('bytes', 'sha256')}:
        raise ValueError('old compiler pin changed')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'fixture').mkdir()
    (out / 'fixture/entry.kotoba').write_bytes(SOURCE)
    lock = (f'KSL1\nentry /fixture/entry.kotoba\nroot /fixture\n'
            f'file {sha(SOURCE)} /fixture/entry.kotoba\n').encode()
    (out / 'fixture.ksl').write_bytes(lock)
    calls = []

    def compile_with(producer, version, name, expected=0):
        dest = name + '.elf'
        command = ['compile', '/fixture/entry.kotoba', '--target',
                   'x86_64-aiueos-kernel-' + version, '--artifact', 'image',
                   '--output', dest, '--fuel', '1000000', '--source-path',
                   '/fixture', '--source-lock', 'fixture.ksl',
                   '--source-lock-sha256', sha(lock)]
        result = mac.native_run(producer, out, *command, expected=expected)
        if b'KEXE_TRAP' in result.stderr or (expected and (out / dest).exists()):
            raise ValueError(name + ' failed open')
        calls.append({'producer': mac.pin(producer), 'target': version,
                      'exit': result.returncode, 'stderr': result.stderr.decode()[:400]})
        return out / dest

    legacy = []
    for version, address in (('v1', 0x200000), ('v2', 0x300000)):
        baseline = compile_with(old, version, 'old-' + version)
        current = compile_with(compiler, version, 'new-' + version)
        if mac.pin(baseline) != mac.pin(current):
            raise ValueError(version + ' changed under the new compiler')
        image_layout(current.read_bytes(), address)
        legacy.append({'target': version, 'elf': mac.pin(current)})
    v3 = compile_with(compiler, 'v3', 'new-v3')
    layout = image_layout(v3.read_bytes(), 0x400000)
    compile_with(old, 'v3', 'old-v3-refused', expected=2)
    mac.native_run(compiler, out, 'package-aiueos-boot', v3.name,
                   '--output', 'kernel-v3.efi')
    slot = args.user_v5_slot.read_bytes()
    if len(slot) != 524288 or struct.unpack_from('<QQ', slot) != (0x0031444c50554941, 4):
        raise ValueError('user-v5 slot input changed')
    (out / 'user-v5.slot').write_bytes(slot)
    (out / 'font.bin').write_bytes(struct.pack('<II', 0x46554941, 1) + bytes(524288 - 8))
    result = mac.native_run(compiler, out, 'package-aiueos-boot', v3.name,
                            '--output', 'mixed-v3-v5.efi', '--font', 'font.bin',
                            '--user-slot', 'user-v5.slot', '--pci-resources', 'v1',
                            expected=1)
    if b'E7111' not in result.stderr or (out / 'mixed-v3-v5.efi').exists():
        raise ValueError('guest-incompatible slot-v4 admitted')
    receipt = {'schema': 'amu.mac-aiueos-kernel-v3-layout-candidate.v1',
               'status': 'PASS_MAC_NATIVE_KERNEL_V3_LAYOUT_CANDIDATE',
               'compiler': mac.pin(compiler), 'oldCompiler': mac.pin(old),
               'source': {'bytes': len(SOURCE), 'sha256': sha(SOURCE)},
               'sourceLock': mac.pin(out / 'fixture.ksl'), 'legacy': legacy,
               'kernelV3': mac.pin(v3), 'efiV3': mac.pin(out / 'kernel-v3.efi'),
               'layout': layout, 'oldCompilerV3Refused': True,
               'dualSlotV4Refused': True, 'guestV5Admission': False,
               'releaseQualified': False, 'linuxJVMNodeCompiler': False,
               'calls': calls}
    (out / 'mac-aiueos-kernel-v3-layout.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'], receipt['kernelV3']['sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mac-build', type=Path, required=True)
    parser.add_argument('--user-v5-slot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
