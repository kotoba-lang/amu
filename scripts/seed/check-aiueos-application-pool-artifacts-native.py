#!/usr/bin/env python3
"""Bind v4/v7 and v5/v8 artifacts to native Linux compiler generations.

Amu checks, links and packages. Python only stages the already-QEMU-tested
source, observes processes and compares complete bytes to the Mac producer.
This does not execute a guest or replace any existing native/CDCI gate.
"""
import argparse
import gzip
import hashlib
import json
import platform
import struct
import subprocess
from pathlib import Path

from aiueos_native_proof import load_native_producers

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(build, complete, out):
    graph, producers, _ = load_native_producers(build=build, complete=complete)
    fixture = ROOT / 'seed/tests/aiueos-application-pool.kotoba'
    evidence = ROOT / 'docs/evidence/aiueos-application-pool-main-merge-20261103/receipt.json'
    reference = json.loads(evidence.read_text())
    assert pin(fixture) == reference['sources'][str(fixture.relative_to(ROOT))]
    unity = b''.join((ROOT / p).read_bytes() + b'\n'
                     for p in (ROOT / 'seed/FULL-MANIFEST').read_text().splitlines()
                     if p and not p.startswith('#'))
    # The old v4 runtime evidence remains immutable. Bind the current native
    # producer to its new complete source proof, then require complete old
    # artifact equality rather than relabeling that old boot as a new one.
    current_path = ROOT / 'docs/evidence/aiueos-application-transmit-pool-20261103/receipt.json'
    current = json.loads(current_path.read_text())
    assert current['state'] == 'PASS_NATIVE_APPLICATION_TRANSMIT_ALLOCATION'
    for name, expected_pin in current['nativeSourcePins'].items():
        assert pin(ROOT / name) == expected_pin
    def original_report(name):
        row = current['runs'][name]
        path = current_path.parent / row['file']
        assert pin(path) == row['compressed']
        raw = gzip.decompress(path.read_bytes())
        assert dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) == row['original']
        return json.loads(raw)
    assert dict(bytes=len(unity), sha256=hashlib.sha256(unity).hexdigest()) == original_report('mac')['source']
    transmit_expected = original_report('pool')
    assert transmit_expected['state'] == 'PASS_NATIVE_APPLICATION_TRANSMIT_POOLS'
    transmit_fixture = ROOT / 'seed/tests/aiueos-application-transmit-pool.kotoba'
    assert pin(transmit_fixture) == current['fixture'] == transmit_expected['fixture']
    expected = reference['reports']['pool']['observations']
    assert expected['state'] == 'PASS_NATIVE_APPLICATION_POOL'
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    routes = []
    report = dict(schema='amu.native-application-pool-artifacts.v1', state='TESTING',
                  host=[platform.system(), platform.machine()], sourceGraph=graph,
                  evidence=pin(evidence), fixture=pin(fixture), routes=routes,
                  currentCompilerEvidence=pin(current_path), transmitFixture=pin(transmit_fixture),
                  guestExecution=False, physical=False, appConnection=False,
                  nativeCDCI=False, observer=pin(Path(__file__)))

    def save():
        (out / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')

    save()
    try:
        for index, producer in enumerate(producers):
            scope = out / ('generation-' + str(index))
            scope.mkdir()
            src, lock = scope / 'probe.kotoba', scope / 'probe.ksl'
            src.write_bytes(fixture.read_bytes())

            def make_lock():
                lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n')

            make_lock()
            calls, artifacts = [], {}
            route = dict(compiler=pin(producer), calls=calls, artifacts=artifacts)
            routes.append(route)
            env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_CAP_RESOURCES_35=str(scope))

            def run(name, argv, expected_exit=0, diagnostic=None, absent=None):
                result = subprocess.run([str(producer), *map(str, argv)], cwd=scope,
                                        env=env, capture_output=True, timeout=240)
                for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
                    (scope / (name + '.' + suffix)).write_bytes(raw)
                calls.append(dict(name=name, argv=list(map(str, argv)), exit=result.returncode,
                                  stdout=pin(scope / (name + '.stdout')), stderr=pin(scope / (name + '.stderr'))))
                save()
                assert result.returncode == expected_exit, (name, result.returncode, result.stderr[-600:])
                if diagnostic is not None:
                    assert diagnostic in result.stderr, (name, result.stderr)
                elif expected_exit == 0:
                    assert not result.stderr, (name, result.stderr)
                if absent is not None:
                    assert not absent.exists(), (name, 'refusal created an artifact')

            def arguments(target='v4', lock_digest=None):
                return ['compile', src, '--target', 'x86_64-aiueos-kernel-' + target,
                        '--artifact', 'image', '--fuel', '9007199254740991',
                        '--source-path', scope, '--source-lock', lock,
                        '--source-lock-sha256', lock_digest or pin(lock)['sha256']]

            kernel, efi = scope / 'kernel.elf', scope / 'boot.efi'
            run('kernel', [*arguments(), '--output', kernel])
            run('efi', ['package-aiueos-boot', kernel, '--output', efi, '--pci-resources', 'v1'])
            assert pin(kernel) == expected['kernel'], 'native kernel differs from the actual Mac/QEMU artifact'
            assert pin(efi) == expected['efi'], 'native EFI differs from the actual Mac/QEMU artifact'
            raw = kernel.read_bytes()
            ph = struct.unpack_from('<Q', raw, 32)[0]
            assert struct.unpack_from('<H', raw, 56)[0] == 2
            rx, rw = [struct.unpack_from('<IIQQQQQQ', raw, ph + i*56) for i in range(2)]
            assert rx[:5] == (1, 5, 4096, 0x101000, 0x101000) and rx[5] == rx[6] <= 2097152-4096
            assert rw[:5] == (1, 6, 3145728, 0x400000, 0x400000) and rw[5] == rw[6] == 131072
            assert struct.unpack_from('<Q', raw, rw[2]+496)[0] == 0x314d5041
            artifacts.update(kernel=pin(kernel), efi=pin(efi))
            old = scope / 'old-target.elf'
            run('old-target', [*arguments('v3'), '--output', old], 1,
                b"E2101 unknown or unsupported form 'kernel-application-pool'", old)
            no_pci = scope / 'no-pci.efi'
            run('no-pci', ['package-aiueos-boot', kernel, '--output', no_pci], 1, b'E7111', no_pci)
            missing_lock = scope / 'wrong-lock.elf'
            run('wrong-lock', [*arguments(lock_digest='0'*64), '--output', missing_lock], 1, b'E6015', missing_lock)
            src.write_bytes(b'(ns forged-pool (:export [main]))\n(defn main [] :i64 (kernel-load-u32-64k 16777216 65536 0))\n')
            make_lock()
            forged = scope / 'forged.elf'
            run('forged-region', [*arguments(), '--output', forged], 1, b'E7106', forged)
            route['refusals'] = 4
            src.write_bytes(transmit_fixture.read_bytes())
            make_lock()
            tx_kernel, tx_efi = scope / 'transmit.elf', scope / 'transmit.efi'
            run('transmit-kernel', [*arguments('v5'), '--output', tx_kernel])
            run('transmit-efi', ['package-aiueos-boot', tx_kernel, '--output', tx_efi,
                                 '--pci-resources', 'v1'])
            assert pin(tx_kernel) == transmit_expected['kernel']
            assert pin(tx_efi) == transmit_expected['efi']
            artifacts.update(transmitKernel=pin(tx_kernel), transmitEFI=pin(tx_efi))
            tx_old = scope / 'transmit-old-target.elf'
            run('transmit-old-target', [*arguments('v4'), '--output', tx_old], 1,
                b"E2101 unknown or unsupported form 'kernel-application-transmit-pool'", tx_old)
            tx_no_pci = scope / 'transmit-no-pci.efi'
            run('transmit-no-pci', ['package-aiueos-boot', tx_kernel, '--output', tx_no_pci],
                1, b'E7111', tx_no_pci)
            tx_wrong_lock = scope / 'transmit-wrong-lock.elf'
            run('transmit-wrong-lock', [*arguments('v5', lock_digest='0'*64), '--output', tx_wrong_lock],
                1, b'E6015', tx_wrong_lock)
            src.write_bytes(b'(ns forged-transmit (:export [main]))\n(defn main [] :i64 (kernel-load-u32-64k 16777216 65536 0))\n')
            make_lock()
            tx_forged = scope / 'transmit-forged.elf'
            run('transmit-forged-region', [*arguments('v5'), '--output', tx_forged],
                1, b'E7106', tx_forged)
            route['transmitRefusals'] = 4
            save()
        assert len(routes) == 2 and routes[0]['artifacts'] == routes[1]['artifacts']
        report.update(state='PASS_NATIVE_APPLICATION_POOL_ARTIFACTS', crossProducerBytesMatch=True)
        save()
        print(report['state'], platform.machine(), 'two actual generations, eight refusals each; guest separate')
    except BaseException as error:
        report.update(state='FAILED', failure=str(error))
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    selected = parser.add_mutually_exclusive_group(required=True)
    selected.add_argument('--build', type=Path)
    selected.add_argument('--complete', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.build.resolve() if args.build else None,
         args.complete.resolve() if args.complete else None, args.output.resolve())
