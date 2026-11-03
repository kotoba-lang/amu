#!/usr/bin/env python3
"""Observe the fixed-source ARM64 cgroup configurator in a delegated scope.

Run this observer as a non-root user inside an otherwise unused cgroup-v2
scope delegated to that user. It creates and removes only its own cgroups;
it does not qualify fune workload execution or a security boundary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'seed/fune/cgroup-limits.kotoba'


def pin(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main(compiler, out):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64')
    assert os.geteuid() != 0
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    image = out / 'limits.elf'
    env = {'PATH': '/nonexistent', 'KEXE_ALLOW': '35,37,38,39', 'KEXE_STACK_BYTES': '8388608',
           'KEXE_CAP_RESOURCES_35': f'{ROOT}:{out}'}
    cmd = [str(compiler), 'fune-cgroup-build', 'aarch64-linux', str(SOURCE), str(image)]
    built = subprocess.run(cmd, cwd=out, env=env, capture_output=True, timeout=900)
    assert built.returncode == 0 and image.is_file(), (built.returncode, built.stderr[-1000:])
    image.chmod(0o700)
    altered = out / 'altered.kotoba'
    altered.write_bytes(SOURCE.read_bytes() + b'\n;; altered input\n')
    wrong = out / 'altered.elf'
    refused = subprocess.run([str(compiler), 'fune-cgroup-build', 'aarch64-linux', str(altered), str(wrong)],
                             cwd=out, env=env, capture_output=True, timeout=900)
    assert refused.returncode != 0 and not wrong.exists() and b'E6015' in refused.stderr
    before_image = pin(image)
    existing = subprocess.run(cmd, cwd=out, env=env, capture_output=True, timeout=900)
    assert existing.returncode != 0 and pin(image) == before_image

    cgpath = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1]
    root = Path('/sys/fs/cgroup') / cgpath.lstrip('/')
    assert all(x in (root / 'cgroup.controllers').read_text().split() for x in ('cpu', 'memory', 'pids'))
    # The entire scope belongs to this observer; never use a shared cgroup.
    assert len((root / 'cgroup.procs').read_text().split()) == 1
    driver = root / 'fune-test-driver'
    target = root / 'fune-test-target'
    disabled = root / 'fune-test-disabled'
    incomplete = disabled / 'workload'
    driver.mkdir(); target.mkdir(); disabled.mkdir()
    observations = {}
    try:
        (driver / 'cgroup.procs').write_text(str(os.getpid()))
        (root / 'cgroup.subtree_control').write_text('+cpu +memory +pids')
        incomplete.mkdir()
        (disabled / 'cgroup.subtree_control').write_text('+memory +pids')

        def run(path, payload):
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
            assert fd == 3, f'expected FD 3, got {fd}'
            try:
                p = subprocess.run([str(image)], input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   pass_fds=(fd,), timeout=20, env={'PATH': '/nonexistent'})
                return {'exit': p.returncode, 'stdout': p.stdout.decode(), 'stderr': p.stderr.decode()}
            finally:
                os.close(fd)

        policy = struct.pack('>III', 67108864, 4, 50000)
        observations['ordinaryDir'] = run('/tmp', policy)
        observations['truncated'] = run(target, b'bad')
        observations['invalidMemory'] = run(target, struct.pack('>III', 1048575, 4, 50000))
        observations['invalidPids'] = run(target, struct.pack('>III', 67108864, 0, 50000))
        observations['invalidCpu'] = run(target, struct.pack('>III', 67108864, 4, 999))
        observations['excessPids'] = run(target, struct.pack('>III', 67108864, 4097, 50000))
        observations['excessCpu'] = run(target, struct.pack('>III', 67108864, 4, 1000001))
        missing = subprocess.run([str(image)], input=policy, capture_output=True, timeout=20, env={'PATH': '/nonexistent'})
        observations['missingFd'] = {'exit': missing.returncode, 'stdout': missing.stdout.decode(), 'stderr': missing.stderr.decode()}
        assert (target / 'memory.max').read_text().strip() == 'max'
        assert (target / 'pids.max').read_text().strip() == 'max'
        observations['missingController'] = run(incomplete, policy)
        assert (incomplete / 'memory.max').read_text().strip() == '67108864'
        assert (incomplete / 'pids.max').read_text().strip() == '4'
        observations['configured'] = run(target, policy)
        observations['values'] = {f: (target / f).read_text().strip() for f in ('memory.max', 'pids.max', 'cpu.max')}
        assert observations['configured'] == {'exit': 0, 'stdout': 'K', 'stderr': ''}
        assert observations['values'] == {'memory.max': '67108864', 'pids.max': '4', 'cpu.max': '50000 100000'}
        child = subprocess.Popen(['/bin/sleep', '20'])
        try:
            (target / 'cgroup.procs').write_text(str(child.pid))
            observations['nonempty'] = run(target, policy)
        finally:
            child.kill(); child.wait(timeout=20)
        # A target can have no direct tasks while a descendant is populated.
        # Applying ancestor limits would still affect that descendant.
        descendant = target / 'fune-descendant'
        descendant.mkdir()
        child = subprocess.Popen(['/bin/sleep', '20'])
        try:
            (descendant / 'cgroup.procs').write_text(str(child.pid))
            assert (target / 'cgroup.procs').read_text() == ''
            assert 'populated 1' in (target / 'cgroup.events').read_text()
            observations['populatedDescendant'] = run(target, policy)
        finally:
            child.kill(); child.wait(timeout=20)
            descendant.rmdir()
        for name in ('ordinaryDir', 'truncated', 'invalidMemory', 'invalidPids', 'invalidCpu', 'missingController', 'nonempty', 'populatedDescendant', 'excessPids', 'excessCpu', 'missingFd'):
            assert observations[name]['exit'] == 2 and observations[name]['stdout'] == '', (name, observations[name])

        # The target was configured by the native image. Each independent
        # probe moves only itself into that cgroup, never the observer.
        def in_target(program):
            prefix = "from pathlib import Path; import os; Path(%r).write_text(str(os.getpid()))\n" % str(target / 'cgroup.procs')
            return subprocess.run([sys.executable, '-c', prefix + program], capture_output=True, text=True, timeout=20)
        pids = in_target('''import errno, json, signal, time
children=[]
try:
 for _ in range(5):
  try: pid=os.fork()
  except OSError as e:
   print(json.dumps({'children':len(children),'errno':e.errno}),flush=True); break
  if pid==0: time.sleep(10); os._exit(0)
  children.append(pid)
finally:
 for pid in children: os.kill(pid,signal.SIGKILL); os.waitpid(pid,0)
''')
        assert pids.returncode == 0, (pids.returncode, pids.stderr)
        observations['pidsEnforcement'] = json.loads(pids.stdout)
        assert observations['pidsEnforcement'] == {'children': 3, 'errno': 11}
        before = (target / 'memory.events').read_text()
        memory = in_target('x=bytearray(160*1024*1024)\nprint(len(x))\n')
        after = (target / 'memory.events').read_text()
        def fields(s): return {k: int(v) for k, v in (line.split() for line in s.splitlines())}
        observations['memoryEnforcement'] = {'exit': memory.returncode, 'oomKillsBefore': fields(before)['oom_kill'],
                                             'oomKillsAfter': fields(after)['oom_kill']}
        assert memory.returncode == -9 and fields(after)['oom_kill'] > fields(before)['oom_kill']
        cpu_before = fields((target / 'cpu.stat').read_text())
        cpu = in_target('import time\ns=time.monotonic()\nwhile time.monotonic()-s<2: pass\n')
        cpu_after = fields((target / 'cpu.stat').read_text())
        observations['cpuEnforcement'] = {'exit': cpu.returncode,
            'throttledPeriods': cpu_after['nr_throttled'] - cpu_before['nr_throttled'],
            'throttledUsec': cpu_after['throttled_usec'] - cpu_before['throttled_usec']}
        assert cpu.returncode == 0 and observations['cpuEnforcement']['throttledPeriods'] > 0
    finally:
        # Never remove or alter cgroups other than these newly created names.
        if incomplete.exists(): incomplete.rmdir()
        if disabled.exists():
            (disabled / 'cgroup.subtree_control').write_text('-memory -pids')
            disabled.rmdir()
        (root / 'cgroup.subtree_control').write_text('-cpu -memory -pids')
        (root / 'cgroup.procs').write_text(str(os.getpid()))
        target.rmdir(); driver.rmdir()
    report = {'source': pin(SOURCE), 'compiler': pin(compiler), 'image': pin(image),
              'sourceMutationRefused': True, 'existingOutputRefused': True, 'observations': observations}
    (out / 'cgroup-limits.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print('PASS_FUNE_CGROUP_LIMITS_CANDIDATE')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
