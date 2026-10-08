"""Exact GO authoring only. No native, process, thread, FD or kernel-query calls."""
from pathlib import Path
import json,hashlib,sys
D=Path(__file__).resolve().parent;W=D.parent;S=W/'tc-current7618-off18-compile36-source-v1-20261009'
assert len(sys.argv)==2 and len(sys.argv[1])==64 and all(c in '0123456789abcdef'for c in sys.argv[1]);independentSHA=sys.argv[1]
def rec(p):
 assert p.is_file()and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
pr=load(S/'preregistration.json');sp=load(S/'source-pins.json');assert rec(S/'source-pins.json')['sha256']=='7663e9cd700585e24cc064b1bb95e052f7220aed1c05240e3a34b588fb692155'
assert pr['maximumLoaderCalls']==36 and len(pr['cases'])==36 and pr['maximumDistinctProcessStarts']==108 and pr['C2']is False
assert all(c['nativeArgv'][1]==pr['producer']for c in pr['cases'])and not Path(pr['freshOutputRoot']).exists()
reviews=[]
for name in ['tc-current7618-off18-compile36-source-review-v1-root-20261009','tc-current7618-off18-compile36-source-review-v1-independent-20261009']:
 p=W/name/'report.json';r=load(p);assert r['status']==pr['sourceReviewStatus']and r['sourcePinsSHA256']==rec(S/'source-pins.json')['sha256']and r['driverSHA256']==rec(S/'run.py')['sha256']and r['preregistrationSHA256']==rec(S/'preregistration.json')['sha256'];reviews.append(rec(p))
assert reviews[1]['sha256']==independentSHA
fixture=pr['qualifiedIntegrationFixtureProof'];assert rec(Path(fixture['path']))==fixture and fixture['sha256']=='4aa595c93dbb25527caf264411e46ca9cf3bf38fc111f854d7b422963191be18';f=load(Path(fixture['path']));assert f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert f[k]==sp[n]['sha256']
for n in ['baselineActualProof','TCActualProof']:
 assert rec(Path(pr[n]['path']))==pr[n]and load(Path(pr[n]['path']))['status']==pr[n+'Status']
assert pr['TCActualProof']['sha256']=='adfb2a8050b8aff56ef86ecefb0bf2a6628e64311172d8efa5085d09e2a70d80'
for n,r in sp.items():assert {k:rec(S/n)[k]for k in ['bytes','sha256']}==r
G={'status':pr['rootGOStatus'],'maximumLoaderCalls':36,'outputRoot':pr['freshOutputRoot'],'noRetry':True,'timingAuthorized':False,'runtimeGuestAuthorized':False,'C2':False,'sourcePinsSHA256':rec(S/'source-pins.json')['sha256'],'inputPinsSHA256':rec(S/'input-pins.json')['sha256'],'preregistrationSHA256':rec(S/'preregistration.json')['sha256'],'driverSHA256':rec(S/'run.py')['sha256'],'sourceReviews':reviews,'integrationFixtureProof':fixture,'baselineActualProof':pr['baselineActualProof'],'TCActualProof':pr['TCActualProof']}
p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(G,indent=2)+'\n');print(json.dumps(rec(p),indent=2))
