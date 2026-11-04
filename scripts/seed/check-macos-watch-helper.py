#!/usr/bin/env python3
"""Stage and observe the experimental native watcher on an owned child.

This is a kernel/ABI fixture, not a process supervisor or governor.
The compiler and emitted watcher execute natively; Python only stages,
queries identity and observes their outputs.
"""
import ctypes
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/seed' / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def identity(pid):
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                 ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int
    raw = ctypes.create_string_buffer(136)
    got = lib.proc_pidinfo(pid, 3, 0, raw, len(raw))
    if got != 136:
        raise RuntimeError(('proc_pidinfo', got, ctypes.get_errno()))
    observed = struct.unpack_from('<I', raw.raw, 12)[0]
    sec, usec = struct.unpack_from('<QQ', raw.raw, 120)
    if observed != pid or not sec or usec > 999999:
        raise RuntimeError('invalid process identity')
    return sec, usec


def observe(image, directory, request):
    path = directory / 'request.bin'
    path.write_bytes(request)
    fd = os.open(path, os.O_RDONLY)
    saved = None
    relocated = fd != 3
    try:
        if relocated:
            try:
                saved = os.dup(3)
            except OSError:
                pass
            os.dup2(fd, 3)
        return subprocess.run([str(image)], cwd=directory, pass_fds=(3,),
                              capture_output=True, timeout=10, check=False)
    finally:
        if relocated:
            if saved is None:
                os.close(3)
            else:
                os.dup2(saved, 3)
                os.close(saved)
        os.close(fd)


