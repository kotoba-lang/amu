#!/usr/bin/env python3
"""Observe #UD at a native fixture's window guard, not an arbitrary failed boot.

Each fixture has one window access: its two UD2 sites are fuel and the
window guard. QEMU's exception trace must name the latter exact instruction.
Only scratch vvfat media is writable; no network or physical media.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time


def pin(path):
    b = path.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def main(efi, kernel, qemu, firmware, output, guard_kind='window'):
    data = kernel.read_bytes()
    assert data[:8] == b'\x7fELF\x02\x01\x01\0'
    assert efi.read_bytes().count(data) == 1
    phoff = struct.unpack_from('<Q', data, 32)[0]
    ph = struct.unpack_from('<IIQQQQQQ', data, phoff)
    assert ph[0:2] == (1, 5) and ph[2] == 4096 and ph[3] == 0x101000
    code = data[ph[2]:ph[2]+ph[5]]
    sites = [i for i in range(len(code)-1) if code[i:i+2] == b'\x0f\x0b']
    if guard_kind == 'pci-seal':
        marker=bytes.fromhex('498b49504885c90f84')
        starts=[i for i in range(len(code)) if code.startswith(marker,i)]
        assert len(starts)==1, 'one trusted bootstrap required'
        at=starts[0];target=at+13+struct.unpack_from('<i',code,at+9)[0]
        assert code[target:target+2]==b'\x0f\x0b'
        expected=ph[3]+target
    elif guard_kind == 'pci-mmio':
        starts = [i for i in range(len(code)) if code.startswith(bytes.fromhex('4981f8ff0000000f87'), i)]
        assert len(starts) == 1, ('one PCI constructor required', starts)
        at = starts[0]
        # Decode the first three identity guards; they share the single
        # constructor refusal site. A bootstrap, memory, fuel or stack
        # failure is not accepted as the PCI-constructor positive.
        targets=[]
        for delta, opcode in [(7,b'\x0f\x87'),(17,b'\x0f\x87'),(27,b'\x0f\x87')]:
            pc=at+delta;assert code[pc:pc+2]==opcode
            targets.append(pc+6+struct.unpack_from('<i',code,pc+2)[0])
        assert len(set(targets))==1 and code[targets[0]:targets[0]+2]==b'\x0f\x0b'
        expected=ph[3]+targets[0]
    elif guard_kind in ('owned-page', 'owned-window'):
        starts = [i for i in range(len(code)) if code.startswith(bytes.fromhex('4883f80f0f83'), i)]
        assert len(starts) == 1, ('one owned-page constructor required', starts)
        at = starts[0]
        assert code[at+10:at+18] == bytes.fromhex('4983b9180100000f')
        targets = []
        branches = [(4, b'\x0f\x83'), (18, b'\x0f\x85'), (34, b'\x0f\x84'), (47, b'\x0f\x82')]
        if guard_kind == 'owned-window':
            assert code[at+40:at+47] == bytes.fromhex('4881f900f00000')
            assert code[at+53:at+60] == bytes.fromhex('48f7c1ff0f0000')
            branches = [(4, b'\x0f\x83'), (18, b'\x0f\x85'), (34, b'\x0f\x84'),
                        (47, b'\x0f\x87'), (60, b'\x0f\x85'), (81, b'\x0f\x87'),
                        (97, b'\x0f\x84'), (110, b'\x0f\x82')]
        for delta, opcode in branches:
            pc = at + delta
            assert code[pc:pc+2] == opcode
            targets.append(pc+6+struct.unpack_from('<i', code, pc+2)[0])
        assert len(set(targets)) == 1 and code[targets[0]:targets[0]+2] == b'\x0f\x0b'
        expected = ph[3] + targets[0]
    else:
        assert len(sites) == 2, ('fixture must have exactly fuel + window guards', sites)
        expected = ph[3] + sites[1]
    output.mkdir(parents=True, exist_ok=False)
    esp = output / 'esp/EFI/BOOT'
    esp.mkdir(parents=True)
    shutil.copyfile(efi, esp / 'BOOTX64.EFI')
    argv = [str(qemu), '-machine', 'q35,accel=tcg', '-cpu', 'max', '-m', '128M', '-smp', '1',
            '-drive', f'if=pflash,format=raw,readonly=on,file={firmware}',
            '-drive', 'file=fat:rw:esp,format=raw', '-boot', 'order=c', '-nic', 'none',
            '-display', 'none', '-serial', 'file:serial.log', '-debugcon', 'file:debug.log',
            '-no-reboot', '-d', 'int', '-D', 'exceptions.log']
    (output / 'command.json').write_text(json.dumps(argv, indent=2)+'\n')
    with (output / 'qemu.log').open('wb') as log:
        process = subprocess.Popen(argv, cwd=output, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            event = None
            while time.monotonic() < deadline:
                trace = output / 'exceptions.log'
                text = trace.read_text(errors='replace') if trace.exists() else ''
                for match in re.finditer(r'v=06[^\n]*?\bIP=[0-9a-fA-F]+:([0-9a-fA-F]+)', text):
                    ip = int(match[1], 16)
                    if ph[3] <= ip < ph[3] + ph[5]:
                        assert ip == expected, ('wrong kernel #UD site', hex(ip), hex(expected))
                        event = match[0]
                        break
                if event:
                    break
                assert process.poll() is None, ('QEMU exited without the guard event', process.returncode)
                time.sleep(0.25)
            assert event, ('no #UD at the native window guard', hex(expected))
            report = dict(status='PASS_NATIVE_KERNEL_GUARD_QEMU', exception=6, instruction='UD2',
                          savedIP=hex(expected), event=event, guardKind=guard_kind, kernel=pin(kernel), efi=pin(efi),
                          firmware=pin(firmware), observer=pin(Path(__file__).resolve()),
                          fullKernel=False, desktop=False, input=False, nativeCDCI=False,
                          guestEmulation='QEMU TCG', compilerProvenance='requires associated native packaging receipt')
            (output / 'guard-qemu.json').write_text(json.dumps(report, indent=2)+'\n')
            print(report['status'], hex(expected), flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('efi', 'kernel', 'qemu', 'firmware', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--guard-kind', choices=('window', 'owned-page', 'owned-window', 'pci-mmio', 'pci-seal'), default='window')
    a = p.parse_args()
    main(*(getattr(a, n).resolve() for n in ('efi','kernel','qemu','firmware','output')), guard_kind=a.guard_kind)
