#!/usr/bin/env python3
"""Observe two vector write boundaries in native macOS ARM; not a safety gate."""
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
FIXTURES=ROOT/'test/fixtures/selfhost/safety-boundaries/vector-bounds'
CASES={'first':42,'last':42,'upper':-signal.SIGILL,'negative':-signal.SIGILL}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('compiler','packager','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    if (platform.system(),platform.machine())!=('Darwin','arm64'):raise ValueError('requires macOS arm64')
    compiler,packager=(p.resolve(strict=True) for p in (a.compiler,a.packager))
    for p in (compiler,packager):subprocess.run(['/usr/bin/codesign','--verify','--strict',str(p)],check=True,capture_output=True,timeout=30)
    inputs=[compiler,packager,Path(__file__).resolve(),*[FIXTURES/(n+'.kotoba') for n in CASES]]
    pins={str(p):sha(p) for p in inputs};out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    for n in CASES:shutil.copyfile(FIXTURES/(n+'.kotoba'),out/(n+'.kotoba'))
    fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);saved=None
    try:
        if fd!=3:
            try:saved=os.dup(3)
            except OSError:pass
            os.dup2(fd,3)
        def run(*args):return subprocess.run(list(map(str,args)),cwd=out,env={'PATH':'/nonexistent','LANG':'C'},pass_fds=(3,),capture_output=True,timeout=180)
        rows=[]
        for name,expected in CASES.items():
            payload=out/(name+'.kseed');raw=out/(name+'.raw');image=out/(name+'.macho')
            r=run(compiler,'compile','/'+name+'.kotoba','--target','aarch64-macos','--output',payload.name)
            if r.returncode or r.stderr:raise RuntimeError((name,'compile',r.returncode,r.stderr[-300:]))
            r=run(compiler,'extract-native',payload.name,'--symbol','main','--output',raw.name);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',r.stdout)
            if r.returncode or r.stderr or not m or int(m[2])!=raw.stat().st_size:raise RuntimeError((name,'extract'))
            r=run(packager,image.name,raw.name,'fs2-cli-stdio-general',m[1].decode())
            if r.returncode or r.stderr:raise RuntimeError((name,'package',r.stderr[-300:]))
            image.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(image)],check=True,capture_output=True,timeout=30)
            r=run(image)
            if r.returncode!=expected or r.stdout or r.stderr:raise RuntimeError((name,'execute',r.returncode,r.stdout[:100],r.stderr[:100]))
            rows.append({'case':name,'exit':r.returncode,'sourceSha256':sha(out/(name+'.kotoba')),'payloadSha256':sha(payload),'imageSha256':sha(image)})
    finally:
        if fd!=3:
            if saved is None:os.close(3)
            else:os.dup2(saved,3);os.close(saved)
        os.close(fd)
    if any(sha(Path(p))!=v for p,v in pins.items()):raise ValueError('input drift')
    receipt={'status':'PASS_NATIVE_VECTOR_WRITE_BOUNDARY_SLICE','inputs':pins,'observations':rows,'target':'aarch64-macos','fullMemorySafetyQualified':False,'otherOperationsAndTargetsQualified':False,'nativeControllerGate':False}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])

if __name__=='__main__':main()
