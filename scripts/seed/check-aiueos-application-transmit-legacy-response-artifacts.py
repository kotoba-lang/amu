#!/usr/bin/env python3
"""Fresh old-v4 real-runtime artifact equality, not another old-profile boot."""
import argparse,importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main(a):
    sp=importlib.util.spec_from_file_location('tx_legacy_mac',ROOT/'scripts/seed/check-aiueos-user-macos-native.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
    d=a.output.resolve();d.mkdir(parents=True,exist_ok=False);s=d/'source';s.mkdir()
    p=a.fixture_run.resolve(strict=True)/'receipt.json';assert m.pin(p)['sha256']==a.fixture_receipt_sha256
    b=json.loads(p.read_text());assert b['schema']=='kekkai.native-application-response.v1' and b['state']=='PASS_FULL_NATIVE_APPLICATION_RECEIVE' and not b['fault']
    assert len(b['sourceGraph'])==45 and b['receiveResult']['observed']['nativeErrors']==0
    for virtual,digest in b['sourceGraph'].items():
        q=p.parent/'source'/virtual.lstrip('/');assert m.pin(q)['sha256']==digest
        target=s/virtual.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,target)
    for name,key in [('boot-font.bin','bootFont'),('boot-user-slot.bin','userSlot')]:assert m.pin(p.parent/'source'/name)==b[key];shutil.copyfile(p.parent/'source'/name,s/name)
    assert m.pin(p.parent/'source/kernel.elf')==b['kernel'] and m.pin(p.parent/'source/boot.efi')==b['efi']
    build=json.loads((a.mac_build/'mac-aiueos-user-target.json').read_text());assert build['status']=='PASS_MAC_NATIVE_USER_TARGET_SELFHOST' and build['generations'][-1]['container']==build['generations'][-2]['container']
    for row in build['sources']:assert m.pin(ROOT/row['name'])=={k:row[k] for k in ['bytes','sha256']}
    f=a.mac_build/f"F{build['generations'][-1]['number']}-signed.macho";assert m.verify_macho(f)==build['generations'][-1]['signed']
    flags=next(c['argv'][:-2] for c in b['calls'] if c['label']=='kernel.elf');assert flags[3]=='x86_64-aiueos-kernel-v4'
    roots=flags[8:flags.index('--source-lock')]
    for root in roots[1::2]:(s/root.lstrip('/')).mkdir(parents=True,exist_ok=True)
    assert m.pin(p.parent/'source/receive.ksl')==b['sourceLock'];shutil.copyfile(p.parent/'source/receive.ksl',s/'receive.ksl')
    for name in ['kernel.elf','kernel-repeat.elf']:m.native_run(f,s,*flags,'--output',name)
    assert m.pin(s/'kernel.elf')==m.pin(s/'kernel-repeat.elf')==b['kernel']
    for name in ['boot.efi','boot-repeat.efi']:m.native_run(f,s,'package-aiueos-boot','kernel.elf','--output',name,'--font','boot-font.bin','--user-slot','boot-user-slot.bin','--pci-resources','v1')
    assert m.pin(s/'boot.efi')==m.pin(s/'boot-repeat.efi')==b['efi']
    report=dict(schema='amu.transmit-legacy-response-artifact-parity.v1',state='PASS_REAL45_V4_ARTIFACT_PARITY',observer=m.pin(Path(__file__)),compiler=m.pin(f),compilerBuild=m.pin(a.mac_build/'mac-aiueos-user-target.json'),sourceGraph=b['sourceGraph'],baselineReceipt=m.pin(p),kernel=b['kernel'],efi=b['efi'],oldExecutedPackets=b['fixture']['cases'],freshKernelAndEFIBytesEqual=True,newBoot=False,scope='fresh native discovery-derived source lock/compile/package equality to complete previously executed files; no new protocol or physical qualification')
    (d/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['state'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['mac-build','fixture-run','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--fixture-receipt-sha256',required=True);main(p.parse_args())
