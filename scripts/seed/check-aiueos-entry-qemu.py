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


def main(efi, kernel, qemu, firmware, output):
    assert efi.read_bytes().count(kernel.read_bytes()) == 1, "EFI/kernel pair identity mismatch"
    output.mkdir(parents=True, exist_ok=False)
    esp = output / "esp/EFI/BOOT"
    esp.mkdir(parents=True)
    shutil.copyfile(efi, esp / "BOOTX64.EFI")
    args = [str(qemu), "-machine", "q35,accel=tcg", "-cpu", "max", "-m", "128M", "-smp", "1",
            "-drive", f"if=pflash,format=raw,readonly=on,file={firmware}",
            "-drive", "file=fat:rw:esp,format=raw", "-boot", "order=c", "-nic", "none",
            "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04", "-display", "none",
            "-serial", "file:serial.log", "-debugcon", "file:debug.log", "-no-reboot",
            "-qmp", "unix:qmp.sock,server=on,wait=off"]
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
            if re.search(r"RIP=0*10104b\b", registers, re.I):
                assert re.search(r"RAX=0*2a\b", registers, re.I), registers
                break
            time.sleep(1)
        else:
            raise AssertionError("native kernel did not reach its post-return halt")
        call("stop")
        data = kernel.read_bytes()
        context = struct.unpack_from("<Q", data, 64 + 56 + 24)[0]
        assert hmp(f"pmemsave 0x{context:x} 96 context.bin") == ""
        ctx = Path("context.bin").read_bytes()
        fuel, boot = struct.unpack_from("<Q", ctx, 8)[0], struct.unpack_from("<Q", ctx, 80)[0]
        # Literal-only main has no source charge site (same as the existing
        # public native product test); preserving fuel is the exact contract.
        assert fuel == 1024 and boot > 0, (fuel, boot)
        assert hmp(f"pmemsave 0x{boot:x} 160 boot-info.bin") == ""
        info = Path("boot-info.bin").read_bytes()
        assert struct.unpack_from("<QQ", info) == (0x544f4f4245554941, 5)
        map_pointer, map_size, desc_size = struct.unpack_from("<QQQ", info, 16)
        assert map_pointer == boot + 160 and 0 < map_size <= 16384 and desc_size >= 40
        fb, fbsize = struct.unpack_from("<QQ", info, 112)
        width, height, stride, pixel_format = struct.unpack_from("<IIII", info, 128)
        assert fb > 0 and fbsize > 0 and width > 0 and height > 0 and stride >= width
        (output / "registers.txt").write_text(registers)
        report = dict(status="PASS_AIUEOS_ENTRY_QEMU", observer=pin(Path(__file__).resolve()), efi=pin(efi), kernel=pin(kernel),
                      firmware=pin(firmware), qemuVersion=subprocess.check_output([str(qemu), "--version"]).decode().splitlines()[0],
                      result=42, pc="0x10104b", remainingFuel=fuel, bootInfoVersion=5,
                      framebuffer=dict(base=fb, bytes=fbsize, width=width, height=height, stride=stride, pixelFormat=pixel_format),
                      completeKernel=False, desktop=False, input=False, gpt=False, physicalHardware=False,
                      compilerProvenance="requires associated native packaging receipt",
                      guestEmulation="QEMU TCG", nativeCDCI=False)
        (output / "entry-qemu.json").write_text(json.dumps(report, indent=2) + "\n")
        print(report["status"], "native-produced EFI -> native-produced kernel -> result 42; full OS gate open", flush=True)
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
    a = p.parse_args()
    main(*(getattr(a, n).resolve() for n in ("efi", "kernel", "qemu", "firmware", "output")))
