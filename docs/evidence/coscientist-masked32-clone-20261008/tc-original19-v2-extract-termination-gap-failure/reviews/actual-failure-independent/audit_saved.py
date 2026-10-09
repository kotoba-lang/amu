from pathlib import Path
import hashlib,json,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-fixedpoint-source-v2-20261009';O=D/'run-outputs';R=Path(__file__).parent;G=W/'tc-original19-fixedpoint-go-v2-root-20261009/root-go.json'
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=h(b))
def ck(p,v):
 assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink(),str(p);b=p.read_bytes();assert len(b)==v['bytes'] and h(b)==v['sha256'],str(p);return b
def load(p):return json.loads(p.read_bytes())
g=load(G);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');regs={}
for n,x,rel in [('source-pins.json',sp,True),('input-pins.json',ip,False)]:
 total=sum(len(ck(D/k if rel else Path(k),v)) for k,v in x.items());regs[n]={'files':len(x),'logicalBytes':total,**rec(D/n)}
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]
assert g['status']==pr['rootGOStatus']=='GO_TC_ORIGINAL19_FIXEDPOINT44_V2' and g['C2'] is False and g['maximumLoaderCalls']==44 and g['noRetry'] and not g['runtimeGuestAuthorized'] and not g['timingAuthorized']
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus'];assert all(q[k]==g[k] for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
fp=g['integrationFixtureProof'];fq=json.loads(ck(Path(fp['path']),fp));assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
mat=load(Path(pr['canonicalMatrix']));assert mat['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70' and len(mat['entries'])==len(pr['entries'])==19
for e,m in zip(pr['entries'],mat['entries']):assert (e['workload'],e['symbol'],e['iterations'],e['source']['sha256'])==(m['workload'],m['symbol'],m['iterations'],m['expectedSourceSha256'])
assert ck(O/'aha-mont64.kotoba',pr['entries'][0]['source'])==Path(pr['entries'][0]['source']['path']).read_bytes()
for p,v in load(O/'generated-pins.json').items():ck(Path(p),v)
# Independent complete container parser, not importing operational code.
def parse_container(b):
 header=b.split(b'\n',1)[0];m=re.fullmatch(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)',header);assert m
 table,payload=b[len(header)+1:].split(b'\n\n',1);lines=table.split(b'\n');assert len(lines)==int(m[2]);ex=[]
 for line in lines:
  x=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);assert x;ex.append([x[1].decode(),int(x[2]),int(x[3])])
 assert len(payload)==int(m[1]) and len(set(x[0] for x in ex))==len(ex) and all(x[1]%4==0 and 0<=x[1]<len(payload)-3 and x[2]<=32 for x in ex)
 return payload,ex
