"""Prospective V2 authoring: saved evidence only, no child/native/SSH execution."""
from pathlib import Path
import hashlib,json,ast
D=Path(__file__).resolve().parent;W=D.parent;V=W/'vector-leaf-straight-read-cache-current19-timing-source-v1';G=W/'vector-leaf-straight-read-cache-current19-timing-go-v1-root';A=W/'vector-leaf-straight-read-cache-current19-timing-actual-review-v1-independent';X=W/'vector-leaf-straight-read-cache-current19-timing-v1-failure-diagnosis'
NEW='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-v2-root'
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);assert p.is_file()and not p.is_symlink();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def main():
 failure=ref(A/'failure-report.json');acceptance=ref(G/'failure-acceptance.json')
 assert failure['sha256']=='b66c32e6ee345111e12a47e32df8d71279d015c64288a9c643263d8a97a7f9eb'
 assert acceptance['sha256']=='cfef92e03c69d4b009f0c17bffe0504c1ced384271fa54e42a0ef19bd4de3ee5'
 f=load(failure['path']);ac=load(acceptance['path']);assert f['allRemoteChildrenClosed']is True and f['remoteChildren']==14 and f['runnerChildren']==5 and f['loadChildren']==9 and f['failedRunnerReturncode']==-25 and f['acceptedPairedTriples']==0 and f['timingQualified']is False
 assert ac['independentReview']==failure
 local=load(D/'input-pins.json');remote=load(D/'remote-input-pins.json')
 for folder in [V,G,A,X]:
  for p in folder.rglob('*'):
   if p.is_file()and '__pycache__'not in p.parts:r=ref(p);local[r.pop('path')]=r
 # V1 package SOURCE and exact control/raw/envelope data are actual remote files.
 receipt=load(G/'collected/collection-receipt.json')
 for m in receipt['members']:
  p=G/'collected'/m['path'];r=ref(p);assert {k:r[k]for k in ['bytes','sha256']}=={k:m[k]for k in ['bytes','sha256']};remote[receipt['root']+'/'+m['path']]={k:m[k]for k in ['bytes','sha256']}
 # Top-level receipt is collector-generated, never an old remote filesystem member.
 for filename,path in [('prior-v1-failure-report.json',failure['path']),('prior-v1-failure-acceptance.json',acceptance['path']),('prior-v1-collection-receipt.json',G/'collected/collection-receipt.json'),('prior-v1-diagnosis.json',X/'report.json')]: (D/filename).write_bytes(Path(path).read_bytes())
 remote[NEW+'/source/prior-v1-collection-receipt.json']={k:ref(D/'prior-v1-collection-receipt.json')[k]for k in ['bytes','sha256']}
 binding=dict(status='PRESERVED_INDEPENDENTLY_ACCEPTED_V1_TIMING_FAILURE_NO_RETRY',acceptance=acceptance,independentFailureReview=failure,priorSourcePinsSHA256=f['sourcePinsSHA256'],priorLocalGOSHA256=f['localGOSHA256'],priorRemoteGOSHA256=f['remoteGOSHA256'],launchChildren=1,remoteChildren=14,runnerChildren=5,loadChildren=9,allClosed=True,measuredTriples=0,acceptedTriples=0,timingQualified=False,noRetry=True,signal25Observed=True,exactWriteOriginTraced=False,fullCollectedRegularMembers=88,fullCollectedMemberBytes=7108183,sourceHypothesis=ref(X/'report.json'))
 save('prior-v1-failure-binding.json',binding);save('input-pins.json',local);save('remote-input-pins.json',remote)
 p=load(D/'preregistration.json');p.update(status='PROSPECTIVE_LC_TIMING_V2_BOUNDED_PIPES_PRIOR_FAILURE_BOUND_NO_GO',priorTimingFailureBinding=ref(D/'prior-v1-failure-binding.json'),localClosureFiles=len(local),localClosureBytes=sum(r['bytes']for r in local.values()),remoteClosureFiles=len(remote),remoteClosureBytes=sum(r['bytes']for r in remote.values()),maximumCumulativeTimingChildren=16259,maximumCumulativeRunnerChildren=5420,maximumCumulativeLoadChildren=10839,maximumCumulativeLaunchChildren=2,sourceAuthorNativeCompilerSSHCalls=0)
 assert len(local)<=8192 and len(remote)<=8192 and p['localClosureBytes']<=469762048 and p['remoteClosureBytes']<=469762048
 save('preregistration.json',p);g=load(D/'go-schema.json');g['hashBindings']['prior-v1-failure-binding.json']='priorFailureBindingSHA256';g['fixedFields'].update(priorTimingFailedLaunches=1,priorTimingChildren=14,priorTimingRunnerChildren=5,priorTimingLoadChildren=9,maximumCumulativeTimingChildren=16259,maximumCumulativeRunnerChildren=5420,maximumCumulativeLoadChildren=10839,maximumCumulativeLaunchChildren=2);g['exactLocalFields']=sorted([*g['fixedFields'],*g['hashBindings'].values(),'sourceReviews']);save('go-schema.json',g)
 role=load(D/'evidence-role-contract.json');role.update(V1FailureBinding=binding,V1FailureRemoteOrigins='Only actual receipt.members mapped to old installed V1 root. Local launch/archive/reviewer source/proofs retain full local refs, never guessed remote origins.',V1SyntheticReceiptSource=dict(originalLocal=ref(G/'collected/collection-receipt.json'),remoteSource=NEW+'/source/prior-v1-collection-receipt.json',role='Full byte-identical SOURCE proof, no invalid oldremote receiptpathname'),regularFileLimit=dict(bytesMaximum=16777216,perStreamCaptureLimitsUnchanged=True,reason='Unchanged consumer materializes embedded C image up to83640B before dlopen; file RLIMIT is global. Cap is orchestration resource bound, no language/fuel/arena/body change.'),temporaryCImages=p['temporaryCImageRole']);save('evidence-role-contract.json',role)
 for p in D.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
 print(json.dumps(dict(localFiles=len(local),localBytes=sum(r['bytes']for r in local.values()),remoteFiles=len(remote),remoteBytes=sum(r['bytes']for r in remote.values()),priorFailureAccepted=True,finalFreeze=False,operationalCalls=0)))
if __name__=='__main__':main()
