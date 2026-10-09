"""Saved actual audit only: no guest/process/thread/FD/group/network calls."""
from pathlib import Path
import json,hashlib,stat,sys,importlib.util,copy
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense';O=D/'run-outputs';A=Path(__file__).resolve().parent;G=W/'tc-hft-g4-held-v6-original19-runtime190-go-root-20261009/root-go.json'
checked={}
def need(v,m):
 if not v:raise AssertionError(m)
def raw(p,cap=33554432):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=cap,'bounded regular:'+str(p));b=p.read_bytes();t=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns),'immutable saved bytes');checked[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def ref(p,cap=33554432):raw(p,cap);return dict(path=str(p),**checked[str(Path(p))])
def load(p):return json.loads(raw(p))
def pin(p,r):b=raw(p);need(checked[str(Path(p))]=={k:r[k]for k in ['bytes','sha256']},'pin:'+str(p));return b
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');go=load(G);gr=ref(G)
expected={'source-pins.json':'a27f04cb0a94abd33241d97f63065cda0f986646f119ec39ff54ec785c3fcdef','input-pins.json':'46e416a702cfce829040b3b2a237de7177708ebb234477d3ef7dbe6890e01e33','run.py':'97cd34ae622b9ade79a1ee327c270247b5b04c1080722a113ecaf510b322ef54','preregistration.json':'801c5f5551900760e38196f7732b9728fb604ffc0e3b2585dcc99eea0ded9471'}
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:need(ref(D/n)['sha256']==go[k]==expected[n],'SOURCE+GO')
need(gr['sha256']=='8afb3dc18827512ad482323af97e55f54fa8275cfdb0bf30b96ab26c8773edb0'and len(sp)==19 and len(ip)==127 and sum(v['bytes']for v in ip.values())==6144468,'exact campaign')
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
sys.path.insert(0,str(D));import run,runtime,ownership
from artifact_admission import accept_artifact_observation
spec=importlib.util.spec_from_file_location('saved_resources',D/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
proofkeys=run.go_header(go,pr,O);need(run.registry_scope(pr,ip)and run.source_scope(pr)and run.fixture_guard(go['ownershipIntegrationFixtureProof'],pr),'full native/source fixture contract')
need(len(go['sourceReviews'])==2 and len({q['path']for q in go['sourceReviews']})==2,'two independent SOURCE reviews')
for r in go['sourceReviews']:
 q=json.loads(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==go[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'SOURCE review identities')
for k in proofkeys:need(go[k]==pr[k],'proof identity');pin(go[k]['path'],go[k])
co=load(O/'report.json');term=load(O/'terminal.json');at=load(O/'attempts.json');rs=load(O/'results.json');gen=load(O/'generated-pins.json');need(not(O/'failure.json').exists(),'no new campaign failure')
need(term=={'loaderCalls':190,'allChildrenClosed':True,'failure':False}and len(at)==len(rs)==len(pr['cases'])==len(gen)==190,'exact190 terminal')
need(co['status']=='COMPLETE_HFT_G4_HELD_V6_ORIGINAL19_RUNTIME190_DIAGNOSTIC_ONLY'and co['runtimeCalls']==190 and co['originalWorkloads']==19 and co['pairedProfiles']==95 and co['results']==rs and co['rootGO']==gr and co['sourcePinsSHA256']==go['sourcePinsSHA256']and co['all190StrictSampledPolicyPassed']is True and co['full19FunctionalAdmissionPassed']is True,'valid-last complete exact runtime only')
for k in ['G4Original19ActualProof','FixedpointActualProof','C95Oracle','ownershipIntegrationFixtureProof','diagnosticLoaderBuildProof']:need(co[k]==go[k],'completion proof:'+k)
for k in ['generalCandidateAdoptionQualified','fullClobberCertificateQualified','actualTypedMode2AdmissionObserved','performanceQualified','hardPeakQualified','strictPhysicalMemoryQualified','C2','C95FuelArenaAvailable']:need(co[k]is False,'qualified boundary:'+k)
need(co['C95FuelArena']is None,'no invented C fuel/arenas')
for n,r in co['evidence'].items():need(r['path']==str(O/n),'valid-last evidence owner');pin(r['path'],r)
need(load(O/'effective-environment.json')==pr['environment']and len(pr['environment'])==17,'actual native env')
for p,r in gen.items():need(Path(p).parent==O,'new generated seal owner');pin(p,r)
allSamples=0;details=[];pairs=[];pids=set();workloads={};oracle=load(pr['C95Oracle']['path'])
def controller(o,a,mem,stdout,stderr,bindings):
 need(accept_artifact_observation(o)is True and o['status']=='COMPLETE_HELD_LAUNCH_SEMANTIC_SAMPLED_MEMORY'and o['strictHeldSamplingPolicyPassed']is True,'strict held admission')
 m=o['memoryAdmissionRecord'];need(m['failure']is None and m['otherRefusals']==[]and m['acceptedLeaderBirthBound']is True and m['heldOwnershipQualified']is True and m['exactHeldChildWait0']is True and m['initialHeldSamples']==2 and m['exactDirectChildWait']=='closed0'and m['waitUncertain']is False and m['withinOriginalDeadline']is True and m['groupAuthorityRetired']is True and m['groupOperationsAfterUncertainty']==m['groupOperationsAfterWait']==0 and m['loaderWaitProtocolPinned']is True,'record invariants')
 cap=o['capture'];need(cap['EOF']=={'stdout':True,'stderr':True}and cap['completeRaw']is True and cap['stoppedWriter']is True and cap['semanticDecodeAuthorized']is True and cap['ownershipDecision']=='worker-granted'and cap['firstFailure']is None and cap['errors']==[]and cap['dropped']=={'stdout':0,'stderr':0},'stopped complete capture')
 need(cap['hashes']=={'stdout':a['stdout'],'stderr':a['stderr']}and cap['retained']=={'stdout':len(stdout),'stderr':len(stderr)}and cap['observedBytes']==len(stdout)+len(stderr),'all raw captured')
 need(2<=len(mem)<=2048 and len(mem)==a['memorySamples']==o['sampleCount']==m['acceptedSamples'] and o['sampleReceiptPersistenceQualified']is True and o['directChildWait']=='closed0'and o['waitUncertain']is False,'durable finite samples and direct wait')
 last=-1;mx=0;leader=a['pid'];child=next(k for k in bindings if k!=leader)
 for i,q in enumerate(mem,1):
  need(type(q)is list and len(q)==4 and q[0]==i and type(q[1])is int and last<q[1]<2**64 and q[2]==leader and type(q[3])is list and 1<=len(q[3])<=2,'ordered provenance');last=q[1]
  need(len({m[0]for m in q[3]})==len(q[3]),'unique owned census');known={}
  for p,b,f in q[3]:need(all(type(t)is int for t in [p,b,f])and p in bindings and b==bindings[p]and 0<p<2**31 and 0<b<2**64 and 0<=f<2**64,'exact held PID birth and footprint');known[p]=b
  need(known.get(leader)==bindings[leader]and(i!=1 or set(known)=={leader})and(i!=2 or set(known)=={leader,child}),'initial held leader and unreleased child census')
  total=sum(z[2]for z in q[3]);need(total<=4294967296,'observed soft threshold');mx=max(mx,total)
 ev=o['controllerEvents'];need(len(ev)<=4096 and ev.count('wait-enter')==1 and ev.count('retire:owned-child-exit-before-reap-ACK')==1,'one owned reap and direct wait');first=next(i for i,x in enumerate(ev)if x.startswith('retire:'));need('group-operation'not in ev[first+1:]and ev.count('group-operation')==len(mem),'retirement before any reap/wait prevents future group query');need(ev.index('wait-enter')>first,'no signal/query after directwait')
 return mx
for i,(c,a,r)in enumerate(zip(pr['cases'],at,rs),1):
 label=c['label'];base=O/label;sealpath=base.with_suffix('.admission.json');sr=gen[str(sealpath)];seal=json.loads(pin(sealpath,sr));need(sealpath.stat().st_mode&0o777==0o444 and sr['bytes']<=4096,'seal owner')
 ex={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};ex.update(format=pr['invocationSealVersion'],index=i,rootGO=gr,sourcePinsSHA256=go['sourcePinsSHA256'],preregistrationSHA256=go['preregistrationSHA256']);need(seal==ex,'whole exact seal')
 need(a['index']==i and a['label']==label and a['environment']==pr['environment']and a['nativeArgv']==c['nativeArgv']and a['invocation']==sr['sha256'],'case invocation binding')
 av=a['argv'];need(av[:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd']and av[3].isdigit()and int(av[3])>=3 and av[4:6]==['--admission-sha',sr['sha256']]and av[6]=='--ownership-fd'and av[7].isdigit()and int(av[7])>4 and av[8:]==['--',*c['nativeArgv']],'wrapper args with separated ownership channel')
 need(a['pid']not in pids and type(a['pid'])is int and a['pid']>0,'distinct owned direct handle');pids.add(a['pid']);need(a['state']=='terminal'and a['returncode']==0 and a['waitEntered']is True and a['waitUncertain']is False and a['signalingAuthorityRetired']is True and a['captureStopAcknowledged']is True and a['ownershipWriterStopAcknowledged']is True and a['watchdogErrors']==[]and a['failure']is None,'all stopped/joined closed0')
 for suf,key,limit in [('stdout','stdout',8388608),('stderr','stderr',1048576),('limit-journal.jsonl','limitJournal',65536),('memory-journal.jsonl','memoryJournal',8388608),('ownership-journal.jsonl','ownershipJournal',65536)]:pin(base.with_suffix('.'+suf),a[key]);need(a[key]['bytes']<=limit,'stream bound')
 out=raw(base.with_suffix('.stdout'));err=raw(base.with_suffix('.stderr'));decoded=runtime.qualify(out,err,c['expectedResult']);need(decoded==a['structuredReportObservation']and a['counterObservation']=={'status':'valid','values':decoded['arena17']}and len(decoded['arena17'])==17,'entire structured raw/fuel17 decoder')
 need(nc.resource_journal(base.with_suffix('.limit-journal.jsonl'),pr,c['nativeArgv'])is True,'actual limit/17env/readback/exec receipt')
 mj=raw(base.with_suffix('.memory-journal.jsonl'));mem=[json.loads(x)for x in mj.splitlines()];need(len(mj)==a['memoryJournalBytes']and all(len(x)<=4096 for x in mj.splitlines()),'memory count/write byte accounting')
 own=[json.loads(x)for x in raw(base.with_suffix('.ownership-journal.jsonl')).splitlines()];need(len(own)==4 and all(len(x)<=4096 for x in raw(base.with_suffix('.ownership-journal.jsonl')).splitlines()),'exact four durable ownership rows')
 bindings={int(k):v for k,v in a['ownershipBindings'].items()};need(len(bindings)==2 and a['pid']in bindings,'complete local held births');leader=a['pid'];child=next(k for k in bindings if k!=leader);nonce=hashlib.sha256((sr['sha256']+gr['sha256']).encode()).hexdigest();stages=[(2,1,0,leader),(4,2,child,child),(6,3,child,child),(8,4,child,child)]
 for j,(stage,seq,wirechild,owner)in enumerate(stages):
  z=own[j];wire=ownership.encode(stage,seq,leader,wirechild,bindings[owner],leader,0,bytes.fromhex(gr['sha256']),bytes.fromhex(nonce));need(z['pid']==owner and z['birth']==bindings[owner]and z['GO']==gr['sha256']and z['nonce']==nonce and z['wireSHA256']==hashlib.sha256(wire).hexdigest(),'exact wire/GO/invocation/birth identity')
  if j<2:need(z==dict(stage='held-birth-admitted',sequence=seq,leader=leader,pid=owner,birth=bindings[owner],GO=gr['sha256'],nonce=nonce,wireSHA256=hashlib.sha256(wire).hexdigest(),guestStillHeld=True),'held-before-ACK durable source contract')
  elif j==2:need(z==dict(stage='loader-child-exit-held',pid=child,birth=bindings[child],exit=0,GO=gr['sha256'],nonce=nonce,wireSHA256=hashlib.sha256(wire).hexdigest(),unreapedPIDAnchor=True),'exact child EXIT_HELD0')
  else:need(z==dict(stage='loader-child-wait',pid=child,birth=bindings[child],waitStatus=0,GO=gr['sha256'],nonce=nonce,wireSHA256=hashlib.sha256(wire).hexdigest(),noPostReapGroupQueries=True),'exact child WAIT0 durable')
 need(a['childWaitReceipt']==dict(pid=child,birth=bindings[child],exit=0,durable=True),'exact child wait receipt')
 mx=controller(a['controllerObservation'],a,mem,out,err,bindings);allSamples+=len(mem)
 reconstructed=dict(label=label,case=c,returncode=0,report=decoded,arena=decoded['arena17'],rawStdoutSHA256=a['stdout']['sha256'],rawStderrSHA256=a['stderr']['sha256'],memoryObservation=a['controllerObservation']['memoryObservation'],strictHeldSamplingPolicyPassed=True);need(r==reconstructed,'independent saved result identity')
 answers=[z for z in oracle['rows']if z['workload']==c['workload']and z['n']==c['profile']];need(len(answers)==1 and answers[0]['result']==decoded['result']and answers[0]['sourceSHA256']==c['source']['sha256']and answers[0]['symbol']==c['symbol'],'C Boolean result oracle only')
 details.append(dict(index=i,label=label,workload=c['workload'],arm=c['arm'],profile=c['profile'],result=decoded['result'],fuelConsumed=decoded['fuelConsumed'],arena17=decoded['arena17'],directPID=leader,childPID=child,birthBindings=bindings,samples=len(mem),maximumObservedGroupFootprint=mx,childWait0=True,strictHeldSamplingPolicyPassed=True,raw={k:dict(path=str(base.with_suffix('.'+suffix)),**a[k])for k,suffix in [('stdout','stdout'),('stderr','stderr'),('limitJournal','limit-journal.jsonl'),('memoryJournal','memory-journal.jsonl'),('ownershipJournal','ownership-journal.jsonl')]}))
 if i%2==0:
  first=rs[i-2];need(all(first['report'][k]==decoded[k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']),'result/fuel/all17 exact pair');pairs.append(dict(workload=c['workload'],profile=c['profile'],result=decoded['result'],fuelConsumed=decoded['fuelConsumed'],arena17=decoded['arena17'],OFFindex=i-1,ONindex=i,CBooleanEqual=True));workloads.setdefault(c['workload'],[]).append(c['profile'])
need(len(pairs)==95 and len(workloads)==19 and allSamples==587 and all(r['strictHeldSamplingPolicyPassed']for r in rs),'finite exact tally')
# Actual saved record/decoder refusals; no real callbacks.
neg=[]
def refuse(name,fn):
 try:fn()
 except(AssertionError,KeyError,TypeError,ValueError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
a=at[0];c=pr['cases'][0];base=O/c['label'];mem=[json.loads(x)for x in raw(base.with_suffix('.memory-journal.jsonl')).splitlines()];bindings={int(k):v for k,v in a['ownershipBindings'].items()};out=raw(base.with_suffix('.stdout'));err=raw(base.with_suffix('.stderr'))
for name,fn in [('active-capture',lambda z:z['capture'].update(stoppedWriter=False)),('unbound-held-owner',lambda z:z['memoryAdmissionRecord'].update(heldOwnershipQualified=False)),('wrong-child-wait',lambda z:z['memoryAdmissionRecord'].update(exactHeldChildWait0=False)),('post-retire-group-query',lambda z:z['controllerEvents'].append('group-operation')),('capture-first-refusal',lambda z:z['capture'].update(firstFailure='bad')),('unknown-refusal',lambda z:z['memoryAdmissionRecord']['otherRefusals'].append('unknown'))]:
 z=copy.deepcopy(a['controllerObservation']);fn(z);refuse(name,lambda:controller(z,a,mem,out,err,bindings))
refuse('raw-extra-stdout',lambda:runtime.qualify(out+b'foreign\n',err,c['expectedResult']));refuse('raw-extra-stderr',lambda:runtime.qualify(out,err+b'foreign\n',c['expectedResult']))
for p,r in list(checked.items()):pin(p,r)
q={'status':'PASS_INDEPENDENT_SAVED_HFT_G4_HELD_V6_ORIGINAL19_RUNTIME190_FINITE_PARITY_ONLY','sourcePinsSHA256':go['sourcePinsSHA256'],'inputPinsSHA256':go['inputPinsSHA256'],'driverSHA256':go['driverSHA256'],'preregistrationSHA256':go['preregistrationSHA256'],'rootGO':gr,'sourceReviews':go['sourceReviews'],'completion':ref(O/'report.json'),'G4Original19ActualProof':pr['G4Original19ActualProof'],'FixedpointActualProof':pr['FixedpointActualProof'],'OFFActualProof':pr['OFFActualProof'],'diagnosticLoaderBuildProof':pr['diagnosticLoaderBuildProof'],'ownershipIntegrationFixtureProof':pr['ownershipIntegrationFixtureProof'],'C95Oracle':pr['C95Oracle'],'G4Producer':pr['G4Producer'],'imagesOFF':pr['imagesOFF'],'imagesON':pr['imagesON'],'verifiedClosure':{'sourceFiles':19,'inputFiles':127,'inputLogicalBytes':6144468,'regularFilesReread':len(checked)},'runtimeCalls':190,'directClosed0':190,'heldChildWait0':190,'strictHeldSamplingCalls':190,'typedTerminationGapCalls':0,'originalWorkloads':19,'pairedProfiles':95,'finiteMemorySamples':allSamples,'durableOwnershipJournalRows':760,'originalProfileCoverage':workloads,'pairs':pairs,'calls':details,'savedRefusalControls':neg,'reviewerRole':'Authored diagnostic registration driver, not optimization algorithm; independent saved raw audit from parent once execution, not independent SOURCE review of own driver','noNewOperationalCalls':True,'subjectWrites':0,'qualification':{'original95ResultFuelAll17ArenaParity':True,'originalC95BooleanEqual':True,'currentG4Original19FiniteFunctionalAdmission':True,'performance':False,'officialEmbenchScore':False,'generalABI':False,'fullClobberCertificate':False,'adoption':False,'hardPeak':False,'strictPhysicalMemory':False,'dynamicRuntimeWhole':False,'C2':False},'C95FuelArenaAvailable':False,'C95FuelArena':None,'limitations':['Only exact original95 profiles/currentOFF/currentHFT G4/heldV6 loader checked; finite cases are not general compiler correctness proof','587 samples are finite owned observations, not hardpeak/completeness or universal OS descendant tracing','WNOWAIT/reap protocol source and saved correlated journals do not create a universal adversarial scheduling proof','No timing measured here; full C-or-better performance goal remains open','All old unbound-PID/runtime/preflight/build failures remain preserved; this is a new once registration'],'checkedSavedPins':checked,'auditScript':ref(Path(__file__))}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(ref(A/'report.json'))
