#!/usr/bin/env python3
"""Observe source-locked pure fixture repeatability on native Linux x86_64.

Python only stages files and observes pinned Amu native compiler/runner output.
This is not a full determinism or safety qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'test/fixtures/selfhost/safety-boundaries/determinism.kotoba'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('compiler','runner','output'):ap.add_argument('--'+n,type=Path,required=True)
    for n in ('compiler-sha256','runner-sha256'):ap.add_argument('--'+n,required=True)
    a=ap.parse_args()
    if (platform.system(),platform.machine())!=('Linux','x86_64'):raise ValueError('requires Linux x86_64')
    compiler,runner=(p.resolve(strict=True) for p in (a.compiler,a.runner))
    if sha(compiler)!=a.compiler_sha256 or sha(runner)!=a.runner_sha256:raise ValueError('binary pin mismatch')
    inputs=[compiler,runner,FIXTURE,Path(__file__).resolve()];pins={str(p):sha(p) for p in inputs}
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);root=out/'src';root.mkdir();entry=root/'main.kotoba';lock=out/'fixture.ksl'
    source=FIXTURE.read_bytes();old=b'(mix 20) 42)';new=b'(mix 20) 41)'
    if source.count(old)!=1:raise ValueError('mutation anchor changed')
    def stage(data):
        entry.write_bytes(data)
        lock.write_text('KSL1\nentry '+str(entry)+'\nroot '+str(root)+'\nfile '+sha(entry)+' '+str(entry)+'\n')
    stage(source);original_lock_sha=sha(lock)
    env={'PATH':'/nonexistent','LANG':'C','KEXE_CAP_RESOURCES_35':str(out),'KEXE_STACK_BYTES':'8388608'}
    def compile_to(image,lock_sha):
        return subprocess.run([str(compiler),'compile',str(entry),'--target','x86_64-linux','--output',str(image),'--format','kx64-v1','--source-path',str(root),'--source-lock',str(lock),'--source-lock-sha256',lock_sha],cwd=out,env=env,capture_output=True,timeout=300)
    observations=[]
    for name,expected in (('first',42),('second',42),('changed',7)):
        if name=='changed':
            stage(source.replace(old,new,1));rejected=out/'stale.kx64';r=compile_to(rejected,original_lock_sha)
            if r.returncode==0 or rejected.exists():raise ValueError(('stale lock accepted',r.returncode))
        image=out/(name+'.kx64');r=compile_to(image,sha(lock))
        if r.returncode or r.stderr or not image.is_file():raise ValueError((name,'compile',r.returncode,r.stderr[-300:]))
        header,payload=image.read_bytes().split(b'\n\n',1);m=re.fullmatch(rb'KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0',header)
        if not m or int(m[1])!=len(payload):raise ValueError('invalid native container')
        raw=out/(name+'.bin');raw.write_bytes(payload)
        r=subprocess.run([str(runner),str(raw),'0','0','x86_64','-','--'],cwd=out,env=dict(env,KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_FUEL='off'),capture_output=True,timeout=120)
        if r.returncode or r.stderr or not re.search(rb':status :ok\s+:result '+str(expected).encode()+rb'\b',r.stdout):raise ValueError((name,'execute',r.returncode,r.stdout[-300:],r.stderr[-300:]))
        observations.append({'case':name,'result':expected,'sourceSha256':sha(entry),'lockSha256':sha(lock),'payloadSha256':sha(image),'rawSha256':sha(raw)})
    if observations[0]['payloadSha256']!=observations[1]['payloadSha256'] or observations[0]['rawSha256']!=observations[1]['rawSha256']:raise ValueError('same input outputs differ')
    if observations[0]['payloadSha256']==observations[2]['payloadSha256']:raise ValueError('changed source produced same artifact')
    if any(sha(p)!=pins[str(p)] for p in inputs):raise ValueError('input drift')
    receipt={'status':'PASS_PURE_NATIVE_REPEATABILITY_X86_SLICE','inputs':pins,'observations':observations,'sameSourceLockAndTarget':True,'differentOutputNames':True,'mutationChangedResultAndArtifact':True,'staleLockRefused':True,'target':'x86_64-linux','fullDeterminismQualified':False,'fullSafetyQualified':False,'nativeControllerGate':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])
if __name__=='__main__':main()
