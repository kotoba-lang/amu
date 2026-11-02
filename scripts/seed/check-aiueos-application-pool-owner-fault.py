#!/usr/bin/env python3
"""Build a whole-compiler owner-check fault and observe its native bypass.

The primary source is unchanged. All61 compiler modules remain in the
native mutant; both valid/wrong-owner boots complete the full eight-MiB
checks. This is one targeted fault, not the complete negative corpus.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,json,struct,hashlib
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
for name in ['mac-build','qemu','firmware','output']:
 p.add_argument('--'+name,type=Path,required=True)
for name in ['qemu-sha256','firmware-sha256']:
 p.add_argument('--'+name,required=True)
args=p.parse_args()

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('mac',R/'scripts/seed/check-aiueos-user-macos-native.py');g=load('pool',R/'scripts/seed/check-aiueos-application-pool-macos-native.py');D=args.output.resolve();D.mkdir(parents=True,exist_ok=False,mode=0o700)
build=json.loads((args.mac_build/'mac-aiueos-user-target.json').read_text())
assert build['status']=='PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
for row in build['sources']:
 assert m.pin(R/row['name'])=={k:row[k] for k in ['bytes','sha256']}
assert m.pin(args.mac_build/'full-unity.kotoba')==build['source']
s=(args.mac_build/'full-unity.kotoba').read_bytes();old=b'(iv-hex "48837e2001") (xg-rel 0x850f 2 2 fail)';assert s.count(old)==1;mutated=s.replace(old,b'(iv-hex "48837e2001")');(D/'full-unity.kotoba').write_bytes(mutated)
descriptor=json.loads((R/'seed/bootstrap/aarch64-macos/root.json').read_text())
F=R/descriptor['compiler']['path'];P=R/descriptor['packager']['path']
for role,path in [('compiler',F),('packager',P)]:
 assert m.verify_macho(path)=={k:descriptor[role][k] for k in ['bytes','sha256']}
for name in ['qemu','firmware']:
 path=getattr(args,name).resolve(strict=True);setattr(args,name,path)
 assert m.pin(path)['sha256']==getattr(args,name+'_sha256')
rows=[]
for n in [1,2]:F,row=m.generation(n,F,P,D);rows.append(row)
assert rows[0]['container']==rows[1]['container'] and rows[0]['raw']==rows[1]['raw'] and rows[0]['unsigned']==rows[1]['unsigned']
S=D/'fixture';S.mkdir();source=(R/'seed/tests/aiueos-application-pool.kotoba').read_bytes();(S/'probe.kotoba').write_bytes(source);lock=f'KSL1\nentry /fixture/probe.kotoba\nroot /fixture\nfile {hashlib.sha256(source).hexdigest()} /fixture/probe.kotoba\n'.encode();(D/'probe.ksl').write_bytes(lock)
m.native_run(F,D,'compile','/fixture/probe.kotoba','--target','x86_64-aiueos-kernel-v4','--artifact','image','--output','kernel.elf','--fuel','9007199254740991','--source-path','/fixture','--source-lock','probe.ksl','--source-lock-sha256',hashlib.sha256(lock).hexdigest())
m.native_run(F,D,'package-aiueos-boot','kernel.elf','--output','boot.efi','--pci-resources','v1')
k=(D/'kernel.elf').read_bytes();ph=struct.unpack_from('<Q',k,32)[0];rx=struct.unpack_from('<IIQQQQQQ',k,ph);efi=(D/'boot.efi').read_bytes();changed=bytearray(efi);struct.pack_into('<Q',changed,g.data_offset(efi)+24784+32,2)
a=SimpleNamespace(qemu=args.qemu,firmware=args.firmware)
valid=g.boot(a,D,'valid-owner',efi,'pattern',rx[3]+rx[5]);wrong=g.boot(a,D,'incorrect-owner',bytes(changed),'pattern',rx[3]+rx[5])
report=dict(state='DETECTED_NATIVE_OWNER_CHECK_REMOVAL',scope='one targeted fault with valid and wrong owner; both complete native memory checks',baselineSource=m.pin(args.mac_build/'full-unity.kotoba'),mutantSource=m.pin(D/'full-unity.kotoba'),generations=rows,validOwner=valid,wrongOwner=wrong,compiler=m.pin(F),kernel=m.pin(D/'kernel.elf'),efi=m.pin(D/'boot.efi'),observer=m.pin(Path(__file__)),allSourcesRetained=True,adopted=False,production=False)
(D/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['state'],flush=True)
