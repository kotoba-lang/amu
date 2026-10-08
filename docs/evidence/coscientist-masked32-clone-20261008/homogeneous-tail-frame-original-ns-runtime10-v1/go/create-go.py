from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-original-ns-runtime10-source-v1-20261009';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
pr=json.loads((S/'preregistration.json').read_bytes());schema=json.loads((S/'go-schema.json').read_bytes());assert r(S/'source-pins.json')['sha256']=='dbd3e3c9f0200bfe5086fb84c5f3518805699d10f10fa0d4dac4a9bc57b044b4';assert not Path(pr['freshOutputRoot']).exists()
g=dict(status=pr['rootGOStatus'],maximumLoaderCalls=10,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True,sourceReviews=[])
for name in ['tc-homogeneous-tail-frame-runtime10-source-review-root-20261009','tc-homogeneous-tail-frame-original-ns-runtime10-source-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert q[k]==r(S/n)['sha256']
 g['sourceReviews'].append(r(p))
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:g[k]=r(S/n)['sha256']
for k in ['OFFActualProof','ONActualProof','ONCompletion','C95Oracle','C95OracleProof','integrationFixtureProof']:
 x=pr['qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k];assert x==r(x['path']);g[k]=x
assert set(g)==set(schema['exactKeys']);p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(r(p))
