#!/usr/bin/env python3
"""Build complete61-module native compiler faults; observe full9MiB execution.

Alias faults must finish with native and independent whole-memory errors.
Owner-check removal must let an actually wrong-owner grant finish, unlike the
normal compiler's before-main refusal. No trap/build failure counts as detection.
"""
import argparse,importlib.util,json,hashlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main(a):
    m=load('tx_fault_mac',ROOT/'scripts/seed/check-aiueos-user-macos-native.py')
    g=load('tx_fault_gate',ROOT/'scripts/seed/check-aiueos-application-transmit-pool-macos-native.py')
    d=a.output.resolve();d.mkdir(parents=True,exist_ok=False)
    for key in ['qemu','firmware']:assert m.pin(getattr(a,key))['sha256']==getattr(a,key+'_sha256')
    build=json.loads((a.mac_build/'mac-aiueos-user-target.json').read_text());assert build['status']=='PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
    assert len(build['sources'])==61
    for row in build['sources']:assert m.pin(ROOT/row['name'])=={k:row[k] for k in ['bytes','sha256']}
    raw=(a.mac_build/'full-unity.kotoba').read_bytes();assert m.pin(a.mac_build/'full-unity.kotoba')==build['source']
    before,after=(b'(cond-> transmit (iv-hex "480500008000"))',b'(cond-> transmit (iv-hex "4883c000"))') if a.kind=='alias' else (b'(iv-hex "48837e2001") (xg-rel 0x850f 2 2 fail)',b'(iv-hex "48837e2001")')
    assert raw.count(before)==1;(d/'full-unity.kotoba').write_bytes(raw.replace(before,after))
    f=a.mac_build/f"F{build['generations'][-1]['number']}-signed.macho";assert m.verify_macho(f)==build['generations'][-1]['signed']
    packager=ROOT/'seed/bootstrap/aarch64-macos/kotoba-packager-root.macho';rows=[]
    report=dict(schema='amu.native-application-transmit-pool-fault.v1',state='BUILDING',kind=a.kind,source=m.pin(d/'full-unity.kotoba'),baselineSource=build['source'],observer=m.pin(Path(__file__)),nativeBootObserver=m.pin(ROOT/'scripts/seed/check-aiueos-application-transmit-pool-macos-native.py'),allCompilerModules=61,adopted=False,production=False)
    def save():(d/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for number in [1,2]:f,row=m.generation(number,f,packager,d);rows.append(row)
        assert rows[0]['container']==rows[1]['container'] and rows[0]['raw']==rows[1]['raw'] and rows[0]['unsigned']==rows[1]['unsigned']
        report.update(generations=rows,compiler=m.pin(f),state='BOOTING');save()
        (d/'fixture').mkdir();source=(ROOT/'seed/tests/aiueos-application-transmit-pool.kotoba').read_bytes();(d/'fixture/probe.kotoba').write_bytes(source)
        lock=f'KSL1\nentry /fixture/probe.kotoba\nroot /fixture\nfile {hashlib.sha256(source).hexdigest()} /fixture/probe.kotoba\n'.encode();(d/'source.ksl').write_bytes(lock)
        flags=['compile','/fixture/probe.kotoba','--target','x86_64-aiueos-kernel-v5','--artifact','image','--fuel','9007199254740991','--source-path','/fixture','--source-lock','source.ksl','--source-lock-sha256',hashlib.sha256(lock).hexdigest()]
        for name in ['kernel.elf','kernel-repeat.elf']:m.native_run(f,d,*flags,'--output',name)
        assert m.pin(d/'kernel.elf')==m.pin(d/'kernel-repeat.elf')
        for name in ['boot.efi','boot-repeat.efi']:m.native_run(f,d,'package-aiueos-boot','kernel.elf','--output',name,'--pci-resources','v1')
        assert m.pin(d/'boot.efi')==m.pin(d/'boot-repeat.efi')
        raw_kernel=(d/'kernel.elf').read_bytes();ph=struct.unpack_from('<Q',raw_kernel,32)[0];rx=struct.unpack_from('<IIQQQQQQ',raw_kernel,ph);efi=(d/'boot.efi').read_bytes()
        boots=[g.boot(a,d,'normal-grant',efi,'pattern',rx[3]+rx[5],allow_errors=a.kind=='alias')]
        if a.kind=='owner':
            changed=bytearray(efi);struct.pack_into('<Q',changed,g.g.data_offset(efi)+24784+32,2)
            boots.append(g.boot(a,d,'wrong-owner',bytes(changed),'pattern',rx[3]+rx[5]))
        report.update(state='DETECTED_NORMALLY_COMPLETED_TRANSMIT_POOL_FAULT',boots=boots,kernel=m.pin(d/'kernel.elf'),efi=m.pin(d/'boot.efi'));save();print(report['state'],a.kind,flush=True)
    except BaseException as e:report.update(state='FAILED',failure=str(e));save();raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['mac-build','qemu','firmware','output']:p.add_argument('--'+key,type=Path,required=True)
    for key in ['qemu-sha256','firmware-sha256']:p.add_argument('--'+key,required=True)
    p.add_argument('--kind',choices=['alias','owner'],required=True);main(p.parse_args())
