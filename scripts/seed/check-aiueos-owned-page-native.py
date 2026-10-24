#!/usr/bin/env python3
"""Observe the bounded slot constructor and immutable pre-main metadata seal."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers

SOURCE='''(ns entry (:export [main]))
(defn main [] :i64
 (let [header (kernel-subregion (kernel-boot-info) 16544 0 160)
       original (kernel-load-u64 header 160 80)
       changed (kernel-store-u64 header 160 80 0)
       first (kernel-owned-page 0) last (kernel-owned-page 14)
       saved (kernel-load-u64-4k first 4096 0)
       stored (kernel-store-u8-4k first 4096 0 42)
       readback (kernel-load-u8-4k first 4096 0)
       restored (kernel-store-u64-4k first 4096 0 saved)
       metadata (kernel-store-u64 header 160 80 original)]
  (if (and (> original 0) (= first original) (= (- last first) 57344)
           (= (bit-and first 4095) 0) (= changed 0) (= stored 42)
           (= readback 42) (= restored saved) (= metadata original)) 42 0)))
'''


def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())


def main(build, out, complete=None):
 graph,producers,_=load_native_producers(build=build, complete=complete);out.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  scope=out/compiler.stem;scope.mkdir();src=scope/'entry.kotoba';lock=scope/'source.ksl';calls=[];artifacts={}
  def compile_(name,text,bad=False):
   src.write_text(text);lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n');image=scope/(name+'.elf')
   env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(scope))
   args=[str(compiler),'compile',str(src),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
   r=subprocess.run(args,env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),sourceText=text));(scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if bad:assert r.returncode==1 and b'E7106' in r.stderr and not image.exists(),calls[-1]
   else:
    assert r.returncode==0 and not r.stderr and image.exists(),calls[-1]
    efi=scope/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi)],env=env,capture_output=True,timeout=180);assert q.returncode==0 and not q.stderr,q.stderr
    artifacts[name]=dict(kernel=pin(image),efi=pin(efi))
  compile_('sealed-pages',SOURCE)
  for name,slot in [('invalid-slot','15'),('negative-slot','-1'),('valid-slot','0')]:
   compile_(name,f'(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-owned-page {slot}) 0) 42 0))\n')
  compile_('loaded-pointer',SOURCE.replace('(kernel-load-u8-4k first 4096 0)','(kernel-load-u8-4k original 4096 0)'),True)
  compile_('computed-pointer',SOURCE.replace('(kernel-load-u8-4k first 4096 0)','(kernel-load-u8-4k (+ first 0) 4096 0)'),True)
  compile_('wrong-length',SOURCE.replace('(kernel-load-u8-4k first 4096 0)','(kernel-load-u8-4k first 64 0)'),True)
  compile_('forged-recovery-pages','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-configure-page-fault-recovery 4096 8192))\n',True)
  routes.append(dict(compiler=pin(compiler),artifacts=artifacts,compileRefusals=4))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_OWNED_PAGE_PACKAGING',source=graph,routes=routes,guestExecution=False,nativeCDCI=False,fullKernel=False,liveRuntime=False)
 (out/'native-owned-page.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'15 sealed pages, mutable-header forgery fixture and4 refusal controls; guest execution separate')


if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve() if a.build else None, a.output.resolve(), a.complete.resolve() if a.complete else None)
