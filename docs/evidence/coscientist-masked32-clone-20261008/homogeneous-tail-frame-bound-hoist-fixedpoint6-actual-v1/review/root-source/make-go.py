from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-compose511-bound-hoist-g2-g3-g4-fixedpoint6-source-v1-20261009';P=json.loads((D/'preregistration.json').read_bytes());O=W/'tc-hft-compose511-bound-hoist-fixedpoint6-go-root-20261009';O.mkdir(exist_ok=False)
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
g=dict(status=P['rootGOStatus'],maximumLoaderCalls=6,outputRoot=P['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=False,C2=False,outerHostLaunchRequiresEscalation=True,sourceReviews=[rec(W/'tc-hft-compose511-bound-hoist-fixedpoint6-source-review-root-20261009/report.json'),rec(W/'tc-hft-compose511-bound-hoist-fixedpoint6-source-review-independent-20261009-dense/report.json')],candidateSourcePinsSHA256=P['candidateSourcePins']['sha256'])
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:g[k]=rec(D/n)['sha256']
for k in ['G1ActualProof','G1Completion','G1ProducerBuildReceipt']:g[k]=P[k]
g['integrationFixtureProof']=P['qualifiedIntegrationFixtureProof']
assert not Path(P['freshOutputRoot']).exists();(O/'root-go.json').write_text(json.dumps(g,indent=2)+'\n');print(json.dumps(rec(O/'root-go.json')))
