#!/usr/bin/env python3
"""Observe explicit v5/v8 receive8MiB + transmit1MiB native allocations.

Python stages bytes and observes native processes/memory. It never creates
guest allocations, compiles Kotoba, runs app effects or grants consent.
"""
import argparse, importlib.util, json, re, struct, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RX=8388608
TX=1048576
TOTAL=RX+TX
MARKER=0x324d5041
MAGIC=0x31545345544e5354
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('tx_mac',ROOT/'scripts/seed/check-aiueos-user-macos-native.py')
g=load('tx_qmp',ROOT/'scripts/seed/check-aiueos-application-pool-macos-native.py')
def expected(size,tag):
    return bytes(size) if not tag else b''.join(struct.pack('<I',i^tag) for i in range(0,size,4))
def boot(a,out,name,efi,mode,rx_end,post_seal=False,allow_errors=False):
    d=out/name;(d/'esp/EFI/BOOT').mkdir(parents=True);(d/'esp/EFI/BOOT/BOOTX64.EFI').write_bytes(efi)
    cmd=[str(a.qemu),'-machine','q35,accel=tcg,i8042=off','-cpu','max,phys-bits=37','-m','128M','-smp','1','-drive',f'if=pflash,format=raw,readonly=on,file={a.firmware}','-drive','file=fat:rw:esp,format=raw','-boot','order=c','-nic','none','-display','none','-no-reboot','-no-shutdown','-serial','file:serial.log','-debugcon','file:debug.log','-qmp','stdio']
    (d/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');q=None
    with (d/'qemu.stderr').open('wb') as err:
        proc=subprocess.Popen(cmd,cwd=d,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,bufsize=0)
        try:
            q=g.QMP(proc);until=time.monotonic()+120
            while time.monotonic()<until:
                if proc.poll() is not None:raise RuntimeError(name+': QEMU terminated')
                ctx=q.dump(0x400000,65536,d,'context-last.bin');scratch=struct.unpack_from('<Q',ctx,272)[0]
                row=q.dump(scratch,4096,d,'receipt-last.bin') if scratch else bytes(4096)
                status=q.call('query-status')
                if status['status'] in ('shutdown','guest-panicked'):
                    assert mode=='refuse',name+': positive faulted'
                    registers=q.hmp('info registers');(d/'registers.txt').write_text(registers)
                    rip=int(re.search(r'\bRIP=([0-9a-f]+)',registers,re.I)[1],16)
                    assert 0x101000<=rip<rx_end and struct.unpack_from('<Q',row)[0]!=MAGIC
                    assert struct.unpack_from('<Q',ctx,33552)[0]==(MARKER if post_seal else 0)
                    return dict(name=name,state='REFUSED_AFTER_SEAL' if post_seal else 'REFUSED_BEFORE_MAIN',rip=rip,efi=dict(bytes=len(efi),sha256=g.digest(efi)))
                if struct.unpack_from('<Q',row)[0]==MAGIC:
                    assert mode!='refuse',name+': refused input reached receipt'
                    q.call('stop');row=q.dump(scratch,4096,d,'receipt.bin');words=struct.unpack_from('<13Q',row)
                    base,size,ready=struct.unpack_from('<3Q',ctx,33536)
                    assert size==TOTAL and ready==MARKER and base==words[8] and words[9]==RX and words[11]==TX
                    assert words[10]==base+RX or allow_errors
                    assert words[12]==(1 if mode=='wipe' else 0)
                    assert words[1:8]==(0,)*7 or allow_errors
                    assert base>=0x1000000 and base%4096==0 and base+TOTAL<=2**32
                    assert base+TOTAL<=scratch or scratch+15*4096<=base
                    raw=q.dump(base,TOTAL,d,'both-pools.bin');wanted=expected(RX,0xa55a17c3)+expected(TX,0 if mode=='wipe' else 0x3cc3e19f)
                    assert raw==wanted or allow_errors
                    map_size,stride=struct.unpack_from('<2Q',ctx,288);assert 0<map_size<=16384 and 40<=stride<=map_size and map_size%stride==0
                    descriptors=[]
                    for at in range(512,512+map_size,stride):
                        kind=struct.unpack_from('<I',ctx,at)[0];start,_,pages,attrs=struct.unpack_from('<4Q',ctx,at+8)
                        if kind==2 and not(attrs>>63) and start<=base and base+TOTAL<=start+pages*4096:descriptors.append(dict(type=kind,start=start,pages=pages,attributes=attrs))
                    assert len(descriptors)==1
                    if allow_errors:assert words[1:8]!=(0,)*7 and raw!=wanted
                    return dict(name=name,state='DETECTED_COMPLETED_MEMORY_FAULT' if allow_errors else 'PASS_BOTH_FULL_POOLS',nativeReceipt=list(words),wholePoolsMatch=raw==wanted,pools=m.pin(d/'both-pools.bin'),allocatedDescriptor=descriptors[0],efi=dict(bytes=len(efi),sha256=g.digest(efi)))
                time.sleep(.1)
            raise TimeoutError(name+': no terminal observation')
        finally:
            if proc.poll() is None:
                try:q.call('quit')
                except Exception:proc.terminate()
                proc.wait(timeout=10)

def main(a):
    for key in ['mac_build','reference_compiler','qemu','firmware']:setattr(a,key,getattr(a,key).resolve(strict=True))
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    build=json.loads((a.mac_build/'mac-aiueos-user-target.json').read_text());assert build['status']=='PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
    assert build['generations'][-1]['container']==build['generations'][-2]['container']
    for row in build['sources']:assert m.pin(ROOT/row['name'])=={k:row[k] for k in ['bytes','sha256']}
    compiler=a.mac_build/f"F{build['generations'][-1]['number']}-signed.macho";assert m.verify_macho(compiler)==build['generations'][-1]['signed']
    assert m.verify_macho(a.reference_compiler)['sha256']==a.reference_sha256
    for key in ['qemu','firmware']:assert m.pin(getattr(a,key))['sha256']==getattr(a,key+'_sha256')
    report=dict(schema='amu.application-transmit-pool-native.v1',state='TESTING',compiler=m.pin(compiler),compilerBuild=m.pin(a.mac_build/'mac-aiueos-user-target.json'),referenceCompiler=m.pin(a.reference_compiler),sources=build['sources'],observer=m.pin(Path(__file__)),fixture=m.pin(ROOT/'seed/tests/aiueos-application-transmit-pool.kotoba'),qemu=m.pin(a.qemu),firmware=m.pin(a.firmware),calls=[],boots=[],legacyArtifactEquality=[],production=False,physicalHardware=False,appConnection=False,hostileCPL3Execution=False)
    def save():(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    def call(label,d,argv,producer=compiler,want=0):
        try:r=m.native_run(producer,d,*argv,expected=want)
        except ValueError:
            if want:raise
            r=m.native_run(producer,d,*argv,expected=1)
            (d/(label+'.stdout')).write_bytes(r.stdout);(d/(label+'.stderr')).write_bytes(r.stderr)
            raise RuntimeError('native command refused: '+label)
        (d/(label+'.stdout')).write_bytes(r.stdout);(d/(label+'.stderr')).write_bytes(r.stderr)
        report['calls'].append(dict(label=label,argv=argv,exit=r.returncode,producer=m.pin(producer)));save();return r
    def compile_source(label,raw,target='v5',want=0):
        d=out/label;(d/'fixture').mkdir(parents=True);(d/'fixture/probe.kotoba').write_bytes(raw)
        lock=f'KSL1\nentry /fixture/probe.kotoba\nroot /fixture\nfile {g.digest(raw)} /fixture/probe.kotoba\n'.encode();(d/'probe.ksl').write_bytes(lock)
        flags=['compile','/fixture/probe.kotoba','--target','x86_64-aiueos-kernel-'+target,'--artifact','image','--fuel','9007199254740991','--source-path','/fixture','--source-lock','probe.ksl','--source-lock-sha256',g.digest(lock)]
        for name in (['kernel.elf','kernel-repeat.elf'] if want==0 else ['refused.elf']):
            r=call(name,d,flags+['--output',name],want=want)
            if want:assert b'E' in r.stderr and not(d/name).exists()
        if want:return d,flags
        assert m.pin(d/'kernel.elf')==m.pin(d/'kernel-repeat.elf')
        for name in ['boot.efi','boot-repeat.efi']:call(name,d,['package-aiueos-boot','kernel.elf','--output',name,'--pci-resources','v1'])
        assert m.pin(d/'boot.efi')==m.pin(d/'boot-repeat.efi');return d,flags
    save()
    try:
        source=(ROOT/'seed/tests/aiueos-application-transmit-pool.kotoba').read_bytes()
        d,flags=compile_source('pattern',source);kernel=(d/'kernel.elf').read_bytes();ph=struct.unpack_from('<Q',kernel,32)[0]
        rx,rw=[struct.unpack_from('<IIQQQQQQ',kernel,ph+i*56) for i in range(2)];assert struct.unpack_from('<H',kernel,56)[0]==2 and rx[5]<=2093056 and rw[5]==131072
        assert struct.unpack_from('<Q',kernel,rw[2]+496)[0]==MARKER
        efi=(d/'boot.efi').read_bytes();data=g.data_offset(efi);assert struct.unpack_from('<Q',efi,data+24)[0]==8
        assert struct.unpack_from('<5Q',efi,data+24784)==(0x314c4f4f5050414b,2,2**32-1,TOTAL,1)
        report.update(kernel=m.pin(d/'kernel.elf'),efi=m.pin(d/'boot.efi'),layout=dict(rx=rx,rw=rw))
        report['boots'].append(boot(a,out,'boot-pattern',efi,'pattern',rx[3]+rx[5]));save()
        if a.development_probe:report['state']='PASS_DEVELOPMENT_TRANSMIT_PROBE';save();return
        wipe,_=compile_source('wipe',source.replace(b'(def WIPE false)',b'(def WIPE true)'))
        report['boots'].append(boot(a,out,'boot-wipe',(wipe/'boot.efi').read_bytes(),'wipe',rx[3]+rx[5]));save()
        for name,offset,value in [('grant-magic',0,0),('grant-version',8,1),('grant-size',24,RX),('grant-owner',32,2),('grant-reserved',56,1),('loader-size',48,0)]:
            changed=bytearray(efi);struct.pack_into('<Q',changed,data+24784+offset,value)
            report['boots'].append(boot(a,out,'refuse-'+name,bytes(changed),'refuse',rx[3]+rx[5]));save()
        changed=bytearray(efi);struct.pack_into('<Q',changed,data+24,7)
        report['boots'].append(boot(a,out,'refuse-old-boot',bytes(changed),'refuse',rx[3]+rx[5]));save()
        r=call('no-pci',d,['package-aiueos-boot','kernel.elf','--output','no-pci.efi'],want=1);assert b'E7111' in r.stderr and not(d/'no-pci.efi').exists()
        scalar=b'(ns tx-legacy (:export [main]))\n(defn main [] :i64 42)\n'
        for target in ['v1','v2','v3','v4']:
            old,f=compile_source('legacy-'+target,scalar,target)
            call('reference-kernel',old,f+['--output','reference.elf'],producer=a.reference_compiler)
            call('reference-boot',old,['package-aiueos-boot','reference.elf','--output','reference.efi','--pci-resources','v1'],producer=a.reference_compiler)
            assert m.pin(old/'kernel.elf')==m.pin(old/'reference.elf') and m.pin(old/'boot.efi')==m.pin(old/'reference.efi')
            report['legacyArtifactEquality'].append(dict(target=target,kernel=m.pin(old/'kernel.elf'),efi=m.pin(old/'boot.efi')))
            compile_source('unavailable-'+target,source,target,want=1)
        r=call('old-compiler-v5',d,flags+['--output','old-v5.elf'],producer=a.reference_compiler,want=2);assert b'E1' in r.stderr and not(d/'old-v5.elf').exists()
        forged=b'(ns tx-forged (:export [main]))\n(defn main [] :i64 (kernel-load-u8 16777216 512 0))\n'
        bad,_=compile_source('forged',forged,want=1);assert b'E7106' in (bad/'refused.elf.stderr').read_bytes()
        # Dynamic offsets pass the region-origin checker, then must trap at
        # the real subregion boundary. A receipt proves an unexpected bypass.
        for label,offset in [('negative',-1),('past-end',TX),('cross-end',TX-4)]:
            raw=('(ns tx-boundary (:export [main]))\n(defn main [] :i64 (let [off (kernel-cli) tx (kernel-application-transmit-pool) receipt (kernel-owned-page 0) index-store (kernel-store-u64-4k receipt 4096 128 '+str(offset)+') index (kernel-load-u64-4k receipt 4096 128) access (kernel-store-u64 (kernel-subregion tx 1048576 index 8) 8 0 123) done (kernel-store-u64-4k receipt 4096 0 '+str(MAGIC)+')] (loop [n 0] (let [p (kernel-pause)] (recur (inc n))))))\n').encode()
            boundary,_=compile_source('boundary-'+label,raw)
            raw_kernel=(boundary/'kernel.elf').read_bytes();phb=struct.unpack_from('<Q',raw_kernel,32)[0];rxb=struct.unpack_from('<IIQQQQQQ',raw_kernel,phb)
            report['boots'].append(boot(a,out,'refuse-boundary-'+label,(boundary/'boot.efi').read_bytes(),'refuse',rxb[3]+rxb[5],post_seal=True));save()
        user=out/'user-unavailable';user.mkdir();(user/'probe.kotoba').write_text('(ns tx-user (:export [main]))\n(defn main [a :i64 b :i64] :i64 (kernel-application-transmit-pool))\n')
        r=call('user-root-refused',user,['compile','probe.kotoba','--target','x86_64-aiueos-user-v4','--output','user.elf'],want=1)
        assert b'E2101' in r.stderr and not(user/'user.elf').exists()
        report['state']='PASS_NATIVE_APPLICATION_TRANSMIT_POOLS';save();print(report['state'],flush=True)
    except BaseException as e:report.update(state='FAILED',failure=str(e));save();raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['mac-build','reference-compiler','qemu','firmware','output']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['reference-sha256','qemu-sha256','firmware-sha256']:p.add_argument('--'+name,required=True)
    p.add_argument('--development-probe',action='store_true');main(p.parse_args())
