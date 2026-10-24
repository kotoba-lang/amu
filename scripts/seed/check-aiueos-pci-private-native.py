#!/usr/bin/env python3
"""Stage native private PCI policy fixtures. QEMU execution is separate."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from aiueos_native_proof import load_native_producers

ACCESS='''(ns entry (:export [main]))
(defn main [] :i64
 (let [selected (kernel-out-u32 3320 2147485712)
       raw (kernel-in-u32 3324)
       base (bit-and raw 4294967280)
       mmio (kernel-pci-mmio 0 1 0 base 4096)
       old (kernel-load-u32-4k mmio 4096 0)
       wrote (kernel-store-u32-4k mmio 4096 0 305419896)
       actual (kernel-load-u32-4k mmio 4096 0)
       restored (kernel-store-u32-4k mmio 4096 0 old)
       again (kernel-load-u32-4k mmio 4096 0)]
   (if (and (= selected 2147485712) (= wrote 305419896) (= actual 305419896)
            (= restored old) (= again old)) 42 0)))
'''

def pin(p):
    raw=p.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def stage(compiler,scope):
    scope.mkdir();source=scope/'entry.kotoba';lock=scope/'source.ksl';calls=[];artifacts={}
    env=dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(scope))
    def compile_(name,text,bad=False):
        source.write_text(text);lock.write_text(f'KSL1\nentry {source}\nroot {scope}\nfile {pin(source)["sha256"]} {source}\n')
        dst=scope/(name+'.elf');args=['compile',str(source),'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(dst),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
        r=subprocess.run([str(compiler),*args],env=env,capture_output=True,timeout=240);calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),sourceText=text))
        (scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
        if bad:
            assert r.returncode==1 and b'E7106' in r.stderr and not dst.exists(),calls[-1];return
        assert r.returncode==0 and not r.stderr,calls[-1]
        ef=scope/(name+'.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(dst),'--output',str(ef),'--pci-resources','v1'],env=env,capture_output=True,timeout=180);assert q.returncode==0 and not q.stderr,q.stderr
        wrong=scope/(name+'-missing-v6.efi');q=subprocess.run([str(compiler),'package-aiueos-boot',str(dst),'--output',str(wrong)],env=env,capture_output=True,timeout=180);assert q.returncode==1 and b'E7111' in q.stderr and not wrong.exists(),q.stderr
        artifacts[name]=dict(kernel=pin(dst),efi=pin(ef))
    compile_('access',ACCESS)
    compile_('wrong-identity',ACCESS.replace('mmio 0 1 0','mmio 0 2 0'))
    compile_('outside-bar',ACCESS.replace('0 1 0 base 4096','0 1 0 (+ base 16777216) 4096'))
    compile_('oversized','(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-pci-mmio 0 1 0 2147483648 65537) 0) 42 0))\n')
    compile_('zero-bytes','(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-pci-mmio 0 1 0 2147483648 0) 0) 42 0))\n')
    compile_('ram',ACCESS.replace('0 1 0 base 4096','0 1 0 1048576 4096'))
    compile_('literal-root','(ns entry (:export [main]))\n(defn main [] :i64 (kernel-load-u32 2147483648 512 0))\n',True)
    return dict(compiler=pin(compiler),artifacts=artifacts,regionRefusals=1,missingV6Refusals=len(artifacts))

def main(build,out):
    graph,producers,_=load_native_producers(build=build);out.mkdir(parents=True,exist_ok=False)
    routes=[stage(c,out/c.stem) for c in producers];assert routes[0]['artifacts']==routes[1]['artifacts']
    report=dict(status='PASS_NATIVE_PRIVATE_PCI_PACKAGING',observer=pin(Path(__file__)),source=graph,routes=routes,guestExecution=False,fullKernel=False,physicalHardware=False,nativeCDCI=False)
    (out/'native-private-pci.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve(),a.output.resolve())
