#!/usr/bin/env python3
"""Stage public metadata forgery and an intentionally corrupted PCI handoff.

Only fixed test inputs and one declared EFI corruption are staged in Python.
The admitted native compiler emits every kernel and loader instruction.
The corrupted EFI is a refusal control and cannot qualify a device grant.
"""
import argparse,hashlib,json,subprocess,sys,runpy
from pathlib import Path
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers
ACCESS=runpy.run_path(str(Path(__file__).with_name('check-aiueos-pci-private-native.py')))['ACCESS']

def pin(p):
 raw=p.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main(build, out, complete=None):
 graph,producers,_=load_native_producers(build=build, complete=complete);out.mkdir(parents=True,exist_ok=False);routes=[]
 fields=[0x31494350534f4941,1,1,64,1048576,4096,0,0,1,0,0,286331444]
 prefix='(let [boot (kernel-subregion (kernel-boot-info) 16544 0 160)\n fake (kernel-owned-page 14)\n'
 for i,value in enumerate(fields):prefix+=f' f{i} (kernel-store-u64-4k fake 4096 {8*i} {value})\n'
 prefix+=' fp (kernel-store-u64 boot 160 144 fake)\n fn (kernel-store-u64 boot 160 152 96)\n selected'
 forged=ACCESS.replace('(let [selected',prefix)
 absent='(ns entry (:export [main]))\n(defn main [] :i64 (if (= (kernel-pci-mmio 0 1 0 0 4096) 0) 42 0))\n'
 for c in producers:
  scope=out/c.stem;scope.mkdir();src=scope/'entry.kotoba';lock=scope/'source.ksl';calls=[];artifacts={}
  env=dict(PATH='/nonexistent',KEXE_CAP_RESOURCES_35=str(scope),KEXE_STACK_BYTES='8388608')
  for name,text in [('public-forgery',forged),('forged-ram',forged.replace('0 1 0 base 4096','0 1 0 1048576 4096')),('absent',absent),('protected-overlap',ACCESS)]:
   src.write_text(text);lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n')
   image=scope/(name+'.elf');efi=scope/(name+'.efi')
   args=[str(c),'compile',str(src),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
   r=subprocess.run(args,env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),sourceText=text));assert r.returncode==0 and not r.stderr,calls[-1]
   r=subprocess.run([str(c),'package-aiueos-boot',str(image),'--output',str(efi),'--pci-resources','v1'],env=env,capture_output=True,timeout=180);assert r.returncode==0 and not r.stderr,r.stderr
   artifacts[name]=dict(kernel=pin(image),originalEfi=pin(efi))
   if name=='protected-overlap':
    raw=efi.read_bytes();before=bytes.fromhex('488d7c0720488b860e000000')
    assert raw.count(before)==1,'unique collector record writer required'
    at=raw.index(before)+5;changed=raw[:at]+bytes.fromhex('b8000010009090')+raw[at+7:]
    assert changed.count(image.read_bytes())==1 and len(changed)==len(raw)
    efi.write_bytes(changed);artifacts[name]['mutatedEfi']=pin(efi)
    artifacts[name]['mutation']=dict(offset=at,before=raw[at:at+7].hex(),after=changed[at:at+7].hex(),meaning='replace collected BAR base with RAM1048576; negative handoff control only')
  (scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');routes.append(dict(compiler=pin(c),artifacts=artifacts))
 assert routes[0]['artifacts']==routes[1]['artifacts']
 report=dict(status='PASS_NATIVE_PCI_FORGERY_PACKAGING',observer=pin(Path(__file__)),source=graph,routes=routes,guestExecution=False,fullKernel=False,nativeCDCI=False)
 (out/'native-pci-forgery.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve() if a.build else None, a.output.resolve(), a.complete.resolve() if a.complete else None)
