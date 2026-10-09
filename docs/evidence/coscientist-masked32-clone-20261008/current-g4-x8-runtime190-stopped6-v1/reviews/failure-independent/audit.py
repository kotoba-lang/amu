from pathlib import Path
import json,hashlib,stat,sys,importlib.util,copy
sys.dont_write_bytecode=True
D=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-g4-original19-runtime190-source-v1-20261009-root');S=D/'run-outputs';O=Path(__file__).resolve().parent
G=Path('/Users/junkawasaki/github/workspaces/codex/current-g4-x8-runtime190-go-root-20261009/root-go.json')
H=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();assert s==p.lstat();return dict(bytes=len(b),sha256=H(b))
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):return dict(path=str(p),**rec(p))
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');g=load(G)
def fullpins():
 for n,r in sp.items():assert rec(D/n)==r
 for n,r in ip.items():assert rec(n)==r
fullpins();assert len(sp)==18 and len(ip)==120 and sum(r['bytes']for r in ip.values())==9774015
assert rec(G)['sha256']=='2b77a8ff37b7fded56d12145ab95e03569f9f9f25e4c02b1dcb91e66177b9727'
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert rec(D/n)['sha256']==g[k]
for r in g['sourceReviews']:
 assert rec(r['path'])=={k:r[k]for k in ['bytes','sha256']};q=load(r['path']);assert q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
