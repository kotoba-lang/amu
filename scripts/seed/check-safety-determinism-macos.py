#!/usr/bin/env python3
"""Observe repeatability of one source-locked pure native fixture on macOS ARM.

Python stages data, invokes the selfhost compiler/packager, and checks their
results. This is not a full deterministic-build or safety qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'test/fixtures/selfhost/safety-boundaries/determinism.kotoba'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('compiler','packager','output'): ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    if (platform.system(),platform.machine()) != ('Darwin','arm64'): raise ValueError('requires macOS ARM64')
    compiler,packager=(p.resolve(strict=True) for p in (a.compiler,a.packager))
    for p in (compiler,packager): subprocess.run(['/usr/bin/codesign','--verify','--strict',str(p)],check=True,capture_output=True,timeout=30)
    inputs=[compiler,packager,FIXTURE,Path(__file__).resolve()];pins={str(p):sha(p) for p in inputs}
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=FIXTURE.read_bytes();old=b'(mix 20) 42)';new=b'(mix 20) 41)'
    if source.count(old)!=1:raise ValueError('mutation anchor changed')
    root=out/'fixture'/'src';root.mkdir(parents=True)
    virtual='/fixture/src';lock=out/'fixture.ksl'
    def stage(data):
        (root/'main.kotoba').write_bytes(data)
        lock.write_text('KSL1\nentry '+virtual+'/main.kotoba\nroot '+virtual+'\nfile '+sha(root/'main.kotoba')+' '+virtual+'/main.kotoba\n')
    stage(source);original_lock_sha=sha(lock)
    fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);saved=None
    try:
        if fd!=3:
            try:saved=os.dup(3)
            except OSError:pass
            os.dup2(fd,3)
        def run(*args):return subprocess.run(list(map(str,args)),cwd=out,env={'PATH':'/nonexistent','LANG':'C'},pass_fds=(3,),capture_output=True,timeout=180)
        observations=[]
        for out_name,expected in (('first',42),('second',42),('changed',7)):
            if out_name=='changed':
                stage(source.replace(old,new,1))
                rejected=out/'stale-lock.kseed'
                refusal=run(compiler,'compile',virtual+'/main.kotoba','--target','aarch64-macos','--output',rejected.name,'--source-path',virtual,'--source-lock',lock.name,'--source-lock-sha256',original_lock_sha)
                if refusal.returncode==0 or rejected.exists():raise ValueError(('stale lock accepted',refusal.returncode))
            payload=out/(out_name+'.kseed');raw=out/(out_name+'.raw');image=out/(out_name+'.macho')
            r=run(compiler,'compile',virtual+'/main.kotoba','--target','aarch64-macos','--output',payload.name,'--source-path',virtual,'--source-lock',lock.name,'--source-lock-sha256',sha(lock))
            if r.returncode or r.stderr or not payload.is_file():raise ValueError((out_name,'compile',r.returncode,r.stderr[-300:]))
            r=run(compiler,'extract-native',payload.name,'--symbol','main','--output',raw.name);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',r.stdout)
            if r.returncode or r.stderr or not m or int(m[2])!=raw.stat().st_size:raise ValueError((out_name,'extract'))
            r=run(packager,image.name,raw.name,'fs2-cli-stdio-general',m[1].decode())
            if r.returncode or r.stderr:raise ValueError((out_name,'package',r.returncode,r.stderr[-300:]))
            image.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(image)],check=True,capture_output=True,timeout=30)
            r=run(image)
            if r.returncode!=expected or r.stderr:raise ValueError((out_name,'execute',r.returncode,r.stderr[-300:]))
            observations.append({'case':out_name,'exit':r.returncode,'sourceSha256':sha(root/'main.kotoba'),'lockSha256':sha(lock),'payloadSha256':sha(payload),'rawSha256':sha(raw)})
    finally:
        if fd!=3:
            if saved is None:os.close(3)
            else:os.dup2(saved,3);os.close(saved)
        os.close(fd)
    if observations[0]['payloadSha256']!=observations[1]['payloadSha256'] or observations[0]['rawSha256']!=observations[1]['rawSha256']:raise ValueError('same-input outputs differ')
    if observations[0]['payloadSha256']==observations[2]['payloadSha256']:raise ValueError('source mutation did not change artifact')
    if any(sha(p)!=pins[str(p)] for p in inputs):raise ValueError('input drift')
    receipt={'status':'PASS_PURE_NATIVE_REPEATABILITY_SLICE','inputs':pins,'observations':observations,'sameSourceLockAndTarget':True,'differentOutputNames':True,'mutationChangedResultAndArtifact':True,'staleLockRefused':True,'target':'aarch64-macos','fullDeterminismQualified':False,'fullSafetyQualified':False,'nativeControllerGate':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])
if __name__=='__main__':main()
