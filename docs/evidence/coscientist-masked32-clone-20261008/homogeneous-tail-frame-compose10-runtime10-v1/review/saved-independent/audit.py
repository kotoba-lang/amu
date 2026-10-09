"""Independent saved-byte audit. No loader/compiler/guest/native/resource/FD/thread queries."""
from pathlib import Path
import json,hashlib,stat,sys,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex')
D=W/'tc-hft-compose10-original-ns-runtime10-source-v1-20261009'
R=W/'tc-hft-compose10-runtime10-actual-review-independent-20261009-dense'
G=W/'tc-hft-compose10-runtime10-go-root-20261009/root-go.json'
checked={}
def need(v,m):
 if not v: raise AssertionError(m)
def raw(p):
 p=Path(p)
 for ancestor in [p,*p.parents]:need(not ancestor.is_symlink(),'no symlink traversal '+str(ancestor))
 a=p.lstat();need(stat.S_ISREG(a.st_mode) and a.st_size<=469762048,'bounded regular '+str(p));b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'immutable '+str(p));checked[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(p,r):
 b=raw(p);need(checked[str(Path(p))]=={k:r[k] for k in ['bytes','sha256']},'pin '+str(p));return b
def load(p):return json.loads(raw(p))
def module(n):
 spec=importlib.util.spec_from_file_location('audit_'+n,D/(n+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');g=load(G);gr=dict(path=str(G),**checked[str(G)])
need(len(sp)==20 and len(ip)==155 and sum(r['bytes'] for r in ip.values())==13280263,'full closure counts')
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
need(gr['sha256']=='0ee3180ea64520a21d77da21b50174b61d288b48834e40501e08208ded5fc20f','exact root GO')
sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
run=module('run');runtime=module('runtime');admission=module('artifact_admission')
O=Path(pr['freshOutputRoot']);need(O==D/'run-outputs','output namespace')
proofkeys=run.go_header(g,pr,O)
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(checked[str(D/n)]['sha256']==g[k],'GO '+k)
need(len(g['sourceReviews'])==2 and len({r['path'] for r in g['sourceReviews']})==2,'two distinct reviews')
for r in g['sourceReviews']:
 q=json.loads(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k] for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'source review binding')
for k in proofkeys:
 need(g[k]==pr['qualifiedIntegrationFixtureProof' if k=='integrationFixtureProof' else k],'proof binding');pin(g[k]['path'],g[k])
f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','fixture')
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'fixture source')
op=load(pr['C95OracleProof']['path']);need(op['status']==pr['C95OracleProofStatus'] and op['oracle']==pr['C95Oracle'],'C result-only proof')
# Pure pinned read-only scope helper validates original source, protocol spans, whole containers and exact four words.
run.source_scope(pr)
proto=load(pr['loaderSupervisorProtocolView']['path'])
for r in proto['pins']:pin(r['path'],r)
need(pr['loaderSupervisorProtocolView']['sha256'].startswith('679'),'loader protocol pin')
on=load(pr['ONActualProof']['path']);need(on['closedCompilerCalls']==4,'prior four code calls')
need(len(on['calls'])==4 and sum(c['strictOldSamplingPassed'] is True for c in on['calls'])==4 and sum(c['memoryAdmissionRecord']['failure'] is not None for c in on['calls'])==0,'prior compose10 native4 four strict preserved')
v1=load(W/'tc-homogeneous-tail-frame-native4-v1-actual-failure-review-independent-20261009/report.json');need(v1['status']=='PASS_INDEPENDENT_SAVED_FAILURE_HFT_NATIVE4_V1_UNKNOWN_ENCODER_ONLY' and v1['calls']==1 and v1['directWaitReturncode']==1 and len(v1['remainingUnexecuted'])==3,'original V1 encoder failure preserved')
for ref in v1['evidence'].values():pin(ref['path'],ref)
rep=load(O/'report.json');need(rep['status']=='COMPLETE_HFT_COMPOSE10_ORIGINAL_NS_RUNTIME10_FINITE_PARITY_ONLY','runtime completion')
for n,r in rep['evidence'].items():need(r['path']==str(O/n),'evidence namespace');pin(r['path'],r)
rows=load(O/'attempts.json');results=load(O/'results.json');generated=load(O/'generated-pins.json');terminal=load(O/'terminal.json')
need(terminal=={'loaderCalls':10,'allChildrenClosed':True,'failure':False} and len(rows)==len(results)==len(pr['cases'])==len(generated)==10,'ten closed exactly')
need(load(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17,'effective environment')
need(rep['results']==results and rep['rootGO']==gr and rep['sourcePinsSHA256']==g['sourcePinsSHA256'],'completion binding')
for k in ['ONActualProof','OFFActualProof','C95Oracle']:need(rep[k]==g[k],'completion proof')
for k in ['C95FuelArenaAvailable','full19FunctionalQualified','generalCandidateAdoptionQualified','all10EdgeCompositionQualified','performanceQualified','hardPeakQualified','strictPhysicalMemoryQualified','C2']:need(rep[k] is False,'scope '+k)
need(rep['new10StrictSampledPolicyPassed'] is True and rep['runtimeCalls']==10 and rep['originalProfiles']==[0,1,2,17,32] and rep['pairedProfiles']==5,'bounded runtime claims')
all_samples=0;details=[];seen_pid=set();seen_birth=set()
for i,(c,a,r) in enumerate(zip(pr['cases'],rows,results),1):
 label=c['label'];base=O/label;sealpath=base.with_suffix('.admission.json');sr=generated[str(sealpath)];seal=json.loads(pin(sealpath,sr));need(sealpath.stat().st_mode&0o777==0o444 and sr['bytes']<=4096,'sealed mode/size')
 expected={k:c[k] for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};expected.update(format=pr['invocationSealVersion'],index=i,rootGO=gr,sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256']);need(seal==expected,'exact seal')
 need(a['index']==i and a['label']==label and a['environment']==pr['environment'] and a['nativeArgv']==c['nativeArgv'],'attempt case')
 argv=a['argv'];need(argv[:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd'] and argv[3].isdigit() and int(argv[3])>=3 and argv[4:]==['--admission-sha',sr['sha256'],'--',*c['nativeArgv']],'exact wrapper argv')
 need(a['state']=='terminal' and a['returncode']==0 and a['waitEntered'] is True and a['waitUncertain'] is False and a['signalingAuthorityRetired'] is True and a['captureStopAcknowledged'] is True and a['failure'] is None and a['watchdogErrors']==[],'wait/capture closure')
 for name,key in [('stdout','stdout'),('stderr','stderr'),('limit-journal.jsonl','limitJournal'),('memory-journal.jsonl','memoryJournal')]:pin(base.with_suffix('.'+name),a[key])
 out=raw(base.with_suffix('.stdout'));err=raw(base.with_suffix('.stderr'));decoded=runtime.qualify(out,err,c['expectedResult']);need(decoded==a['structuredReportObservation'] and a['counterObservation']=={'status':'valid','values':decoded['arena17']},'independent entire raw decode')
 need(decoded['result']==[0,1,1,1,1][(i-1)//2] and decoded['fuelConsumed']==[1,272,527,4352,8177][(i-1)//2] and len(decoded['arena17'])==17,'expected result/fuel/17arenas')
 obs=a['controllerObservation'];need(admission.accept_artifact_observation(obs) is True and obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['strictOldMemoryPolicyPassed'] is True,'strict sample admission')
 cap=obs['capture'];need(cap['EOF']=={'stdout':True,'stderr':True} and cap['completeRaw'] is True and cap['ownershipDecision']=='worker-granted' and cap['errors']==[] and cap['firstFailure'] is None and cap['stoppedWriter'] is True,'full EOF stopped owner')
 for name in ['stdout','stderr']:need(cap['hashes'][name]==a[name] and cap['retained'][name]==a[name]['bytes'] and cap['dropped'][name]==0,'raw capture identity')
 need(cap['observedBytes']==len(out)+len(err),'complete observed bytes')
 j=[json.loads(x) for x in raw(base.with_suffix('.limit-journal.jsonl')).splitlines()];need(len(j)==6,'six exact resource rows');keys=sorted(pr['environment']);need(j[0]=={'stage':'environment-admission','suppliedKeyNames':keys,'runtimeExtraKeyNames':j[0]['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':keys,'nativeExecEnvironmentExact':True} and j[0]['runtimeExtraKeyNames'] in [[],['__CF_USER_TEXT_ENCODING']],'exact env witness')
 for k,(name,soft,hard) in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)],1):
  b,z=j[2*k-1:2*k+1];need(set(b)=={'index','limit','stage','before','desired'} and b['index']==k and b['limit']==name and b['stage']=='before' and b['desired']==[soft,hard],'resource setter');need(all(v==9223372036854775807 or v>=n for v,n in zip(b['before'],[soft,hard])),'no inherited raise');need(z=={'index':k,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]},'readback')
 need(j[-1]=={'stage':'exec-ready','argv':c['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':31},'exec witness')
 memraw=raw(base.with_suffix('.memory-journal.jsonl'));samples=[json.loads(x) for x in memraw.splitlines()];count=len(samples);need(1<=count<=2048 and count==a['memorySamples']==obs['sampleCount']==obs['memoryAdmissionRecord']['acceptedSamples'] and len(memraw)==a['memoryJournalBytes'],'finite sample counts')
 birth=None;last=-1;maximum=0
 for n,s in enumerate(samples,1):
  need(len(s)==4 and s[0]==n and type(s[1]) is int and 0<=s[1]<2**64 and s[1]>last and s[2]==a['pid'] and 1<=len(s[3])<=2,'numeric sample provenance');last=s[1];need(len({m[0] for m in s[3]})==len(s[3]),'unique sample members');owner=[]
  for m in s[3]:
   need(len(m)==3 and all(type(x) is int for x in m) and 0<m[0]<2**31 and 0<m[1]<2**64 and 0<=m[2]<2**64,'finite numeric member');
   if m[0]==a['pid']:owner.append(m)
  need(len(owner)==1,'leader birth witness');b=owner[0][1];birth=b if birth is None else birth;need(b==birth,'stable leader birth');aggregate=sum(m[2] for m in s[3]);need(aggregate<=4294967296,'sample threshold');maximum=max(maximum,aggregate)
 need(a['pid'] not in seen_pid and birth not in seen_birth,'distinct ten child births');seen_pid.add(a['pid']);seen_birth.add(birth)
 ev=obs['controllerEvents'];need(ev==['group-operation']*count+['retire:before-watchdog-stop-and-wait','wait-enter','retire:final-cleanup'],'retirement/order no postwait group');need(obs['directChildWait']=='closed0' and obs['waitUncertain'] is False and obs['sampleReceiptPersistenceQualified'] is True and obs['nativeControllerWiringQualified'] is False,'controller scope')
 expectedresult={'label':label,'case':c,'returncode':0,'report':decoded,'arena':decoded['arena17'],'rawStdoutSHA256':a['stdout']['sha256'],'rawStderrSHA256':a['stderr']['sha256'],'memoryObservation':obs['memoryObservation'],'strictOldMemoryPolicyPassed':True};need(r==expectedresult,'saved result reconstruction')
 all_samples+=count;details.append({'label':label,'result':decoded['result'],'fuelConsumed':decoded['fuelConsumed'],'arena17':decoded['arena17'],'samples':count,'pid':a['pid'],'birth':birth,'maximumObservedAggregateBytes':maximum,'strictSampledPolicyPassed':True})
 if i%2==0:need(results[i-2]['report']==r['report'],'adjacent OFF/ON exact full report parity')
need(10<=all_samples<=20480,'bounded total accepted finite samples')
for p,r in list(checked.items()):pin(p,r)
report={'status':'PASS_INDEPENDENT_SAVED_HFT_COMPOSE10_RUNTIME10_ORIGINAL_FIVE_PAIR_DIAGNOSTIC_ONLY','sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'driverSHA256':g['driverSHA256'],'rootGO':gr,'sourceReviews':g['sourceReviews'],'independent':True,'priorImplementationAuthorship':True,'authorshipDisclosure':'Reviewer authored diagnostic native4/runtime10 SOURCE drivers, not compose10 optimization algorithm; root executed campaigns once; this saved actual byte/raw audit is not an independent SOURCE review of own driver','priorNative4CompilerStrictCalls':4,'priorNative4TypedTerminationGapCalls':0,'V1UnknownEncoderFailurePreserved':True,'sourceFiles':20,'inputFiles':155,'inputLogicalBytes':13280263,'runtimeCalls':10,'closed0':10,'strictSampledCases':10,'finiteSamples':all_samples,'originalProfiles':[0,1,2,17,32],'cases':details,'wholeOriginalNSNativeBytes':37520,'selectedBatchOffset':36440,'selectedBatchArity':1,'wordChanges':40,'loaderProtocolConditionalOnly':True,'CResultOnly':True,'completion':dict(path=str(O/'report.json'),**checked[str(O/'report.json')]),'ONActualProof':pr['ONActualProof'],'wholeONArtifact':pr['images']['ON'],'wholeOFFArtifact':pr['images']['OFF'],'erroneousV2SourceUnexecuted':True,'executedNativeOrGuest':False,'noNewOperationalCalls':True,'qualifications':{k:False for k in ['generalFrameABI','composition','full19','ownFixedpoint','CPerformance','productAdoption','hardPeak','strictPhysicalMemory']},'checkedRegularPins':checked,'auditor':dict(path=str(R/'audit.py'),bytes=len((R/'audit.py').read_bytes()),sha256=hashlib.sha256((R/'audit.py').read_bytes()).hexdigest())}
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'reportSHA256':hashlib.sha256((R/'report.json').read_bytes()).hexdigest(),'regularFiles':len(checked),'samples':all_samples}))
