from pathlib import Path
import json,hashlib,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-hft-compose511-bound-hoist-original-ns-runtime10-source-v2-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
I=W/'tc-hft-compose511-bound-hoist-runtime10-v2-actual-failure-review-independent-20261009-dense/report.json';ind=load(I)
for p,r in ind['checkedRegularPins'].items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
sys.path.insert(0,str(S));import runtime
p=load(S/'preregistration.json');a=load(O/'attempts.json');rs=load(O/'results.json');assert len(a)==7 and len(rs)==6
assert load(O/'terminal.json')==dict(loaderCalls=7,allChildrenClosed=True,failure=True) and not (O/'report.json').exists()
dec=[];rows=0
for i,x in enumerate(a):
 c=p['cases'][i];assert x['label']==c['label'] and x['nativeArgv']==c['nativeArgv'] and x['environment']==p['environment'] and x['state']=='terminal' and x['returncode']==0 and x['waitEntered'] and not x['waitUncertain'] and x['captureStopAcknowledged'] and x['signalingAuthorityRetired']
 for n in ['stdout','stderr']:assert rec(O/(x['label']+'.'+n))==x[n]
 q=runtime.qualify((O/(x['label']+'.stdout')).read_bytes(),(O/(x['label']+'.stderr')).read_bytes(),c['expectedResult']);dec.append(q)
 if i<6:assert q==rs[i]['report'] and x['controllerObservation']['semanticQualification'] and x['controllerObservation']['strictOldMemoryPolicyPassed']
 mem=[json.loads(l)for l in (O/(x['label']+'.memory-journal.jsonl')).read_bytes().splitlines()];assert len(mem)==x['memorySamples'];rows+=len(mem)
 if i==6:assert all(all(z[0]!=61254 for z in y[3])for y in mem)
for i in [0,2,4]:assert dec[i]==dec[i+1]
f=a[-1]['controllerObservation']['memoryAdmissionRecord'];assert f['failure']==dict(contextVersion='owned-group-sampling-failure-context-v1',typedOrigin='fresh-owned-group-api-v1',stage='member-getpgid',pid=61254,queryOrdinal=21,errno=3,failureClass='kernel-oserror') and f['otherRefusals']==['failure-pid-not-previously-bound'] and not a[-1]['controllerObservation']['semanticQualification']
assert rows==20
q=dict(status='PASS_ROOT_SAVED_FAILURE_HFT_COMPOSE511_BOUND_HOIST_RUNTIME10_V2_ONLY',independentAudit=dict(path=str(I),**rec(I)),verifiedPins=len(ind['checkedRegularPins']),runtimeCalls=7,closed0=7,admittedCalls=6,admittedPairs=3,admittedProfiles=[0,1,2],fuel=[dec[i]['fuelConsumed']for i in [0,2,4]],all17ArenaEqual=True,finiteSamples=20,refusedCase='nsichneu-OFF-n17',unknownPID=61254,rawOFF17ConditionalOnly=True,remainingUnexecuted=[x['label']for x in p['cases'][7:]],noRetry=True,fullFivePairQualified=False,performanceQualified=False,C2=False)
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],report=rec(D/'report.json'))))
