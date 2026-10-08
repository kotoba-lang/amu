from pathlib import Path
import json,hashlib,re,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'shared-frame-currenttyped-observer3-source-v1-20261009';O=D/'run-outputs';R=Path(__file__).parent
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
assert regs['source-pins.json']['files']==23 and regs['input-pins.json']['files']==2841 and regs['input-pins.json']['logicalBytes']==449385544
G=W/'shared-frame-currenttyped-observer3-go-v1-root-20261009/root-go.json';g=load(G);assert g['status']==pr['rootGOStatus'] and g['maximumLoaderCalls']==3 and g['noRetry']is True and all(g[k]is False for k in ['C2','timingAuthorized','runtimeGuestAuthorized'])
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:assert rec(D/n)['sha256']==g[k]
assert len(g['sourceReviews'])==2
for v in g['sourceReviews']:
 q=json.loads(ck(Path(v['path']),v));assert q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
f=g['integrationFixtureProof'];assert f==pr['qualifiedIntegrationFixtureProof'];fq=json.loads(ck(Path(f['path']),f));assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert fq[k]==sp[n]['sha256']
p=pr['currentProducerProof'];pq=json.loads(ck(Path(p['path']),p));assert pq['G0G1G2G3WholeNativeEqual'] and pq['G0G1G2G3WholeContainerEqual']
for n,v in load(O/'generated-pins.json').items():ck(Path(n),v)
for n in ['observer-current16.kotoba','nsichneu.kotoba']:assert (O/n).read_bytes()==(D/n).read_bytes()
delta=load(D/'instrumentation-delta.json');bare=(D/'observer-current16.kotoba').read_text().replace((D/'observer-helpers.kotoba').read_text()+'\n','',1);assert bare.replace(delta['newLoop'],delta['oldLoop'],1).replace(delta['newDriver'],delta['oldDriver'],1).replace(delta['newLayout'],delta['oldLayout'],1)==(D/'ordinary-current16.kotoba').read_text()
a=load(Path(pr['sourceAssembly']));parts=[Path(a['candidate41']['path']if n=='seed/41-a64gen.kotoba'else v['path']).read_bytes()+b'\n'for n,v in zip(a['modules'],a['modulePins'])];assert len(parts)==16 and b''.join(parts)==(D/'ordinary-current16.kotoba').read_bytes()
# Frozen validator is pure saved data only. Independent raw reconstruction below supplements it.
vn={};exec(compile((D/'validate_observer.py').read_text(),str(D/'validate_observer.py'),'exec'),vn)
assert not (O/'report.json').exists() and load(O/'terminal.json')=={'calls':3,'closed':True,'failure':True} and load(O/'failure.json')=={'error':"AssertionError('first failure preserved; no retry')",'calls':3,'noRetry':True}
rows=load(O/'attempts.json');results=load(O/'results.json');assert len(rows)==3 and len(results)==2;summ=[];samplesTotal=0
from derive_expanded import derive
expanded,expProof=derive();(R/'expanded-source.kotoba').write_bytes(expanded);observed=None
keys=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
for i,(row,case)in enumerate(zip(rows,pr['cases'])):
 label=case['label'];assert row['index']==i+1 and row['label']==label and row['nativeArgv']==case['nativeArgv']and row['environment']==pr['environment']and len(row['environment'])==17
 assert row['state']=='terminal'and row['returncode']==0 and row['waitEntered']and not row['waitUncertain']and row['signalingAuthorityRetired']and row['captureStopAcknowledged']and row['watchdogErrors']==[] and row['failure']==(None if i<2 else 'AssertionError()')
 seal=load(O/(label+'.admission.json'));assert row['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd']and row['argv'][3].isdigit()and row['argv'][4:6]==['--admission-sha',rec(O/(label+'.admission.json'))['sha256']]and row['argv'][6:]==['--',*case['nativeArgv']]
 assert seal['index']==i+1 and seal['label']==label and seal['nativeArgv']==case['nativeArgv']and seal['outputPath']==case['outputPath']and seal['rootGO']==rec(G)and seal['sourcePinsSHA256']==g['sourcePinsSHA256']and seal['preregistrationSHA256']==g['preregistrationSHA256']
 for k in ['producer','producerContainer','input']:ck(Path(seal[k]['path']),seal[k])
 pp,pe=container(Path(seal['producerContainer']['path']).read_bytes());assert pe==[['main',0,0]]and pp==Path(seal['producer']['path']).read_bytes()
 raw={k:ck(O/(label+ext),row[k])for k,ext in [('stdout','.stdout'),('stderr','.stderr'),('memoryJournal','.memory-journal.jsonl'),('limitJournal','.limit-journal.jsonl')]}
 obs=row['controllerObservation'];cap=obs['capture'];mr=obs['memoryAdmissionRecord'];assert cap['stoppedWriter']and cap['completeRaw']and cap['EOF']=={'stdout':True,'stderr':True}and not any(cap['dropped'].values())and cap['errors']==[]and cap['hashes']=={k:row[k]for k in ['stdout','stderr']}and cap['retained']=={k:len(raw[k])for k in ['stdout','stderr']}
 assert len(raw['stdout'])<=8388608 and len(raw['stderr'])<=1048576
 out=raw['stdout'];lines=[]
 if i==2:lines,out=vn['split'](out)
 if case['kind']=='compile':
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output "([^"]+)", :bytes ([0-9]+)\}\n',out);assert m and m[1].decode()==case['outputPath'];b=Path(case['outputPath']).read_bytes();assert len(b)==int(m[2]);payload,exports=container(b);report={'kind':'compile','containerBytes':len(b)}
  if i==0:assert exports==[['main',0,0]]
  else:
   assert b==Path(case['ordinaryContainer']).read_bytes();rr=[(l.split()[0].decode(),list(map(int,l.split()[1:])))for l in lines];assert rr[0][0]=='SH'and rr[0][1][2]==267 and case['expectedFNCount']==265
   originalFailures=[]
   for title,src,fn in [('original-count',Path(case['nativeArgv'][8]).read_bytes(),265),('count-only-corrected',Path(case['nativeArgv'][8]).read_bytes(),267)]:
    try:vn['validate'](lines,payload,src,fn)
    except AssertionError as ex:originalFailures.append({'control':title,'error':str(ex)})
    else:raise AssertionError('frozen or unexpanded source accepted')
   assert originalFailures==[{'control':'original-count','error':'prior current FN count'},{'control':'count-only-corrected','error':'token source bounds'}]
   ov=vn['validate'](lines,payload,expanded,267);assert ov['selectedOwners']==list(range(132,144))and ov['selectedSIR']==150 and ov['selectedEdges']==24 and ov['genericBoundaryOwners']==[2,4,144]and not ov['safeRewriteQualified']and ov['wholeCODEProjection']and ov['allFIXProjection']
   st=[v[2:]for tag,v in rr if tag=='ST'];extra=[{'token':k,'span':[t[1],t[2]],'text':expanded[t[1]:t[2]].decode()}for k,t in enumerate(st)if t[2]>len(Path(case['nativeArgv'][8]).read_bytes())];assert len(extra)==24 and all(len(Path(case['nativeArgv'][8]).read_bytes())<e['span'][0]<=e['span'][1]<=len(expanded)for e in extra)
   # Independent raw CODE/native and 76(?) relocations are exact under full frozen validator; no missing field relaxed.
   sc=[v[2]for t,v in rr if t=='SC'and v[0]==2 and v[1]>0];import struct;assert b''.join(struct.pack('<I',w)for w in sc)==payload
   negatives=[]
   for name,mut in [('missing-footer',lines[:-1]),('unknown-refusal',lines+[b'SREFUSE 0\n']),('missing-state',[l for k,l in enumerate(lines)if k!=next(i for i,l in enumerate(lines)if l.startswith(b'SG '))]),('missing-FIX',[l for k,l in enumerate(lines)if k!=next(i for i,l in enumerate(lines)if l.startswith(b'SX 1 1 '))])]:
    try:vn['validate'](mut,payload,expanded,267)
    except (AssertionError,KeyError,IndexError):negatives.append(name)
    else:raise AssertionError('actual mutation admitted '+name)
   observed={'qualification':'CONDITIONAL_SAVED_RAW_CURRENT_TYPED_REGION_STRUCTURE_ONLY_ORIGINAL_GATE_FAIL','artifact':rec(Path(case['outputPath'])),'ordinaryArtifact':rec(Path(case['ordinaryContainer'])),'wholeContainerEqual':True,'wholeNativeCODEProjectionIndependent':True,'exports':exports,'originalRefusalsReproduced':originalFailures,'sourceExpansion':expProof,'extraTokens':extra,'expandedSource':rec(R/'expanded-source.kotoba'),'observer':ov,'actualMutationRefusals':negatives}
 else:
  m=re.fullmatch(rb'\{:ok true, :output "([^"]+)", :offset ([0-9]+), :length ([0-9]+), :arity ([0-9]+)\}\n',out);assert m and m[1].decode()==case['outputPath'];payload,exports=container((O/'G1.kseed').read_bytes());assert Path(case['outputPath']).read_bytes()==payload and exports==[['main',0,0]];report={'kind':'extract','offset':int(m[2]),'nativeBytes':int(m[3]),'arity':int(m[4])};assert report=={'kind':'extract','offset':0,'nativeBytes':len(payload),'arity':0}
 if i<2:assert results[i]['report']==report==row['structuredReportObservation'];ck(Path(case['outputPath']),results[i]['artifact']);assert results[i]['strictOldMemoryPolicyPassed']and results[i]['memoryObservation']==obs['memoryObservation']
 else:assert row.get('structuredReportObservation')is None and row.get('counterObservation')is None
 kv=re.findall(rb':([a-z-]+) ([0-9]+)',raw['stderr']);counter={k.decode():int(v)for k,v in kv};assert len(kv)==17 and list(counter)==keys and b'KEXE_ARENA_USE {'+b' '.join(b':'+k+b' '+v for k,v in kv)+b'}\n'==raw['stderr']
 jl=[json.loads(x)for x in raw['limitJournal'].splitlines()];assert len(jl)==6;ew=jl[0];ek=sorted(pr['environment']);assert ew=={'stage':'environment-admission','suppliedKeyNames':ek,'runtimeExtraKeyNames':ew['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':ek,'nativeExecEnvironmentExact':True}and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,want)in enumerate([('RLIMIT_FSIZE',[67108864,67108864]),('RLIMIT_CPU',[1800,1801])]):
  bef,aft=jl[1+2*k:3+2*k];assert bef['index']==k+1 and bef['stage']=='before'and bef['limit']==name and bef['desired']==want and all(z==9223372036854775807 or z>=w for z,w in zip(bef['before'],want));assert aft=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':want}
 assert jl[-1]=={'stage':'exec-ready','argv':case['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801}
 samples=[json.loads(x)for x in raw['memoryJournal'].splitlines()];assert len(samples)==row['memorySamples']and row['memoryJournalBytes']==len(raw['memoryJournal'])<=16777216;totals=[];prev=0;births={}
 for ordinal,tm,pgid,members in samples:
  assert ordinal==len(totals)+1 and tm>prev and pgid==row['pid']and 1<=len(members)<=2 and len({x[0]for x in members})==len(members)and len([x for x in members if x[0]==pgid])==1
  for pid,bt,foot in members:
   assert pid>0 and bt>0 and 0<=foot<2**64
   if pid in births:assert births[pid]==bt
   births[pid]=bt
  total=sum(x[2]for x in members);assert total<=4294967296;totals.append(total);prev=tm
 assert mr['acceptedSamples']==obs['sampleCount']==len(samples)and obs['sampleReceiptPersistenceQualified']and mr['acceptedLeaderBirthBound']and mr['completePipeEOF']and mr['stoppedClosedCapture']and not mr['rawTruncated']and not mr['captureErrors']and mr['exactDirectChildWait']=='closed0'and not mr['waitUncertain']and mr['withinOriginalDeadline']and mr['groupAuthorityRetired']and mr['groupOperationsAfterUncertainty']==mr['groupOperationsAfterWait']==0
 if i<2:assert obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY'and obs['semanticQualification']and obs['strictOldMemoryPolicyPassed']and mr['failure']is None and mr['otherRefusals']==[]and cap['firstFailure']is None
 else:
  assert obs['status']=='REFUSE'and not obs['semanticQualification']and not obs['strictOldMemoryPolicyPassed']and mr['otherRefusals']==['validation:AssertionError','resource-journal-unqualified']and cap['firstFailure']=='sampling-uncertainty'
  assert mr['failure']=={'contextVersion':'owned-group-sampling-failure-context-v1','typedOrigin':'fresh-owned-group-api-v1','stage':'leader-getpgid','pid':33610,'queryOrdinal':53,'errno':3,'failureClass':'kernel-oserror'}and mr['failure']['pid']in births
 ev=obs['controllerEvents'];assert ev.count('wait-enter')==1 and ev.index('retire:before-watchdog-stop-and-wait')<ev.index('wait-enter')and not any(z=='group-operation'for z in ev[ev.index('wait-enter')+1:]);samplesTotal+=len(samples)
 summ.append({'index':i+1,'label':label,'wait':0,'admitted':i<2,'acceptedSamples':len(samples),'sampleSums':totals,'raw':{k:row[k]for k in ['stdout','stderr','limitJournal','memoryJournal']},'artifact':rec(Path(case['outputPath'])),'arena17':counter,'installedResource6Verified':True,'memoryAdmissionRecord':mr,'capture':cap,'seal':rec(O/(label+'.admission.json'))})
assert samplesTotal==70 and [r['acceptedSamples']for r in summ]==[61,4,5]
r={'status':'PASS_INDEPENDENT_SAVED_FAILURE_SHARED_FRAME_OBSERVER3_WITH_CONDITIONAL_TYPED_RAW_ONLY','independent':True,'priorImplementationAuthorship':False,'priorSOURCEReviewer':True,'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'registries':regs,'rootGO':rec(G),'sourceReviews':g['sourceReviews'],'fixture':f,'currentProducerProof':p,'attempts':rec(O/'attempts.json'),'results':rec(O/'results.json'),'terminal':rec(O/'terminal.json'),'failure':rec(O/'failure.json'),'calls':summ,'closedCalls':3,'admittedCalls':2,'acceptedFiniteSamples':70,'campaignStatus':'FAIL','completionAbsent':True,'conditionalTypedRaw':observed,'reviewMissAcknowledgment':'Both SOURCE reviews, including this independent reviewer, accepted expectedFNCount265 and raw30386B source offsets without accounting for nullFN sentinel plus implicit rem library expansion. Actual267 and source30443 derive exactly from primaryscan; frozen gate is not repaired or promoted.','limits':['Original parser and controller REFUSE remain immutable; conditional savedraw structural decoding does not retroactively admit command3 or complete observer3.','resource-journal-unqualified in controller means validation short-circuited its downstream check; independent six raw rows show exact FSIZE/CPU setters installed, not setterfailure.','Bound leader-getpgid33610 query53 errno3 is actual API context; scheduling/termination kernelcause unknown.','12 current owners132..143/150SIR24edges and boundary2/4/144 are observed structure only; no shared-frame rewrite safety or dynamicguest reach/performance/CID effect.','70 finite physicalfootprint samples/parentwait0/source events are not hardpeak/atomiccensus/external syscalltrace.','Parent reports prelaunch permission-review timeout before CreateProcess, later approved once session23015 CLOSED1; this is supplied attribution, no durable outer rawreceipt inspected. No native replay inferred.'],'operations':{'nativeThreadFDPipeProcessGroupSetterNetworkCalls':0,'reruns':0,'frozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
