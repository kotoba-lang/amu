#!/usr/bin/env python3
"""Observe native v3 admission and refusals; hardware entry is a QEMU gate."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from aiueos_native_proof import load_native_producers
from check_aiueos_value_fixture import user_source

def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def main(build,complete,output):
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
   assert rw[5]==0x240000 and struct.unpack_from('<Q',b,rw[2]+464)[0]==0x334c5652
   assert rx[3]+77<struct.unpack_from('<Q',b,rw[2]+30400)[0]<rx[3]+rx[5]
   assert struct.unpack_from('<Q',b,rw[2]+172)[0]==rw[3]+131072
   efi=out/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi),'--pci-resources','v1'],env=env,capture_output=True,timeout=180)
   assert not q.returncode and not q.stderr and efi.read_bytes().count(b)==1
   return dict(kernel=pin(image),efi=pin(efi))
  text=user_source();good=compile_('owned-user-pages',text)
  for vector in (6,13,14):
   conflict=text.replace('(:export [main',f'(:export [aiueos-isr-{vector} main')+f'\n(defn aiueos-isr-{vector} [v :i64 e :i64 p :i64 s :i64] :i64 0)\n'
   compile_(f'reserved-vector-{vector}',conflict,'E7102')
  compile_('partial-family',text.replace('main aiueos-value-runtime-entry','main',1),'E7102')
  compile_('literal-code-address',text.replace('(kernel-value-domain-code-page 73)','1970176'),'E7106')
  compile_('entry-result-is-scalar',text.replace('(kernel-value-domain-code-page 73)','(kernel-value-enter-user 73)'),'E7106')
  routes.append(dict(compiler=pin(compiler),artifacts=good,refusals=6))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_USER_CONTEXT_ADMISSION',source=graph,routes=routes,guestExecution=False,userSyscall=False,nativeCDCI=False)
 (output/'native-user-context.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();main(a.build.resolve() if a.build else None,a.complete.resolve() if a.complete else None,a.output.resolve())
