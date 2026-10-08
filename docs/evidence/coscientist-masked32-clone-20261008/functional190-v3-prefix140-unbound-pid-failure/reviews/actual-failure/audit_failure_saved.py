from pathlib import Path
import json,hashlib,re,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-functional190-source-v3-20261009';O=D/'run-outputs';R=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def ck(p,v):
 assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes'] and h(b)==v['sha256'];return b
def load(p):return json.loads(p.read_bytes())
def container(b):
 head,rest=b.split(b'\n',1);m=re.fullmatch(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)',head);assert m
 table,payload=rest.split(b'\n\n',1);exports=[]
 for l in table.splitlines():
  x=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',l);assert x;exports.append([x[1].decode(),int(x[2]),int(x[3])])
 assert len(payload)==int(m[1]) and len(exports)==int(m[2]) and len(set(e[0]for e in exports))==len(exports)
 assert all(e[1]%4==0 and 0<=e[1]<len(payload)-3 and e[2]<=32 for e in exports);return payload,exports
# Prepared standalone offline auditor: operational drivers/modules are never imported.
import sys
assert sys.argv[1:]==['--root-terminal-confirmed'], 'Run only after root confirms saved terminal; no polling/live audit'
freeze=load(D/'freeze.json')
assert freeze['sourcePinsSHA256']=='c48b75be4296316df2143c1b91bcf8231558f56c3762bd91e761c56c6c0fcca2'
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');regs={}
for name,entries,relative in [('source-pins.json',sp,True),('input-pins.json',ip,False)]:regs[name]={'files':len(entries),'logicalBytes':sum(len(ck(D/k if relative else Path(k),v))for k,v in entries.items()),**rec(D/name)}
assert regs['source-pins.json']['files']==18 and regs['input-pins.json']['files']==2905 and regs['input-pins.json']['logicalBytes']==455796828
G=W/'tc-original19-functional190-go-v3-root-20261009/root-go.json';g=load(G);assert g['status']==pr['rootGOStatus'] and g['maximumLoaderCalls']==190 and g['noRetry']is True and g['runtimeGuestAuthorized']is True and g['C2']is False and g['timingAuthorized']is False
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]==freeze[k]
assert len(g['sourceReviews'])==2 and len(set(v['path']for v in g['sourceReviews']))==2
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
for k in ['OFFActualProof','TCActualProof','C95Oracle','C95OracleProof','retainedV2FailureProof']:
 assert g[k]==pr[k];ck(Path(g[k]['path']),g[k])
