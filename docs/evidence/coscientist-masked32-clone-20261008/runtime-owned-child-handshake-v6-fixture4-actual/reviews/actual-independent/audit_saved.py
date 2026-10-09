from pathlib import Path
import json,hashlib,stat,re,importlib.util
D=Path('/Users/junkawasaki/github/workspaces/codex/held-launch-v6-ownership-fixture4-source-v1-20261009-crc');O=D/'run-outputs';R=Path(__file__).parent
L=lambda p:json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def pin(q):
 p=Path(q['path']);assert rec(p)=={k:q[k]for k in ['bytes','sha256']};return p
pr=L(D/'preregistration.json');sp=L(D/'source-pins.json');ip=L(D/'input-pins.json')
for n,r in sp.items():assert rec(D/n)==r
for n,r in ip.items():assert rec(n)==r
spec=importlib.util.spec_from_file_location('inert_fixture_source',D/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.closure(pr,sp,ip);m.source_scope(pr)
report=L(O/'report.json');g=L(pin(report['rootGO']));m.go_header(g,pr)
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert rec(D/n)['sha256']==g[k]
for r in g['sourceReviews']:
 q=L(pin(r));assert q['status']==pr['sourceReviewStatus'];assert all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
build=L(pin(g['diagnosticLoaderBuildProof']));pin(g['diagnosticLoaderArtifact']);target=L(pin(pr['targetPreregistration']));assert build['status']==pr['loaderBuildIdentityStatus']and build['artifact']==g['diagnosticLoaderArtifact']and build['compileArgv']==target['prospectiveLoaderBuildArgv']and build['closedBuildCalls']==1 and build['noRetry']is True
assert build['copiedCSource']==dict(path=str(Path(pr['targetMechanismWorkspace'])/'kexe_loader_diagnostic.c'),**rec(Path(pr['targetMechanismWorkspace'])/'kexe_loader_diagnostic.c'))and build['originalCSource']==target['originalLoaderCSource']and build['compileFlag']=='KEXE_OWNERSHIP_DIAGNOSTIC_V3'
assert report['status']=='COMPLETE_FIXED_HELD_LAUNCH_V6_DIAGNOSTIC_FIXTURE4_ONLY'and report['sourcePinsSHA256']==g['sourcePinsSHA256']and report['targetSourcePinsSHA256']==pr['targetSourcePins']['sha256']
assert L(O/'terminal.json')=={'startedCases':[c['id']for c in pr['cases']],'completedCases':4,'failure':False,'noRetry':True,'missingCaseClosureIsRefusal':True}
assert L(O/'started-cases.json')==[c['id']for c in pr['cases']]and L(O/'results.json')==report['results'];assert not (O/'failure.json').exists()
summary=[];raws=[];sampletotal=0
for c,x in zip(pr['cases'],report['results']):
 C=Path(c['capsule']);P=L(pin(c['preregistration']));out=Path(c['outputRoot']);assert x==L(out/'fixture-case.json')and x['id']==c['id']
 t=L(pin(x['delegatedTicket']));assert t['status']==P['rootGOStatus']and t['maximumLoaderCalls']==2 and t['delegation']=={'parentGO':report['rootGO'],'fixtureCase':c['id'],'allowedStarts':1,'originalPaired2Credit':False};assert t['diagnosticLoaderBuildProof']==g['diagnosticLoaderBuildProof']and t['diagnosticLoaderArtifact']==g['diagnosticLoaderArtifact']
 sealpath=out/(c['case']['label']+'.admission.json');seal=L(sealpath);assert stat.S_IMODE(sealpath.stat().st_mode)==0o444
 expected={k:c['case'][k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};expected.update(format=P['invocationSealVersion'],index=1,rootGO=x['delegatedTicket'],sourcePinsSHA256=c['sourcePins']['sha256'],preregistrationSHA256=c['preregistration']['sha256']);assert seal==expected
 rows=L(pin(x['attempt']));assert len(rows)==1;a=rows[0];assert a['state']=='terminal'and a['waitEntered']is True and a['waitUncertain']is False and a['signalingAuthorityRetired']is True and a['ownershipWriterStopAcknowledged']is True and a['watchdogErrors']==[]
 assert a['environment']==P['environment']and len(a['environment'])==17 and a['nativeArgv']==c['case']['nativeArgv']and a['invocation']==rec(sealpath)['sha256']
 expectedargv=[P['interpreter']['path'],str(C/'launch-wrapper.py'),'--journal-fd',a['argv'][3],'--admission-sha',a['invocation'],'--ownership-fd',a['argv'][7],'--',*c['case']['nativeArgv']];assert a['argv']==expectedargv and all(re.fullmatch('[0-9]+',a['argv'][k])for k in [3,7])
 base=out/c['case']['label'];journals={n:base.with_suffix('.'+suffix)for n,suffix in [('limitJournal','limit-journal.jsonl'),('memoryJournal','memory-journal.jsonl'),('ownershipJournal','ownership-journal.jsonl')]}
 for n,p in journals.items():assert rec(p)==a[n]
 mem=[json.loads(s)for s in journals['memoryJournal'].read_bytes().splitlines()];own=[json.loads(s)for s in journals['ownershipJournal'].read_bytes().splitlines()];sampletotal+=len(mem);assert len(mem)==a['memorySamples']and journals['memoryJournal'].stat().st_size==a['memoryJournalBytes']
 trace=x['trace'];assert trace[-1]=={'event':'leader-wait-return','pid':a['pid'],'returncode':a['returncode']}and sum(t['event']=='leader-wait-enter'for t in trace)==1
 if c['kind']=='dup2':
  assert a['returncode']==-9 and a['childWaitReceipt']is None and a['ownershipBindings']=={}and mem==own==[] and x['result']is None and x['error']is not None and 'TransferFailure' in a['failure'];assert [t['event']for t in trace]==['injected-second-dup-failure','exact-leader-signal','leader-wait-enter','leader-wait-return'];assert trace[1]['pid']==a['pid']and trace[1]['signal']==9
 else:
  assert a['returncode']==0 and a['failure']is None and x['error']is None and len(own)==4 and len(a['ownershipBindings'])==2
  assert [q['stage']for q in own]==['held-birth-admitted','held-birth-admitted','loader-child-exit-held','loader-child-wait'];bindings={str(q['pid']):q['birth']for q in own[:2]};assert bindings==a['ownershipBindings']and own[0]['pid']==a['pid'];assert [q['sequence']for q in own[:2]]==[1,2]
  nonce=hashlib.sha256((a['invocation']+x['delegatedTicket']['sha256']).encode()).hexdigest();assert all(q['GO']==x['delegatedTicket']['sha256']and q['nonce']==nonce and re.fullmatch('[0-9a-f]{64}',q['wireSHA256'])for q in own)
  assert own[2]['pid']==own[3]['pid']==own[1]['pid']and own[2]['birth']==own[3]['birth']==own[1]['birth']and own[2]['exit']==0 and own[2]['unreapedPIDAnchor']is True and own[3]['waitStatus']==0 and own[3]['noPostReapGroupQueries']is True
  assert a['childWaitReceipt']=={'pid':own[1]['pid'],'birth':own[1]['birth'],'exit':0,'durable':True}
  prev=0
  for i,q in enumerate(mem,1):
   assert len(q)==4 and q[0]==i and q[1]>prev and q[2]==a['pid']and 1<=len(q[3])<=2;prev=q[1];assert sum(z[2]for z in q[3])<=4294967296 and all(bindings[str(z[0])]==z[1]and z[2]>=0 for z in q[3])
  assert len(mem[0][3])==1 and len(mem[1][3])==2
  obs=a['controllerObservation'];mr=obs['memoryAdmissionRecord'];assert mr['failure']is None and mr['groupOperationsAfterWait']==mr['groupOperationsAfterUncertainty']==0 and mr['heldOwnershipQualified']and mr['exactHeldChildWait0']and obs['strictHeldSamplingPolicyPassed'];assert obs['controllerEvents'].index('retire:owned-child-exit-before-reap-ACK')<obs['controllerEvents'].index('wait-enter')
  raw={k:base.with_suffix('.'+k)for k in ['stdout','stderr']}
  for k,p in raw.items():assert rec(p)==a[k]==obs['capture']['hashes'][k]
  cp=obs['capture'];assert cp['stoppedWriter']and cp['completeRaw']and all(cp['EOF'].values())and cp['dropped']=={'stdout':0,'stderr':0}and cp['errors']==[]
  parser=importlib.util.spec_from_file_location('inert_raw_parser',C/'runtime.py');rt=importlib.util.module_from_spec(parser);parser.loader.exec_module(rt);decoded=rt.qualify(raw['stdout'].read_bytes(),raw['stderr'].read_bytes(),1);assert decoded==a['structuredReportObservation']==x['result']['report'];assert decoded['arena17']==a['counterObservation']['values']==x['result']['arena'];assert decoded['fuelConsumed']==1698;raws.append(decoded)
  lr=[json.loads(s)for s in journals['limitJournal'].read_bytes().splitlines()];assert len(lr)==6 and lr[-1]=={'stage':'exec-ready','argv':c['case']['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':31};assert lr[0]['nativeExecEnvironmentExact']and lr[0]['nativeExecKeyNames']==sorted(P['environment'])and lr[0]['missingKeyNames']==lr[0]['changedExpectedKeyNames']==[]and lr[0]['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
  for i,(n,v)in enumerate([('RLIMIT_FSIZE',[67108864,67108864]),('RLIMIT_CPU',[30,31])],1):assert lr[2*i-1]['limit']==n and lr[2*i-1]['desired']==v and lr[2*i]=={'index':i,'limit':n,'stage':'outcome','outcome':'installed','readback':v}
  if c['kind']=='blocked':
   b=L(out/'blocked-guard.json');assert b==x['coordinator']and b['workerAlive']and not b['writerStopAcknowledged']and not b['journalClosed']and b['retainedJournal']and b['observedBeforeRelease']and not b['kernelFsyncStall'];assert b['journalHashGuard']['status']=='UNHASHED_UNCLOSED_WRITER_OWNERSHIP_RETAINED'
 summary.append({'id':c['id'],'pid':a['pid'],'waitReturncode':a['returncode'],'memorySamples':len(mem),'ownershipRows':len(own),'attempt':x['attempt'],'fixtureCase':dict(path=str(out/'fixture-case.json'),**rec(out/'fixture-case.json'))})
assert raws[0]==raws[1]==raws[2]and sampletotal==9
q={'status':'PASS_INDEPENDENT_ACTUAL_DIAGNOSTIC_HELD_LAUNCH_CHANNEL_FD_AND_OWNERSHIP_V6_ONLY','sourcePinsSHA256':pr['targetSourcePins']['sha256'],'fixtureSourcePinsSHA256':g['sourcePinsSHA256'],'fixtureInputPinsSHA256':g['inputPinsSHA256'],'fixtureDriverSHA256':g['driverSHA256'],'fixturePreregistrationSHA256':g['preregistrationSHA256'],'rootGO':report['rootGO'],'fixtureReport':dict(path=str(O/'report.json'),**rec(O/'report.json')),'actualBuildProof':g['diagnosticLoaderBuildProof'],'verifiedSourceFiles':64,'verifiedInputFiles':79,'verifiedInputBytes':2454696,'cases':summary,'memorySamples':sampletotal,'ownershipJournalRows':12,'heldBirthRecords':6,'decodedNormalReport':raws[0],'reviewerRole':{'V6MechanismAuthor':True,'buildRegistrationAuthor':True,'independentOfCRCFixtureAuthorAndRootExecution':True},'qualification':'One saved four-case diagnostic fixture only; three normal protocol cases and one pre-TICKET injected refusal. Source-bound retirement before exit ACK, durable child-wait records, one local direct wait per case, no source-recorded postwait group operations, stopped acknowledged final writers. The blocked callback live-writer witness and exact hash guard precede source-controlled release and final real persistence acknowledgment.','limitations':['No operations or reruns by reviewer. Saved source-bound assertions and wire hashes, not independent syscall/thread chronology trace or complete raw wire replay.','WNOWAIT/ACK/reap order is inferred from exact admitted loader/ownership source plus durable stage receipts; not external kernel tracing.','Negative guest0 is conditional source-protocol proof, not actual fork counter. Negative has no semantic stdout admission.','Injected callback barrier is not kernel fsync stall or cancellation-timeout proof.','No universal FD/interruption cleanup, atomic census/hardpeak/overshoot, original95 credit, general race proof, full19/C2/timing/performance qualification.','Prior failed campaigns and buildV2 namespace unchanged; current source/GO/pins closed independently, no historical failed raw substituted.'],'operationalCalls':0}
(R/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(rec(R/'report.json'))
