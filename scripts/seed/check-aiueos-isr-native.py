#!/usr/bin/env python3
"""Observe the native ISR table's shape and compile-time refusal controls.

QEMU interrupt execution and its failing marker control run separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers

SOURCE='''(ns entry (:export [main aiueos-isr-3]))
(defn aiueos-isr-3 [vector :i64 error :i64 rip :i64 rsp :i64] :i64
 (let [r (kernel-subregion (kernel-boot-info) 16544 152 8)
       value (if (and (= vector 3) (= error 0) (>= rip 1052672) (> rsp 0)) 42 0)
       mark (kernel-store-u32 r 8 0 value)]
  (+ mark 1234)))
(defn main [] :i64
 (let [boot (kernel-boot-info)
       workspace (kernel-subregion boot 16544 12448 4096)
       idt (kernel-subregion workspace 4096 0 64)
       descriptor (kernel-subregion workspace 4096 512 10)
       record (kernel-subregion boot 16544 152 8)
       saved (kernel-load-u64 record 8 0)
       clear (kernel-store-u32 record 8 0 0)
       address (kernel-isr-entry-address 3) cs (kernel-read-cs)
       s0 (kernel-store-u16 idt 64 48 (bit-and address 65535))
       s1 (kernel-store-u16 idt 64 50 cs)
       s2 (kernel-store-u8 idt 64 52 0)
       s3 (kernel-store-u8 idt 64 53 142)
       s4 (kernel-store-u16 idt 64 54 (bit-and (u64-shift-right address 16) 65535))
       s5 (kernel-store-u32 idt 64 56 (u64-shift-right address 32))
       s6 (kernel-store-u32 idt 64 60 0)
       d0 (kernel-store-u16 descriptor 10 0 63)
       d1 (kernel-store-u32 descriptor 10 2 (bit-and idt 4294967295))
       d2 (kernel-store-u32 descriptor 10 6 (u64-shift-right idt 32))
       loaded (kernel-load-idt descriptor 10)
       fired (if (= loaded 1) (kernel-debug-break) 0)
       received (kernel-load-u32 record 8 0)
       restored (kernel-store-u64 record 8 0 saved)]
  (if (and (= loaded 1) (= fired 0) (= received 42) (= restored saved)
           (= clear 0) (= cs 8) (> address 1052672)
           (= s0 (bit-and address 65535)) (= s1 cs) (= s2 0) (= s3 142)
           (= s4 (bit-and (u64-shift-right address 16) 65535))
           (= s5 (u64-shift-right address 32)) (= s6 0) (= d0 63)
           (= d1 (bit-and idt 4294967295)) (= d2 (u64-shift-right idt 32))) 42 0)))
'''


def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())


def verify(image):
 b=image.read_bytes();ph=struct.unpack_from('<Q',b,32)[0]
 rx=struct.unpack_from('<IIQQQQQQ',b,ph);rw=struct.unpack_from('<IIQQQQQQ',b,ph+56)
 table=struct.unpack_from('<Q',b,rw[2]+328)[0]
 assert table>=rx[3] and table+8192<=rx[3]+rx[5] and table%128==0
 at=rx[2]+table-rx[3];slot=b[at+3*128:at+4*128]
 assert slot[:2]==b'\x6a\0' and slot[25]==0xfc and slot[26:29]==bytes.fromhex('4c8d0d')
 assert struct.unpack_from('<i',slot,29)[0]+table+3*128+33==rw[3]
 assert slot[33:41]==bytes.fromhex('41ff710849c74108') and struct.unpack_from('<I',slot,41)[0]==4096
 assert slot[45]==191 and struct.unpack_from('<I',slot,46)[0]==3 and slot[74]==232
 body=table+3*128+79+struct.unpack_from('<i',slot,75)[0]
 assert rx[3]+77<=body<table and slot[79:83]==bytes.fromhex('418f4108') and slot[110:112]==bytes.fromhex('48cf')
 assert slot[112:]==bytes([204])*16
 for v in range(64):
  if v not in (3,6):assert b[at+v*128:at+(v+1)*128]==bytes.fromhex('faf4ebfd')+bytes([204])*124
 assert b[at+6*128]==250 and b[at+6*128+35:at+7*128]==bytes([204])*93
 return dict(vectors=64,stride=128,table=table,context=rw[3],body=body,entryFuel=4096)


def main(build,out):
 graph,producers,_=load_native_producers(build=build);out.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  scope=out/compiler.stem;scope.mkdir();source=scope/'entry.kotoba';lock=scope/'source.ksl';calls=[];artifacts={}
  def compile_(name,text,diagnostic=None):
   source.write_text(text);lock.write_text(f'KSL1\nentry {source}\nroot {scope}\nfile {pin(source)["sha256"]} {source}\n');image=scope/(name+'.elf')
   env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(scope))
   args=[str(compiler),'compile',str(source),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
   r=subprocess.run(args,env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),source=pin(source),sourceText=text));(scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if diagnostic:assert r.returncode==1 and diagnostic.encode() in r.stderr and b'KEXE_TRAP' not in r.stderr and not image.exists(),calls[-1]
   else:
    assert r.returncode==0 and not r.stderr and image.exists(),calls[-1]
    shape=verify(image);efi=scope/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi)],env=env,capture_output=True,timeout=180);assert q.returncode==0 and not q.stderr,q.stderr
    artifacts[name]=dict(kernel=pin(image),efi=pin(efi),shape=shape)
  compile_('interrupt',SOURCE)
  compile_('wrong-marker',SOURCE.replace(')) 42 0)', ')) 43 0)',1))
  for name,text,code in [
   ('invalid-vector',SOURCE.replace('aiueos-isr-3','aiueos-isr-64'),'E7102'),
   ('leading-zero',SOURCE.replace('aiueos-isr-3','aiueos-isr-03'),'E7102'),
   ('bool-parameter',SOURCE.replace('vector :i64','vector :bool').replace('(= vector 3)','vector'),'E7102'),
   ('direct-call',SOURCE.replace('(kernel-debug-break)','(aiueos-isr-3 3 0 1052672 1)'),'E7106'),
   ('hardware-argument-root',SOURCE.replace('(+ mark 1234)','(kernel-load-u8 vector error 0)'),'E7106'),
   ('no-table','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-isr-entry-address 3))\n','E7102'),
   ('unknown-export',SOURCE.replace('[main aiueos-isr-3]','[main aiueos-isr-3 other]')+'\n(defn other [] :i64 0)\n','E7102'),
  ]:compile_(name,text,code)
  routes.append(dict(compiler=pin(compiler),artifacts=artifacts,refusals=7))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_ISR_PACKAGING',source=graph,routes=routes,guestInterruptExecution=False,errorCodeInterruptExecution=False,fullKernel=False,liveRuntime=False,nativeCDCI=False)
 (out/'native-isr.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'64-vector layout, typed callback ABI and 7 refusal controls; interrupt execution separate')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve(),a.output.resolve())
