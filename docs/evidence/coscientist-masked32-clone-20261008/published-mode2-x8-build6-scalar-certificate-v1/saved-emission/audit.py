"""Saved bytes + pure A64 fixture interpreter. No native or operational APIs."""
from pathlib import Path
import struct,json,hashlib,copy,stat
D=Path(__file__).resolve().parent
A=D.parent/'published-mode2-x8-build-fixture6-source-v1-20261009'
def need(v,m):
 if not v:raise AssertionError(m)
def rec(p):
 s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink(),'regular saved file');b=p.read_bytes();z=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable saved bytes');return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def signed(x,n):return x-(1<<n)if x&(1<<(n-1))else x
# Exact fixture-only decoding; unknown instructions/operands fail closed.
FIXED={0xa9bf7bfd:'stp29,30-pre16',0x910003fd:'mov29,sp',0xd10103ff:'subsp64',0xf90003f3:'store19,sp0',0xf9001fe7:'store7,sp56',0xaa0003f3:'mov19,0',0xf94004f0:'load16,ctx8',0xf1000610:'subs16,16,1',0xf90004f0:'store16,ctx8',0xf100027f:'cmp19,0',0xd2800229:'mov9,17',0xd1000669:'sub9,19,1',0xaa0903e0:'mov0,9',0xf9401fe7:'load7,sp56',0xaa0003e9:'mov9,0',0xf94003f3:'load19,sp0',0x910003bf:'movsp,29',0xa8c17bfd:'ldp29,30-post16',0xd65f03c0:'ret30',0xd4200000:'fuel-trap0',0xd4200020:'unreachable-trap1',0xf94004e8:'load8,ctx8',0xf1000508:'subs8,8,1',0xf90004e8:'store8,ctx8'}
def decode(w,pc):
 if w in FIXED:return dict(op=FIXED[w],word=f'{w:08x}')
 if w&0xfc000000 in (0x14000000,0x94000000):return dict(op='bl'if w&0xfc000000==0x94000000 else'b',target=pc+4*signed(w&0x3ffffff,26),word=f'{w:08x}')
 if w&0xff000010==0x54000000:
  cond=w&15;need(cond in (1,2),'fixture only BNE/BHS');return dict(op='bne'if cond==1 else'bhs',target=pc+4*signed((w>>5)&0x7ffff,19),word=f'{w:08x}')
 raise AssertionError('UNKNOWN_OPCODE_OR_OPERAND '+hex(w))
def decoded(raw):
 need(len(raw)==236,'exact finite fixture59 words');return {i*4:decode(w,i*4)for i,(w,)in enumerate(struct.iter_unpack('<I',raw))}
def cfg(code):
 # RET may target only the two statically resolved BL continuations or outer sentinel.
 returns={p+4 for p,d in code.items()if d['op']=='bl'};need(returns=={76,180},'exact returning callers')
 edges={};work=[208];seen=set()
 while work:
  p=work.pop()
  if p in seen:continue
  need(p in code,'in-payload aligned target');seen.add(p);d=code[p];op=d['op']
  if op=='ret30':succ=sorted(returns)
  elif op in ['fuel-trap0','unreachable-trap1']:succ=[]
  elif op in ['b','bl']:succ=[d['target']]
  elif op in ['bne','bhs']:succ=[p+4,d['target']]
  else:succ=[p+4]
  need(all(q in code for q in succ),'no indirect unknown/outside target');edges[p]=succ;work+=succ
 need(100 not in seen and 204 not in seen and 232 not in seen,'padding BRK1 unreachable')
 return dict(entry=208,reachableWords=len(seen),reachableOffsets=sorted(seen),edges=edges,returnContinuations=sorted(returns),outerReturn='initial loader x30 only')
