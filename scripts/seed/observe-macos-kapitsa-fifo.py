#!/usr/bin/env python3
"""Observe a pinned Kapitsa local-model startup blocked on a private FIFO.

No model bytes, inference or persistent service are supplied. The loopback
port is only selected for the CLI's startup preflight; the process is killed
while blocked on its private configuration FIFO. No governor is qualified.
"""
import argparse
import ctypes
import errno
import hashlib
import importlib.util
import json
import os
import platform
import re
import select
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path


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
    spec = importlib.util.spec_from_file_location('version_observer', Path(__file__).with_name('observe-macos-kapitsa-version.py'))
    version = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version)
    executable = Path.home() / '.local/share/awai/flint16-0.2.26/kapitsa-0.2.26-darwin-arm64/kapitsa'
    if executable.is_symlink() or hashlib.sha256(executable.read_bytes()).hexdigest() != version.KAPITSA_SHA:
        raise ValueError('unexpected Kapitsa image')
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(executable)], capture_output=True, check=True, timeout=30)
    with tempfile.TemporaryDirectory(prefix='awai152-fifo-model-') as tmp:
        root = Path(tmp)
        fifo = root / 'config.json'
        os.mkfifo(fifo, 0o600)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
        lib.syscall.argtypes = [ctypes.c_int]
        lib.syscall.restype = ctypes.c_int
        raw = ctypes.create_string_buffer(data, len(data))
        desc = (ctypes.c_uint64 * 18)()
        desc[0], desc[1] = len(data), ctypes.addressof(raw)
        fields = [str(executable), 'serve', '--model', str(root), '--host', '127.0.0.1',
                  '--port', str(port), '--private', '--local']
        argv = (ctypes.c_char_p * (len(fields) + 1))(*[x.encode() for x in fields], None)
        env = (ctypes.c_char_p * 5)(b'PATH=/usr/bin:/bin', ('HOME=' + tmp).encode(),
                                    b'KAPITSA_NO_AUTO_UPDATE=1', b'CI=true', None)
        pid = ctypes.c_int(-1)
        null = os.open('/dev/null', os.O_WRONLY)
        saved_out, saved_err = os.dup(1), os.dup(2)
        try:
            os.dup2(null, 1)
            os.dup2(null, 2)
            ctypes.set_errno(0)
            rc = lib.syscall(244, ctypes.byref(pid), ctypes.c_char_p(str(executable).encode()), ctypes.byref(desc), argv, env)
            error = ctypes.get_errno()
        finally:
            os.dup2(saved_out, 1)
            os.dup2(saved_err, 2)
            os.close(saved_out)
            os.close(saved_err)
            os.close(null)
        if rc != 0 or pid.value <= 0:
            raise RuntimeError(('spawn failed', rc, error))
        reaped = False
        queue = None
        writer = None
        try:
            deadline = time.monotonic() + 5
            while True:
                got, status = os.waitpid(pid.value, os.WUNTRACED | os.WNOHANG)
                if got:
                    if not os.WIFSTOPPED(status):
                        reaped = os.WIFEXITED(status) or os.WIFSIGNALED(status)
                        raise RuntimeError(('child did not stop initially', status))
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('child did not stop initially')
                time.sleep(0.01)
            before = version.properties(pid.value)
            if before != [64, 1, 64, 1]:
                raise RuntimeError(('initial properties mismatch', before))
            queue = select.kqueue()
            queue.control([select.kevent(pid.value, filter=select.KQ_FILTER_PROC,
                          flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                          fflags=select.KQ_NOTE_EXEC | select.KQ_NOTE_EXIT)], 0, 0)
            os.kill(pid.value, signal.SIGCONT)
            deadline = time.monotonic() + 5
            while writer is None:
                try:
                    writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                except OSError as e:
                    if e.errno != errno.ENXIO:
                        raise
                    got, status = os.waitpid(pid.value, os.WNOHANG)
                    if got:
                        reaped = True
                        raise RuntimeError(('child exited before FIFO', os.waitstatus_to_exitcode(status)))
                    if time.monotonic() >= deadline:
                        raise TimeoutError('no private FIFO reader observed')
                    time.sleep(0.01)
            os.kill(pid.value, signal.SIGSTOP)
            deadline = time.monotonic() + 5
            while True:
                got, status = os.waitpid(pid.value, os.WUNTRACED | os.WNOHANG)
                if got:
                    if not os.WIFSTOPPED(status):
                        reaped = os.WIFEXITED(status) or os.WIFSIGNALED(status)
                        raise RuntimeError(('child exited before sample', status))
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('child did not stop for sample')
                time.sleep(0.01)
            after = version.properties(pid.value)
            proc = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
            proc.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
            buf = ctypes.create_string_buffer(4096)
            n = proc.proc_pidpath(pid.value, buf, len(buf))
            path_matches = n > 0 and os.path.realpath(os.fsdecode(buf.value)) == os.path.realpath(executable)
            observed = queue.control(None, 4, 0)
            os.kill(pid.value, signal.SIGKILL)
            got, status = os.waitpid(pid.value, 0)
            reaped = True
            if got != pid.value or not os.WIFSIGNALED(status) or os.WTERMSIG(status) != signal.SIGKILL:
                raise RuntimeError(('child not reaped as expected', status))
            print(json.dumps({'schema': 'amu.kapitsa-fifo-attribute-observation.v1',
                              'build': build, 'attributeSha256': args.expected_sha256,
                              'kapitsaSha256': version.KAPITSA_SHA, 'before': before, 'afterFifo': after,
                              'fifoReaderObserved': True, 'pathMatches': path_matches,
                              'execEventObserved': any(e.ident == pid.value and (e.fflags & select.KQ_NOTE_EXEC) for e in observed),
                              'childReapedAfterTestKill': True, 'governorQualified': False}))
        finally:
            if writer is not None:
                os.close(writer)
            if queue is not None:
                queue.close()
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
