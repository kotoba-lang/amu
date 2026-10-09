from pathlib import Path
import json,hashlib,sys,copy
D=Path('/Users/junkawasaki/github/workspaces/codex/native-ctx-query-observer4-source-v2-20261009-independent');O=D/'run-outputs';A=Path(__file__).resolve().parent
sys.path.insert(0,str(D));from compiler_output import parse_output
from runtime import counters
from artifact_admission import accept_artifact_observation
from producer_guard import validate_producer
from run import container
checked={}
def rec(p):
 p=Path(p);a=p.stat();b=p.read_bytes();z=p.stat();assert p.is_file()and not p.is_symlink()and (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 r={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};checked[str(p)]=r;return r
def check(p,r):v=rec(p);assert all(v[k]==r[k]for k in('bytes','sha256'));return Path(p).read_bytes()
def registries():
 sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text())
 for tab,rel in[(sp,True),(ip,False)]:
  for p,r in tab.items():check(D/p if rel else p,r)
 return sp,ip
sp,ip=registries();pr=json.loads((D/'preregistration.json').read_text());report=json.loads((O/'report.json').read_text());term=json.loads(check(O/'terminal.json',report['evidence']['terminal.json']));assert term=={'calls':4,'closed':True,'failure':False};assert report['calls']==4 and report['status']=='COMPLETE_CURRENT_G4_CTX_QUERY_OBSERVER4_ARTIFACT_AND_BOUNDED_TRACE_ONLY'
for n,r in report['evidence'].items():check(O/n,r)
rows=json.loads((O/'attempts.json').read_text());assert len(rows)==4
seal0=json.loads((O/'observer-build.admission.json').read_text());go=seal0['rootGO'];g=json.loads(check(go['path'],go));assert g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==4 and g['runtimeGuestAuthorized']is False and g['timingAuthorized']is False and g['C2']is False
assert g['sourcePinsSHA256']==rec(D/'source-pins.json')['sha256']and g['preregistrationSHA256']==rec(D/'preregistration.json')['sha256']and g['driverSHA256']==rec(D/'run.py')['sha256']
for r in g['sourceReviews']:
 q=json.loads(check(r['path'],r));assert q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in('sourcePinsSHA256','driverSHA256','preregistrationSHA256'))
assert len({r['path']for r in g['sourceReviews']})==2
out=[];samplesTotal=0;strictTotal=0
for i,(r,c,result)in enumerate(zip(rows,pr['cases'],report['results']),1):
 assert r['index']==i and r['label']==c['label']and r['nativeArgv']==c['nativeArgv']and r['environment']==pr['environment']
 assert r['state']=='terminal'and r['returncode']==0 and r['waitEntered']is True and r['waitUncertain']is False and r['failure']is None and r['signalingAuthorityRetired']is True and r['captureStopAcknowledged']is True and r['watchdogErrors']==[]
 sealPath=O/(c['label']+'.admission.json');seal=json.loads(rec(sealPath)and sealPath.read_bytes());assert seal['rootGO']==go and seal['index']==i and seal['label']==c['label']and seal['nativeArgv']==c['nativeArgv']and seal['sourcePinsSHA256']==g['sourcePinsSHA256']and seal['preregistrationSHA256']==g['preregistrationSHA256']
 assert r['argv'][5]==rec(sealPath)['sha256']
 for k in('producer','producerContainer','input'):check(seal[k]['path'],seal[k])
 obs=r['controllerObservation'];assert accept_artifact_observation(obs) and obs['capture']['stoppedWriter']is True and obs['capture']['completeRaw']is True and all(obs['capture']['EOF'].values())and not any(obs['capture']['dropped'].values())and obs['capture']['errors']==[]
 stdout=check(O/(c['label']+'.stdout'),r['stdout']);stderr=check(O/(c['label']+'.stderr'),r['stderr'])
 for name in('stdout','stderr'):assert obs['capture']['hashes'][name]=={k:r[name][k]for k in('bytes','sha256')}
 decoded=parse_output(stdout,c);assert decoded==result['report'];counter=counters(stderr);assert counter['status']=='valid'and counter==r['counterObservation']
 jr=json.loads if False else None
 limitRaw=check(O/(c['label']+'.limit-journal.jsonl'),r['limitJournal']);limit=[json.loads(x)for x in limitRaw.splitlines()];assert len(limit)==6
 assert limit[0]['nativeExecEnvironmentExact']is True and limit[0]['changedExpectedKeyNames']==limit[0]['missingKeyNames']==[]and set(limit[0]['nativeExecKeyNames'])==set(pr['environment'])
 assert limit[2]['readback']==[67108864,67108864]and limit[4]['readback']==[1800,1801]and limit[5]['argv']==c['nativeArgv']and limit[5]['ASSetterRequested']is False
 memRaw=check(O/(c['label']+'.memory-journal.jsonl'),r['memoryJournal']);memory=[json.loads(x)for x in memRaw.splitlines()];assert len(memory)==r['memorySamples']==obs['sampleCount']==obs['memoryAdmissionRecord']['acceptedSamples']>0
 previousNs=-1;births={};maxPhysical=0
 for ordinal,row in enumerate(memory,1):
  assert len(row)==4 and row[0]==ordinal and type(row[1])is int and row[1]>previousNs and row[2]==r['pid'];previousNs=row[1]
  members=row[3];assert 1<=len(members)<=2 and len({m[0]for m in members})==len(members)
  for pid,birth,physical in members:
   assert all(type(v)is int for v in(pid,birth,physical))and pid>0 and birth>0 and 0<=physical<=4294967296
   if pid in births:assert births[pid]==birth
   births[pid]=birth
  assert any(m[0]==r['pid']for m in members);total=sum(m[2]for m in members);assert total<=4294967296;maxPhysical=max(maxPhysical,total)
 record=obs['memoryAdmissionRecord'];failure=record['failure'];strict=obs['strictOldMemoryPolicyPassed'];strictTotal+=int(strict)
 if failure:
  assert i==3 and failure['failureClass']=='kernel-oserror'and failure['stage']=='member-getpgid'and failure['errno']==3 and failure['pid']in births and record['otherRefusals']==[]
  assert obs['memoryObservation']['missingFootprint']is None and obs['memoryObservation']['zeroSynthesized']is False and not strict
 samplesTotal+=len(memory)
 ar=result['artifact'];whole=check(ar['path'],ar)
 if c['kind']=='compile':
  payload,exports=container(whole)
  if i==1:assert exports==[('main',0,0)]
  else:
   e=next(e for e in pr['entries']if e['workload']==c['workload']);assert whole==check(e['container']['path'],e['container'])and payload==check(e['native']['path'],e['native'])and exports==[tuple(x)for x in e['exports']]
 else:
  packed=(O/'observer.kseed').read_bytes();payload,exports=container(packed);assert whole==payload and exports==[('main',0,0)]
 out.append({'label':c['label'],'directWait':0,'artifact':ar,'wholeOrdinaryIdentity':i>=3,'decoded':decoded,'arena17':counter['values'],'memorySamples':len(memory),'maximumObservedPhysicalBytes':maxPhysical,'strictOldMemoryPolicyPassed':strict,'memoryAdmissionRecord':record,'memoryObservation':obs['memoryObservation'],'stoppedWriter':True,'rawReceipts':{n:r[n]for n in('stdout','stderr','limitJournal','memoryJournal')}})
