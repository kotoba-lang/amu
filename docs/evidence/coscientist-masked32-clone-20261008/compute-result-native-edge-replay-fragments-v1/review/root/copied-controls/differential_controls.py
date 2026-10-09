"""Finite arithmetic/identity model only. No native or operational imports."""
import itertools,json,hashlib
from pathlib import Path
D=Path(__file__).parent
meet=lambda a,b: b if a==-1 else a if b==-1 else min(a,b)
def baseline(start,visits):
 out=list(start)
 for e,k,L,preserves,pos in visits:
  if pos and not preserves:out[k]=meet(out[k],L)
 return out
def capture(visits,edges):
 cells=[[-1]*4 for _ in range(edges)]
 for e,k,L,preserves,pos in visits:
  if pos and not preserves:cells[e][k]=meet(cells[e][k],L)
 return cells
def replay(start,cells):
 out=list(start)
 for e in cells:
  for k,L in enumerate(e):out[k]=meet(out[k],L)
 return out
checks=0
for a,b,c in itertools.product([-1,0,1,2,7],repeat=3):
 assert meet(meet(a,b),c)==meet(a,meet(b,c));assert meet(a,b)==meet(b,a);assert meet(a,a)==a;checks+=1
for vals in itertools.product([-1,0,1,2],repeat=4):
 for old in [-1,0,1,5]:
  start=[old]*4
  visits=[(e,k,L,False,True)for e in range(2)for k,L in enumerate(vals)]
  # Earlier optimistic/provisional contribution must survive even final larger.
  visits.extend([(0,0,0,False,True),(0,0,7,False,True),(1,1,0,True,True),(1,2,0,False,False)])
  assert replay(start,capture(visits,2))==baseline(start,visits);checks+=1
# Poison always executed on unsupported caller each round, never cached-away.
poison=lambda start:[0]*4
assert poison(replay([-1]*4,[[-1]*4]))==[0]*4
assert baseline([5]*4,[(0,0,0,True,True)])==[5]*4
assert baseline([5]*4,[(0,0,0,False,False)])==[5]*4
assert baseline([5]*4,[(0,0,0,False,True)])==[0,5,5,5]
# Differential cycles: snapshot/read inputs and meet rounds remain same; no
# downstream stop until whole owned contribution equality, then boundsFinish.
def rounds(cached):
 state=[4,3];memo={};hits=0;history=[]
 for _ in range(12):
  old=tuple(state);acc=[-1,-1]
  for f in range(2):
   key=(f,old[f]);L=max(0,old[f]-1)
   if cached and key in memo:answer=memo[key];hits+=1
   else:answer=L;memo[key]=answer
   acc[1-f]=meet(acc[1-f],answer)
  state=[max(0,x)for x in acc];history.append(tuple(state))
  if tuple(state)==old:return history,hits
 raise AssertionError('bounded convergence')
assert rounds(False)[0]==rounds(True)[0]
fields=['moduleBytes','SIR','FREC','caller','mode','candidate','entry4','aliasAndReturnAndLifetime','paramPositions','edgeOrderAndTargets','ruleAndABI','effectTrapContract','budgetContract','supported','poison']
key={n:('stable',n)for n in fields};key['entry4']=(1,2,3,4)
keyhash=lambda q:hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':')).encode()).hexdigest()
req=keyhash(key);refusals=[]
for n in fields:
 changed=dict(key);changed[n]='mutated';assert keyhash(changed)!=req;refusals.append('invalidate:'+n)
# Publish valid last; invalidation precedes partial clear/key write. Model all
# stop boundaries: none may expose previous valid result under fresh key.
for stop in range(7):
 valid=0;stored={};complete=False
 for k in range(4):
  if stop==k:break
  stored[k]=key['entry4'][k]
 else:
  complete=stop>4
  if complete:valid=1
 assert not valid or (len(stored)==4 and complete)
 
 if stop<=4:refusals.append('partial-publication:'+str(stop))
answer={'scope':'mode1-edge-contributions/v1','complete':True,'supported':True,'poison':False,'edges':[[0,-1,2,3],[-1,0,-1,1]]}
ans=keyhash(answer)
# changed request with same result only stops pure owned-answer consumers;
# no current authorization, budget, or transition receipt inferred from digest.
changed=dict(key);changed['moduleBytes']='different-equivalent-body';assert keyhash(changed)!=req and keyhash(dict(answer))==ans
for n in ['complete','supported','poison','scope','edges']:
 q=dict(answer);q[n]='changed';assert keyhash(q)!=ans;refusals.append('result-change:'+n)
# Explicit broken implementations caught by concrete witnesses.
v=[(0,0,0,False,True),(0,0,7,False,True)]
assert baseline([5]*4,v)[0]==0 and 7!=0;refusals.append('drop-provisional-zero')
assert replay([0]*4,[[7,-1,-1,-1]])[0]==0 and 7!=0;refusals.append('overwrite-target-total')
assert replay([5]*4,[[-1]*4])==[5]*4 and [0]*4!=[5]*4;refusals.append('neutral-confused-with-zero')
# Current gn-ctx-safe exact integer answer includes remaining work; recursive
# calls cannot share top-level Boolean cache across different work/depth/open.
ctx={'module':'fixed','f':3,'n':1,'depth':8,'work':512,'openFirst':0,'openCount':0}
for n in ['module','f','n','depth','work','openFirst','openCount']:
 q=dict(ctx);q[n]='changed';assert keyhash(q)!=keyhash(ctx);refusals.append('ctx-key:'+n)
q={'status':'PASS_FINITE_SOURCE_DIFFERENTIAL_MODEL_ONLY','arithmeticAndContributionChecks':checks,'cycleHistory':rounds(True)[0],'cycleMemoHits':rounds(True)[1],'refusals':refusals,'requestDigestModel':'canonical-JSON SHA256, not native/IPLD CID implementation','operationalCalls':0,'nativeQualified':False}
print(json.dumps(q,indent=2))
if __name__=='__main__':(D/'controls.json').write_text(json.dumps(q,indent=2)+'\n')
