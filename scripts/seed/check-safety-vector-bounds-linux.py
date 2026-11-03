#!/usr/bin/env python3
"""Observe native Linux x86 vector read/write boundaries; not a safety gate."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
FIXTURES=ROOT/'test/fixtures/selfhost/safety-boundaries'
CASES=('first','last','upper','negative')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('compiler','runner','output'):ap.add_argument('--'+n,type=Path,required=True)
    for n in ('compiler-sha256','runner-sha256'):ap.add_argument('--'+n,required=True)
    a=ap.parse_args()
    if (platform.system(),platform.machine())!=('Linux','x86_64'):raise ValueError('requires Linux x86_64')
    compiler,runner=(p.resolve(strict=True) for p in (a.compiler,a.runner))
    if sha(compiler)!=a.compiler_sha256 or sha(runner)!=a.runner_sha256:raise ValueError('binary pin mismatch')
    fixtures=[FIXTURES/d/(n+'.kotoba') for d in ('vector-bounds','vector-write-bounds') for n in CASES]
    inputs=[compiler,runner,Path(__file__).resolve(),*fixtures];pins={str(p):sha(p) for p in inputs}
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    env={'PATH':'/nonexistent','LANG':'C','KEXE_CAP_RESOURCES_35':str(out),'KEXE_STACK_BYTES':'8388608'}
    observations=[]
    for kind,directory in (('read','vector-bounds'),('write','vector-write-bounds')):
        stage=out/kind;stage.mkdir()
        for name in CASES:
            source=stage/(name+'.kotoba');shutil.copyfile(FIXTURES/directory/(name+'.kotoba'),source)
            lock=stage/(name+'.ksl');lock.write_text('KSL1\nentry '+str(source)+'\nroot '+str(stage)+'\nfile '+sha(source)+' '+str(source)+'\n')
            image=stage/(name+'.kx64');raw=stage/(name+'.bin')
            r=subprocess.run([str(compiler),'compile',str(source),'--target','x86_64-linux','--output',str(image),'--format','kx64-v1','--source-path',str(stage),'--source-lock',str(lock),'--source-lock-sha256',sha(lock)],cwd=out,env=env,capture_output=True,timeout=300)
            if r.returncode or r.stderr or not image.is_file():raise RuntimeError((kind,name,'compile',r.returncode,r.stderr[-300:]))
            header,payload=image.read_bytes().split(b'\n\n',1);m=re.fullmatch(rb'KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0',header)
            if not m or int(m[1])!=len(payload):raise ValueError('invalid native container')
            raw.write_bytes(payload)
            r=subprocess.run([str(runner),str(raw),'0','0','x86_64','-','--'],cwd=out,env=dict(env,KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_FUEL='off'),capture_output=True,timeout=120)
            if name in ('first','last'):
                if r.returncode or r.stderr or not re.search(rb':status :ok\s+:result 42\b',r.stdout):raise RuntimeError((kind,name,r.returncode,r.stdout[-300:],r.stderr[-300:]))
                result='ok-42'
            else:
                if r.returncode!=120 or b':status :trap' not in r.stdout or b':signal :SIGILL' not in r.stderr:raise RuntimeError((kind,name,r.returncode,r.stdout[-300:],r.stderr[-300:]))
                result='trap-sigill'
            observations.append({'operation':kind,'case':name,'result':result,'sourceSha256':sha(source),'lockSha256':sha(lock),'payloadSha256':sha(image),'rawSha256':sha(raw)})
    if any(sha(Path(p))!=digest for p,digest in pins.items()):raise ValueError('input drift')
    receipt={'status':'PASS_NATIVE_VECTOR_BOUNDARY_LINUX_SLICE','inputs':pins,'observations':observations,'target':'x86_64-linux','fullMemorySafetyQualified':False,'otherOperationsAndTargetsQualified':False,'nativeControllerGate':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])

if __name__=='__main__':main()
