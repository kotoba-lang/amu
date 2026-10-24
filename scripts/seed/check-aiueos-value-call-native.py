#!/usr/bin/env python3
"""Observe typed role/range admission; actual guest call execution is separate."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from aiueos_native_proof import load_native_producers

ROLES = [
 ('aiueos-value-runtime-entry','a :i64 p :i64 u :i64 r :i64 c :i64',
  '(+ (kernel-load-u8-4k a 4096 0) (kernel-load-u8-4k u 4096 0) (kernel-load-u8 r 96 0) (kernel-load-u8-4k c 4096 0))'),
 ('aiueos-value-runtime-syscall-plan','n :i64 d :i64 p :i64 i :i64 s :i64','0'),
 ('aiueos-value-runtime-publish-domain','d :i64','0'),
 ('aiueos-value-runtime-provider-status','g :i64 a :i64','0'),
 ('aiueos-value-runtime-capability-grant','a :i64 s :i64 g :i64 r :i64 o :i64','0'),
 ('aiueos-value-runtime-provider-claim','','0'),
 ('aiueos-value-runtime-provider-complete','t :i64 r :i64 b :i64 n :i64 d :i64','(kernel-load-u8-16k b n 0)'),
 ('aiueos-value-runtime-cas-verify','b :i64 n :i64 e :i64 o :i64 w :i64',
  '(+ (kernel-load-u8-16k b n 0) (kernel-load-u8 e 32 0) (kernel-load-u8 o 32 0) (kernel-load-u8 w 352 0))')]
SOURCE = '(ns entry (:export [main '+' '.join(r[0] for r in ROLES)+']))\n'+''.join(
 f'(defn {name} [{args}] :i64 {body})\n' for name,args,body in ROLES)+\
 '(defn main [] :i64 (let [r (kernel-value-runtime-invoke 5 0 0 0 0 0)] (+ 42 r)))\n'

def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def main(build, complete, output):
 graph,producers,_=load_native_producers(build,complete);output.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  out=output/compiler.stem;out.mkdir();source=out/'entry.kotoba';lock=out/'source.ksl';calls=[]
  def compile_(name,text,code=None):
   source.write_text(text);lock.write_text(f'KSL1\nentry {source}\nroot {out}\nfile {pin(source)["sha256"]} {source}\n');image=out/(name+'.elf')
   env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(out))
   r=subprocess.run([str(compiler),'compile',str(source),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(out),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']],env=env,capture_output=True,timeout=240)
   calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),source=pin(source)));(out/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if code:
    assert r.returncode==1 and code.encode() in r.stderr and not image.exists(),calls[-1]
    return None
   assert not r.returncode and not r.stderr,calls[-1]
   b=image.read_bytes();rx=struct.unpack_from('<IIQQQQQQ',b,64);rw=struct.unpack_from('<IIQQQQQQ',b,120)
   targets=struct.unpack_from('<8Q',b,rw[2]+30208)
   assert rw[5]==147456 and len(set(targets))==8 and all(rx[3]+77<p<rx[3]+rx[5] for p in targets)
   assert struct.unpack_from('<Q',b,rw[2]+172)[0]==rw[3]+131072
   assert struct.unpack_from('<Q',b,rw[2]+328)[0]==0,'typed roles must not become ISR callbacks'
   efi=out/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi),'--pci-resources','v1'],env=env,capture_output=True,timeout=180)
   assert not q.returncode and not q.stderr and efi.read_bytes().count(b)==1
   return dict(kernel=pin(image),efi=pin(efi))
  good=compile_('typed-roles',SOURCE)
  compile_('partial-family',SOURCE.replace('main aiueos-value-runtime-entry','main',1),'E7102')
  compile_('wrong-role-type',SOURCE.replace('[g :i64 a :i64]','[g :i64 a :bool]'),'E7102')
  compile_('extra-export',SOURCE.replace('(:export [main','(:export [other main')+'(defn other [] :i64 0)\n','E7102')
  compile_('direct-role-call',SOURCE.replace('(kernel-value-runtime-invoke 5 0 0 0 0 0)','(aiueos-value-runtime-provider-claim)'),'E7106')
  compile_('scalar-role-is-not-region',SOURCE.replace('(defn aiueos-value-runtime-publish-domain [d :i64] :i64 0)','(defn aiueos-value-runtime-publish-domain [d :i64] :i64 (kernel-load-u8 d 512 0))'),'E7106')
  compile_('computed-abi-pointer',SOURCE.replace('(kernel-load-u8-16k b n 0)','(kernel-load-u8-16k (+ b 0) n 0)'),'E7106')
  compile_('unbound-invoke','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-value-runtime-invoke 5 0 0 0 0 0))\n','E7102')
  routes.append(dict(compiler=pin(compiler),artifacts=good,refusals=7))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_TYPED_VALUE_CALL_ADMISSION',source=graph,routes=routes,guestExecution=False,userSyscall=False,nativeCDCI=False)
 (output/'native-value-call.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();main(a.build.resolve() if a.build else None,a.complete.resolve() if a.complete else None,a.output.resolve())