assert g['retainedV2Failure']==pr['retainedV2Failure']
for v in pr['retainedV2Failure'].values():ck(Path(v['path']),v)
v2p=json.loads(ck(Path(pr['retainedV2FailureProof']['path']),pr['retainedV2FailureProof']));assert v2p['status']=='PASS_INDEPENDENT_SAVED_FAILURE_CURRENT_OFF_TC_FUNCTIONAL190_V2_ONLY' and v2p['remainingUnexecuted']==189
v2a=load(Path(pr['retainedV2Failure']['attempts.json']['path']));assert len(v2a)==1 and v2a[0]['returncode']==2 and v2a[0]['stdout']['bytes']==v2a[0]['stderr']['bytes']==0
f=g['integrationFixtureProof'];assert f==pr['qualifiedIntegrationFixtureProof'];fq=json.loads(ck(Path(f['path']),f));assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
for n,v in load(O/'generated-pins.json').items():ck(Path(n),v)
assert load(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17
oracle=load(Path(pr['C95Oracle']['path']));assert len(oracle['rows'])==95;oraclemap={(x['workload'],x['n']):x for x in oracle['rows']};assert len(oraclemap)==95
offProof=load(Path(pr['OFFActualProof']['path']));tcProof=load(Path(pr['TCActualProof']['path']));ownImages={'OFF':{v['workload']:v for v in offProof['joinedOriginal19Images']},'TC':{v['workload']:v for v in tcProof['joinedOriginal19Images']}}
assert all(len(v)==19 for v in ownImages.values()) and offProof['joinedOriginal19ArtifactWholePayloadIdentity'] and tcProof['joinedOriginal19ArtifactWholePayloadIdentity']
matrix=load(Path(pr['canonicalMatrix']));assert len(pr['entries'])==len(matrix['entries'])==19
expected=[]
for e,m in zip(pr['entries'],matrix['entries']):
 assert (e['workload'],e['symbol'],e['iterations'],e['source']['sha256'])==(m['workload'],m['symbol'],m['iterations'],m['expectedSourceSha256'])
 for n in e['iterations']:
  cv=oraclemap[e['workload'],n];assert cv['sourceSHA256']==e['source']['sha256'] and cv['symbol']==e['symbol'] and type(cv['result'])is int and cv['result']in [0,1]
  for arm in ['OFF','TC']:expected.append((e,n,arm,cv['result']))
rows=load(O/'attempts.json');results=load(O/'results.json');assert len(rows)==140 and len(results)==139 and len(pr['cases'])==len(expected)==190
last=rows[-1];assert last['label']=='slre-TC-n32';resultsForAudit=results+[{'label':last['label'],'case':pr['cases'][139],'returncode':last['returncode'],'report':last['structuredReportObservation'],'arena':last['counterObservation']['values'],'rawStdoutSHA256':last['stdout']['sha256'],'rawStderrSHA256':last['stderr']['sha256'],'memoryObservation':last['controllerObservation']['memoryObservation'],'strictOldMemoryPolicyPassed':False}]
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
# Independently specified strict report grammar; no permissive JSON/status fallback.
PAT=re.compile(rb'\{:status :ok :result (-?[0-9]{1,20}) :fuel \{:initial ([0-9]{1,20}) :remaining ([0-9]{1,20})\} :heap \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :string-pool \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vectors \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vector-items \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\}\}\n')
summ=[];pairRows=[];sampletotal=0;gaps=[]
for i,(row,c,result,(e,n,arm,canswer))in enumerate(zip(rows,pr['cases'],resultsForAudit,expected)):
 label=c['label'];image=ownImages[arm][e['workload']];assert c['native']==image['native'] and c['container']==image['container'] and c['offset']==image['offset'] and c['source']==image['source'] and e['iterations']==image['iterations']
 assert result['case']==c and result['returncode']==0 and result['label']==label
 assert (c['workload'],c['profile'],c['arm'],c['expectedResult'],c['source'],c['symbol'])==(e['workload'],n,arm,canswer,e['source'],e['symbol'])
 assert c['arity']==1 and c['nativeArgv']==[pr['loader'],c['native']['path'],str(c['offset']),'1','aarch64','-',str(n)] and '--'not in c['nativeArgv']
 assert row['index']==i+1 and row['label']==label and row['nativeArgv']==c['nativeArgv'] and row['environment']==pr['environment'] and row['state']=='terminal' and row['returncode']==0 and row['waitEntered'] and not row['waitUncertain'] and row['signalingAuthorityRetired'] and row['captureStopAcknowledged'] and row['failure']==(None if i<139 else 'AssertionError()') and row['watchdogErrors']==[]
 seal=load(O/(label+'.admission.json'));assert row['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd'] and row['argv'][3].isdigit() and row['argv'][4]=='--admission-sha' and row['argv'][5]==rec(O/(label+'.admission.json'))['sha256'] and row['argv'][6:]==['--',*c['nativeArgv']]
 assert seal['index']==i+1 and seal['rootGO']==rec(G) and seal['sourcePinsSHA256']==g['sourcePinsSHA256'] and seal['preregistrationSHA256']==g['preregistrationSHA256']
 for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']:assert seal[k]==c[k]
 for k in ['native','container','source']:ck(Path(c[k]['path']),c[k])
 payload,exports=container(Path(c['container']['path']).read_bytes());assert payload==Path(c['native']['path']).read_bytes() and [c['symbol'],c['offset'],1]in exports
 raw={}
 for k,suffix in [('stdout','.stdout'),('stderr','.stderr'),('limitJournal','.limit-journal.jsonl'),('memoryJournal','.memory-journal.jsonl')]:raw[k]=ck(O/(label+suffix),row[k])
 obs=row['controllerObservation'];cap=obs['capture'];mr=obs['memoryAdmissionRecord'];assert cap['stoppedWriter'] and cap['completeRaw'] and cap['EOF']=={'stdout':True,'stderr':True} and cap['errors']==[] and not any(cap['dropped'].values()) and cap['hashes']=={k:row[k]for k in ['stdout','stderr']}
 assert 0<len(raw['stdout'])<=65536 and len(raw['stderr'])<=1048576;m=PAT.fullmatch(raw['stdout']);assert m is not None
 nums=list(map(int,m.groups()));answer,initial,remaining=nums[:3];caps=nums[3::2];used=nums[4::2];assert -(1<<63)<=answer<(1<<63) and answer==canswer and initial==16777216 and 0<=remaining<=initial and caps==[2097152,65536,4096,65536] and all(0<=u<=cp for u,cp in zip(used,caps))
 kv=re.findall(rb':([a-z-]+) ([0-9]{1,20})',raw['stderr']);arena={k.decode():int(v)for k,v in kv};assert len(kv)==17 and list(arena)==FIELDS and b'KEXE_ARENA_USE {'+b' '.join(b':'+k+b' '+v for k,v in kv)+b'}\n'==raw['stderr'] and all(0<=v<2**64 for v in arena.values())
 assert [arena[k]for k in FIELDS[:4]]==used and arena['heap-bytes']==16*arena['pairs']+arena['string-pool-bytes']+16*arena['vectors']+8*arena['vector-items']
 decoded={'status':'ok','result':answer,'trapExit':None,'initialFuel':initial,'remainingFuel':remaining,'metered':True,'arenaCapacities':dict(zip(FIELDS[:4],caps)),'arenaUsed':dict(zip(FIELDS[:4],used))};report={'result':answer,'fuelInitial':initial,'fuelRemaining':remaining,'fuelConsumed':initial-remaining,'arena17':arena,'structured':decoded};assert result['report']==row['structuredReportObservation']==report and result['arena']==arena and result['rawStdoutSHA256']==row['stdout']['sha256'] and result['rawStderrSHA256']==row['stderr']['sha256'] and row['counterObservation']=={'status':'valid','values':arena}
 jl=[json.loads(x)for x in raw['limitJournal'].splitlines()];assert len(jl)==6 and len(raw['limitJournal'])<=65536;ek=sorted(pr['environment']);ew=jl[0];assert ew=={'stage':'environment-admission','suppliedKeyNames':ek,'runtimeExtraKeyNames':ew['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':ek,'nativeExecEnvironmentExact':True} and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,want)in enumerate([('RLIMIT_FSIZE',[67108864,67108864]),('RLIMIT_CPU',[30,31])]):
  bef,aft=jl[1+2*k:3+2*k];assert bef['index']==k+1 and bef['limit']==name and bef['stage']=='before' and bef['desired']==want and all(b==9223372036854775807 or b>=w for b,w in zip(bef['before'],want));assert aft=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':want}
 assert jl[5]=={'stage':'exec-ready','argv':c['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':31}
 samples=[json.loads(x)for x in raw['memoryJournal'].splitlines()];assert 1<=len(samples)==row['memorySamples']<=2048 and row['memoryJournalBytes']==len(raw['memoryJournal'])<=8388608;prev=0;birth=None;sums=[];births={}
 for ordinal,tm,pgid,members in samples:
  assert ordinal==len(sums)+1 and tm>prev and pgid==row['pid'] and 1<=len(members)<=2 and len(set(x[0]for x in members))==len(members);leaders=[x for x in members if x[0]==pgid];assert len(leaders)==1
  if birth is None:birth=leaders[0][1]
  assert birth==leaders[0][1]>0
  for pid,bt,foot in members:
   assert pid>0 and bt>0 and 0<=foot<2**64
   if pid in births:assert births[pid]==bt
   births[pid]=bt
  total=sum(x[2]for x in members);assert total<=4294967296;sums.append(total);prev=tm
 assert mr['acceptedSamples']==len(samples) and mr['acceptedLeaderBirthBound'] and mr['otherRefusals']==([] if i<139 else ['failure-pid-not-previously-bound']) and mr['completePipeEOF'] and mr['stoppedClosedCapture'] and not mr['rawTruncated'] and mr['captureErrors']==[] and mr['exactDirectChildWait']=='closed0' and not mr['waitUncertain'] and mr['withinOriginalDeadline'] and mr['groupAuthorityRetired'] and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0 and mr['loaderWaitProtocolPinned']
 assert obs['semanticQualification']==(i<139) and obs['sampleReceiptPersistenceQualified'] and obs['sampleCount']==len(samples) and result['memoryObservation']==obs['memoryObservation'] and result['strictOldMemoryPolicyPassed']==obs['strictOldMemoryPolicyPassed']
 failure=mr['failure']
 if i==139:
  assert failure=={'contextVersion':'owned-group-sampling-failure-context-v1','typedOrigin':'fresh-owned-group-api-v1','stage':'member-getpgid','pid':14948,'queryOrdinal':21,'errno':3,'failureClass':'kernel-oserror'} and row['pid']==14947 and len(samples)==2 and set(births)=={14947} and failure['pid']not in births
  assert obs['status']=='REFUSE' and not obs['strictOldMemoryPolicyPassed'] and cap['firstFailure']=='sampling-uncertainty' and obs['memoryObservation']=={'status':'refused','strictOldSamplingRefusal':True,'sampleCompleteness':'unavailable','hardPeakQualified':False}
 elif failure is None:
  assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['strictOldMemoryPolicyPassed'] and cap['firstFailure']is None and obs['memoryObservation']=={'status':'sampled-observations-only','strictOldSamplingRefusal':False,'sampleCompleteness':'finite-samples-only','hardPeakQualified':False}
 else:
  assert failure['typedOrigin']=='fresh-owned-group-api-v1' and failure['contextVersion']=='owned-group-sampling-failure-context-v1' and failure['failureClass']in ['kernel-oserror','kernel-failed-return'] and failure['errno']==3 and failure['stage']in ['leader-getpgid','member-getpgid','member-rusage'] and type(failure['queryOrdinal'])is int and failure['queryOrdinal']>0 and failure['pid']in births
  assert obs['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP' and not obs['strictOldMemoryPolicyPassed'] and cap['firstFailure']=='sampling-uncertainty' and obs['memoryObservation']=={'status':'termination-gap-unavailable','strictOldSamplingRefusal':True,'sampleCompleteness':'gap-unavailable','missingFootprint':None,'zeroSynthesized':False,'hardPeakQualified':False};gaps.append({'label':label,'failure':failure})
 ev=obs['controllerEvents'];assert ev.count('wait-enter')==1 and ev.index('retire:before-watchdog-stop-and-wait')<ev.index('wait-enter') and not any(x=='group-operation'for x in ev[ev.index('wait-enter')+1:]);sampletotal+=len(samples)
 summ.append({'admittedByCampaign':i<139,'label':label,'workload':e['workload'],'n':n,'arm':arm,'directWait':0,'report':report,'samples':len(samples),'sampleSums':sums,'strictSampledPolicyPassed':obs['strictOldMemoryPolicyPassed'],'raw':{k:row[k]for k in ['stdout','stderr','limitJournal','memoryJournal']},'admission':rec(O/(label+'.admission.json'))})
 if i%2==1:
  a,b=summ[-2:];assert (a['workload'],a['n'],a['arm'],b['arm'])==(e['workload'],n,'OFF','TC') and all(a['report'][k]==b['report'][k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']);pairRows.append({'workload':e['workload'],'n':n,'C95Result':canswer,'OFFTCResult':answer,'fuelConsumed':initial-remaining,'arena17':arena,'allPairFieldsEqual':True,'admittedPair':i<139,'conditionalRawOnly':i==139})
assert len(pairRows)==70 and sum(x['admittedPair']for x in pairRows)==69 and pairRows[-1]['workload']=='slre' and pairRows[-1]['n']==32 and pairRows[-1]['conditionalRawOnly']
assert load(O/'terminal.json')=={'loaderCalls':140,'allChildrenClosed':True,'failure':True} and load(O/'failure.json')=={'error':"AssertionError('first failure preserved; no retry')",'loaderCalls':140,'noRetry':True}
assert not (O/'report.json').exists() and len(list(O.glob('*.admission.json')))==140
assert not any((O/(c['label']+'.stdout')).exists() or (O/(c['label']+'.admission.json')).exists()for c in pr['cases'][140:])
assert sampletotal==290 and sum(x['strictSampledPolicyPassed']for x in summ)==136 and len(gaps)==3
r={'status':'PASS_INDEPENDENT_SAVED_FAILURE_CURRENT_OFF_TC_FUNCTIONAL190_V3_ONLY','independent':True,'sourcePinsSHA256':g['sourcePinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'registries':regs,'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'fixture':f,'retainedV2FailureProof':pr['retainedV2FailureProof'],'terminal':rec(O/'terminal.json'),'failure':rec(O/'failure.json'),'attempts':rec(O/'attempts.json'),'admittedResults139':rec(O/'results.json'),'calls':summ,'rawPairs70':pairRows,'closedCalls':140,'admittedResultPrefixCalls':139,'admittedPairs':69,'conditionalRawOnlyPairs':1,'remainingUnexecuted':50,'acceptedSamples':sampletotal,'strictSampledPolicyAcceptedCalls':136,'admittedTypedMemoryGaps':gaps,'strictPhysicalMemoryQualified':False,'campaignComplete':False,'completionAbsent':True,'lastRefusalRecord':rows[-1]['controllerObservation']['memoryAdmissionRecord'],'C95FuelArenaAvailable':False,'C95FuelArena':None,'scope':'Saved 139 admitted results/69 pairs; last SLRE32 TC full raw matches own OFF and savedC95 result, fuel and17arena, but unbound sampler PID refusal disqualifies campaign pair admission. Old V2 failure unchanged.','lastConditionalRaw':summ[-1],'sourceBinding':'All cases join exact current OFF or TC whole payload/export/source/profile proofs and corrected typed i64 argv before any CLI separator.','limits':['Frozen functional190 gate remains failed; do not promote70 raw pairs to70 admitted pairs or full19 result.','member-getpgid PID14948/query21/errno3 persisted; accepted leader14947 only means failure PID not previously bound. Unknown kernel scheduling/termination cause; do not relax policy or synthesize missing footprint.','All140 complete EOF/capture journals and directparentwait0 are saved receipts/source assertions, not external syscall chronology proof.','Finite soft sampling and admitted gaps do not prove hardpeak/atomic census.','SavedC95 supplies Boolean only; no current C host/fuel/arena/timing comparison.','No speed/C-or-better/fullselfhost/CID cache performance qualification.','Root outer session72947 CLOSED1 attribution supplied separately; no saved raw outertool receipt inspected.'],'operations':{'savedDataOnly':True,'nativeThreadsPipesProcessNetworkAPICalls':0,'reruns':0,'frozenSubjectWrites':0},'preparedCompleteAuditorPreserved':rec(R/'validate_saved.py')}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
