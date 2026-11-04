#!/usr/bin/env python3
"""Observe CI-produced attribute bytes on one task-owned suspended process.

The expected digest must come from verified CI evidence. This does not test
memory enforcement, workload containment, or authorize a governor release.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attributes', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.expected_sha256):
        raise ValueError('invalid attribute digest')
    data = args.attributes.read_bytes()
    if len(data) != 248 or hashlib.sha256(data).hexdigest() != args.expected_sha256:
        raise ValueError('attribute digest or length mismatch')
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise ValueError('Darwin ARM64 required')
    build = subprocess.run(['/usr/bin/sw_vers', '-buildVersion'], check=True,
                           capture_output=True, text=True, timeout=10).stdout.strip()
    if build != '25G332':
        raise ValueError('unqualified Darwin build: ' + build)
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    lib.syscall.argtypes = [ctypes.c_int]
    lib.syscall.restype = ctypes.c_int
    raw = ctypes.create_string_buffer(data, len(data))
    desc = (ctypes.c_uint64 * 18)()
    desc[0], desc[1] = len(data), ctypes.addressof(raw)
    argv = (ctypes.c_char_p * 2)(b'/usr/bin/true', None)
    env = (ctypes.c_char_p * 2)(b'PATH=/usr/bin:/bin', None)
    pid = ctypes.c_int(-1)
    ctypes.set_errno(0)
    rc = lib.syscall(244, ctypes.byref(pid), ctypes.c_char_p(b'/usr/bin/true'),
                     ctypes.byref(desc), argv, env)
    if rc != 0 or pid.value <= 0:
        raise RuntimeError(('spawn failed', rc, ctypes.get_errno()))
    reaped = False
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
        observer = '''import ctypes,json,sys
class P(ctypes.Structure):
 _fields_=[('active',ctypes.c_int32),('active_attr',ctypes.c_uint32),('inactive',ctypes.c_int32),('inactive_attr',ctypes.c_uint32)]
l=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
f=l.memorystatus_control;f.argtypes=[ctypes.c_uint32,ctypes.c_int32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t];f.restype=ctypes.c_int
p=P();r=f(8,int(sys.argv[1]),0,ctypes.byref(p),ctypes.sizeof(p));print(json.dumps([r,ctypes.get_errno(),p.active,p.active_attr,p.inactive,p.inactive_attr]))
'''
        observed = subprocess.run(['/usr/bin/sudo', '-n', '/usr/bin/python3', '-c', observer, str(pid.value)],
                                  capture_output=True, text=True, timeout=10, check=True)
        values = json.loads(observed.stdout)
        if values[0] != 0 or values[2:] != [64, 1, 64, 1]:
            raise RuntimeError(('unexpected memory properties', values))
        os.kill(pid.value, signal.SIGCONT)
        deadline = time.monotonic() + 5
        while True:
            got, status = os.waitpid(pid.value, os.WNOHANG)
            if got:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('child did not exit')
            time.sleep(0.01)
        reaped = True
        if got != pid.value or not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
            raise RuntimeError(('child failed', status))
        print(json.dumps({'schema': 'amu.darwin-spawn-attribute-observation.v1',
                          'build': build, 'attributeSha256': args.expected_sha256,
                          'suspended': True, 'memoryProperties': values[2:],
                          'childExit': 0, 'governorQualified': False}))
    finally:
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
