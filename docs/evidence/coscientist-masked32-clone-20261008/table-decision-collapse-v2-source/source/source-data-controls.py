"""SOURCE-data finite controls. Does not run compiler, guest, solver or probe."""
from pathlib import Path
import json, hashlib, copy, re
W=Path(__file__).resolve().parent
R=Path('/Users/junkawasaki/github/wt/amu-seed17')
O=Path('/Users/junkawasaki/github/workspaces/codex/vector-typed-observer-native-v8')
rec=json.loads((O/'ports/crc32/observer-records.json').read_text())
sir={x['fields'][0]:x['fields'][1:] for x in rec if x['tag']=='SIR'}
lits={x['fields'][0]:x['fields'][1:] for x in rec if x['tag']=='LIT'}
src=R/'bench/embench/batch-ports/crc32.kotoba'
assert src.read_bytes()==(O/'sources/crc32.kotoba').read_bytes()
line=next(x for x in src.read_text().splitlines() if x.startswith('(defn- table-at'))
tables=[list(map(int,s.split())) for s in re.findall(r'\[([\d\s]+)\]',line)]
assert len(tables)==16 and all(len(x)==16 for x in tables)

def validate(s,ls,n=256):
 p=1;e=min(j for j,r in s.items() if r==[2,1,0,0])
 if s[p]!=[1,1,1,1] or s[p+1]!=[18,0,0,0] or s[e]!=[2,1,0,0]:return False
 labels={}
 for j in range(p+2,e):
  if s[j][0]==9:
   lab,a,b=s[j][1:]
   if lab<=0 or a or b or lab in labels:return False
   labels[lab]=j
 j=3;leaf=0
 while j<e:
  op,a,b,c=s[j]
  if op==9:j+=1;continue
  if op==10:
   if b or c or labels.get(a,0)<=j:return False
   j+=1;continue
  if j==e-1:
   if s[j]!=[19,0,0,0]:return False
   j+=1;continue
  if j+3>=e:return False
  if s[j]!=[4,0,1,0] or s[j+1][0:2]!=[3,1] or s[j+1][3]:return False
  if s[j+2]==[7,2,0,0]:
   z=s[j+3]
   if z[0:2]!=[11,0] or z[3] or labels.get(z[2],0)<=j+3:return False
  elif s[j+2]==[6,2,0,0]:
   if s[j+1][2]!=leaf*16 or s[j+3]!=[21,0,leaf+1,16]:return False
   if leaf+1 not in ls or ls[leaf+1][1]!=128:return False
   # N is the saved raw literal byte count (last128-byte origin ends2049).
   B=ls[leaf+1][0];N=2049;CAP=262144
   if N<128 or N>CAP or B<0 or B>N-128 or B>CAP-128:return False
   leaf+=1
  else:return False
  j+=4
 return leaf==n//16

# Independent finite SIR interpreter tracks original checked read and charge.
def path(s,x):
 end=min(j for j,r in s.items() if r==[2,1,0,0])
 labels={r[1]:j for j,r in s.items() if 1<j<end and r[0]==9}
 pc=2;t={};fuel=0;reads=[];trace=[]
 for _ in range(256):
  op,a,b,c=s[pc];trace.append(pc)
  if op==18:fuel+=1
  elif op==9:pass
  elif op==4:
   assert b==1;t[a]=x
  elif op==3:t[a]=b
  elif op==7:
   assert a==2;t[b]=int(t[b]<t[b+1])
  elif op==6:
   assert a==2;t[b]=(t[b]-t[b+1])&((1<<64)-1)
  elif op==11:
   if t[a]==0:pc=labels[b];continue
  elif op==10:pc=labels[a];continue
  elif op==21:
   assert 0<=t[a]<c;reads.append([b,t[a]]);t[a]=tables[b-1][t[a]]
  elif op==19:return {'value':t[a],'fuel':fuel,'reads':reads,'trace':trace}
  else:raise ValueError((pc,op))
  pc+=1
 raise ValueError('work cap')