def launch_watcher(image, directory, request):
    path = directory / 'transition-request.bin'
    path.write_bytes(request)
    fd = os.open(path, os.O_RDONLY)
    saved = None
    relocated = fd != 3
    try:
        if relocated:
            try:
                saved = os.dup(3)
            except OSError:
                pass
            os.dup2(fd, 3)
        return subprocess.Popen([str(image)], cwd=directory, pass_fds=(3,),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        if relocated:
            if saved is None:
                os.close(3)
            else:
                os.dup2(saved, 3)
                os.close(saved)
        os.close(fd)


def heartbeat_frames(data, request, minimum=1, start=1):
    if len(data) % 40 or len(data) // 40 < minimum:
        raise RuntimeError('missing or partial heartbeat')
    for index in range(len(data) // 40):
        expected = b'WH01' + struct.pack('<I', index + start) + request
        if data[index * 40:(index + 1) * 40] != expected:
            raise RuntimeError('malformed or out-of-order heartbeat')


def transition_case(image, directory, mode, protocol=b'WP01'):
    if mode == 'exec':
        action = "os.execv('/bin/sleep',['sleep','2'])"
    elif mode == 'fork':
        action = "p=os.fork(); (os._exit(0) if p==0 else os.waitpid(p,0)); time.sleep(2)"
    else:
        raise ValueError('unknown transition')
    code = "import os,sys,time; print('READY',flush=True); sys.stdin.buffer.read(1); " + action
    child = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    watcher = None
    try:
        import select
        if not select.select([child.stdout], [], [], 5)[0] or child.stdout.readline() != b'READY\n':
            raise RuntimeError((mode, 'child not ready'))
        os.kill(child.pid, signal.SIGSTOP)
        deadline = time.monotonic() + 5
        while True:
            got, status = os.waitpid(child.pid, os.WUNTRACED | os.WNOHANG)
            if got:
                if not os.WIFSTOPPED(status):
                    child.returncode = os.waitstatus_to_exitcode(status)
                    raise RuntimeError((mode, 'child exited before registration', status))
                break
            if time.monotonic() >= deadline:
                raise TimeoutError((mode, 'child did not stop'))
            time.sleep(0.01)
        sec, usec = identity(child.pid)
        request = struct.pack('<4sIQQII', protocol, child.pid, sec, usec, 12345, 1)
        watcher = launch_watcher(image, directory, request)
        ready = b''
        deadline = time.monotonic() + 5
        while len(ready) < 40:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([watcher.stdout], [], [], remaining)[0]:
                raise RuntimeError((mode, 'watcher ready timeout'))
            chunk = os.read(watcher.stdout.fileno(), 40 - len(ready))
            if not chunk:
                raise RuntimeError((mode, 'short ready frame'))
            ready += chunk
        if ready != b'WR01\0\0\0\0' + request:
            raise RuntimeError((mode, 'invalid ready frame', ready))
        if protocol in (b'WP02', b'WP04'):
            time.sleep(2.2)
        if watcher.poll() is not None:
            raise RuntimeError((mode, 'watcher exited before trigger'))
        os.kill(child.pid, signal.SIGCONT)
        child.stdin.write(b'x')
        child.stdin.flush()
        out, err = watcher.communicate(timeout=7)
        if protocol in (b'WP02', b'WP04'):
            heartbeat_frames(out, request)
        if watcher.returncode != 1 or (protocol in (b'WP01', b'WP03') and out) or err:
            raise RuntimeError((mode, 'transition was not cleanly refused', watcher.returncode, out, err))
        if child.wait(timeout=5) != 0:
            raise RuntimeError((mode, 'child failed'))
        print('WATCH_TRANSITION_REFUSED', protocol.decode(), mode, flush=True)
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.kill()
            watcher.wait(timeout=3)
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)


def persistent_case(image, directory, protocol=b'WP02'):
    import select
    child = subprocess.Popen(['/bin/sleep', '5'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    watcher = None
    try:
        sec, usec = identity(child.pid)
        request = struct.pack('<4sIQQII', protocol, child.pid, sec, usec, 12345, 1)
        watcher = launch_watcher(image, directory, request)
        ready = b''
        deadline = time.monotonic() + 5
        while len(ready) < 40:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([watcher.stdout], [], [], remaining)[0]:
                raise RuntimeError('persistent watcher not ready')
            chunk = os.read(watcher.stdout.fileno(), 40 - len(ready))
            if not chunk:
                raise RuntimeError('persistent watcher short ready frame')
            ready += chunk
        if ready != b'WR01\0\0\0\0' + request:
            raise RuntimeError(('persistent ready mismatch', ready))
        seen = b''
        deadline = time.monotonic() + 3.5
        while len(seen) < 80:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([watcher.stdout], [], [], remaining)[0]:
                raise RuntimeError('persistent heartbeat timeout')
            chunk = os.read(watcher.stdout.fileno(), 80 - len(seen))
            if not chunk:
                raise RuntimeError('persistent watcher did not survive multiple intervals')
            seen += chunk
        heartbeat_frames(seen, request, minimum=2)
        if watcher.poll() is not None or child.poll() is not None:
            raise RuntimeError('persistent watcher did not survive multiple intervals')
        out, err = watcher.communicate(timeout=5)
        final = (b'WS01' if protocol == b'WP04' else b'WO01') + b'\0\0\0\0' + request
        if watcher.returncode != 0 or not out.endswith(final) or err:
            raise RuntimeError(('persistent event mismatch', watcher.returncode, out, err))
        heartbeat_frames(out[:-40], request, minimum=0, start=3)
        if child.wait(timeout=2) != 0:
            raise RuntimeError('persistent child did not exit normally')
        print('WATCH_PERSISTENT_EVENT_AFTER_TIMEOUTS', flush=True)
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.kill(); watcher.wait(timeout=3)
        if child.poll() is None:
            child.kill(); child.wait(timeout=3)


def status_case(image, directory, mode, protocol=b'WP03'):
    """Observe an owned child's raw exit status, not a reservation release."""
    import select
    code = "import os,sys; print('READY',flush=True); os.read(0,1); sys.exit(" + ('7' if mode == 'seven' else '0') + ")"
    child = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    watcher = None
    try:
        if not select.select([child.stdout], [], [], 4)[0] or child.stdout.readline() != b'READY\n':
            raise RuntimeError((mode, 'child not ready'))
        sec, usec = identity(child.pid)
        request = struct.pack('<4sIQQII', protocol, child.pid, sec, usec, 12345, 4)
        watcher = launch_watcher(image, directory, request)
        ready = b''
        deadline = time.monotonic() + 4
        while len(ready) < 40:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([watcher.stdout], [], [], remaining)[0]:
                raise RuntimeError((mode, 'watcher ready timeout'))
            part = os.read(watcher.stdout.fileno(), 40 - len(ready))
            if not part:
                raise RuntimeError((mode, 'watcher ready EOF'))
            ready += part
        if ready != b'WR01\0\0\0\0' + request or watcher.poll() is not None:
            raise RuntimeError((mode, 'invalid ready'))
        if mode == 'signal':
            os.kill(child.pid, signal.SIGKILL)
        else:
            child.stdin.write(b'x'); child.stdin.flush()
        output, err = watcher.communicate(timeout=5)
        pid, status = os.waitpid(child.pid, 0)
        child.returncode = os.waitstatus_to_exitcode(status)
        if pid != child.pid or watcher.returncode or err or output != b'WS01' + struct.pack('<I', status) + request:
            raise RuntimeError((mode, 'status mismatch', status, watcher.returncode, output, err))
        expected = {'zero': 0, 'seven': 7 << 8, 'signal': signal.SIGKILL}[mode]
        if status != expected:
            raise RuntimeError((mode, 'unexpected child status', status))
        print('WATCH_STATUS', mode, status, flush=True)
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.kill(); watcher.wait(timeout=3)
        if child.returncode is None:
            try: child.kill(); child.wait(timeout=3)
            except ProcessLookupError: pass


def run(compiler, packager, output, artifact_dir=None):
    gate = load('mac_native_watcher', 'check-aiueos-user-macos-native.py')
    fixture = load('mac_scope_watcher', 'check-macos-arena-scope.py')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    source = ROOT / 'seed/macos-process-watch-packager.kotoba'
    emitter = fixture.build(gate, compiler, packager, output, 'watch-emitter', source)
    gate.native_run(emitter, output, 'watch-unsigned.macho', timeout=120)
    unsigned = output / 'watch-unsigned.macho'
    image = output / 'watch.macho'
    image.write_bytes(unsigned.read_bytes())
    image.chmod(0o700)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(image)],
                   capture_output=True, check=True, timeout=30)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(image)],
                   capture_output=True, check=True, timeout=30)
    pins = {}
    for name, path in (('source', source), ('compiler', compiler), ('packager', packager),
                       ('emitter', emitter), ('watcher-unsigned', unsigned), ('watcher-signed', image)):
        pins[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(name, 'sha256', pins[name], flush=True)
    print('host', platform.system(), platform.machine(), platform.release(), flush=True)
    child = subprocess.Popen(['/bin/sleep', '8'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        sec, usec = identity(child.pid)
        request = struct.pack('<4sIQQII', b'WP01', child.pid, sec, usec, 12345, 8)
        wrong = struct.pack('<4sIQQII', b'WP01', child.pid, sec + 1, usec, 12345, 8)
        for malformed in (struct.pack('<4sIQQII', b'WP05', child.pid, sec, usec, 12345, 1),
                          struct.pack('<4sIQQII', b'WP02', child.pid, sec, usec, 12345, 0)):
            refused = observe(image, output, malformed)
            if refused.returncode != 1 or refused.stdout or refused.stderr or child.poll() is not None:
                raise RuntimeError(('invalid request did not refuse', refused.returncode, refused.stdout, refused.stderr))
        refused = observe(image, output, wrong)
        if refused.returncode != 1 or refused.stdout or refused.stderr or child.poll() is not None:
            raise RuntimeError(('wrong identity did not cleanly refuse', refused.returncode,
                                refused.stdout, refused.stderr, child.poll()))
        timeout_request = struct.pack('<4sIQQII', b'WP01', child.pid, sec, usec, 12345, 1)
        timed = observe(image, output, timeout_request)
        if timed.returncode != 1 or timed.stdout != b'WR01\0\0\0\0' + timeout_request or timed.stderr or child.poll() is not None:
            raise RuntimeError(('watch timeout did not cleanly refuse', timed.returncode,
                                timed.stdout, timed.stderr, child.poll()))
        status_timeout = struct.pack('<4sIQQII', b'WP03', child.pid, sec, usec, 12345, 1)
        timed_status = observe(image, output, status_timeout)
        if timed_status.returncode != 1 or timed_status.stdout != b'WR01\0\0\0\0' + status_timeout or timed_status.stderr or child.poll() is not None:
            raise RuntimeError(('status timeout did not cleanly refuse', timed_status.returncode,
                                timed_status.stdout, timed_status.stderr, child.poll()))
        result = observe(image, output, request)
        if result.returncode != 0 or result.stdout != b'WR01\0\0\0\0' + request + b'WO01\0\0\0\0' + request or result.stderr:
            raise RuntimeError(('watch failed', result.returncode, result.stdout, result.stderr))
        if child.wait(timeout=2) != 0:
            raise RuntimeError('owned child did not exit normally')
        reaped = observe(image, output, request)
        if reaped.returncode != 1 or reaped.stdout or reaped.stderr:
            raise RuntimeError(('reaped child did not cleanly refuse', reaped.returncode,
                                reaped.stdout, reaped.stderr))
        transition_case(image, output, 'exec')
        transition_case(image, output, 'fork')
        persistent_case(image, output)
        transition_case(image, output, 'exec', b'WP02')
        transition_case(image, output, 'fork', b'WP02')
        for mode in ('zero', 'seven', 'signal'):
            status_case(image, output, mode)
            status_case(image, output, mode, b'WP04')
        transition_case(image, output, 'exec', b'WP03')
        transition_case(image, output, 'fork', b'WP03')
        transition_case(image, output, 'exec', b'WP04')
        transition_case(image, output, 'fork', b'WP04')
        persistent_case(image, output, b'WP04')
        anchor = '(ds-imm 10 1) (ds-and 9 25 10) (ds-cmpi 9 1) (ds-b 0x54000001 9)'
        text = source.read_text()
        if text.count(anchor) != 1:
            raise RuntimeError('persistent negative-control anchor changed')
        mutant_source = text.replace(anchor, '(ds-cmpi 25 0) (ds-b 0x54000001 9)')
        mutant_emitter = fixture.build(gate, compiler, packager, output, 'watch-mutant-emitter', mutant_source)
        gate.native_run(mutant_emitter, output, 'watch-mutant-unsigned.macho', timeout=120)
        mutant = output / 'watch-mutant.macho'
        shutil.copyfile(output / 'watch-mutant-unsigned.macho', mutant)
        mutant.chmod(0o700)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(mutant)],
                       capture_output=True, check=True, timeout=30)
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(mutant)],
                       capture_output=True, check=True, timeout=30)
        try:
            persistent_case(mutant, output)
        except RuntimeError as error:
            if str(error) != 'persistent watcher did not survive multiple intervals':
                raise
        else:
            raise RuntimeError('persistent negative control unexpectedly passed')
        try:
            persistent_case(mutant, output, b'WP04')
        except RuntimeError as error:
            if str(error) != 'persistent watcher did not survive multiple intervals':
                raise
        else:
            raise RuntimeError('WP04 persistent negative control unexpectedly passed')
        print('WATCH_PERSISTENT_MUTANT_REFUSED', flush=True)
        heartbeat_anchor = '(ds-imm 8 825247831)'
        if text.count(heartbeat_anchor) != 1:
            raise RuntimeError('heartbeat negative-control anchor changed')
        bad_source = text.replace(heartbeat_anchor, '(ds-imm 8 825247830)')
        bad_emitter = fixture.build(gate, compiler, packager, output, 'heartbeat-mutant-emitter', bad_source)
        gate.native_run(bad_emitter, output, 'heartbeat-mutant-unsigned.macho', timeout=120)
        bad = output / 'heartbeat-mutant.macho'
        shutil.copyfile(output / 'heartbeat-mutant-unsigned.macho', bad)
        bad.chmod(0o700)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(bad)],
                       capture_output=True, check=True, timeout=30)
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(bad)],
                       capture_output=True, check=True, timeout=30)
        try:
            persistent_case(bad, output)
        except RuntimeError as error:
            if str(error) != 'malformed or out-of-order heartbeat':
                raise
        else:
            raise RuntimeError('heartbeat negative control unexpectedly passed')
        print('WATCH_HEARTBEAT_MUTANT_REFUSED', flush=True)
        status_anchor = '(ds-imm 8 3825205248)'
        if text.count(status_anchor) != 1:
            raise RuntimeError('status registration negative-control anchor changed')
        no_status = text.replace(status_anchor, '(ds-imm 8 3758096384)')
        status_emitter = fixture.build(gate, compiler, packager, output, 'status-mutant-emitter', no_status)
        gate.native_run(status_emitter, output, 'status-mutant-unsigned.macho', timeout=120)
        status_mutant = output / 'status-mutant.macho'
        shutil.copyfile(output / 'status-mutant-unsigned.macho', status_mutant)
        status_mutant.chmod(0o700)
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(status_mutant)],
                       capture_output=True, check=True, timeout=30)
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(status_mutant)],
                       capture_output=True, check=True, timeout=30)
        try:
            status_case(status_mutant, output, 'zero')
        except RuntimeError as error:
            if error.args != (('zero', 'status mismatch', 0, 1, b'', b''),):
                raise
        else:
            raise RuntimeError('missing-status negative control unexpectedly passed')
        try:
            status_case(status_mutant, output, 'zero', b'WP04')
        except RuntimeError as error:
            if error.args != (('zero', 'status mismatch', 0, 1, b'', b''),):
                raise
        else:
            raise RuntimeError('WP04 missing-status negative control unexpectedly passed')
        print('WATCH_MISSING_STATUS_MUTANT_REFUSED', flush=True)
        if artifact_dir is not None:
            artifact_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
            shutil.copyfile(image, artifact_dir / 'watch.macho')
            (artifact_dir / 'evidence.json').write_text(json.dumps({
                'schema': 'amu.darwin-watch-fixture.v1', 'sha256': pins,
                'host': {'system': platform.system(), 'machine': platform.machine(),
                         'release': platform.release()},
                'scope': 'owned children; identity mismatch, timeout, reaped PID and exec/fork event refusals; not a governor',
            }, indent=2) + '\n')
        print('PASS_MAC_WATCH_HELPER exact event; wrong identity, timeout, reaped PID and exec/fork observations refused; no governor qualification')
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGKILL)
            child.wait(timeout=3)
