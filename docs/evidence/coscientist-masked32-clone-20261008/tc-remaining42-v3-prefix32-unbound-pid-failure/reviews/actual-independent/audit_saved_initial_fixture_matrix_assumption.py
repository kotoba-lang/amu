from pathlib import Path
import hashlib,json,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-remaining42-fixedpoint-source-v3-20261009';O=D/'run-outputs';R=Path(__file__).parent;G=W/'tc-original19-remaining42-fixedpoint-go-v3-dense-20261009/root-go.json';h=lambda b:hashlib.sha256(b).hexdigest()
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
assert g['status']==pr['rootGOStatus'] and g['maximumLoaderCalls']==42 and g['noRetry'] and not g['C2'] and not g['timingAuthorized'] and not g['runtimeGuestAuthorized']
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k] for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
fp=g['integrationFixtureProof'];fq=json.loads(ck(Path(fp['path']),fp));assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
ret=g['retainedArtifactProof'];retq=json.loads(ck(Path(ret['path']),ret));assert ret==pr['retainedArtifactProof'] and retq['status']==pr['retainedArtifactProofStatus'] and retq['campaignQualified'] is False and retq['strictMemoryQualification'] is False
mat=load(Path(pr['canonicalMatrix']));assert len(mat['entries'])==19 and len(pr['entries'])==18
allentries=[pr['retainedWorkload']]+pr['entries'];assert [x['workload'] for x in allentries]==[x['workload'] for x in mat['entries']]
for e,m in zip(allentries,mat['entries']):assert (e['symbol'],e['iterations'],e['source']['sha256'])==(m['symbol'],m['iterations'],m['expectedSourceSha256'])
for p,v in load(O/'generated-pins.json').items():ck(Path(p),v)
pp,px=parse(Path(pr['candidateContainer']).read_bytes());assert pp==Path(pr['producer']).read_bytes() and px==[['main',0,0]]
a=load(Path(pr['sourceAssembly']));parts=[Path(a['candidate41']['path'] if n=='seed/41-a64gen.kotoba' else v['path']).read_bytes()+b'\n' for n,v in zip(a['modules'],a['modulePins'])];assert len(parts)==16 and b''.join(parts)==Path(pr['ownSource']).read_bytes()
rows=load(O/'attempts.json');assert len(rows)==32 and load(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17;keys=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];summ=[];sampletotal=0
for i,row in enumerate(rows):
 case=pr['cases'][i];label=row['label'];assert row['index']==i+1 and label==case['label'] and row['nativeArgv']==case['nativeArgv'] and row['environment']==pr['environment'] and row['state']=='terminal' and row['returncode']==0 and row['waitEntered'] and not row['waitUncertain'] and row['signalingAuthorityRetired'] and row['captureStopAcknowledged'] and row['watchdogErrors']==[]
 assert row['argv'][:5]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd','3','--admission-sha'] and row['argv'][6:]==['--']+row['nativeArgv'];seal=load(O/(label+'.admission.json'));assert rec(O/(label+'.admission.json'))['sha256']==row['argv'][5] and seal['nativeArgv']==row['nativeArgv'] and seal['index']==i+1 and seal['rootGO']==rec(G)
 for n in ['producer','producerContainer','input']:ck(Path(seal[n]['path']),seal[n])
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
 mr=obs['memoryAdmissionRecord'];assert mr['acceptedSamples']==len(samples) and mr['acceptedLeaderBirthBound'] and mr['completePipeEOF'] and mr['stoppedClosedCapture'] and not mr['rawTruncated'] and not mr['captureErrors'] and mr['exactDirectChildWait']=='closed0' and not mr['waitUncertain'] and mr['withinOriginalDeadline'] and mr['groupAuthorityRetired'] and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0 and mr['loaderWaitProtocolPinned']
 if i<31:assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['strictOldMemoryPolicyPassed'] and obs['semanticQualification'] and mr['failure'] is None and mr['otherRefusals']==[] and row['failure'] is None
 else:
  assert obs['status']=='REFUSE' and not obs['semanticQualification'] and not obs['strictOldMemoryPolicyPassed'];assert mr['failure']=={'contextVersion':'owned-group-sampling-failure-context-v1','typedOrigin':'fresh-owned-group-api-v1','stage':'member-getpgid','pid':67249,'queryOrdinal':21,'errno':3,'failureClass':'kernel-oserror'} and mr['failure']['pid'] not in seen and mr['otherRefusals']==['failure-pid-not-previously-bound'] and cap['firstFailure']=='sampling-uncertainty'
 summ.append({'index':i+1,'label':label,'pid':row['pid'],'directWait':0,'sampleCount':len(samples),'sampleFootprintSums':totals,'controllerStatus':obs['status'],'strictMemory':obs['strictOldMemoryPolicyPassed'],'raw':{n:row[n] for n in ['stdout','stderr','limitJournal','memoryJournal']}})