assert validate(sir,lits)
paths=[path(sir,x) for x in range(256)]
for x,a in enumerate(paths):
 assert a['fuel']==1 and a['reads']==[[1+x//16,x%16]]
 assert a['value']==sum(tables,[])[x]
assert sir[216]==[3,1,255,0] and sir[217]==[6,5,0,0]
assert sir[218]==[5,7,0,0] and sir[219]==[4,0,7,0] and sir[220]==[13,1,0,1]

faults=[]
def fault(name,change):
 s=copy.deepcopy(sir);ls=copy.deepcopy(lits);change(s,ls)
 assert not validate(s,ls)
 faults.append({'fault':name,'admitted':False})
fault('path-dependent fuel',lambda s,l:s.__setitem__(25,[18,0,0,0]))
fault('runtime effect',lambda s,l:s.__setitem__(23,[14,1,0,2]))
fault('wrong chunk offset',lambda s,l:s.__setitem__(27,[3,1,17,0]))
fault('non-contiguous literal ID',lambda s,l:s.__setitem__(29,[21,0,3,16]))
fault('short physical slice',lambda s,l:l[2].__setitem__(1,120))
fault('backward edge',lambda s,l:s.__setitem__(24,[10,1,0,0]))
fault('duplicate label',lambda s,l:s.__setitem__(25,[9,1,0,0]))
fault('additional trap',lambda s,l:s.__setitem__(31,[20,0,0,0]))
fault('wrong result temp',lambda s,l:s.__setitem__(173,[19,1,0,0]))
fault('additional local mutation',lambda s,l:s.__setitem__(31,[5,1,0,0]))
fault('near-max LF-B metadata',lambda s,l:l[2].__setitem__(0,(1<<63)-1))
fault('negative LF-B metadata',lambda s,l:l[2].__setitem__(0,-1))
fault('short final LITB origin span',lambda s,l:l[16].__setitem__(0,1922))

def synthetic_reader(n):
 rows=[[1,1,1,1],[18,0,0,0],[9,1,0,0]];lab=1
 def label():
  nonlocal lab
  lab+=1;return lab
 def tree(lo,hi):
  if hi-lo==16:
   rows.extend([[4,0,1,0],[3,1,lo,0],[6,2,0,0],[21,0,1+lo//16,16]])
  else:
   mid=(lo+hi)//2;other=label();join=label()
   rows.extend([[4,0,1,0],[3,1,mid,0],[7,2,0,0],[11,0,other,0]])
   tree(lo,mid);rows.extend([[10,join,0,0],[9,other,0,0]])
   tree(mid,hi);rows.append([9,join,0,0])
 tree(0,n);rows.extend([[19,0,0,0],[2,1,0,0]])
 return {j+1:r for j,r in enumerate(rows)}
length_models=[]
for n in [32,64,128,256]:
 s=synthetic_reader(n);ls={k:v for k,v in lits.items() if k<=n//16}
 assert len(s)<=258 and validate(s,ls,n)
 vals=[path(s,x) for x in range(n)]
 assert all(a['fuel']==1 and a['reads']==[[1+x//16,x%16]] for x,a in enumerate(vals))
 length_models.append({'n':n,'mask':n-1,'sourceRows':len(s),'finitePaths':n,
                       'allExactlyOneChargeAndRead':True,'syntheticSourceData':True,'native':False})

def bounded_caller(s):
 if s[220]!=[13,1,0,1] or s[221][0] in [19,25]:return False
 return s[216]==[3,1,255,0] and s[217]==[6,5,0,0] and s[218]==[5,7,0,0] and s[219]==[4,0,7,0]
assert bounded_caller(sir)
caller_faults=[]
for name,row,replacement in [
 ('CALL/RES2 result dependency',221,[25,0,0,0]),
 ('tail CALL/RET lifetime',221,[19,0,0,0]),
 ('unknown caller mask history',216,[3,1,254,0]),
 ('caller local reassignment',218,[5,8,0,0]),
 ('control target inside mask suffix',219,[9,51,0,0]),
 ('multiple arguments',220,[13,1,0,2])]:
 s=copy.deepcopy(sir);s[row]=replacement
 assert not bounded_caller(s)
 caller_faults.append({'fault':name,'admitted':False,'modelOnly':True})

# Source ordering checks only. These checks detect source omissions;
# they are not actual generated-code or runtime fault detection.
fragment=(W/'candidate-fragment.kotoba').read_text()
def source_order(s):
 start=s.index('(defn- tc-call');s=s[start:]
 required=['(di-save M 0 0)','(gn-save 0 t)','(gn-into 0 t)','(gn-ctx)',
           '(gn-mask-charge)','(gn-e-ldrr 0 17 16 0)',
           '(enc-str 8 7 CTX-FUEL)','(gn-vclear)','(gn-ctx-safe M f 1 8 512)',
           '(gn-take i t 0)']
 try:pos=[s.index(x) for x in required]
 except ValueError:return False
 return pos==sorted(pos)
assert source_order(fragment)
source_faults=[]
for name,needle in [('omit live-prefix save','(gn-save 0 t)'),
                    ('omit descriptor cache clear','(gn-vclear)'),
                    ('omit original context analysis','(gn-ctx-safe M f 1 8 512)')]:
 assert not source_order(fragment.replace(needle,'',1))
 source_faults.append({'fault':name,'sourceContractDetected':True,'nativeFaultDetected':False})

# Pure descriptor transaction model: canonical REG temps are x9+k, not x0.
# V1 absence of save is a difference from original call homes/descriptors;
# this model does not claim V1 empirically clobbered a register.
prefix_controls=[]
for height in [0,1,3,6]:
 before=[{'kind':'reg' if k%2==0 else 'local','value':100+k} for k in range(height)]
 original=copy.deepcopy(before);replacement=copy.deepcopy(before);homes={}
 for k,d in enumerate(original):
  if d['kind']=='reg':homes[k]=d['value'];d['kind']='home'
 for d in replacement:
  if d['kind']=='reg':d['kind']='home'
 assert replacement==original
 prefix_controls.append({'livePrefixHeight':height,'descriptorAgreement':True,
                         'nativeRegisterObservation':False,'saveHomes':homes})
near_fuel=[]
for initial in [0,1,2,3]:
 original={'trap':initial==0,'remaining':max(0,initial-1),'read':initial>0}
 replacement={'trap':initial==0,'remaining':max(0,initial-1),'read':initial>0}
 assert original==replacement
 near_fuel.append({'initialFuel':initial,'original':original,'replacement':replacement,'modelOnly':True})

# Existing di snapshot field map covers scalar0..15, sreg0..7 and dk/dv0..6.
fields=list(range(16))+list(range(8))+list(range(7))+list(range(7))
assert len(fields)==38
before=list(range(38));snapshot=before.copy();after=[-1]*38
after[:]=snapshot
assert after==before

# Layout42 invariant: each existing128-byte literal begins at aligned8;
# literal order has no dedup/interposed record here. LF-B identity is not
# used as a substitute for physical LF-POOL order; this is layout source law.
pos=0;pool=[]
for lit in range(1,17):
 pool.append(pos);pos=(pos+lits[lit][1]+7)&-8
assert pool==[128*k for k in range(16)] and pos==2048
badpool=pool.copy();badpool[1]+=8
assert any(badpool[x//16]+8*(x%16)!=8*x for x in range(256))
layout_fault={'fault':'physical pool interposed gap','finiteAddressMismatch':True,
              'changedLayoutProducerWouldRequireNewProof':True,'nativeFaultDetected':False}
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
out={'status':'SOURCE V2 HOLD pending root and independent review; finite source-data checks completed',
 'sourceMatchesHistoricalObserver':True,'historicalProducerMatchesCurrent41Proved':False,
 'reader':{'fn':1,'sirStart':1,'sirEnd':174,'entryFuel':2,'otherFuel':[],
   'pathCount':256,'allExactlyOneCharge':True,'allExactlyOneCheckedRead':True,
   'literalIds':list(range(1,17)),'literalBytes':128,'wholeLookupBytes':2048},
 'caller':{'fn':3,'callSir':220,'boundedSuffixSir':[216,217,218,219],'indexDomain':[0,255]},
 'mutantControls':faults,'callerFaults':caller_faults,'sourceOrderingFaults':source_faults,
 'finiteLengthModels':length_models,'layoutAddressFault':layout_fault,
 'prefixDescriptorModels':prefix_controls,'nearFuelModels':near_fuel,
 'snapshot38Model':{'restored':True,'actualKotobaExecuted':False},
 'paths':paths,'poolRelativeOffsets':pool,
 'pins':[pin(src),pin(R/'seed/41-a64gen.kotoba'),pin(R/'seed/42-layout.kotoba'),
   pin(O/'ports/crc32/observer-records.json'),pin(W/'candidate-fragment.kotoba'),
   pin(W/'41-a64gen-candidate.kotoba')],
 'execution':{'compiler':0,'native':0,'ssh':0,'solver':0,'cpuProbe':0,'timing':0}}
(W/'source-data-controls.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','reader','caller','mutantControls','execution']},indent=2))
