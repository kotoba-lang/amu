#!/usr/bin/env python3
"""Observe one pinned Kapitsa --version child under the diagnostic attribute.

No model, listener, persistent service, reservation or governor is started.
Post-resume sampling is race-prone and an unknown result stays unknown.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import select
import signal
import subprocess
import time
from pathlib import Path

KAPITSA_SHA = '20db8dadcb79de820d237367ca93d7ac66f8a70d91d5513f6e1ab77253925daa'
OBSERVER = '''import ctypes,json,sys
class P(ctypes.Structure):
 _fields_=[('active',ctypes.c_int32),('active_attr',ctypes.c_uint32),('inactive',ctypes.c_int32),('inactive_attr',ctypes.c_uint32)]
l=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
f=l.memorystatus_control;f.argtypes=[ctypes.c_uint32,ctypes.c_int32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t];f.restype=ctypes.c_int
p=P();r=f(8,int(sys.argv[1]),0,ctypes.byref(p),ctypes.sizeof(p));print(json.dumps([r,ctypes.get_errno(),p.active,p.active_attr,p.inactive,p.inactive_attr]))
'''


def properties(pid):
    r = subprocess.run(['/usr/bin/sudo', '-n', '/usr/bin/python3', '-c', OBSERVER, str(pid)],
                       capture_output=True, text=True, timeout=10, check=True)
    values = json.loads(r.stdout)
    if values[0] != 0:
        raise RuntimeError(('memory readback unavailable', values))
    return values[2:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--attributes', required=True, type=Path)
    p.add_argument('--expected-sha256', required=True)
    args = p.parse_args()
    data = args.attributes.read_bytes()
    if not re.fullmatch('[0-9a-f]{64}', args.expected_sha256) or len(data) != 248 or hashlib.sha256(data).hexdigest() != args.expected_sha256:
        raise ValueError('attribute digest or size mismatch')
    build = subprocess.run(['/usr/bin/sw_vers', '-buildVersion'], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if (platform.system(), platform.machine(), build) != ('Darwin', 'arm64', '25G332'):
        raise ValueError('unqualified host')
    executable = Path.home() / '.local/share/awai/flint16-0.2.26/kapitsa-0.2.26-darwin-arm64/kapitsa'
    if executable.is_symlink() or hashlib.sha256(executable.read_bytes()).hexdigest() != KAPITSA_SHA:
        raise ValueError('unexpected Kapitsa image')
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(executable)], capture_output=True, check=True, timeout=30)
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    lib.syscall.argtypes = [ctypes.c_int]
    lib.syscall.restype = ctypes.c_int
    raw = ctypes.create_string_buffer(data, len(data))
    desc = (ctypes.c_uint64 * 18)()
    desc[0], desc[1] = len(data), ctypes.addressof(raw)
    argv = (ctypes.c_char_p * 3)(str(executable).encode(), b'--version', None)
    env = (ctypes.c_char_p * 2)(b'PATH=/usr/bin:/bin', None)
    pid = ctypes.c_int(-1)
    rd, wr = os.pipe()
    saved = os.dup(1)
    try:
        os.dup2(wr, 1)
        ctypes.set_errno(0)
        rc = lib.syscall(244, ctypes.byref(pid), ctypes.c_char_p(str(executable).encode()), ctypes.byref(desc), argv, env)
        error = ctypes.get_errno()
    finally:
        os.dup2(saved, 1)
        os.close(saved)
        os.close(wr)
    if rc != 0 or pid.value <= 0:
        os.close(rd)
        raise RuntimeError(('spawn failed', rc, error))
    reaped = False
    queue = None
    try:
        deadline = time.monotonic() + 5
        while True:
            got, status = os.waitpid(pid.value, os.WUNTRACED | os.WNOHANG)
            if got:
                if not os.WIFSTOPPED(status):
                    reaped = os.WIFEXITED(status) or os.WIFSIGNALED(status)
                    raise RuntimeError(('child did not stop', status))
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('child did not stop')
            time.sleep(0.01)
        before = properties(pid.value)
        if before != [64, 1, 64, 1]:
            raise RuntimeError(('initial limit mismatch', before))
        queue = select.kqueue()
        queue.control([select.kevent(pid.value, filter=select.KQ_FILTER_PROC,
                      flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                      fflags=select.KQ_NOTE_EXEC | select.KQ_NOTE_EXIT)], 0, 0)
        os.kill(pid.value, signal.SIGCONT)
        time.sleep(0.005)
        sample = None
        try:
            os.kill(pid.value, signal.SIGSTOP)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 5
        while True:
            got, status = os.waitpid(pid.value, os.WUNTRACED | os.WNOHANG)
            if got:
                if os.WIFSTOPPED(status):
                    sample = properties(pid.value)
                    os.kill(pid.value, signal.SIGCONT)
                else:
                    reaped = True
                    break
            if time.monotonic() >= deadline:
                raise TimeoutError('child did not exit')
            time.sleep(0.01)
        events = queue.control(None, 4, 0)
        os.set_blocking(rd, False)
        try:
            output = os.read(rd, 4096)
        except BlockingIOError:
            output = b''
        print(json.dumps({'schema': 'amu.kapitsa-version-attribute-observation.v1',
                          'build': build, 'kapitsaSha256': KAPITSA_SHA,
                          'attributeSha256': args.expected_sha256, 'before': before,
                          'postResumeSample': sample, 'exit': os.waitstatus_to_exitcode(status),
                          'versionOutput': output.decode(errors='replace').strip(),
                          'execEventObserved': any(e.ident == pid.value and (e.fflags & select.KQ_NOTE_EXEC) for e in events),
                          'governorQualified': False}))
    finally:
        if queue is not None:
            queue.close()
        os.close(rd)
        if not reaped:
            try:
                os.kill(pid.value, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid.value, 0)
            except ChildProcessError:
                pass


if __name__ == '__main__':
    main()
