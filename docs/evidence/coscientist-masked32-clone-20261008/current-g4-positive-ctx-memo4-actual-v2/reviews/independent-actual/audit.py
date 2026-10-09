from pathlib import Path
import json,hashlib,sys,importlib.util,copy
D=Path('/Users/junkawasaki/github/workspaces/codex/native-ctx-positive-memo4-source-v2-20261009-independent');O=D/'run-outputs';R=Path(__file__).parent;G=D.parent/'native-ctx-positive-memo4-go-root-20261009/root-go.json'
H=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):
 p=Path(p);s=p.lstat();assert p.is_file()and not p.is_symlink();b=p.read_bytes();t=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns);return dict(path=str(p),bytes=len(b),sha256=H(b))
def load(p):return json.loads(Path(p).read_bytes())
def pin(p,r):assert {k:rec(p)[k]for k in ('bytes','sha256')}=={k:r[k]for k in ('bytes','sha256')}
sys.path.insert(0,str(D));from run import container
from artifact_admission import accept_artifact_observation
from producer_guard import validate_producer
from compiler_output import parse_output
from runtime import counters
spec=importlib.util.spec_from_file_location('saved_native_call',D/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
p=load(D/'preregistration.json');g=load(G);sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]
assert g['maximumLoaderCalls']==4 and not g['C2']and not g['runtimeGuestAuthorized']and not g['timingAuthorized']and g['noRetry']
for rr in g['sourceReviews']:
 pin(rr['path'],rr);q=load(rr['path']);assert q['status']==p['sourceReviewStatus'];assert all(q[k]==g[k]for k in ('sourcePinsSHA256','preregistrationSHA256','driverSHA256'))
for n,v in sp.items():pin(D/n,v)
for n,v in ip.items():pin(n,v)
assert len(ip)==p['exactInputFiles'] and sum(r['bytes']for r in ip.values())==p['exactInputLogicalBytes']
for n,v in load(O/'generated-pins.json').items():pin(n,v)
a=load(O/'attempts.json');res=load(O/'results.json');report=load(O/'report.json');assert len(a)==len(res)==4 and report['calls']==4
assert load(O/'terminal.json')=={'calls':4,'closed':True,'failure':False}
for n,r in report['evidence'].items():pin(O/n,r)
assert report['rootGO']==rec(G)and report['sourcePinsSHA256']==g['sourcePinsSHA256']and report['results']==res
validate_producer(p,rec(G),g['sourcePinsSHA256'],g['preregistrationSHA256'])
assert load(O/'memo-producer-evidence.json')==a[:2]
out=[];samples=0;peaks=[]
for i,(c,row,result)in enumerate(zip(p['cases'],a,res),1):
 assert row['index']==i and row['label']==c['label'] and row['nativeArgv']==c['nativeArgv']and row['environment']==p['environment']
 assert row['state']=='terminal'and row['returncode']==0 and row['waitEntered']is True and row['waitUncertain']is False and row['signalingAuthorityRetired']is True and row['captureStopAcknowledged']is True and row['failure']is None and row['watchdogErrors']==[]
 sealPath=O/(c['label']+'.admission.json');seal=load(sealPath);assert seal['rootGO']==rec(G)and seal['nativeArgv']==c['nativeArgv']and seal['index']==i and seal['outputPath']==c['outputPath']and row['argv'][5]==rec(sealPath)['sha256']
 for k in ('producer','producerContainer','input'):pin(seal[k]['path'],seal[k])
 co=row['controllerObservation'];assert accept_artifact_observation(co)
 raw={}
 for k,cap in [('stdout',8388608),('stderr',1048576),('limitJournal',65536),('memoryJournal',16777216)]:
  suffix={'limitJournal':'.limit-journal.jsonl','memoryJournal':'.memory-journal.jsonl'}.get(k,'.'+k);f=O/(c['label']+suffix);pin(f,row[k]);assert f.stat().st_size<=cap;raw[k]=f.read_bytes()
 assert parse_output(raw['stdout'],c)==row['structuredReportObservation']==result['report']
 assert counters(raw['stderr'])==row['counterObservation']and len(row['counterObservation']['values'])==17
 assert co['capture']['completeRaw']and co['capture']['EOF']=={'stdout':True,'stderr':True}and co['capture']['dropped']=={'stdout':0,'stderr':0}and co['capture']['errors']==[]
 for k in ('stdout','stderr'):assert co['capture']['hashes'][k]==row[k]
 nc.resource_journal(O/(c['label']+'.limit-journal.jsonl'),p,c['nativeArgv'])
 ms=[json.loads(x)for x in raw['memoryJournal'].splitlines()];assert len(ms)==row['memorySamples']==co['sampleCount']==co['memoryAdmissionRecord']['acceptedSamples']and len(ms)>0
 births={};prev=0;peak=0
 for ordinal,tick,leader,members in ms:
  assert ordinal>0 and tick>prev and leader==row['pid']and 1<=len(members)<=2;prev=tick
  assert len({x[0]for x in members})==len(members)and leader in {x[0]for x in members}
  for pid,birth,footprint in members:
   assert pid>0 and birth>0 and type(footprint)is int and footprint>=0
   assert pid not in births or births[pid]==birth;births[pid]=birth
  total=sum(x[2]for x in members);assert total<=4294967296;peak=max(peak,total)
 assert [x[0]for x in ms]==list(range(1,len(ms)+1));samples+=len(ms);peaks.append(peak)
 assert result['memoryObservation']==co['memoryObservation']and result['strictOldMemoryPolicyPassed']==co['strictOldMemoryPolicyPassed']
 if i==1:
  assert not co['strictOldMemoryPolicyPassed']and co['memoryObservation']['missingFootprint']is None and co['memoryObservation']['zeroSynthesized']is False
 else:assert co['strictOldMemoryPolicyPassed']and co['memoryAdmissionRecord']['failure']is None
 pin(c['outputPath'],result['artifact']);out.append({'label':c['label'],'artifact':rec(c['outputPath']),'samples':len(ms),'observedMaximumAggregateFootprintBytes':peak,'strictOldMemoryPolicyPassed':co['strictOldMemoryPolicyPassed'],'memoryObservation':co['memoryObservation'],'arenaCounters':row['counterObservation']['values']})
