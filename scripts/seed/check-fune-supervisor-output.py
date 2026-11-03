#!/usr/bin/env python3
"""Observe the fixed-fixture supervisor mode in a fresh delegated cgroup.

This is an ARM64 diagnostic, not authenticated OCI admission or a general
container runtime. It creates and removes only its own cgroups and processes.
"""
import argparse
import importlib.util
import json
import os
import platform
from pathlib import Path
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('fune_supervisor', ROOT / 'scripts/seed/check-fune-supervisor.py')
common = importlib.util.module_from_spec(spec); spec.loader.exec_module(common)
FRAME = b'K\x07\x00\x00\x00\x0bfune-smoke\n'


def main(compiler, worker, producer, layout, manifest, zero_layout, zero_manifest, out, bad_worker, max_layout, max_manifest, failed_producer):
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
    assert all(x in (root / 'cgroup.controllers').read_text().split() for x in ('cpu','memory','pids'))
    driver = root / 'fune-output-test-driver'; target = root / 'fune-output-test-target'
    driver.mkdir(); target.mkdir(); observed = {}
    try:
        (driver / 'cgroup.procs').write_text(str(os.getpid()))
        (root / 'cgroup.subtree_control').write_text('+cpu +memory +pids')
        cg = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
        try:
            def configure(pids):
                p = subprocess.run([str(helper)], input=struct.pack('>III', 67108864, pids, 50000),
                                   capture_output=True, pass_fds=(cg,), timeout=20)
                assert p.returncode == 0 and p.stdout == b'K' and not p.stderr, (p.returncode,p.stderr)
            def empty():
                for _ in range(100):
                    if 'populated 0' in (target / 'cgroup.events').read_text(): return
                    time.sleep(.05)
                raise AssertionError('owned test cgroup remained populated')
            def invoke(*, image=worker, verifier=producer, image_layout=layout, digest=manifest, pids=4,
                       memory=67108864, grouped=True, mode='O'):
                wf, pf = common.image_fd(image), common.image_fd(verifier)
                args = [str(supervisor),str(wf),common.digest(image),str(pf),common.digest(verifier),str(image_layout),digest]
                if grouped: args += [str(cg), str(memory), str(pids), '50000']
                if mode is not None: args += [mode]
                try:
                    return subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,
                                          pass_fds=(cg,wf,pf),env={'PATH':'/nonexistent'},timeout=75)
                finally: os.close(wf); os.close(pf)
            def refuses(name, **kw):
                p = invoke(**kw)
                assert p.returncode != 0 and not p.stdout, (name,p.returncode,p.stdout,p.stderr)
                empty(); observed[name] = 'refused'
            configure(4)
            p = invoke()
            assert p.returncode == 0 and p.stdout == FRAME and not p.stderr, (p.returncode,p.stdout,p.stderr)
            empty(); observed['fixed_output'] = 'pass'
            if max_layout is not None:
                penv = {'PATH':'/nonexistent','KEXE_ALLOW':'35,37,38,39','KEXE_COMMAND':'1',
                        'KEXE_FUEL':'100000000000','KEXE_STACK_BYTES':'8388608',
                        'KEXE_CAP_RESOURCES_35':str(max_layout)}
                emitted = subprocess.run([str(producer),str(max_layout),max_manifest],env=penv,capture_output=True,timeout=120)
                assert emitted.returncode == 0 and not emitted.stderr and emitted.stdout.startswith(b'H')
                wire = bytes.fromhex(emitted.stdout[1:].decode('ascii')); pos = count = 0
                while pos < len(wire):
                    op = wire[pos]; pos += 1
                    if op == ord('T'):
                        assert pos + 6 <= len(wire)
                        recorded, size = struct.unpack_from('>HI',wire,pos); pos += 6 + size
                        assert recorded == count and pos == len(wire)
                        break
                    assert op in b'MFUP' and pos + 6 <= len(wire)
                    name, size = struct.unpack_from('>HI',wire,pos); pos += 6 + name
                    if op in b'FU': pos += size
                    assert pos <= len(wire); count += 1
                assert count == 640, count
                maximum = invoke(image_layout=max_layout,digest=max_manifest)
                assert maximum.returncode == 0 and maximum.stdout == FRAME and not maximum.stderr, (maximum.returncode,maximum.stdout,maximum.stderr)
                empty(); observed['fixed_output_640_operations'] = 'pass'
            refuses('no_cgroup', grouped=False)
            refuses('wrong_mode', mode='Q')
            refuses('trailing_mode_bytes', mode='OO')
            refuses('different_limits', memory=67108865)
            refuses('wrong_manifest', digest='sha256:' + '0'*64)
            refuses('wrong_fixture', image_layout=zero_layout, digest=zero_manifest)
            if failed_producer is not None:
                penv = {'PATH':'/nonexistent','KEXE_ALLOW':'35,37,38,39','KEXE_COMMAND':'1',
                        'KEXE_FUEL':'100000000000','KEXE_STACK_BYTES':'8388608',
                        'KEXE_CAP_RESOURCES_35':str(layout)}
                emitted = subprocess.run([str(failed_producer),str(layout),manifest],env=penv,capture_output=True,timeout=120)
                baseline = subprocess.run([str(producer),str(layout),manifest],env=penv,capture_output=True,timeout=120)
                assert baseline.returncode == 0 and not baseline.stderr and baseline.stdout.startswith(b'H')
                assert emitted.returncode != 0 and emitted.stdout == baseline.stdout and len(emitted.stdout) > 300000
                refuses('producer_failure_after_stream', verifier=failed_producer)
            if bad_worker is not None:
                refuses('invalid_worker_frame', image=bad_worker)
            configure(3)
            before = int(dict(x.split() for x in (target / 'pids.events').read_text().splitlines())['max'])
            refuses('pids_limit', pids=3)
            after = int(dict(x.split() for x in (target / 'pids.events').read_text().splitlines())['max'])
            assert after > before, (before,after)
            observed['kernel_pids_event'] = 'increased'
        finally: os.close(cg)
    finally:
        (root / 'cgroup.subtree_control').write_text('-cpu -memory -pids')
        (root / 'cgroup.procs').write_text(str(os.getpid()))
        target.rmdir(); driver.rmdir()
    result = {'status':'PASS_FUNE_SUPERVISOR_FIXED_OUTPUT','observations':observed,
              'sourceMutationRefused':True,'generalExecutionQualified':False,'securityBoundaryQualified':False}
    (out/'supervisor-output.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('compiler','worker','producer','layout','zero-layout','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest',required=True);p.add_argument('--zero-manifest',required=True)
    p.add_argument('--bad-worker',type=Path);p.add_argument('--failed-producer',type=Path)
    p.add_argument('--max-layout',type=Path);p.add_argument('--max-manifest')
    a=p.parse_args();assert bool(a.max_layout) == bool(a.max_manifest)
    main(a.compiler.resolve(),a.worker.resolve(),a.producer.resolve(),a.layout.resolve(),a.manifest,
         a.zero_layout.resolve(),a.zero_manifest,a.output.resolve(),a.bad_worker.resolve() if a.bad_worker else None,
         a.max_layout.resolve() if a.max_layout else None,a.max_manifest,
         a.failed_producer.resolve() if a.failed_producer else None)
