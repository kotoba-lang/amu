from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-vector-statemate6-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
a=json.loads((O/'attempts.json').read_bytes());t=json.loads((O/'terminal.json').read_bytes());assert len(a)==1 and a[0]['state']=='terminal'and a[0]['returncode']==125 and not a[0]['waitUncertain']and t=={'loaderCalls':1,'allChildrenClosed':True,'failure':True}
assert not (O/'report.json').exists()and not (O/'off-vector.kseed').exists()
s=(O/'OFF-vector-compile.stderr').read_text();assert 'sandbox_init: Operation not permitted'in s and ':pairs 0'in s and ':heap-bytes 0'in s
q=dict(status='FAIL_ONCE1_CLOSED125_LOADER_SANDBOX_INIT_BEFORE_GUEST',rootOrchestrationError='Default outer tool sandbox prevented existing loader sandbox_init. Required host escalation was omitted.',originalCampaignPreserved=True,nativeCalls=1,compilerBodyExecuted=False,allChildrenClosed=True,retries=0,performanceQualified=False,C2=False,evidence=[r(p)for p in sorted(O.iterdir())if p.is_file()])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(r(D/'report.json'))
p=W/'compute-address-continuation-20261008-root/checkpoint.json';c=json.loads(p.read_bytes());c['currentPublishedX8VectorStatemate6']={'source':str(S),'state':q['status'],'rootFailureProof':str(D/'report.json'),'nativeCalls':1,'retry':False,'noLiveProcess':True,'next':'Separate V2 with host-authorized escalation; preserve loader sandbox.'};c['noLiveProcess']=True;p.write_text(json.dumps(c,indent=2)+'\n')
