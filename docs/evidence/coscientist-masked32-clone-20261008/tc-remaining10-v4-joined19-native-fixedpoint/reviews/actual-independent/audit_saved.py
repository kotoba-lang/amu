from pathlib import Path
import hashlib,json,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-remaining10-fixedpoint-source-v4-20261009';O=D/'run-outputs';R=Path(__file__).parent;G=W/'tc-original19-remaining10-fixedpoint-go-v4-dense-20261009/root-go.json';h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=h(b))
def ck(p,v):
 assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink(),str(p);b=p.read_bytes();assert len(b)==v['bytes'] and h(b)==v['sha256'],str(p);return b
def load(p):return json.loads(p.read_bytes())
def parse(b):
 hd,rest=b.split(b'\n',1);m=re.fullmatch(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)',hd);assert m;tb,payload=rest.split(b'\n\n',1);ex=[]
 for line in tb.split(b'\n'):
  x=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);assert x;ex.append([x[1].decode(),int(x[2]),int(x[3])])
 assert len(payload)==int(m[1]) and len(ex)==int(m[2]) and len(set(x[0] for x in ex))==len(ex) and all(x[1]%4==0 and 0<=x[1]<len(payload)-3 and x[2]<=32 for x in ex);return payload,ex
g=load(G);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');regs={}
for n,x,rel in [('source-pins.json',sp,True),('input-pins.json',ip,False)]:
 total=sum(len(ck(D/k if rel else Path(k),v)) for k,v in x.items());regs[n]={'files':len(x),'logicalBytes':total,**rec(D/n)}
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]
assert rec(G)['sha256']=='9257b55145840b78b4a8cae003845c35ef5f0ed998808d239a0205adfa607f30' and g['status']==pr['rootGOStatus'] and g['maximumLoaderCalls']==10 and g['noRetry'] and not g['C2'] and not g['timingAuthorized'] and not g['runtimeGuestAuthorized']
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k] for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
fp=g['integrationFixtureProof'];fq=json.loads(ck(Path(fp['path']),fp));assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
for name in ['retainedArtifactProof','retainedSuiteProof']:
 v=g[name];q=json.loads(ck(Path(v['path']),v));assert v==pr[name] and q['status']==pr[name+'Status'] and q['campaignQualified'] is False
