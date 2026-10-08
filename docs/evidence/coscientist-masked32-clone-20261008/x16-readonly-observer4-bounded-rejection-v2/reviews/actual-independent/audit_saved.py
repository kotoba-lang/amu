from pathlib import Path
import json,hashlib,re,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-published-x16-current-observer-source-v2-20261009';O=D/'run-outputs';R=Path(__file__).parent
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
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');regs={}
for name,entries,relative in [('source-pins.json',sp,True),('input-pins.json',ip,False)]:
 total=sum(len(ck(D/k if relative else Path(k),v))for k,v in entries.items());regs[name]={'files':len(entries),'logicalBytes':total,**rec(D/name)}
assert regs['source-pins.json']['files']==25 and regs['input-pins.json']['files']==2819 and regs['input-pins.json']['logicalBytes']==446728459
completion=load(O/'report.json');G=Path(completion['rootGO']['path']);g=json.loads(ck(G,completion['rootGO']));assert g['status']==pr['rootGOStatus'] and g['maximumLoaderCalls']==4 and g['noRetry'] is True and all(g[k]is False for k in ['C2','timingAuthorized','runtimeGuestAuthorized'])
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]
assert len(g['sourceReviews'])==2
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
f=g['integrationFixtureProof'];assert f==pr['qualifiedIntegrationFixtureProof'];fq=json.loads(ck(Path(f['path']),f));assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
p=pr['currentProducerProof'];pq=json.loads(ck(Path(p['path']),p));assert pq['G0G1G2G3WholeNativeEqual'] and pq['G0G1G2G3WholeContainerEqual']
for n,v in load(O/'generated-pins.json').items():ck(Path(n),v)
for n in ['observer-current16.kotoba','statemate.kotoba','nsichneu.kotoba']:assert (O/n).read_bytes()==(D/n).read_bytes()
delta=load(D/'instrumentation-delta.json');bare=(D/'observer-current16.kotoba').read_text().replace((D/'observer-helpers.kotoba').read_text()+'\n','',1);assert bare.replace(delta['newLoop'],delta['oldLoop'],1).replace(delta['newDriver'],delta['oldDriver'],1)==(D/'ordinary-current16.kotoba').read_text()
a=load(Path(pr['sourceAssembly']));parts=[Path(a['candidate41']['path']if n=='seed/41-a64gen.kotoba'else v['path']).read_bytes()+b'\n'for n,v in zip(a['modules'],a['modulePins'])];assert len(parts)==16 and b''.join(parts)==(D/'ordinary-current16.kotoba').read_bytes()
# Frozen validator is pure saved data only. Independent raw reconstruction below supplements it.
vn={};exec(compile((D/'validate_observer.py').read_text(),str(D/'validate_observer.py'),'exec'),vn)
rows=load(O/'attempts.json');results=load(O/'results.json');assert len(rows)==len(results)==4 and results==completion['results'];summ=[];observations=[];samplesTotal=0;negativeControls=[]
keys=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
for i,(row,case,result)in enumerate(zip(rows,pr['cases'],results)):
 label=case['label'];assert row['index']==i+1 and row['label']==label and row['nativeArgv']==case['nativeArgv'] and row['environment']==pr['environment'] and len(row['environment'])==17
 assert row['state']=='terminal' and row['returncode']==0 and row['waitEntered'] and not row['waitUncertain'] and row['signalingAuthorityRetired'] and row['captureStopAcknowledged'] and row['failure']is None and row['watchdogErrors']==[]
 seal=load(O/(label+'.admission.json'));assert row['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd'] and row['argv'][3].isdigit() and row['argv'][4]=='--admission-sha' and row['argv'][5]==rec(O/(label+'.admission.json'))['sha256'] and row['argv'][6:]==['--',*case['nativeArgv']]
 assert seal['nativeArgv']==row['nativeArgv'] and seal['index']==i+1 and seal['label']==label and seal['outputPath']==case['outputPath'] and seal['rootGO']==rec(G) and seal['sourcePinsSHA256']==g['sourcePinsSHA256'] and seal['preregistrationSHA256']==g['preregistrationSHA256']
 for k in ['producer','producerContainer','input']:ck(Path(seal[k]['path']),seal[k])
 pp,pe=container(Path(seal['producerContainer']['path']).read_bytes());assert pp==Path(seal['producer']['path']).read_bytes() and pe==[['main',0,0]]
 raw={}
 for n,suf in [('stdout','.stdout'),('stderr','.stderr'),('limitJournal','.limit-journal.jsonl'),('memoryJournal','.memory-journal.jsonl')]:raw[n]=ck(O/(label+suf),row[n])
 cap=row['controllerObservation']['capture'];assert cap['stoppedWriter'] and cap['completeRaw'] and all(cap['EOF'].values()) and not any(cap['dropped'].values()) and cap['errors']==[] and cap['firstFailure']is None and cap['hashes']=={n:row[n]for n in ['stdout','stderr']}
 assert cap['retained']=={n:len(raw[n])for n in ['stdout','stderr']} and len(raw['stdout'])<=8388608 and len(raw['stderr'])<=1048576
 lines=[];out=raw['stdout']
 if 'ordinaryContainer'in case:lines,out=vn['split'](out)
 if case['kind']=='compile':
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output "([^"]+)", :bytes ([0-9]+)\}\n',out);assert m and m[1].decode()==case['outputPath']
  b=ck(Path(case['outputPath']),result['artifact']);assert int(m[2])==len(b);payload,exports=container(b);report={'kind':'compile','containerBytes':len(b)}
  if i==0:assert exports==[['main',0,0]]
  else:
   assert b==Path(case['ordinaryContainer']).read_bytes();ov=vn['validate'](lines,payload);assert ov['eligiblePairs']==0 and ov['selectedFNs']==[] and ov['selectedSIR']==ov['largeFNOmitted']==ov['budgetFNOmitted']==ov['typedPotentialPairsBoundedFunctions']==0
   # Independently reconstruct actual two-phase zero-selection receipt and every FN summary.
   rr=[(x.split()[0].decode(),list(map(int,x.split()[1:])))for x in lines];h0=rr[0][1];n=h0[2];assert h0[:2]==[0,0] and len(rr)==2*n+6
   for phase,base in [(0,0),(1,n+3)]:
    header=rr[base];assert header[0]=='RH' and header[1][:2]==[phase,0] and header[1][2:4]==h0[2:4];assert rr[base+1]==('RQ',[0]*22)
    for fno in range(n):
     tag,v=rr[base+2+fno];assert tag=='RF' and len(v)==6 and v[:2]==[phase,fno] and 0<=v[2]<h0[3] and 0<=v[4]<=16
     if phase==1:assert v[2]==rr[2+fno][1][2] and v[4:]==rr[2+fno][1][4:]
    assert rr[base+2+n]==('RE',[phase])
   assert not any(t in ['RS','RC','RI']for t,v in rr)
   mutants={'missing-footer':lines[:-1],'extra-footer':lines+[b'RE 1\n'],'unknown-trap':lines+[b'KEXE_TRAP 0\n'],'missing-FN':lines[:2]+lines[3:],'duplicate-owner':[b'RF 0 0 0 0 0 0\n'if x.startswith(b'RF 0 1 ')else x for x in lines],'unselected-emission':lines[:n+3]+[b'RI 1 1 1 0 0 0 1 0\n']+lines[n+3:],'post-SIR-mismatch':[b'RF 1 1 2 1 1 0\n'if x.startswith(b'RF 1 1 ')else x for x in lines]}
   for name,mut in mutants.items():
    try:vn['validate'](mut,payload)
    except (AssertionError,KeyError,IndexError):negativeControls.append(label+':'+name)
    else:raise AssertionError('actual receipt mutation admitted '+name)
   report['observer']=ov;observations.append({'workload':label.replace('-compile',''),'raw':rec(O/(label+'.stdout')),'FNRowsIncludingZero':n,'SIRTotalIncludingZero':h0[3],'allFNPrePostIdentity':True,'zeroSelectionReconstructed':True,'ordinaryContainer':rec(Path(case['ordinaryContainer'])),'observedContainer':result['artifact'],'wholeContainerAndPayloadEqual':True,'exports':exports,'observer':ov,'currentTypedBodyInventoryObtained':False})
 else:
  m=re.fullmatch(rb'\{:ok true, :output "([^"]+)", :offset ([0-9]+), :length ([0-9]+), :arity ([0-9]+)\}\n',out);assert m and m[1].decode()==case['outputPath'];report={'kind':'extract','offset':int(m[2]),'nativeBytes':int(m[3]),'arity':int(m[4])};payload,exports=container((O/'G1.kseed').read_bytes());assert payload==ck(Path(case['outputPath']),result['artifact']) and exports==[['main',0,0]] and report=={'kind':'extract','offset':0,'nativeBytes':len(payload),'arity':0}
 assert report==row['structuredReportObservation']==result['report']
 kv=re.findall(rb':([a-z-]+) ([0-9]+)',raw['stderr']);counter={k.decode():int(v)for k,v in kv};assert len(kv)==17 and list(counter)==keys and b'KEXE_ARENA_USE {'+b' '.join(b':'+k+b' '+v for k,v in kv)+b'}\n'==raw['stderr'] and row['counterObservation']['status']=='valid' and counter==row['counterObservation']['values']
 jl=[json.loads(x)for x in raw['limitJournal'].splitlines()];assert len(jl)==6 and len(raw['limitJournal'])<=65536;ew=jl[0];envkeys=sorted(pr['environment']);assert ew=={'stage':'environment-admission','suppliedKeyNames':envkeys,'runtimeExtraKeyNames':ew['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':envkeys,'nativeExecEnvironmentExact':True} and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,desired)in enumerate([('RLIMIT_FSIZE',[67108864,67108864]),('RLIMIT_CPU',[1800,1801])]):
  bef,aft=jl[1+2*k:3+2*k];assert bef['index']==k+1 and bef['stage']=='before' and bef['limit']==name and bef['desired']==desired and all(b==9223372036854775807 or b>=d for b,d in zip(bef['before'],desired));assert aft=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':desired}
 assert jl[5]=={'stage':'exec-ready','argv':case['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801}
 samples=[json.loads(x)for x in raw['memoryJournal'].splitlines()];assert len(samples)==row['memorySamples'] and row['memoryJournalBytes']==len(raw['memoryJournal'])<=16777216;totals=[];prev=0;birth=None;births={}
 for ordinal,tm,pgid,members in samples:
  assert ordinal==len(totals)+1 and tm>prev and pgid==row['pid'] and 1<=len(members)<=2 and len(set(x[0]for x in members))==len(members)
  leader=[x for x in members if x[0]==pgid];assert len(leader)==1
  if birth is None:birth=leader[0][1]
  assert birth==leader[0][1]>0
  for pid,bt,foot in members:
   assert type(pid)is int and pid>0 and bt>0 and 0<=foot<2**64
   if pid in births:assert births[pid]==bt
   births[pid]=bt
  total=sum(x[2]for x in members);assert total<=4294967296;totals.append(total);prev=tm
 obs=row['controllerObservation'];mr=obs['memoryAdmissionRecord'];assert len(samples)>0 and mr['acceptedSamples']==obs['sampleCount']==len(samples) and obs['sampleReceiptPersistenceQualified'] and mr['acceptedLeaderBirthBound'] and mr['failure']is None and mr['otherRefusals']==[]
 assert all(mr[x]is True for x in ['completePipeEOF','stoppedClosedCapture','withinOriginalDeadline','groupAuthorityRetired','loaderWaitProtocolPinned']) and not mr['waitUncertain'] and not mr['rawTruncated'] and mr['captureErrors']==[] and mr['exactDirectChildWait']=='closed0' and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0
 assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY' and obs['semanticQualification'] and obs['strictOldMemoryPolicyPassed'] and result['strictOldMemoryPolicyPassed'] and result['memoryObservation']==obs['memoryObservation'];assert obs['memoryObservation']=={'status':'sampled-observations-only','strictOldSamplingRefusal':False,'sampleCompleteness':'finite-samples-only','hardPeakQualified':False}
 assert obs['controllerEvents']==['group-operation']*len(samples)+['retire:before-watchdog-stop-and-wait','wait-enter','retire:final-cleanup'];samplesTotal+=len(samples)
 summ.append({'index':i+1,'label':label,'directParentWait':0,'acceptedSamples':len(samples),'sampleFootprintSums':totals,'fullRawAndEOF':True,'resourceJournalSixRows':True,'arenaCounters17':counter,'artifact':result['artifact'],'admission':rec(O/(label+'.admission.json')),'raw':{k:row[k]for k in ['stdout','stderr','limitJournal','memoryJournal']}})
assert samplesTotal==75 and [x['acceptedSamples']for x in summ]==[60,4,8,3]
assert load(O/'terminal.json')=={'calls':4,'closed':True,'failure':False} and not (O/'failure.json').exists()
for n,v in completion['evidence'].items():assert v['path']==str(O/n);ck(Path(v['path']),v)
assert completion['status']=='COMPLETE_READONLY_X16_OBSERVER4_INITIAL_BOUNDED_APPLICABILITY_ONLY' and completion['calls']==4 and completion['sourcePinsSHA256']==g['sourcePinsSHA256'] and all(completion[x]is False for x in ['globalApplicabilityClaim','optimizerImplemented','guestExecuted','speedQualified','C2'])
report={'status':'PASS_INDEPENDENT_SAVED_READONLY_X16_OBSERVER4_INITIAL_BOUNDED_REJECTION_ONLY','independent':True,'priorSubjectImplementationAuthorship':False,'priorSourceReviewer':True,'subject':str(D),'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'registries':regs,'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'integrationFixtureProof':f,'currentProducerProof':p,'completion':rec(O/'report.json'),'terminal':rec(O/'terminal.json'),'calls':summ,'closedCalls':4,'acceptedFiniteSampleRows':75,'strictSampledPolicyAcceptedCalls':4,'observerResults':observations,'actualRawMutationRefusals':negativeControls,'boundedInitialRuleRejectedBothWorkloads':True,'sharedFrameTailRuleRejected':False,'globalRuleRejected':False,'qualification':'Saved source-bound readonly compiler artifacts equal entire ordinary containers; zero structural selection and zero eligible x16 reload pair for this initial finite partition rule.','validLast':'Saved terminal closed4/no failure, report binds terminal/attempts/results/generated pins and GO; frozen source orders terminal then final guard then report. No external persistence chronology trace.','limitations':['No RS/RI/RC emitted because Q selected zero; no current typed body/register-layout inventory for shared-frame region obtained.','This rejects only the initial bounded adjacent published-fuel reload hypothesis; no global fuel optimization/tail/SCC impossibility claim.','Observer strings/vectors/IO change compiler allocations; no compiler arena equivalence.','75 sampled soft footprint sums and closed direct-parent wait receipts are not hard peak, atomic census, complete child syscall trace or universal process ownership proof.','No workload guest, speed, full19 C-or-better, optimizer implementation or CID cache performance qualification.','Outer tool66454 CLOSED0 is parent-provided attribution; no saved raw outer tool receipt inspected.'],'reviewerOperations':{'savedFilesAndPureArithmeticOnly':True,'nativeOrAPIOrThreadsPipesNetwork':0,'reruns':0,'frozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
