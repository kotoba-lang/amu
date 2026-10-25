from pathlib import Path
import importlib.util,json,struct,hashlib
BASE=Path(__file__).with_name('native-map.py')
s=importlib.util.spec_from_file_location('prior_physical',BASE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
scope={};exec(Path(__file__).with_name('scratch-effects.py').read_text(),scope);effects=scope['effects']
def asr(d,n,p):return 0x93400000|(p<<16)|(63<<10)|(n<<5)|d
def integer(w):
 return any([w&0xff800000 in(0xd2800000,0xf2800000),w&0xff000000 in(0x91000000,0xd1000000,0xb1000000,0xf1000000),w&0xffc00000 in(0xd3400000,0x93400000),w&0xff800000 in(0x92000000,0xb2000000,0xd2000000),w&0xff200000 in(0x8b000000,0xcb000000,0xeb000000,0xab000000,0x8a000000,0xaa000000,0xca000000),w&0xffe00c00 in(0x9a800000,0x9a800400),w&0xffe00000==0x9b000000])
def audit(old,arm):
 A,ae=m.payload(old);N,ne=m.payload(arm);S=Path(old['source']['path']).read_bytes();assert S==Path(arm['source']['path']).read_bytes()
 assert len(A)==len(N)and ae==ne
 if A==N:return dict(status='PASS_WHOLE_NATIVE_CONTAINER_SOURCE_EXPORT_IDENTITY',changed=False)
 pool,entries=m.source_pool(S);end=len(A)-len(pool);assert A[end:]==N[end:]==pool and end%4==0
 a=list(struct.unpack('<'+'I'*(end//4),A[:end]));b=list(struct.unpack('<'+'I'*(end//4),N[:end]));roots={0}|{p for p,arity in ae.values()};refs=[]
 for i,w in enumerate(a):
  pc=i*4;r=m.ref(w,pc)
  if r:
   refs.append(dict(pc=pc,kind=r[0],target=r[1]));roots.add(r[1])
   if r[0]=='BL':roots.add(pc+4)
  if w&0xffe0001f==0xd4200000 or w==0 or w==0xd65f03c0:roots.add(pc+4)
  # Complete generated ADR-self / ADD-low12 / ADD-high12 pointer recipe.
  if i+2<len(a)and w&~31==0x10000000:
   reg=w&31;lo=0x91000000|(reg<<5)|reg;hi=lo|0x400000
   if a[i+1]&~0x3ffc00==lo and a[i+2]&~0x3ffc00==hi:roots.add(pc+((a[i+1]>>10)&4095)+(((a[i+2]>>10)&4095)<<12))
 def bound(reg,pc,work):
  if pc<0 or work<=0 or not 0<=reg<31:raise AssertionError(('NO_BOUNDED_POSITIVE_DEFINITION',reg,pc))
  w=a[pc//4];assert integer(w),('UNKNOWN_RANGE_OPERATION',pc,hex(w))
  rr,ww,ns,kind=effects(w,pc);assert kind=='normal' and ns==[pc+4]
  if reg not in ww:
   assert pc not in roots,('RANGE_INCOMING_EDGE',pc)
   v,proof=bound(reg,pc-4,work-1);return v,[dict(pc=pc,word=hex(w),writes=sorted(ww),preservedRegister=reg)]+proof
  if w&0xffe00000==0xd2800000:return (w>>5)&65535,[dict(pc=pc,word=hex(w),reason='complete MOVZ64 low16')]
  if w&0xffff0000==0x92400000 and (w>>10)&63<=30:return (1<<(((w>>10)&63)+1))-1,[dict(pc=pc,word=hex(w),reason='complete AND64 low contiguous mask')]
  assert pc not in roots,('RANGE_DEFINITION_INCOMING',pc)
  if w&~((31<<16)|31)==0xaa0003e0:return bound((w>>16)&31,pc-4,work-1)
  if w&0xffe0fc00==0x9b007c00:
   va,pa=bound((w>>5)&31,pc-4,(work-1)//2);vb,pb=bound((w>>16)&31,pc-4,(work-1)//2)
   assert va*vb<=(1<<63)-1,('SIGNED64_OVERFLOW_REFUSAL',pc,va,vb)
   return va*vb,[dict(pc=pc,word=hex(w),reason='full64 MUL bounded no signed overflow',left=va,right=vb)]+pa+pb
  raise AssertionError(('UNKNOWN_RANGE_DEFINITION',pc,hex(w)))
 def dead17(pc):
  rows=[]
  for _ in range(64):
   assert pc<end;w=a[pc//4];rr,ww,ns,kind=effects(w,pc)
   assert kind=='normal'and ns==[pc+4]and 17 not in rr,('SCRATCH17_NOT_DEAD',pc,hex(w),rr,kind)
   rows.append(dict(pc=pc,word=hex(w),reads=sorted(rr),writes=sorted(ww)))
   if 17 in ww:return rows
   assert pc not in roots,('SCRATCH17_INCOMING_ROOT',pc);pc+=4
  raise AssertionError('SCRATCH17_PROOF_BUDGET')
 sites=[]
 for i,(u,v)in enumerate(zip(a,b)):
  if u==v:continue
  pc=i*4;x=(u>>5)&31;assert 9<=x<=15 and i+3<=len(a)
  p=(a[i+2]>>16)&63;assert 2<=p<=62
  assert a[i:i+3]==[asr(17,x,63),0x8b000000|(1<<22)|((64-p)<<10)|(17<<16)|(x<<5)|x,asr(x,x,p)]
  assert v==0x14000002 and b[i+1:i+3]==a[i+1:i+3]
  assert all(q not in roots for q in range(pc,pc+12,4)),('QUOTIENT_INTERIOR_ENTRY',pc)
  upper,proof=bound(x,pc-4,64);scratch=dead17(pc+12)
  sites.append(dict(pc=pc,target=pc+8,dividendRegister=x,power=p,maximumDividend=upper,rangeProof=proof,scratch17Proof=scratch,oldWords=[hex(z)for z in a[i:i+3]],newFirstWord=hex(v),originalOutputAndNZCVPreserved=True))
 assert sites
 for r in refs:
  assert m.ref(b[r['pc']//4],r['pc'])==(r['kind'],r['target'],m.ref(a[r['pc']//4],r['pc'])[2])
 return dict(status='PASS_SAME_LAYOUT_POSITIVE_QUOTIENT_B2_FULL_NATIVE_RANGE_AND_SCRATCH',changed=True,sites=sites,allOtherWordsRefsExportsAndPoolExact=True,sourcePoolBytes=len(pool),performanceMeasured=False)