MASK=(1<<64)-1
CTX=0x100000;SP0=0x1000000;DONE=0x2000000
def execute(code,n,fuel,maxsteps=4096):
 need(type(n)is int and 0<=n<=16 and type(fuel)is int and 0<=fuel<=MASK,'bounded modeled inputs')
 r=[0]*31;r[0]=n;r[7]=CTX;r[30]=DONE;sp=SP0;pc=208;stack={};allocated=[];memory={CTX+8:fuel};carry=False;zero=False;trace=[];writes=[];steps=0
 def stackread(a):need(a in stack and any(lo<=a<hi for lo,hi in allocated),'live initialized stack read');return stack[a]
 def stackwrite(a,v):need(any(lo<=a<hi for lo,hi in allocated),'live stack write');stack[a]=v
 while pc!=DONE:
  need(steps<maxsteps and pc in code,'bounded interpreter/known PC');steps+=1;trace.append(pc);d=code[pc];op=d['op'];nextpc=pc+4
  if op=='stp29,30-pre16':sp-=16;allocated.append((sp,sp+16));stackwrite(sp,r[29]);stackwrite(sp+8,r[30])
  elif op=='mov29,sp':r[29]=sp
  elif op=='subsp64':sp-=64;allocated.append((sp,sp+64))
  elif op=='store19,sp0':stackwrite(sp,r[19])
  elif op=='store7,sp56':stackwrite(sp+56,r[7])
  elif op=='mov19,0':r[19]=r[0]
  elif op in ['load16,ctx8','load8,ctx8']:
   need(r[7]==CTX,'context pointer preserved');r[16 if op.startswith('load16')else 8]=memory[CTX+8]
  elif op in ['subs16,16,1','subs8,8,1']:
   k=16 if op.startswith('subs16')else 8;carry=r[k]>=1;r[k]=(r[k]-1)&MASK;zero=r[k]==0
  elif op in ['store16,ctx8','store8,ctx8']:
   need(r[7]==CTX,'context pointer preserved');v=r[16 if op.startswith('store16')else 8];writes.append((pc,memory[CTX+8],v));memory[CTX+8]=v
  elif op=='cmp19,0':zero=r[19]==0;carry=True
  elif op=='mov9,17':r[9]=17
  elif op=='sub9,19,1':r[9]=(r[19]-1)&MASK
  elif op=='mov0,9':r[0]=r[9]
  elif op=='load7,sp56':r[7]=stackread(sp+56)
  elif op=='mov9,0':r[9]=r[0]
  elif op=='load19,sp0':r[19]=stackread(sp)
  elif op=='movsp,29':need(allocated[-1]==(sp,r[29]),'exact64-byte frame retirement');allocated.pop();sp=r[29]
  elif op=='ldp29,30-post16':r[29]=stackread(sp);r[30]=stackread(sp+8);need(allocated[-1]==(sp,sp+16),'exact16-byte frame retirement');allocated.pop();sp+=16
  elif op=='ret30':nextpc=r[30];need(nextpc in (76,180,DONE),'known saved return owner')
  elif op=='bl':r[30]=pc+4;nextpc=d['target']
  elif op=='b':nextpc=d['target']
  elif op in ['bne','bhs']:
   if (not zero)if op=='bne'else carry:nextpc=d['target']
  elif op=='fuel-trap0':return dict(status='fuel-trap0',pc=pc,fuel=memory[CTX+8],writes=writes,trace=trace,steps=steps,context=r[7])
  else:raise AssertionError('unreachable padding/unknown semantic operation')
  pc=nextpc
 need(sp==SP0 and not allocated and r[7]==CTX,'closed model stack/context')
 return dict(status='return',result=r[0],fuel=memory[CTX+8],writes=writes,trace=trace,steps=steps,context=r[7])
