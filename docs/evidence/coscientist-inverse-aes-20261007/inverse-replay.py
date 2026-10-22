"""Stdlib-only offline verifier. Executes Python certificate/audit copies only, never native/solver."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,sys,subprocess,struct,re,functools
D=Path(__file__).resolve().parent;m=json.loads((D/'inverse-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();archive=D/m['archive'];assert sha(archive)==m['archiveSHA256']and archive.stat().st_size==m['archiveBytes']
root=Path(tempfile.mkdtemp(prefix='inverse-offline-'));expected={x['member']:x for x in m['members']};assert len(expected)==m['memberCount']
with tarfile.open(archive,'r:gz')as t:
 members=t.getmembers();assert len(members)==len(expected)and{q.name for q in members}==set(expected)
 for q in members:
  p=PurePosixPath(q.name);assert q.isfile()and not p.is_absolute()and'..'not in p.parts;row=expected[q.name];data=t.extractfile(q).read();assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];out=root/q.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
W=root/'payload/private/tmp/amu-aes-resident-fuel-20261007';records=[]
def python_copy(rel,output):
 original=W/rel;source=original.read_text();assert source.count('from pathlib import Path')==1
 injection='''from pathlib import Path as _OriginalPath
class Path(type(_OriginalPath())):
 def __new__(cls,*args,**kwargs):
  if args:
   s=str(args[0])
   if s.startswith('/') and not s.startswith(ROOT): args=(ROOT+'/payload/'+s.lstrip('/'),)+args[1:]
  return super().__new__(cls,*args,**kwargs)
'''
 code='ROOT='+repr(str(root))+'\n'+source.replace('from pathlib import Path',injection,1)
 runtime=root/(Path(rel).parent.name+'-runtime.py');runtime.write_text('SOURCE='+repr(code)+'\nexec(compile(SOURCE,'+repr(str(original))+',"exec"),{"__file__":'+repr(str(original))+'})\n')
 wanted={q:sha(W/q)for q in output};p=subprocess.run([sys.executable,str(runtime)],capture_output=True,timeout=60)
 (root/(Path(rel).parent.name+'.stdout')).write_bytes(p.stdout);(root/(Path(rel).parent.name+'.stderr')).write_bytes(p.stderr);assert p.returncode==0,(rel,p.stderr.decode());assert all(sha(W/q)==h for q,h in wanted.items()),(rel,'generated output changed')
 records.append({'script':rel,'exit':p.returncode,'outputsExact':len(wanted)})
python_copy('team-inverse-compositional-laws/check.py',['team-inverse-compositional-laws/checker-report.json','team-inverse-compositional-laws/realized-source-witnesses.json'])
python_copy('team-inverse-machine-independent/audit.py',['team-inverse-machine-independent/machine-report.json'])
seeds=[(W/'root-inverse-selfbuild-v2'/f'seed-{i}.bin').read_bytes()for i in range(1,5)];assert len(set(seeds))==1 and hashlib.sha256(seeds[0]).hexdigest()=='7ea1b815396ef85dabe25a5c648efe74ff853d823507412c59178c1e26795f92'
H=W/'team-inverse-hardware-fragment';plan=json.loads((W/'team-inverse-native-calibration-plan/case-manifest.json').read_text());cases=plan['cases'];assert len(cases)==1108;src=(W/'team-timing/timing-package/nettle-aes/source.kotoba').read_text();read=lambda n:sum([list(map(int,re.search(r'\(def '+n+'-'+str(k)+r' \[([^]]+)\]',src)[1].split()))for k in range(2)],[]);T=[read('dec-t'+str(k))for k in range(4)];S=read('dec-sbox')
def mul(a,b):
 v=0
 for _ in range(8):
  if b&1:v^=a
  a=((a<<1)^(0x11b if a&128 else 0))&255;b>>=1
 return v
def mix(vals,inv=True):
 mat=[[14,11,13,9],[9,14,11,13],[13,9,14,11],[11,13,9,14]]if inv else[[2,3,1,1],[1,2,3,1],[1,1,2,3],[3,1,1,2]]
 return sum(functools.reduce(int.__xor__,[mul(vals[k],mat[row][k])for k in range(4)])<<(8*row)for row in range(4))
pr=json.loads((H/'preregistration.json').read_text());build=json.loads((H/'build-receipts.json').read_text());executions=json.loads((H/'execution-receipts.json').read_text());assert len(build)==4 and len(executions)==16 and all(x['exit']==0 for x in executions)
results={}
for name in ['positive',*pr['mutations']]:
 br=next(x for x in build if x['name']==name);b=(H/name).read_bytes();assert hashlib.sha256(b).hexdigest()==br['sha256'];words=pr['words'].copy()
 if name!='positive':
  for k,v in pr['mutations'][name]['wordChanges'].items():words[int(k)]=v
 assert list(struct.unpack_from('<10I',b,br['functionFileOffset']))==br['words']==words
 actual={}
 for g in range(4):
  data=(H/f'group-{g}.bin').read_bytes();entries=list(struct.iter_unpack('<8Q',data));lines=(H/f'{name}-{g}.stdout').read_text().splitlines();assert len(entries)==len(lines)==277
  for entry,line in zip(entries,lines):
   i,*args,ex=entry;c=cases[i];assert c['group']==g and args==c['argsUint64']and ex==c['inverseFragmentExpectedUint64'];j,v=map(int,line.split());assert i==j and i not in actual;actual[i]=v
 assert len(actual)==1108;changed=[]
 for i,c in enumerate(cases):
  mode,a,b,cw,d,key=c['argsUint64'];state=[a,b,cw,d];idx=[(state[k]>>(8*k))&255 for k in range(4)];source=functools.reduce(int.__xor__,[T[k][idx[k]]for k in range(4)])^key;assert source==c['inverseFragmentExpectedUint64'];want=source
  if name=='wrongpacking':want=mix([S[a&255],S[(d>>8)&255],S[(cw>>16)&255],S[(b>>24)&255]])^key
  if name=='wrongmix':want=mix([S[v]for v in idx],False)^key
  if name=='truncatedkey':want=source&0xffffffff
  assert actual[i]==want
  if want!=source:changed.append(i)
 if name=='positive':assert not changed
 else:assert next(i for i,c in enumerate(cases)if c['id']==pr['mutations'][name]['witness'])in changed
 results[name]={'cases':1108,'changed':len(changed),'same':1108-len(changed)}
# Offline retained provenance checks; no fresh CPU query or native process.
assert (H/'host-feature-read.stdout').read_text()=='1\nMacBookPro18,4\narm64\n'
assert (H/'host-feature-read.stderr').read_text()==''
fs=json.loads((H/'host-feature-read-status.json').read_text());assert fs['exit']==0 and fs['command']==['/usr/sbin/sysctl','-n','hw.optional.arm.FEAT_AES','hw.model','hw.machine']
feature=json.loads((H/'host-feature.json').read_text());assert feature=={'AES':1,'model':'MacBookPro18,4','arch':'arm64','hostname':'main-2.local','verifiedReadOnlySysctl':True}
for pin in json.loads((H/'pre-execution-pins.json').read_text()):
 q=H/pin['path'];assert q.stat().st_size==pin['bytes'] and sha(q)==pin['sha256']
seen=set()
legacy='/private/tmp/amu-aes-resident-fuel-20261007/team-inverse-hardware-fragment'
for e in executions:
 name=e['variant'];g=e['group'];assert name in ['positive',*pr['mutations']] and g in range(4) and (name,g)not in seen;seen.add((name,g))
 assert e['command']==[legacy+'/'+name,legacy+'/group-'+str(g)+'.bin',name]
 stderr=(H/f'{name}-{g}.stderr').read_text();match=re.fullmatch(r'AES=1 cases=277 mismatches=(\d+)\n',stderr);assert match
 mismatch=sum(int(v)!=cases[int(i)]['inverseFragmentExpectedUint64'] for i,v in [line.split()for line in(H/f'{name}-{g}.stdout').read_text().splitlines()]);assert int(match[1])==mismatch
 if name=='positive':assert mismatch==0
assert len(seen)==16
report={'status':'PASS selected offline inverse proof replay only','members':len(expected),'allMemberHashesExact':True,'fourGenerationNativeBytesEqual':True,'copiedPythonChecks':records,'hardwareFragmentRetainedRawRecomputed':results,'nativeSolverNetworkTimingRuns':0,'retainedFeatureAndPreExecutionProvenanceExact':True,'historicalSMT':'Retained pinned UNSAT/UNKNOWN/SAT and independent structural-binding receipts; no solver rerun or stdlib SMT solver claim.','unqualified':['compiledCALL ABI/capture/fuel/fullM dynamic validation','product adoption','performance or official score'],'extractionDirectory':str(root)}
(D/'offline-replay-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
