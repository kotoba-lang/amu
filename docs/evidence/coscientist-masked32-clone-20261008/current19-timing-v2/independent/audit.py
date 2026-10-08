from pathlib import Path
import json,hashlib,sys,tarfile,stat,collections
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');T=W/'vector-masked32-current19-timing-transport-source-v1-controls';O=T/'collect-outputs';C=O/'collected';A=Path(__file__).parent;ip={}
def pin(p):
 st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink();b=p.read_bytes();z={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};ip[str(p)]=z;return z
def load(p):pin(p);return json.loads(p.read_bytes())
inv=load(C/'inventory.json');seal=load(O/'seal-receipt.json');assert pin(O/'result.tgz')=={'bytes':1562981,'sha256':'432360a1590a33f21fbc07c73451fe11f564cf7c77ef2bf83ba643399e8037cc'}
expected={r['name']:r for r in inv['members']};assert len(expected)==len(inv['members'])==20893
seen=set();expanded=0;inventorySeen=0
with tarfile.open(O/'result.tgz','r:gz') as tf:
 for m in tf:
  assert m.isreg() and not m.pax_headers and '..' not in Path(m.name).parts and not m.name.startswith('/')
  if m.name=='inventory.json':
   inventorySeen+=1;assert inventorySeen==1;assert tf.extractfile(m).read()==(C/'inventory.json').read_bytes();continue
  assert m.name in expected and m.name not in seen;z=expected[m.name];assert m.size==z['bytes'];b=tf.extractfile(m).read();assert hashlib.sha256(b).hexdigest()==z['sha256'];p=C/m.name;assert pin(p)=={k:z[k]for k in ['bytes','sha256']};seen.add(m.name);expanded+=len(b)
assert inventorySeen==1 and seen==set(expected) and expanded==18974091
assert pin(C/'inventory.json')['sha256']==seal['inventorySHA256']
for stage in ['install','launch','collect']:
 d=T/(stage+'-outputs');g=load(d/'root-go.json');rows=load(d/'attempts.json');term=load(d/'terminal.json');assert len(rows)==(2 if stage=='collect' else 1)
 for r in rows:
  assert r['state']=='terminal' and r['returncode']==0 and not r['timeout'] and r['exception'] is None
  for suffix in ['stdout','stderr']:
   p=d/(r['label']+'.'+suffix);assert pin(p)['sha256']==r[suffix+'SHA256'];assert suffix!='stderr' or p.stat().st_size==0
 for v in g['sourceReviews']:assert pin(Path(v['path']))=={k:v[k]for k in ['bytes','sha256']}
 assert g['sourcePinsSHA256']=='765ec502a34f7af02cacac3be769e804452559b738378f7ccb039f9ed9c26fe4'
for name,z in load(C/'transport/installed-manifest.json').items():assert pin(C/'installed'/name)==z
local=T/'install-outputs/installed-manifest-proposed.json';assert (C/'transport/installed-manifest.json').read_bytes()==local.read_bytes();pin(local)
assert (C/'transport/install-go.json').read_bytes()==(T/'install-outputs/root-go.json').read_bytes()
assert (C/'transport/campaign-go.json').read_bytes()==(C/'results/root-go.json').read_bytes()
S=W/'vector-masked32-current19-timing-source-v2-controls'
for d in [S,T]:
 for n,z in load(d/'source-pins.json').items():assert pin(d/n)==z
remote=load(S/'remote-input-pins.json');assert len(remote)==118
assert pin(S/'remote-input-pins.json')['sha256']=='2df9e1b812b08c97be5918d2a83b869dca982101a82bb2bbfa3436f5f5e20147'
R=W/'vector-masked32-current19-timing-audit-reader-v1-width';sys.path.insert(0,str(R));import reader
result=reader.audit(C/'results',True);assert result==load(W/'vector-masked32-current19-timing-collected-audit-v1-root/report.json');(A/'recomputed.json').write_text(json.dumps(result,indent=2)+'\n')
for k,z in load(S/'proof-bindings.json').items():assert pin(S/'proofs'/(k+'.json'))=={k:z[k]for k in ['bytes','sha256']}
for n,z in load(S/'proofs/functionalInputPins.json').items():assert pin(Path(n))==z
for n,z in load(R/'source-pins.json').items():assert pin(R/n)==z
partial={}
for name,v in result['partial'].items():
 s=load(C/'results/workloads'/(name+'.json'));reasons=collections.Counter();arms=collections.Counter()
 for t in s['triples']:
  for a,ev in t['arms'].items():
   if not ev['quiet']:
    d=ev['diagnostic'];reasons[d['reason']]+=1;arms[a]+=1
    if d['reason']=='notQuiet':
     if ev['beforeLoad']>4 or ev['afterLoad']>4:reasons['loadAbove4']+=1
     if d['external']['estimatedBackgroundIdlePercent']<90:reasons['backgroundIdleBelow90']+=1
 partial[name]={**v,'rejectedMeasuredArmReasons':dict(reasons),'rejectedMeasuredArms':dict(arms),'calibrationByArm':{a:[{'attempt':q['attempt'],'calls':q['calls'],'elapsedNanoseconds':q['elapsedNanoseconds'],'quiet':q['quiet'],'reason':q['diagnostic']['reason']}for q in s['calibration']if q['arm']==a]for a in ['baseline','candidate','C']}}
(A/'partial-causes.json').write_text(json.dumps(partial,indent=2)+'\n')
(A/'input-pins.json').write_text(json.dumps(ip,indent=2,sort_keys=True)+'\n')
print('PASS',len(ip),len(result['completedNamedWorkloads']),len(partial))
