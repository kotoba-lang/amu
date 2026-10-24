#!/usr/bin/env python3
"""Stage sealed-catalog and fail-closed MMIO fixtures; no platform MMIO pass."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers

CATALOG='''(ns entry (:export [main]))
(defn main [] :i64
 (let [m (kernel-subregion (kernel-boot-info) 16544 160 16384)
       state (kernel-owned-page 14)
       kind (kernel-load-u32-16k m 16384 0)
       base (kernel-load-u64-16k m 16384 8)
       pages (kernel-load-u64-16k m 16384 24)
       k (kernel-store-u64-4k state 4096 0 kind)
       b (kernel-store-u64-4k state 4096 8 base)
       p (kernel-store-u64-4k state 4096 16 pages)
       forged-kind (kernel-store-u32-16k m 16384 0 11)
       forged-base (kernel-store-u64-16k m 16384 8 4096)
       forged-pages (kernel-store-u64-16k m 16384 24 16)]
  (if (and (= k kind) (= b base) (= p pages) (= forged-kind 11)
           (= forged-base 4096) (= forged-pages 16)) 42 0)))
'''
DEEP='''(ns entry (:export [main]))
(defn- deep [n :i64] :i64 (if (= n 0) 42 (+ 1 (deep (- n 1)))))
(defn main [] :i64 (if (> (kernel-owned-page 0) 0) (deep 10000) 0))
'''

def pin(p):
 raw=p.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main(build,out):
 graph,producers,_=load_native_producers(build=build);out.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  scope=out/compiler.stem;scope.mkdir();src=scope/'entry.kotoba';lock=scope/'source.ksl';calls=[];artifacts={}
  def compile_(name,text,bad=False):
   src.write_text(text);lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n');image=scope/(name+'.elf')
   env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(scope))
   r=subprocess.run([str(compiler),'compile',str(src),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']],env=env,capture_output=True,timeout=240)
   calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),sourceText=text));(scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if bad:assert r.returncode==1 and b'E7106' in r.stderr and not image.exists(),calls[-1]
   else:
    assert r.returncode==0 and not r.stderr and image.exists(),calls[-1]
    efi=scope/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(image),'--output',str(efi)],env=env,capture_output=True,timeout=180);assert q.returncode==0 and not q.stderr,q.stderr
    artifacts[name]=dict(kernel=pin(image),efi=pin(efi))
  compile_('catalog',CATALOG)
  compile_('forged-map',CATALOG.replace('42 0)))','(if (> (kernel-firmware-mmio 4096 512) 0) 42 0) 0)))'))
  for name,base,size in [('ram',4096,512),('zero',4096,0),('oversized',4096,65537),('overflow',-4096,8192)]:
   compile_(name,f'(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-firmware-mmio {base} {size}) 0) 42 0))\n')
  compile_('wrong-extent','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-load-u8 (kernel-firmware-mmio 4096 512) 64 0))\n',True)
  compile_('computed-root','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-load-u8 (+ (kernel-firmware-mmio 4096 512) 0) 512 0))\n',True)
  compile_('stack-exhaustion',DEEP)
  compile_('shallow-stack',DEEP.replace('deep 10000','deep 0'))
  routes.append(dict(compiler=pin(compiler),artifacts=artifacts,provenanceRefusals=2))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_FIRMWARE_FIXTURE_PACKAGING',source=graph,routes=routes,guestExecution=False,positivePlatformMMIOQualified=False,fullKernel=False,nativeCDCI=False)
 (out/'native-firmware.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'sealed catalog + stack/bounds fixtures; actual positive MMIO remains open')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve(),a.output.resolve())
