from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;F=W/'crc-capture-popen-transfer-fixture-source-v3-20261009'
rec=lambda p:{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
sp=json.loads((F/'source-pins.json').read_text());ip=json.loads((F/'input-pins.json').read_text());reviews=[]
for name in ['crc-capture-popen-transfer-fixture-source-v3-review-root-20261009','crc-capture-popen-transfer-fixture-source-v3-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_text());assert q['status']=='PASS_SOURCE_ONLY_FIXED_FILEIO_CAPTURE_CONTROLLER_FIXTURE' and q['sourcePinsSHA256']==rec(F/'source-pins.json')['sha256'] and q['driverSHA256']==sp['run.py']['sha256'];reviews.append(rec(p))
p=W/'crc-capture-popen-transfer-fixture-supervisor-review-v4-independent-20261009/report.json';sr=rec(p);q=json.loads(p.read_text());assert q['status']=='PASS_SOURCE_ONLY_ONE_FIXED_FILEIO_FIXTURE_SUPERVISOR_V4' and q['supervisorSHA256']==rec(D/'supervise.py')['sha256']
assert not (F/'GO.json').exists() and not (F/'run-outputs').exists() and not (D/'GO.json').exists() and not (D/'run-outputs').exists()
(F/'GO.json').write_text(json.dumps({'status':'GO_FIXED_FILEIO_THREAD_FIXTURE_ONCE','sourcePinsSha256':rec(F/'source-pins.json')['sha256'],'outputRoot':str(F/'run-outputs')},indent=2)+'\n')
pins=dict(ip)
for n,v in sp.items():assert str(F/n)not in pins or pins[str(F/n)]==v;pins[str(F/n)]=v
for p in [F/'source-pins.json',F/'input-pins.json',F/'GO.json',F/'preregistration.json']:
 r=rec(p);pins[str(p)]={k:r[k]for k in ['bytes','sha256']}
g={'status':'ROOT_GO_ONE_FIXED_FILEIO_FIXTURE_SUPERVISED_V4','supervisorSHA256':rec(D/'supervise.py')['sha256'],'pins':pins,'sourceReviews':reviews,'supervisorReview':sr,'outputRoot':str(D/'run-outputs')}
(D/'GO.json').write_text(json.dumps(g,indent=2)+'\n');print(rec(D/'GO.json'))
