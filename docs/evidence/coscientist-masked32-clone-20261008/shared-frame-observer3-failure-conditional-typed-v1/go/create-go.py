from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'shared-frame-currenttyped-observer3-source-v1-20261009';D=Path(__file__).resolve().parent

def R(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
pr=json.loads((S/'preregistration.json').read_bytes());assert R(S/'source-pins.json')['sha256']=='3cadbd6ade753cb48a6ff808d4fd0174aaa08b6e0a75569732850af5fc007fd9'
assert not Path(pr['freshOutputRoot']).exists()and len(pr['cases'])==3
r=[]
for name in ['shared-frame-currenttyped-observer3-source-review-root-20261009','shared-frame-currenttyped-observer3-source-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert q[k]==R(S/n)['sha256']
 r.append(R(p))
g={'status':pr['rootGOStatus'],'maximumLoaderCalls':3,'outputRoot':pr['freshOutputRoot'],'noRetry':True,'timingAuthorized':False,'runtimeGuestAuthorized':False,'C2':False,'sourceReviews':r,'integrationFixtureProof':pr['qualifiedIntegrationFixtureProof']}
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:g[k]=R(S/n)['sha256']
assert set(g)==set(json.loads((S/'go-schema.json').read_bytes())['exactKeys'])
p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(R(p))
