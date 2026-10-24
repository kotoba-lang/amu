#!/usr/bin/env python3
"""Observe bounded contiguous grants from the sealed fifteen-page allocation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers

SOURCE = '''(ns entry (:export [main]))
(defn main [] :i64
 (let [h (kernel-subregion (kernel-boot-info) 16544 0 160)
       original (kernel-load-u64 h 160 80)
       changed (kernel-store-u64 h 160 80 0)
       w (kernel-owned-window 1 12288)
       page (kernel-owned-page 1)
       last (kernel-subregion w 12288 8192 4096)
       third (kernel-owned-page 3)
       saved (kernel-load-u64-16k w 12288 12280)
       write (kernel-store-u64-16k w 12288 12280 42)
       readback (kernel-load-u64-4k last 4096 4088)
       restored (kernel-store-u64-16k w 12288 12280 saved)
       metadata (kernel-store-u64 h 160 80 original)]
  (if (and (= changed 0) (= w page) (= last third) (= write 42)
           (= readback 42) (= restored saved) (= metadata original)) 42 0)))
'''


def pin(p):
    raw = p.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(build, out):
    graph, producers, _ = load_native_producers(build=build)
    out.mkdir(parents=True, exist_ok=False)
    routes = []
    for compiler in producers:
        scope = out / compiler.stem
        scope.mkdir()
        src, lock = scope/'entry.kotoba', scope/'source.ksl'
        calls, artifacts = [], {}

        def compile_(name, text, bad=False):
            src.write_text(text)
            lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n')
            image = scope/(name+'.elf')
            env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_CAP_RESOURCES_35=str(scope))
            r = subprocess.run([str(compiler), 'compile', str(src), '--target', 'x86_64-aiueos-kernel-v1', '--artifact', 'image', '--output', str(image), '--fuel', '1000000', '--source-path', str(scope), '--source-lock', str(lock), '--source-lock-sha256', pin(lock)['sha256']], env=env, capture_output=True, timeout=240)
            calls.append(dict(name=name, exit=r.returncode, stderr=r.stderr.decode(), sourceText=text))
            (scope/'calls.json').write_text(json.dumps(calls, indent=2)+'\n')
            if bad:
                assert r.returncode == 1 and b'E7106' in r.stderr and not image.exists(), calls[-1]
            else:
                assert r.returncode == 0 and not r.stderr and image.exists(), calls[-1]
                efi = scope/(name+'.efi')
                q = subprocess.run([str(compiler), 'package-aiueos-boot', str(image), '--output', str(efi)], env=env, capture_output=True, timeout=180)
                assert q.returncode == 0 and not q.stderr, q.stderr
                artifacts[name] = dict(kernel=pin(image), efi=pin(efi))

        compile_('sealed-window', SOURCE)
        for name, slot, size in [('zero', 0, 0), ('unaligned', 0, 4095), ('negative-size', 0, -4096), ('too-wide', 0, 65536), ('cross-end', 14, 8192), ('invalid-slot', 15, 4096), ('negative-slot', -1, 4096), ('valid-window', 0, 61440)]:
            compile_(name, f'(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-owned-window {slot} {size}) 0) 42 0))\n')
        compile_('wrong-length', SOURCE.replace('(kernel-load-u64-16k w 12288 12280)', '(kernel-load-u64-16k w 16384 12280)'), True)
        compile_('computed-root', SOURCE.replace('(kernel-load-u64-16k w 12288 12280)', '(kernel-load-u64-16k (+ w 0) 12288 12280)'), True)
        routes.append(dict(compiler=pin(compiler), artifacts=artifacts, compileRefusals=2))
    assert routes[0]['artifacts'] == routes[1]['artifacts']
    report = dict(status='PASS_NATIVE_OWNED_WINDOW_PACKAGING', source=graph, routes=routes, guestExecution=False, fullKernel=False, nativeCDCI=False)
    (out/'native-owned-window.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], 'sealed contiguous allocation,7 runtime bounds fixtures and2 provenance refusals; guest separate')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    main(a.build.resolve(), a.output.resolve())
