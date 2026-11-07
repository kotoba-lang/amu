# Test-only source-operation encoder plus LLDB in-memory disassembly.
# It does not invoke the Kotoba compiler or execute the instructions.
import lldb,re,struct,sys,hashlib
from pathlib import Path
src=Path(sys.argv[1]).read_text();assert hashlib.sha256(src.encode()).hexdigest()=='a387d7ec0d4b991ffdc2b29b83bdd3d948af3b9a4a5cd5badbbee5c261c9cf2c'
b=src[src.index('(defn- watcher-words'):src.index('(defn- body-at')];b=re.sub(r';;[^\n]*','',b)
ops=[(n,[int(x,0) for x in a.split()]) for n,a in re.findall(r'\((ds-[a-z]+)\s+([^()]*)\)',b)]
words=[];checks=[];labels={};fix=[]
def emit(w,kind,args):words.append(w);checks.append((kind,args))
def imm(rd,v):
 emit(0xd2800000|rd|((v&65535)<<5),'movz',(rd,v&65535))
 emit(0xf2a00000|rd|(((v>>16)&65535)<<5),'movk',(rd,(v>>16)&65535))
for op,a in ops:
 if op=='ds-label':labels[a[0]]=len(words);continue
 if op=='ds-b':fix.append((len(words),a[0],a[1]));emit(a[0],'branch',(a[0]&15,a[1]));continue
 if op=='ds-imm':imm(*a);continue
 if op=='ds-sys':imm(16,33554432+a[0]);emit(0xd4001001,'svc',(a[0],));continue
 if op=='ds-i':emit(a[0],'literal',(a[0],));continue
 if op in ('ds-add','ds-sub'):
  rd,rn,v=a;emit((0x91000000 if op=='ds-add' else 0xd1000000)|rd|(rn<<5)|(v<<10),op[3:],tuple(a));continue
 if op in ('ds-ldr','ds-str','ds-lw','ds-sw','ds-lh'):
  rd,rn,off=a;scale={'ds-ldr':8,'ds-str':8,'ds-lw':4,'ds-sw':4,'ds-lh':2}[op];base={'ds-ldr':0xf9400000,'ds-str':0xf9000000,'ds-lw':0xb9400000,'ds-sw':0xb9000000,'ds-lh':0x79400000}[op]
  emit(base|rd|(rn<<5)|((off//scale)<<10),op[3:],tuple(a));continue
 if op=='ds-and':rd,rn,rm=a;emit(0x8a000000|rd|(rn<<5)|(rm<<16),'and',tuple(a));continue
 if op=='ds-cmpi':rn,v=a;emit(0xf100001f|(rn<<5)|(v<<10),'cmpi',tuple(a));continue
 if op=='ds-cmp':rn,rm=a;emit(0xeb00001f|(rn<<5)|(rm<<16),'cmp',tuple(a));continue
 raise RuntimeError((op,a))
for at,op,label in fix:
 delta=labels[label]-at;words[at]=op|((delta&0x7ffff)<<5)
lldb.SBDebugger.Initialize();dbg=lldb.SBDebugger.Create();target=dbg.CreateTarget('/usr/bin/true');base=0x100000400;addr=lldb.SBAddress();addr.SetLoadAddress(base,target)
def xr(n):return 'xzr' if n==31 else 'x'+str(n)
def base_reg(n):return 'sp' if n==31 else 'x'+str(n)
def mem(rn,off):return '['+base_reg(rn)+('' if off==0 else ', #'+hex(off))+']'
def intended(kind,a):
 if kind=='movz':return 'mov',f'x{a[0]}, #{hex(a[1])}'
 if kind=='movk':return 'movk',f'x{a[0]}, #{hex(a[1])}, lsl #16'
 if kind in ('add','sub'):
  rd,rn,n=a;dest='sp' if rd==31 else xr(rd);source=base_reg(rn)
  return ('mov',f'{dest}, {source}') if kind=='add' and n==0 and rn==31 else (kind,f'{dest}, {source}, #{hex(n)}')
 if kind in ('ldr','str','lw','sw','lh'):
  rd,rn,off=a;mn={'ldr':'ldr','str':'str','lw':'ldr','sw':'str','lh':'ldrh'}[kind]
  reg=('wzr' if rd==31 else 'w'+str(rd)) if kind in ('lw','sw','lh') else xr(rd)
  return mn,f'{reg}, {mem(rn,off)}'
 if kind=='cmp':return 'cmp',f'{xr(a[0])}, {xr(a[1])}'
 if kind=='cmpi':return 'cmp',f'{xr(a[0])}, #{hex(a[1])}'
 if kind=='and':return 'and',f'{xr(a[0])}, {xr(a[1])}, {xr(a[2])}'
 if kind=='svc':return 'svc','#0x80'
 if kind=='branch':return {0:'b.eq',1:'b.ne',2:'b.hs',8:'b.hi'}[a[0]],hex(base+4*labels[a[1]])
 if kind=='literal':return {0xaa1303e1:('mov','x1, x19'),0xaa0003f7:('mov','x23, x0'),0xaa1703e0:('mov','x0, x23'),0xd4200000:('brk','#0')}[a[0]]
 raise AssertionError((kind,a))
def verify(candidate):
 ins=target.GetInstructions(addr,struct.pack('<'+'I'*len(candidate),*candidate));assert ins.GetSize()==len(candidate),(ins.GetSize(),len(candidate))
 for i,(item,(kind,args)) in enumerate(zip(ins,checks)):
  actual=(item.GetMnemonic(target),item.GetOperands(target));expected=intended(kind,args)
  if actual!=expected:raise AssertionError((i,kind,args,actual,expected))
try:
 verify(words)
 idx=next(i for i,c in enumerate(checks) if c==('literal',(0xaa1303e1,)))
 mutant=words.copy();mutant[idx]=0xaa1403e1
 try:verify(mutant);raise RuntimeError('register mutation passed')
 except AssertionError:pass
 idx=next(i for i,c in enumerate(checks) if c[0]=='branch')
 mutant=words.copy();mutant[idx]+=32
 try:verify(mutant);raise RuntimeError('branch mutation passed')
 except AssertionError:pass
 print('source_sha256',hashlib.sha256(src.encode()).hexdigest(),'disassembled_in_memory',len(words),'register_and_branch_mutants','refused')
 print('modeled encoder plus LLDB only; no Kotoba compilation, generated artifact or instruction execution')
finally:lldb.SBDebugger.Destroy(dbg);lldb.SBDebugger.Terminate()
