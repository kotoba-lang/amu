#!/usr/bin/env python3
"""Check kernel-v3 layout, guest mapping and slot-v4 package admission on Mac.

The signed native artifact gate does not execute a guest or qualify a typed ABI.
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
WINDOW_SOURCE = b'''(ns request-window-probe
  (:export [main aiueos-value-runtime-entry aiueos-value-runtime-syscall-plan
            aiueos-value-runtime-publish-domain aiueos-value-runtime-provider-status
            aiueos-value-runtime-capability-grant aiueos-value-runtime-provider-claim
            aiueos-value-runtime-provider-complete aiueos-value-runtime-cas-verify]))
(defn aiueos-value-runtime-entry [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)
(defn aiueos-value-runtime-syscall-plan [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)
(defn aiueos-value-runtime-publish-domain [a :i64] :i64 0)
(defn aiueos-value-runtime-provider-status [a :i64 b :i64] :i64 0)
(defn aiueos-value-runtime-capability-grant [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)
(defn aiueos-value-runtime-provider-claim [] :i64 0)
(defn aiueos-value-runtime-provider-complete [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)
(defn aiueos-value-runtime-cas-verify [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)
(defn main [] :i64
  (let [request (kernel-value-domain-request-page 73)
        final-page (kernel-subregion request 262144 196608 65536)]
    (if (= request 0) 0
      (kernel-load-u8-64k final-page 65536 65535))))
'''


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
    # Compiler-only control: the linked exports below are inert fixtures, not
    # a guest ValueRuntime. The final byte of v5's 64-page RW window must be
    # statically rooted; the same source must fail under the v2 extent.
    (out / 'fixture/window.kotoba').write_bytes(WINDOW_SOURCE)
    window_lock = (f'KSL1\nentry /fixture/window.kotoba\nroot /fixture\n'
                   f'file {sha(WINDOW_SOURCE)} /fixture/window.kotoba\n').encode()
    (out / 'window.ksl').write_bytes(window_lock)
    window_args = ['--artifact', 'image', '--fuel', '1000000', '--source-path', '/fixture',
                   '--source-lock', 'window.ksl',
                   '--source-lock-sha256', sha(window_lock)]
    mac.native_run(compiler, out, 'compile', '/fixture/window.kotoba', '--target',
                   'x86_64-aiueos-kernel-v3', *window_args, '--output', 'window-v3.elf')
    window_v3 = out / 'window-v3.elf'
    image_layout(window_v3.read_bytes(), 0x400000)
    refused_window = mac.native_run(compiler, out, 'compile', '/fixture/window.kotoba',
                                    '--target', 'x86_64-aiueos-kernel-v2', *window_args,
                                    '--output', 'window-v2.elf', expected=1)
    if b'E7106' not in refused_window.stderr or (out / 'window-v2.elf').exists():
        raise ValueError('v2 admitted the 256 KiB request extent')
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
    fixture = importlib.util.spec_from_file_location(
        'value_fixture', HERE / 'check_aiueos_value_fixture.py')
    value = importlib.util.module_from_spec(fixture)
    fixture.loader.exec_module(value)
    guest_source = value.user_source().encode()
    (out / 'fixture/guest.kotoba').write_bytes(guest_source)
    guest_lock = (f'KSL1\nentry /fixture/guest.kotoba\nroot /fixture\n'
                  f'file {sha(guest_source)} /fixture/guest.kotoba\n').encode()
    (out / 'guest.ksl').write_bytes(guest_lock)
    mac.native_run(compiler, out, 'compile', '/fixture/guest.kotoba', '--target',
                   'x86_64-aiueos-kernel-v3', '--artifact', 'image', '--output',
                   'guest-v3.elf', '--fuel', '1000000', '--source-path', '/fixture',
                   '--source-lock', 'guest.ksl', '--source-lock-sha256', sha(guest_lock))
    guest = out / 'guest-v3.elf'
    guest_raw = guest.read_bytes()
    guest_layout = image_layout(guest_raw, 0x400000)
    guest_rw = guest_layout['rw']
    marker = struct.unpack_from('<Q', guest_raw, guest_rw[2] + 464)[0]
    handler = struct.unpack_from('<Q', guest_raw, guest_rw[2] + 30400)[0]
    if (guest_rw[5] != 0x240000 or marker != 0x354c5652
            or not guest_layout['rx'][3] <= handler <
            guest_layout['rx'][3] + guest_layout['rx'][5]):
        raise ValueError('guest-v3 mapping or syscall handler missing')
    mac.native_run(compiler, out, 'package-aiueos-boot', guest.name,
                   '--output', 'guest-v3-v5.efi', '--font', 'font.bin',
                   '--user-slot', 'user-v5.slot', '--pci-resources', 'v1')
    efi = (out / 'guest-v3-v5.efi').read_bytes()
    if efi.count(guest_raw) != 1 or efi.count(slot) != 1:
        raise ValueError('guest-v3 EFI lacks pinned kernel or slot')
    for name, offset in (('marker', 464), ('handler', 30400)):
        changed = bytearray(guest_raw)
        struct.pack_into('<Q', changed, guest_rw[2] + offset, 0)
        (out / (name + '.elf')).write_bytes(changed)
        result = mac.native_run(compiler, out, 'package-aiueos-boot', name + '.elf',
                                '--output', name + '.efi', '--font', 'font.bin',
                                '--user-slot', 'user-v5.slot', '--pci-resources', 'v1',
                                expected=1)
        if b'E7111' not in result.stderr or (out / (name + '.efi')).exists():
            raise ValueError('changed guest-v3 ' + name + ' admitted')
    receipt = {'schema': 'amu.mac-aiueos-kernel-v3-layout-candidate.v2',
               'status': 'PASS_MAC_NATIVE_KERNEL_V3_GUEST_ARTIFACT',
               'compiler': mac.pin(compiler), 'oldCompiler': mac.pin(old),
               'source': {'bytes': len(SOURCE), 'sha256': sha(SOURCE)},
               'sourceLock': mac.pin(out / 'fixture.ksl'), 'legacy': legacy,
               'kernelV3': mac.pin(v3), 'efiV3': mac.pin(out / 'kernel-v3.efi'),
               'windowSource': {'bytes': len(WINDOW_SOURCE), 'sha256': sha(WINDOW_SOURCE)},
               'windowSourceLock': mac.pin(out / 'window.ksl'),
               'windowKernelV3': mac.pin(window_v3), 'windowV2ExtentRefused': True,
               'windowGuestExecution': False,
               'layout': layout, 'oldCompilerV3Refused': True,
               'dualSlotV4RefusedForScalar': True,
               'guestV5Admission': True, 'guestExecution': False,
               'guestSource': {'bytes': len(guest_source), 'sha256': sha(guest_source)},
               'guestSourceLock': mac.pin(out / 'guest.ksl'),
               'guestKernel': mac.pin(guest), 'guestEfi': mac.pin(out / 'guest-v3-v5.efi'),
               'guestLayout': guest_layout, 'guestMarker': marker, 'guestHandler': handler,
               'changedMarkerRefused': True, 'changedHandlerRefused': True,
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
