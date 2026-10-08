"""Finite saved-word structural association only. No native/process operations."""
from pathlib import Path
import json,struct,hashlib,stat,bisect
D=Path(__file__).resolve().parent;W=D.parent;A=W/'published-mode2-x8-vector-statemate6-source-v2-20261009'
def need(v,m):
 if not v:raise AssertionError(m)
def rec(p):
 s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink(),'regular saved byte owner');b=p.read_bytes();z=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable bytes');return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def sign(x,n):return x-(1<<n)if x&(1<<(n-1))else x
GEN=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0]
PUB=[0xf1000508,0x54000042,0xd4200000,0xf90004e8]
PRIVATE=[0xf1000508,0x54000062,0xf90004ff,0xd4200000]
def branch(w,pc):
 if w&0xfc000000 in (0x14000000,0x94000000):return {'kind':'bl'if w&0xfc000000==0x94000000 else'b','base':w&0xfc000000,'target':pc+4*sign(w&0x3ffffff,26)}
 if w&0xff000010==0x54000000:return {'kind':'bcond','base':w&~(0x7ffff<<5),'target':pc+4*sign((w>>5)&0x7ffff,19)}
 if w&0x7e000000==0x34000000:return {'kind':'cb','base':w&~(0x7ffff<<5),'target':pc+4*sign((w>>5)&0x7ffff,19)}
 return None

