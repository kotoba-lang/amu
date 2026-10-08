from pathlib import Path
import json,hashlib,re,stat,sys,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-vector-statemate6-source-v2-20261009';O=D/'run-outputs';R=Path(__file__).parent
assert sys.argv[1:]==['--root-terminal-confirmed'],'No live mutable-output polling; root terminal notice required'
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=h(b))
def ck(p,v):assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes']and h(b)==v['sha256'];return b
load=lambda p:json.loads(p.read_bytes())
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');fr=load(D/'freeze.json')
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
assert len(sp)==22 and len(ip)==80 and sum(v['bytes']for v in ip.values())==11077437
completion=load(O/'report.json');G=Path(completion['rootGO']['path']);g=json.loads(ck(G,completion['rootGO']));sys.path.insert(0,str(D));import run
assert run.go_header(g,pr,O)and run.source_scope(pr,ip)
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]
assert len(g['sourceReviews'])==2 and len({x['path']for x in g['sourceReviews']})==2
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
f=g['integrationFixtureProof'];assert f==pr['qualifiedIntegrationFixtureProof'];fq=json.loads(ck(Path(f['path']),f))
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
for k in ['baselineActualProof','TCActualProof','candidateActualProof']:assert g[k]==pr[k];ck(Path(g[k]['path']),g[k])
assert g['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256']
for k,v in load(O/'generated-pins.json').items():ck(Path(k),v)
assert load(O/'effective-environment.json')==pr['environment']and len(pr['environment'])==17
assert (O/'vector-fixture.kotoba').read_bytes()==ck(Path(pr['fixtureSource']['path']),pr['fixtureSource'])
assert (O/'statemate.kotoba').read_bytes()==ck(Path(pr['statemateEntry']['source']['path']),pr['statemateEntry']['source'])
container=run.container
rows=load(O/'attempts.json');results=load(O/'results.json');artifacts=load(O/'artifacts.json');assert len(rows)==len(results)==6 and len(artifacts)==3
assert run.existing_candidate_guard(pr) and run.preserved_failure_guard(pr)
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];summ=[];gaps=[];sampletotal=0
for i,(row,c,result)in enumerate(zip(rows,pr['cases'],results)):
 label=c['label'];assert row['index']==i+1 and row['label']==label and row['nativeArgv']==c['nativeArgv']and row['environment']==pr['environment']and row['state']=='terminal'and row['returncode']==0 and row['failure']is None and row['waitEntered']and not row['waitUncertain']and row['signalingAuthorityRetired']and row['captureStopAcknowledged']and row['watchdogErrors']==[]
 seal=load(O/(label+'.admission.json'));assert seal['index']==i+1 and seal['label']==label and seal['nativeArgv']==c['nativeArgv']and seal['rootGO']==rec(G)and seal['sourcePinsSHA256']==g['sourcePinsSHA256']and seal['preregistrationSHA256']==g['preregistrationSHA256']and seal['outputPath']==c['outputPath']
 assert row['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd']and row['argv'][3].isdigit()and row['argv'][4:6]==['--admission-sha',rec(O/(label+'.admission.json'))['sha256']]and row['argv'][6:]==['--',*c['nativeArgv']]
 for k in ['producer','producerContainer','input']:ck(Path(seal[k]['path']),seal[k])
 payload,exports=container(Path(seal['producerContainer']['path']).read_bytes());assert payload==Path(seal['producer']['path']).read_bytes()and exports==[('main',0,0)]and seal['producer']['path']==c['producer']
 if i<2:assert seal['producer']==pr['offCompiler']and seal['producerContainer']==pr['offCompilerContainer']and seal['existingProducerProof']==pr['TCActualProof']
 else:assert seal['producer']==pr['candidateCompiler']and seal['producerContainer']==pr['candidateCompilerContainer']and seal['existingProducerProof']==pr['candidateActualProof']
 raw={k:ck(O/(label+ext),row[k])for k,ext in [('stdout','.stdout'),('stderr','.stderr'),('memoryJournal','.memory-journal.jsonl'),('limitJournal','.limit-journal.jsonl')]};obs=row['controllerObservation'];cap=obs['capture'];mr=obs['memoryAdmissionRecord']
 assert cap['stoppedWriter']and cap['completeRaw']and cap['EOF']=={'stdout':True,'stderr':True}and not any(cap['dropped'].values())and cap['errors']==[]and cap['hashes']=={k:row[k]for k in ['stdout','stderr']}and cap['retained']=={k:len(raw[k])for k in ['stdout','stderr']}
 assert 0<len(raw['stdout'])<=8388608 and len(raw['stderr'])<=1048576
 path=json.dumps(c['outputPath']).encode();out=Path(c['outputPath']).read_bytes()
 if c['kind']=='compile':
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output '+re.escape(path)+rb', :bytes ([0-9]{1,10})\}\n',raw['stdout']);assert m and int(m[1])==len(out);container(out);rep={'kind':'compile','containerBytes':len(out)}
 else:
  m=re.fullmatch(rb'\{:ok true, :output '+re.escape(path)+rb', :offset ([0-9]{1,10}), :length ([0-9]{1,10}), :arity ([0-9]{1,2})\}\n',raw['stdout']);assert m;rep={'kind':'extract','offset':int(m[1]),'nativeBytes':int(m[2]),'arity':int(m[3])};payload,exports=container(Path(c['nativeArgv'][8]).read_bytes());entry=[e for e in exports if e[0]==c['symbol']];assert len(entry)==1 and entry[0][2]==c['arity']and payload==out and rep=={'kind':'extract','offset':entry[0][1],'nativeBytes':len(payload),'arity':c['arity']}
  ar=artifacts[i//2];assert ar['label']==label and ar['native']==rec(Path(c['outputPath']))and ar['container']==rec(Path(c['nativeArgv'][8]))and ar['selectedExport']==list(entry[0])and ar['exports']==[list(e)for e in exports]
 assert rep==result['report']==row['structuredReportObservation']and result['label']==label and result['case']==c and result['returncode']==0 and result['rawStdoutSHA256']==row['stdout']['sha256']and result['rawStderrSHA256']==row['stderr']['sha256']
 kv=re.findall(rb':([a-z-]+) ([0-9]{1,20})',raw['stderr']);arena={k.decode():int(v)for k,v in kv};assert len(kv)==17 and list(arena)==FIELDS and b'KEXE_ARENA_USE {'+b' '.join(b':'+k+b' '+v for k,v in kv)+b'}\n'==raw['stderr']and result['arena']==arena and row['counterObservation']=={'status':'valid','values':arena,'entireStderrIsCounterLine':True}
 assert all(0<=z<2**64 for z in arena.values())and arena['heap-bytes']==16*arena['pairs']+arena['string-pool-bytes']+16*arena['vectors']+8*arena['vector-items']and arena['pairs']<=16777216 and arena['string-pool-bytes']<=268435456 and arena['vectors']<=4194304 and arena['vector-items']<=134217728
 jl=[json.loads(x)for x in raw['limitJournal'].splitlines()];assert len(jl)==6 and len(raw['limitJournal'])<=65536;ew=jl[0];ek=sorted(pr['environment']);assert ew=={'stage':'environment-admission','suppliedKeyNames':ek,'runtimeExtraKeyNames':ew['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':ek,'nativeExecEnvironmentExact':True}and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,want)in enumerate([('RLIMIT_FSIZE',[67108864,67108864]),('RLIMIT_CPU',[1800,1801])]):
  bef,aft=jl[1+2*k:3+2*k];assert bef['index']==k+1 and bef['stage']=='before'and bef['limit']==name and bef['desired']==want and all(z==9223372036854775807 or z>=w for z,w in zip(bef['before'],want));assert aft=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':want}
 assert jl[-1]=={'stage':'exec-ready','argv':c['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801}
 samples=[json.loads(x)for x in raw['memoryJournal'].splitlines()];assert 0<len(samples)==row['memorySamples']<=90502 and row['memoryJournalBytes']==len(raw['memoryJournal'])<=16777216;totals=[];prev=0;births={}
 for ordinal,tm,pgid,members in samples:
  assert ordinal==len(totals)+1 and tm>prev and pgid==row['pid']and 1<=len(members)<=2 and len({x[0]for x in members})==len(members)and len([x for x in members if x[0]==pgid])==1
  for pid,bt,foot in members:
   assert pid>0 and bt>0 and 0<=foot<2**64
   if pid in births:assert births[pid]==bt
   births[pid]=bt
  total=sum(x[2]for x in members);assert total<=4294967296;totals.append(total);prev=tm
 assert mr['acceptedSamples']==obs['sampleCount']==len(samples)and obs['sampleReceiptPersistenceQualified']and mr['acceptedLeaderBirthBound']and mr['completePipeEOF']and mr['stoppedClosedCapture']and not mr['rawTruncated']and not mr['captureErrors']and mr['exactDirectChildWait']=='closed0'and not mr['waitUncertain']and mr['withinOriginalDeadline']and mr['groupAuthorityRetired']and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0 and mr['otherRefusals']==[]and obs['semanticQualification']
 failure=mr['failure']
 if failure is None:assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY'and obs['strictOldMemoryPolicyPassed']and cap['firstFailure']is None
 else:
  assert failure['contextVersion']=='owned-group-sampling-failure-context-v1'and failure['typedOrigin']=='fresh-owned-group-api-v1'and failure['failureClass']in ['kernel-oserror','kernel-failed-return']and failure['errno']==3 and failure['stage']in ['leader-getpgid','member-getpgid','member-rusage']and failure['pid']in births and failure['queryOrdinal']>0
  assert obs['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP'and not obs['strictOldMemoryPolicyPassed']and cap['firstFailure']=='sampling-uncertainty'and obs['memoryObservation']=={'status':'termination-gap-unavailable','strictOldSamplingRefusal':True,'sampleCompleteness':'gap-unavailable','missingFootprint':None,'zeroSynthesized':False,'hardPeakQualified':False};gaps.append({'label':label,'failure':failure})
 assert result['strictOldMemoryPolicyPassed']==obs['strictOldMemoryPolicyPassed']and result['memoryObservation']==obs['memoryObservation']
 ev=obs['controllerEvents'];assert ev.count('wait-enter')==1 and ev.index('retire:before-watchdog-stop-and-wait')<ev.index('wait-enter')and not any(z=='group-operation'for z in ev[ev.index('wait-enter')+1:]);sampletotal+=len(samples)
 summ.append({'label':label,'wait':0,'acceptedSamples':len(samples),'sampleSums':totals,'strictSampledPolicyPassed':obs['strictOldMemoryPolicyPassed'],'memoryAdmissionRecord':mr,'report':rep,'arena17':arena,'artifact':rec(Path(c['outputPath'])),'seal':rec(O/(label+'.admission.json')),'raw':{k:row[k]for k in ['stdout','stderr','limitJournal','memoryJournal']}})
assert load(O/'terminal.json')=={'loaderCalls':6,'allChildrenClosed':True,'failure':False}and not (O/'failure.json').exists()
assert completion['status']=='COMPLETE_PUBLISHED_MODE2_X8_VECTOR_STATEMATE6_V2_COMPILER_ARTIFACTS_ONLY'and completion['closedCompilerCalls']==6 and completion['artifacts']==artifacts and completion['candidateActualProof']==pr['candidateActualProof']and completion['preservedCandidateBuildRootGO']==pr['candidateBuildRootGO']and completion['unchangedStatemateSource']==pr['statemateEntry']['source']and completion['preservedV1Failure']==pr['preservedV1Failure']and completion['operationalEnvironment']==pr['operationalEnvironment']and completion['fixtureSource']==pr['fixtureSource']and completion['sourcePinsSHA256']==g['sourcePinsSHA256']
for k in ['guestRuntimeExecuted','stageClobberCertificateQualified','candidateAdoptionQualified','selfhostFixedpointQualified','original19FunctionalQualified','performanceQualified','hardPeakQualified','strictPhysicalMemoryQualified','C2']:assert completion[k]is False
for n,v in completion['evidence'].items():ck(O/n,v)
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
r={'status':'PASS_INDEPENDENT_SAVED_PUBLISHED_MODE2_X8_VECTOR_STATEMATE6_V2_COMPILER_ARTIFACTS_ONLY','independent':True,'priorImplementationAuthorship':False,'priorSOURCEReviewer':True,'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'sourceRegistry':{'files':22,'logicalBytes':sum(x['bytes']for x in sp.values())},'inputRegistry':{'files':80,'logicalBytes':11077437},'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'fixture':f,'completion':rec(O/'report.json'),'terminal':rec(O/'terminal.json'),'calls':summ,'closedCompilerCalls':6,'acceptedFiniteSamples':sampletotal,'strictSampledPolicyPassedCalls':sum(x['strictSampledPolicyPassed']for x in summ),'admittedTypedMemoryGaps':gaps,'preservedSealedProducerBuild':pr['candidateSealedBuild'],'preservedCandidateBuildRootGO':pr['candidateBuildRootGO'],'candidateActualProof':pr['candidateActualProof'],'wholeArtifactsAndOwnExports':artifacts,'candidateSourceChallenge':pr['candidateSourceChallenge'],'stageClobberCertificateQualified':False,'candidateAdoptionQualified':False,'guestRuntimeExecuted':False,'selfhostFixedpointQualified':False,'performanceQualified':False,'limits':['Compiler artifact formation only; exact x8/x7/fuel clobber/alias/lifetime/entry CFG certificate remains HOLD.','Fixture OFF/ON selectedbench exports are artifact identity only, no invocation/result/fuel/trap parity or full19/performance.','Finite physicalfootprint samples and eligible termination gaps do not qualify hardpeak/atomiccensus/universalownership or kernelcause.','Durable source-bound resource/EOF/wait/controller receipts do not supply external syscall chronology.','Original V1 directchild125 sandbox initialization failure remains immutable and unqualified. Parent reports V2 once host require_escalated execution closed0; external privilege context is attributed to root, not independently measured from Boolean declaration or raw child evidence.','No ComputeCID/ResultCID cache performance claim.'],'operations':{'nativeThreadFDPipeProcessGroupSetterNetworkCalls':0,'reruns':0,'frozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
