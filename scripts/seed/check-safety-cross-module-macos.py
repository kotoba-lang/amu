#!/usr/bin/env python3
"""Observe per-module capability declarations on source-locked macOS ARM projects.

Python only stages files, invokes supplied native programs and checks results.
This is not a whole-project admission gate or a full safety qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'test/fixtures/selfhost/safety-boundaries/project'
def digest(b): return hashlib.sha256(b).hexdigest()
def sha(p): return digest(p.read_bytes())

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('compiler', 'packager', 'output'): ap.add_argument('--' + key, type=Path, required=True)
    a = ap.parse_args()
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'): raise ValueError('requires macOS ARM64')
    compiler, packager = (p.resolve(strict=True) for p in (a.compiler, a.packager))
    for p in (compiler, packager): subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(p)], check=True, capture_output=True, timeout=30)
    entry, library = FIXTURES/'main.kotoba', FIXTURES/'safety/fs_library.kotoba'
    inputs = [compiler, packager, entry, library, Path(__file__).resolve()]
    pins = {str(p):sha(p) for p in inputs}
    out = a.output.resolve(); out.mkdir(parents=True,exist_ok=False); (out/'data').write_bytes(b'abc')
    original_entry, original_lib = entry.read_bytes(), library.read_bytes()
    if original_entry.count(b'(lib/read-size) 3)') != 1 or original_lib.count(b'[:fs/app-data]') != 1:
        raise ValueError('fixture mutation anchors changed')
    cases = [('root-empty',original_entry,original_lib,42,None),
             ('wrong-result',original_entry.replace(b'(lib/read-size) 3)',b'(lib/read-size) 4)'),original_lib,7,None),
             ('library-empty',original_entry,original_lib.replace(b'[:fs/app-data]',b'[]'),None,'E2176')]
    fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);saved=None
    try:
        if fd!=3:
            try: saved=os.dup(3)
            except OSError: pass
            os.dup2(fd,3)
        def run(args): return subprocess.run(list(map(str,args)),cwd=out,env={'PATH':'/nonexistent','LANG':'C'},pass_fds=(3,),capture_output=True,timeout=180)
        observations=[]
        for name,main_source,lib_source,expected,diagnostic in cases:
            src=out/name/'src';(src/'safety').mkdir(parents=True)
            (src/'main.kotoba').write_bytes(main_source);(src/'safety/fs_library.kotoba').write_bytes(lib_source)
            virtual='/'+name+'/src';lock=out/(name+'.ksl')
            lock.write_text('KSL1\nentry '+virtual+'/main.kotoba\nroot '+virtual+'\nfile '+digest(main_source)+' '+virtual+'/main.kotoba\nfile '+digest(lib_source)+' '+virtual+'/safety/fs_library.kotoba\n')
            payload=out/(name+'.kseed');raw=out/(name+'.raw');image=out/(name+'.macho')
            r=run([compiler,'compile',virtual+'/main.kotoba','--target','aarch64-macos','--output',payload.name,'--source-path',virtual,'--source-lock',lock.name,'--source-lock-sha256',sha(lock)])
            if diagnostic:
                if r.returncode==0 or diagnostic.encode() not in r.stderr or payload.exists(): raise ValueError((name,'refusal',r.returncode,r.stderr[-300:]))
                observations.append({'case':name,'diagnostic':diagnostic,'artifact':False,'lockSha256':sha(lock)});continue
            if r.returncode or r.stderr or not payload.is_file():raise ValueError((name,'compile',r.returncode,r.stderr[-300:]))
            r=run([compiler,'extract-native',payload.name,'--symbol','main','--output',raw.name]);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',r.stdout)
            if r.returncode or r.stderr or not m or int(m[2])!=raw.stat().st_size:raise ValueError((name,'extract'))
            r=run([packager,image.name,raw.name,'fs2-cli-stdio-general',m[1].decode()])
            if r.returncode or r.stderr:raise ValueError((name,'package'))
            image.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(image)],check=True,capture_output=True,timeout=30)
            r=run([image])
            if r.returncode!=expected or r.stderr:raise ValueError((name,'execute',r.returncode,r.stderr[-300:]))
            observations.append({'case':name,'exit':r.returncode,'lockSha256':sha(lock),'payloadSha256':sha(payload),'imageSha256':sha(image)})
    finally:
        if fd!=3:
            if saved is None: os.close(3)
            else: os.dup2(saved,3);os.close(saved)
        os.close(fd)
    if any(sha(p)!=pins[str(p)] for p in inputs):raise ValueError('input drift')
    receipt={'status':'PASS_MODULE_CAPABILITY_SLICE','inputs':pins,'observations':observations,'hostGrant':'test-only FD3 data file','fullAdmissionQualified':False,'nativeControllerGate':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])
if __name__=='__main__':main()
