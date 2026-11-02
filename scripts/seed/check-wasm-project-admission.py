#!/usr/bin/env python3
"""Check locked Wasm project discovery; success still refuses unimplemented linking."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    compiler = args.compiler.resolve(strict=True)
    root = args.output.resolve(); root.mkdir(parents=True, exist_ok=False)
    entry = root / 'app.kotoba'; dep = root / 'util.kotoba'; lock = root / 'source.ksl'
    entry.write_text('(ns app (:require [util :as u]) (:export [main]))\n(defn main [] :i64 (u/add 41))\n')
    dep.write_text('(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n')
    sha = lambda value: hashlib.sha256(value).hexdigest()
    def make_lock(extra=None):
        files = sorted([entry, dep] + ([extra] if extra is not None else []))
        text = f'KSL1\nentry {entry}\nroot {root}\n' + ''.join(f'file {sha(path.read_bytes())} {path}\n' for path in files)
        lock.write_text(text)
        return sha(text.encode())
    env = dict(PATH='/nonexistent', KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(root), KEXE_STACK_BYTES='8388608')
    calls = []
    def run(name, tail, status, marker):
        image = root / (name + '.wasm')
        proc = subprocess.run([str(compiler), 'compile', str(entry), '--target', 'wasm32-browser', '--output', str(image), *tail],
                              cwd=root, env=env, capture_output=True, timeout=120)
        assert proc.returncode == status and marker in proc.stderr and not image.exists(), (name, proc.returncode, proc.stderr)
        calls.append({'case':name,'exit':proc.returncode,'stderr':proc.stderr.decode()})
    scalar = root / 'scalar.kotoba'; wasm = root / 'scalar.wasm'
    scalar.write_text('(ns scalar (:export [main]))\n(defn main [] :i64 42)\n')
    basic = subprocess.run([str(compiler),'compile',str(scalar),'--target','wasm32-browser','--output',str(wasm)],
                           cwd=root,env=env,capture_output=True,timeout=120)
    assert basic.returncode == 0 and not basic.stderr and wasm.read_bytes().startswith(b'\0asm\1\0\0\0'), (basic.returncode,basic.stderr)
    calls.append({'case':'single-source','exit':basic.returncode,'wasmSha256':sha(wasm.read_bytes())})
    digest = make_lock()
    prefix = ['--source-path',str(root),'--source-lock',str(lock),'--source-lock-sha256']
    positive = subprocess.run([str(compiler),'check',str(entry),*prefix,digest],cwd=root,env=env,capture_output=True,timeout=120)
    assert positive.returncode == 0 and not positive.stderr, (positive.returncode,positive.stderr)
    run('valid', prefix + [digest], 2, b'E7107')
    run('wrong-digest', prefix + ['0'*64], 1, b'E6015')
    dep.write_text(dep.read_text() + '\n;; changed\n')
    run('changed-source', prefix + [digest], 1, b'E6015')
    dep.write_text('(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n')
    extra = root / 'unused.kotoba'; extra.write_text('(ns unused)\n')
    digest = make_lock(extra)
    run('extra-source', prefix + [digest], 1, b'E6015')
    digest = make_lock()
    run('missing-digest', ['--source-path',str(root),'--source-lock',str(lock)], 2, b'E7100')
    run('unpinned', ['--source-path',str(root),'--unpinned'], 2, b'E7100')
    (root/'receipt.json').write_text(json.dumps({'status':'PASS_LOCKED_WASM_PROJECT_ADMISSION', 'compilerSha256':sha(compiler.read_bytes()),
        'cases':calls, 'limitations':['valid project still refuses E7107; no Wasm project linker or artifact', 'no browser graph or x86 qualification']},indent=2)+'\n')
    print('PASS_LOCKED_WASM_PROJECT_ADMISSION')

if __name__ == '__main__': main()
