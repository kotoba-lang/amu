#!/usr/bin/env python3
"""Exercise delegated-cgroup attachment before supervisor worker exec.

Run in a fresh delegated ARM64 Linux user scope. This observer creates and
removes only its own cgroups and processes; it does not launch a workload.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('supervisor_observer', ROOT / 'scripts/seed/check-fune-supervisor.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def main(compiler, worker, producer, slow, layouts, runnable, runnable_layouts, runnable_digests, limit_layout, limit_digest, out):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64') and os.geteuid() != 0
    supervisor = common.build_candidate(compiler, out)
    helper = out / 'cgroup-limits.elf'
    env = {'PATH': '/nonexistent', 'KEXE_ALLOW': '35,37,38,39', 'KEXE_STACK_BYTES': '8388608',
           'KEXE_CAP_RESOURCES_35': f'{ROOT}:{out}'}
    built = subprocess.run([str(compiler), 'fune-cgroup-build', 'aarch64-linux',
                            str(ROOT / 'seed/fune/cgroup-limits.kotoba'), str(helper)],
                           cwd=out, env=env, capture_output=True, timeout=900)
    assert built.returncode == 0 and helper.is_file(), (built.returncode, built.stderr)
    helper.chmod(0o700)
    cgpath = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1]
    root = Path('/sys/fs/cgroup') / cgpath.lstrip('/')
    assert len((root / 'cgroup.procs').read_text().split()) == 1
    assert all(x in (root / 'cgroup.controllers').read_text().split() for x in ('cpu', 'memory', 'pids'))
    driver = root / 'fune-supervisor-test-driver'
    target = root / 'fune-supervisor-test-target'
    driver.mkdir(); target.mkdir()
    observations = {}
    try:
        (driver / 'cgroup.procs').write_text(str(os.getpid()))
        (root / 'cgroup.subtree_control').write_text('+cpu +memory +pids')
        cg = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
        assert cg == 3, cg
        try:
            def configure(pids):
                data = struct.pack('>III', 67108864, pids, 50000)
                p = subprocess.run([str(helper)], input=data, capture_output=True, pass_fds=(cg,), timeout=20)
                assert p.returncode == 0 and p.stdout == b'K' and not p.stderr, (p.returncode, p.stderr)

            def command(image, cgfd, memory=67108864, pids=4, cpu=50000, layout=None, manifest=None):
                wf, pf = common.image_fd(worker), common.image_fd(image)
                argv = [str(supervisor), str(wf), common.digest(worker), str(pf), common.digest(image),
                        str(layout or layouts / 'plan-binary'), manifest or common.DIGEST, str(cgfd), str(memory), str(pids), str(cpu)]
                return argv, wf, pf

            def run(image, cgfd=cg, memory=67108864, pids=4, cpu=50000, layout=None, manifest=None):
                argv, wf, pf = command(image, cgfd, memory, pids, cpu, layout, manifest)
                try:
                    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                          pass_fds=(cgfd, wf, pf), env={'PATH':'/nonexistent'}, timeout=75)
                finally:
                    os.close(wf); os.close(pf)

            def empty():
                for _ in range(100):
                    if 'populated 0' in (target / 'cgroup.events').read_text(): return
                    time.sleep(.05)
                raise AssertionError('owned test cgroup remained populated')

            configure(4)
            p = run(producer)
            assert p.returncode == 0 and p.stdout == b'fune-supervisor-ok\n' and not p.stderr, (p.returncode,p.stdout,p.stderr)
            empty(); observations['configured_run'] = 'pass'
            digests = json.loads(runnable_digests.read_text())
            p = run(runnable, layout=runnable_layouts / 'good', manifest=digests['good'])
            assert p.returncode == 0 and p.stdout == b'fune-supervisor-ok\n' and not p.stderr, (p.returncode,p.stdout,p.stderr)
            empty(); observations['configured_runnable_stream'] = 'pass'
            p = run(producer, layout=limit_layout, manifest=limit_digest)
            assert p.returncode == 0 and p.stdout == b'fune-supervisor-ok\n' and not p.stderr, (p.returncode,p.stdout,p.stderr)
            empty(); observations['configured_640_operation_stream'] = 'pass'
            p = run(runnable, layout=runnable_layouts / 'noexec', manifest=digests['noexec'])
            assert p.returncode != 0 and not p.stdout
            empty(); observations['runnable_noexec'] = 'refused'
            for name, memory, pids, cpu in (('memory',67108865,4,50000), ('pids',67108864,5,50000),
                                            ('cpu',67108864,4,50001)):
                p = run(producer, memory=memory, pids=pids, cpu=cpu)
                assert p.returncode != 0 and not p.stdout, (name,p.returncode,p.stdout,p.stderr)
                empty(); observations['mismatch_' + name] = 'refused'
            tmp = os.open('/tmp', os.O_RDONLY | os.O_DIRECTORY)
            try:
                p = run(producer, cgfd=tmp)
                assert p.returncode != 0 and not p.stdout
                empty(); observations['ordinary_dir'] = 'refused'
            finally: os.close(tmp)
            foreign = os.open('/sys/fs/cgroup', os.O_RDONLY | os.O_DIRECTORY)
            try:
                assert os.fstat(foreign).st_uid != os.geteuid()
                p = run(producer, cgfd=foreign)
                assert p.returncode != 0 and not p.stdout
                empty(); observations['foreign_owner'] = 'refused'
            finally: os.close(foreign)
            for name, memory, pids, cpu in (('memory',1048575,4,50000), ('pids',67108864,0,50000),
                                            ('cpu',67108864,4,999)):
                p = run(producer, memory=memory, pids=pids, cpu=cpu)
                assert p.returncode != 0 and not p.stdout
                empty(); observations['invalid_' + name] = 'refused'

            # Missing a delegated controller must not fall back to an
            # unrestricted worker or attach anything to that subtree.
            partial = root / 'fune-supervisor-missing-controller'
            missing = partial / 'workload'
            partial.mkdir(); missing.mkdir()
            try:
                (partial / 'cgroup.subtree_control').write_text('+memory +pids')
                (missing / 'memory.max').write_text('67108864')
                (missing / 'pids.max').write_text('4')
                assert not (missing / 'cpu.max').exists()
                missing_fd = os.open(missing, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    p = run(producer, cgfd=missing_fd)
                    assert p.returncode != 0 and not p.stdout
                    assert 'populated 0' in (missing / 'cgroup.events').read_text()
                    observations['missing_controller'] = 'refused'
                finally: os.close(missing_fd)
            finally:
                missing.rmdir()
                (partial / 'cgroup.subtree_control').write_text('-memory -pids')
                partial.rmdir()

            # An existing process in the target must cause refusal without
            # killing it or moving the observer into that cgroup.
            occupied = subprocess.Popen(['/bin/sleep', '20'])
            try:
                (target / 'cgroup.procs').write_text(str(occupied.pid))
                p = run(producer)
                assert p.returncode != 0 and not p.stdout and occupied.poll() is None
                assert (target / 'cgroup.procs').read_text().split() == [str(occupied.pid)]
                observations['populated_target'] = 'refused-without-killing-occupant'
            finally:
                occupied.kill(); occupied.wait(timeout=20)
            empty()

            # Inspect actual processes while a trusted slow producer holds the
            # pipe open. The observer and producer remain outside the target.
            argv, wf, pf = command(slow, cg)
            p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 pass_fds=(cg,wf,pf), env={'PATH':'/nonexistent'})
            try:
                members, children = [], []
                for _ in range(200):
                    if p.poll() is not None: break
                    members = (target / 'cgroup.procs').read_text().split()
                    children = Path(f'/proc/{p.pid}/task/{p.pid}/children').read_text().split()
                    if len(members) == 2 and len(children) == 2: break
                    time.sleep(.05)
                assert len(members) == 2, (members,p.poll())
                assert str(os.getpid()) not in members and str(p.pid) not in members
                assert len(children) == 2, children
                worker_parent = list(set(children).intersection(members))
                assert len(worker_parent) == 1, (children,members)
                # The cgroup directory was used before exec and must not leak
                # into the worker's post-exec descriptor table.
                targets = []
                for entry in Path(f'/proc/{worker_parent[0]}/fd').iterdir():
                    try: targets.append(os.readlink(entry))
                    except FileNotFoundError: pass
                assert str(target) not in targets, targets
                observations['cgroup_fd_after_exec'] = 'closed'
                for member in members:
                    assert str(target).removeprefix('/sys/fs/cgroup') in Path(f'/proc/{member}/cgroup').read_text()
                assert (target / 'pids.max').read_text().strip() == '4'
                charged = int((target / 'memory.current').read_text().strip())
                assert charged > 0, "worker memory was not charged to its cgroup"
                observations['worker_tree_members'] = len(members)
                observations['worker_memory_current'] = charged
            finally:
                if p.poll() is None: p.kill()
                p.communicate(timeout=20); os.close(wf); os.close(pf)
            empty(); observations['killed_supervisor_cleanup'] = 'observed-empty'

            # With room for only one process, the supervisor child can enter,
            # but the worker cannot fork its own child. Check kernel pids.events.
            configure(1)
            before = dict(line.split() for line in (target / 'pids.events').read_text().splitlines())
            p = run(producer, pids=1)
            after = dict(line.split() for line in (target / 'pids.events').read_text().splitlines())
            assert p.returncode != 0 and not p.stdout, (p.returncode,p.stdout,p.stderr)
            assert int(after['max']) > int(before['max']), (before,after,p.stderr)
            empty(); observations['pids_enforced'] = 'refused-and-counted'
        finally: os.close(cg)
    finally:
        (root / 'cgroup.subtree_control').write_text('-cpu -memory -pids')
        (root / 'cgroup.procs').write_text(str(os.getpid()))
        target.rmdir(); driver.rmdir()
    report = {'status':'PASS_FUNE_CGROUP_SUPERVISOR_CANDIDATE','supervisor':common.digest(supervisor),
              'worker':common.digest(worker),'observations':observations,
              'sourceMutationRefused':True,'workloadExecutionQualified':False,'securityBoundaryQualified':False}
    (out / 'cgroup-supervisor.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(report['status'],flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--worker',type=Path,required=True)
    p.add_argument('--producer',type=Path,required=True);p.add_argument('--slow-producer',type=Path,required=True)
    p.add_argument('--layouts',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--runnable-producer',type=Path,required=True);p.add_argument('--runnable-layouts',type=Path,required=True)
    p.add_argument('--runnable-digests',type=Path,required=True)
    p.add_argument('--limit-layout',type=Path,required=True);p.add_argument('--limit-digest',required=True)
    a=p.parse_args();main(a.compiler.resolve(),a.worker.resolve(),a.producer.resolve(),a.slow_producer.resolve(),a.layouts.resolve(),
                          a.runnable_producer.resolve(),a.runnable_layouts.resolve(),a.runnable_digests.resolve(),
                          a.limit_layout.resolve(),a.limit_digest,a.output.resolve())
