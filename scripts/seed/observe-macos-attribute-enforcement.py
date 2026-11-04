#!/usr/bin/env python3
"""Bounded memory test of pinned native-generated spawn attributes.

Two owned children run serially. The control touches 128 MiB and the limited
child uses the exact 64 MiB attribute. This does not qualify GPU/model,
descendant, restart, multi-process or governor behavior.
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

PYTHON = '/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9'
OBSERVER = '''import ctypes,json,sys
class P(ctypes.Structure):
 _fields_=[('active',ctypes.c_int32),('active_attr',ctypes.c_uint32),('inactive',ctypes.c_int32),('inactive_attr',ctypes.c_uint32)]
l=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
f=l.memorystatus_control;f.argtypes=[ctypes.c_uint32,ctypes.c_int32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t];f.restype=ctypes.c_int
p=P();r=f(8,int(sys.argv[1]),0,ctypes.byref(p),ctypes.sizeof(p));print(json.dumps([r,ctypes.get_errno(),p.active,p.active_attr,p.inactive,p.inactive_attr]))
'''
CHILD = '''import json,mmap,os,resource
resource.setrlimit(resource.RLIMIT_CPU,(5,5))
f=int(os.environ['TEST_FD'])
def out(x): os.write(f,(json.dumps(x)+'\\n').encode())
out({'event':'start'})
m=mmap.mmap(-1,128*1024*1024)
for i in range(0,128*1024*1024,16384):
 m[i:i+1]=b'x'
 if i%(8*1024*1024)==0: out({'event':'touched','mib':i//1048576})
out({'event':'complete'})
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attributes', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    data = args.attributes.read_bytes()
    if not re.fullmatch('[0-9a-f]{64}', args.expected_sha256) or len(data) != 248 or hashlib.sha256(data).hexdigest() != args.expected_sha256:
        raise ValueError('attribute digest or length mismatch')
    build = subprocess.run(['/usr/bin/sw_vers', '-buildVersion'], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    if (platform.system(), platform.machine(), build) != ('Darwin', 'arm64', '25G332'):
        raise ValueError('unqualified host')
    pressure = subprocess.run(['/usr/bin/memory_pressure'], check=True, capture_output=True, text=True, timeout=10).stdout
    match = re.search(r'System-wide memory free percentage:\s*(\d+)%', pressure)
    if not match or int(match.group(1)) < 40:
        raise RuntimeError('preflight pressure unavailable or below refusal threshold')
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    lib.syscall.argtypes = [ctypes.c_int]
    lib.syscall.restype = ctypes.c_int
    lib.posix_spawnattr_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.posix_spawnattr_setflags.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_short]
    lib.posix_spawnattr_destroy.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    results = []
    for mode in ('control', 'limited'):
        rd, wr = os.pipe()
        os.set_inheritable(wr, True)
        attr = ctypes.c_void_p()
        pid = ctypes.c_int(-1)
        reaped = False
        try:
            if mode == 'control':
                if lib.posix_spawnattr_init(ctypes.byref(attr)) != 0 or lib.posix_spawnattr_setflags(ctypes.byref(attr), 0x80) != 0:
                    raise RuntimeError('control attribute setup failed')
                address = attr.value
            else:
                raw = ctypes.create_string_buffer(data, len(data))
                address = ctypes.addressof(raw)
            desc = (ctypes.c_uint64 * 18)()
            desc[0], desc[1] = 248, address
            argv = (ctypes.c_char_p * 4)(PYTHON.encode(), b'-c', CHILD.encode(), None)
            env = (ctypes.c_char_p * 3)(b'PATH=/usr/bin:/bin', ('TEST_FD='+str(wr)).encode(), None)
            ctypes.set_errno(0)
            rc = lib.syscall(244, ctypes.byref(pid), ctypes.c_char_p(PYTHON.encode()), ctypes.byref(desc), argv, env)
            if rc != 0 or pid.value <= 0:
                raise RuntimeError(('spawn failed', mode, rc, ctypes.get_errno()))
            os.close(wr)
            wr = -1
            deadline = time.monotonic() + 5
            while True:
                got, status = os.waitpid(pid.value, os.WUNTRACED | os.WNOHANG)
                if got:
                    if not os.WIFSTOPPED(status):
                        reaped = os.WIFEXITED(status) or os.WIFSIGNALED(status)
                        raise RuntimeError(('child did not stop', mode, status))
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('child did not stop')
                time.sleep(0.01)
            r = subprocess.run(['/usr/bin/sudo', '-n', '/usr/bin/python3', '-c', OBSERVER, str(pid.value)], capture_output=True, text=True, timeout=10, check=True)
            props = json.loads(r.stdout)
            if props[0] != 0 or (mode == 'limited' and props[2:] != [64, 1, 64, 1]):
                raise RuntimeError(('invalid properties', mode, props))
            if mode == 'control' and props[2] == 64 and props[4] == 64:
                raise RuntimeError('control unexpectedly has the test limit')
            os.kill(pid.value, signal.SIGCONT)
            deadline = time.monotonic() + 15
            while True:
                got, status = os.waitpid(pid.value, os.WNOHANG)
                if got:
                    reaped = True
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('child did not finish')
                time.sleep(0.02)
            output = b''
            while True:
                part = os.read(rd, 8192)
                if not part:
                    break
                output += part
                if len(output) > 16384:
                    raise ValueError('excess child output')
            events = [json.loads(line) for line in output.splitlines()]
            exit_code = os.waitstatus_to_exitcode(status)
            complete = any(e.get('event') == 'complete' for e in events)
            if mode == 'control' and (exit_code != 0 or not complete):
                raise RuntimeError(('control failed', exit_code, events))
            if mode == 'limited' and (exit_code != -signal.SIGKILL or complete):
                raise RuntimeError(('limited case unexpected', exit_code, events))
            results.append({'mode': mode, 'properties': props[2:], 'exit': exit_code, 'events': events})
        finally:
            if pid.value > 0 and not reaped:
                try:
                    os.kill(pid.value, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(pid.value, 0)
                except ChildProcessError:
                    pass
            if wr >= 0:
                os.close(wr)
            os.close(rd)
            if attr.value:
                lib.posix_spawnattr_destroy(ctypes.byref(attr))
    print(json.dumps({'schema': 'amu.darwin-attribute-enforcement-observation.v1', 'build': build,
                      'attributeSha256': args.expected_sha256, 'preflightFreePercent': int(match.group(1)),
                      'cases': results, 'kernelKillReasonCollected': False, 'governorQualified': False}))


if __name__ == '__main__':
    main()
