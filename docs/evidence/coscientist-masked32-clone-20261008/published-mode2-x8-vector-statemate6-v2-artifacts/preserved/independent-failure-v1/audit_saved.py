from pathlib import Path
import json,hashlib,stat,sys,importlib.util
D=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-vector-statemate6-source-v1-20261009');S=D/'run-outputs';O=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();assert s.st_size==len(b);return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pin(p,r):
 a=rec(p);assert all(a[k]==r[k]for k in ['bytes','sha256']);return a
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
G=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-vector-statemate6-go-v1-root-20261009/root-go.json');go=json.loads(G.read_bytes())
import run
assert run.go_header(go,pr,S)
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert rec(D/n)['sha256']==go[k]
assert len(go['sourceReviews'])==2 and len(set(r['path']for r in go['sourceReviews']))==2
for r in go['sourceReviews']:
 pin(r['path'],r);q=json.loads(Path(r['path']).read_bytes());assert q['status']==pr['sourceReviewStatus']and all(q[k]==go[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
for k in ['integrationFixtureProof','baselineActualProof','TCActualProof','candidateActualProof']:pin(go[k]['path'],go[k]);assert go[k]==pr['qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k]
assert run.source_scope(pr,ip)
a=json.loads((S/'attempts.json').read_bytes());assert len(a)==1;r=a[0];c=pr['cases'][0];assert r['nativeArgv']==c['nativeArgv']and r['environment']==pr['environment']and r['index']==1 and r['label']==c['label']
assert r['state']=='terminal'and r['returncode']==125 and r['waitEntered']and not r['waitUncertain']and r['signalingAuthorityRetired']and r['captureStopAcknowledged']and not r['watchdogErrors']
for n,k in [('OFF-vector-compile.limit-journal.jsonl','limitJournal'),('OFF-vector-compile.memory-journal.jsonl','memoryJournal'),('OFF-vector-compile.stdout','stdout'),('OFF-vector-compile.stderr','stderr')]:pin(S/n,r[k])
sealPath=S/'OFF-vector-compile.admission.json';seal=json.loads(sealPath.read_bytes());assert r['argv'][:6]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd','3','--admission-sha',rec(sealPath)['sha256']]and r['argv'][6:]==['--',*c['nativeArgv']]
assert seal['rootGO']==rec(G)and seal['nativeArgv']==c['nativeArgv']and seal['input']['sha256']==pr['fixtureSource']['sha256'];pin(seal['input']['path'],seal['input'])
spec=importlib.util.spec_from_file_location('audit_resource',D/'native-call.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert m.resource_journal(S/'OFF-vector-compile.limit-journal.jsonl',pr,c['nativeArgv'])
j=[json.loads(x)for x in (S/'OFF-vector-compile.memory-journal.jsonl').read_bytes().splitlines()];assert len(j)==r['memorySamples']==3
births={};samples=[]
for i,q in enumerate(j,1):
 assert q[0]==i and q[2]==r['pid']and 1<=len(q[3])<=2
 for pid,birth,foot in q[3]:assert birth>0 and foot>=0 and (pid not in births or births[pid]==birth);births[pid]=birth
 assert any(x[0]==r['pid']for x in q[3]);samples.append(dict(index=i,members=len(q[3]),sumFootprintBytes=sum(x[2]for x in q[3])))
obs=r['controllerObservation'];cap=obs['capture'];assert cap['completeRaw']and cap['stoppedWriter']and cap['EOF']==dict(stdout=True,stderr=True)and cap['dropped']==dict(stdout=0,stderr=0)and not cap['errors']
assert obs['status']=='REFUSE'and not obs['semanticQualification'];adm=obs['memoryAdmissionRecord'];assert adm['failure']is None and adm['groupOperationsAfterWait']==adm['groupOperationsAfterUncertainty']==0
err=(S/'OFF-vector-compile.stderr').read_bytes();out=(S/'OFF-vector-compile.stdout').read_bytes();assert not out and err.startswith(b'sandbox initialization failed: Operation not permitted\nkexe-loader: sandbox_init: Operation not permitted\n')
from runtime import counters
assert counters(err)['status']=='unavailable-or-invalid';tail=err[err.index(b'KEXE_ARENA_USE'):];decoded=counters(tail);assert decoded['status']=='valid'and set(decoded['values'].values())=={0}
assert json.loads((S/'terminal.json').read_bytes())==dict(loaderCalls=1,allChildrenClosed=True,failure=True)
assert json.loads((S/'failure.json').read_bytes())['noRetry']is True
assert not any((S/n).exists()for n in ['report.json','results.json','artifacts.json',*([Path(c['outputPath']).name for c in pr['cases']])])
for p,rp in json.loads((S/'generated-pins.json').read_bytes()).items():pin(p,rp)
loaderSource=Path('/Users/junkawasaki/github/workspaces/codex/vector-masked32-source-bound-loader-build-plan-v2-native-controls/kexe_loader.c');primary=Path('/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c');assert loaderSource.read_bytes()==primary.read_bytes();ls=loaderSource.read_text();assert ls.index('install_syscall_sandbox();',ls.index('int main'))<ls.index('result = fn(',ls.index('int main'))
report={'status':'PASS_INDEPENDENT_SAVED_FAILURE_PUBLISHED_MODE2_X8_VECTOR_STATEMATE6_V1_ONLY','independent':True,'priorImplementationAuthorship':False,'subject':str(D),'sourcePinsSHA256':go['sourcePinsSHA256'],'inputPinsSHA256':go['inputPinsSHA256'],'driverSHA256':go['driverSHA256'],'preregistrationSHA256':go['preregistrationSHA256'],'rootGO':rec(G),'sourceReviews':go['sourceReviews'],'verifiedClosure':dict(sourceFiles=len(sp),inputFiles=len(ip),inputLogicalBytes=sum(x['bytes']for x in ip.values())),'attempts':1,'directWaitReturncode':125,'capture':cap,'resourceJournalIndependentlyDecoded':True,'memorySamples':samples,'retainedControllerObservation':obs,'stderr':rec(S/'OFF-vector-compile.stderr'),'stdout':rec(S/'OFF-vector-compile.stdout'),'zeroArenaTail':decoded,'loaderPrimarySource':rec(loaderSource),'sourceTrace':{'sandboxFailureExit':'sandbox_init nonzero -> _exit(125), tools/kexe_loader.c lines12433-12442','ordering':'install_limits then install_syscall_sandbox line12991, before guest fn invocation lines13035/13039'},'conclusion':'Original compiler6 campaign FAIL preserved. First OFF loader sandbox initialization failed EPERM and exited125 before guest compiler invocation by exact source-order trace; stdout empty and no generated artifact. Remaining five calls unexecuted. This is not candidate product rejection or semantic evidence.','rootOrchestrationDisclosure':'Parent reports using the default outer execution sandbox in error; that orchestration choice is attributed to root, not reconstructed from stderr as a kernel-cause proof. Loader own sandbox policy is unchanged. No saved external syscall trace or outer sandbox receipt independently proves causality.','closureLimits':'Saved direct loader/wrapper wait125 is closed; observed loader-forked member57325 exists in final sample. No separately witnessed wait for that member is asserted. allChildrenClosed is driver direct-child census, not universal descendant closure.','noRetry':True,'originalCompletionAbsent':True,'unexecutedCases':[x['label']for x in pr['cases'][1:]],'qualification':dict(campaignSuccess=False,artifactIdentity=False,guestCorrectness=False,memoryAdmission=False,hardPeak=False,performance=False,emittedClobberCertificate=False),'operationalCalls':0,'subjectEdits':False,'savedEvidence':{p.name:rec(p)for p in S.iterdir()if p.is_file()}}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');rr=rec(O/'report.json');print(json.dumps(rr))
