from pathlib import Path
import json,hashlib,tarfile
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent
S=W/'vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote';G=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root';R=W/'vector-leaf-straight-read-cache-current19-build52-actual-review-v2-independent'
ROOT='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root';NEW='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-fresh-consumer-functional285-v1-root'
H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def ref(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=H(b))
pr=load(S/'preregistration.json');man=load(G/'collected/package/manifest.json');rev=load(R/'report.json')
assert H((G/'build52-acceptance.json').read_bytes())=='ddd76f3a44bf33e619a5a796e50816e10b2253b41d584c8988b15ea2a64880a1'
assert H((R/'report.json').read_bytes())=='9f222b2c1aab80dcb68dd8b5cdf2b6b6a844aea98b85eb6e0e3ef46ee8ba4f5e'
with tarfile.open(S/'assembly-outputs/package.tgz') as t:origin=json.load(t.extractfile('package/origin-map.json'))
guards={ROOT+'/'+m['path']:{k:m[k] for k in ['bytes','sha256']} for m in man['members']}
guards[ROOT+'/package/manifest.json']={k:ref(G/'collected/package/manifest.json')[k] for k in ['bytes','sha256']}
for p,r in load(R/'input-pins.json').items():
 prefix=str(G/'collected')+'/'
 if p.startswith(prefix):guards[ROOT+'/'+p.removeprefix(prefix)]={k:r[k] for k in ['bytes','sha256']}
cases=[]
for r,a in zip(pr['entries'],rev['images']):
 assert r['workload']==a['workload'];c=dict(r)
 for arm in ['OFF','LC','OFFContainer','LCContainer']:
  target=origin[r[arm]['path']];assert isinstance(target,str);c[arm]=dict(r[arm],path=ROOT+'/'+target)
 c.update(C=a['C'],runner=a['runner'],header=a['header'],buildAnchors=a);cases.append(c)
save('remote-input-pins.json',guards)
inputs=load(S/'input-origins.json')
for p,r in load(R/'input-pins.json').items():inputs[p]={k:r[k] for k in ['bytes','sha256']}
for p in [S/'preregistration.json',S/'source-pins.json',S/'README.md',S/'common.py',S/'header.py',S/'build52.py',G/'build52-acceptance.json',R/'report.json',R/'input-pins.json',S/'assembly-outputs/manifest.json',S/'root-functional285-acceptance-ref.json']:
 rr=ref(p);inputs[str(p)]={k:rr[k] for k in ['bytes','sha256']}
assert len(inputs)<=4096 and sum(r['bytes'] for r in inputs.values())<=448*1024**2,(len(inputs),sum(r['bytes'] for r in inputs.values()))
save('input-pins.json',inputs)
for n,p in [('build52-acceptance.json',G/'build52-acceptance.json'),('build52-independent-report.json',R/'report.json')]: (D/n).write_bytes(p.read_bytes())
# Preregistration is written before the operative SOURCE files.
save('preregistration.json',dict(status='PROSPECTIVE_SOURCE_ONLY_FRESH_CONSUMER_FUNCTIONAL285_NO_GO',schema='LC_FRESH_CONSUMER_FUNCTIONAL285/v1',destination='zebulun@100.66.28.79',buildRoot=ROOT,remoteRoot=NEW,outputRoot=NEW+'/functional285',maximumChildren=285,maximumLaunchTransportChildren=1,callsPerProfile=1,warmupCalls=0,nativeFuel=16777216,nativeCaps=dict(pairs=2097152,stringPoolBytes=65536,vectors=4096,vectorItems=65536),maximumInputFiles=4096,maximumInputLogicalBytes=448*1024**2,childTimeoutSeconds=30,childRawBytesMaximum=16777216,totalSequentialDeadlineSeconds=9300,reapSeconds=[30,30],firstFailureStop=True,retries=0,compilerCalls=0,timingQualified=False,quietQualified=False,C2skip=False,wholeOriginalBodiesSourcesSymbolsProfilesBuildAnchorsUnchanged=True,buildAcceptance=ref(G/'build52-acceptance.json'),buildIndependentReview=ref(R/'report.json'),initialDirect285Acceptance=load(S/'root-functional285-acceptance-ref.json'),consumerSource=pr['consumerSource'],cases=cases,remoteClosureFiles=len(guards),remoteClosureBytes=sum(r['bytes'] for r in guards.values()),localClosureFiles=len(inputs),localClosureBytes=sum(r['bytes'] for r in inputs.values()),rootGOStatus='ROOT_GO_LC_FRESH_CONSUMER_FUNCTIONAL285_ONLY',sourceReviewStatus='PASS_SOURCE_LC_FRESH_CONSUMER_FUNCTIONAL285',beforeOperativeSourceWriting=True))
# Reuse reviewed finite ledger byte-for-byte; only its cohort deadline changes.
common=(S/'common.py').read_text();ledger=common[common.index('class Ledger:'):].replace('<7800','<9300')
(D/'ledger.py').write_text('from pathlib import Path\nimport hashlib,json,os,subprocess,signal,time,stat,resource\nH=lambda b:hashlib.sha256(b).hexdigest()\ndef need(x,m):\n if not x:raise AssertionError(m)\ndef save(p,v):Path(p).write_text(json.dumps(v,indent=2)+"\\n")\ndef ref(p):\n p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=H(p.read_bytes()))\n'+ledger)
