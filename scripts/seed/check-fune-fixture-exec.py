#!/usr/bin/env python3
"""Exercise only the fixed-digest ARM64 worker execution smoke test.

The fixture is a fixed Amu-built static ELF, not an arbitrary guest, and this
host observer does not qualify OCI admission or a workload security boundary.
"""
import argparse
import ctypes
import hashlib
import io
import json
import os
import platform
import struct
import subprocess
import tarfile
from pathlib import Path

EXPECTED = 'bb4aef9071c2a402b36c72012e89e166aaedb44cc811e05e4cdef9e150063b09'
READY = b'fune-private-root-ready\n'
OUTPUT_EXPECTED = 'e0e1ca9321c42adfff1f7e9fe490a5750310b89bf9a9b0b577dcef9563ec57a7'
OUTPUT_FRAME = b'K\x07\x00\x00\x00\x0bfune-smoke\n'


class Filter(ctypes.Structure):
    _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]


class Program(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]


def deny_execveat():
    code = (Filter * 4)(Filter(0x20, 0, 0, 0), Filter(0x15, 0, 1, 281),
                        Filter(0x06, 0, 0, 0x00050001), Filter(0x06, 0, 0, 0x7fff0000))
    program = Program(len(code), code)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        os._exit(125)


def deny_clock():
    code = (Filter * 4)(Filter(0x20, 0, 0, 0), Filter(0x15, 0, 1, 113),
                        Filter(0x06, 0, 0, 0x00050001), Filter(0x06, 0, 0, 0x7fff0000))
    program = Program(len(code), code)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        os._exit(125)


def deny_pread():
    code = (Filter * 4)(Filter(0x20, 0, 0, 0), Filter(0x15, 0, 1, 67),
                        Filter(0x06, 0, 0, 0x00050001), Filter(0x06, 0, 0, 0x7fff0000))
    program = Program(len(code), code)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        os._exit(125)


def frame(op, path, size, data=b''):
    path = path.encode('ascii')
    return op + struct.pack('>HI', len(path), size) + path + data


def spec(args, env=(), cwd=b'/'):
    result = b'FPS\1' + struct.pack('>HHH', len(args), len(env), len(cwd)) + cwd
    for value in (*args, *env):
        result += struct.pack('>I', len(value)) + value
    return result


