#!/usr/bin/python3
"""Local diagnostic only: test process-fork policy, not a governor."""
import errno
import json
import os
import subprocess
import sys
import threading

if len(sys.argv) == 2 and sys.argv[1] == 'child':
    thread_result = []
    thread = threading.Thread(target=lambda: thread_result.append(True))
    thread.start(); thread.join()
    def attempt(method):
        try:
            if method == 'fork':
                pid = os.fork()
                if pid == 0: os._exit(0)
            else:
                pid = os.posix_spawn('/usr/bin/true', ['/usr/bin/true'], {})
            _, status = os.waitpid(pid, 0)
            return 'ok' if os.waitstatus_to_exitcode(status) == 0 else 'unexpected-child-status'
        except OSError as error:
            return 'EPERM' if error.errno == errno.EPERM else 'error-' + str(error.errno)
    print(json.dumps({'thread': thread_result == [True], 'fork': attempt('fork'),
                      'posix_spawn': attempt('spawn')}, sort_keys=True))
    sys.exit(0)
if len(sys.argv) == 2 and sys.argv[1] == 'exec':
    os.execv(sys.executable, [sys.executable, os.path.realpath(__file__), 'child'])
if len(sys.argv) != 1: raise SystemExit('invalid arguments')
profile = '(version 1) (allow default) (deny process-fork)'
for name, command, expected in (
    ('control', [sys.executable, __file__, 'child'], 'ok'),
    ('restricted', ['/usr/bin/sandbox-exec', '-p', profile, sys.executable, __file__, 'child'], 'EPERM'),
    ('after_exec', ['/usr/bin/sandbox-exec', '-p', profile, sys.executable, __file__, 'exec'], 'EPERM')):
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=15)
    value = json.loads(result.stdout)
    if value != {'thread': True, 'fork': expected, 'posix_spawn': expected}:
        raise SystemExit(name + ' unexpected: ' + repr(value))
    print(name, json.dumps(value, sort_keys=True))
