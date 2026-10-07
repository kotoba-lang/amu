from pathlib import Path
import json,hashlib,collections,copy
from domain import audit
P=Path('/private/tmp/amu-aes-resident-fuel-20261007');D=Path(__file__).parent;O=P/'team-inverse-native-images/continuation/observer/ports'
M=(1<<64)-1;S=1<<63
SC=lambda a,b=None:('s',a,a if b is None else b)
V=lambda origin,l,anchor=True:('v',origin,'entry',l,anchor)
def mergefact(a,b):
 if a==b:return a
 if not a or not b or a[0]!=b[0]:return None
 if a[0]=='s':return SC(min(a[1],b[1]),max(a[2],b[2]))
 if a[1:3]==b[1:3]:return ('v',a[1],a[2],min(a[3],b[3]),a[4]or b[4])
 return None
def merge(a,b):
 return {k:v for k in a.keys()&b.keys() if (v:=mergefact(a[k],b[k]))is not None}
def tarjan(graph):
 ix={};lo={};st=[];active=set();groups=[]
 def visit(f):
  ix[f]=lo[f]=len(ix);st.append(f);active.add(f)
  for g in graph[f]:
   if g not in ix:visit(g);lo[f]=min(lo[f],lo[g])
   elif g in active:lo[f]=min(lo[f],ix[g])
  if lo[f]==ix[f]:
   comp=[]
   while True:
    g=st.pop();active.remove(g);comp.append(g)
    if g==f:break
   groups.append(comp)
 for f in graph:
  if f not in ix:visit(f)
 return groups
