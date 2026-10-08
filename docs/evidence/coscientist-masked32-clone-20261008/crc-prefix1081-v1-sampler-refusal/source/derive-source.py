"""Finite offline original-source arithmetic certificate, zero native execution.

This model is a SOURCE expectation; it never supplies guest runtime answers.
"""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent;W=D.parent;R=Path('/Users/junkawasaki/github/wt/amu-seed17')
source=R/'bench/embench/batch-ports/crc32.kotoba'
raw=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008/run-outputs/observed-input-compile.stdout'
class Vec(list):pass
def parse(s):
 ts=[t for t in re.findall(r';[^\n]*|[()\[\]]|[^\s()\[\];]+',s)if not t.startswith(';')];st=[[]];ds=[]
 for t in ts:
  if t in ('(','['):q=Vec()if t=='['else[];st[-1].append(q);st.append(q);ds.append(t)
  elif t in (')',']'):assert ds.pop()==('('if t==')'else'[');st.pop()
  else:st[-1].append(int(t)if re.fullmatch(r'-?\d+',t)else t)
 assert len(st)==1;return st[0]
forms=parse(source.read_text());defs={f[1]:f for f in forms if f and f[0]in ['defn','defn-']}
def wrap(x):return ((x+(1<<63))%(1<<64))-(1<<63)
class Recur:
 def __init__(self,x):self.x=x
steps=0;indices=[]
def ev(x,e):
 global steps
 steps+=1;assert steps<=200000
 if type(x)is int:return x
 if type(x)is str:return e[x]
 if isinstance(x,Vec):return [ev(v,e)for v in x]
 h=x[0]
 if h=='if':return ev(x[2]if ev(x[1],e)else x[3],e)
 if h=='let':
  q=dict(e)
  for j in range(0,len(x[1]),2):q[x[1][j]]=ev(x[1][j+1],q)
  return ev(x[2],q)
 if h=='loop':
  q=dict(e);names=x[1][::2]
  for j in range(0,len(x[1]),2):q[x[1][j]]=ev(x[1][j+1],q)
  for _ in range(1082):
   y=ev(x[2],q)
   if not isinstance(y,Recur):return y
   q.update(zip(names,y.x))
  raise AssertionError('bounded SOURCE loop')
 if h=='recur':return Recur([ev(v,e)for v in x[1:]])
 a=[ev(v,e)for v in x[1:]]
 if h=='+':return wrap(a[0]+a[1])
 if h=='-':return wrap(a[0]-a[1])
 if h=='*':return wrap(a[0]*a[1])
 if h=='=':return a[0]==a[1]
 if h=='<':return a[0]<a[1]
 if h=='bit-and':return wrap(a[0]&a[1])
 if h=='bit-xor':return wrap(a[0]^a[1])
 if h=='bit-not':return wrap(~a[0])
 if h=='u64-shift-right':return (a[0]%2**64)>>a[1]
 if h=='vector-at':assert 0<=a[1]<len(a[0]);return a[0][a[1]]
 f=defs[h]
 if h=='table-at':assert 0<=a[0]<256;indices.append(a[0])
 return ev(f[4],dict(zip(f[2][::2],a)))
answer=ev(['prefix-crc',1081],{});assert answer==4018572661 and len(indices)==1081 and set(indices)==set(range(256))
first={i:indices.index(i)+1 for i in range(256)}
rows=[line.split()for line in raw.read_text().splitlines()]
sir={int(x[2]):list(map(int,x[3:]))for x in rows if x[0]=='FSIR'and x[1]=='0'}
ff={(int(x[2]),int(x[3])):int(x[4])for x in rows if x[0]=='FF'and x[1]=='0'}
assert [ff[(f,14)]for f in [1,2,3,6]]==[1,0,1,1]
assert sir[220]==[13,1,0,1] and sir[207]==[13,2,0,1] and sir[295]==[13,3,0,1]
assert [j for j in range(1,175)if sir[j][0]==18]==[2]
assert [j for j in range(186,239)if sir[j][0]==18]==[187,234]
assert [j for j in range(291,298)if sir[j][0]==18]==[292]
charged=1+1+1081+1081;assert charged==2164
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
out={'status':'SOURCE_FINITE_EXPECTATION_ONLY_NO_NATIVE_REACH_PROOF','source':pin(source),'typedCurrentRaw':pin(raw),
 'argument':1081,'expectedCRC':answer,'initialFuel':1000000,'fuelFormula':'prefix entry1 +checksum entry1 +table-at entry*n +checksum recur*n =2*n+2',
 'entryFuelSIR':[292,187,2],'recurFuelSIR':234,'nextSeedEntryCharged':False,'consumedFuel':charged,'expectedRemainingFuel':1000000-charged,
 'expectedIndexCount':len(indices),'uniqueTableIndices':len(set(indices)),'orderedIndices':indices,'firstVisitIterationByIndex':first,'lastFirstVisitIteration':max(first.values()),
 'selectedCallerSIR':220,'originalGuestSourceUnchanged':True,'modelOperationBudget':200000,'modelOperationsUsed':steps,'nativeCalls':0,'nativeFull256ReachQualified':False}
(D/'fuel-reach-certificate.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['expectedCRC','consumedFuel','expectedRemainingFuel','uniqueTableIndices','lastFirstVisitIteration','modelOperationsUsed']}))
