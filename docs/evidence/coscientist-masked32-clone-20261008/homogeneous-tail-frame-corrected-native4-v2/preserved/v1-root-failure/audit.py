from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-native4-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
a=json.loads((O/'attempts.json').read_bytes());t=json.loads((O/'terminal.json').read_bytes());assert len(a)==1 and a[0]['state']=='terminal'and a[0]['returncode']==1 and not a[0]['waitUncertain']and t=={'calls':1,'closed':True,'failure':True}
assert not (O/'report.json').exists();s=(O/'G1-compile.stderr').read_text();assert "E2101 unknown or unsupported form 'enc-mov'"in s
q=dict(status='FAIL_HFT_NATIVE4_ONCE1_CLOSED1_UNKNOWN_ENCODER_NAME_BEFORE_ARTIFACT',rootAndIndependentSourceReviewMiss='enc-mov absent; primary encoder name is enc-mov-r.',originalFailurePreserved=True,retries=0,nativeCalls=1,remainingNativeCallsUnexecuted=3,compilerSourceExecuted=True,guestWorkloadExecuted=False,strictPolicyRefuseRetained=True,nativeCandidateProduced=False,C2=False,performanceQualified=False,evidence=[r(p)for p in sorted(O.iterdir())if p.is_file()]);(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(r(D/'report.json'))
p=W/'compute-address-continuation-20261008-root/checkpoint.json';c=json.loads(p.read_bytes());c['currentHomogeneousFrameCandidate']['native4State']=q['status'];c['currentHomogeneousFrameCandidate']['native4RootFailureProof']=str(D/'report.json');c['currentHomogeneousFrameCandidate']['native4Calls']=1;c['currentHomogeneousFrameCandidate']['next']='Separate V3 candidate + V2native4 registration with correct encoder heads; original failure preserved.';c['noLiveProcess']=True;p.write_text(json.dumps(c,indent=2)+'\n')
