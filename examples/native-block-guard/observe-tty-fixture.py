#!/usr/bin/env python3
"""PTY observer only: injected responses do not establish human consent."""
import os
import pty
import select
import subprocess
import sys
import time

PROGRAM = sys.argv[1]
PROMPT = b'TEST ONLY: erase marked 4 MiB virtual fixture? Type YES: '


def case(answer, expected):
    master, slave = pty.openpty()
    proc = subprocess.Popen([PROGRAM], stdin=slave, stdout=slave, stderr=slave,
                            close_fds=True, env={})
    os.close(slave)
    data = b''
    try:
        deadline = time.monotonic() + 10
        while PROMPT not in data:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([master], [], [], remaining)[0]:
                raise RuntimeError('prompt timeout')
            part = os.read(master, 4096)
            if not part:
                raise RuntimeError('missing prompt')
            data += part
        os.write(master, answer)
        result = proc.wait(timeout=10)
        if result != expected:
            raise RuntimeError('wrong process result: %s' % result)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)


case(b'YES\n', 0)
case(b'NO\n', 1)
case(b'YES!\n', 1)
pipe = subprocess.run([PROGRAM], input=b'YES\n', capture_output=True,
                      timeout=10, env={}, check=False)
if pipe.returncode != 1 or pipe.stdout:
    raise RuntimeError('non-TTY input or output accepted')
master1, slave1 = pty.openpty()
master2, slave2 = pty.openpty()
try:
    mixed = subprocess.run([PROGRAM], stdin=slave1, stdout=slave2,
                           stderr=subprocess.PIPE, timeout=10, env={}, check=False)
    if mixed.returncode != 1:
        raise RuntimeError('different terminals accepted')
finally:
    for fd in (master1, slave1, master2, slave2):
        os.close(fd)
print('native tty fixture: YES accepted, NO/extra/pipe/different-tty refused; responses synthetic')
