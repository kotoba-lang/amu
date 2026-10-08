from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-statemate-vector-runtime12-source-v1-20261009';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
pr=json.loads((S/'preregistration.json').read_bytes());schema=json.loads((S/'go-schema.json').read_bytes());assert r(S/'source-pins.json')['sha256']=='11ebd564d88d282c61fad728af445d6049d6d23fa8dc4ace2fa0438985c23336';assert not Path(pr['freshOutputRoot']).exists()
g={k:schema[k]for k in schema['requiredExactKeys']if k in schema};g['sourceReviews']=[]
for name in ['published-mode2-x8-runtime12-source-review-root-20261009','published-mode2-x8-statemate-vector-runtime12-source-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_bytes());assert q['status']==pr['sourceReviewStatus']
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert q[k]==r(S/n)['sha256']
 g['sourceReviews'].append(r(p))
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:g[k]=r(S/n)['sha256']
for k,x in schema['proofs'].items():assert x==r(x['path']);g[k]=x
assert set(g)==set(schema['requiredExactKeys']);p=D/'root-go.json';assert not p.exists();p.write_text(json.dumps(g,indent=2)+'\n');print(r(p))
