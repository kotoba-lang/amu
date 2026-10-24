#!/usr/bin/env python3
"""Native CPU primitive fixture images; QEMU execution is observed separately."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers


def pin(p):
    b = p.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def main(build, output):
    source, producers, _ = load_native_producers(build=build)
    output.mkdir(parents=True, exist_ok=False)
    vendors = []
    for vendor in (b'GenuineIntel', b'AuthenticAMD'):
        bx, dx, cx = [int.from_bytes(vendor[i:i+4], 'little') for i in (0,4,8)]
        vendors.append(f'(and (= bx {bx}) (= dx {dx}) (= cx {cx}))')
    text = '''(ns cpu (:export [main]))
(defn main [] :i64
  (let [leaf (kernel-cpuid-eax 0 0)
        bx (kernel-cpuid-ebx 0 0) cx (kernel-cpuid-ecx 0 0) dx (kernel-cpuid-edx 0 0)
        features (kernel-cpuid-edx 2147483649 0)
        cr0 (kernel-read-cr0) cr3 (kernel-read-cr3) cr4 (kernel-read-cr4)
        wrote0 (kernel-write-cr0 cr0) wrote3 (kernel-write-cr3 cr3) wrote4 (kernel-write-cr4 cr4)
        after0 (kernel-read-cr0) after3 (kernel-read-cr3) after4 (kernel-read-cr4)
        cs (kernel-read-cs) efer (kernel-read-msr 3221225600)
        oldfs (kernel-read-msr 3221225728)
        wrotefs (kernel-write-msr 3221225728 4294971392)
        newfs (kernel-read-msr 3221225728)
        restored (kernel-write-msr 3221225728 oldfs)
        afterfs (kernel-read-msr 3221225728)
        t0 (kernel-rdtsc) paused (kernel-pause) t1 (kernel-rdtsc)
        invalidated (kernel-invlpg 1089536) disabled (kernel-cli)]
    (if (and (> leaf 0) (< leaf 1024) VENDOR
             (= (bit-and features 536870912) 536870912)
             (= (bit-and cr0 2147483649) 2147483649) (> cr3 0) (= (bit-and cr3 4095) 0)
             (= (bit-and cr4 32) 32) (= cs 8) (= (bit-and efer 1280) 1280)
             (= wrote0 cr0) (= wrote3 cr3) (= wrote4 cr4)
             (= after0 cr0) (= after3 cr3) (= after4 cr4)
             (= wrotefs 4294971392) (= newfs 4294971392) (= restored oldfs) (= afterfs oldfs)
             (>= t1 t0) (= paused 0) (= invalidated 1089536) (= disabled 0)) 42 0)))
'''.replace('VENDOR', '(or '+' '.join(vendors)+')')
    routes = []
    for producer in producers:
        out = output / producer.stem
        out.mkdir()
        src, lock = out / 'cpu.kotoba', out / 'cpu.ksl'
        src.write_text(text)
        lock.write_text(f'KSL1\nentry {src}\nroot {out}\nfile {pin(src)["sha256"]} {src}\n')
        image, efi = out / 'cpu.elf', out / 'cpu.efi'
        commands = [
            [str(producer), 'compile', str(src), '--target', 'x86_64-aiueos-kernel-v1', '--artifact', 'image',
             '--output', str(image), '--fuel', '1000000', '--source-path', str(out),
             '--source-lock', str(lock), '--source-lock-sha256', pin(lock)['sha256']],
            [str(producer), 'package-aiueos-boot', str(image), '--output', str(efi)],
        ]
        calls = []
        for command in commands:
            r = subprocess.run(command, env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608'),
                               capture_output=True, timeout=180)
            calls.append(dict(argv=command, exit=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode()))
            assert r.returncode == 0 and not r.stderr, (command, r.returncode, r.stderr)
        (out / 'commands.json').write_text(json.dumps(calls, indent=2)+'\n')
        routes.append(dict(producer=pin(producer), source=pin(src), lock=pin(lock), image=pin(image), efi=pin(efi)))
    assert routes[0]['image'] == routes[1]['image'] and routes[0]['efi'] == routes[1]['efi']
    report = dict(status='PASS_NATIVE_CPU_PROJECT_IMAGES', source=source, routes=routes,
                  qemuBoot=False, stiHltExecuted=False, fullKernel=False, nativeCDCI=False)
    (output / 'native-cpu-project.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], 'CPUID/CR/MSR/CS/TSC/pause/CLI/invlpg; guest execution pending')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    main(a.build.resolve(), a.output.resolve())
