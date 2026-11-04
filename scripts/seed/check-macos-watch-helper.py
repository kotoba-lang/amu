#!/usr/bin/env python3
"""Stage and observe the experimental native watcher on an owned child.

This is a kernel/ABI fixture, not a process supervisor or governor.
The compiler and emitted watcher execute natively; Python only stages,
queries identity and observes their outputs.
"""
import ctypes
import importlib.util
import os
import signal
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/seed' / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def identity(pid):
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                 ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int
    raw = ctypes.create_string_buffer(136)
    got = lib.proc_pidinfo(pid, 3, 0, raw, len(raw))
    if got != 136:
        raise RuntimeError(('proc_pidinfo', got, ctypes.get_errno()))
    observed = struct.unpack_from('<I', raw.raw, 12)[0]
    sec, usec = struct.unpack_from('<QQ', raw.raw, 120)
    if observed != pid or not sec or usec > 999999:
        raise RuntimeError('invalid process identity')
    return sec, usec


def observe(image, directory, request):
    path = directory / 'request.bin'
    path.write_bytes(request)
    fd = os.open(path, os.O_RDONLY)
    saved = None
    relocated = fd != 3
    try:
        if relocated:
            try:
                saved = os.dup(3)
            except OSError:
                pass
            os.dup2(fd, 3)
        return subprocess.run([str(image)], cwd=directory, pass_fds=(3,),
                              capture_output=True, timeout=10, check=False)
    finally:
        if relocated:
            if saved is None:
                os.close(3)
            else:
                os.dup2(saved, 3)
                os.close(saved)
        os.close(fd)


def run(compiler, packager, output):
    gate = load('mac_native_watcher', 'check-aiueos-user-macos-native.py')
    fixture = load('mac_scope_watcher', 'check-macos-arena-scope.py')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    source = ROOT / 'seed/macos-process-watch-packager.kotoba'
    emitter = fixture.build(gate, compiler, packager, output, 'watch-emitter', source)
    gate.native_run(emitter, output, 'watch-unsigned.macho', timeout=120)
    unsigned = output / 'watch-unsigned.macho'
    image = output / 'watch.macho'
    image.write_bytes(unsigned.read_bytes())
    image.chmod(0o700)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(image)],
                   capture_output=True, check=True, timeout=30)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(image)],
                   capture_output=True, check=True, timeout=30)
    child = subprocess.Popen(['/bin/sleep', '4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        sec, usec = identity(child.pid)
        request = struct.pack('<4sIQQII', b'WP01', child.pid, sec, usec, 12345, 8)
        wrong = struct.pack('<4sIQQII', b'WP01', child.pid, sec + 1, usec, 12345, 8)
        refused = observe(image, output, wrong)
        if refused.returncode == 0 or refused.stdout:
            raise RuntimeError(('wrong identity accepted', refused.returncode, refused.stdout))
        result = observe(image, output, request)
        if result.returncode != 0 or result.stdout != b'WO01\0\0\0\0' + request or result.stderr:
            raise RuntimeError(('watch failed', result.returncode, result.stdout, result.stderr))
        if child.wait(timeout=2) != 0:
            raise RuntimeError('owned child did not exit normally')
        print('PASS_MAC_WATCH_HELPER exact event and wrong-start-time refusal; no governor qualification')
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGKILL)
            child.wait(timeout=3)
