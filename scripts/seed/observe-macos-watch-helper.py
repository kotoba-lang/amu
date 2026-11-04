#!/usr/bin/env python3
"""Observe a pinned signed watcher on a disposable owned child; no builds.

The caller must bind the hash to a verified build and record its provenance.
This is an ABI diagnostic, not a scheduler, process-tree proof, or governor.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import platform
import re
import signal
import struct
import subprocess
import tempfile
import threading
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--watcher', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.expected_sha256):
        raise ValueError('invalid expected SHA-256')
    watcher = args.watcher.resolve(strict=True)
    if not watcher.is_file() or hashlib.sha256(watcher.read_bytes()).hexdigest() != args.expected_sha256:
        raise ValueError('watcher hash mismatch')
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise ValueError('Darwin ARM64 required')
    build = subprocess.run(['/usr/bin/sw_vers', '-buildVersion'], check=True,
                           capture_output=True, text=True, timeout=10).stdout.strip()
    if build != '25G332':
        raise ValueError('unqualified Darwin build: ' + build)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(watcher)],
                   check=True, capture_output=True, timeout=30)
    spec = importlib.util.spec_from_file_location('watch_test', Path(__file__).with_name('check-macos-watch-helper.py'))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    with tempfile.TemporaryDirectory(prefix='awai152-watch-observe-') as tmp:
        root = Path(tmp)
        child = subprocess.Popen(['/bin/sleep', '8'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            sec, usec = helper.identity(child.pid)
            request = struct.pack('<4sIQQII', b'WP01', child.pid, sec, usec, 12345, 8)
            wrong = struct.pack('<4sIQQII', b'WP01', child.pid, sec + 1, usec, 12345, 8)
            refused = helper.observe(watcher, root, wrong)
            if refused.returncode != 1 or refused.stdout or refused.stderr or child.poll() is not None:
                raise RuntimeError('wrong identity did not cleanly refuse on live child')
            short = struct.pack('<4sIQQII', b'WP01', child.pid, sec, usec, 12345, 1)
            timed = helper.observe(watcher, root, short)
            if timed.returncode != 1 or timed.stdout != b'WR01\0\0\0\0' + short or timed.stderr or child.poll() is not None:
                raise RuntimeError('timeout did not cleanly refuse on live child')
            result = helper.observe(watcher, root, request)
            if result.returncode != 0 or result.stdout != b'WR01\0\0\0\0' + request + b'WO01\0\0\0\0' + request or result.stderr:
                raise RuntimeError('exact event response failed')
            if child.wait(timeout=2) != 0:
                raise RuntimeError('owned child failed')
            reaped = helper.observe(watcher, root, request)
            if reaped.returncode != 1 or reaped.stdout or reaped.stderr:
                raise RuntimeError('reaped PID did not cleanly refuse')
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGKILL)
                child.wait(timeout=3)
        # An observed exit event is not a successful child outcome. Kill a
        # separate owned child while the watcher is registered, then compare
        # the watch frame with the independent wait status.
        killed = subprocess.Popen(['/bin/sleep', '10'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        timer = None
        try:
            sec, usec = helper.identity(killed.pid)
            request = struct.pack('<4sIQQII', b'WP01', killed.pid, sec, usec, 23456, 8)
            timer = threading.Timer(2, killed.kill)
            timer.start()
            result = helper.observe(watcher, root, request)
            status = killed.wait(timeout=3)
            if result.returncode != 0 or result.stdout != b'WR01\0\0\0\0' + request + b'WO01\0\0\0\0' + request or result.stderr:
                raise RuntimeError('signalled child did not produce exact event')
            if status != -signal.SIGKILL:
                raise RuntimeError('independent child status was not SIGKILL')
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            if killed.poll() is None:
                killed.kill()
                killed.wait(timeout=3)
        # These cases start their own short-lived child and verify that the
        # watcher refuses the event. They do not prevent fork or exec.
        with contextlib.redirect_stdout(io.StringIO()):
            helper.transition_case(watcher, root, 'exec')
            helper.transition_case(watcher, root, 'fork')
            helper.persistent_case(watcher, root)
            helper.transition_case(watcher, root, 'exec', b'WP02')
            helper.transition_case(watcher, root, 'fork', b'WP02')
    print(json.dumps({'schema': 'amu.darwin-watch-observation.v1', 'build': build,
                      'watcherSha256': args.expected_sha256, 'positive': True,
                      'wrongIdentityRefused': True, 'timeoutRefused': True,
                      'reapedPidRefused': True, 'signalledExitEventObserved': True,
                      'signalledChildIsSuccess': False, 'execEventRefused': True,
                      'forkEventRefused': True, 'persistentExitObserved': True,
                      'persistentExecRefused': True, 'persistentForkRefused': True,
                      'governorQualified': False}))


if __name__ == '__main__':
    main()