class Module:
 def __init__(self,records):
  self.sir={x['fields'][0]:tuple(x['fields'][1:])for x in records if x['tag']=='SIR'};self.ff={x['fields'][0]:x['fields'][1:]for x in records if x['tag']=='FREC'};self.cache={x['fields'][0]:x['fields'][1]for x in records if x['tag']=='CACHE'};self.fn={};self.owner={};self.edges=[];self.invalid={};self.steps=0
  f=None
  for i,row in sorted(self.sir.items()):
   op,a,b,c=row
   if op==1:f=a;self.fn[f]=[]
   if f is not None:self.fn[f].append(i);self.owner[i]=f
   if op==2:f=None
  self.graph={f:set()for f in self.fn};self.labels={}
  for f,ids in self.fn.items():
   labs={};bad=[]
   for i in ids:
    op,a,b,c=self.sir[i]
    if op==9:
     if a in labs:bad.append('duplicate-label')
     labs[a]=i
    if op==13:
     if a not in self.fn:bad.append('unknown-direct-target')
     else:self.graph[f].add(a);self.edges.append((f,i,a,b,c))
   self.labels[f]=labs
   for i in ids:
    op,a,b,c=self.sir[i];target=a if op==10 else b if op in[11,12]else None
    if target is not None and target not in labs:bad.append('unknown-owned-label')
   if len(ids)>8192:bad.append('body-budget')
   if any(self.sir[i][0]in[25,26]for i in ids):bad.append('unsupported-dual-result')
   if any(self.sir[i][0]not in range(1,27)for i in ids):bad.append('unsupported-opcode')
   if any(self.sir[i][0]==13 and (self.sir[i][2]<0 or self.sir[i][3]<0 or self.sir[i][1]not in self.ff or self.sir[i][3]!=self.ff[self.sir[i][1]][3])for i in ids):bad.append('malformed-call-shape')
   if any(self.sir[i][0]==14 and self.sir[i][1] in {72:1,144:2,168:1,176:2,208:3,200:1} and self.sir[i][3]!={72:1,144:2,168:1,176:2,208:3,200:1}[self.sir[i][1]] for i in ids):bad.append('malformed-known-runtime-arity')
   if f not in self.ff:bad.append('missing-FREC')
   elif sum(self.ff[f][5+k]==4 for k in range(min(self.ff[f][3],5)))>4:bad.append('four-vector-summary-budget')
   if bad:self.invalid[f]=sorted(set(bad))
  self.groups=tarjan(self.graph);self.group={f:idx for idx,g in enumerate(self.groups)for f in g}
  self.clean={f:f not in self.invalid for f in self.fn};self.cleanReasons={}
  for f,ids in self.fn.items():
   bad=[]
   for i in ids:
    op,a,b,c=self.sir[i]
    if op in [15,23]:bad.append('capability-or-indirect-call')
    if op==14 and a not in [72,144,168,176,208,200]:bad.append('unproved-runtime-epoch-slot:'+str(a))
    if op==14 and a in {72:1,144:2,168:1,176:2,208:3,200:1} and c!={72:1,144:2,168:1,176:2,208:3,200:1}[a]:bad.append('unproved-runtime-contract-arity')
   if bad:self.clean[f]=False;self.cleanReasons[f]=sorted(set(bad))
  changed=True
  while changed:
   changed=False
   for f in self.fn:
    if self.clean[f] and any(not self.clean[g]for g in self.graph[f]):self.clean[f]=False;self.cleanReasons[f]=['transitive-unproved-epoch'];changed=True
  self.addressed={b for op,a,b,c in self.sir.values()if op==22}
  self.roots={f for f in self.fn if self.ff[f][2]!=2 or self.ff[f][11]!=0}|self.addressed
  self.reachable=set();todo=list(self.roots)
  while todo:
   f=todo.pop()
   if f in self.reachable:continue
   self.reachable.add(f);todo.extend(self.graph.get(f,set()))
  self.closedGraph=not self.invalid and all(op not in [15,23] for op,a,b,c in self.sir.values()) and self.addressed<=self.fn.keys()
  if not self.closedGraph:self.reachable=set(self.fn)
  self.alias={};self.retLen={};self.bounds={f:{k:0 for k in self.vecparams(f)}for f in self.fn}
 def vecparams(self,f):
  z=self.ff[f];return [k+1 for k in range(min(z[3],5))if z[5+k]==4][:4]
 def run(self,f,bounds=None,assumeSelfAlias=None,proof=False):
  ids=self.fn[f];entry=ids[0];incoming={entry:{('l',k):V(('param',k),(bounds or{}).get(k,0))for k in self.vecparams(f)}};queue=collections.deque([entry]);returns={};calls={};reads={};baseRets=set(); visits=0
  while queue:
   i=queue.popleft();state=dict(incoming[i]);op,a,b,c=self.sir[i];n=i+1;succ=[];visits+=1;self.steps+=1
   if self.steps>262144:raise RuntimeError('module-work-budget')
   def get(t):return state.get(('t',t))
   def put(t,v):
    if v is None:state.pop(('t',t),None)
    else:state[('t',t)]=v
   def kill():
    for k,v in list(state.items()):
     if v[0]=='v':state.pop(k,None)
   if op==3:put(a,SC(b))
   elif op==4:put(a,state.get(('l',b)))
   elif op==5:
    v=get(b)
    if v is None:state.pop(('l',a),None)
    else:state[('l',a)]=v
   elif op==6:
    x=get(b);y=get(b+1);val=None
    if x and y and x[0]==y[0]=='s':
     lo,hi=x[1:];l,h=y[1:]
     if a==1:q=(lo+l,hi+h)
     elif a==2:q=(lo-h,hi-l)
     elif a==3:q=(min(lo*l,lo*h,hi*l,hi*h),max(lo*l,lo*h,hi*l,hi*h))
     else:q=None
     if q and -S<=q[0]<=q[1]<S:val=SC(*q)
    put(b,val)
   elif op in[7,8]:put(b,None)
   elif op in[17,24]:put(a,V(('allocation',i),b if op==17 else c))
   elif op==13:
    args=[get(b+k)for k in range(c)];calls[i]=(a,args)
    alias=self.alias.get(a)
    selfassume=a==f and assumeSelfAlias is not None
    if selfassume:alias=assumeSelfAlias
    val=args[alias-1]if alias and alias<=len(args)else None
    if val and val[0]=='v'and selfassume:val=(*val[:4],False)
    if not self.clean.get(a,False):kill();val=None
    if val is None and self.clean.get(a,False)and self.retLen.get(a,0)>0:val=V(('returned-allocation',i),self.retLen[a])
    put(b,val)
   elif op==14:
    args=[get(b+k)for k in range(c)]
    if a==200:
     z=args[0]if args else None;put(b,V(('allocation',i),z[1])if z and z[0]=='s'and 0<=z[1]<=z[2]<S else None)
    elif a==208:put(b,args[0]if args else None)
    elif a==168:put(b,None)
    elif a==176:
     h=args[0]if args else None;k=args[1]if len(args)>1 else None;reads[i]=(h,k);put(b,None)
    elif a in[72,144]:put(b,None)
    else:kill();put(b,None)
   elif op==15:kill();put(c,None)
   elif op==23:kill();put(b,None)
   elif op==19:
    val=get(a);returns[i]=val
    if val and val[0]=='v'and val[4]:baseRets.add(i)
   elif op in[16,21,22,25]:put(a,None)
   if op==10:succ=[self.labels[f].get(a)]
   elif op in[11,12]:succ=[n,self.labels[f].get(b)]
   elif op not in[2,19,20,26]:succ=[n]
   for j in succ:
    if j is None or self.owner.get(j)!=f:continue
    if j not in incoming:incoming[j]=dict(state);queue.append(j)
    else:
     edgeState=state
     if j<=i:
      edgeState={k:v for k,v in state.items()if not(v[0]=='s'and incoming[j].get(k)!=v)}
     m=merge(incoming[j],edgeState)
     if m!=incoming[j]:incoming[j]=m;queue.append(j)
   if visits>65536:raise RuntimeError('function-work-budget')
  return {'returns':returns,'calls':calls,'reads':reads,'baseRets':baseRets,'states':incoming}
 def globally_refuse(self,reason,aliasConverged):
  # Prospective V6: no partially positive facts survive any nonconvergence.
  self.alias={};self.retLen={};self.bounds={f:{k:0 for k in self.vecparams(f)}for f in self.fn}
  reads=[{'sir':i,'fn':f,'handleFact':None,'indexFact':None,'generatorMode':self.cache.get(i),
          'admittedReference':False,'reasons':[reason],'CMPKept':True,'handleValidationKept':True,
          'preciseNFElementTypeCertificate':False,'typedEmitterQualification':False}
         for f,ids in self.fn.items()for i in ids if self.sir[i][0]==14 and self.sir[i][1]==176]
  return {'summaries':{'lifetimeClean':self.clean,'lifetimeRefusals':self.cleanReasons,
          'returnAlias':{},'returnMinLength':{},'parameterLowerBounds':self.bounds,
          'invalidFunctions':self.invalid,'closedGraph':self.closedGraph,
          'publicAddressedRoots':sorted(self.roots),'reachableFunctions':sorted(self.reachable),
          'FADDRTargets':sorted(self.addressed),'allDeclaredDirectEdges':self.edges,
          'rootedBoundsConverged':False,'aliasSummariesConverged':aliasConverged,
          'globalRefusal':reason},'reads':reads,'transferSteps':self.steps}
 def solve(self):
  # Self-recursive alias hypothesis is checked against every normal RET and a direct base return.
  aliasConverged=False
  for _ in range(8):
   changed=False
   for f in self.fn:
    if not self.clean[f]or f in self.invalid or len(self.groups[self.group[f]])!=1:continue
    for k in self.vecparams(f):
     q=self.run(f,assumeSelfAlias=k);rets=list(q['returns'].values())
     if rets and q['baseRets'] and all(v and v[0]=='v'and v[1]==('param',k)for v in rets):
      if self.alias.get(f)!=k:self.alias[f]=k;changed=True
      break
    q=self.run(f);rets=list(q['returns'].values());L=min((v[3]if v and v[0]=='v'else 0 for v in rets),default=0)
    if L>self.retLen.get(f,0):self.retLen[f]=L;changed=True
   if not changed:aliasConverged=True;break
  if not aliasConverged:return self.globally_refuse('global-alias-summary-nonconvergence',False)
  # Caller-before-callee condensation traversal; no global depth iteration cap.
  converged=True;runCache={}
  for group in reversed(self.groups):
   if len(group)!=1:
    for f in group:runCache[f]=self.run(f,self.bounds[f]) if f not in self.invalid else {'calls':{},'reads':{}}
    continue
   f=group[0]
   if f in self.invalid:continue
   if f not in self.reachable or f in self.addressed or self.ff[f][2]!=2 or self.ff[f][11]!=0:
    self.bounds[f]={k:0 for k in self.vecparams(f)}
   else:
    external=[]
    for caller,site,target,argbase,arity in self.edges:
     if target!=f or caller==f:continue
     if caller not in self.reachable:continue
     if caller in self.invalid or caller not in runCache:external.append([None]*arity)
     elif site in runCache[caller]['calls']:external.append(runCache[caller]['calls'][site][1])
     # A declared edge absent from a VALID complete CFG traversal is structurally unreachable, recorded below.
    trial={k:min((args[k-1][3]if len(args)>=k and args[k-1]and args[k-1][0]=='v'else 0 for args in external),default=0)for k in self.vecparams(f)}
    stable=False
    for _ in range(8):
     q=self.run(f,trial);nextBounds=dict(trial)
     for k,L in trial.items():
      if L and any(target==f and (len(args)<k or not args[k-1]or args[k-1][0]!='v'or args[k-1][3]<L)for target,args in q['calls'].values()):nextBounds[k]=0
     if nextBounds==trial:stable=True;break
     trial=nextBounds
    self.bounds[f]=trial if stable else {k:0 for k in self.vecparams(f)}
    if not stable:converged=False
   runCache[f]=self.run(f,self.bounds[f])
  if not converged:return self.globally_refuse('global-rooted-bound-nonconvergence',True)
  # Every incoming edge receives the final value/epoch transfer, including self.
  for f in self.fn:
   for k,L in self.bounds[f].items():
    if not L:continue
    incoming=[args for caller,q in runCache.items()if caller in self.reachable for target,args in q['calls'].values()if target==f]
    assert incoming and all(len(args)>=k and args[k-1]and args[k-1][0]=='v'and args[k-1][3]>=L for args in incoming),('allcaller-invariant',f,k,L)
  self.output=[]
  for f,ids in self.fn.items():
   if f in self.invalid:q={'reads':{i:(None,None)for i in ids if self.sir[i][0]==14 and self.sir[i][1]==176}}
   else:q=self.run(f,self.bounds[f])
   leaders={ids[0]}
   for j in ids:
    op,a,b,c=self.sir[j]
    if op in[10,11,12]:
     target=self.labels[f].get(a if op==10 else b)
     if target is not None:leaders.add(target)
    if op in[10,11,12,19,20,26]and j+1 in ids:leaders.add(j+1)
   blocks=len(leaders)
   for i,(h,k)in q['reads'].items():
    reasons=[]
    if f not in self.reachable:reasons.append('certified-unreachable-private-body')
    if not self.clean[f]:reasons.append('unproved-lifetime-closure')
    if f in self.invalid:reasons.append('invalid-or-unsupported-function')
    if not h or h[0]!='v'or h[3]<=0:reasons.append('no-positive-allcaller-or-origin-length')
    if not k or k[0]!='s'or k[1]!=k[2]or k[1]<0:reasons.append('not-nonnegative-constant-index')
    elif h and h[0]=='v'and not k[1]<h[3]:reasons.append('index-not-proved-below-length')
    if self.sir[i][3]!=2:reasons.append('RT176-not-two-argument-read')
    if self.cache.get(i)!=0:reasons.append('unsupported-generator-cache-mode')
    if self.sir[i][2]>5:reasons.append('unsupported-high-temp')
    if blocks>8:reasons.append('CFG-eight-block-budget')
    if len(self.fn)>128 or len(self.edges)>512:reasons.append('module-table-budget')
    self.output.append({'sir':i,'fn':f,'handleFact':h,'indexFact':k,'generatorMode':self.cache.get(i),'admittedReference':not reasons,'reasons':reasons,'CMPKept':True,'handleValidationKept':True,'preciseNFElementTypeCertificate':False,'typedEmitterQualification':False})
  return {'summaries':{'lifetimeClean':self.clean,'lifetimeRefusals':self.cleanReasons,'returnAlias':self.alias,'returnMinLength':self.retLen,'parameterLowerBounds':self.bounds,'invalidFunctions':self.invalid,'closedGraph':self.closedGraph,'publicAddressedRoots':sorted(self.roots),'reachableFunctions':sorted(self.reachable),'certifiedUnreachableCallerEdges':[list(e)for e in self.edges if e[0]not in self.reachable],'FADDRTargets':sorted(self.addressed),'allDeclaredDirectEdges':self.edges,'structurallyUnreachableCallEdges':[list(e)for e in self.edges if e[0]in runCache and e[1]not in runCache[e[0]]['calls']],'baseAnchorMeaning':'MAY syntactic nonself-assumption path with MUST exact returnedparameter identity/epoch; not termination proof','rootedBoundsConverged':converged,'aliasSummariesConverged':aliasConverged},'reads':self.output,'transferSteps':self.steps}
if __name__=='__main__':
 rows=[];pins={}
 for d in sorted(O.iterdir()):
  if not d.is_dir():continue
  p=d/'observer-records.json';raw=p.read_bytes();pins[str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};mod=Module(json.loads(raw))
  try:
   domain=audit(json.loads(raw))
   if domain['errors']:r={'status':'REFUSED whole-module indexed-domain','domain':domain,'reads':[],'summaries':{},'transferSteps':0}
   else:r=mod.solve();r['status']='completed conservative reference';r['domain']=domain
  except (RuntimeError,KeyError,IndexError)as e:r={'status':'REFUSED setup/budget','error':repr(e),'reads':[],'summaries':{},'transferSteps':mod.steps}
  r['workload']=d.name;r['admittedCount']=sum(x['admittedReference']for x in r['reads']);rows.append(r);print(d.name,r['status'],r['admittedCount'],r['transferSteps'],flush=True)
 (D/'reference-results.json').write_text(json.dumps(rows,indent=2)+'\n');(D/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
