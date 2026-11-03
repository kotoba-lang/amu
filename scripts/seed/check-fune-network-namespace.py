#!/usr/bin/env python3
"""Observe task-owned ARM64 workers' network views; not an escape test.

The negative-control image must be a separately built worker that omits
CLONE_NEWNET. This observer never changes host networking or joins a namespace.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
from pathlib import Path
import select
import subprocess


class Filter(ctypes.Structure):
    _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]


class Program(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]


def deny_network_unshare():
    # The worker unshares mount and network together after its user mapping.
    code = (Filter * 6)(Filter(0x20, 0, 0, 0), Filter(0x15, 0, 3, 97),
                        Filter(0x20, 0, 0, 16), Filter(0x15, 0, 1, 1073872896),
                        Filter(0x06, 0, 0, 0x00050001), Filter(0x06, 0, 0, 0x7fff0000))
    program = Program(len(code), code)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        os._exit(125)


def network_view(pid):
    base = Path('/proc') / str(pid) / 'net'
    interfaces = sorted(line.split(':', 1)[0].strip()
                        for line in (base / 'dev').read_text().splitlines()[2:] if ':' in line)
    routes = [line.split() for line in (base / 'route').read_text().splitlines()
              if line.strip() and not line.startswith('Iface')]
    ipv6 = [line.split() for line in (base / 'if_inet6').read_text().splitlines() if line.strip()]
    return {'interfaces': interfaces, 'ipv4Routes': routes, 'ipv6Addresses': ipv6}


def observe(image):
    proc = subprocess.Popen([str(image)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={'PATH': '/nonexistent'})
    try:
        ready, _, _ = select.select([proc.stdout], [], [], 20)
        assert ready and proc.stdout.readline() == b'fune-private-root-ready\n', 'worker not ready'
        mapper = Path(f'/proc/{proc.pid}/task/{proc.pid}/children').read_text().split()
        assert len(mapper) == 1
        init = Path(f'/proc/{mapper[0]}/task/{mapper[0]}/children').read_text().split()
        assert len(init) == 1
        return network_view(init[0])
    finally:
        if proc.poll() is None:
            try:
                proc.stdin.write(b'X')
                proc.stdin.flush()
                proc.communicate(timeout=20)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                proc.kill()
                proc.communicate(timeout=20)


def main(worker, mutant, output):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64') and os.geteuid() != 0
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(worker) != digest(mutant), 'negative control must differ'
    host = network_view('self')
    assert any(x != 'lo' for x in host['interfaces']) and host['ipv4Routes'], 'host must expose an active comparison route'
    isolated = observe(worker)
    assert isolated['interfaces'] == ['lo'] and not isolated['ipv4Routes'] and not isolated['ipv6Addresses'], isolated
    control = observe(mutant)
    assert control == host, ('negative control did not expose host network view', control, host)
    denied = subprocess.run([str(worker)], input=b'X', capture_output=True, timeout=20,
                            env={'PATH': '/nonexistent'}, preexec_fn=deny_network_unshare)
    assert denied.returncode == 2 and not denied.stdout and b'FREFUSE:9' in denied.stderr
    result = {'status': 'PASS_FUNE_NETWORK_NAMESPACE_OBSERVATION', 'workerSHA256': digest(worker),
              'negativeControlSHA256': digest(mutant), 'host': host, 'worker': isolated,
              'mutantMatchedHost': True, 'networkUnshareDeniedBeforeReady': True,
              'arbitraryWorkloadIsolationQualified': False, 'escapeResistanceQualified': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(result['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--negative-control', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.worker.resolve(), args.negative_control.resolve(), args.output.resolve())
