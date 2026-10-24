#!/usr/bin/env python3
"""Observe native kernel-project memory/I/O images; guest execution is separate."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(build, output, complete=None):
    source, producers, _ = load_native_producers(build=build, complete=complete)
    output.mkdir(parents=True, exist_ok=False)
    value, base = 0x123456789abcdef, 0x10a000
    bindings, checks, operations = [], [], []
    for tier, size in [('', 512), ('-4k', 4096), ('-16k', 16384), ('-64k', 65536)]:
        for bits in (8, 16, 32, 64):
            k = len(operations)
            store, load = 'kernel-store-u' + str(bits) + tier, 'kernel-load-u' + str(bits) + tier
            bindings += [f's{k} ({store} {base} {size} {16*k} {value})',
                         f'l{k} ({load} {base} {size} {16*k})']
            checks += [f'(= s{k} {value})', f'(= l{k} {value & ((1 << bits)-1)})']
            operations.append(dict(store=store, load=load, bits=bits, maximum=size))
    memory = '(ns memory (:export [main]))\n(defn main [] :i64 (let [' + '\n'.join(bindings) + '] (if (and ' + ' '.join(checks) + ') 42 0)))\n'
    pci = '''(ns pci (:export [main]))
(defn main [] :i64
  (let [mark (kernel-out-u8 233 65)
        selected (kernel-out-u32 3320 (+ 2147483648 (* 0 mark)))
        wide (kernel-in-u32 (+ 3324 (* 0 selected)))
        byte (kernel-in-u8 3324)]
    (if (and (= (bit-and wide 65535) 32902) (= byte 134)) 42 0)))
'''
    spec = importlib.util.spec_from_file_location('image_observer', Path(__file__).with_name('check-aiueos-image-native.py'))
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    routes = []
    for producer in producers:
        out = output / producer.stem
        out.mkdir()
        calls, artifacts = [], {}
        for name, text in [('memory-widths', memory), ('q35-pci-ports', pci),
                           ('loaded-base', f'(ns bad (:export [main]))\n(defn main [] :i64 (let [p (kernel-load-u64-4k {base} 4096 0)] (kernel-load-u8 p 512 0)))\n'),
                           ('computed-base', f'(ns bad (:export [main]))\n(defn main [] :i64 (kernel-load-u8 (+ {base} 1) 512 0))\n')]:
            src, image, lock = out / (name + '.kotoba'), out / (name + '.elf'), out / (name + '.ksl')
            src.write_text(text)
            lock.write_text(f'KSL1\nentry {src}\nroot {out}\nfile {pin(src)["sha256"]} {src}\n')
            argv = [str(producer), 'compile', str(src), '--target', 'x86_64-aiueos-kernel-v1',
                    '--artifact', 'image', '--output', str(image), '--fuel', '1000000',
                    '--source-path', str(out), '--source-lock', str(lock), '--source-lock-sha256', pin(lock)['sha256']]
            r = subprocess.run(argv, env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608'),
                               capture_output=True, timeout=180)
            calls.append(dict(name=name, exit=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode(), source=pin(src), lock=pin(lock)))
            if name.endswith('base'):
                assert r.returncode == 1 and b'E7106' in r.stderr and not image.exists(), (name, r.returncode, r.stderr)
            else:
                assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr)
                observer.verify(image.read_bytes(), 1000000)
                artifacts[name] = pin(image)
                efi = out / (name + '.efi')
                r = subprocess.run([str(producer), 'package-aiueos-boot', str(image), '--output', str(efi)],
                                   env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608'),
                                   capture_output=True, timeout=180)
                assert r.returncode == 0 and not r.stderr, (name, r.stderr)
                artifacts[name + '-efi'] = pin(efi)
        (out / 'commands.json').write_text(json.dumps(calls, indent=2) + '\n')
        routes.append(dict(producer=pin(producer), artifacts=artifacts))
    assert routes[0]['artifacts'] == routes[1]['artifacts']
    report = dict(status='PASS_NATIVE_KERNEL_MEMORY_PROJECT_IMAGES', source=source, routes=routes,
                  operationPairs=operations, qemuBoot=False, fullKernel=False, nativeCDCI=False)
    (output / 'native-memory-project.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], 'all32 width/tier operations and q35 PCI port fixture; guest execution pending')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    main(a.build.resolve() if a.build else None, a.output.resolve(), a.complete.resolve() if a.complete else None)
