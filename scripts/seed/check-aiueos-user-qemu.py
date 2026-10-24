#!/usr/bin/env python3
"""Observe CPL3/SYSCALL and real page faults; no compiler or native verdict."""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path

def pin(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def main(efi,kernel,qemu,firmware,output,mode):
 assert mode in range(8)
 image=kernel.read_bytes();boot_image=efi.read_bytes();assert boot_image.count(image)==1
 pe=struct.unpack_from('<I',boot_image,60)[0];loader_base=struct.unpack_from('<Q',boot_image,pe+24+24)[0]
 loader_text=struct.unpack_from('<I',boot_image,pe+24+240+8)[0]
 rx=struct.unpack_from('<IIQQQQQQ',image,64);rw=struct.unpack_from('<IIQQQQQQ',image,120);context=rw[3]
 assert rw[5]==0x240000 and struct.unpack_from('<Q',image,rw[2]+464)[0]==0x334c5652
 table=struct.unpack_from('<Q',image,rw[2]+328)[0]
 code=context+0x20000;request=code+4096;stack=code+12288;guard=code+8192
 fault=mode in (1,2,3,6,7);vector=6 if mode==7 else 13 if mode==6 else 14
 expected_pc=table+vector*128+126 if fault else code+51
 output.mkdir(parents=True,exist_ok=False);esp=output/'esp/EFI/BOOT';esp.mkdir(parents=True);shutil.copy2(efi,esp/'BOOTX64.EFI')
 args=[str(qemu),'-machine','q35,accel=tcg','-cpu','max','-m','128M','-smp','1',
       '-drive',f'if=pflash,format=raw,readonly=on,file={firmware}','-drive','file=fat:rw:esp,format=raw',
       '-boot','order=c','-nic','none','-display','none','-no-reboot','-serial','file:serial.log',
       '-debugcon','file:debug.log','-global',f'isa-debugcon.readback={mode}',
       '-qmp','unix:qmp.sock,server=on,wait=off','-d','int','-D','exceptions.log']
 (output/'command.json').write_text(json.dumps(args,indent=2)+'\n')
 log=open(output/'qemu.log','wb');proc=subprocess.Popen(args,cwd=output,stdout=log,stderr=subprocess.STDOUT);conn=None;stream=None;seq=0;registers='';old_cwd=Path.cwd();os.chdir(output)
 try:
  end=time.monotonic()+90
  while not (output/'qmp.sock').exists():
   assert proc.poll() is None,('QEMU exited',proc.returncode)
   assert time.monotonic()<end,'QMP startup timeout';time.sleep(.2)
  conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);conn.settimeout(10);conn.connect('qmp.sock');stream=conn.makefile('rwb',buffering=0);assert 'QMP' in json.loads(stream.readline())
  def call(command,arguments=None):
   nonlocal seq
   seq+=1;row=dict(execute=command,id=seq)
   if arguments is not None:row['arguments']=arguments
   stream.write(json.dumps(row).encode()+b'\n')
   while True:
    result=json.loads(stream.readline())
    if result.get('id')==seq:
     assert 'error' not in result,result
     return result['return']
  def hmp(command):return call('human-monitor-command',{'command-line':command})
  def dump(base,size,name):
   assert hmp(f'pmemsave 0x{base:x} {size} {name}')==''
   return (output/name).read_bytes()
  call('qmp_capabilities')
  while time.monotonic()<end:
   assert proc.poll() is None,('guest exited',proc.returncode)
   registers=hmp('info registers');(output/'registers-last.txt').write_text(registers)
   if re.search(rf'RIP=0*{expected_pc:x}\b',registers,re.I):break
   handler=struct.unpack_from('<Q',image,rw[2]+30400)[0]
   unexpected=tuple(pc for pc in (table+6*128+126,table+13*128+126,table+14*128+126,handler+1022,loader_base+4096+loader_text-2) if pc!=expected_pc)
   if any(re.search(rf'RIP=0*{pc:x}\b',registers,re.I) for pc in unexpected):
    dump(context,65536,'failed-context.bin');raise AssertionError('unexpected native loader/entry/fault halt: '+registers[:500])
   if re.search(r'RIP=0*10104b\b',registers,re.I):
    dump(context,65536,'failed-context.bin');raise AssertionError('user setup returned instead of entering CPL3')
   time.sleep(.5)
  else:
   dump(context,65536,'failed-context.bin');raise AssertionError('declared user/fault endpoint not reached')
  call('stop');(output/'registers.txt').write_text(registers)
  state=dump(context,65536,'user-context.bin');page=dump(request,4096,'user-request.bin')
  def reg(name):return int(re.search(rf'\b{name}\s*=([0-9a-f]+)',registers,re.I)[1],16)
  assert reg('CR3')==context+0x30000 and reg('CR0')&0x10000 and not reg('CR4')&0x1000
  assert reg('EFER')&0x801==0x801
  assert struct.unpack_from('<Q',state,32832)[0]==1 and struct.unpack_from('<Q',state,480)[0]==73
  assert struct.unpack_from('<I',state,49152+12)[0]==1
  pml4=struct.unpack('<512Q',dump(context+0x30000,4096,'pml4.bin'))
  pdpt=struct.unpack('<512Q',dump(context+0x31000,4096,'pdpt.bin'))
  pds=struct.unpack('<262144Q',dump(context+0x32000,2097152,'pds.bin'))
  small=struct.unpack('<2048Q',dump(context+0x232000,16384,'small.bin'))
  mask=0xffffffffffffffff^0x60  # Hardware-accessed/dirty bits are observations.
  assert (pml4[0]&mask)==context+0x31000+7 and all((p&mask)==0 for p in pml4[1:])
  assert all((p&mask)==context+0x32000+i*4096+7 for i,p in enumerate(pdpt))
  for i,p in enumerate(pds):
   expected=context+0x232000+i*4096+7 if i<4 else (i*2097152)|0x8000000000000083
   assert p&mask==expected,('PD',i,hex(p),hex(expected))
  user_pages={}
  for slot in range(4):
   for role in range(4):
    physical=context+0x20000+slot*16384+role*4096
    expected=0 if role==2 else physical|((5 if role==0 else 0x8000000000000007) if slot==0 else 0x8000000000000003)
    user_pages[physical]=expected
  for i,p in enumerate(small):
   physical=i*4096
   expected=user_pages.get(physical,0 if i==0 else physical|(1 if 0x101000<=physical<context else 0x8000000000000003))
   assert p&mask==expected,('PTE',i,hex(p),hex(expected))
  cpl=int(re.search(r'\bCPL=([0-3])',registers)[1]);details={}
  if fault:
   cr2,error,cs,rip,rsp,magic,observed_vector=struct.unpack_from('<7Q',state,33024)
   assert (cs,magic,observed_vector)==(0x23,0x334c5652,vector)
   if vector==14:
    assert (cr2,error)==({1:context,2:request,3:guard}[mode],{1:5,2:21,3:6}[mode])
   else:assert error==0
   expected_rip=request if mode==2 else code+({6:6,7:0}.get(mode,10))
   assert rip==expected_rip and stack<=rsp<stack+4096
   assert cpl==0 and context+65536<=reg('RSP')<context+131072
   details=dict(vector=observed_vector,cr2=cr2,error=error,userCS=cs,userRIP=rip,userRSP=rsp)
  else:
   result,returned_r9=struct.unpack_from('<QQ',page,128);expected=72057594037927943 if mode==0 else 0
   assert cpl==3 and result==expected and returned_r9==0 and reg('RAX')==expected
   assert reg('R9')==0 and stack<=reg('RSP')<stack+4096 and reg('RFL')&0x77700==0
   if mode==0:assert state[32896:32896+96]==page[:56]+bytes(40)
   else:assert state[32896:32896+96]==bytes(96),'rejected call mutated kernel request'
   details=dict(result=result,forgedR9Discarded=True,privateRegistersCleared=True)
  fpu=re.findall(r'FPR[0-7]=([0-9a-f]+)\s+([0-9a-f]+)',registers,re.I)
  xmm=re.findall(r'XMM[0-9]{2}=([0-9a-f]+)\s+([0-9a-f]+)',registers,re.I)
  assert len(fpu)==8 and len(xmm)==16 and all(int(a,16)==int(b,16)==0 for a,b in fpu+xmm)
  assert reg('MXCSR')==0x1f80 and reg('FCW')==0x37f
  report=dict(status='PASS_NATIVE_USER_ENTRY_QEMU',mode=mode,details=details,efi=pin(efi),kernel=pin(kernel),observer=pin(Path(__file__)),firmware=pin(firmware),
              qemuVersion=subprocess.check_output([str(qemu),'--version']).decode().splitlines()[0],pageTable=pin(output/'pds.bin'),
              userPageTables=True,kernelWriteProtected=True,guestEmulation='QEMU TCG',nativeCDCI=False,
              initialLegacyFpuCleared=True,extendedState=False,fpuContextSwitch=False,
              applicationCompiler=False,preemptiveScheduler=False,completeKernel=False,media=False,desktopInput=False,physicalHardware=False)
  (output/'user-entry-qemu.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],mode)
 finally:
  if proc.poll() is None:
   try:
    if stream:call('quit')
   except (OSError,ValueError,AssertionError):pass
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
  if stream:stream.close()
  if conn:conn.close()
  log.close()
  os.chdir(old_cwd)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['efi','kernel','qemu','firmware','output']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',type=int,required=True,choices=range(8));a=p.parse_args();main(*(getattr(a,n).resolve() for n in ['efi','kernel','qemu','firmware','output']),a.mode)