sys.path.insert(0,str(D));import run,runtime,artifact_admission
spec=importlib.util.spec_from_file_location('inert_saved_nativecall',D/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
run.go_header(g,pr,S);run.source_scope(pr);run.loader_protocol(pr)
a=load(S/'attempts.json');results=load(S/'results.json');t=load(S/'terminal.json');f=load(S/'failure.json');gen=load(S/'generated-pins.json')
assert len(a)==6 and len(results)==5 and len(gen)==6
assert t=={'loaderCalls':6,'allChildrenClosed':True,'failure':True} and f=={'error':"AssertionError('first failure preserved; no retry')",'loaderCalls':6,'noRetry':True}
assert not (S/'report.json').exists()
for p,r in gen.items():assert rec(p)==r
pinned={};decoded=[];totalSamples=0
for i,r in enumerate(a):
 c=pr['cases'][i];label=c['label'];assert r['index']==i+1 and r['label']==label and r['nativeArgv']==c['nativeArgv'] and r['environment']==pr['environment']
 assert r['state']=='terminal'and r['returncode']==0 and r['waitEntered']is True and r['waitUncertain']is False and r['signalingAuthorityRetired']is True and r['captureStopAcknowledged']is True and r['watchdogErrors']==[]
 seal=load(S/(label+'.admission.json'));assert seal['index']==i+1 and seal['label']==label and seal['nativeArgv']==c['nativeArgv'] and seal['rootGO']==ref(G) and seal['sourcePinsSHA256']==g['sourcePinsSHA256'] and seal['preregistrationSHA256']==g['preregistrationSHA256']
 for k in ['native','container','source']:
  assert seal[k]==c[k] and rec(c[k]['path'])=={x:c[k][x]for x in ['bytes','sha256']}
 payload,exports=run.container(Path(c['container']['path']).read_bytes());assert payload==Path(c['native']['path']).read_bytes() and (c['symbol'],c['offset'],c['arity'])in exports
 assert r['argv']==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd','3','--admission-sha',gen[str(S/(label+'.admission.json'))]['sha256'],'--',*c['nativeArgv']]
 for k,suffix in [('stdout','.stdout'),('stderr','.stderr'),('limitJournal','.limit-journal.jsonl'),('memoryJournal','.memory-journal.jsonl')]:
  p=S/(label+suffix);assert rec(p)==r[k];pinned[str(p)]=rec(p)
 out=(S/(label+'.stdout')).read_bytes();err=(S/(label+'.stderr')).read_bytes();q=runtime.qualify(out,err,c['expectedResult']);assert q==r['structuredReportObservation'] and q['arena17']==r['counterObservation']['values'];decoded.append(q)
 nc.resource_journal(S/(label+'.limit-journal.jsonl'),pr,c['nativeArgv'])
 o=r['controllerObservation'];cap=o['capture'];assert cap['hashes']=={k:r[k]for k in ['stdout','stderr']}and cap['stoppedWriter']is True and cap['completeRaw']is True and cap['dropped']=={'stdout':0,'stderr':0}and cap['EOF']=={'stdout':True,'stderr':True}and cap['errors']==[]
 assert o['directChildWait']=='closed0'and o['waitUncertain']is False and o['sampleReceiptPersistenceQualified']is True
 ev=o['controllerEvents'];assert ev.index('retire:before-watchdog-stop-and-wait')<ev.index('wait-enter') and 'group-operation'not in ev[ev.index('wait-enter')+1:]
 samples=[json.loads(x)for x in (S/(label+'.memory-journal.jsonl')).read_bytes().splitlines()];assert len(samples)==r['memorySamples']==o['sampleCount'];totalSamples+=len(samples);births={};times=[]
 for j,s in enumerate(samples):
  assert len(s)==4 and s[0]==j+1 and s[2]==r['pid'] and 1<=len(s[3])<=2;times.append(s[1]);assert sum(x[2]for x in s[3])<=4294967296
  for pid,birth,memory in s[3]:
   assert type(pid)is int and birth>0 and memory>=0 and births.get(pid,birth)==birth;births[pid]=birth
 assert times==sorted(times)
 if i<5:
  assert r['failure']is None and artifact_admission.accept_artifact_observation(o)is True and results[i]['label']==label and results[i]['report']==q and results[i]['returncode']==0
 else:
  assert r['failure']=='AssertionError()'and o['status']=='REFUSE'and o['semanticQualification']is False
  m=o['memoryAdmissionRecord'];assert m['failure']=={'contextVersion':'owned-group-sampling-failure-context-v1','typedOrigin':'fresh-owned-group-api-v1','stage':'member-getpgid','pid':16475,'queryOrdinal':21,'errno':3,'failureClass':'kernel-oserror'} and m['otherRefusals']==['failure-pid-not-previously-bound'] and 16475 not in births
  assert m['acceptedSamples']==2 and m['acceptedLeaderBirthBound']is True and m['groupOperationsAfterWait']==m['groupOperationsAfterUncertainty']==0
  try:artifact_admission.accept_artifact_observation(o)
  except AssertionError:pass
  else:raise AssertionError('refusal laundered')
for i in [0,2,4]:assert decoded[i]==decoded[i+1]
# Only two pairs admitted; third pair raw diagnostic equality does not close refused admission.
for c in pr['cases'][6:]:assert not any((S/(c['label']+s)).exists()for s in ['.stdout','.stderr','.admission.json','.limit-journal.jsonl','.memory-journal.jsonl'])
neg=[]
for name,b in [('empty',b''),('partial',(S/'aha-mont64-ON-n2.stdout').read_bytes()[:-1]),('extra',(S/'aha-mont64-ON-n2.stdout').read_bytes()+b'x')]:
 try:runtime.qualify(b,(S/'aha-mont64-ON-n2.stderr').read_bytes(),1)
 except AssertionError:neg.append(name)
 else:raise AssertionError(name)
for name,mut in [('semanticflag',lambda q:q.update(semanticQualification=True)),('status',lambda q:q.update(status='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP')),('strictflag',lambda q:q.update(strictOldMemoryPolicyPassed=True))]:
 q=copy.deepcopy(a[-1]['controllerObservation']);mut(q)
 try:artifact_admission.accept_artifact_observation(q)
 except AssertionError:neg.append(name)
 else:raise AssertionError(name)
fullpins()
report={'status':'PASS_INDEPENDENT_SAVED_CURRENT_G4_X8_RUNTIME190_FIRST_FAILURE_ONLY','sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'rootGO':ref(G),'sourceReviews':g['sourceReviews'],'sourceFiles':18,'inputFiles':120,'inputLogicalBytes':9774015,'attemptedRuntimeCalls':6,'closedRuntimeCalls':6,'allSixReturncodes':0,'admittedCalls':5,'completeAdmittedPairs':2,'rawEqualPairs':3,'unexecutedCalls':184,'campaignFailurePreserved':True,'noRetry':True,'terminal':ref(S/'terminal.json'),'failure':ref(S/'failure.json'),'attempts':ref(S/'attempts.json'),'results':ref(S/'results.json'),'generatedPins':ref(S/'generated-pins.json'),'savedRawPins':pinned,'sampleCount':totalSamples,'failedCase':{'label':a[-1]['label'],'controllerStatus':'REFUSE','failureContext':a[-1]['controllerObservation']['memoryAdmissionRecord']['failure'],'otherRefusals':['failure-pid-not-previously-bound'],'failedPIDAbsentFromAcceptedSamples':True,'rawResult':1,'rawFuelConsumed':1698,'all17ArenaParity':True,'rawResultFuelArenaEqualOFF':True,'semanticQualification':False},'pureNegativeControls':neg,'completedRuntime190Qualification':False,'full19FunctionalAdmissionPassed':False,'performanceQualified':False,'hardPeakQualified':False,'C2':False,'nativeOperationsDuringAudit':0,'scope':'Saved once-failure audit only. Raw n2 equality does not supersede refused sampling admission; no report.json completion exists and184 calls remain unexecuted.'}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rec(O/'report.json')))
