"""Read-only saved ACTUAL audit. No process/native/query/setter/thread/FD/network APIs."""
from pathlib import Path
import json,hashlib,stat,sys,importlib.util,copy
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-g4-original19-compile38-source-v1-20261009';O=D/'run-outputs';A=Path(__file__).resolve().parent;G=W/'published-mode2-x8-g4-compile38-go-root-20261009/root-go.json'
sys.path.insert(0,str(D))
def need(x,m):
 if not x:raise AssertionError(m)
def r(p,cap=33554432):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=cap,'regular bounded:'+str(p));b=p.read_bytes();z=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable bytes');return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def ref(p,cap=33554432):return dict(path=str(p),**r(p,cap))
def load(p):return json.loads(Path(p).read_bytes())
def pin(v):need(r(v['path'])=={k:v[k]for k in ['bytes','sha256']},'pin:'+v['path']);return Path(v['path'])
def save(n,q):(A/n).write_text(json.dumps(q,indent=2)+'\n')
import run
from artifact_admission import accept_artifact_observation
from compiler_output import parse_output
from runtime import counters
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');go=load(G);gr=ref(G);expected={'sourcePinsSHA256':'099f52dbbbd0a09bdb9bec665287785fc7bd42074f98c9410659d230cefe068b','inputPinsSHA256':'ab76312481d00a708be43bd18f824b360493fd9db36d710944d0fce34bf31f14','driverSHA256':'129d5ef6ca7347bf0884b82b613404bd2e35534ae6767ce71091644bd6736343','preregistrationSHA256':'337f1571da4603ed8f1afd8efa2f736b9f23e342ba92d7366acb8955236ea85f'}
for f,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:need(r(D/f)['sha256']==go[k]==expected[k],'source/GO')
need(len(sp)==22 and len(ip)==80 and sum(v['bytes']for v in ip.values())==10983592,'complete closure')
for n,v in sp.items():need(r(D/n)==v,'own source:'+n)
for n,v in ip.items():need(r(n)==v,'input:'+n)
need(run.go_header(go,pr,O)and run.source_scope(pr,ip)and run.existing_g4_guard(pr),'current exact source and G4')
need(len(go['sourceReviews'])==2 and len({v['path']for v in go['sourceReviews']})==2,'reviews')
for v in go['sourceReviews']:
 q=load(pin(v));need(q['status']==pr['sourceReviewStatus']and all(q[k]==go[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact pre-GO source review')
for key,target in [('fixedpointActualProof','fixedpointActualProof'),('integrationFixtureProof','qualifiedIntegrationFixtureProof')]:need(go[key]==pr[target],'fixed proof identity');pin(go[key])
need(go['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'candidate source')
completion=load(O/'report.json');terminal=load(O/'terminal.json');attempts=load(O/'attempts.json');results=load(O/'results.json');images=load(O/'artifacts.json');generated=load(O/'generated-pins.json')
need(terminal=={'loaderCalls':38,'allChildrenClosed':True,'failure':False}and len(attempts)==len(results)==38 and len(images)==19 and len(generated)==95,'closed once38')
need(not(O/'failure.json').exists(),'no campaign failure')
need(completion['status']=='COMPLETE_PUBLISHED_MODE2_X8_G4_ORIGINAL19_COMPILE38_ARTIFACTS_ONLY'and completion['closedCompilerCalls']==38 and completion['original19Images']==images and completion['rootGO']==gr and completion['sourcePinsSHA256']==go['sourcePinsSHA256']and completion['currentG4Native']==pr['currentCompiler']and completion['currentG4Container']==pr['currentCompilerContainer']and completion['fixedpointActualProof']==pr['fixedpointActualProof'],'valid-last completion binding')
for n,v in completion['evidence'].items():need(v['path']==str(O/n),'evidence owner');pin(v)
for p,v in generated.items():need(Path(p).parent==O and r(p)==v,'generated current owner pin')
need(load(O/'effective-environment.json')==pr['environment'],'supplied17 actual receipt')
spec=importlib.util.spec_from_file_location('saved_native_resources',D/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
calls=[];samplesTotal=0;strict=0;gaps=[];allPIDs=set();negatives=[]
def validate_observation(obs,pid,journal,raw):
 need(accept_artifact_observation(obs)is True,'honest artifact/sample-or-gap admission')
 rec=obs['memoryAdmissionRecord'];cap=obs['capture'];need(rec['acceptedSamples']==obs['sampleCount']==len(journal)>=1 and rec['acceptedLeaderBirthBound']is True and obs['sampleReceiptPersistenceQualified']is True,'durable accepted samples')
 need(obs['directChildWait']=='closed0'and obs['waitUncertain']is False,'direct closure')
 need(cap['stoppedWriter']is True and cap['ownershipDecision']=='worker-granted'and cap['completeRaw']is True and cap['semanticDecodeAuthorized']is True and cap['errors']==[] and cap['dropped']=={'stdout':0,'stderr':0}and cap['EOF']=={'stdout':True,'stderr':True},'stopped complete raw')
 need(cap['retained']=={k:v['bytes']for k,v in raw.items()}and cap['hashes']==raw and cap['observedBytes']==sum(v['bytes']for v in raw.values()),'capture hash/byte complete')
 bound={};seen=set();clock=-1
 for i,q in enumerate(journal,1):
  need(isinstance(q,list)and len(q)==4 and q[0]==i and type(q[1])is int and clock<q[1]<2**64 and q[2]==pid and isinstance(q[3],list)and 1<=len(q[3])<=2,'bounded ordered numeric witness');clock=q[1];members=q[3];need(len({m[0]for m in members})==len(members),'unique members')
  need(sum(m[2]for m in members)<=4294967296,'soft observed footprint threshold')
  need(len([m for m in members if m[0]==pid])==1,'anchored leader')
  for p,birth,foot in members:
   need(type(p)is int and 0<p<=2147483647 and type(birth)is int and 0<birth<2**64 and type(foot)is int and 0<=foot<2**64,'finite typed member')
   need(p not in bound or bound[p]==birth,'per-case birth coherence');bound[p]=birth;seen.add(p)
 events=obs['controllerEvents'];need(len(events)<=4096 and events.count('wait-enter')==1,'bounded one wait event');wait=events.index('wait-enter');need(any(e.startswith('retire:')for e in events[:wait]),'retired before wait');first=next(i for i,e in enumerate(events)if e.startswith('retire:'));need('group-operation'not in events[first+1:],'no group operation after retirement/wait')
 if rec['failure']is not None:
  f=rec['failure'];need(f['pid']in seen and f['contextVersion']=='owned-group-sampling-failure-context-v1'and f['typedOrigin']=='fresh-owned-group-api-v1'and f['stage']in ['leader-getpgid','member-getpgid','member-rusage']and f['errno']==3 and type(f['queryOrdinal'])is int and f['queryOrdinal']>0 and f['failureClass']in ['kernel-oserror','kernel-failed-return'],'typed observed prior-bound termination gap')
 return True
for i,(c,a,res)in enumerate(zip(pr['cases'],attempts,results),1):
 need(a['index']==i and a['label']==c['label']and a['nativeArgv']==c['nativeArgv']and a['environment']==pr['environment']and a['state']=='terminal'and a['returncode']==0 and a['failure']is None and a['waitEntered']is True and a['waitUncertain']is False and a['signalingAuthorityRetired']is True and a['captureStopAcknowledged']is True and a['watchdogErrors']==[],'normal closure:'+c['label'])
 need(type(a['pid'])is int and a['pid']>0 and a['pid']not in allPIDs,'distinct saved direct wrappers');allPIDs.add(a['pid'])
 sealPath=O/(c['label']+'.admission.json');seal=load(sealPath);sr=r(sealPath);need(generated[str(sealPath)]==sr and sr['bytes']<=4096,'exact current seal')
 need(set(seal)=={'format','index','label','nativeArgv','producer','producerContainer','existingProducerProof','input','outputPath','rootGO','sourcePinsSHA256','preregistrationSHA256'}and seal['format']==pr['invocationSealVersion']and seal['index']==i and seal['label']==c['label']and seal['nativeArgv']==c['nativeArgv']and seal['producer']==pr['currentCompiler']and seal['producerContainer']==pr['currentCompilerContainer']and seal['existingProducerProof']==pr['fixedpointActualProof']and seal['rootGO']==gr and seal['outputPath']==c['outputPath']and seal['sourcePinsSHA256']==go['sourcePinsSHA256']and seal['preregistrationSHA256']==go['preregistrationSHA256'],'source/seal currentG4 owner')
 need(seal['input']['path']==c['nativeArgv'][8],'input owner');pin(seal['input']);argv=a['argv'];need(argv[:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd']and argv[3].isdecimal()and int(argv[3])>=3 and argv[4:7]==['--admission-sha',sr['sha256'],'--']and argv[7:]==c['nativeArgv'],'exact outer interpreter/wrapper/argv')
 paths={k:O/(c['label']+'.'+suffix)for k,suffix in [('stdout','stdout'),('stderr','stderr'),('limitJournal','limit-journal.jsonl'),('memoryJournal','memory-journal.jsonl')]}
 for k,p in paths.items():need(r(p,8388608 if k=='stdout'else 1048576 if k=='stderr'else 65536 if k=='limitJournal'else 16777216)==a[k],'whole savedraw:'+k)
 raw={k:a[k]for k in ['stdout','stderr']};report=parse_output(paths['stdout'].read_bytes(),c);counter=counters(paths['stderr'].read_bytes());need(counter['status']=='valid'and counter==a['counterObservation']and report==a['structuredReportObservation'],'entire raw report/counters')
 need(nc.resource_journal(paths['limitJournal'],pr,c['nativeArgv'])is True,'named limits/environment/exec exact')
 numeric=[json.loads(line)for line in paths['memoryJournal'].read_bytes().splitlines()];need(len(numeric)==a['memorySamples']<=90502 and a['memoryJournalBytes']==a['memoryJournal']['bytes']and all(len(line)<=4096 for line in paths['memoryJournal'].read_bytes().splitlines()),'sample durability/count/bound')
 obs=a['controllerObservation'];validate_observation(obs,a['pid'],numeric,raw);samplesTotal+=len(numeric);strict+=int(obs['strictOldMemoryPolicyPassed'])
 if not obs['strictOldMemoryPolicyPassed']:gaps.append({'label':c['label'],'failure':obs['memoryAdmissionRecord']['failure'],'acceptedSamples':len(numeric),'missingFootprint':None,'strictOldPolicyPassed':False})
 need(res=={'label':c['label'],'case':c,'returncode':0,'report':report,'arena':counter['values'],'rawStdoutSHA256':raw['stdout']['sha256'],'rawStderrSHA256':raw['stderr']['sha256'],'memoryObservation':obs['memoryObservation'],'strictOldMemoryPolicyPassed':obs['strictOldMemoryPolicyPassed']},'independent normalized result')
 if c['kind']=='compile':
  e=pr['entries'][(i-1)//2];need({k:seal['input'][k]for k in ['bytes','sha256']}=={k:e['source'][k]for k in ['bytes','sha256']},'original copied workload source');out=Path(c['outputPath']);need(report=={'kind':'compile','containerBytes':r(out)['bytes']},'whole compiled image');run.container(out.read_bytes())
 else:
  im=images[(i-1)//2];e=pr['entries'][(i-1)//2];payload,exports=run.container(pin(im['container']).read_bytes());need(payload==pin(im['native']).read_bytes()and im['source']==e['source']and im['workload']==e['workload']and im['symbol']==e['symbol']and im['iterations']==e['iterations']and im['exports']==[list(z)for z in exports]and im['selectedExport']in im['exports']and im['selectedExport'][0]==c['symbol']and im['selectedExport'][2]==1 and report=={'kind':'extract','offset':im['selectedExport'][1],'nativeBytes':len(payload),'arity':1},'whole19 native own exports source profiles')
 calls.append(dict(index=i,label=c['label'],directWait=0,pid=a['pid'],admission=ref(sealPath),raw={k:dict(path=str(p),**a[k])for k,p in paths.items()},report=report,counters17=counter['values'],samples=len(numeric),strictSampledPolicyPassed=obs['strictOldMemoryPolicyPassed'],memoryObservation=obs['memoryObservation']))
need(samplesTotal==121 and strict==34 and len(gaps)==4,'actual finite tally')
# Meaningful saved-record faults; no callbacks to real APIs.
base=attempts[0];numeric=[json.loads(x)for x in (O/(pr['cases'][0]['label']+'.memory-journal.jsonl')).read_bytes().splitlines()];raw={k:base[k]for k in ['stdout','stderr']}
for name,change in [('unknown-failure-pid',lambda o:o['memoryAdmissionRecord']['failure'].update(pid=2147483647)),('false-wait',lambda o:o['memoryAdmissionRecord'].update(exactDirectChildWait='uncertain')),('other-refusal',lambda o:o['memoryAdmissionRecord']['otherRefusals'].append('unbound')),('untyped-origin',lambda o:o['memoryAdmissionRecord']['failure'].update(typedOrigin='guessed')),('active-capture',lambda o:o['capture'].update(stoppedWriter=False)),('truncated',lambda o:o['capture']['dropped'].update(stdout=1)),('post-wait-group',lambda o:o['controllerEvents'].append('group-operation'))]:
 z=copy.deepcopy(base['controllerObservation']);change(z)
 try:validate_observation(z,base['pid'],numeric,raw)
 except (AssertionError,KeyError,TypeError):negatives.append(name)
 else:raise AssertionError('fault admitted:'+name)
# Optional oldOFF byte comparisons are informational only, never admission expectations.
offPath=W/'tc-current7618-off18-compile36-actual-review-independent-20261009/report.json';off=load(offPath);om={i['workload']:i for i in off['joinedOriginal19Images']};comparisons=[]
for im in images:
 old=om[im['workload']];a=pin(old['native']).read_bytes();b=Path(im['native']['path']).read_bytes();comparisons.append(dict(workload=im['workload'],OFFNative=old['native'],G4Native=im['native'],wholeNativeEqual=a==b,oldBytes=len(a),newBytes=len(b)))
for n,v in sp.items():need(r(D/n)==v,'subject remained frozen')
for p,v in generated.items():need(r(p)==v,'saved output unchanged')
need(r(G)=={k:gr[k]for k in ['bytes','sha256']},'GO unchanged')
q=dict(status='PASS_INDEPENDENT_SAVED_PUBLISHED_MODE2_X8_G4_ORIGINAL19_COMPILE38_ARTIFACT_IDENTITY_ONLY',independent=True,priorImplementationAuthorship=False,sourcePinsSHA256=go['sourcePinsSHA256'],inputPinsSHA256=go['inputPinsSHA256'],driverSHA256=go['driverSHA256'],preregistrationSHA256=go['preregistrationSHA256'],rootGO=gr,sourceReviews=go['sourceReviews'],completion=ref(O/'report.json'),verifiedClosure=dict(sourceFiles=22,inputFiles=80,inputLogicalBytes=10983592,generatedCurrentPins=95),closedCompilerCalls=38,currentG4Native=pr['currentCompiler'],currentG4Container=pr['currentCompilerContainer'],currentG4BuildReceipt=pr['fixedpointBuildReceipt'],fixedpointActualProof=pr['fixedpointActualProof'],currentG4Receipts=load(pr['fixedpointActualProof']['path'])['generatedProducerReceipts'],sourceCandidate=pr['sourceCandidate'],original19Images=images,calls=calls,acceptedFiniteSamples=samplesTotal,strictSampledPolicyPassedCalls=strict,admittedTypedTerminationGaps=gaps,savedRecordRefusals=negatives,oldOFFSavedByteComparisons=comparisons,oldOFFComparisonSemanticQualification=False,qualification=dict(currentG4Original19ArtifactIdentity=True,guestRuntime=False,fullOriginal19Functional=False,privateClobberCertificate=False,generalABI=False,performance=False,adoption=False,hardPeak=False),limitations=['saved evidence audit only, no live process or sampler query','four typed prior-bound termination gaps accepted as semantic artifacts with footprint unavailable/null and strict old sampled policy false','34 remaining calls retain strict finite sampled policy; none establishes hardpeak or OS-descendant closure','public export/code identity is not workload guest execution or full-machine ABI proof','oldOFF byte comparisons are diagnostic, not expected new bytes or timing evidence'],operationalCalls=0,subjectWrites=0,auditScript=ref(Path(__file__)))
save('report.json',q);print(q['status'])
