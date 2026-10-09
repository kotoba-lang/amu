"""Excluded offline oracle: sets, boolean tuples and global elimination, no native bitmask/worklist reuse."""
from pathlib import Path
from collections import deque,Counter
import json,re,hashlib
W=Path(__file__).resolve().parent
C={n:int(v) for n,v in re.findall(r'\(def ([A-Z][A-Z0-9-]*) (-?\d+)\)',(W/'observer/observer-unity.kotoba').read_text())}
O=lambda n:C['OP-'+n]
def parse(p):
 s={};m={};got={};end=None
 for line in p.read_text().splitlines():
  q=line.split()
  if not q:continue
  if q[0]=='SIR': s[int(q[1])]=tuple(map(int,q[2:]))
  if q[0]=='META':m[int(q[1])]=tuple(map(int,q[2:]))
  if q[0]=='SHAPE':got[int(q[1])]=tuple(map(int,q[2:]))
  if q[0]=='SHAPE-END':end=tuple(map(int,q[1:]))
 assert s and m and got and end is not None
 return s,m,got,end

def infer(s,m,join='and'):
 bounds={};locally=set();dimensions={}
 for f,(p,np,ns,dp,rt,pt) in m.items():
  e=next((j for j in range(p+1,min(max(s)+1,p+8193)) if s[j][0] in (O('FN'),O('END'))),0) if p>0 else 0
  if not e or s[e]!=(O('END'),f,0,0) or s.get(p)!=(O('FN'),f,np,s[p][3]):continue
  bounds[f]=(p,e)
  for op,a,b,c in (s[j] for j in range(p+1,e)):
   ns=max(ns,b if op==O('LGET') else a if op==O('LSET') else 0)
   need=(a+1 if op in [O(x) for x in ['CONST','LGET','STR','RET','BRZ','BRNZ','TAB','FADDR','VECP','RES2']] else a+2 if op==O('RET2') else b+1 if op in [O('LSET'),O('UN')] else b+2 if op in [O('BIN'),O('CMP')] else c+1 if op==O('CAP') else b+max(c,1) if op in [O('CALL'),O('RT')] else b+c+1 if op==O('CALLI') else a+max(b,1) if op==O('VEC') else 0)
   dp=max(dp,need)
  ns=max(ns,np,s[p][3]);dimensions[f]=(ns,dp)
  valid=0<=np<=5 and 0<=ns<4096 and 0<dp<4096
  for op,a,b,c in (s[j] for j in range(p+1,e)):
   if op==O('CONST'):good=0<=a<dp and c==0
   elif op==O('LGET'):good=0<=a<dp and 0<b<=ns and c==0
   elif op==O('LSET'):good=0<a<=ns and 0<=b<dp and c==0
   elif op in (O('BIN'),O('CMP')):good=0<=a<(16 if op==O('BIN') else 8) and 0<=b and b+1<dp and c==0
   elif op==O('UN'):good=0<=a<16 and 0<=b<dp and c==0
   elif op==O('RET'):good=0<=a<dp and b==c==0
   elif op==O('FUEL'):good=a==b==c==0
   elif op in (O('LABEL'),O('BR')):good=0<a<C['MM-LABEL-CAP'] and b==c==0
   elif op in (O('BRZ'),O('BRNZ')):good=0<=a<dp and 0<b<C['MM-LABEL-CAP'] and c==0
   elif op==O('CALL'):good=a in m and 0<=b and c>=0 and b+max(c,1)<=dp and c==m[a][1]
   elif op==O('RT'):good=0<=b and c>0 and b+c<=dp and ((a==176 and c==2 and b<=5) or (a==208 and c==3 and b<=4) or (a in (64,72,168) and c==1))
   else:good=False
   valid=valid and good
  if valid:locally.add(f)
 closed=set(locally)
 while True:
  new={f for f in closed if all(a in closed for op,a,b,c in (s[j] for j in range(bounds[f][0]+1,bounds[f][1])) if op==O('CALL'))}
  if new==closed:break
  closed=new
 ids={f for f in closed if m[f][1]>0 and m[f][4:]==(4,4) and max(dimensions[f])<=16}
 labels={}
 for i,(op,a,b,c) in s.items():
  if op==O('LABEL'):labels[a]=i if a not in labels else -1
 def identity(f,candidates):
  p,e=bounds[f];ns,dp=dimensions[f];init=((True,)+(False,)*(ns-1),(False,)*dp);incoming={p+1:init};queue=deque([p+1]);ret=False;bad=False
  def merge(j,state):
   nonlocal bad
   if not p<j<=e:bad=True;return
   old=incoming.get(j)
   value=state if old is None else tuple(tuple((x and y) if join=='and' else (x or y) for x,y in zip(xx,yy)) for xx,yy in zip(old,state))
   if old!=value:incoming[j]=value;queue.append(j)
  while queue:
   i=queue.popleft();op,a,b,c=s[i];ll,tt=incoming[i];l=list(ll);t=list(tt)
   if op==O('RET'):ret=True;bad=bad or not t[a];continue
   if op==O('END'):bad=True;continue
   if op in (O('BR'),O('BRZ'),O('BRNZ')):
    target=labels.get(a if op==O('BR') else b,0);merge(target,(tuple(l),tuple(t)))
    if op==O('BR'):continue
   elif op==O('LGET'):t[a]=l[b-1]
   elif op==O('LSET'):l[a-1]=t[b]
   elif op==O('CONST'):t[a]=False
   elif op in (O('BIN'),O('CMP'),O('UN')):t[b]=False
   elif op==O('RT'):t[b]=t[b] if a==208 else False
   elif op==O('CALL'):t[b]=(a in candidates) and t[b]
   merge(i+1,(tuple(l),tuple(t)))
  return ret and not bad
 while True:
  new={f for f in ids if identity(f,ids)}
  if new==ids:break
  ids=new
 return {f:(int(f in closed),int(f in ids)) for f in m},{'functions':len(m),'closed':len(closed),'identity':len(ids)}

def verify(p):
 s,m,got,end=parse(p);want,counts=infer(s,m)
 if end[1]:want={f:(0,0) for f in m}
 assert got==want,[(f,got.get(f),want.get(f)) for f in want if got.get(f)!=want.get(f)][:10]
 return counts
if __name__=='__main__':
 rows=[]
 for p in sorted((W/'observer/meta-ports').glob('*/compile.log')):
  rows.append({'workload':p.parent.name,**verify(p),'logSha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 assert len(rows)==19
 result={'status':'PASS independent global-set tuple-CFG oracle matches actual native output','entries':rows,'totalFunctions':sum(x['functions'] for x in rows),'totalClosed':sum(x['closed'] for x in rows),'totalIdentity':sum(x['identity'] for x in rows),'optimizerImplemented':False,'performanceClaim':False}
 (W/'oracle-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
