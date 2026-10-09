"""Independent constructor/context oracle. Diagnostic only, never product execution."""
from pathlib import Path
from collections import deque,Counter
import importlib.util,json,hashlib
W=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('shape_oracle',W/'shape-oracle.py');shape=importlib.util.module_from_spec(sp);sp.loader.exec_module(shape);C=shape.C;O=shape.O

def wrapper(s,m,i,a,b,c):
 if s.get(i+1,(0,))[0]==O('RES2') or a not in m:return 0
 p=m[a][0]
 if p<1 or not 1<=c<=3 or s.get(p,(0,0,0))[:3]!=(O('FN'),a,c):return 0
 j=p+1
 if s[j][0]==O('FUEL'):j+=1
 while s[j][0]==O('LABEL'):j+=1
 for k in range(c):
  if s[j][:3]!=(O('LGET'),k,k+1):return 0
  j+=1
 rt=s[j][0]==O('RT');slot=s[j][1] if rt else 1;ret=j+1 if rt else j
 good=(s[ret][:2]==(O('RET'),0) and s[ret+1][0]==O('END'))
 if rt:good=good and s[j][2:]==(0,c) and ((slot==176 and c==2 and b<=5) or (slot==208 and c==3 and b<=4) or (slot in (64,72,168) and c==1))
 else:good=good and c==1
 return slot if good else 0

def inference(s,m,flags):
 labels={}
 for i,(op,a,b,c) in s.items():
  if op==O('LABEL'):labels[a]=i if a not in labels else -1
 contexts=[(f,-1) for f in sorted(m)];contextsSeen=set(contexts);calls=[];accesses=[];status=[]
 for f,length in contexts:
  p,np,ns,dp,rt,pt=m[f];end=next((j for j in range(p+1,min(max(s)+1,p+8193)) if s[j][0] in (O('FN'),O('END'))),0) if p>0 else 0
  if end and s[end]!=(O('END'),f,0,0):end=0
  if end:
   ns=max(ns,np,s[p][3],*( [b if op==O('LGET') else a if op==O('LSET') else 0 for op,a,b,c in (s[j] for j in range(p+1,end))] or [0]))
   needs=[]
   for op,a,b,c in (s[j] for j in range(p+1,end)):
    needs.append(a+1 if op in [O(x) for x in ['CONST','LGET','STR','RET','BRZ','BRNZ','TAB','FADDR','VECP','RES2']] else a+2 if op==O('RET2') else b+1 if op in (O('LSET'),O('UN')) else b+2 if op in (O('BIN'),O('CMP')) else c+1 if op==O('CAP') else b+max(c,1) if op in (O('CALL'),O('RT')) else b+c+1 if op==O('CALLI') else a+max(b,1) if op==O('VEC') else 0)
   dp=max(dp,*needs)
  else:ns=dp=0
  if not(p>0 and end>p and 0<=np<=16 and np<=ns<=16 and 0<dp<=16):status.append(('LENGTH-SKIP',f,length,p,ns,dp));continue
  entry=[None]*32
  if length>=0 and np>0 and pt==4:entry[0]=('V',length)
  incoming={p+1:tuple(entry)};queue=deque([p+1]);bad=False;pops=0
  def merge(j,state):
   nonlocal bad
   if not p<j<=end:bad=True;return
   old=incoming.get(j);new=state if old is None else tuple(a if a==b else None for a,b in zip(old,state))
   if old!=new:incoming[j]=new;queue.append(j)
  while queue:
   i=queue.popleft();pops+=1;assert pops<128*(end-p)
   op,a,b,c=s[i];h=list(incoming[i])
   if op==O('RET'):continue
   if op==O('END'):bad=True;continue
   if op in (O('BR'),O('BRZ'),O('BRNZ')):
    target=labels.get(a if op==O('BR') else b,0);merge(target,tuple(h))
    if op==O('BR'):continue
   elif op==O('LGET'):h[16+a]=h[b-1]
   elif op==O('LSET'):h[a-1]=h[16+b]
   elif op==O('CONST'):h[16+a]=('I',b)
   elif op in (O('BIN'),O('CMP'),O('UN')):h[16+b]=None
   elif op==O('CALL'):
    closed=a in m and c==m[a][1] and flags[a][0];identity=closed and flags[a][1];retvalue=h[16+b] if identity else None
    if not closed:h=[None]*32
    h[16+b]=retvalue
   elif op==O('RT'):
    arg=h[16+b];alloc=a==200 and c==1 and arg is not None and arg[0]=='I' and 0<=arg[1]<=4096
    admitted=b>=0 and ((a==176 and c==2 and b<=5) or (a==208 and c==3 and b<=4) or (a in (64,72,168) and c==1))
    known=arg is not None and arg[0]=='V'
    value=('V',arg[1]) if alloc else arg if admitted and a==208 and known else ('I',arg[1]) if admitted and a==168 and known else None
    if not(alloc or admitted):h=[None]*32
    h[16+b]=value
   elif op in (O('VEC'),O('VECP')):
    n=b if op==O('VEC') else c;h=[None]*32;h[16+a]=('V',n) if 0<=n<=4096 else None
   elif op not in (O('FUEL'),O('LABEL')):h=[None]*32
   merge(i+1,tuple(h))
  status.append(('LENGTH-REFUSE' if bad else 'LENGTH-CONTEXT',f,length,p,ns,dp))
  if bad:continue
  for i in range(p+1,end):
   if i not in incoming:continue
   op,a,b,c=s[i];h=incoming[i];slot=a if op==O('RT') else wrapper(s,m,i,a,b,c) if op==O('CALL') else 0
   arg=h[16+b] if 0<=b<16 else None;index=h[17+b] if 0<=b<15 else None
   if slot in (176,208) and arg is not None and arg[0]=='V' and index is not None and index[0]=='I':accesses.append((f,length,i,arg[1],index[1]))
   if op==O('CALL') and a in m and c==m[a][1] and c>0 and m[a][5]==4 and flags[a][0] and arg is not None and arg[0]=='V':
    calls.append((f,length,i,a,arg[1]));job=(a,arg[1])
    if 0<=arg[1]<=4096 and job not in contextsSeen:contexts.append(job);contextsSeen.add(job)
  assert len(contexts)<=4096
 return contexts,calls,accesses,status

