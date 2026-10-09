"""Pure identity/registration transforms; file materialization only inside explicit build GO."""
from pathlib import Path
import json,hashlib,copy
def unique_object(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise AssertionError("duplicate metadata key")
  d[k]=v
 return d
def load(p):return json.loads(Path(p).read_bytes(),object_pairs_hook=unique_object)
from header import header
from qualification import cases
D=Path(__file__).resolve().parent
def need(x,m):
 if not x:raise AssertionError(m)
def pin(p,r):
 p=Path(p);a=p.stat();b=p.read_bytes();z=p.stat();need(p.is_file()and not p.is_symlink()and(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable regular');need(len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256'],'whole pin');return b
def receipt(p):
 b=Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def packet(root):
 rows=copy.deepcopy(json.loads((D/'packet.json').read_text())['entries'])
 for r in rows:
  w=r['workload'];r['source']['path']=str(root/'sources/kotoba'/f'{w}.kotoba');pin(r['source']['path'],r['source'])
  for arm in ['OFF','ON']:
   r[arm]['native']['path']=str(root/'inputs'/w/(arm+'.bin'));r[arm]['container']['path']=str(root/'inputs'/w/(arm+'.kseed'))
   pin(r[arm]['native']['path'],r[arm]['native']);pin(r[arm]['container']['path'],r[arm]['container'])
 return rows
def c_proofs(root,rows,pins):
 need(len(pins)==19 and len({r['path']for r in pins})==19,'19 distinct independent C proofs');result={}
 for descriptor in pins:
  pin(descriptor['path'],descriptor);q=load(descriptor['path']);need(q['status']=='PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY'and q['bridgeABI']=='I64_8ARGS','fresh independently audited C source identity')
  w=q['workload'];r=next(r for r in rows if r['workload']==w);need(w not in result and q['symbol']==r['symbol'],'own symbol/workload')
  need(Path(q['artifact']['path'])==root/'C-build-outputs'/w/'c.dylib','same fresh actual C phase output');pin(q['artifact']['path'],q['artifact']);result[w]=q
 need(set(result)=={r['workload']for r in rows},'all19 proof coverage');return result
def expected_index():
 q=json.loads((D/'expected-observables.json').read_text());need(q['actualProofSHA256']=='c059cce62673d6885c9f2cabdedee68286af90f6dd4d0b0c2120e63cccc1b91e'and len(q['cases'])==190,'exact current190 expectations');return {(r['workload'],r['n'],r['arm']):r['observables']for r in q['cases']}
def qualification_cases(root,rows,consumer_artifacts):
 need(set(consumer_artifacts)=={r['workload']for r in rows},'all19 consumers');expected=expected_index();out=cases(rows)
 for i,q in enumerate(out,1):
  w=q['workload'];q['index']=i;q['label']=f'{i:03d}-{w}-{q["arm"]}-n{q["n"]}-{q["phase"]}';q['profile']=q['n'];q['expected']=expected[(w,q['n'],'ON'if q['arm']=='ON'else'OFF')];q['expectedResult']=q['expected']['result'];q['consumer']=consumer_artifacts[w]
  q['nativeArgv']=[str(root/'consumer-build-outputs'/w/'consumer'),q['arm'],str(q['n']),str(q['calls']),'1'];need(q['consumer']['path']==q['nativeArgv'][0],'own consumer fixed path')
 need(len(out)==342 and sum(q['calls']+q['warmup']for q in out)==741,'original285+repeat57');return out
