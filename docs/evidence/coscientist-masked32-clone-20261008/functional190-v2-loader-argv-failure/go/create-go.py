from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-functional190-source-v2-20261009';O=Path(__file__).resolve().parent
def R(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
pr=json.loads((D/'preregistration.json').read_bytes());assert R(D/'source-pins.json')['sha256']=='8d3805c69a58a545c8b71aa618c81161172210c33e210f98edd6fa693da9b2be'
assert len(pr['cases'])==190 and not Path(pr['freshOutputRoot']).exists()
reviews=[]
for name in ['tc-original19-functional190-source-review-v2-root-20261009','tc-original19-functional190-source-v2-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==R(D/'source-pins.json')['sha256']and q['driverSHA256']==R(D/'run.py')['sha256']and q['preregistrationSHA256']==R(D/'preregistration.json')['sha256'];reviews.append(R(p))
assert reviews[0]['sha256']=='ef30036674fc38843a39463d0f6efa932e6ae02faedb2f2294d4591e124ad7fd'
g={'status':pr['rootGOStatus'],'maximumLoaderCalls':190,'outputRoot':pr['freshOutputRoot'],'noRetry':True,'timingAuthorized':False,'runtimeGuestAuthorized':True,'C2':False,'sourcePinsSHA256':R(D/'source-pins.json')['sha256'],'inputPinsSHA256':R(D/'input-pins.json')['sha256'],'preregistrationSHA256':R(D/'preregistration.json')['sha256'],'driverSHA256':R(D/'run.py')['sha256'],'sourceReviews':reviews}
for k in ['OFFActualProof','TCActualProof','C95Oracle','C95OracleProof','integrationFixtureProof']:
 g[k]=pr['qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k];assert R(Path(g[k]['path']))==g[k]
assert set(g)==set(json.loads((D/'go-schema.json').read_bytes())['exactKeys'])
p=O/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(R(p))