def verify(p):
 s,m,nativeFlags,end=shape.parse(p);flags,_=shape.infer(s,m);assert flags==nativeFlags and end[1]==0
 contexts,calls,accesses,status=inference(s,m,flags);gotCalls=[];gotAccess=[];gotStatus=[];end=None
 for line in p.read_text().splitlines():
  q=line.split()
  if not q:continue
  if q[0]=='LENGTH-CALL':gotCalls.append(tuple(map(int,q[1:])))
  if q[0]=='LENGTH-ACCESS':gotAccess.append(tuple(map(int,q[1:])))
  if q[0] in ('LENGTH-CONTEXT','LENGTH-REFUSE','LENGTH-SKIP'):gotStatus.append((q[0],*map(int,q[1:])))
  if q[0]=='LENGTH-END':end=tuple(map(int,q[1:]))
 assert calls==gotCalls,('calls',set(calls)^set(gotCalls));assert accesses==gotAccess,('accesses',set(accesses)^set(gotAccess));assert status==gotStatus,('status',set(status)^set(gotStatus));assert end==(len(contexts),0),(end,len(contexts))
 positive=[x for x in contexts if x[1]>=0];safe=[x for x in accesses if 0<=x[4]<x[3]]
 return {'contexts':len(contexts),'privateLengthContexts':len(positive),'constantLengthAccessFacts':len(accesses),'inRangeAccessFacts':len(safe),'outsideRangeAccessFacts':len(accesses)-len(safe),'callsWithActualLength':len(calls),'privateLengthValues':sorted({x[1] for x in positive}),'skippedContexts':sum(x[0]=='LENGTH-SKIP' for x in status),'refusedContexts':sum(x[0]=='LENGTH-REFUSE' for x in status)}
if __name__=='__main__':
 rows=[]
 for p in sorted((W/'observer/meta-ports').glob('*/compile.log')):
  rows.append({'workload':p.parent.name,**verify(p),'logSha256':hashlib.sha256(p.read_bytes()).hexdigest()});print(rows[-1],flush=True)
 assert len(rows)==19
 (W/'oracle-proof.json').write_text(json.dumps({'status':'PASS actual native rooted constructor/context CFG matches independent tuple oracle','entries':rows,'productChanged':False,'boundsChecksRemoved':0,'performanceClaim':False},indent=2)+'\n')
