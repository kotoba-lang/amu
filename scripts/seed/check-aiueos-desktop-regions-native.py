#!/usr/bin/env python3
"""Native admission/refusal evidence for closed GOP/Browser/font regions."""
import argparse,hashlib,json,runpy,struct,subprocess
from pathlib import Path
from aiueos_native_proof import load_native_producers
HERE=Path(__file__).resolve().parent
BASE=runpy.run_path(str(HERE/'check-aiueos-value-call-native.py'))['SOURCE']
SOURCE=BASE[:BASE.index('(defn main ')]+'''(defn main [] :i64
  (let [s (kernel-browser-surface) c (kernel-browser-context)
        f (kernel-native-font) p (kernel-framebuffer-page 0)
        a (kernel-store-u32 (kernel-subregion s 8192 0 4) 4 0 42)
        b (kernel-store-u32 (kernel-subregion c 8192 0 4) 4 0 7)
        font (kernel-subregion f 524288 0 16384)]
    (+ (kernel-load-u32-4k p 4096 0)
       (kernel-load-u32-16k font 16384 0))))
'''
def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main(build,complete,out):
 graph,producers,_=load_native_producers(build,complete);out.mkdir(parents=True,exist_ok=False);routes=[]
 for compiler in producers:
  work=out/compiler.stem;work.mkdir();source=work/'entry.kotoba';lock=work/'source.ksl';calls=[]
  def compile_(name,text,code=None):
   source.write_text(text);lock.write_text(f'KSL1\nentry {source}\nroot {work}\nfile {pin(source)["sha256"]} {source}\n');dest=work/(name+'.elf')
   env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(work))
   args=[compiler,'compile',source,'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',dest,'--fuel','1000000','--source-path',work,'--source-lock',lock,'--source-lock-sha256',pin(lock)['sha256']]
   r=subprocess.run(list(map(str,args)),env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode()));(work/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
   if code:
    assert r.returncode==1 and code.encode() in r.stderr and not dest.exists(),calls[-1];return None
   assert not r.returncode and not r.stderr,calls[-1]
   image=dest.read_bytes();rw=struct.unpack_from('<IIQQQQQQ',image,120);assert rw[5]==0x240000
   assert struct.unpack_from('<Q',image,rw[2]+464)[0]==0x334c5652
   return pin(dest)
  good=compile_('owned-gop-browser-font',SOURCE)
  controls={
   'literal-framebuffer':SOURCE.replace('(kernel-framebuffer-page 0)','3221225472'),
   'scalar-width-is-not-region':SOURCE.replace('(kernel-framebuffer-page 0)','(kernel-framebuffer-width)'),
   'computed-font-pointer':SOURCE.replace('(kernel-native-font)','(+ (kernel-native-font) 0)'),
   'font-extent-forgery':SOURCE.replace('kernel-subregion f 524288','kernel-subregion f 1048576'),
   'surface-extent-forgery':SOURCE.replace('kernel-subregion s 8192','kernel-subregion s 16384'),
   'context-extent-forgery':SOURCE.replace('kernel-subregion c 8192','kernel-subregion c 16384')}
  for name,text in controls.items():compile_(name,text,'E7106')
  routes.append(dict(compiler=pin(compiler),image=good,refusals=len(controls)))
 assert routes[0]['image']==routes[1]['image']
 result=dict(status='PASS_NATIVE_DESKTOP_REGION_ADMISSION',source=graph,routes=routes,firmwareExecution=False,guestBoot=False,desktopInput=False)
 (out/'native-desktop-regions.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve() if a.build else None,a.complete.resolve() if a.complete else None,a.output.resolve())
