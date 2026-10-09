import copy,json,hashlib
from pathlib import Path
from analyze import Module
D=Path(__file__).parent
# Fixed diagnostic SIR only; not native fixtures or source-to-SIR certificates.
def records(bodies):
 out=[];i=1
 for f,np,private,ops in bodies:
  start=i;out.append({'tag':'SIR','fields':[i,1,f,np,4]});i+=1
  for op,a,b,c in ops:out.append({'tag':'SIR','fields':[i,op,a,b,c]});i+=1
  out.append({'tag':'SIR','fields':[i,2,f,0,0]});i+=1
  ff=[0]*16;ff[2]=2 if private else 1;ff[3]=np;ff[5]=4 if np else 0;ff[10]=4;ff[11]=0 if private else 1;ff[12]=start;ff[15]=4
  out.append({'tag':'FREC','fields':[f,*ff]})
 for x in list(out):
  if x['tag']=='SIR' and x['fields'][1:3]==[14,176]:out.append({'tag':'CACHE','fields':[x['fields'][0],0,0,0,0]})
 return out
root=[(3,0,4,0),(14,200,0,1),(13,2,0,1),(19,0,0,0)]
helper=[(4,0,1,0),(3,1,2,0),(14,176,0,2),(19,0,0,0)]
base=[(1,0,False,root),(2,1,True,helper)]
def result(b):return Module(records(b)).solve()
def count(r):return sum(x['admittedReference'] for x in r['reads'])
assert count(result(base))==1
controls=[]
def reject(name,b):
 r=result(b);n=count(r);assert n==0,(name,n)
 controls.append({'name':name,'expectedAdmitted':0,'actualAdmitted':n,'detected':True,'records':records(b),'summaries':r['summaries']})
b=copy.deepcopy(base);b[0][3][0]=(3,0,1,0);reject('short-normal-allocation',b)
b=copy.deepcopy(base);b[0][3].insert(2,(14,232,2,0));reject('epoch-reset-before-call',b)
b=copy.deepcopy(base);b[0][3].insert(2,(14,184,0,1));reject('ordinary-assoc-not-alias',b)
b=copy.deepcopy(base);b[0][3].insert(2,(22,3,2,0));reject('FADDR-b-target-is-external-root',b)
b=copy.deepcopy(base);b[1][3][-1]=(26,0,0,0);reject('RET2-refuses-all-normal-return-closure',b)
b=copy.deepcopy(base);b.append((3,1,False,[(4,0,1,0),(13,2,0,1),(19,0,0,0)]));reject('complete-unknown-incoming-caller-poisons',b)
b=copy.deepcopy(base);b.append((3,1,True,[(9,1,0,0),(9,1,0,0),(13,2,0,1),(19,0,0,0)]));reject('invalid-unreachable-caller-disables-exclusion-and-poisons',b)
# CAP wire/kind/temp: stale scalar destination must be removed, kind must not be mistaken for temp.
b=[(1,0,False,[(3,2,2,0),(15,40,1,2),(19,2,0,0)])]
m=Module(records(b));z=m.run(1);assert all(v is None for v in z['returns'].values());controls.append({'name':'CAP-clears-c-not-kind-b','detected':True,'records':records(b)})
# Hash-bound deletion cannot masquerade as a complete original incoming graph.
r=records(base);h=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest();mut=[x for x in r if not(x['tag']=='SIR' and x['fields'][1]==13)];assert hashlib.sha256(json.dumps(mut,sort_keys=True).encode()).hexdigest()!=h
controls.append({'name':'removed-caller-input-rejected-by-origin-binding','detected':True,'scope':'transport/origin integrity, not independent semantic recovery from missing SIR'})
# Normal return alias is distinct from length; every RET must preserve identity.
a=copy.deepcopy(base);a[0][3].insert(2,(13,3,0,1));a.append((3,1,True,[(4,0,1,0),(19,0,0,0)]));assert count(result(a))==1
b=copy.deepcopy(a);b[-1][3][-1]=(19,1,0,0);reject('return-identity-changed',b)
b=copy.deepcopy(a);b[-1][3][:]=[(4,0,1,0),(13,3,0,1),(19,0,0,0)];reject('recursive-return-no-base-anchor',b)
b=copy.deepcopy(base);b[0][3].insert(2,(13,3,0,1))
for f in range(3,13):b.append((f,1,True,[(4,0,1,0)]+([(13,f+1,0,1)]if f<12 else [])+[(19,0,0,0)]))
r=result(b);assert not r['summaries']['aliasSummariesConverged'] and not r['summaries']['returnAlias'] and not r['summaries']['returnMinLength'];assert count(r)==0
controls.append({'name':'eight-pass-alias-nonconvergence-clears-positive-summaries','detected':True,'records':records(b),'summaries':r['summaries']})
b=copy.deepcopy(base);b[0][3].insert(2,(14,208,0,1));reject('malformed-inplace-arity-not-alias',b)
# Independent preregistered mixed14th: unrelated exhaustion must poison whole module.
b=copy.deepcopy(base)
for f in range(3,13):b.append((f,1,True,[(4,0,1,0)]+([(13,f+1,0,1)]if f<12 else [])+[(19,0,0,0)]))
r=result(b);assert not r['summaries']['aliasSummariesConverged'];assert count(r)==0
assert not r['summaries']['returnAlias'] and not r['summaries']['returnMinLength']
assert not any(L for p in r['summaries']['parameterLowerBounds'].values()for L in p.values())
controls.append({'name':'mixed-independent-allocation-global-exhaustion','expectedAdmitted':0,'actualAdmitted':count(r),'detected':True,'records':records(b),'summaries':r['summaries']})
(D/'fault-controls.json').write_text(json.dumps({'scope':'fixed finite diagnostic model/domain controls; no native proof','baselineRecords':records(base),'baselineAdmitted':1,'controls':controls,'allDetected':True},indent=2)+'\n')
print('PASS',len(controls),'fixed controls')
