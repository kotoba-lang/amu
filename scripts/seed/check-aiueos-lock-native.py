#!/usr/bin/env python3
"""Observe native CAS lock/unlock and extended-control-register fixtures.

The owner fixes 0->1 / 1->0 and returns the swap's Boolean result. The
privileged guest tests run separately; this observer does not own CDCI.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers

LOCK='''(ns entry (:export [main]))
(defn main [] :i64
 (let [r (kernel-subregion (kernel-boot-info) 16544 152 8)
       saved (kernel-load-u64 r 8 0)
       cleared (kernel-store-u32 r 8 0 0)
       a (kernel-try-lock-u32 r 8 0)
       held (kernel-load-u32 r 8 0)
       b (kernel-try-lock-u32 r 8 0)
       u (kernel-unlock-u32 r 8 0)
       free (kernel-load-u32 r 8 0)
       v (kernel-unlock-u32 r 8 0)
       other (kernel-store-u32 r 8 0 2)
       denied (kernel-unlock-u32 r 8 0)
       unchanged (kernel-load-u32 r 8 0)
       z (kernel-store-u32 r 8 1 0)
       odd (kernel-try-lock-u32 r 8 1)
       odd-held (kernel-load-u8 r 8 1)
       odd-u (kernel-unlock-u32 r 8 1)
       restored (kernel-store-u64 r 8 0 saved)]
   (if (and (= cleared 0) (= a 1) (= held 1) (= b 0)
            (= u 1) (= free 0) (= v 0) (= other 2) (= denied 0)
            (= unchanged 2) (= z 0) (= odd 1) (= odd-held 1)
            (= odd-u 1) (= restored saved)) 42 0)))
'''
XCR='''(ns entry (:export [main]))
(defn main [] :i64
 (let [features (kernel-cpuid-ecx 1 0) old (kernel-read-cr4)
       enabled (kernel-write-cr4 (bit-or old 262144))
       xcr (kernel-xgetbv 0) written (kernel-xsetbv 0 xcr)
       readback (kernel-xgetbv 0) restored (kernel-write-cr4 old)]
  (if (and (not= (bit-and features 67108864) 0)
           (= enabled (bit-or old 262144)) (= xcr written)
           (= readback xcr) (= restored old)) 42 0)))
'''


def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())


def main(build,out):
 graph,producers,_=load_native_producers(build=build);out.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  scope=out/compiler.stem;scope.mkdir();src=scope/'entry.kotoba';lock=scope/'source.ksl';calls=[];artifacts={}
  def compile_(name,text,ok=True):
   src.write_text(text);lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n');image=scope/(name+'.elf')
   env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(scope))
   args=[str(compiler),'compile',str(src),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
   r=subprocess.run(args,env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),source=pin(src),sourceText=text));(scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if ok:
    assert r.returncode==0 and not r.stderr and image.exists(),calls[-1]
    efi=scope/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi)],env=env,capture_output=True,timeout=180);assert q.returncode==0 and not q.stderr,q.stderr;artifacts[name]=dict(kernel=pin(image),efi=pin(efi))
   else:assert r.returncode==1 and b'E7106' in r.stderr and not image.exists(),calls[-1]
  compile_('lock',LOCK);compile_('xcr',XCR)
  compile_('lock-oversized','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-try-lock-u32 (kernel-boot-info) 16544 0))\n')
  compile_('literal-lock',LOCK.replace('(kernel-try-lock-u32 r 8 0)','(kernel-try-lock-u32 1089536 8 0)'),False)
  compile_('wrong-lock-length',LOCK.replace('(kernel-try-lock-u32 r 8 0)','(kernel-try-lock-u32 r 64 0)'),False)
  compile_('wrong-unlock-length',LOCK.replace('(kernel-unlock-u32 r 8 0)','(kernel-unlock-u32 r 64 0)'),False)
  routes.append(dict(compiler=pin(compiler),artifacts=artifacts,refusals=3))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_LOCK_PACKAGING',source=graph,routes=routes,guestExecution=False,ISRLiveRuntime=False,fullKernel=False,nativeCDCI=False)
 (out/'native-lock.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'CAS success/failure/preserved word/unaligned; XCR0 read/write; guest gates separate')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve(),a.output.resolve())
