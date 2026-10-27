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
import select
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path


def pin(path):
    b = path.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


class QmpStdio:
    """Private QMP pipe for the LLM guest gate; no local socket listener."""

    def __init__(self, process, reply_timeout=30):
        self.reader = process.stdout
        self.writer = process.stdin
        self.reply_timeout = reply_timeout
        self.pending = b""

    def readline(self):
        deadline = time.monotonic() + self.reply_timeout
        while b"\n" not in self.pending:
            remaining = deadline - time.monotonic()
            assert remaining > 0, 'QMP stdio reply timeout'
            ready, _, _ = select.select([self.reader], [], [], remaining)
            assert ready, 'QMP stdio reply timeout'
            chunk = os.read(self.reader.fileno(), 4096)
            assert chunk, 'QMP stdio closed'
            self.pending += chunk
        line, _, self.pending = self.pending.partition(b"\n")
        return line + b"\n"

    def write(self, data):
        self.writer.write(data)
        self.writer.flush()

    def close(self):
        self.writer.close()
        self.reader.close()


def main(efi, kernel, qemu, firmware, output, remaining_fuel=1024, sealed_catalog=False, stack_exhaustion=False, pci_catalog=False, pci_private=False, pci_private_forgery=False, dma_snapshot=False, value_context=False, value_call=False, llm_header=False, llm_result=False, llm_keyword_text=False, llm_ticket=False):
    llm_header = llm_header or llm_result or llm_ticket
    assert not llm_keyword_text or llm_result, 'keyword text requires a result receipt'
    assert not llm_ticket or llm_result, 'ticket receipt requires the request/result probe'
    assert sum([dma_snapshot,value_context,value_call,llm_header]) <= 1, 'select one functional receipt'
    pci_private = pci_private or pci_private_forgery or dma_snapshot or value_context or value_call or llm_header
    pci_catalog = pci_catalog or pci_private
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
            "-qmp", "stdio" if llm_header else "unix:qmp.sock,server=on,wait=off",
            "-d", "int", "-D", "exceptions.log"]
    (output / "command.json").write_text(json.dumps(args, indent=2) + "\n")
    old_cwd = Path.cwd()
    os.chdir(output)  # Keep the Unix socket name below macOS's path limit.
    log = open("qemu.log", "wb")
    proc = (subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=log, bufsize=0) if llm_header else
            subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT))
    conn, stream, next_id = None, None, 0
    try:
        end = time.monotonic() + 90
        if llm_header:
            assert proc.poll() is None, ("QEMU exited", proc.returncode)
            stream = QmpStdio(proc)
        else:
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
        if stack_exhaustion or dma_snapshot or value_context or value_call or llm_header:
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
            if pci_private_forgery:
                scratch=struct.unpack_from('<Q', info, 80)[0]
                assert (pointer,size)==(scratch+14*4096,96)
                assert hmp(f"pmemsave 0x{pointer:x} {size} forged-catalog.bin")==""
                fake=Path('forged-catalog.bin').read_bytes()
                assert struct.unpack_from('<QQQQ',fake)==(0x31494350534f4941,1,1,64)
                assert struct.unpack_from('<8Q',fake,32)==(1048576,4096,0,0,1,0,0,286331444)
                pointer=boot+16544
                assert hmp(f"pmemsave 0x{context+312:x} 8 pci-private-size.bin")==""
                size=struct.unpack('<Q',Path('pci-private-size.bin').read_bytes())[0]
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
            private_pci = None
            if pci_private:
                assert hmp(f"pmemsave 0x{context:x} 28672 private-pci.bin") == ""
                private = Path('private-pci.bin').read_bytes()
                assert struct.unpack_from('<QQ', private, 312) == (size, 0x31494350)
                assert struct.unpack_from('<QQ', private, 336) == (0x31494350, context+65536)
                assert private[20480:20480+size] == raw
                private_pci = dict(privateBytesMatch=True,stackFloor=context+65536,
                                   context=pin(Path('private-pci.bin')))
            pci = dict(publicMetadataForged=pci_private_forgery,privateSnapshot=private_pci,records=count,catalog=pin(Path('pci-catalog.bin')),qmp=pin(output/'qmp-pci.json'),
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
        dma = None
        if dma_snapshot:
            # Functional memory gate; exact source-fuel parity is deliberately
            # separate. Locate pages through sealed context, never public info.
            scratch, pages = struct.unpack_from('<QQ', private, 272)
            assert scratch > 0 and pages == 15
            assert hmp(f"pmemsave 0x{scratch:x} 80 dma-receipt.bin") == ""
            assert hmp(f"pmemsave 0x{scratch+14*4096:x} 4096 dma-snapshot.bin") == ""
            checks = struct.unpack('<10Q', Path('dma-receipt.bin').read_bytes())
            snapshot = Path('dma-snapshot.bin').read_bytes()
            assert checks == (1,)*10, checks
            assert snapshot == bytes([68])*64+bytes(4096-64)
            dma = dict(checks=list(checks),receipt=pin(Path('dma-receipt.bin')),
                       snapshot=pin(Path('dma-snapshot.bin')),four2048ByteBuffers=True,
                       invalidIndexSizeAndAliasPreserveSnapshot=True,exactFuelParity=False)
        llm = None
        llm_result_receipt = None
        llm_ticket_receipt = None
        if llm_header:
            scratch, pages = struct.unpack_from('<QQ', private, 272)
            assert scratch > 0 and pages == 15
            assert hmp(f"pmemsave 0x{scratch+4096:x} 168 llm-header-receipt.bin") == ""
            assert hmp(f"pmemsave 0x{scratch:x} 64 llm-header.bin") == ""
            model_bytes = 6 if llm_keyword_text else 5
            assert hmp(f"pmemsave 0x{scratch+8192:x} {model_bytes} llm-request-model.bin") == ""
            assert hmp(f"pmemsave 0x{scratch+12288:x} {model_bytes} llm-selected-model.bin") == ""
            assert hmp(f"pmemsave 0x{scratch+24576:x} 5 llm-request-prompt.bin") == ""
            checks = struct.unpack('<21Q', Path('llm-header-receipt.bin').read_bytes())
            header = Path('llm-header.bin').read_bytes()
            assert checks[:12] == (1,)*12, checks
            assert checks[12:] == (1,)*9, checks
            assert struct.unpack_from('<10I', header) == (
                827149387, 1, 11, model_bytes, 0, 5, 16, 0,
                model_bytes + 5, 64)
            assert header[40:] == bytes(24), 'header mutation was not restored'
            expected_model = b':local' if llm_keyword_text else b'local'
            assert Path('llm-request-model.bin').read_bytes() == expected_model
            assert Path('llm-selected-model.bin').read_bytes() == expected_model
            assert Path('llm-request-prompt.bin').read_bytes() == b'hello'
            llm = dict(checks=list(checks[:12]), receipt=pin(Path('llm-header-receipt.bin')),
                       header=pin(Path('llm-header.bin')), wire=11,
                       providerDispatch=False, modelExecution=False,
                       exactFuelParity=False)
            llm_request = dict(checks=list(checks[12:]),
                               model=pin(Path('llm-request-model.bin')),
                               selectedModelFixture=pin(Path('llm-selected-model.bin')),
                               prompt=pin(Path('llm-request-prompt.bin')),
                               aliasingQualified=False, utf8ComponentValidated=True,
                               hostPolicyQualified=False, providerDispatch=False)
            if llm_result:
                assert hmp(f"pmemsave 0x{scratch+12*4096:x} 48 llm-result-receipt.bin") == ""
                assert hmp(f"pmemsave 0x{scratch+7*4096:x} 64 llm-result-header.bin") == ""
                assert hmp(f"pmemsave 0x{scratch+8*4096:x} 2 llm-result-text.bin") == ""
                finish_bytes = 5 if llm_keyword_text else 4
                assert hmp(f"pmemsave 0x{scratch+9*4096:x} {finish_bytes} llm-result-finish.bin") == ""
                result_checks = struct.unpack('<6Q', Path('llm-result-receipt.bin').read_bytes())
                result_header = Path('llm-result-header.bin').read_bytes()
                assert result_checks == (1,)*6, result_checks
                assert struct.unpack_from('<8I', result_header) == (
                    827477067, 1, 11, 1, 2, finish_bytes, 0, 0)
                assert struct.unpack_from('<2Q', result_header, 32) == (7, 1)
                assert struct.unpack_from('<4I', result_header, 48) == (0, 2 + finish_bytes, 0, 0)
                assert Path('llm-result-text.bin').read_bytes() == b'ok'
                expected_finish = b':stop' if llm_keyword_text else b'stop'
                assert Path('llm-result-finish.bin').read_bytes() == expected_finish
                llm_result_receipt = dict(
                    checks=list(result_checks), receipt=pin(Path('llm-result-receipt.bin')),
                    header=pin(Path('llm-result-header.bin')),
                    text=pin(Path('llm-result-text.bin')),
                    finishReason=pin(Path('llm-result-finish.bin')),
                    resultCodecComponent=True, providerDispatch=False,
                    userValueLowering=False)
                if llm_ticket:
                    assert hmp(f"pmemsave 0x{scratch+13*4096:x} 72 llm-ticket-state.bin") == ""
                    assert hmp(f"pmemsave 0x{scratch+13*4096+256:x} 96 llm-ticket-receipt.bin") == ""
                    assert hmp(f"pmemsave 0x{scratch+14*4096:x} 32 llm-ticket-digest.bin") == ""
                    ticket_state = Path('llm-ticket-state.bin').read_bytes()
                    ticket_checks = struct.unpack('<12Q', Path('llm-ticket-receipt.bin').read_bytes())
                    assert ticket_checks == (1,)*12, ticket_checks
                    assert struct.unpack_from('<Q', ticket_state)[0] == 0, 'consumed ticket remained live'
                    assert Path('llm-ticket-digest.bin').read_bytes() == struct.pack(
                        '<8I', 0x12345678, 0x23456789, 0x3456789a, 0x456789ab,
                        0x56789abc, 0x6789abcd, 0x789abcde, 0x89abcdef)
                    llm_ticket_receipt = dict(
                        checks=list(ticket_checks), receipt=pin(Path('llm-ticket-receipt.bin')),
                        state=pin(Path('llm-ticket-state.bin')),
                        digest=pin(Path('llm-ticket-digest.bin')),
                        oneUseAndBindingComponent=True, trustedApproval=False,
                        providerDispatch=False, userCall=False)
        else:
            llm_request = None
        value = None
        if value_context:
            scratch, pages = struct.unpack_from('<QQ', private, 272)
            assert scratch > 0 and pages == 15
            assert hmp(f"pmemsave 0x{scratch:x} 96 value-receipt.bin") == ''
            assert hmp(f"pmemsave 0x{context:x} 65536 value-context.bin") == ''
            checks = struct.unpack('<12Q', Path('value-receipt.bin').read_bytes())
            state = Path('value-context.bin').read_bytes()
            assert checks == (1,)*12, checks
            assert struct.unpack_from('<Q', state, 464)[0] == 0x324c5652
            assert struct.unpack_from('<QQ', state, 480) == (76, 2)
            assert struct.unpack_from('<4I', state, 33792) == (73,74,75,76)
            assert struct.unpack_from('<II', state, 36864) == (0,4294967295)
            assert state[36864+36] == 0
            assert [state[36864+32+i*64+4] for i in range(1,7)] == [1]*6
            # Completion occurred while 74 was current, but only 73 owns it.
            assert struct.unpack_from('<I', state, 49152+12)[0] == 1
            assert struct.unpack_from('<I', state, 53248+12)[0] == 0
            assert struct.unpack_from('<II', state, 49152+64+8) == (7,9)
            value = dict(checks=list(checks),receipt=pin(Path('value-receipt.bin')),
                         context=pin(Path('value-context.bin')),domainArenas=4,
                         completionUsesRequestDomain=True,queueFullRefuses=True,
                         ticketWrapRefuses=True,exactFuelParity=False,
                         userSyscall=False,canonicalValueBinding=False)
        live_call = None
        if value_call:
            scratch, pages = struct.unpack_from('<QQ', private, 272)
            assert scratch > 0 and pages == 15
            assert hmp(f"pmemsave 0x{scratch:x} 128 call-receipt.bin") == ''
            assert hmp(f"pmemsave 0x{context:x} 65536 call-context.bin") == ''
            checks = struct.unpack('<16Q', Path('call-receipt.bin').read_bytes())
            state = Path('call-context.bin').read_bytes()
            assert checks == (1,)*16, checks
            assert struct.unpack_from('<QQ', state, 480) == (73,65537)
            rw = struct.unpack_from('<IIQQQQQQ', data, 120)
            rx = struct.unpack_from('<IIQQQQQQ', data, 64)
            assert rw[5] == 147456
            assert struct.unpack_from('<Q', data, rw[2]+172)[0] == context+131072
            targets = struct.unpack_from('<8Q', state, 30208)
            assert len(set(targets)) == 8 and all(rx[3]+77 < p < rx[3]+rx[5] for p in targets)
            assert state[30208:30272] == data[rw[2]+30208:rw[2]+30272]
            assert struct.unpack_from('<I', state, 32896)[0] == 1364350539
            assert state[32896+56:32896+96] == bytes(40)
            live_call = dict(checks=list(checks),receipt=pin(Path('call-receipt.bin')),
                             context=pin(Path('call-context.bin')),typedRoles=8,
                             forgedPointersPreserveRequest=True,entryAndCASExecuted=True,
                             privateRequestPages=4,userSyscall=False,canonicalValueBinding=False)
        if not stack_exhaustion:
            assert re.search(r"RAX=0*2a\b", registers, re.I), registers
        fb, fbsize = struct.unpack_from("<QQ", info, 112)
        width, height, stride, pixel_format = struct.unpack_from("<IIII", info, 128)
        assert fb > 0 and fbsize > 0 and width > 0 and height > 0 and stride >= width
        (output / "registers.txt").write_text(registers)
        report = dict(status="PASS_NATIVE_STACK_LIMIT_QEMU" if stack_exhaustion else "PASS_AIUEOS_ENTRY_QEMU", observer=pin(Path(__file__).resolve()), efi=pin(efi), kernel=pin(kernel),
                      firmware=pin(firmware), qemuVersion=subprocess.check_output([str(qemu), "--version"]).decode().splitlines()[0],
                      result=None if stack_exhaustion else 42, pc=hex(expected_pc), remainingFuel=fuel,
                      expectedRemainingFuel=None if stack_exhaustion or dma_snapshot or value_context or value_call or llm_header else remaining_fuel, bootInfoVersion=6 if pci_catalog else 5, pciResources=pci, dmaSnapshot=dma, llmHeader=llm, llmRequest=llm_request, llmResult=llm_result_receipt, llmTicket=llm_ticket_receipt, valueContext=value, valueCall=live_call,
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
    p.add_argument("--pci-private", action="store_true")
    p.add_argument("--pci-private-forgery", action="store_true")
    p.add_argument("--dma-snapshot", action="store_true")
    p.add_argument("--value-context", action="store_true")
    p.add_argument("--value-call", action="store_true")
    p.add_argument("--llm-header", action="store_true")
    p.add_argument("--llm-result", action="store_true")
    p.add_argument("--llm-keyword-text", action="store_true")
    p.add_argument("--llm-ticket", action="store_true")
    a = p.parse_args()
    main(*(getattr(a, n).resolve() for n in ("efi", "kernel", "qemu", "firmware", "output")), remaining_fuel=a.remaining_fuel,
         sealed_catalog=a.sealed_catalog, stack_exhaustion=a.stack_exhaustion, pci_catalog=a.pci_catalog, pci_private=a.pci_private, pci_private_forgery=a.pci_private_forgery, dma_snapshot=a.dma_snapshot, value_context=a.value_context, value_call=a.value_call, llm_header=a.llm_header, llm_result=a.llm_result, llm_keyword_text=a.llm_keyword_text, llm_ticket=a.llm_ticket)