assert sampletotal==99
artifacts=[]
for e in pr['entries'][:16]:
 n=e['workload'];src=O/(n+'.kotoba');ck(src,e['source']);assert src.read_bytes()==Path(e['source']['path']).read_bytes();k=O/(n+'.kseed');b=O/(n+'.bin');payload,ex=parse(k.read_bytes());assert payload==b.read_bytes();selected=[x for x in ex if x[0]==e['symbol']];assert len(selected)==1 and selected[0][2]==1
 extract=rows[[x['label'] for x in rows].index(n+'-extract')]['structuredReportObservation'];assert extract=={'kind':'extract','offset':selected[0][1],'nativeBytes':len(payload),'arity':1};artifacts.append({'workload':n,'source':e['source'],'container':rec(k),'native':rec(b),'exports':ex,'selectedExport':selected[0],'wholePayloadEqual':True,'admittedByCampaign':n!='ud'})
images=load(O/'images.json');assert len(images)==16 and images[0]['retained'] and images[0]['strictOldMemoryPolicyPassed'] is False and images[0]['retainedArtifactProof']==ret;assert [x['workload'] for x in images]==[pr['retainedWorkload']['workload']]+[e['workload'] for e in pr['entries'][:15]]
for im in images:
 payload,ex=parse(ck(Path(im['container']['path']),im['container']));assert payload==ck(Path(im['native']['path']),im['native']) and ex==im['exports']
assert load(O/'terminal.json')=={'loaderCalls':32,'allChildrenClosed':True,'failure':True};assert load(O/'failure.json')['noRetry'];assert not (O/'report.json').exists() and not (O/'generations.json').exists();assert all(not (O/(x['label']+'.stdout')).exists() for x in pr['cases'][32:]);assert all(not (O/(x+'.kseed')).exists() for x in ['wikisort','xgboost','G1','G2','G3'])
r={'status':'PASS_INDEPENDENT_SAVED_FAILURE_TC_REMAINING42_FIXEDPOINT_V3_ONLY','independent':True,'priorAuthorshipOfSubject':False,'subject':str(D),'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'registries':regs,'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'integrationFixtureProof':fp,'retainedAhaProof':ret,'attempts':rec(O/'attempts.json'),'terminal':rec(O/'terminal.json'),'failure':rec(O/'failure.json'),'newClosedCalls':32,'remainingUnexecutedCalls':10,'acceptedSampleRows':99,'strictAcceptedNewCalls':31,'campaignAdmittedFreshWorkloadPairs':15,'campaignRecordedImagesIncludingRetainedAha':16,'conditionallyByteIdenticalFreshPairsIncludingRefusedUD':16,'conditionallyByteIdenticalJoinedPairsIncludingRetainedAha':17,'missingOriginalWorkloads':['wikisort','xgboost'],'newGenerationsExecuted':0,'campaignQualified':False,'full19ArtifactIdentityQualified':False,'strictJoinedPhysicalMemoryQualified':False,'calls':summ,'freshSavedArtifactIdentityObservations':artifacts,'failureRecord':rows[-1]['controllerObservation']['memoryAdmissionRecord'],'refusedUDScope':'Complete saved UD container/native whole payload equality and raw export observation only. Controller semanticQualification false and unknown member birth identity prevent admission; not a complete accepted workload image.','provenance':'Frozen typed-adapter attempt(member-getpgid,pid,os.getpgid,pid) caught OSError errno3 for PID67249 at API query21; PID absent from previously accepted two sample member sets. Underlying kernel termination/scheduling cause and missing footprint unknown.','limitations':['OldV2 retained aha strict-memory FAIL remains permanent; joining its identity does not change failed campaign.','No G1/G2/G3 fixedpoint or full19/guest/performance/CID effect; remaining ten calls never launched.','Finite soft physical-footprint sample sums do not prove hard peak, atomic census, or absent transient processes.','Direct-parent wait0 and pinned loader childwait source, not independent all-descendant syscall trace.','Saved failure/terminal receipts and source-bound assertions only; outer roottool CLOSED1 attribution separate.'],'reviewerOperations':{'savedFilesystemPureArithmeticOnly':True,'operationalReruns':0,'nativeProcessThreadFDPipeNetworkAPICalls':0,'subjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
