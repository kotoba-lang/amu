from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-vector-statemate6-source-v1-20261009';D=Path(__file__).resolve().parent
def R(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
pr=json.loads((S/'preregistration.json').read_bytes());assert R(S/'source-pins.json')['sha256']=='364c06e8377afe6275f5c8edbbcb1e23b48ef6487c874c9489be5be31fb8ba85'
assert not Path(pr['freshOutputRoot']).exists()
reviews=[]
for name in ['published-mode2-x8-vector-statemate6-source-review-root-20261009','published-mode2-x8-vector-statemate6-source-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert q[k]==R(S/n)['sha256']
 reviews.append(R(p))
g=dict(status=pr['rootGOStatus'],maximumLoaderCalls=6,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=False,C2=False,sourceReviews=reviews,candidateSourcePinsSHA256=pr['candidateSourcePins']['sha256'])
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:g[k]=R(S/n)['sha256']
for k in ['integrationFixtureProof','baselineActualProof','TCActualProof','candidateActualProof']:
 g[k]=pr['qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k];assert R(g[k]['path'])==g[k]
assert set(g)==set(json.loads((S/'go-schema.json').read_bytes())['requiredExactKeys'])
p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(R(p))
