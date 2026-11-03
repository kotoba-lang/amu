#!/usr/bin/env python3
"""Synthetic PTY observer for one attached, task-owned disk image only.

PTY responses are injected by a process, not a trusted human decision.
"""
import errno
import os
import plistlib
import pty
import select
import subprocess
import sys
import time

program, rawchar, backing, access, response, expected_text, prompt_text = sys.argv[1:]
expected = int(expected_text)
want_prompt = prompt_text == 'prompt'
if not rawchar.startswith('/dev/rdisk') or not rawchar[10:].isdigit():
    raise SystemExit('invalid raw device name')
whole = '/dev/disk' + rawchar[10:]
images = plistlib.loads(subprocess.check_output(['/usr/bin/hdiutil', 'info', '-plist']))
matches = [x for x in images.get('images', [])
           if os.path.realpath(x.get('image-path', '')) == os.path.realpath(backing)
           and any(y.get('dev-entry') == whole for y in x.get('system-entities', []))]
if len(matches) != 1:
    raise SystemExit('backing image identity mismatch')
fd = os.open(rawchar, os.O_RDWR if access == 'rw' else os.O_RDONLY)
master, slave = pty.openpty()
pid = os.fork()
if pid == 0:
    try:
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        os.dup2(fd, 3)
        os.set_inheritable(3, True)
        for n in (master, slave, fd):
            if n > 3:
                os.close(n)
        os.execve(program, [program], {})
    finally:
        os._exit(127)
os.close(slave)
os.close(fd)
prompt = b'TEST ONLY: erase marked 4 MiB virtual fixture? Type YES: '
received = b''
sent = False
status = None
try:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if select.select([master], [], [], 0.05)[0]:
            try:
                chunk = os.read(master, 4096)
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                chunk = b''
            received += chunk
            if prompt in received and not sent:
                os.write(master, response.encode('ascii') + b'\n')
                sent = True
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            break
    else:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
        raise RuntimeError('native raw choice timed out')
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != expected:
        raise RuntimeError('unexpected native exit status')
    if sent != want_prompt:
        raise RuntimeError('unexpected prompt state')
finally:
    os.close(master)
