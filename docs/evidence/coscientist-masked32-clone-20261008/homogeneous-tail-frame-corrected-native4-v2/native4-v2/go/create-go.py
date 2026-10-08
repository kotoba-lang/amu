from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-native4-source-v2-20261009';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
pr=json.loads((S/'preregistration.json').read_bytes());schema=json.loads((S/'go-schema.json').read_bytes());assert not Path(pr['freshOutputRoot']).exists()
g=dict(schema['fixed']);g['sourceReviews']=[]
for name in ['tc-homogeneous-tail-frame-native4-source-review-root-v2-20261009','tc-homogeneous-tail-frame-native4-source-v2-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert q[k]==r(S/n)['sha256']
 g['sourceReviews'].append(r(p))
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:g[k]=r(S/n)['sha256']
g['integrationFixtureProof']=pr['qualifiedIntegrationFixtureProof'];assert g['integrationFixtureProof']==r(g['integrationFixtureProof']['path']);assert set(g)==set(schema['required'])
p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(r(p))
