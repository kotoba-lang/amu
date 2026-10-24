#!/usr/bin/env python3
"""Observe whole-project canonical SIR provenance and scalar stack calls.

No alternate region policy, native controller or compiler in this observer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers


def pin(p):
    raw = p.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(build, output, complete=None):
    source, producers, _ = load_native_producers(build=build, complete=complete)
    output.mkdir(parents=True, exist_ok=False)
    routes = []
    for producer in producers:
        out = output / producer.stem
        (out / 'lib').mkdir(parents=True)
        entry = out / 'entry.kotoba'
        bridge = out / 'lib/bridge.kotoba'
        memory = out / 'lib/memory.kotoba'
        lock = out / 'source.ksl'
        good_entry = '(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 42)\n'
        good_bridge = '(ns lib.bridge (:require [lib.memory :as m]) (:export [through]))\n(defn through [base :i64 length :i64] :i64 (m/read base length))\n'
        good_memory = '(ns lib.memory (:export [read]))\n(defn- leaf [base :i64 length :i64] :i64 (kernel-load-u8 base length 0))\n(defn read [base :i64 length :i64] :i64 (leaf base length))\n'
        calls = []

        def reset():
            entry.write_text(good_entry)
            bridge.write_text(good_bridge)
            memory.write_text(good_memory)

        def compile_(name, expected=0):
            lock.write_text(f'KSL1\nentry {entry}\nroot {out}\n'
                + ''.join(f'file {pin(p)["sha256"]} {p}\n' for p in sorted([entry, bridge, memory])))
            image = out / (name + '.elf')
            args = [str(producer), 'compile', str(entry), '--target', 'x86_64-aiueos-kernel-v1',
                '--artifact', 'image', '--output', str(image), '--fuel', '1000000',
                '--source-path', str(out), '--source-lock', str(lock), '--source-lock-sha256', pin(lock)['sha256']]
            r = subprocess.run(args, env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608'), capture_output=True, timeout=240)
            calls.append(dict(name=name, exit=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode(), sourceLock=pin(lock)))
            (out/'commands.json').write_text(json.dumps(calls, indent=2)+'\n')
            assert r.returncode == expected and b'KEXE_TRAP' not in r.stderr, (name, r.returncode, r.stderr)
            if expected:
                assert b'E7106' in r.stderr and not image.exists(), (name, r.stderr)
            else:
                assert not r.stderr and image.is_file(), (name, r.stderr)
            return image

        reset()
        # Uncalled helpers remain in the graph and use the same conservative
        # adjacent base/length rule as canonical object admission.
        valid = compile_('canonical-helper-graph')
        for name, file, before, after in [
            ('literal-through-import', entry, ':i64 42)', ':i64 (b/through 1089536 64))'),
            ('length-lie-through-import', bridge, '(m/read base length)', '(m/read base 4096)'),
            ('second-bad-caller', bridge, '\n', '\n(defn- bad [] :i64 (m/read 1089536 64))\n'),
            ('private-length-lie', memory, '(leaf base length)', '(leaf base 512)'),
            ('private-computed-base', memory, '(leaf base length)', '(leaf (+ base 8) length)'),
            ('loaded-base', memory, '(leaf base length)', '(leaf (kernel-load-u64 base length 0) length)'),
            ('subregion-parent-length', memory, '(leaf base length)', '(leaf (kernel-subregion base 4096 0 64) 64)'),
            ('subregion-output-length', memory, '(leaf base length)', '(leaf (kernel-subregion base length 0 64) 32)'),
        ]:
            reset()
            file.write_text(file.read_text().replace(before, after, 1))
            compile_(name, expected=1)
        reset()
        params = ' '.join(f'a{i} :i64' for i in range(16))
        # The independent stack-ABI fixture has no privileged memory ops,
        # so the canonical AArch64 backend can execute this same full graph.
        memory.write_text('(ns lib.memory (:export [read]))\n(defn read [base :i64 length :i64] :i64 0)\n')
        bridge.write_text(f'(ns lib.bridge (:require [lib.memory :as m]) (:export [sum16]))\n(defn sum16 [{params}] :i64 (+ '+' '.join(f'a{i}' for i in range(16))+'))\n')
        entry.write_text('(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 (- (b/sum16 '+' '.join(str(i+1) for i in range(16))+') 94))\n')
        stack = compile_('stack16')
        artifacts = dict(helperGraph=pin(valid), stack16=pin(stack))
        for label, image in [('helper-graph', valid), ('stack16', stack)]:
            efi = out / (label + '.efi')
            r = subprocess.run([str(producer), 'package-aiueos-boot', str(image), '--output', str(efi)], env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out)), capture_output=True, timeout=180)
            assert r.returncode == 0 and not r.stderr, r.stderr
            artifacts[label+'EFI'] = pin(efi)
        routes.append(dict(producer=pin(producer), artifacts=artifacts, refusalCount=8))
    assert routes[0]['artifacts'] == routes[1]['artifacts']
    report = dict(status='PASS_NATIVE_CANONICAL_PROJECT_PROVENANCE', source=source, routes=routes,
                  qemuBoot=False, fullKernel=False, nativeCDCI=False)
    (output / 'native-regions.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], 'resolved whole-project SIR, 8 refusals and scalar16 calls')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    main(a.build.resolve() if a.build else None, a.output.resolve(), a.complete.resolve() if a.complete else None)
