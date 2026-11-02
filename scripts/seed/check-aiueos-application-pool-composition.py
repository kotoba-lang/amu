#!/usr/bin/env python3
"""Native v4 pool composition with a pinned, already-qualified public Kekkai run.

Amu owns discovery/checking/linking/packaging. Python only stages bytes,
hashes the native discovery output and observes actual QEMU memory.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,hashlib,json,shutil,struct,subprocess,time
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
for name in ['mac-build','fixture-run','qemu','firmware','output']:
 p.add_argument('--'+name,type=Path,required=True)
for name in ['fixture-receipt-sha256','qemu-sha256','firmware-sha256']:
 p.add_argument('--'+name,required=True)
args=p.parse_args()
B=args.fixture_run.resolve(strict=True)

def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('mac',R/'scripts/seed/check-aiueos-user-macos-native.py');g=load('pool',R/'scripts/seed/check-aiueos-application-pool-macos-native.py')
D=args.output.resolve();D.mkdir(parents=True,exist_ok=False,mode=0o700);S=D/'source';S.mkdir()
assert m.pin(B/'receipt.json')['sha256']==args.fixture_receipt_sha256
b=json.loads((B/'receipt.json').read_text())
assert b['state']=='PASS_NATIVE_OS_APPLICATION_FRAME' and not b['mutation']
assert b['cases']['count']==113 and b['cases']['publicDataOnly'] and len(b['sourceGraph'])==17
build=json.loads((args.mac_build/'mac-aiueos-user-target.json').read_text())
assert build['status']=='PASS_MAC_NATIVE_USER_TARGET_SELFHOST'
assert build['generations'][-1]['container']==build['generations'][-2]['container']
for row in build['sources']:
 assert m.pin(R/row['name'])=={k:row[k] for k in ['bytes','sha256']}
F=args.mac_build/f"F{build['generations'][-1]['number']}-signed.macho"
assert m.verify_macho(F)==build['generations'][-1]['signed']
descriptor=json.loads((R/'seed/bootstrap/aarch64-macos/root.json').read_text())
reference_info=descriptor['kernelV3ReferenceCompiler']
O=R/reference_info['path'];assert m.verify_macho(O)=={k:reference_info[k] for k in ['bytes','sha256']}
for name in ['qemu','firmware']:
 path=getattr(args,name).resolve(strict=True);setattr(args,name,path)
 assert m.pin(path)['sha256']==getattr(args,name+'_sha256')
for virtual,digest in b['sourceGraph'].items():
 assert virtual.startswith('/') and '..' not in Path(virtual).parts
 source=B/'source'/virtual.lstrip('/');assert m.require_regular(source)['sha256']==digest
 target=S/virtual.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for filename,field in [('boot-font.bin','bootFont'),('boot-user-slot.bin','diagnosticUserSlot')]:
 assert m.require_regular(B/'source'/filename)==b[field];shutil.copyfile(B/'source'/filename,S/filename)
flags=next(x['argv'][:-2] for x in b['calls'] if x['argv'][0]=='compile' and x['argv'][-1]=='KERNEL.ELF')
assert flags[3]=='x86_64-aiueos-kernel-v3'
assert m.require_regular(B/'source/region.ksl')['sha256']==flags[-1]
shutil.copyfile(B/'source/region.ksl',S/'region.ksl')
for root in flags[9:flags.index('--source-lock'):2]:
 assert root.startswith('/') and '..' not in Path(root).parts
 (S/root.lstrip('/')).mkdir(parents=True,exist_ok=True)
calls=[]
for label,producer in [('old',O),('new',F)]:
 a=flags+['--output',label+'.elf'];p=m.native_run(producer,S,*a);calls.append(dict(name=label,argv=a,exit=p.returncode,artifact=m.pin(S/(label+'.elf'))))
 m.native_run(producer,S,'package-aiueos-boot',label+'.elf','--output',label+'.efi','--font','boot-font.bin','--user-slot','boot-user-slot.bin','--pci-resources','v1')
assert m.pin(S/'old.elf')==m.pin(S/'new.elf')==b['artifacts']['kernel'] and m.pin(S/'old.efi')==m.pin(S/'new.efi')==b['artifacts']['efi']
p=S/'os/aiueos/native/kekkai-application-frame-region-entry.kotoba';s=p.read_text();a='(defn main [] :i64\n  (fixture/run))';assert s.count(a)==1
s=s.replace(a,'''(defn main [] :i64
  (let [pool (kernel-application-pool)
        first (kernel-subregion pool 8388608 0 65536)
        last (kernel-subregion pool 8388608 8323072 65536)
        w (kernel-store-u32-64k first 65536 0 0x12345678)
        z (kernel-store-u32-64k last 65536 65532 0x87654321)]
    (fixture/run)))''');p.write_text(s)
roots=flags[8:flags.index('--source-lock')];assert roots[0]=='--source-path'
r=m.native_run(F,S,'modules',flags[1],*roots)
graph={}
for line in r.stdout.decode().splitlines():
 ns,virtual=line.split(' ',1);assert virtual.startswith('/') and virtual not in graph
 graph[virtual]=hashlib.sha256((S/virtual.lstrip('/')).read_bytes()).hexdigest()
assert set(graph)==set(b['sourceGraph'])
lock=('KSL1\nentry '+flags[1]+'\n'+''.join('root '+v+'\n' for v in roots[1::2])+''.join('file '+digest+' '+v+'\n' for v,digest in sorted(graph.items()))).encode()
(S/'pool.ksl').write_bytes(lock)
v4=flags.copy();v4[3]='x86_64-aiueos-kernel-v4';v4[-3]='pool.ksl';v4[-1]=hashlib.sha256(lock).hexdigest()
for name in ['v4.elf','v4-repeat.elf']:m.native_run(F,S,*v4,'--output',name)
assert m.pin(S/'v4.elf')==m.pin(S/'v4-repeat.elf')
for name in ['v4.efi','v4-repeat.efi']:m.native_run(F,S,'package-aiueos-boot','v4.elf','--output',name,'--font','boot-font.bin','--user-slot','boot-user-slot.bin','--pci-resources','v1')
assert m.pin(S/'v4.efi')==m.pin(S/'v4-repeat.efi')
kernel=(S/'v4.elf').read_bytes();ph=struct.unpack_from('<Q',kernel,32)[0]
assert struct.unpack_from('<H',kernel,56)[0]==2
rx,rw=[struct.unpack_from('<IIQQQQQQ',kernel,ph+i*56) for i in range(2)]
assert rx[:5]==(1,5,4096,0x101000,0x101000) and rx[5]==rx[6]<=2097152-4096
assert rw[:5]==(1,6,3145728,0x400000,0x400000) and rw[5]==rw[6]==0x240000
efi=(S/'v4.efi').read_bytes();data=g.data_offset(efi)
assert efi[data+24848:data+24848+524288]==(S/'boot-font.bin').read_bytes()
assert efi[data+24848+524288:data+24848+1048576]==(S/'boot-user-slot.bin').read_bytes()
assert len(efi)<=7247872
T=D/'qemu';(T/'esp/EFI/BOOT').mkdir(parents=True);shutil.copyfile(S/'v4.efi',T/'esp/EFI/BOOT/BOOTX64.EFI')
cmd=[str(args.qemu),'-machine','q35,accel=tcg,i8042=off','-cpu','max,phys-bits=37','-m','128M','-smp','1','-drive',f'if=pflash,format=raw,readonly=on,file={args.firmware}','-drive','file=fat:rw:esp,format=raw','-boot','order=c','-nic','none','-display','none','-no-reboot','-no-shutdown','-serial','file:serial.log','-debugcon','file:debug.log','-qmp','stdio']
report=dict(state='TESTING',layout=dict(rx=rx,rw=rw),payloadBytesPreserved=True,observer=m.pin(Path(__file__)),compilerBuild=m.pin(args.mac_build/'mac-aiueos-user-target.json'),qemu=m.pin(args.qemu),firmware=m.pin(args.firmware),sourceGraph=graph,originalSourceGraph=b['sourceGraph'],baselineReceipt=m.pin(B/'receipt.json'),compiler=m.pin(F),referenceCompiler=m.pin(O),legacyRealGraphEquality=True,calls=calls,sourceLock=m.pin(S/'pool.ksl'),kernel=m.pin(S/'v4.elf'),efi=m.pin(S/'v4.efi'),command=cmd)
def save():(D/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
save()
with (T/'qemu.stderr').open('wb') as err:
 q=subprocess.Popen(cmd,cwd=T,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,bufsize=0);c=None
 try:
  c=g.QMP(q);until=time.monotonic()+360
  while time.monotonic()<until:
   assert q.poll() is None
   ctx=c.dump(0x63a000,8192,T,'context.bin');words=struct.unpack_from('<6I',ctx,74*4)
   if words[-1]==2:break
   status=c.call('query-status');assert status['running'],status
   time.sleep(1)
  else:raise TimeoutError('real application fixture did not finish')
  c.call('stop');ctx=c.dump(0x63a000,8192,T,'context.bin');words=struct.unpack_from('<6I',ctx,74*4);assert words==(113,0,1,1,113,2),words
  assert struct.unpack_from('<3I',ctx,91*4)==(1,12,0)
  owner,caller=struct.unpack_from('<2Q',ctx,400);assert owner+262144<=caller or caller+262144<=owner
  assert c.dump(owner,8192,T,'work.bin')==bytes(8192)
  pairs=c.dump(caller+196608,113*16,T,'returns.bin');assert all(a==b for a,b in struct.iter_unpack('<qq',pairs))
  hashes=c.dump(caller+229376,113*32,T,'hashes.bin');assert hashes==bytes.fromhex(''.join(b['cases']['expectedHashes']))
  assert c.dump(caller+163840,113*4,T,'assertions.bin')==bytes(113*4)
  private=c.dump(0x400000,65536,T,'private.bin');base,size,ready=struct.unpack_from('<3Q',private,33536);assert size==8388608 and ready==g.MARKER
  assert all(base+size<=at or at+262144<=base for at in [owner,caller])
  pool=c.dump(base,size,T,'pool.bin');expected=bytearray(size);struct.pack_into('<I',expected,0,0x12345678);struct.pack_into('<I',expected,size-4,0x87654321);assert pool==expected
  registers=c.hmp('info registers');(T/'registers.txt').write_text(registers);assert 'CR3=0000000000530000' in registers,registers
  leaves=[]
  for leaf in range(base//2097152,(base+size-1)//2097152+1):
   value=struct.unpack('<Q',c.dump(0x532000+leaf*8,8,T,'leaf-last.bin'))[0];assert value&(1<<63) and not(value&4) and value&0x83==0x83
   leaves.append(dict(index=leaf,pde=value))
  report.update(state='PASS_REAL_RUNTIME_APPLICATION_POOL',caseCount=113,words=words,cursorGuards=12,assertionFailures=0,fullHashesMatch=True,returnsMatch=True,pool=m.pin(T/'pool.bin'),poolBase=base,domains=[owner,caller],supervisorNXLeaves=leaves,userCodeExecuted=False,physical=False,appConnection=False);save();print(report['state'],report['kernel'],report['efi'],flush=True)
 except BaseException as error:
  report.update(state='FAILED',failure=str(error));save();raise
 finally:
  if q.poll() is None:
   try:c.call('quit')
   except Exception: q.terminate()
   q.wait(timeout=10)
