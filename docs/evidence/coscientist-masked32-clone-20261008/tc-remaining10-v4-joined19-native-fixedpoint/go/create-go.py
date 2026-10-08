"""Exact bounded GO authoring only; no native/process/thread/FD/kernel-query operations."""
from pathlib import Path
import json,hashlib,sys
D=Path(__file__).resolve().parent
W=D.parent;S=W/'tc-original19-remaining10-fixedpoint-source-v4-20261009'
assert len(sys.argv)==2 and len(sys.argv[1])==64 and all(c in '0123456789abcdef'for c in sys.argv[1]);independentSHA=sys.argv[1]
def rec(p):
 assert p.is_file()and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
pr=load(S/'preregistration.json');sp=load(S/'source-pins.json')
assert rec(S/'source-pins.json')['sha256']=='690de404bdf7fbccab3726f66309a2dcfe88e43adecb44c669c03b41aae7db9b'
assert pr['maximumLoaderCalls']==10 and len(pr['cases'])==10 and pr['maximumDistinctProcessStarts']==30 and pr['C2']is False
assert not Path(pr['freshOutputRoot']).exists()
reviews=[]
for name in ['tc-original19-remaining10-fixedpoint-source-review-v4-root-20261009','tc-original19-remaining10-fixedpoint-source-review-v4-independent-20261009']:
 p=W/name/'report.json';r=load(p);assert r['status']==pr['sourceReviewStatus'];assert r['sourcePinsSHA256']==rec(S/'source-pins.json')['sha256']and r['driverSHA256']==rec(S/'run.py')['sha256']and r['preregistrationSHA256']==rec(S/'preregistration.json')['sha256'];reviews.append(rec(p))
assert reviews[1]['sha256']==independentSHA
fixture=pr['qualifiedIntegrationFixtureProof'];assert rec(Path(fixture['path']))==fixture and fixture['sha256']=='4aa595c93dbb25527caf264411e46ca9cf3bf38fc111f854d7b422963191be18';f=load(Path(fixture['path']));assert f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for name,key in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert f[key]==sp[name]['sha256']
retained=pr['retainedArtifactProof'];assert rec(Path(retained['path']))==retained and retained['sha256']=='92cfd8152e6baa4884a73f3d7c6341b96228cfb16481137a93ef9afbb30f402c';r=load(Path(retained['path']));assert r['status']==pr['retainedArtifactProofStatus']and r['conditionalAhaArtifactIdentityOnly']['verified']is True and r['strictMemoryQualification']is False
for name,z in sp.items():assert {k:rec(S/name)[k]for k in ['bytes','sha256']}==z
suite=pr['retainedSuiteProof'];assert rec(Path(suite['path']))==suite and suite['sha256']=='f253472ee7a2931e6118df45d2bf87a948c0db3fe64abb77aec8df463313c81b';sr=load(Path(suite['path']));assert sr['status']==pr['retainedSuiteProofStatus']and sr['newClosedCalls']==32 and sr['remainingUnexecutedCalls']==10 and sr['campaignQualified'] is False
G={'status':pr['rootGOStatus'],'maximumLoaderCalls':10,'outputRoot':pr['freshOutputRoot'],'noRetry':True,'timingAuthorized':False,'runtimeGuestAuthorized':False,'C2':False,'sourcePinsSHA256':rec(S/'source-pins.json')['sha256'],'inputPinsSHA256':rec(S/'input-pins.json')['sha256'],'preregistrationSHA256':rec(S/'preregistration.json')['sha256'],'driverSHA256':rec(S/'run.py')['sha256'],'sourceReviews':reviews,'integrationFixtureProof':fixture,'retainedArtifactProof':retained,'retainedSuiteProof':suite}
p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(G,indent=2)+'\n');print(json.dumps(rec(p),indent=2))
