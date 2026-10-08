from pathlib import Path
import hashlib,json
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-full256-prefix1081-source-v1-20261009';O=Path(__file__).resolve().parent
pin=lambda p:dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
reviews=[]
for name in ['crc-table-full256-prefix1081-source-review-root-20261009','crc-table-full256-prefix1081-source-review-independent-20261009']:
 p=W/name/'report.json';q=json.loads(p.read_text());assert q['status']=='PASS_SOURCE_ONLY_TC_FULL256_PREFIX1081_PAIRED2' and q['sourcePinsSHA256']==pin(D/'source-pins.json')['sha256'] and q['driverSHA256']==pin(D/'run.py')['sha256'];reviews.append(pin(p))
pr=json.loads((D/'preregistration.json').read_text());f=W/'crc-capture-popen-transfer-fixture-v2-actual-review-independent-20261009/report.json';assert json.loads(f.read_text())['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
assert not (D/'run-outputs').exists() and not (O/'root-go.json').exists()
g={'status':'ROOT_GO_TC_FULL256_PREFIX1081_PAIRED2_ONLY','maximumLoaderCalls':2,'outputRoot':str(D/'run-outputs'),'outerExecution':'require_escalated','noRetry':True,'TCEmitterExecutionAuthorized':False,'generatedWorkloadExecutionAuthorized':True,'timingAuthorized':False,'sha256':{n:pin(D/n)['sha256']for n in ['run.py','preregistration.json','source-pins.json','input-pins.json']},'sourceReviews':reviews,'memoryPolicyVersion':pr['memoryPolicyVersion'],'integrationFixtureProof':pin(f)}
(O/'root-go.json').write_text(json.dumps(g,indent=2)+'\n');print(pin(O/'root-go.json'))
