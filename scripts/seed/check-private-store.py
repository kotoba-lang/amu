#!/usr/bin/env python3
"""Linux native private-store diagnostics. Python orchestrates and hashes only.
Explicit selfhost compiler required; no hosted compiler/crypto/key fixture.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
binary = p.add_mutually_exclusive_group(required=True)
binary.add_argument('--compiler', type=Path)
binary.add_argument('--probe', type=Path, help='already cross-compiled probe; execution qualification only')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'x86_64')
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
private = out / 'private'
private.mkdir(mode=0o700)
probe = out / 'probe.elf'
env = dict(os.environ, KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out))
source = REPO / 'seed/tests/private-store/probe.kotoba'
compile_env = dict(env, KEXE_CAP_RESOURCES_35=f'{out}:{REPO}')
build = subprocess.run([str(a.compiler.resolve()), 'compile', str(source), '--target',
                       'aarch64-linux' if platform.machine() == 'aarch64' else 'x86_64-linux',
                       '--output', str(probe), '--format', 'static'], env=compile_env, capture_output=True, text=True) if a.compiler else None
if build:
    assert build.returncode == 0 and not build.stderr, build
else:
    shutil.copyfile(a.probe, probe)
probe.chmod(0o755)
cases = []

def run(op, path, *args, runtime_env=None):
    return subprocess.run([str(probe), op, str(path), *args], env=runtime_env or env,
                          capture_output=True, text=True, timeout=20)

def check(name, op, path, args=(), status=0, stdout=None):
    r = run(op, path, *args)
    assert r.returncode == status and not r.stderr and (stdout is None or r.stdout == stdout), (name, r)
    cases.append(dict(case=name, exit=r.returncode, passed=True))

f = private / 'journal'
check('exclusive create', 'C', f, ('first\n',), stdout='1 1 \n')
check('read same owner 0600 in 0700 directory', 'R', f, stdout='1 7 first\n\n')
assert (f.stat().st_mode & 0o7777) == 0o600
check('existing file never truncated', 'C', f, ('wrong',), status=2)
assert f.read_text() == 'first\n'
check('compare append and fsync', 'A', f, ('first\n', 'second\n'))
check('stale comparison refused', 'A', f, ('first\n', 'replay\n'), status=2)
assert f.read_text() == 'first\nsecond\n'
check('unsupported operation refused', 'X', f, status=2)
f.chmod(0o644)
check('public file refused', 'R', f, status=2)
check('public file not appended', 'A', f, ('first\nsecond\n', 'bad\n'), status=2)
f.chmod(0o600)
link = private / 'hardlink'
os.link(f, link)
check('hardlink read refused', 'R', f, status=2)
check('hardlink append refused', 'A', f, ('first\nsecond\n', 'bad\n'), status=2)
link.unlink()
link.symlink_to(f)
check('final symlink refused', 'R', link, status=2)
check('final symlink create refused', 'C', link, ('bad',), status=2)
parent_link = out / 'parent-link'
parent_link.symlink_to(private, target_is_directory=True)
check('parent symlink refused', 'R', parent_link / 'journal', status=2)
private.chmod(0o755)
check('public parent refused', 'R', f, status=2)
check('public parent create refused', 'C', private / 'no-create', ('bad',), status=2)
private.chmod(0o700)
check('outside scope refused', 'R', out.parent / 'not-in-scope', status=2)
content = 'WRITE_SEP RENAME_SEP FSYNC_SEP\n'
check('private payload cannot invoke text tokens', 'C', private / 'tokens', (content,))
assert (private / 'tokens').read_text() == content
old = f.read_text()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    raced = list(pool.map(lambda i: run('A', f, old, f'writer-{i}\n'), range(8)))
assert sum(r.returncode == 0 for r in raced) == 1 and all(r.returncode in (0, 2) for r in raced), raced
assert len(f.read_text().splitlines()) == 3
cases.append(dict(case='eight concurrent CAS writers: one success', passed=True))
refused = run('R', f, runtime_env=dict(env, KEXE_ALLOW='37,38,39'))
assert refused.returncode == 120, refused
cases.append(dict(case='missing wire grant traps', exit=120, passed=True))
receipt = dict(schema='amu.native.private-store.gate.v1', host=platform.machine(),
               compilerSha256=hashlib.sha256(a.compiler.read_bytes()).hexdigest() if a.compiler else None,
               crossCompiledProbe=bool(a.probe),
               probeSha256=hashlib.sha256(probe.read_bytes()).hexdigest(), cases=cases,
               count=len(cases), passed=True, cdciQualified=False,
               note='Process/fsync/atomic-comparison diagnostics, not a power-loss experiment or independent custody qualification')
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
