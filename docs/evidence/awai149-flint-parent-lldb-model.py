#!/usr/bin/env python3
"""Model source builder words and compare LLDB decoding; does not emit or execute an image."""
import hashlib,importlib.util,lldb,re,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[2]
source=(root/'seed/macos-flint-parent-fd-packager.kotoba').read_text()
if hashlib.sha256(source.encode()).hexdigest()!='9b1cd906ec0e670ff2bbbc65b1bace291a28283166eca151f730d0b16f281239':raise ValueError('source pin mismatch')
spec=importlib.util.spec_from_file_location('model',root/'docs/evidence/awai149-flint-parent-source-sim.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
ops=model.load_program();words=[];checks=[];labels={};fix=[]
def emit(word,kind,args):words.append(word);checks.append((kind,args))
def imm(rd,v):
 emit(0xd2800000|rd|((v&65535)<<5),'movz',(rd,v&65535));emit(0xf2a00000|rd|(((v>>16)&65535)<<5),'movk',(rd,(v>>16)&65535))
for op,a in ops:
 if op=='label':
  if a[0] in labels:raise ValueError('duplicate label')
  labels[a[0]]=len(words);continue
 if op=='b':fix.append((len(words),a[0],a[1]));emit(a[0],'branch',(a[0],a[1]));continue
 if op=='imm':imm(*a);continue
 if op=='sys':imm(16,33554432+a[0]);emit(0xd4001001,'svc',(a[0],));continue
 if op=='i':emit(a[0],'literal',(a[0],));continue
 if op=='hex-digit':
  emit(0x9100c16b,'add',(11,11,48));emit(0xf100e57f,'cmpi',(11,57));emit(0x91009d6c,'add',(12,11,39));emit(0x9a8b818b,'literal',(0x9a8b818b,));continue
 if op in ('add','sub'):
  rd,rn,n=a;emit((0x91000000 if op=='add' else 0xd1000000)|rd|(rn<<5)|(n<<10),op,a);continue
 if op in ('ldr','str','lw','sw','lh','lb','sb'):
  rd,rn,off=a;scale={'ldr':8,'str':8,'lw':4,'sw':4,'lh':2,'lb':1,'sb':1}[op]
  base={'ldr':0xf9400000,'str':0xf9000000,'lw':0xb9400000,'sw':0xb9000000,'lh':0x79400000,'lb':0x39400000,'sb':0x39000000}[op]
  if off%scale:raise ValueError('unaligned offset')
  emit(base|rd|(rn<<5)|((off//scale)<<10),op,a);continue
 if op=='cmpi':rn,n=a;emit(0xf100001f|(rn<<5)|(n<<10),'cmpi',a);continue
 if op=='cmp':rn,rm=a;emit(0xeb00001f|(rn<<5)|(rm<<16),'cmp',a);continue
 raise ValueError(('unmodeled op',op,a))
for at,op,label in fix:
 if label not in labels:raise ValueError('missing label')
 delta=labels[label]-at
 if op==0x14000000:
  if not -(1<<25)<=delta<(1<<25):raise ValueError('branch out of range')
  words[at]=op|(delta&0x03ffffff)
 else:
  if not -(1<<18)<=delta<(1<<18):raise ValueError('branch out of range')
  words[at]=op|((delta&0x7ffff)<<5)
lldb.SBDebugger.Initialize();dbg=lldb.SBDebugger.Create();target=dbg.CreateTarget('/usr/bin/true');base=0x100000400;addr=lldb.SBAddress();addr.SetLoadAddress(base,target)
def xr(n):return 'xzr' if n==31 else 'x'+str(n)
def br(n):return 'sp' if n==31 else 'x'+str(n)
def mem(rn,off):return '['+br(rn)+('' if off==0 else ', #'+hex(off))+']'
def intended(kind,a):
 if kind=='movz':return 'mov',f'x{a[0]}, #{hex(a[1])}'
 if kind=='movk':return 'movk',f'x{a[0]}, #{hex(a[1])}, lsl #16'
 if kind in ('add','sub'):
  rd,rn,n=a;dest='sp' if rd==31 else xr(rd);src=br(rn)
  return ('mov',f'{dest}, {src}') if kind=='add' and n==0 and rn==31 else (kind,f'{dest}, {src}, #{hex(n)}')
 if kind in ('ldr','str','lw','sw','lh','lb','sb'):
  rd,rn,off=a;mn={'ldr':'ldr','str':'str','lw':'ldr','sw':'str','lh':'ldrh','lb':'ldrb','sb':'strb'}[kind]
  reg=('wzr' if rd==31 else 'w'+str(rd)) if kind in ('lw','sw','lh','lb','sb') else xr(rd)
  return mn,f'{reg}, {mem(rn,off)}'
 if kind=='cmp':return 'cmp',f'{xr(a[0])}, {xr(a[1])}'
 if kind=='cmpi':return 'cmp',f'{xr(a[0])}, #{hex(a[1])}'
 if kind=='svc':return 'svc','#0x80'
 if kind=='branch':return ({0x14000000:'b',0x54000000:'b.eq',0x54000001:'b.ne',0x54000002:'b.hs'}[a[0]],hex(base+4*labels[a[1]]))
 if kind=='literal':return {0x12140d09:('and','w9, w8, #0xf000'),0xaa1403f8:('mov','x24, x20'),0xd344fd4b:('lsr','x11, x10, #4'),0x8a0c014b:('and','x11, x10, x12'),0xaa1803e1:('mov','x1, x24'),0xaa1903e2:('mov','x2, x25'),0x9a8b818b:('csel','x11, x12, x11, hi'),0xd4200000:('brk','#0')}[a[0]]
 raise ValueError(('unknown kind',kind,a))
def verify(candidate):
 ins=target.GetInstructions(addr,struct.pack('<'+'I'*len(candidate),*candidate))
 if ins.GetSize()!=len(candidate):raise AssertionError('instruction count')
 for i,(item,(kind,args)) in enumerate(zip(ins,checks)):
  actual=(item.GetMnemonic(target),item.GetOperands(target));want=intended(kind,args)
  if actual!=want:raise AssertionError((i,kind,args,actual,want))
try:
 verify(words)
 for idx,delta in [(next(i for i,c in enumerate(checks) if c[0]=='branch'),32),(next(i for i,c in enumerate(checks) if c==('literal',(0xaa1403f8,))),1)]:
  mutant=words.copy();mutant[idx]+=delta
  try:verify(mutant)
  except AssertionError:continue
  raise RuntimeError('mutant passed')
 print('source-sha256',hashlib.sha256(source.encode()).hexdigest(),'words',len(words),'branches',len(fix),'mutants-refused',2)
 print('Python-modeled instructions disassembled in memory; no generated helper or execution')
finally:lldb.SBDebugger.Destroy(dbg);lldb.SBDebugger.Terminate()
