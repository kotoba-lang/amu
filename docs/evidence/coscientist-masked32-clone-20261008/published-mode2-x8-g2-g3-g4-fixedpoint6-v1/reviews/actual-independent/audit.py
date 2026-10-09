"""Saved-byte independent ACTUAL audit. No compiler/loader/guest/rerun/OS query operations."""
from pathlib import Path
import json,hashlib,stat,sys,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-g2-g3-g4-fixedpoint6-source-v1-20261009';O=D/'run-outputs';R=W/'published-mode2-x8-fixedpoint6-actual-review-independent-20261009';G=W/'published-mode2-x8-fixedpoint6-go-root-20261009/root-go.json'
checked={}
def need(v,m):
 if not v:raise AssertionError(m)
def raw(p):
 p=Path(p)
 for q in [p,*p.parents]:need(not q.is_symlink(),'no symlink traversal '+str(q))
 a=p.lstat();need(stat.S_ISREG(a.st_mode) and a.st_size<=469762048,'bounded regular');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable bytes');checked[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(p,r):b=raw(p);need(checked[str(Path(p))]=={k:r[k] for k in ['bytes','sha256']},'exact pin '+str(p));return b
def load(p):return json.loads(raw(p))
def ref(p):raw(p);return dict(path=str(p),**checked[str(p)])
def module(n):spec=importlib.util.spec_from_file_location('independent_'+n,D/(n+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');fr=load(D/'freeze.json');g=load(G);gr=ref(G)
need(len(sp)==21 and len(ip)==50 and sum(r['bytes'] for r in ip.values())==5292422,'closure counts')
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
for n,k in [('source-pins.json','sourcePins'),('input-pins.json','inputPins'),('preregistration.json','preregistration'),('run.py','driver')]:pin(D/n,fr[k])
sys.dont_write_bytecode=True;sys.path.insert(0,str(D));run=module('run');parser=module('compiler_output');runtime=module('runtime');admission=module('artifact_admission')
run.source_scope(pr,ip);run.go_header(g,pr,O);need(gr['sha256']=='e3b13206f88387460da61fda9c256a5cb11ca219c1b4246c96523e56f69c8905','exact root GO')
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(checked[str(D/n)]['sha256']==g[k],'GO source identity')
need(g['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'candidate source')
need(len(g['sourceReviews'])==2 and len({r['path'] for r in g['sourceReviews']})==2,'two reviews')
for r in g['sourceReviews']:
 v=json.loads(pin(r['path'],r));need(v['status']==pr['sourceReviewStatus'] and all(v[k]==g[k] for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'review bindings')
for k in run.PROOF_KEYS:
 need(g[k]==pr['qualifiedIntegrationFixtureProof' if k=='integrationFixtureProof' else k],'prerequisite bindings');pin(g[k]['path'],g[k])
f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','fixture')
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'fixture source')
proto=load(pr['loaderSupervisorProtocolView']['path'])
for r in proto['pins']:pin(r['path'],r)
need(proto['OSClosureTraceQualified'] is False and proto['universalCompilerProof'] is False,'conditional protocol')
rep=load(O/'report.json');need(rep['status']=='COMPLETE_PUBLISHED_MODE2_X8_G2_G3_G4_WHOLE_FIXEDPOINT6_COMPILER_ARTIFACTS_ONLY' and rep['closedCompilerCalls']==6,'complete compiler only')
for n,r in rep['evidence'].items():need(r['path']==str(O/n),'evidence owner');pin(r['path'],r)
rows=load(O/'attempts.json');results=load(O/'results.json');artifacts=load(O/'artifacts.json');generated=load(O/'generated-pins.json');terminal=load(O/'terminal.json')
need(terminal=={'loaderCalls':6,'allChildrenClosed':True,'failure':False} and len(rows)==len(results)==6,'six exact closed')
need(rep['rootGO']==gr and rep['sourcePinsSHA256']==g['sourcePinsSHA256'] and rep['artifacts']==artifacts,'completion binding')
for k in ['sourceCandidate','G1Native','G1Container']:need(rep[k]==pr[k],'completion prerequisite '+k)
for k in ['guestRuntimeExecuted','stageClobberCertificateQualified','candidateAdoptionQualified','full19FunctionalQualified','performanceQualified','hardPeakQualified','strictPhysicalMemoryQualified','C2']:need(rep[k] is False,'scope '+k)
need(rep['G2G3G4WholeNativeEqual'] is True and rep['G2G3G4WholeContainerEqual'] is True and rep['G1EqualityRequired'] is False,'fixedpoint scope')
need(load(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17,'exact17 environment')
expectedpaths={str(O/'candidate-source.kotoba')}|{str(O/(c['label']+'.admission.json')) for c in pr['cases']}|{str(O/('G'+str(n)+ext)) for n in [2,3,4] for ext in ['.bin','.kseed','-build-receipt.json']};need(set(generated)==expectedpaths,'exact generated closure')
for p,r in generated.items():pin(p,r)
need(raw(O/'candidate-source.kotoba')==pin(pr['sourceCandidate']['path'],pr['sourceCandidate']),'same source actual bytes')
need([a['generation'] for a in artifacts]==[2,3,4],'generation sequence');whole=[];builds={}
for a in artifacts:
 n=a['generation'];need(a['native']['path']==str(O/('G'+str(n)+'.bin')) and a['container']['path']==str(O/('G'+str(n)+'.kseed')),'whole artifact owners');nb=pin(a['native']['path'],a['native']);kb=pin(a['container']['path'],a['container']);payload,exports=run.container(kb);need(payload==nb and exports==[('main',0,0)] and a['exports']==[['main',0,0]],'whole container/native/sole exports')
 need(len(nb)==866680 and len(kb)==866706 and a['native']['sha256']=='6b410b003a428a40098bdd330539ccf3fef5fdd6d8e9bad23758f941b347462d' and a['container']['sha256']=='3ebef5afb6b2b7cd826499722dbbbc250c8e71ed54afc893f5124ee8d6f952da','whole fixedpoint hashes');whole.append((nb,kb,exports))
 bp=O/('G'+str(n)+'-build-receipt.json');b=load(bp);need(bp.stat().st_mode&0o777==0o444 and b['attempts']==rows[(n-2)*2:(n-1)*2],'current receipt exact admitted attempts');run.build_guard(b,pr,a['native'],a['container'],gr,n);builds[n]=ref(bp)
need(whole[0]==whole[1]==whole[2],'independent full native/container/export equality');need(pin(pr['G1Native']['path'],pr['G1Native'])!=whole[0][0] and pin(pr['G1Container']['path'],pr['G1Container'])!=whole[0][1],'old G1 differs unconstrained')
details=[];strict=0;gaps=0;total=0;seenpid=set();seenbirth=set()
for i,(c,a,r) in enumerate(zip(pr['cases'],rows,results),1):
 base=O/c['label'];generation=c['generation'];previous=generation-1;art=artifacts[generation-2];producer=pr['G1Native'] if generation==2 else artifacts[generation-3]['native'];packed=pr['G1Container'] if generation==2 else artifacts[generation-3]['container'];pb=None if generation==2 else builds[previous];sealpath=base.with_suffix('.admission.json');seal=json.loads(pin(sealpath,generated[str(sealpath)]));need(sealpath.stat().st_mode&0o777==0o444 and generated[str(sealpath)]['bytes']<=4096,'immutable seal')
 expected={'format':pr['invocationSealVersion'],'index':i,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':producer,'producerContainer':packed,'producerBuild':pb,'input':ref(Path(c['nativeArgv'][8])),'outputPath':c['outputPath'],'rootGO':gr,'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};need(seal==expected,'exact current invocation seal')
 need(a['index']==i and a['label']==c['label'] and a['nativeArgv']==c['nativeArgv'] and a['environment']==pr['environment'] and run.compiler_case(a['nativeArgv'],pr,c),'exact generation argv/env')
 argv=a['argv'];need(argv[:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd'] and argv[3].isdigit() and int(argv[3])>=3 and argv[4:]==['--admission-sha',generated[str(sealpath)]['sha256'],'--',*c['nativeArgv']],'wrapper argv seal binding')
 need(a['state']=='terminal' and a['returncode']==0 and a['waitEntered'] is True and a['waitUncertain'] is False and a['failure'] is None and a['watchdogErrors']==[] and a['signalingAuthorityRetired'] is True and a['captureStopAcknowledged'] is True,'normal wait/closed capture lifecycle')
 for suffix,key in [('stdout','stdout'),('stderr','stderr'),('limit-journal.jsonl','limitJournal'),('memory-journal.jsonl','memoryJournal')]:pin(base.with_suffix('.'+suffix),a[key])
 out=raw(base.with_suffix('.stdout'));err=raw(base.with_suffix('.stderr'));decoded=parser.parse_output(out,c);counters=runtime.counters(err);need(counters['status']=='valid' and len(counters['values'])==17 and decoded==a['structuredReportObservation'] and counters==a['counterObservation'],'entire raw parser/counters')
 need(decoded==({'kind':'compile','containerBytes':art['container']['bytes']} if c['kind']=='compile' else {'kind':'extract','offset':0,'nativeBytes':art['native']['bytes'],'arity':0}),'exact compiler output artifact')
 obs=a['controllerObservation'];need(admission.accept_artifact_observation(obs) is True,'unchanged strict or typed gap admission');cap=obs['capture'];record=obs['memoryAdmissionRecord'];need(cap['stoppedWriter'] is True and cap['completeRaw'] is True and cap['EOF']=={'stdout':True,'stderr':True} and cap['errors']==[] and cap['ownershipDecision']=='worker-granted' and cap['observedBytes']==len(out)+len(err),'complete raw EOF')
 for name in ['stdout','stderr']:need(cap['hashes'][name]==a[name] and cap['retained'][name]==a[name]['bytes'] and cap['dropped'][name]==0,'capture whole hashes')
 j=[json.loads(x) for x in raw(base.with_suffix('.limit-journal.jsonl')).splitlines()];need(len(j)==6,'six resource rows');keys=sorted(pr['environment']);need(j[0]=={'stage':'environment-admission','suppliedKeyNames':keys,'runtimeExtraKeyNames':j[0]['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':keys,'nativeExecEnvironmentExact':True} and j[0]['runtimeExtraKeyNames'] in [[],['__CF_USER_TEXT_ENCODING']],'exact env witness')
 for k,(name,soft,hard) in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):
  b,z=j[2*k-1:2*k+1];need(set(b)=={'index','limit','stage','before','desired'} and b['index']==k and b['limit']==name and b['stage']=='before' and b['desired']==[soft,hard],'named resource setter');need(all(v==9223372036854775807 or v>=n for v,n in zip(b['before'],[soft,hard])),'no inherited raise');need(z=={'index':k,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]},'exact readback')
 need(j[-1]=={'stage':'exec-ready','argv':c['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801},'exec-ready witness')
 memraw=raw(base.with_suffix('.memory-journal.jsonl'));samples=[json.loads(x) for x in memraw.splitlines()];count=len(samples);need(1<=count<=90502 and count==a['memorySamples']==obs['sampleCount']==record['acceptedSamples'] and len(memraw)==a['memoryJournalBytes']<=16777216,'finite persisted accepted samples');binding={};last=-1;maximum=0
 for index,s in enumerate(samples,1):
  need(len(s)==4 and s[0]==index and type(s[1]) is int and last<s[1]<2**64 and s[2]==a['pid'] and 1<=len(s[3])<=2,'ordered sample numeric provenance');last=s[1];need(len({m[0] for m in s[3]})==len(s[3]),'unique members');owner=[]
  for m in s[3]:
   need(len(m)==3 and all(type(x) is int for x in m) and 0<m[0]<2**31 and 0<m[1]<2**64 and 0<=m[2]<2**64,'bounded member receipt');need(m[0] not in binding or binding[m[0]]==m[1],'stable lifetime member birth');binding[m[0]]=m[1]
   if m[0]==a['pid']:owner.append(m)
  need(len(owner)==1 and len(binding)<=2,'finite owned leader/lifetime membership');aggregate=sum(m[2] for m in s[3]);need(aggregate<=4294967296,'sample aggregate threshold');maximum=max(maximum,aggregate)
 birth=binding[a['pid']];need(a['pid'] not in seenpid and birth not in seenbirth,'distinct six child births');seenpid.add(a['pid']);seenbirth.add(birth)
 failure=record['failure'];events=obs['controllerEvents'];tail=['retire:before-watchdog-stop-and-wait','wait-enter','retire:final-cleanup']
 if failure is None:
  need(obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['strictOldMemoryPolicyPassed'] is True and cap['firstFailure'] is None and events==['group-operation']*count+tail,'strict controller order');strict+=1
 else:
  need(failure['pid'] in binding and failure['contextVersion']=='owned-group-sampling-failure-context-v1' and failure['typedOrigin']=='fresh-owned-group-api-v1' and failure['stage'] in ['leader-getpgid','member-getpgid','member-rusage'] and failure['errno']==3 and type(failure['queryOrdinal']) is int and failure['queryOrdinal']>0,'fresh eligible previously bound failure');need(events==['group-operation']*(count+1)+['retire:group-exception-atomic','retire:sampling-uncertainty']+tail and obs['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP' and obs['strictOldMemoryPolicyPassed'] is False and cap['firstFailure']=='sampling-uncertainty' and obs['memoryObservation']['missingFootprint'] is None and obs['memoryObservation']['zeroSynthesized'] is False,'typed gap order no synthesized zero');gaps+=1
 need(obs['directChildWait']=='closed0' and obs['waitUncertain'] is False and obs['sampleReceiptPersistenceQualified'] is True and obs['nativeControllerWiringQualified'] is False,'controller scope')
 expectedresult={'label':c['label'],'case':c,'returncode':0,'report':decoded,'arena':counters['values'],'rawStdoutSHA256':a['stdout']['sha256'],'rawStderrSHA256':a['stderr']['sha256'],'memoryObservation':obs['memoryObservation'],'strictOldMemoryPolicyPassed':obs['strictOldMemoryPolicyPassed']};need(r==expectedresult,'result exact reconstruction');total+=count;details.append({'label':c['label'],'pid':a['pid'],'leaderBirth':birth,'acceptedSamples':count,'maximumObservedAggregateBytes':maximum,'strictOldSamplingPassed':obs['strictOldMemoryPolicyPassed'],'memoryAdmissionRecord':record,'arena17':counters['values'],'report':decoded,'seal':ref(sealpath),'raw':{k:a[k] for k in ['stdout','stderr','limitJournal','memoryJournal']}})
need(total==185 and strict==4 and gaps==2,'185 accepted samples four strict two gaps')
for p,r in list(checked.items()):pin(p,r)
report={'status':'PASS_INDEPENDENT_SAVED_PUBLISHED_MODE2_X8_G2_G3_G4_FIXEDPOINT6_COMPILER_ARTIFACTS_ONLY','independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'rootGO':gr,'sourceReviews':g['sourceReviews'],'completion':ref(O/'report.json'),'verifiedClosure':{'sourceFiles':21,'inputFiles':50,'inputLogicalBytes':5292422},'closedCompilerCalls':6,'strictSampledCalls':4,'typedTerminationGapCalls':2,'acceptedFiniteSamples':185,'sourceCandidate':pr['sourceCandidate'],'wholeArtifactsAndOwnExports':artifacts,'G2G3G4WholeNativeEqual':True,'G2G3G4WholeContainerEqual':True,'G2G3G4WholeExportsEqual':True,'G1Differs':True,'G1EqualityRequired':False,'generatedProducerReceipts':builds,'calls':details,'qualification':{'ownSourceWholeFixedpointG2G3G4':True,'generalMachineClobber':False,'candidateAdoption':False,'fullOriginal19':False,'newBenchmarkRuntime':False,'currentG4Runtime':False,'CPerformance':False,'hardPeak':False,'strictPhysicalMemory':False},'operationalCalls':0,'noNativeOrGuestRerun':True,'C2':False,'conclusion':'Six current-GO compile/extract calls are semantically closed0; same exact unity source generates identical whole G2/G3/G4 native/container/sole-main exports. Four strict sampled calls and two fully typed termination gaps; no general correctness, workload runtime, adoption or performance qualification.','checkedRegularPins':checked,'auditor':ref(R/'audit.py')}
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'sha256':hashlib.sha256((R/'report.json').read_bytes()).hexdigest(),'regularFiles':len(checked),'acceptedSamples':total}))
