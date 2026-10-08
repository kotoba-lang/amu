from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-functional-remaining50-source-v1-20261009';O=Path(__file__).resolve().parent
def R(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
pr=json.loads((D/'preregistration.json').read_bytes());assert R(D/'source-pins.json')['sha256']=='c9a42f1ad3281e97f4b1d9521b67259e27531c1ecd23c31f0e5d21000a73461a'
assert len(pr['cases'])==50 and not Path(pr['freshOutputRoot']).exists()
reviews=[]
for name in ['tc-original19-functional-remaining50-source-review-root-20261009','tc-original19-functional-remaining50-source-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==R(D/'source-pins.json')['sha256']and q['driverSHA256']==R(D/'run.py')['sha256']and q['preregistrationSHA256']==R(D/'preregistration.json')['sha256'];reviews.append(R(p))
assert reviews[0]['sha256']=='ccb492841170bfe2faf95d19a34daa02799fbfd4e349190407e8fb4e1698b346'
g={'status':pr['rootGOStatus'],'maximumLoaderCalls':50,'outputRoot':pr['freshOutputRoot'],'noRetry':True,'timingAuthorized':False,'runtimeGuestAuthorized':True,'C2':False,'sourcePinsSHA256':R(D/'source-pins.json')['sha256'],'inputPinsSHA256':R(D/'input-pins.json')['sha256'],'preregistrationSHA256':R(D/'preregistration.json')['sha256'],'driverSHA256':R(D/'run.py')['sha256'],'sourceReviews':reviews}
for k in ['OFFActualProof','TCActualProof','C95Oracle','C95OracleProof','integrationFixtureProof']:
 g[k]=pr['qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k];assert R(Path(g[k]['path']))==g[k]
g['retainedV2Failure']=pr['retainedV2Failure']
for r in g['retainedV2Failure'].values():assert R(Path(r['path']))==r
g['retainedV2FailureProof']=pr['retainedV2FailureProof'];assert R(Path(g['retainedV2FailureProof']['path']))==g['retainedV2FailureProof']
for k in ['retainedV3FailureProof','retainedRaw70Proof']:
 g[k]=pr[k];assert R(Path(g[k]['path']))==g[k]
assert set(g)==set(json.loads((D/'go-schema.json').read_bytes())['exactKeys'])
p=O/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(R(p))