def main(worker, fixture, expect_pids_refusal, producer, output, output_fixture):
    assert platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64')
    assert os.geteuid() != 0
    data = fixture.read_bytes()
    assert len(data) == 320000 and hashlib.sha256(data).hexdigest() == EXPECTED

    outdata = output_fixture.read_bytes() if output_fixture else None
    if outdata is not None:
        assert len(outdata) == 320000 and hashlib.sha256(outdata).hexdigest() == OUTPUT_EXPECTED

    def run(request, preexec=None):
        return subprocess.run([str(worker)], input=request, capture_output=True,
                              env={'PATH': '/nonexistent'}, preexec_fn=preexec, timeout=35)

    def setup(image, payload):
        return (frame(b'F', 'app', len(image), image) + frame(b'P', 'app', 0o755)
                + b'T' + struct.pack('>HI', 2, len(payload)) + payload)

    payload = spec([b'/app'])
    if expect_pids_refusal:
        cgroup = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
        def denied_count():
            return int(dict(line.split() for line in (cgroup / 'pids.events').read_text().splitlines())['max'])
        before = denied_count()
        limited = run(setup(outdata or data, payload) + (b'O' if outdata else b'E'))
        after = denied_count()
        stage = b'FREFUSE:27' if outdata else b'FREFUSE:26'
        assert limited.returncode == 2 and limited.stdout == READY + b'KKD' and stage in limited.stderr
        assert after > before, (before, after)
        print('PASS_FUNE_FIXED_FIXTURE_PIDS_REFUSAL')
        return
    valid = run(setup(data, payload) + b'EX')
    assert valid.returncode == 0 and valid.stdout == READY + b'KKDK' and not valid.stderr, (valid.returncode, valid.stdout, valid.stderr)
    altered = bytearray(data); altered[-1] ^= 1
    bad_hash = run(setup(altered, payload) + b'E')
    assert bad_hash.returncode == 2 and bad_hash.stdout == READY + b'KKD' and b'FREFUSE:26' in bad_hash.stderr
    truncated = run(setup(data[:-1], payload) + b'E')
    assert truncated.returncode == 2 and truncated.stdout == READY + b'KKD' and b'FREFUSE:26' in truncated.stderr
    extended = run(setup(data + b'x', payload) + b'E')
    assert extended.returncode == 2 and extended.stdout == READY + b'KKD' and b'FREFUSE:26' in extended.stderr
    wrong_shape = run(setup(data, spec([b'/app', b'extra'])) + b'E')
    assert wrong_shape.returncode == 2 and wrong_shape.stdout == READY + b'KKD' and b'FREFUSE:26' in wrong_shape.stderr
    wrong_env = run(setup(data, spec([b'/app'], [b'X=1'])) + b'E')
    assert wrong_env.returncode == 2 and wrong_env.stdout == READY + b'KKD' and b'FREFUSE:26' in wrong_env.stderr
    repeated = run(setup(data, payload) + b'EE')
    assert repeated.returncode == 2 and repeated.stdout == READY + b'KKDK' and b'FREFUSE:15' in repeated.stderr
    data_only = run(b'C\x00\x00E')
    assert data_only.returncode == 2 and data_only.stdout == READY + b'D' and b'FREFUSE:15' in data_only.stderr
    denied = run(setup(data, payload) + b'E', deny_execveat)
    assert denied.returncode == 2 and denied.stdout == READY + b'KKD' and b'FREFUSE:26' in denied.stderr
    no_clock = run(setup(data, payload) + b'E', deny_clock)
    assert no_clock.returncode == 2 and no_clock.stdout == READY + b'KKD' and b'FREFUSE:26' in no_clock.stderr
    early = run(b'E')
    assert early.returncode == 2 and early.stdout == READY and b'FREFUSE:15' in early.stderr
    if outdata is not None:
        out = run(setup(outdata, payload) + b'OX')
        assert out.returncode == 0 and out.stdout == READY + b'KKD' + OUTPUT_FRAME and not out.stderr, (out.returncode, out.stdout, out.stderr)
        changed = bytearray(outdata); changed[-1] ^= 1
        bad = run(setup(changed, payload) + b'O')
        assert bad.returncode == 2 and bad.stdout == READY + b'KKD' and b'FREFUSE:26' in bad.stderr
        wrong_fixture = run(setup(data, payload) + b'O')
        assert wrong_fixture.returncode == 2 and wrong_fixture.stdout == READY + b'KKD' and b'FREFUSE:26' in wrong_fixture.stderr
        with_args_env = run(setup(outdata, spec([b'/app', b'extra'], [b'X=1'])) + b'OX')
        assert with_args_env.returncode == 0 and with_args_env.stdout == READY + b'KKD' + OUTPUT_FRAME and not with_args_env.stderr
        wrong_command = run(setup(outdata, payload) + b'E')
        assert wrong_command.returncode == 2 and wrong_command.stdout == READY + b'KKD' and b'FREFUSE:26' in wrong_command.stderr
        early_out = run(b'O')
        assert early_out.returncode == 2 and early_out.stdout == READY and b'FREFUSE:15' in early_out.stderr
        data_only_out = run(b'C\x00\x00O')
        assert data_only_out.returncode == 2 and data_only_out.stdout == READY + b'D' and b'FREFUSE:15' in data_only_out.stderr
        denied_out = run(setup(outdata, payload) + b'O', deny_execveat)
        assert denied_out.returncode == 2 and denied_out.stdout == READY + b'KKD' and b'FREFUSE:27' in denied_out.stderr
        denied_preflight = run(setup(outdata, payload) + b'O', deny_pread)
        assert denied_preflight.returncode == 2 and denied_preflight.stdout == READY + b'KKD' and b'FREFUSE:28' in denied_preflight.stderr
        no_clock_out = run(setup(outdata, payload) + b'O', deny_clock)
        assert no_clock_out.returncode == 2 and no_clock_out.stdout == READY + b'KKD' and b'FREFUSE:27' in no_clock_out.stderr
        repeat_out = run(setup(outdata, payload) + b'OO')
        assert repeat_out.returncode == 2 and repeat_out.stdout == READY + b'KKD' + OUTPUT_FRAME and b'FREFUSE:15' in repeat_out.stderr
        print('PASS_FUNE_FIXED_FIXTURE_OUTPUT')
    if producer is not None:
        data = outdata if outdata is not None else data
        expected_digest = OUTPUT_EXPECTED if outdata is not None else EXPECTED
        assert output is not None and not output.exists()
        root = output / 'oci-layout'
        blobs = root / 'blobs/sha256'
        blobs.mkdir(parents=True, mode=0o700)
        def blob(content):
            h = hashlib.sha256(content).hexdigest()
            (blobs / h).write_bytes(content)
            return 'sha256:' + h
        def encode(obj):
            return json.dumps(obj, separators=(',', ':')).encode()
        layer_bytes = io.BytesIO()
        with tarfile.open(fileobj=layer_bytes, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            if outdata is not None:
                directory = tarfile.TarInfo('work')
                directory.type, directory.mode = tarfile.DIRTYPE, 0o755
                directory.uid = directory.gid = directory.mtime = 0
                archive.addfile(directory)
            entry = tarfile.TarInfo('app')
            entry.size, entry.mode, entry.uid, entry.gid, entry.mtime = len(data), 0o755, 0, 0, 0
            archive.addfile(entry, io.BytesIO(data))
        layer = layer_bytes.getvalue(); layer_digest = blob(layer)
        config = encode({'architecture': 'arm64', 'os': 'linux',
                         'rootfs': {'type': 'layers', 'diff_ids': [layer_digest]},
                         'config': ({'Entrypoint': ['/app'], 'Cmd': ['hello', '世界'],
                                     'Env': ['X=1', 'EMPTY='], 'WorkingDir': '/work'}
                                    if outdata is not None else
                                    {'Entrypoint': ['/app'], 'Cmd': [], 'Env': [], 'WorkingDir': '/'})})
        config_digest = blob(config)
        manifest = encode({'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                           'config': {'mediaType': 'application/vnd.oci.image.config.v1+json',
                                      'digest': config_digest, 'size': len(config)},
                           'layers': [{'mediaType': 'application/vnd.oci.image.layer.v1.tar',
                                       'digest': layer_digest, 'size': len(layer)}]})
        manifest_digest = blob(manifest)
        (root / 'oci-layout').write_text('{"imageLayoutVersion":"1.0.0"}')
        (root / 'index.json').write_bytes(encode({'schemaVersion': 2, 'manifests': [
            {'mediaType': 'application/vnd.oci.image.manifest.v1+json',
             'digest': manifest_digest, 'size': len(manifest)}]}))
        env = {'PATH': '/nonexistent', 'KEXE_ALLOW': '35,37,38,39', 'KEXE_COMMAND': '1',
               'KEXE_FUEL': '100000000000', 'KEXE_STACK_BYTES': '8388608',
               'KEXE_CAP_RESOURCES_35': str(root)}
        def emit(digest):
            return subprocess.run([str(producer), str(root), digest], env=env, capture_output=True, timeout=120)
        stream = emit(manifest_digest)
        assert stream.returncode == 0 and not stream.stderr and stream.stdout.startswith(b'H'), (stream.returncode, stream.stderr[-1000:])
        refused = emit('sha256:' + '0' * 64)
        assert refused.returncode != 0 and not refused.stdout
        layer_path = blobs / layer_digest.removeprefix('sha256:')
        corrupted = bytearray(layer); corrupted[512] ^= 1
        try:
            layer_path.write_bytes(corrupted)
            refused_layer = emit(manifest_digest)
            assert refused_layer.returncode != 0 and not refused_layer.stdout
        finally:
            layer_path.write_bytes(layer)
        launched = run(stream.stdout + (b'4f58' if outdata is not None else b'4558'))
        expected_output = READY + (b'KKKKD' if outdata is not None else b'KKD') + (OUTPUT_FRAME if outdata is not None else b'K')
        assert launched.returncode == 0 and launched.stdout == expected_output and not launched.stderr, (launched.returncode, launched.stdout[-500:], launched.stderr[-500:])
        (output / 'result.json').write_text(json.dumps({'manifest': manifest_digest, 'producerSHA256': hashlib.sha256(producer.read_bytes()).hexdigest(),
                                                        'workerSHA256': hashlib.sha256(worker.read_bytes()).hexdigest(),
                                                        'fixtureSHA256': expected_digest, 'status': 'PASS_FUNE_OCI_FIXED_FIXTURE_EXEC'}, indent=2) + '\n')
        print('PASS_FUNE_OCI_FIXED_FIXTURE_EXEC')
    print('PASS_FUNE_FIXED_FIXTURE_EXEC')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--output-fixture', type=Path)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--expect-pids-refusal', action='store_true')
    parser.add_argument('--producer', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    assert bool(args.producer) == bool(args.output)
    main(args.worker.resolve(), args.fixture.resolve(), args.expect_pids_refusal,
         args.producer.resolve() if args.producer else None, args.output.resolve() if args.output else None,
         args.output_fixture.resolve() if args.output_fixture else None)
