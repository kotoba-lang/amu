#!/usr/bin/env python3
"""Observe legacy close_range semantics on an isolated Linux ARM64 child.

This is a syscall diagnostic, not execution of the Amu runtime candidate.
"""
import ctypes
import errno
import json
import os
import pathlib
import platform
import tempfile

assert platform.system() == 'Linux' and platform.machine() == 'aarch64'
libc = ctypes.CDLL(None, use_errno=True)

def syscall(number, *args):
    ctypes.set_errno(0)
    value = libc.syscall(number, *args)
    return value, ctypes.get_errno()

def observe(root, mode):
    scope = root / mode
    scope.mkdir()
    scope_fd = os.open(scope, os.O_RDONLY | os.O_DIRECTORY)
    out_r, out_w = os.pipe()
    status_r, status_w = os.pipe2(os.O_CLOEXEC)
    for fd in (50, 200):
        os.dup2(scope_fd, fd, inheritable=True)
    pid = os.fork()
    if pid == 0:
        try:
            os.dup2(out_w, 1)
            os.fchdir(scope_fd)
            result, error = syscall(436, 3, ctypes.c_uint(0xffffffff), 4)
            if result != -1 or error != errno.EINVAL:
                os.write(status_w, b'unexpected-fast-path')
                os._exit(101)
            if status_w < 3 or syscall(25, status_w, 2, 1)[0] < 0:
                os.write(status_w, b'fcntl-failed')
                os._exit(102)
            first = syscall(436, 4, 3, 0) if mode == 'fault' else (
                (0, 0) if status_w == 3 else syscall(436, 3, status_w - 1, 0))
            if first[0] < 0:
                os.write(status_w, b'close-failed')
                os._exit(127)
            if syscall(436, status_w + 1, ctypes.c_uint(0xffffffff), 0)[0] < 0:
                os.write(status_w, b'close-failed')
                os._exit(127)
            if syscall(167, 38, 1, 0, 0, 0)[0] < 0:
                os.write(status_w, b'prctl-failed')
                os._exit(127)
            script = ('import os,pathlib; '
                      'closed=[]; '
                      'exec("for f in (50,200):\\n try: os.fstat(f)\\n except OSError: closed.append(f)"); '
                      'n=pathlib.Path("/proc/self/status").read_text(); '
                      'assert closed==[50,200] and "NoNewPrivs:\\t1" in n; '
                      'pathlib.Path("ran").write_text(os.getcwd())')
            os.execve('/usr/bin/python3', ['/usr/bin/python3', '-c', script], {'PATH': '/usr/bin:/bin'})
        except BaseException as exc:
            try:
                os.write(status_w, ('error:' + type(exc).__name__).encode())
            finally:
                os._exit(103)
    os.close(scope_fd)
    os.close(out_w)
    os.close(status_w)
    for fd in (50, 200):
        os.close(fd)
    status = os.read(status_r, 128)
    output = os.read(out_r, 1024)
    _, raw = os.waitpid(pid, 0)
    os.close(status_r)
    os.close(out_r)
    exit_code = os.WEXITSTATUS(raw) if os.WIFEXITED(raw) else -os.WTERMSIG(raw)
    marker = scope / 'ran'
    if mode == 'ok':
        assert exit_code == 0 and not status and marker.read_text() == str(scope), (exit_code, status, output)
    else:
        assert exit_code == 127 and status == b'close-failed' and not marker.exists(), (exit_code, status, output)
    return {'mode': mode, 'exit': exit_code, 'status': status.decode(), 'marker': marker.exists()}

with tempfile.TemporaryDirectory(prefix='awai-spawn-legacy-') as directory:
    base = pathlib.Path(directory)
    results = [observe(base, mode) for mode in ('ok', 'fault')]
    print(json.dumps({'kernel': platform.release(), 'results': results}, sort_keys=True))
