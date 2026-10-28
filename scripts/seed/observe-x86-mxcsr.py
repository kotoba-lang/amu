#!/usr/bin/env python3
"""Observe caller MXCSR through a real KX64 runner without loading guest code in Python."""
import argparse
import ctypes
import json
import os
import platform
import re
import signal
from pathlib import Path

class FP(ctypes.Structure):
    _fields_ = [('cwd', ctypes.c_ushort), ('swd', ctypes.c_ushort), ('ftw', ctypes.c_ushort), ('fop', ctypes.c_ushort),
                ('rip', ctypes.c_ulonglong), ('rdp', ctypes.c_ulonglong), ('mxcsr', ctypes.c_uint), ('mxcr_mask', ctypes.c_uint),
                ('st', ctypes.c_uint * 32), ('xmm', ctypes.c_uint * 64), ('padding', ctypes.c_uint * 24)]
class Regs(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ('r15','r14','r13','r12','rbp','rbx','r11','r10','r9','r8','rax','rcx','rdx','rsi','rdi','orig_rax','rip','cs','eflags','rsp','ss','fs_base','gs_base','ds','es','fs','gs')]
libc = ctypes.CDLL(None, use_errno=True)
libc.ptrace.argtypes = (ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
libc.ptrace.restype = ctypes.c_long

def trace(req, pid, data=None):
    value = libc.ptrace(req, pid, None, data)
    if value == -1:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return value

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runner', type=Path, required=True)
    p.add_argument('--payload', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or ctypes.sizeof(FP) != 512:
        raise SystemExit('native Linux x86_64 and expected FP register layout required')
    runner = a.runner.resolve(strict=True); payload = a.payload.resolve(strict=True)
    out = a.output.resolve(); out.mkdir(mode=0o700, parents=True, exist_ok=False)
    stdout = out / 'guest.stdout'; stderr = out / 'guest.stderr'
    child = os.fork()
    if child == 0:
        try:
            trace(0, 0)
            os.dup2(os.open(stdout, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 1)
            os.dup2(os.open(stderr, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 2)
            os.kill(os.getpid(), signal.SIGSTOP)
            os.execve(runner, [str(runner), str(payload), '0', '0', 'x86_64', '-'],
                      {'PATH': '/nonexistent', 'KEXE_STACK_BYTES': '8388608',
                       'KEXE_CAP_RESOURCES_35': str(out.parent), 'KEXE_STRUCTURED_REPORT': '1', 'KEXE_ALLOW': '-'})
        except BaseException:
            os._exit(127)
    try:
        _, status = os.waitpid(child, 0)
        if not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGSTOP:
            raise RuntimeError('child did not stop before exec')
        trace(0x4200, child, ctypes.c_void_p(1))  # PTRACE_O_TRACESYSGOOD
        trace(7, child)  # PTRACE_CONT to successful exec stop
        _, status = os.waitpid(child, 0)
        if not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGTRAP:
            raise RuntimeError('runner did not reach exec stop')
        fp = FP(); trace(14, child, ctypes.byref(fp))
        wanted = 0x7f80  # exceptions masked; round toward zero
        if fp.mxcr_mask and wanted & ~fp.mxcr_mask:
            raise RuntimeError('requested MXCSR contains unsupported bits')
        fp.mxcsr = wanted; trace(15, child, ctypes.byref(fp))
        fp = FP(); trace(14, child, ctypes.byref(fp))
        if fp.mxcsr != wanted:
            raise RuntimeError('caller MXCSR injection failed')
        after = None
        for _ in range(100000):
            trace(24, child)  # PTRACE_SYSCALL
            _, status = os.waitpid(child, 0)
            if not os.WIFSTOPPED(status):
                raise RuntimeError('runner ended before an observed exit syscall')
            sig = os.WSTOPSIG(status)
            if sig != (signal.SIGTRAP | 0x80):
                raise RuntimeError('unexpected signal while observing runner: ' + str(sig))
            regs = Regs(); trace(12, child, ctypes.byref(regs))
            if regs.orig_rax in (60, 231) and regs.rax == (1 << 64) - 38:
                fp = FP(); trace(14, child, ctypes.byref(fp)); after = fp.mxcsr
                trace(7, child)
                _, status = os.waitpid(child, 0)
                if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                    raise RuntimeError('runner did not exit 0')
                break
        if after is None:
            raise RuntimeError('syscall observation limit exceeded')
        raw = stdout.read_bytes()
        if not re.search(rb':status :ok\s+:result 511\b', raw) or after != wanted:
            raise RuntimeError('float result or caller MXCSR preservation mismatch')
        (out / 'mxcsr.json').write_text(json.dumps({'status':'PASS_X86_MXCSR_OBSERVATION',
            'before':wanted,'after':after,'expectedGuestResult':511,'publicProductAdopted':False,
            'scope':'ptrace observation of one native runner process, not whole runtime qualification'}, indent=2)+'\n')
        print('PASS_X86_MXCSR_OBSERVATION', hex(wanted), hex(after), flush=True)
    finally:
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(child, os.WNOHANG)
        except ChildProcessError:
            pass

if __name__ == '__main__':
    main()
