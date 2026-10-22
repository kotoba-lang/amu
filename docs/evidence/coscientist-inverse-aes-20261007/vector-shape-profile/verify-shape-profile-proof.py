"""Offline digest and recorded-receipt verification. Never executes bundled code."""
from pathlib import Path
import json,hashlib,tarfile,collections
D=Path(__file__).resolve().parent;M=json.loads((D/'shape-profile-proof.manifest.json').read_text());A=D/'shape-profile-proof.tgz'
h=lambda b:hashlib.sha256(b).hexdigest()
assert A.stat().st_size==M['archive']['bytes']<=M['compressedCap'] and h(A.read_bytes())==M['archive']['sha256']
objects={};total=0
with tarfile.open(A,'r:gz') as t:
 for m in t:
  assert m.isfile() and m.name.startswith('objects/') and m.name.count('/')==1
  key=m.name.split('/')[1];assert key in M['objects'] and key not in objects
  assert m.size==M['objects'][key]['bytes'];total+=m.size;assert total<=M['expandedCap']
  b=t.extractfile(m).read();assert h(b)==key and len(b)==m.size;objects[key]=b
assert set(objects)==set(M['objects']) and total==M['expandedObjectBytes']
for p,v in M['logicalPaths'].items():assert len(objects[v['sha256']])==v['bytes'] and '..' not in Path(p).parts
read=lambda p:objects[M['logicalPaths'][p]['sha256']]
j=lambda p:json.loads(read(p))
r1=j('vector-shape-query-profile-native-v1/attempts.json');r2=j('vector-shape-query-profile-native-continuation-v1/attempts.json')
assert len(r1)==4 and len(r2)==2 and all(r['state']=='terminal' and r['returncode']==0 for r in r1+r2)
root=j('vector-shape-query-profile-actual-root-v1/report.json');assert root['fixedCompilerProcesses']==6 and root['baselineKseedNativeOffsetParity'] and not root['timing'] and not root['cacheValidityProven']
rootrows={r['workload']:r for r in root['workloadProfiles']};propagation=j('vector-shape-query-profile-actual-root-v1/round-propagation.json');assert propagation['status'].startswith('PASS observed keys propagate');summary=[]
for n,path in [('picojpeg','vector-shape-query-profile-native-v1/picojpeg/compile.stdout'),('qrduino','vector-shape-query-profile-native-continuation-v1/compile.stdout')]:
 pr=next(v for v in propagation['profiles'] if v['workload']==n);assert pr['rawSHA256']==h(read(path));assert any(v['changedObservedKeys'] for v in pr['rounds']);profile=j('vector-shape-query-profile-parser-v2/'+n+'-profile-accounting.json');stack=[];pairs=[];rounds=[]
 for line in read(path).decode().splitlines():
  p=line.split()
  if not p:continue
  if p[0] in ['VWQBEGIN','VWQEND','VWROUND','VWSTAGE']:
   v=list(map(int,p[1:]));assert len(v)=={'VWQBEGIN':9,'VWQEND':6,'VWROUND':3,'VWSTAGE':3}[p[0]]
   if p[0]=='VWQBEGIN':stack.append(v)
   elif p[0]=='VWQEND':
    assert stack;b=stack.pop();assert b[:3]==v[:3] and v[3]>=b[3];pairs.append((b,v))
   elif p[0]=='VWROUND':rounds.append(v)
 assert not stack and len(pairs)==len(profile['queryPairs'])==rootrows[n]['queryPairs']
 for (b,e),q in zip(pairs,profile['queryPairs']):
  assert [q['fn'],q['candidate'],q['mode']]==b[:3] and q['beginWork']==b[3] and q['endWork']==e[3] and q['workDelta']==e[3]-b[3]
  assert q['partialKey']==[b[0],b[1],b[2],*b[5:9]] and q['refusedPartial']==bool(e[4])
 freq=collections.Counter(tuple(q['partialKey'])for q in profile['queryPairs']);repeat=sum(v-1 for v in freq.values())
 assert repeat==rootrows[n]['repeatedQueriesAfterFirst']
 assert len(rounds)==len(rootrows[n]['rounds']) and profile['finalVWSTATUS']==rootrows[n]['final']==[1,6,268435456,profile['finalVWSTATUS'][3],profile['finalVWSTATUS'][4],0]
 summary.append({'workload':n,'queries':len(pairs),'rounds':len(rounds),'repeatAfterFirst':repeat})
print(json.dumps({'status':'PASS recorded6calls source/log digests and exact query receipt joins','archiveBytes':A.stat().st_size,'objects':len(objects),'compilerCalls':6,'benchmarkBodies':0,'profiles':summary,'nativeExecutionsByReader':0,'timing':False,'cacheValidityProven':False}))