def normalize(raw):
 need(len(raw)%4==0,'aligned');words=list(struct.unpack('<'+'I'*(len(raw)//4),raw));ends=[i for i,w in enumerate(words)if w==0xd4200020];need(ends and ends[-1]==len(words)-1,'complete source OP-END sentinel coverage; no trailing literal region admitted')
 starts=[0]+[e+1 for e in ends[:-1]];need(len(starts)==len(ends),'regions');regions=[];mapping={};patterns=[]
 for rid,(lo,hi)in enumerate(zip(starts,ends)):
  tokens=[];i=lo;initial=[]
  while i<=hi:
   # Candidate entry-only LDRx8 is folded into following first published debit.
   if words[i]==0xf94004e8 and i-lo in (0,1)and words[i+1:i+5]==PUB:
    need(i-lo==0 or words[lo]==0xd2800005,'entry load after optional original MOVx5 only');initial.append(i*4);mapping[i*4]=(rid,len(tokens));i+=1;continue
   if words[i:i+5]==GEN:
    token={'kind':'published-fuel-charge'};n=5;patterns.append(dict(region=rid,pc=i*4,shape='generic-x16',words=[f'{w:08x}'for w in GEN]))
   elif words[i:i+4]==PUB:
    token={'kind':'published-fuel-charge'};n=4;patterns.append(dict(region=rid,pc=i*4,shape='published-x8',words=[f'{w:08x}'for w in PUB]))
   else:token={'kind':'word','word':f'{words[i]:08x}'};n=1
   for j in range(n):mapping[(i+j)*4]=(rid,len(tokens))
   tokens.append(dict(pc=i*4,span=n,token=token));i+=n
  regions.append(dict(ordinal=rid,start=lo*4,end=(hi+1)*4,tokens=tokens,entryInitializationLoads=initial))
 def location(pc):need(pc in mapping,'aligned in-known-region branch target');return list(mapping[pc])
 branches=[]
 for r in regions:
  for t in r['tokens']:
   if t['token']['kind']=='word':
    b=branch(int(t['token']['word'],16),t['pc'])
    if b:
     branches.append(dict(pc=t['pc'],region=r['ordinal'],**b,targetLocation=location(b['target'])));t['token']={'kind':'branch','branchKind':b['kind'],'base':f"{b['base']:08x}",'target':location(b['target'])}
  r['canonicalSHA256']=hashlib.sha256(json.dumps([t['token']for t in r['tokens']],sort_keys=True,separators=(',',':')).encode()).hexdigest()
 # Actual machine leaders are retained separately; association never compares absolute offsets.
 leaders={0}
 for b in branches:leaders.add(b['target']);leaders.add(b['pc']+4)
 for i,w in enumerate(words):
  if w&0xff000010==0x54000000 or w&0xfc000000 in (0x14000000,0x94000000)or w&0x7e000000==0x34000000 or w in (0xd65f03c0,0xd63f0200,0xd4200000,0xd4200020,0):
   if(i+1)*4<len(raw):leaders.add((i+1)*4)
 return dict(words=words,regions=regions,branches=branches,patterns=patterns,mapping=mapping,leaders=sorted(leaders),sourceAssumptions=['OP-END emits only BRK1 and functions keep common source/SIR order','no literal payload contains a BRK1 sentinel here; all branch locations fit associated regions'])

def paired(off,on,offExports,onExports):
 a=normalize(off);b=normalize(on);need(len(a['regions'])==len(b['regions']),'same OP-END region count')
 pairs=[]
 for x,y in zip(a['regions'],b['regions']):
  need(x['canonicalSHA256']==y['canonicalSHA256'],'non-fuel whole-word/branch logical CFG mismatch region'+str(x['ordinal']))
  pairs.append(dict(region=x['ordinal'],OFF=[x['start'],x['end']],ON=[y['start'],y['end']],deltaBytes=(y['end']-y['start'])-(x['end']-x['start']),canonicalSHA256=x['canonicalSHA256'],changed=off[x['start']:x['end']]!=on[y['start']:y['end']],ONentryInitializationLoads=y['entryInitializationLoads'],OFFfuel=[p for p in a['patterns']if p['region']==x['ordinal']],ONfuel=[p for p in b['patterns']if p['region']==y['ordinal']]))
 need([x[0]for x in offExports]==[x[0]for x in onExports]and all(x[2]==y[2]and a['mapping'][x[1]]==b['mapping'][y[1]]for x,y in zip(offExports,onExports)),'same logical export owner/arity')
 private=[]
 starts={r['start']:r for r in b['regions']}
 for br in b['branches']:
  t=br['target'];r=starts.get(t-4)
  if br['kind']=='b'and r and b['words'][r['start']//4]==0xd2800005:
   need(b['words'][t//4]==0xf94004e8,'private+1 still reloads x8');private.append(dict(pc=br['pc'],target=t,region=r['ordinal'],publicStart=r['start'],skippedWord='d2800005',landingWord='f94004e8',logicalTarget=br['targetLocation']))
 return dict(OFFbytes=len(off),ONbytes=len(on),deltaBytes=len(on)-len(off),regions=len(pairs),associatedByCommonSourceOrderAndFullNormalizedWordBranchEquality=True,changedRegions=sum(p['changed']for p in pairs),sizeChangedRegions=sum(p['deltaBytes']!=0 for p in pairs),pairs=pairs,OFFbasicBlockLeaders=a['leaders'],ONbasicBlockLeaders=b['leaders'],ONprivatePlus1Branches=private,exports={'OFF':offExports,'ON':onExports},unknownOpcodeCertificateQualified=False,fullGPRClobberCertificateQualified=False,sourceAssumptions=a['sourceAssumptions'])

def charge(words,value,context):
 # Exact finite actual debit words; local-x8/16 differs, observable context prefix compared.
 need(words in (GEN,PUB),'known exact published-debit words only')
 local=value;carry=local>=1;local=(local-1)&((1<<64)-1)
 if not carry:return dict(status='brk0',context=context,localUnderflow=local,published=False)
 return dict(status='continue',context=local,localUnderflow=None,published=True)
def main():
 import sys;sys.path.insert(0,str(A));from run import container
 terminal=json.loads((A/'run-outputs/terminal.json').read_bytes());need(terminal=={'loaderCalls':6,'allChildrenClosed':True,'failure':False},'closed actual6 first')
 arts=json.loads((A/'run-outputs/artifacts.json').read_bytes());proof=json.loads((W/'tc-current7618-off18-compile36-actual-review-independent-20261009/report.json').read_bytes());old=next(e for e in proof['joinedOriginal19Images']if e['workload']=='statemate')
 def artifact(a):
  nr=a['native'];kr=a['container'];need(rec(Path(nr['path']))==nr and rec(Path(kr['path']))==kr,'whole receipt');payload,exports=container(Path(kr['path']).read_bytes());need(payload==Path(nr['path']).read_bytes()and [list(e)for e in exports]==a['exports'],'payload own exports');return payload,[list(e)for e in exports]
 off,oe=artifact(arts[0]);on,ne=artifact(arts[1]);sn,se=artifact(arts[2]);so,soexp=artifact(old)
 vector=paired(off,on,oe,ne);statemate=paired(so,sn,soexp,se)
 need(vector['deltaBytes']==-8 and vector['regions']==5 and len(vector['ONprivatePlus1Branches'])==1,'actual vector multidebit/private witness')
 need(statemate['deltaBytes']==-1532,'actual original statemate code delta')
 controls=[]
 # Multiple debits from saved region shapes, not full non-fuel execution.
 for value in [0,1,2,3,4,6,7,(1<<64)-1]:
  ac=bc=value;al=value;bl=value;prefix=[]
  for j in range(2):
   x=charge(GEN,ac,ac);y=charge(PUB,bl,bc);need(x==y,'same saved debit prefix');prefix.append(x)
   if x['status']=='brk0':break
   ac=x['context'];bc=y['context'];bl=bc
  controls.append(dict(initial=value,debits=prefix))
 # Decisive negative: omit first publication or reload across the private transition.
 stale=charge(PUB,2,3);fresh=charge(PUB,3,3);need(stale!=fresh,'stale initial register changes charge');need(charge(PUB,1,1)['context']!=1,'omitted publication changes observed context')
 structuralMutants=[]
 for name,pc,word in [('skipped-private-entry-reload',196,0xd503201f),('wrong-published-store',228,0xf90004ff),('wrong-private-plus1-target',448,0x17ffffc0),('changed-nonfuel-value',236,0xd280008b)]:
  q=bytearray(on);q[pc:pc+4]=struct.pack('<I',word)
  try:paired(off,bytes(q),oe,ne)
  except AssertionError:structuralMutants.append(name)
  else:raise AssertionError('structural mutant admitted:'+name)
 out=dict(status='PASS_SAVED_FULLWORD_FUEL_NORMALIZED_STRUCTURAL_ASSOCIATION_WITH_MACHINE_SEMANTICS_HOLD',vector=vector,statemate=statemate,actualSavedChargeModelControls=controls,negativeModelControls=['stale-x8-initialization','omitted-published-counter'],structuralMutantsRefused=structuralMutants,actualNativeGuestCalls=0,fullMachineClobberCertificateQualified=False,actualTypedMode2AdmissionObserved=False,performanceQualified=False,HOLD=['complete opcode/operand register clobber classification','actual typed function/rule admission mapping','vector descriptor/context alias/lifetime and host allocation boundary proof','full vector non-fuel word interpreter/native semantic fuel/trap/17arena outcomes','common SIR order and no literal sentinel assumption not independently machine certified'])
 (D/'report.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(status=out['status'],vector={k:vector[k]for k in ['OFFbytes','ONbytes','deltaBytes','regions','changedRegions','ONprivatePlus1Branches']},statemate={k:statemate[k]for k in ['OFFbytes','ONbytes','deltaBytes','regions','changedRegions','sizeChangedRegions']}),indent=2))
if __name__=='__main__':main()
