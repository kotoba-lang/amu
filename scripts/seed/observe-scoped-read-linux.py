"""Observe a synthetic KFR1 guest in an isolated Linux container."""
import json
import os
import subprocess
import sys
from pathlib import Path

work = Path('/work')
scope = work / 'scope'
scope.mkdir()
env = dict(os.environ, KEXE_ALLOW='35,37,38', KEXE_CAP_RESOURCES_35=str(scope),
           KEXE_SECCOMP='if-available')
cases = []

def check(name, path, expected, output, e=env):
    result = subprocess.run([str(work / 'probe.elf'), str(path)], env=e, capture_output=True, text=True, timeout=10)
    if result.returncode != expected or result.stdout != output or result.stderr:
        raise ValueError((name, result.returncode, result.stdout, result.stderr))
    cases.append(name)

(scope / 'empty').write_bytes(b'')
(scope / 'hello').write_text('hello\n')
(scope / 'big').write_bytes(b'x' * (1048576 + 1))
(work / 'outside').write_text('outside')
(scope / 'link').symlink_to('hello')
(scope / 'folder').mkdir()
(scope / 'folder' / 'hello').write_text('hello\n')
(scope / 'parent-link').symlink_to('folder', target_is_directory=True)
if len(sys.argv) > 1 and sys.argv[1] == 'pread-fault':
    check('pread-eio', scope / 'hello', 2, '0 1 \n')
    if (scope / 'hello').read_text() != 'hello\n':
        raise ValueError('read fault changed source data')
    (work / 'fault-result.json').write_text(json.dumps({'status': 'PASS', 'cases': cases}, indent=2) + '\n')
    raise SystemExit(0)
check('regular', scope / 'hello', 0, '1 7 hello\n\n')
check('empty', scope / 'empty', 0, '1 1 \n')
check('missing', scope / 'missing', 2, '0 1 \n')
check('directory', scope, 2, '0 1 \n')
check('too-large', scope / 'big', 2, '0 1 \n')
check('symlink', scope / 'link', 2, '0 1 \n')
check('nested', scope / 'folder' / 'hello', 0, '1 7 hello\n\n')
check('parent-symlink', scope / 'parent-link' / 'hello', 2, '0 1 \n')
check('outside', work / 'outside', 2, '0 1 \n')
(scope / 'binary').write_bytes(bytes([0, 255, 128]))
binary = subprocess.run([str(work / 'binary.elf'), str(scope / 'binary')], env=env,
                        capture_output=True, timeout=10)
if binary.returncode != 0 or binary.stdout or binary.stderr:
    raise ValueError(('exact-binary', binary.returncode, binary.stdout, binary.stderr))
cases.append('exact-binary')
denied = subprocess.run([str(work / 'probe.elf'), str(scope / 'hello')],
                        env=dict(env, KEXE_ALLOW='37,38'), capture_output=True, text=True, timeout=10)
if denied.returncode == 0 or denied.stdout.startswith('1 '):
    raise ValueError(('missing capability was accepted', denied.returncode, denied.stdout, denied.stderr))
cases.append('missing-capability-refused')
(work / 'scoped-read-result.json').write_text(json.dumps({'status': 'PASS', 'cases': cases}, indent=2) + '\n')