producer=validate_producer(pr,go,g['sourcePinsSHA256'],g['preregistrationSHA256']);assert json.loads((O/'observer-producer-evidence.json').read_text())==rows[:2]
for p,r in json.loads((O/'generated-pins.json').read_text()).items():check(p,r)
# Actual trace refuses missing cleanup, malformed count, and unstable observed-field mutations.
refusals=0
c=pr['cases'][2];raw=(O/'statemate-compile.stdout').read_bytes()
for bad in(raw.replace(b'QCLEAN 0',b'QCLEAN 1',1),raw+b'x',raw.replace(b'QBEGIN 1 ',b'QBEGIN 2 ',1),raw.replace(b'QINIT 147552',b'QINIT 147551',1)):
 try:parse_output(bad,c)
 except (AssertionError,ValueError):refusals+=1
 else:raise AssertionError('actual mutant accepted')
assert refusals==4 and registries()==(sp,ip)
r={'status':'PASS_INDEPENDENT_SAVED_CURRENT_G4_CTX_QUERY_OBSERVER4_ARTIFACT_AND_BOUNDED_TRACE_ONLY','subject':str(D),'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'rootGO':go,'sourceReviews':g['sourceReviews'],'completion':rec(O/'report.json'),'terminal':report['evidence']['terminal.json'],'allSourcePins':len(sp),'allInputPins':len(ip),'allInputBytes':sum(x['bytes']for x in ip.values()),'closedCompilerCalls':4,'guestWorkloadExecutions':0,'strictSampledCalls':strictTotal,'typedTerminationGapCalls':4-strictTotal,'acceptedNumericMemorySamples':samplesTotal,'actualRows':out,'generatedProducerReceipt':producer,'producerGateInterpretation':'Author-written internal verification of admitted firsttwo calls; this later saved audit independent of LC implementation and root execution. No earlier fake independent producer actor.','independentActualTraceMutantsRefused':refusals,'reviewerRole':'Independent of observer implementation and root execution; authored base cap511/source ancestor and reviewed SOURCE. Reads/hashes/pure saved parsers only.','repeatedKeyInterpretation':'Finite observed equal f/n/depth/work/openrange tuples only, not complete read-set/ComputeCID or saved owned ResultCID. Counts hypothetical skipped structural entries, not measured avoided work or timing.','limitations':['Statemate observes221 top queries/24 repeated keys/4305scan333safe hypothetical entries; all221summaries inside256 bound.','NS observes first256 of392queries/127repeated keys/23804scan490safe hypothetical entries; remaining136keys/summaries not observed, fullrecursive traces16only.','Statemate typed prior-bound ESRCH remains physical-memory gap null/strictOld false, no synthesized zero or hardpeak.','No runtime/cache importer/replay/effect/trap correctness, complete read closure, cache performance, timing, Ccomparison or product adoption proof.'],'performanceQualified':False,'cacheAdmissionQualified':False,'sharedCIDCacheImplemented':False,'C2':False,'checkedReceipts':list(checked.values())}
(A/'report.json').write_text(json.dumps(r,indent=2)+'\n');(A/'freeze.json').write_text(json.dumps({'status':'FROZEN_INDEPENDENT_SAVED_ACTUAL_AUDIT_ONLY','report':rec(A/'report.json'),'audit':rec(A/'audit.py')},indent=2)+'\n');print(rec(A/'report.json'))