payload,exports=parse_container((O/'aha-mont64.kseed').read_bytes());native=(O/'aha-mont64.bin').read_bytes();assert payload==native and len(native)==3976 and len((O/'aha-mont64.kseed').read_bytes())==4039 and ['bench',3456,1] in exports
pp,px=parse_container(Path(pr['candidateContainer']).read_bytes());assert pp==Path(pr['producer']).read_bytes() and px==[['main',0,0]]
a=load(Path(pr['sourceAssembly']));parts=[Path(a['candidate41']['path'] if n=='seed/41-a64gen.kotoba' else v['path']).read_bytes()+b'\n' for n,v in zip(a['modules'],a['modulePins'])];assert len(parts)==16 and b''.join(parts)==Path(pr['ownSource']).read_bytes()
rows=load(O/'attempts.json');assert len(rows)==2
keys=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];summ=[]
assert load(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off'
for i,row in enumerate(rows):
 case=pr['cases'][i];label=row['label'];assert row['index']==i+1 and row['label']==case['label'] and row['nativeArgv']==case['nativeArgv'] and row['environment']==pr['environment'] and row['returncode']==0 and row['state']=='terminal' and row['waitEntered'] and not row['waitUncertain'] and row['signalingAuthorityRetired'] and row['captureStopAcknowledged'] and not row['watchdogErrors']
 assert row['argv'][:5]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd','3','--admission-sha'] and row['argv'][6:] == ['--']+row['nativeArgv']
 seal=load(O/(label+'.admission.json'));assert h((O/(label+'.admission.json')).read_bytes())==row['argv'][5] and seal['nativeArgv']==row['nativeArgv'] and seal['index']==i+1 and seal['rootGO']==rec(G)
 for n in ['producer','producerContainer','input']:ck(Path(seal[n]['path']),seal[n])
 obs=row['controllerObservation'];raw={}
 for n in ['stdout','stderr','limitJournal','memoryJournal']:
  suffix={'stdout':'.stdout','stderr':'.stderr','limitJournal':'.limit-journal.jsonl','memoryJournal':'.memory-journal.jsonl'}[n];raw[n]=ck(O/(label+suffix),row[n])
 cap=obs['capture'];assert cap['stoppedWriter'] and cap['completeRaw'] and all(cap['EOF'].values()) and not any(cap['dropped'].values()) and cap['errors']==[] and cap['hashes']=={n:row[n] for n in ['stdout','stderr']}
 if i==0:
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output "([^"]+)", :bytes ([0-9]+)\}\n',raw['stdout']);assert m and m[1].decode()==case['outputPath'] and int(m[2])==4039
 else:
  m=re.fullmatch(rb'\{:ok true, :output "([^"]+)", :offset ([0-9]+), :length ([0-9]+), :arity ([0-9]+)\}\n',raw['stdout']);assert m and m[1].decode()==case['outputPath'] and [int(m[j]) for j in [2,3,4]]==[3456,3976,1]
 s=raw['stderr'];assert s.startswith(b'KEXE_ARENA_USE {') and s.endswith(b'}\n');kv=re.findall(rb':([a-z-]+) ([0-9]+)',s);v={k.decode():int(x) for k,x in kv};assert list(v)==keys and len(kv)==17 and b'KEXE_ARENA_USE {'+b' '.join(b':'+k+b' '+x for k,x in kv)+b'}\n'==s and v==row['counterObservation']['values'] and all(0<=x<2**64 for x in v.values())
 jl=[json.loads(x) for x in raw['limitJournal'].splitlines()];assert len(jl)==6 and jl[0]['nativeExecEnvironmentExact'] and not jl[0]['missingKeyNames'] and not jl[0]['changedExpectedKeyNames'] and set(jl[0]['runtimeExtraKeyNames'])<= {'__CF_USER_TEXT_ENCODING'} and jl[0]['nativeExecKeyNames']==sorted(pr['environment'])
 for before,after,name,des in [(jl[1],jl[2],'RLIMIT_FSIZE',[67108864,67108864]),(jl[3],jl[4],'RLIMIT_CPU',[1800,1801])]:assert before['stage']=='before' and before['limit']==name and before['desired']==des and after['outcome']=='installed' and after['readback']==des
 assert jl[5]['stage']=='exec-ready' and jl[5]['argv']==row['nativeArgv'] and jl[5]['ASSetterRequested'] is False
 samples=[json.loads(x) for x in raw['memoryJournal'].splitlines()];assert len(samples)==3==row['memorySamples'];birth=None;prevTime=0;totals=[]
 for ordinal,tm,pgid,members in samples:
  assert ordinal==len(totals)+1 and tm>prevTime and pgid==row['pid'] and 1<=len(members)<=2 and len(set(x[0] for x in members))==len(members)
  leader=[x for x in members if x[0]==pgid];assert len(leader)==1 and leader[0][1]>0
  if birth is None:birth=leader[0][1]
  assert birth==leader[0][1] and all(x[1]>0 and 0<=x[2]<2**64 for x in members);total=sum(x[2] for x in members);assert total<=4294967296;totals.append(total);prevTime=tm
 mr=obs['memoryAdmissionRecord'];assert mr['acceptedSamples']==3 and mr['acceptedLeaderBirthBound'] and mr['otherRefusals']==[] and mr['completePipeEOF'] and mr['stoppedClosedCapture'] and not mr['rawTruncated'] and mr['captureErrors']==[] and mr['exactDirectChildWait']=='closed0' and not mr['waitUncertain'] and mr['withinOriginalDeadline'] and mr['groupAuthorityRetired'] and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0 and mr['loaderWaitProtocolPinned']
 if i==0:assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['strictOldMemoryPolicyPassed'] and mr['failure'] is None
 else:
  assert obs['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP' and obs['semanticQualification'] and not obs['strictOldMemoryPolicyPassed'];assert mr['failure']=={'contextVersion':'owned-group-sampling-failure-context-v1','typedOrigin':'fresh-owned-group-api-v1','stage':'leader-getpgid','pid':52693,'queryOrdinal':29,'errno':3,'failureClass':'kernel-oserror'};assert cap['firstFailure']=='sampling-uncertainty' and obs['memoryObservation']['missingFootprint'] is None and not obs['memoryObservation']['zeroSynthesized']
 summ.append({'label':label,'pid':row['pid'],'waitReturncode':0,'raw':{n:row[n] for n in ['stdout','stderr','limitJournal','memoryJournal']},'physicalFootprintTotals':totals,'leaderBirth':birth,'counterValues':v,'memoryStatus':obs['status'],'strictMemoryPassed':obs['strictOldMemoryPolicyPassed']})
term=load(O/'terminal.json');fail=load(O/'failure.json');assert term=={'loaderCalls':2,'allChildrenClosed':True,'failure':True} and fail['loaderCalls']==2 and fail['noRetry']
for n in ['report.json','images.json','generations.json']:assert not (O/n).exists()
assert all(not (O/(x['label']+'.stdout')).exists() for x in pr['cases'][2:])
r={'status':'PASS_INDEPENDENT_SAVED_FAILURE_TC_ORIGINAL19_FIXEDPOINT44_V2_ONLY','independent':True,'priorAuthorshipOfSubject':False,'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'subject':str(D),'registries':regs,'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'integrationFixtureProof':fp,'terminal':rec(O/'terminal.json'),'failure':rec(O/'failure.json'),'attempts':rec(O/'attempts.json'),'closedCalls':2,'remainingUnexecutedCalls':42,'calls':summ,'campaignQualified':False,'strictMemoryQualification':False,'conditionalAhaArtifactIdentityOnly':{'verified':True,'originalSource':pr['entries'][0]['source'],'container':rec(O/'aha-mont64.kseed'),'native':rec(O/'aha-mont64.bin'),'wholePayloadEqual':True,'exports':exports,'selectedExport':['bench',3456,1],'producer':rec(Path(pr['producer'])),'scope':'Conditional identity of saved aha-mont64 build/extract through pinned G0; no guest correctness or completed original19/fixedpoint campaign.'},'typedFailure':rows[1]['controllerObservation']['memoryAdmissionRecord']['failure'],'provenance':{'source':str(D/'typed-adapter.py'),'operation':'Sampler attempt leader-getpgid wraps os.getpgid(owned) and journals kernel OSError errno; counter is per sampler API attempt, not sample ordinal.','unknown':'Underlying kernel scheduling/termination cause and missing physical footprint cannot be inferred.'},'limitations':['Sample sums are finite soft footprint observations, not hard peak or atomic group census.','Two direct-loader-parent wait0 receipts plus pinned loader wait protocol; no independent syscall trace of all descendants.','Controller diagnostic classification does not satisfy frozen strictOldMemoryPolicyPassed requirement; driver correctly stops, completion/images/generations absent.','No 19 workload, new selfbuild G1/G2/G3, runtime guest, performance, ComputeCID/ResultCID effect qualification.','Prior failed campaigns preserved in pinned closure, no retries or frozen subject writes.'],'reviewerOperations':{'savedFilesystemAndPureArithmeticOnly':True,'operationalReruns':0,'nativeProcessThreadFDPipeAPIOrNetworkCalls':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
