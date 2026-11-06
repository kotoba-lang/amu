#!/usr/bin/env python3
"""Observe omitted capability declarations with/without an FD3 test host.

This is a bounded Mac native probe, not a project-admission or safety gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'test/fixtures/selfhost/safety-boundaries/fs-omitted.kotoba'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('compiler','packager','output'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    if (platform.system(),platform.machine())!=('Darwin','arm64'):raise ValueError('requires macOS ARM64')
    compiler,packager=(p.resolve(strict=True) for p in (a.compiler,a.packager))
    for p in (compiler,packager):subprocess.run(['/usr/bin/codesign','--verify','--strict',str(p)],check=True,capture_output=True,timeout=30)
    tracked=[compiler,packager,SOURCE,Path(__file__).resolve()];pins={str(p):sha(p) for p in tracked}
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'data').write_bytes(b'abc')
    source=SOURCE.read_bytes();expected=b') 3)';decl=b'(:export [main]))'
    if source.count(expected)!=1 or source.count(decl)!=1:raise ValueError('fixture anchor changed')
    variants={'omitted':source,'wrong-result':source.replace(expected,b') 4)',1),'explicit-empty':source.replace(decl,b'(:export [main]) (:capabilities []))',1)}
    (out/'src').mkdir()
    for name,content in variants.items():(out/'src'/(name+'.kotoba')).write_bytes(content)
    fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
    if fd!=3:os.dup2(fd,3)
    def invoke(image,*args,grant=True):
        return subprocess.run([str(image),*map(str,args)],cwd=out,env={'PATH':'/nonexistent','LANG':'C'},pass_fds=(3,) if grant else (),capture_output=True,timeout=180)
    observed=[]
    for name in variants:
        src=out/'src'/(name+'.kotoba');lock=out/(name+'.ksl')
        lock.write_text('KSL1\nentry /src/'+src.name+'\nroot /src\nfile '+sha(src)+' /src/'+src.name+'\n')
        payload=out/(name+'.kseed');r=invoke(compiler,'compile','/src/'+src.name,'--target','aarch64-macos','--output',payload.name,'--source-path','/src','--source-lock',lock.name,'--source-lock-sha256',sha(lock))
        if name=='explicit-empty':
            if r.returncode==0 or b'E2176' not in r.stderr or payload.exists():raise ValueError(('empty declaration did not refuse',r.returncode,r.stderr[-300:]))
            observed.append({'case':name,'diagnostic':'E2176','artifact':False});continue
        if r.returncode or r.stderr or not payload.is_file():raise ValueError(('compile failed',name,r.returncode,r.stderr[-300:]))
        raw=out/(name+'.raw');r=invoke(compiler,'extract-native',payload.name,'--symbol','main','--output',raw.name);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',r.stdout)
        if r.returncode or r.stderr or not m or int(m[2])!=raw.stat().st_size:raise ValueError(('extract failed',name))
        image=out/(name+'.macho');r=invoke(packager,image.name,raw.name,'fs2-cli-stdio-general',m[1].decode())
        if r.returncode or r.stderr:raise ValueError(('package failed',name,r.returncode))
        image.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(image)],check=True,capture_output=True,timeout=30)
        r=invoke(image);expected_exit=42 if name=='omitted' else 7
        if r.returncode!=expected_exit or r.stderr:raise ValueError(('granted host result',name,r.returncode,r.stderr[-300:]))
        observed.append({'case':name,'fd3':'granted','exit':r.returncode,'sourceSha256':sha(src),'imageSha256':sha(image)})
        if name=='omitted':
            r=invoke(image,grant=False)
            if r.returncode!=-signal.SIGTRAP or r.stderr:raise ValueError(('closed FD3 result',r.returncode,r.stderr[-300:]))
            observed.append({'case':name,'fd3':'closed','signal':'SIGTRAP'})
    if any(sha(p)!=pins[str(p)] for p in tracked):raise ValueError('input changed during probe')
    receipt={'status':'PASS_OMITTED_CAPABILITY_OBSERVATION','inputs':pins,'observations':observed,'target':'aarch64-macos','projectAdmissionQualified':False,'hostProviderDenialQualified':False,'fullSafetyQualification':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])
if __name__=='__main__':main()
