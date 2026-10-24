#!/usr/bin/env python3
"""Observe all-caller fixed extent contracts through real native linking."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers

ENTRY='''(ns entry (:require [lib.bridge :as b]) (:export [main]))
(defn main [] :i64
 (let [p (kernel-owned-page 0) saved (kernel-load-u64-4k p 4096 0)
       write (kernel-store-u64-4k p 4096 0 42)
       value (b/through p 0)
       restored (kernel-store-u64-4k p 4096 0 saved)]
  (if (and (= write 42) (= value 42) (= restored saved)) 42 0)))
'''
BRIDGE='''(ns lib.bridge (:require [lib.memory :as m]) (:export [through]))
(defn through [base :i64 index :i64] :i64 (m/read base index))
'''
MEMORY='''(ns lib.memory (:export [read]))
(defn- leaf [base :i64 index :i64] :i64 (kernel-load-u64-4k base 4096 index))
(defn read [base :i64 index :i64] :i64 (leaf base index))
'''
RECURSIVE='''(ns lib.memory (:export [read]))
(defn- leaf [base :i64 index :i64 remaining :i64] :i64
 (if (= remaining 0) (kernel-load-u64-4k base 4096 index)
  (leaf base index (- remaining 1))))
(defn read [base :i64 index :i64] :i64 (leaf base index 3))
'''

def pin(p):
 raw=p.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main(build,out):
 graph,producers,_=load_native_producers(build=build);out.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  scope=out/compiler.stem;(scope/'lib').mkdir(parents=True)
  entry,bridge,memory=[scope/p for p in ['entry.kotoba','lib/bridge.kotoba','lib/memory.kotoba']]
  lock=scope/'source.ksl';calls=[];artifacts={}
  def compile_(name,e=ENTRY,b=BRIDGE,m=MEMORY,bad=False):
   entry.write_text(e);bridge.write_text(b);memory.write_text(m)
   lock.write_text(f'KSL1\nentry {entry}\nroot {scope}\n'+''.join(f'file {pin(p)["sha256"]} {p}\n' for p in sorted([entry,bridge,memory])))
   image=scope/(name+'.elf');env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(scope))
   args=[str(compiler),'compile',str(entry),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
   r=subprocess.run(args,env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),sources={str(p.relative_to(scope)):p.read_text() for p in [entry,bridge,memory]}));(scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if bad:assert r.returncode==1 and b'E7106' in r.stderr and not image.exists(),calls[-1]
   else:
    assert r.returncode==0 and not r.stderr and image.exists(),calls[-1]
    efi=scope/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi)],env=env,capture_output=True,timeout=180);assert q.returncode==0 and not q.stderr,q.stderr
    artifacts[name]=dict(kernel=pin(image),efi=pin(efi))
  compile_('fixed-helper')
  compile_('identity-recursion',m=RECURSIVE)
  compile_('identity-nontail-recursion',m=RECURSIVE.replace('(leaf base index (- remaining 1))','(+ 0 (leaf base index (- remaining 1)))'))
  compile_('wrong-extent',m=MEMORY.replace('base 4096 index','base 64 index'),bad=True)
  compile_('literal-caller',e=ENTRY.replace('(b/through p 0)','(b/through 4096 0)'),bad=True)
  compile_('computed-caller',e=ENTRY.replace('(b/through p 0)','(b/through (+ p 0) 0)'),bad=True)
  compile_('second-forged-caller',b=BRIDGE+'\n(defn- bad [] :i64 (m/read 4096 0))\n',bad=True)
  compile_('mixed-extents',e=ENTRY.replace('value (b/through p 0)','other (b/through (kernel-owned-window 0 8192) 0) value (b/through p 0)'),bad=True)
  compile_('recursive-pointer-change',m=RECURSIVE.replace('(leaf base index (- remaining 1))','(leaf (+ base 8) index (- remaining 1))'),bad=True)
  compile_('unseeded-recursion',e='(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 42)\n',m=RECURSIVE,bad=True)
  routes.append(dict(compiler=pin(compiler),artifacts=artifacts,refusals=7))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_FIXED_EXTENT_HELPERS',source=graph,routes=routes,guestExecution=False,fullKernel=False,nativeCDCI=False)
 (out/'native-fixed-extent.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'uniform rooted callers, identity recursion,7 refusals; guest separate')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve(),a.output.resolve())
