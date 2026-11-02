#!/usr/bin/env python3
"""Observe the opt-in v4/v7 application allocation with native Amu and QEMU.

Python stages immutable bytes, launches native artifacts and independently
observes physical memory. It does not compile, allocate a guest region or
decide application authority. The firmware fixture uses QEMU's virtual FAT,
not a qualified installer or a production medium.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import select
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIZE = 8388608
MARKER = 0x314d5041
MAGIC = 0x3154534554505041


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=digest(raw))


class QMP:
    def __init__(self, process):
        self.process, self.number = process, 0
        assert 'QMP' in self.read(15)
        self.call('qmp_capabilities')

    def read(self, timeout=10):
        if not select.select([self.process.stdout], [], [], timeout)[0]:
            raise TimeoutError('QMP observation timed out')
        raw = self.process.stdout.readline()
        if not raw:
            raise RuntimeError('QMP closed: ' + str(self.process.poll()))
        return json.loads(raw)

    def call(self, command, arguments=None):
        self.number += 1
        message = dict(execute=command, id=self.number)
        if arguments is not None:
            message['arguments'] = arguments
        self.process.stdin.write(json.dumps(message).encode() + b'\n')
        self.process.stdin.flush()
        while True:
            row = self.read()
            if row.get('id') == self.number:
                if 'error' in row:
                    raise RuntimeError(str(row))
                return row['return']

    def hmp(self, command):
        return self.call('human-monitor-command', {'command-line': command})

    def dump(self, address, size, directory, name):
        assert self.hmp(f'pmemsave {address:#x} {size} {name}') == ''
        raw = (directory / name).read_bytes()
        assert len(raw) == size
        return raw


def data_offset(efi):
    pe = struct.unpack_from('<I', efi, 60)[0]
    count, optional = struct.unpack_from('<H', efi, pe + 6)[0], struct.unpack_from('<H', efi, pe + 20)[0]
    for i in range(count):
        at = pe + 24 + optional + i * 40
        if efi[at:at+8] == b'.data\0\0\0':
            return struct.unpack_from('<I', efi, at + 20)[0]
    raise ValueError('missing native PE data section')


def boot(args, out, name, efi, expected, rx_end):
    directory = out / name
    (directory / 'esp/EFI/BOOT').mkdir(parents=True)
    (directory / 'esp/EFI/BOOT/BOOTX64.EFI').write_bytes(efi)
    command = [str(args.qemu), '-machine', 'q35,accel=tcg', '-cpu', 'max',
               '-m', '128M', '-smp', '1', '-drive',
               f'if=pflash,format=raw,readonly=on,file={args.firmware}',
               '-drive', 'file=fat:rw:esp,format=raw', '-boot', 'order=c',
               '-nic', 'none', '-display', 'none', '-no-reboot', '-no-shutdown',
               '-serial', 'file:serial.log', '-debugcon', 'file:debug.log', '-qmp', 'stdio']
    (directory / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (directory / 'qemu.stderr').open('wb') as errors:
        process = subprocess.Popen(command, cwd=directory, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=errors, bufsize=0)
        qmp = None
        try:
            qmp = QMP(process)
            until = time.monotonic() + 90
            while time.monotonic() < until:
                if process.poll() is not None:
                    raise RuntimeError(name + ': QEMU exited before observation')
                context = qmp.dump(0x400000, 65536, directory, 'context-last.bin')
                scratch = struct.unpack_from('<Q', context, 272)[0]
                row = qmp.dump(scratch, 4096, directory, 'receipt-last.bin') if scratch else bytes(4096)
                status = qmp.call('query-status')
                if expected == 'refuse' and status['status'] in ('shutdown', 'guest-panicked'):
                    registers = qmp.hmp('info registers')
                    (directory / 'registers.txt').write_text(registers)
                    rip = int(re.search(r'\bRIP=([0-9a-f]+)', registers, re.I)[1], 16)
                    assert 0x101000 <= rip < rx_end, (name, hex(rip))
                    assert struct.unpack_from('<Q', context, 33552)[0] == 0
                    assert struct.unpack_from('<Q', row)[0] != MAGIC
                    return dict(name=name, verdict='REFUSED_BEFORE_MAIN', status=status,
                                rip=rip, efi=dict(bytes=len(efi), sha256=digest(efi)))
                if struct.unpack_from('<Q', row)[0] == MAGIC:
                    assert expected != 'refuse', name + ': changed grant reached main'
                    qmp.call('stop')
                    row = qmp.dump(scratch, 4096, directory, 'receipt.bin')
                    words = struct.unpack_from('<7Q', row)
                    assert words[1:4] == (0, 0, 0), (name, words)
                    assert words[5] == SIZE and words[6] == 0
                    base, size, ready = struct.unpack_from('<3Q', context, 33536)
                    assert base == words[4] and size == SIZE and ready == MARKER
                    assert base >= 0x1000000 and base % 4096 == 0 and base + SIZE <= 2**32
                    assert base + SIZE <= scratch or scratch + 15 * 4096 <= base
                    pool = qmp.dump(base, SIZE, directory, 'pool.bin')
                    expected_bytes = bytes(SIZE) if expected == 'zero' else b''.join(
                        struct.pack('<I', i ^ 0xa55a17c3) for i in range(0, SIZE, 4))
                    assert pool == expected_bytes, name + ': full pool differs'
                    # Independently replay allocation containment from the
                    # actual sealed EFI map, never a manufactured test grant.
                    map_size, stride = struct.unpack_from('<2Q', context, 288)
                    assert 0 < map_size <= 16384 and 40 <= stride <= map_size and map_size % stride == 0
                    descriptors = []
                    for at in range(512, 512 + map_size, stride):
                        kind = struct.unpack_from('<I', context, at)[0]
                        start, _, pages, attrs = struct.unpack_from('<4Q', context, at+8)
                        if kind == 2 and not (attrs >> 63) and start <= base and base + SIZE <= start + pages * 4096:
                            descriptors.append(dict(type=kind, start=start, pages=pages, attributes=attrs))
                    assert len(descriptors) == 1
                    return dict(name=name, verdict='PASS_FULL_POOL', nativeReceipt=list(words),
                                pool=dict(bytes=len(pool), sha256=digest(pool)),
                                allocatedDescriptor=descriptors[0], efi=dict(bytes=len(efi), sha256=digest(efi)))
                if status['status'] in ('shutdown', 'guest-panicked'):
                    raise AssertionError(name + ': positive image faulted before receipt')
                time.sleep(.15)
            raise TimeoutError(name + ': no terminal native observation')
        finally:
            if process.poll() is None:
                if qmp is not None:
                    try:
                        qmp.call('quit')
                    except (RuntimeError, TimeoutError, BrokenPipeError):
                        pass
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)


def main(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    spec = importlib.util.spec_from_file_location('mac_pool', ROOT / 'scripts/seed/check-aiueos-user-macos-native.py')
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    build = args.mac_build.resolve(strict=True)
    receipt = json.loads((build / 'mac-aiueos-user-target.json').read_text())
    assert receipt['status'] == 'PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
    assert receipt['generations'][-1]['container'] == receipt['generations'][-2]['container']
    compiler = build / f"F{receipt['generations'][-1]['number']}-signed.macho"
    assert mac.verify_macho(compiler) == receipt['generations'][-1]['signed']
    assert pin(ROOT / 'seed/FULL-MANIFEST') == receipt['manifest']
    for row in receipt['sources']:
        assert pin(ROOT / row['name']) == {k: row[k] for k in ('bytes', 'sha256')}
    reference_descriptor = json.loads((ROOT / 'seed/bootstrap/aarch64-macos/root.json').read_text())
    reference = ROOT / reference_descriptor['compiler']['path']
    assert mac.verify_macho(reference) == {k: reference_descriptor['compiler'][k] for k in ('bytes', 'sha256')}
    for name in ('qemu', 'firmware'):
        path = getattr(args, name).resolve(strict=True)
        assert pin(path)['sha256'] == getattr(args, name + '_sha256')
        setattr(args, name, path)
    original = ROOT / 'seed/tests/aiueos-application-pool.kotoba'
    source = original.read_bytes()
    calls, boots = [], []
    report = dict(schema='amu.application-pool-native.v1', state='TESTING',
                  compiler=pin(compiler), compilerReceipt=pin(build / 'mac-aiueos-user-target.json'),
                  source=pin(original), observer=pin(Path(__file__)), referenceCompiler=pin(reference),
                  qemu=pin(args.qemu), firmware=pin(args.firmware), calls=calls, boots=boots,
                  production=False, physicalHardware=False, appConnection=False)

    def save():
        (out / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')

    def call(label, directory, *argv, producer=compiler, expected=0):
        result = mac.native_run(producer, directory, *argv, expected=expected)
        (directory / (label + '.stdout')).write_bytes(result.stdout)
        (directory / (label + '.stderr')).write_bytes(result.stderr)
        calls.append(dict(label=label, producer=pin(producer), argv=list(argv), exit=result.returncode,
                          stdout=pin(directory / (label + '.stdout')), stderr=pin(directory / (label + '.stderr'))))
        save()
        return result

    def compile_source(label, raw, target='v4'):
        directory = out / label
        (directory / 'fixture').mkdir(parents=True)
        (directory / 'fixture/probe.kotoba').write_bytes(raw)
        lock = f'KSL1\nentry /fixture/probe.kotoba\nroot /fixture\nfile {digest(raw)} /fixture/probe.kotoba\n'.encode()
        (directory / 'probe.ksl').write_bytes(lock)
        flags = ('compile', '/fixture/probe.kotoba', '--target', 'x86_64-aiueos-kernel-' + target,
                 '--artifact', 'image', '--fuel', '9007199254740991', '--source-path', '/fixture',
                 '--source-lock', 'probe.ksl', '--source-lock-sha256', digest(lock))
        for name in ('kernel.elf', 'kernel-repeat.elf'):
            call(name, directory, *flags, '--output', name)
        assert pin(directory / 'kernel.elf') == pin(directory / 'kernel-repeat.elf')
        for name in ('boot.efi', 'boot-repeat.efi'):
            call(name, directory, 'package-aiueos-boot', 'kernel.elf', '--output', name, '--pci-resources', 'v1')
        assert pin(directory / 'boot.efi') == pin(directory / 'boot-repeat.efi')
        return directory, flags

    save()
    try:
        directory, flags = compile_source('pattern', source)
        kernel, efi = (directory / 'kernel.elf').read_bytes(), (directory / 'boot.efi').read_bytes()
        ph = struct.unpack_from('<Q', kernel, 32)[0]
        rx, rw = [struct.unpack_from('<IIQQQQQQ', kernel, ph+i*56) for i in range(2)]
        assert rx[:5] == (1, 5, 4096, 0x101000, 0x101000) and rx[5] == rx[6] <= 2097152 - 4096
        assert rw[:5] == (1, 6, 3145728, 0x400000, 0x400000) and rw[5] == rw[6] == 131072
        assert struct.unpack_from('<Q', kernel, rw[2]+496)[0] == MARKER
        data = data_offset(efi)
        assert struct.unpack_from('<Q', efi, data+24)[0] == 7
        assert struct.unpack_from('<5Q', efi, data+24784) == (0x314c4f4f5050414b, 1, 2**32-1, SIZE, 1)
        boots.append(boot(args, out, 'boot-pattern', efi, 'pattern', rx[3]+rx[5])); save()
        wipe_source = source.replace(b'        boot (kernel-boot-info)', b'        wiped (fill-all pool 8388608 false)\n        clean (check-all pool 8388608 false)\n        recorded (kernel-store-u64-4k receipt 4096 48 clean)\n        boot (kernel-boot-info)')
        assert wipe_source != source
        wipe_dir, _ = compile_source('wipe', wipe_source)
        boots.append(boot(args, out, 'boot-wipe', (wipe_dir / 'boot.efi').read_bytes(), 'zero', rx[3]+rx[5])); save()
        for name, offset, value in [('grant-magic', 0, 0), ('grant-version', 8, 2),
                                    ('grant-size', 24, SIZE+4096), ('grant-owner', 32, 2),
                                    ('grant-reserved', 56, 1), ('loader-size', 48, 0)]:
            changed = bytearray(efi)
            struct.pack_into('<Q', changed, data+24784+offset, value)
            boots.append(boot(args, out, 'refuse-'+name, bytes(changed), 'refuse', rx[3]+rx[5])); save()
        changed = bytearray(efi)
        struct.pack_into('<Q', changed, data+24, 6)
        boots.append(boot(args, out, 'refuse-old-boot-version', bytes(changed), 'refuse', rx[3]+rx[5])); save()
        # The new image must not silently package without its allocating PCI loader.
        refused = call('no-pci-refused', directory, 'package-aiueos-boot', 'kernel.elf',
                       '--output', 'no-pci.efi', expected=1)
        assert b'E7111' in refused.stderr and not (directory / 'no-pci.efi').exists()
        # Old targets retain their intrinsic trailer, placement and complete
        # package bytes. This is artifact equality, not old-target runtime QA.
        scalar = b'(ns legacy-pool-check (:export [main]))\n(defn main [] :i64 42)\n'
        legacy = []
        for target in ('v1', 'v2', 'v3'):
            previous, legacy_flags = compile_source('legacy-' + target, scalar, target)
            call('reference-kernel', previous, *legacy_flags, '--output', 'reference.elf', producer=reference)
            call('reference-efi', previous, 'package-aiueos-boot', 'reference.elf', '--output',
                 'reference.efi', '--pci-resources', 'v1', producer=reference)
            assert pin(previous / 'reference.elf') == pin(previous / 'kernel.elf')
            assert pin(previous / 'reference.efi') == pin(previous / 'boot.efi')
            legacy.append(dict(target=target, kernel=pin(previous / 'kernel.elf'), efi=pin(previous / 'boot.efi')))
            old_flags = list(flags)
            old_flags[3] = 'x86_64-aiueos-kernel-' + target
            unavailable = call('pool-unavailable-' + target, directory, *old_flags,
                               '--output', 'unavailable-' + target + '.elf', expected=1)
            assert b'E' in unavailable.stderr and not (directory / ('unavailable-' + target + '.elf')).exists()
        report['legacyArtifactEquality'] = legacy
        unavailable = call('old-compiler-v4-refused', directory, *flags,
                           '--output', 'old-compiler-v4.elf', expected=2, producer=reference)
        assert b'E1 usage' in unavailable.stderr and not (directory / 'old-compiler-v4.elf').exists()
        forged = out / 'forged'
        (forged / 'fixture').mkdir(parents=True)
        forged_source = b'(ns forged-pool (:export [main]))\n(defn main [] :i64 (kernel-load-u32-64k 16777216 65536 0))\n'
        (forged / 'fixture/probe.kotoba').write_bytes(forged_source)
        forged_lock = f'KSL1\nentry /fixture/probe.kotoba\nroot /fixture\nfile {digest(forged_source)} /fixture/probe.kotoba\n'.encode()
        (forged / 'probe.ksl').write_bytes(forged_lock)
        forged_flags = list(flags)
        forged_flags[-1] = digest(forged_lock)
        result = call('forged-region-refused', forged, *forged_flags, '--output', 'forged.elf', expected=1)
        assert b'E7106' in result.stderr and not (forged / 'forged.elf').exists()
        report['forgedRegionRefused'] = True
        report['kernel'] = pin(directory / 'kernel.elf')
        report['efi'] = pin(directory / 'boot.efi')
        report['layout'] = dict(rx=rx, rw=rw)
        report['state'] = 'PASS_NATIVE_APPLICATION_POOL'
        save()
        print(report['state'], json.dumps(boots), flush=True)
    except BaseException as error:
        report['state'], report['failure'] = 'FAILED', str(error)
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mac-build', 'qemu', 'firmware', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('qemu-sha256', 'firmware-sha256'):
        parser.add_argument('--' + name, required=True)
    main(parser.parse_args())
