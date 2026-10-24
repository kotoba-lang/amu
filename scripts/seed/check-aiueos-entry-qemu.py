#!/usr/bin/env python3
"""QEMU/OVMF entry proof for the native-produced value=42 image/EFI pair.

Only the declared scratch directory is writable media. No physical disk,
network, installed OS, service or application state is accessed. This does
not qualify the complete AIUEOS kernel, desktop, input, GPT or physical HW.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path


def pin(path):
    b = path.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def main(efi, kernel, qemu, firmware, output, remaining_fuel=1024, sealed_catalog=False, stack_exhaustion=False, pci_catalog=False):
    assert not (pci_catalog and (sealed_catalog or stack_exhaustion)), "select one versioned fixture"
    assert 0 <= remaining_fuel <= 9007199254740991
    assert efi.read_bytes().count(kernel.read_bytes()) == 1, "EFI/kernel pair identity mismatch"
    expected_pc = 0x10104b
    if stack_exhaustion:
        data = kernel.read_bytes()
        ph = struct.unpack_from('<IIQQQQQQ', data, struct.unpack_from('<Q', data, 32)[0])
        code = data[ph[2]:ph[2]+ph[5]]
        starts = [i for i in range(len(code)) if code.startswith(bytes.fromhex('4989e24981ea'), i)]
        assert starts, 'native stack guard absent'
        at = starts[0]  # The fixed fixture declares deep before main.
        assert code[at+10:at+12] == b'\x0f\x82' and code[at+26:at+28] == b'\x0f\x82'
        target = at+16+struct.unpack_from('<i', code, at+12)[0]
        assert target == at+32+struct.unpack_from('<i', code, at+28)[0]
        assert code[target:target+4] == bytes.fromhex('faf4ebfd')
        expected_pc = ph[3]+target+2
    output.mkdir(parents=True, exist_ok=False)
    esp = output / "esp/EFI/BOOT"
    esp.mkdir(parents=True)
    shutil.copyfile(efi, esp / "BOOTX64.EFI")
    args = [str(qemu), "-machine", "q35,accel=tcg", "-cpu", "max", "-m", "128M", "-smp", "1",
            "-drive", f"if=pflash,format=raw,readonly=on,file={firmware}",
            "-drive", "file=fat:rw:esp,format=raw", "-boot", "order=c", "-nic", "none",
            "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04", "-display", "none",
            "-serial", "file:serial.log", "-debugcon", "file:debug.log", "-no-reboot",
            "-qmp", "unix:qmp.sock,server=on,wait=off",
            "-d", "int", "-D", "exceptions.log"]
    (output / "command.json").write_text(json.dumps(args, indent=2) + "\n")
    old_cwd = Path.cwd()
    os.chdir(output)  # Keep the Unix socket name below macOS's path limit.
    log = open("qemu.log", "wb")
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
    conn, stream, next_id = None, None, 0
    try:
        end = time.monotonic() + 90
        while not Path("qmp.sock").exists():
            assert proc.poll() is None, ("QEMU exited", proc.returncode)
            assert time.monotonic() < end, "QMP startup timeout"
            time.sleep(0.2)
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.settimeout(10)
        conn.connect("qmp.sock")
        stream = conn.makefile("rwb", buffering=0)
        assert "QMP" in json.loads(stream.readline())

        def call(command, arguments=None):
            nonlocal next_id
            next_id += 1
            request = dict(execute=command, id=next_id)
            if arguments is not None:
                request["arguments"] = arguments
            stream.write(json.dumps(request).encode() + b"\n")
            while True:
                row = json.loads(stream.readline())
                if row.get("id") == next_id:
                    assert "error" not in row, row
                    return row["return"]

        def hmp(command):
            return call("human-monitor-command", {"command-line": command})

        call("qmp_capabilities")
        registers = ""
        while time.monotonic() < end:
            assert proc.poll() is None, ("QEMU exited before entry proof", proc.returncode)
            registers = hmp("info registers")
            (output / "registers-last.txt").write_text(registers)
            if re.search(rf"RIP=0*{expected_pc:x}\b", registers, re.I):
                if not stack_exhaustion:
                    assert re.search(r"RAX=0*2a\b", registers, re.I), registers
                break
            if stack_exhaustion and re.search(r"RIP=0*10104b\b", registers, re.I):
                raise AssertionError('guest returned; expected the declared deep-function stack guard')
            time.sleep(1)
        else:
            raise AssertionError("native kernel did not reach its post-return halt")
        call("stop")
        data = kernel.read_bytes()
        context = struct.unpack_from("<Q", data, 64 + 56 + 24)[0]
        assert hmp(f"pmemsave 0x{context:x} 96 context.bin") == ""
        ctx = Path("context.bin").read_bytes()
        fuel, boot = struct.unpack_from("<Q", ctx, 8)[0], struct.unpack_from("<Q", ctx, 80)[0]
        # The original literal-only probe preserves 1024. Call-bearing locked
        # fixtures supply their exact source-charge expectation explicitly.
        assert boot > 0
        if stack_exhaustion:
            assert 0 < fuel < 1000000, fuel  # Bounded budget, not exact fuel parity.
        else:
            assert fuel == remaining_fuel, (fuel, remaining_fuel)
        assert hmp(f"pmemsave 0x{boot:x} 160 boot-info.bin") == ""
        info = Path("boot-info.bin").read_bytes()
        assert struct.unpack_from("<QQ", info) == (0x544f4f4245554941, 6 if pci_catalog else 5)
        map_pointer, map_size, desc_size = struct.unpack_from("<QQQ", info, 16)
        assert map_pointer == boot + 160 and 0 < map_size <= 16384 and desc_size >= 40
        assert map_size % desc_size == 0
        assert hmp(f"pmemsave 0x{map_pointer:x} 16384 firmware-map.bin") == ""
        memory_map = Path("firmware-map.bin").read_bytes()
        assert len(memory_map) == 16384
        memory_types = {}
        for offset in range(0, map_size, desc_size):
            kind = str(struct.unpack_from("<I", memory_map, offset)[0])
            memory_types[kind] = memory_types.get(kind, 0) + 1
        pci = None
        if pci_catalog:
            pointer, size = struct.unpack_from('<QQ', info, 144)
            assert pointer == boot+16544 and 32 <= size <= 8224
            assert hmp(f"pmemsave 0x{pointer:x} {size} pci-catalog.bin") == ""
            raw = Path('pci-catalog.bin').read_bytes()
            magic, version, count, stride = struct.unpack_from('<QQQQ', raw)
            assert (magic, version, stride) == (0x31494350534f4941, 1, 64)
            assert count <= 128 and size == 32+64*count
            devices = call('query-pci')
            (output/'qmp-pci.json').write_text(json.dumps(devices, indent=2)+'\n')
            expected = set()
            def scan(bus):
                for device in bus['devices']:
                    for region in device.get('regions', []):
                        if region['type'] == 'memory' and 0 <= region['bar'] <= 5:
                            assert region['address'] > 0 and region['size'] > 0
                            expected.add((region['address'],region['size'],0,device['bus'],device['slot'],device['function'],region['bar'],device['id']['vendor']+(device['id']['device']<<16)))
                    if 'pci_bridge' in device:
                        scan(device['pci_bridge']['bus'])
            for bus in devices: scan(bus)
            observed = [struct.unpack_from('<8Q', raw, 32+64*i) for i in range(count)]
            assert len(set(observed)) == len(observed), 'duplicate catalog record'
            assert set(observed) == expected and count > 0, (observed, expected)
            pci = dict(records=count,catalog=pin(Path('pci-catalog.bin')),qmp=pin(output/'qmp-pci.json'),
                       exactDeviceAndBARParity=True,osOwnershipQualified=False)
        catalog = None
        if sealed_catalog or stack_exhaustion:
            assert hmp(f"pmemsave 0x{context:x} 16896 private-context.bin") == ""
            private = Path('private-context.bin').read_bytes()
            size, stride, ready = struct.unpack_from('<QQQ', private, 288)
            assert (size, stride, ready) == (map_size, desc_size, 0x4d415031)
            copied = private[512:512+size]
            if stack_exhaustion:
                assert copied == memory_map[:size], 'stack damaged the sealed catalog'
                rsp = int(re.search(r'\bRSP=([0-9a-f]+)', registers, re.I)[1], 16)
                proposed = int(re.search(r'\bR10=([0-9a-f]+)', registers, re.I)[1], 16)
                floor = context+20480
                assert proposed < floor and rsp >= floor-8, (proposed, floor, rsp)
            else:
                scratch = struct.unpack_from('<Q', info, 80)[0]
                assert hmp(f"pmemsave 0x{scratch+14*4096:x} 24 original-record.bin") == ""
                original = struct.unpack('<QQQ', Path('original-record.bin').read_bytes())
                actual = (struct.unpack_from('<I', copied)[0], struct.unpack_from('<Q', copied, 8)[0], struct.unpack_from('<Q', copied, 24)[0])
                public = (struct.unpack_from('<I', memory_map)[0], struct.unpack_from('<Q', memory_map, 8)[0], struct.unpack_from('<Q', memory_map, 24)[0])
                assert actual == original and public == (11, 4096, 16) and actual != public
            catalog = dict(bytes=size, stride=stride, sha256=hashlib.sha256(copied).hexdigest(),
                           publicMutationIsAuthority=False, positivePlatformMMIOQualified=False)
        fb, fbsize = struct.unpack_from("<QQ", info, 112)
        width, height, stride, pixel_format = struct.unpack_from("<IIII", info, 128)
        assert fb > 0 and fbsize > 0 and width > 0 and height > 0 and stride >= width
        (output / "registers.txt").write_text(registers)
        report = dict(status="PASS_NATIVE_STACK_LIMIT_QEMU" if stack_exhaustion else "PASS_AIUEOS_ENTRY_QEMU", observer=pin(Path(__file__).resolve()), efi=pin(efi), kernel=pin(kernel),
                      firmware=pin(firmware), qemuVersion=subprocess.check_output([str(qemu), "--version"]).decode().splitlines()[0],
                      result=None if stack_exhaustion else 42, pc=hex(expected_pc), remainingFuel=fuel,
                      expectedRemainingFuel=None if stack_exhaustion else remaining_fuel, bootInfoVersion=6 if pci_catalog else 5, pciResources=pci,
                      observedPublicMapTypes=memory_types, firmwareMap=pin(Path("firmware-map.bin")), sealedCatalog=catalog,
                      framebuffer=dict(base=fb, bytes=fbsize, width=width, height=height, stride=stride, pixelFormat=pixel_format),
                      completeKernel=False, desktop=False, input=False, gpt=False, physicalHardware=False,
                      compilerProvenance="requires associated native packaging receipt",
                      guestEmulation="QEMU TCG", nativeCDCI=False)
        (output / ("stack-qemu.json" if stack_exhaustion else "entry-qemu.json")).write_text(json.dumps(report, indent=2) + "\n")
        print(report["status"], "bounded stack halt with intact catalog" if stack_exhaustion else "native-produced EFI -> native-produced kernel -> result 42; full OS gate open", flush=True)
    finally:
        if stream:
            stream.close()
        if conn:
            conn.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        log.close()
        Path("qmp.sock").unlink(missing_ok=True)
        os.chdir(old_cwd)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("efi", "kernel", "qemu", "firmware", "output"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--remaining-fuel", type=int, default=1024)
    p.add_argument("--sealed-catalog", action="store_true")
    p.add_argument("--stack-exhaustion", action="store_true")
    p.add_argument("--pci-catalog", action="store_true")
    a = p.parse_args()
    main(*(getattr(a, n).resolve() for n in ("efi", "kernel", "qemu", "firmware", "output")), remaining_fuel=a.remaining_fuel,
         sealed_catalog=a.sealed_catalog, stack_exhaustion=a.stack_exhaustion, pci_catalog=a.pci_catalog)