blob,exports=container((O/'memo.kseed').read_bytes());assert exports==[('main',0,0)]and blob==(O/'memo.bin').read_bytes()
for e in p['entries']:
 new=O/(e['workload']+'.kseed');assert new.read_bytes()==Path(e['container']['path']).read_bytes();payload,exports=container(new.read_bytes());assert payload==Path(e['native']['path']).read_bytes()and exports==[tuple(x)for x in e['exports']]
 assert (O/(e['workload']+'.kotoba')).read_bytes()==Path(e['source']['path']).read_bytes()
assert (O/'unity-memo.kotoba').read_bytes()==(D/'unity-memo.kotoba').read_bytes()
# Saved-evidence negatives: row closure, gap classification and payload identity must refuse.
negative=[]
for label,mut in [('gap-zero-footprint',lambda z:z['memoryObservation'].update(missingFootprint=0)),('unknown-refusal',lambda z:z['memoryAdmissionRecord'].update(otherRefusals=['unknown'])),('post-wait-query',lambda z:z['memoryAdmissionRecord'].update(groupOperationsAfterWait=1))]:
 z=copy.deepcopy(a[0]['controllerObservation']);mut(z)
 try:accept_artifact_observation(z)
 except AssertionError:negative.append(label)
 else:raise AssertionError(label)
for n,v in sp.items():pin(D/n,v)
for n,v in ip.items():pin(n,v)
q={'status':'PASS_INDEPENDENT_SAVED_CURRENT_G4_POSITIVE_CTX_MEMO4_WHOLE_ARTIFACT_IDENTITY_ONLY','subject':str(D),'sourcePinsSHA256':g['sourcePinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'completion':rec(O/'report.json'),'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'sourceFiles':len(sp),'inputFiles':len(ip),'inputLogicalBytes':sum(x['bytes']for x in ip.values()),'closedCompilerCalls':4,'directWaitClosed0':4,'acceptedFiniteSamples':samples,'strictOldMemoryCalls':3,'retainedTypedTerminationGapCalls':1,'results':out,'memoNative':rec(O/'memo.bin'),'memoContainer':rec(O/'memo.kseed'),'wholeOrdinaryWorkloadContainerParity':True,'fullNativePayloadAndOwnExportsParity':True,'scratchAdditionalWords':128,'capacityQualification':'Native normal compilation and whole outputs support sufficient owned allocation for these fixed successful commands under pinned mem-fits. No exact live heap top observed; old-capacity/general allocation equivalence remains false.','savedNegativeControls':negative,'reviewerAuthorshipDisclosure':'Reviewer authored underlying bound-hoist and memo4 SOURCE independent review; did not author memo query algorithm/registration or execute campaign. This is saved evidence audit, not a second independent source authorship certificate.','limits':['First build retains typed member-getpgid ESRCH termination gap; missing footprint null, strict old refusal, no synthesized zero or hard peak claim.','Other three have finite strict samples only; no universal atomic census or process/OS closure proof.','Compiler fuel off; 17 compiler counters parsed, no baseline compiler counter or fuel equality claimed.','No actual memo hit/miss/avoided-work count, runtime guest, timing, general effect certificate, full19/fixedpoint or adoption qualification.'],'actualNativeGuestNetworkCallsByAuditor':0,'C2':False,'performanceQualified':False,'adoptionQualified':False}
(R/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
