#!/usr/bin/env python3
"""Native PCI collector packaging observations, not an OS ownership gate.

Python stages, starts native producers and inspects bytes. The collector
itself is emitted by the complete Kotoba compiler. QEMU must separately
compare its actual catalog to independent PCI device information.
"""
import argparse, hashlib, json, os, struct, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers

def pin(p):
    raw=p.read_bytes(); return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main(build,out):
    graph,producers,_=load_native_producers(build=build)
    out.mkdir(parents=True,exist_ok=False); routes=[]
    for compiler in producers:
        scope=out/compiler.stem;scope.mkdir()
        env=dict(PATH='/nonexistent',KEXE_CAP_RESOURCES_35=str(scope),KEXE_STACK_BYTES='8388608')
        source=scope/'entry.kotoba'; source.write_text('(ns entry (:export [main]))\n(defn main [] :i64 42)\n')
        kernel=scope/'entry.elf'; calls=[]
        def run(name,args,expected=0):
            r=subprocess.run([str(compiler),*map(str,args)],env=env,capture_output=True,timeout=240)
            calls.append(dict(name=name,exit=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode()))
            (scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
            assert r.returncode==expected,(name,calls[-1])
            if expected==0: assert not r.stderr,calls[-1]
            return r
        run('compile',['compile',source,'--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',kernel,'--fuel',1024])
        artifacts={'kernel':pin(kernel)}
        for name,payload in [('plain',None),('payload',b'PCI payload\x00\xff')]:
            dst=scope/(name+'.efi');args=['package-aiueos-boot',kernel,'--output',dst]
            if payload is not None:
                p=scope/'payload.bin';p.write_bytes(payload);args+=['--payload',p]
            run(name,args+['--pci-resources','v1'])
            raw=dst.read_bytes(); assert raw.count(kernel.read_bytes())==1
            opt=struct.unpack_from('<I',raw,60)[0]+24
            size,rva,rawsize,offset=struct.unpack_from('<IIII',raw,opt+240+40+8)
            data=raw[offset:offset+size]
            assert struct.unpack_from('<QQ',data,16)==(0x544f4f4245554941,6)
            assert not any(data[160:176])
            assert struct.unpack_from('<QQQQ',data,16560)==(0x31494350534f4941,1,0,64)
            assert not any(data[16592:16560+8224])
            ko=(16560+8224+len(payload or b'')+15)&-16
            assert data[16560+8224:16560+8224+len(payload or b'')]==(payload or b'')
            assert data[ko:ko+kernel.stat().st_size]==kernel.read_bytes()
            guid=(ko+kernel.stat().st_size+7)&-8
            assert data[guid+24:guid+40]==bytes.fromhex('00b2f54cb868a54c9eecb23e3f50029a')
            assert size==guid+144
            artifacts[name]=pin(dst)
        for name,flags in [('unknown-version',['--pci-resources','v2']),('duplicate',['--pci-resources','v1','--pci-resources','v1']),('unsupported',['--pci-resources','v1','--resident','yes'])]:
            dst=scope/(name+'.efi')
            run(name,['package-aiueos-boot',kernel,'--output',dst,*flags],2);assert not dst.exists()
        routes.append(dict(compiler=pin(compiler),artifacts=artifacts,cliRefusals=3))
    assert routes[0]['artifacts']==routes[1]['artifacts']
    report=dict(status='PASS_NATIVE_PCI_COLLECTOR_PACKAGING',observer=pin(Path(__file__)),source=graph,routes=routes,
                osOwnershipQualified=False,guestExecution=False,fullKernel=False,nativeCDCI=False)
    (out/'native-pci-boot.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.build.resolve(),a.output.resolve())