def main():
 import sys
 sys.path.insert(0,str(A));from run import container
 report=json.loads((A/'run-outputs/report.json').read_bytes());terminal=json.loads((A/'run-outputs/terminal.json').read_bytes());need(report['closedCompilerCalls']==6 and terminal['allChildrenClosed']and not terminal['failure'],'saved closed campaign only')
 arts=json.loads((A/'run-outputs/artifacts.json').read_bytes());codes={};pins={}
 for side in ['off','on']:
  a=next(x for x in arts if x['label']==side.upper()+'-fixture-extract');raw=Path(a['native']['path']).read_bytes();packed=Path(a['container']['path']).read_bytes();payload,exports=container(packed);need(payload==raw and exports==[('bench',208,1)],'whole fixture payload/export ownership');need(rec(Path(a['native']['path']))==a['native']and rec(Path(a['container']['path']))==a['container'],'saved native/container receipts');codes[side]=decoded(raw);pins[side]=dict(native=a['native'],container=a['container'],export=exports[0])
 diffs=[p for p in codes['off']if codes['off'][p]!=codes['on'][p]];need(diffs==[208,212,224],'exact changed three words only');need(all(codes['off'][p]==codes['on'][p]for p in range(0,208,4)),'both helper bodies unchanged')
 graphs={k:cfg(c)for k,c in codes.items()};need(graphs['off']==graphs['on'],'same complete reachable CFG')
 # Complete reachable x7/x8/context footprint is fixture-specific, closed by exact opcode whitelist.
 footprint={side:[dict(pc=p,**d)for p,d in code.items()if p in graphs[side]['reachableOffsets']and any(s in d['op']for s in ['load7','store7','load8','subs8','store8','ctx8'])]for side,code in codes.items()}
 modeled=[]
 for n in range(5):
  for fuel in [0,1,2,3,4,5,6,7,8,9,10,MASK]:
   a=execute(codes['off'],n,fuel);b=execute(codes['on'],n,fuel);need(a==b,'exact model trace/state/fuel/write parity');need(a['status']==('return'if fuel>=n+2 else'fuel-trap0'),'expected n+2 charges');need(a['fuel']==max(0,fuel-(n+2)),'published counter/trap prefix');modeled.append(dict(n=n,fuel=fuel,status=a['status'],pc=a.get('pc'),steps=a['steps']))
 mutants=[]
 for name,change in [('unknown-x8-writer',lambda c:c.update({64:decode(0xd2800008,64)})),('unknown-target',lambda c:c[228].update(target=240)),('wrong-context-restore',lambda c:c.update({68:decode(0xf94003e7,68)})),('skipped-published-fuel',lambda c:c[224].update(op='mov9,17')),('missing-x8-initialization',lambda c:c[208].update(op='mov9,17'))]:
  try:
   q=copy.deepcopy(codes['on']);change(q);cfg(q);a=execute(codes['off'],2,6);b=execute(q,2,6);need(a==b,'semantic mutant rejected')
  except AssertionError:mutants.append(name)
  else:raise AssertionError('mutant admitted:'+name)
 out=dict(status='PASS_SAVED_FIXTURE_ONLY_CFG_AND_PURE_WORD_MODEL_WITH_STAGE_PATHS_HOLD',savedArtifacts=pins,changedOffsets=diffs,decoded=codes,CFG=graphs,contextAndFuelFootprint=footprint,pureModeledCases=modeled,refusedMutants=mutants,actualNativeGuestExecuted=False,actualMachineModelIsProductionProof=False,fixtureBenchWrapperPublishedX8Observed=True,helperPublishedX8Observed=False,gnOpFn2SingleEntryInitializationObservedBySourceAndSavedWordInference=True,privateFFCodePlus1Exercised=False,full19CertificateQualified=False,generalCandidateAdoptionQualified=False,assumptions=['loader entry provides live disjoint x7 context and stack; x30 outerreturn','no asynchronous foreign writes to context fuel','pure model covers finite n0..4/fuel boundary cases only'],HOLD=['typed admission path observer missing; single entry initialization inferred from exact source and saved words','fixture stage does not exercise multiple debit reuse or private +1','actual runtime fuel/trap/17arena/loader outcomes remain unexecuted'])
 (D/'report.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(status=out['status'],wordsEach=59,reachableWords=graphs['on']['reachableWords'],modeled=len(modeled),mutants=mutants)))
if __name__=='__main__':main()
