from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-published-x16-current-observer-source-v2-20261009';O=Path(__file__).resolve().parent
R=lambda p:dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
pr=json.loads((D/'preregistration.json').read_bytes());assert R(D/'source-pins.json')['sha256']=='0ef46c0fde395c6016976d414704107b49920fa2a3d071af7c3005ffe704668b'and len(pr['cases'])==4 and not Path(pr['freshOutputRoot']).exists()
reviews=[]
for name in ['tc-published-x16-observer4-source-review-v2-root-20261009','tc-published-x16-current-observer-source-v2-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==R(D/'source-pins.json')['sha256']and q['driverSHA256']==R(D/'run.py')['sha256']and q['preregistrationSHA256']==R(D/'preregistration.json')['sha256'];reviews.append(R(p))
assert reviews[1]['sha256']=='6e64184400bd80df1fd9c01570de163f1b6a5c66fe4cac940caf275d076ba579'
f=pr['qualifiedIntegrationFixtureProof'];assert R(Path(f['path']))==f
g={'status':pr['rootGOStatus'],'maximumLoaderCalls':4,'outputRoot':pr['freshOutputRoot'],'noRetry':True,'timingAuthorized':False,'runtimeGuestAuthorized':False,'C2':False,'sourcePinsSHA256':R(D/'source-pins.json')['sha256'],'inputPinsSHA256':R(D/'input-pins.json')['sha256'],'preregistrationSHA256':R(D/'preregistration.json')['sha256'],'driverSHA256':R(D/'run.py')['sha256'],'sourceReviews':reviews,'integrationFixtureProof':f}
p=O/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(R(p))