suite=load(Path(g['retainedSuiteProof']['path']));assert suite['failureRecord']['otherRefusals']==['failure-pid-not-previously-bound']
mat=load(Path(pr['canonicalMatrix']));assert len(mat['entries'])==len(pr['entries'])==19
for e,m in zip(pr['entries'],mat['entries']):assert (e['workload'],e['symbol'],e['iterations'],e['source']['sha256'])==(m['workload'],m['symbol'],m['iterations'],m['expectedSourceSha256'])
for p,v in load(O/'generated-pins.json').items():ck(Path(p),v)
pp,px=parse(Path(pr['candidateContainer']).read_bytes());assert pp==Path(pr['producer']).read_bytes() and px==[['main',0,0]]
a=load(Path(pr['sourceAssembly']));parts=[Path(a['candidate41']['path'] if n=='seed/41-a64gen.kotoba' else v['path']).read_bytes()+b'\n' for n,v in zip(a['modules'],a['modulePins'])];assert len(parts)==16 and b''.join(parts)==Path(pr['ownSource']).read_bytes()==(O/'unity-tc.kotoba').read_bytes()
rows=load(O/'attempts.json');assert len(rows)==10 and load(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17;keys=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];summ=[];sampletotal=0
for i,row in enumerate(rows):
 case=pr['cases'][i];label=row['label'];assert row['index']==i+1 and label==case['label'] and row['nativeArgv']==case['nativeArgv'] and row['environment']==pr['environment'] and row['state']=='terminal' and row['returncode']==0 and row['waitEntered'] and not row['waitUncertain'] and row['signalingAuthorityRetired'] and row['captureStopAcknowledged'] and row['watchdogErrors']==[] and row['failure'] is None
 assert row['argv'][:5]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd','3','--admission-sha'] and row['argv'][6:]==['--']+row['nativeArgv'];seal=load(O/(label+'.admission.json'));assert rec(O/(label+'.admission.json'))['sha256']==row['argv'][5] and seal['nativeArgv']==row['nativeArgv'] and seal['index']==i+1 and seal['rootGO']==rec(G)
 for n in ['producer','producerContainer','input']:ck(Path(seal[n]['path']),seal[n])
 prod,exp=parse(Path(seal['producerContainer']['path']).read_bytes());assert prod==Path(seal['producer']['path']).read_bytes() and exp==[['main',0,0]]
 obs=row['controllerObservation'];cap=obs['capture'];raw={}
 for n,suffix in [('stdout','.stdout'),('stderr','.stderr'),('limitJournal','.limit-journal.jsonl'),('memoryJournal','.memory-journal.jsonl')]:raw[n]=ck(O/(label+suffix),row[n])
 assert cap['stoppedWriter'] and cap['completeRaw'] and all(cap['EOF'].values()) and not any(cap['dropped'].values()) and not cap['errors'] and cap['hashes']=={n:row[n] for n in ['stdout','stderr']}
 if i%2==0:
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output "([^"]+)", :bytes ([0-9]+)\}\n',raw['stdout']);assert m and m[1].decode()==case['outputPath'] and int(m[2])==len(Path(case['outputPath']).read_bytes());report={'kind':'compile','containerBytes':int(m[2])}
 else:
  m=re.fullmatch(rb'\{:ok true, :output "([^"]+)", :offset ([0-9]+), :length ([0-9]+), :arity ([0-9]+)\}\n',raw['stdout']);assert m and m[1].decode()==case['outputPath'];report={'kind':'extract','offset':int(m[2]),'nativeBytes':int(m[3]),'arity':int(m[4])};assert report['nativeBytes']==len(Path(case['outputPath']).read_bytes())
 assert report==row['structuredReportObservation']
 s=raw['stderr'];kv=re.findall(rb':([a-z-]+) ([0-9]+)',s);v={k.decode():int(x) for k,x in kv};assert list(v)==keys and len(kv)==17 and b'KEXE_ARENA_USE {'+b' '.join(b':'+k+b' '+x for k,x in kv)+b'}\n'==s and v==row['counterObservation']['values'] and all(0<=x<2**64 for x in v.values())
 jl=[json.loads(x) for x in raw['limitJournal'].splitlines()];assert len(jl)==6 and jl[0]['nativeExecEnvironmentExact'] and not jl[0]['missingKeyNames'] and not jl[0]['changedExpectedKeyNames'] and set(jl[0]['runtimeExtraKeyNames'])<= {'__CF_USER_TEXT_ENCODING'} and jl[0]['nativeExecKeyNames']==sorted(pr['environment'])
 for bef,aft,name,des in [(jl[1],jl[2],'RLIMIT_FSIZE',[67108864,67108864]),(jl[3],jl[4],'RLIMIT_CPU',[1800,1801])]:assert bef['limit']==name and bef['desired']==des and aft['outcome']=='installed' and aft['readback']==des
 assert jl[5]['argv']==row['nativeArgv'] and not jl[5]['ASSetterRequested']
 samples=[json.loads(x) for x in raw['memoryJournal'].splitlines()];assert len(samples)==row['memorySamples'];sampletotal+=len(samples);birth=None;prevtime=0;totals=[];seen=set()
 for ordinal,tm,pgid,members in samples:
  assert ordinal==len(totals)+1 and tm>prevtime and pgid==row['pid'] and 1<=len(members)<=2 and len(set(x[0] for x in members))==len(members);leader=[x for x in members if x[0]==pgid];assert len(leader)==1
  if birth is None:birth=leader[0][1]
  assert birth==leader[0][1]>0 and all(x[1]>0 and 0<=x[2]<2**64 for x in members);total=sum(x[2] for x in members);assert total<=4294967296;totals.append(total);prevtime=tm;seen.update(x[0] for x in members)
 mr=obs['memoryAdmissionRecord'];assert mr['acceptedSamples']==len(samples) and mr['acceptedLeaderBirthBound'] and mr['completePipeEOF'] and mr['stoppedClosedCapture'] and not mr['rawTruncated'] and not mr['captureErrors'] and mr['exactDirectChildWait']=='closed0' and not mr['waitUncertain'] and mr['withinOriginalDeadline'] and mr['groupAuthorityRetired'] and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0 and mr['loaderWaitProtocolPinned'] and mr['otherRefusals']==[] and obs['semanticQualification'] and obs['sampleReceiptPersistenceQualified']
 if i<9:assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['strictOldMemoryPolicyPassed'] and mr['failure'] is None and cap['firstFailure'] is None and obs['memoryObservation']=={'status':'sampled-observations-only','strictOldSamplingRefusal':False,'sampleCompleteness':'finite-samples-only','hardPeakQualified':False}
 else:
  assert obs['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP' and not obs['strictOldMemoryPolicyPassed'];assert mr['failure']=={'contextVersion':'owned-group-sampling-failure-context-v1','typedOrigin':'fresh-owned-group-api-v1','stage':'leader-getpgid','pid':77473,'queryOrdinal':29,'errno':3,'failureClass':'kernel-oserror'} and mr['failure']['pid'] in seen and cap['firstFailure']=='sampling-uncertainty';assert obs['memoryObservation']=={'status':'termination-gap-unavailable','strictOldSamplingRefusal':True,'sampleCompleteness':'gap-unavailable','missingFootprint':None,'zeroSynthesized':False,'hardPeakQualified':False}
 summ.append({'index':i+1,'label':label,'pid':row['pid'],'directWait':0,'sampleCount':len(samples),'sampleFootprintSums':totals,'controllerStatus':obs['status'],'strictMemory':obs['strictOldMemoryPolicyPassed'],'raw':{n:row[n] for n in ['stdout','stderr','limitJournal','memoryJournal']}})
assert sampletotal==200
report=load(O/'report.json');images=load(O/'images.json');gens=load(O/'generations.json');assert report['images']==images and report['generations']==gens and len(images)==19 and len(gens)==3
for im,e in zip(images,pr['entries']):
 assert im['workload']==e['workload'] and im['source']==e['source'] and im['iterations']==e['iterations'];payload,ex=parse(ck(Path(im['container']['path']),im['container']));assert payload==ck(Path(im['native']['path']),im['native']) and ex==im['exports'];selected=[x for x in ex if x[0]==e['symbol']];assert len(selected)==1 and selected[0][2]==1 and selected[0][1]==im['offset']
 if im.get('retained'):
  original=next(x for x in load(Path(pr['retainedImages'])) if x['workload']==im['workload']);assert all(im[k]==v for k,v in original.items())
 else:assert ck(O/(e['workload']+'.kotoba'),e['source'])==Path(e['source']['path']).read_bytes()
ud=next(x for x in images if x['workload']=='ud');assert ud['admittedByCampaign'] is False and report['retainedUnadmittedUDRemainsRefused'] is True
for im in gens:
 payload,ex=parse(ck(Path(im['container']['path']),im['container']));assert ex==[['main',0,0]] and payload==ck(Path(im['native']['path']),im['native'])==pp and Path(im['container']['path']).read_bytes()==Path(pr['candidateContainer']).read_bytes();assert ck(Path(im['ownSource']['path']),im['ownSource'])==Path(pr['ownSource']).read_bytes() and im['previousContainerEqual'] and im['previousNativeEqual']
assert load(O/'terminal.json')=={'loaderCalls':10,'allChildrenClosed':True,'failure':False} and not (O/'failure.json').exists()
for n,v in report['evidence'].items():assert v['path']==str(O/n);ck(Path(v['path']),v)
assert report['rootGO']==rec(G) and report['sourcePinsSHA256']==g['sourcePinsSHA256'] and report['status']=='COMPLETE_TC_JOINED_ORIGINAL19_ARTIFACT_IDENTITY_G1_G2_G3_FIXEDPOINT_MEMORY_PARTIAL_ONLY' and report['strictPhysicalMemoryQualified'] is False and report['newClosedLoaderCalls']==10 and report['retainedClosedCompileExtractCalls']==34 and report['joinedOriginal19CompileExtractCalls']==38
for n in ['runtimeGuestExecuted','performanceQualified','officialScore','fullSelfhostGoalAchieved','C2']:assert report[n] is False
code=(D/'run.py').read_text();assert code.index("finally:save(O/'terminal.json'")<code.index("durable terminal before COMPLETE")<code.rindex("save(O/'report.json'")
r={'status':'PASS_INDEPENDENT_ACTUAL_TC_JOINED_ORIGINAL19_ARTIFACT_IDENTITY_G1_G2_G3_MEMORY_PARTIAL_ONLY','independent':True,'priorAuthorshipOfSubject':False,'subject':str(D),'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'registries':regs,'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'integrationFixtureProof':fp,'retainedAhaProof':g['retainedArtifactProof'],'retainedSuiteProof':g['retainedSuiteProof'],'savedCompletion':rec(O/'report.json'),'terminal':rec(O/'terminal.json'),'newClosedCalls':10,'acceptedSampleRows':200,'newStrictAcceptedCalls':9,'newAdmittedDiagnosticGapCalls':1,'calls':summ,'joinedOriginal19ArtifactWholePayloadIdentity':True,'joinedOriginal19Images':images,'current16OwnSource':rec(Path(pr['ownSource'])),'G0Native':rec(Path(pr['producer'])),'G0Container':rec(Path(pr['candidateContainer'])),'newGenerations':gens,'G0G1G2G3WholeNativeEqual':True,'G0G1G2G3WholeContainerEqual':True,'strictPhysicalMemoryQualified':False,'retainedUDRemainsRefused':True,'diagnosticGap':rows[-1]['controllerObservation']['memoryAdmissionRecord'],'validLastEvidence':'Saved terminal closed10/no failure and final completion binds all six evidence receipts and GO. Frozen source publishes terminal then final guard then report. No independent persistence syscall chronology trace.','qualificationScope':'Joined saved original19 source-bound compiler artifact identities plus three new current16 TC own-source generations with full native/container byte stability; memory partial. UD retained whole-payload identity is unadmitted raw artifact evidence, never repaired sampler semantic admission.','limitations':['OldV2/V3 campaigns remain failed; retainedaha strictfalse and UD REFUSE permanent. NewG3extract typed previously-bound leader gap accepted only by explicit separate artifact policy, not strict memory.','Finite sampled physical-footprint sums and source-bound loader wait are not hard peak/atomic census/full kernel trace.','No original19 guest semantics, C-or-better performance, official score, ComputeCID/ResultCID effect or full selfhost goal.','Outer roottool CLOSED0 attribution separate from durable direct-parent wait receipts.'],'reviewerOperations':{'savedFilesystemPureArithmeticOnly':True,'reruns':0,'nativeProcessThreadFDPipeNetworkAPICalls':0,'frozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
