"""Mutable local SOURCE preparation only; no operational APIs, freeze or processes."""
from pathlib import Path
import hashlib,json,ast
D=Path(__file__).resolve().parent;W=D.parent;F=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-source-v2-receipt-binding';T=W/'vector-leaf-straight-read-cache-current19-timing-draft-v1';BUILD=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root'
ROOT='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-v1-root'
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);assert p.is_file()and not p.is_symlink();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def main():
 f=load(F/'preregistration.json');t=load(T/'preregistration-preview.json');prof=load(T/'readonly-profile-preview.json');entries=[]
 for c,e in zip(f['cases'],prof['entries']):
  assert c['workload']==e['workload']and c['n']==e['n']==e['matrixMaxN'];q=dict(c);q.update({k:e[k]for k in ['matrixMaxN','bodyCountPerCall','bodyMeaning','codeChanged']});entries.append(q)
 local=load(F/'input-pins.json');remote=load(F/'remote-input-pins.json');before=(len(local),sum(r['bytes']for r in local.values()),len(remote),sum(r['bytes']for r in remote.values()))
 # Retain full inherited banks unchanged, no historical result reads/pooling. Add
 # exact SOURCE references, including whole ordered lossless installed chunks.
 for folder in (T,F):
  for p in folder.iterdir():
   if p.is_file():r=ref(p);local[r.pop('path')]=r
 for n in ['collection-receipt.json','build52-acceptance.json','build52-independent-report.json']:(D/n).write_bytes((F/n).read_bytes())
 old=f['syntheticReceiptBinding']['remotePath'];r=remote.pop(old);assert r=={k:ref(D/'collection-receipt.json')[k]for k in ['bytes','sha256']};remote[ROOT+'/source/collection-receipt.json']=r
 role=load(F/'evidence-role-contract.json');role['syntheticReceiptBinding']['remotePath']=ROOT+'/source/collection-receipt.json';role['runtimeOutputBudget']=dict(bytesMaximum=805306368,runnerStreamBytesMaximum=16384,loadStreamBytesMaximum=1024,childReceiptBytesMaximum=16384,outputScope='Prospective explicit768MiB output cap separate from complete8192/448MiB input closure; all child raw/closures retained')
 save('evidence-role-contract.json',role);save('input-pins.json',local);save('remote-input-pins.json',remote)
 pr=dict(t);pr.update(status='MUTABLE_TIMING_SOURCE_AUTHORING_NOT_FROZEN_NO_GO',remoteRoot=ROOT,outputRoot=ROOT+'/timing',entries=entries,acceptedHostIdentity=load(BUILD/'collected/build52/identity-before.json'),finalSourceFreeze=False,operationalAdapterPresent=True,fresh285Acceptance=None,fresh285IndependentReview=None,expectedSemantics=None,maximumInputFiles=8192,maximumInputLogicalBytes=469762048,runtimeOutputBytesMaximum=805306368,loadQueryArgv=['/usr/sbin/sysctl','-n','vm.loadavg'],maximumLaunchTransportChildren=1,maximumCollectTransportChildren=1,retries=0,firstFailureStop=True,compilerCalls=0)
 save('preregistration.json',pr)
 bindings={'source-pins.json':'sourcePinsSHA256','timing.py':'driverSHA256','launch.py':'launchSHA256','preregistration.json':'preregistrationSHA256','input-pins.json':'inputPinsSHA256','remote-input-pins.json':'remoteInputPinsSHA256','fresh285-binding.json':'fresh285BindingSHA256','expected-semantics.json':'expectedSemanticsSHA256'}
 fixed=dict(status='ROOT_GO_LC_CURRENT19_TIMING_SOURCE_V1_ONLY',authorized=True,destination=f['destination'],buildRoot=f['buildRoot'],remoteRoot=ROOT,outputRoot=ROOT+'/timing',maximumRunnerChildren=5415,maximumLoadChildren=10830,maximumChildren=16245,maximumLaunchTransportChildren=1,timingAuthorized=True,functionalAuthorized=False,compilerAuthorized=False,noRetry=True)
 save('go-schema.json',dict(exactLocalFields=sorted([*fixed,*bindings.values(),'sourceReviews']),fixedFields=fixed,hashBindings=bindings,sourceReviewStatus='PASS_SOURCE_LC_CURRENT19_TIMING_SOURCE_V1'))
 for p in D.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
 report=dict(status='PREPARED_MUTABLE_SOURCE_HOLD_FRESH285_PROOF',localFiles=len(local),localBytes=sum(v['bytes']for v in local.values()),remoteFiles=len(remote),remoteBytes=sum(v['bytes']for v in remote.values()),inheritedBankCounts=before,allInheritedLocalOriginsRetained=True,allInstalled3592MembersAndLosslessChunksRetained=True,nativeCompilerSSHGuestCalls=0,finalFreeze=False,remaining=['independently accepted actual fresh285 full proof/raw closure','derive exact nmax 14field-minus4 semantic map from accepted actual comparisons','add proof inputs preserving full closure budget','freeze exact source manifest then two independent SOURCE reviews then root GO'])
 assert len(local)<=8192 and report['localBytes']<=469762048 and len(remote)<=8192 and report['remoteBytes']<=469762048
 save('authoring-report.json',report);save('mutable-inventory.json',dict(status='MUTABLE_INVENTORY_NOT_SOURCE_PINS',files=[ref(p)for p in sorted(D.iterdir())if p.is_file()and p.name!='mutable-inventory.json']))
 print(json.dumps(report))
if __name__=='__main__':main()
