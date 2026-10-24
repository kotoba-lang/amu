#!/usr/bin/env python3
"""Observe transitive kernel region requirements and scalar stack arguments."""
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


LIBRARY = '''(ns lib.memory (:export [through repeated offset-read]))
(defn- leaf [b :i64 i :i64] :i64 (kernel-load-u8 b 64 i))
(defn- peek-byte [b :i64] :i64 (leaf b 0))
(defn through [b :i64 flag :bool] :i64
  (let [r (if flag b (kernel-subregion b 4096 0 4096))
        ignored (let [r (+ 1 2)] r)]
    (peek-byte (kernel-subregion r 4096 16 64))))
(defn- repeat-byte [b :i64 n :i64] :i64
  (if (= n 0) (leaf b 0) (repeat-byte b (dec n))))
(defn repeated [b :i64] :i64 (repeat-byte b 2))
(defn offset-read
  ([b :i64] :i64 (leaf b 0))
  ([tag :i64 b :i64] :i64 (+ (leaf b 0) (* 0 tag))))
'''
ENTRY = '''(ns entry (:require [lib.memory :as m]) (:export [main]))
(defn main [] :i64
  (let [stored (kernel-store-u8-4k 1089536 4096 16 42)
        a (m/through 1089536 true) b (m/through 1089536 false)
        narrowed (kernel-subregion 1089536 4096 16 64)
        c (m/repeated narrowed) scalar (kernel-load-u8-4k 1089536 4096 16)
        d (m/offset-read narrowed) e (m/offset-read scalar narrowed)]
    (if (and (= stored 42) (= a 42) (= b 42) (= c 42) (= d 42) (= e 42)) 42 0)))
'''


def main(build, output):
    source, producers, _ = load_native_producers(build=build)
    output.mkdir(parents=True, exist_ok=False)
    routes = []
    for producer in producers:
        out = output / producer.stem
        (out / 'lib').mkdir(parents=True)
        entry, library, lock = out / 'entry.kotoba', out / 'lib/memory.kotoba', out / 'source.ksl'
        entry.write_text(ENTRY)
        library.write_text(LIBRARY)
        calls = []

        def compile_(name, extra=(), expected=0, diagnostic=None):
            lock.write_text(f'KSL1\nentry {entry}\nroot {out}\n'
                            + ''.join(f'file {pin(p)["sha256"]} {p}\n' for p in sorted([entry, library])))
            image = out / (name + '.elf')
            argv = [str(producer), 'compile', str(entry), '--target', 'x86_64-aiueos-kernel-v1', '--artifact', 'image',
                    '--output', str(image), '--fuel', '1000000', '--source-path', str(out),
                    '--source-lock', str(lock), '--source-lock-sha256', pin(lock)['sha256'], *extra]
            r = subprocess.run(argv, env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608'),
                               capture_output=True, timeout=180)
            calls.append(dict(name=name, exit=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode(), source=pin(entry), library=pin(library)))
            (out / 'commands.json').write_text(json.dumps(calls, indent=2)+'\n')
            assert r.returncode == expected and b'KEXE_TRAP' not in r.stderr, (name, r.returncode, r.stderr)
            if diagnostic:
                assert diagnostic.encode() in r.stderr, (name, r.stderr)
            if expected:
                assert not image.exists()
            else:
                assert not r.stderr
            return image

        region_image = compile_('regions')
        refusals = {
            'loaded-cross-module': '(m/repeated (kernel-load-u64-4k 1089536 4096 0))',
            'wrong-parameter-position': '(m/offset-read 1089536 (kernel-load-u64-4k 1089536 4096 0))',
            'unsafe-if-arm': '(m/repeated (if true 1089536 (kernel-load-u64-4k 1089536 4096 0)))',
        }
        for name, expression in refusals.items():
            entry.write_text('(ns entry (:require [lib.memory :as m]) (:export [main]))\n(defn main [] :i64 '+expression+')\n')
            compile_(name, expected=1, diagnostic='E7106')
        entry.write_text('''(ns entry (:require [lib.memory :as m]) (:export [main]))
(defn main [] :i64 (bounce (kernel-load-u64-4k 1089536 4096 0)))
(defn- bounce [b :i64] :i64 (m/repeated b))
''')
        compile_('forward-transitive', expected=1, diagnostic='E7106')
        entry.write_text(ENTRY+'\n(defn- unreachable [] :i64 (m/repeated (kernel-load-u64-4k 1089536 4096 0)))\n')
        compile_('unreachable-unsafe-caller', expected=1, diagnostic='E7106')
        entry.write_text('''(ns entry (:export [main]))
(defn- recur-base [b :i64 n :i64] :i64
  (if (= n 0) (kernel-load-u8 b 64 0) (recur-base (+ b 1) (dec n))))
(defn main [] :i64 (recur-base 1089536 2))
''')
        # Retain the declared dependency and its exact lock while checking
        # a local recursive call; no declaration is silently discarded.
        library.write_text('(ns lib.memory (:export [through]))\n(defn through [] :i64 0)\n')
        entry.write_text(entry.read_text().replace('(ns entry (:export [main]))', '(ns entry (:require [lib.memory :as unused]) (:export [main]))'))
        compile_('recursive-base-reassignment', expected=1, diagnostic='E7106')
        parameters = ' '.join(f'a{i} :i64' for i in range(16))
        args = ' '.join(str(i+1) for i in range(16))
        names = ' '.join(f'a{i}' for i in range(16))
        library.write_text(f'(ns lib.memory (:export [sum16]))\n(defn sum16 [{parameters}] :i64 (+ {names}))\n')
        entry.write_text(f'(ns entry (:require [lib.memory :as m]) (:export [main]))\n(defn main [] :i64 (- (m/sum16 {args}) 94))\n')
        stack_image = compile_('stack16')
        library.write_text(library.read_text() + '\n(defn- too-wide ['+' '.join(f'p{i} :i64' for i in range(17))+'] :i64 0)\n')
        compile_('unused-17-arguments', expected=1)
        artifacts = {}
        for name, image in [('regions', region_image), ('stack16', stack_image)]:
            efi = out / (name + '.efi')
            r = subprocess.run([str(producer), 'package-aiueos-boot', str(image), '--output', str(efi)],
                               env=dict(PATH='/nonexistent', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608'),
                               capture_output=True, timeout=180)
            assert r.returncode == 0 and not r.stderr, r.stderr
            artifacts[name] = pin(image)
            artifacts[name+'-efi'] = pin(efi)
        routes.append(dict(producer=pin(producer), artifacts=artifacts, refusalCount=7))
    assert routes[0]['artifacts'] == routes[1]['artifacts']
    report = dict(status='PASS_NATIVE_PROJECT_REGION_REQUIREMENTS', source=source, routes=routes,
                  qemuBoot=False, fullKernel=False, nativeCDCI=False)
    (output / 'native-regions.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], 'private/import/branch/recursive/arity-position masks and scalar16 stack arguments')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    main(a.build.resolve(), a.output.resolve())
