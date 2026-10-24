#!/usr/bin/env python3
"""Observe locked native project linking; no compiler or CDCI verdict in Python."""
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


def main(build, complete, output):
    source, producers, _ = load_native_producers(build, complete)
    output.mkdir(parents=True, exist_ok=False)
    routes = []
    for producer in producers:
        out = output / producer.stem
        out.mkdir()
        root = out / "src"
        (root / "lib").mkdir(parents=True)
        entry = root / "entry.kotoba"
        sources = {
            entry: '(ns entry (:require [lib.left :as l] [lib.right :as r]) (:export [main]))\n(defn main [] :i64 (+ (l/run 20) (r/run 20)))\n',
            root / 'lib/left.kotoba': '(ns lib.left (:require [lib.base :as b]) (:export [run unused]))\n(defn run [x :i64] :i64 (b/plus-one x))\n(defn unused [x :i64] :i64 (- x 1))\n',
            root / 'lib/right.kotoba': '(ns lib.right (:require [lib.base :refer [plus-one]]) (:export [run]))\n(defn run [x :i64] :i64 (plus-one x))\n',
            root / 'lib/base.kotoba': '(ns lib.base (:export [plus-one]))\n(defn- add [x :i64] :i64 (+ x 1))\n(defn plus-one [x :i64] :i64 (add x))\n',
        }
        for path, text in sources.items():
            path.write_text(text)
        lock = out / "project.ksl"

        def write_lock(files=None, roots=None):
            lock.write_text('KSL1\nentry ' + str(entry) + '\n'
                            + ''.join('root ' + str(p) + '\n' for p in (roots or [root]))
                            + ''.join('file ' + pin(p)['sha256'] + ' ' + str(p) + '\n'
                                      for p in sorted(files or sources)))

        write_lock()
        good_lock = lock.read_bytes()
        env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_CAP_RESOURCES_35=str(out))
        calls = []

        def compile_(name, extra=(), lock_args=True, sentinel=None, digest=None):
            dst = out / (name + '.elf')
            if sentinel is not None:
                dst.write_bytes(sentinel)
            argv = [str(producer), 'compile', str(entry), '--target', 'x86_64-aiueos-kernel-v1',
                    '--artifact', 'image', '--output', str(dst), '--fuel', '1000000',
                    '--source-path', str(root)]
            if lock_args:
                argv += ['--source-lock', str(lock), '--source-lock-sha256', digest or pin(lock)['sha256']]
            r = subprocess.run([*argv, *extra], env=env, capture_output=True, timeout=180)
            calls.append(dict(name=name, exit=r.returncode, stderr=r.stderr.decode(),
                              stdout=r.stdout.decode(), lock=pin(lock)))
            (out / 'commands.json').write_text(json.dumps(calls, indent=2) + '\n')
            return dst, r

        image, r = compile_('diamond')
        assert r.returncode == 0 and not r.stderr, ('diamond', r.returncode, r.stderr)
        image_pin = pin(image)
        # Reuse the independent ABI observer, not a hosted compiler oracle.
        observer = Path(__file__).with_name('check-aiueos-image-native.py')
        spec = importlib.util.spec_from_file_location('image_abi_observer', observer)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.verify(image.read_bytes(), 1000000)
        refusals = []

        def refused(name, **kwargs):
            dst, r = compile_(name, **kwargs)
            assert r.returncode != 0 and b'KEXE_TRAP' not in r.stderr, (name, r.returncode, r.stderr)
            assert not dst.exists(), name
            refusals.append(name)

        refused('missing-lock', lock_args=False)
        refused('unpinned', extra=('--unpinned',))
        refused('forbidden-format', extra=('--format', 'static'))
        refused('wrong-lock-digest', digest='0' * 64)
        write_lock([p for p in sources if p.name != 'base.kotoba'])
        refused('missing-transitive-source')
        extra = root / 'unused.kotoba'
        extra.write_text('(ns unused (:export [f]))\n(defn f [] :i64 0)\n')
        write_lock([*sources, extra])
        refused('unused-lock-source')
        lock.write_bytes(good_lock)
        base = root / 'lib/base.kotoba'
        original = base.read_text()
        base.write_text(original.replace('(+ x 1)', '(+ x 2)'))
        refused('transitive-hash-drift')
        base.write_text(original)
        left = root / 'lib/left.kotoba'
        original_left = left.read_text()
        left.write_text(original_left + '(defn- unreachable [] :string "must refuse")\n')
        write_lock()
        refused('unused-unsupported-function')
        left.write_text(original_left)
        original_entry = entry.read_text()
        entry.write_text(original_entry.replace('(l/run 20)', '(l/hidden 20)'))
        write_lock()
        refused('nonexported-import')
        entry.write_text(original_entry.replace('[main]', '[main aiueos-isr-6]')
                         + '(defn aiueos-isr-6 [v :i64 r :i64 c :i64 f :i64] :i64 0)\n')
        write_lock()
        refused('unsupported-isr-export')
        entry.write_text(original_entry)
        write_lock()
        dst, r = compile_('existing', sentinel=b'preserve')
        assert r.returncode != 0 and dst.read_bytes() == b'preserve'
        refusals.append('existing-output')
        again, r = compile_('diamond-again')
        assert r.returncode == 0 and not r.stderr and pin(again) == image_pin
        routes.append(dict(producer=pin(producer), image=image_pin, modules=len(sources),
                           sourceFiles={str(p.relative_to(root)): pin(p) for p in sources},
                           refusals=refusals, compiledUnreachableDeclarations=True))
    assert routes[0]['image'] == routes[1]['image']
    report = dict(status='PASS_NATIVE_AIUEOS_LOCKED_SCALAR_PROJECT', sources=source, routes=routes,
                  nativeCDCI=False, fullKernel=False, ISR=False, liveRuntime=False, qemuBoot=False)
    (output / 'native-project.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], 'diamond/refer/private interface linking and refusal controls')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--build', type=Path)
    group.add_argument('--complete', type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    main(a.build.resolve() if a.build else None, a.complete.resolve() if a.complete else None, a.output.resolve())
