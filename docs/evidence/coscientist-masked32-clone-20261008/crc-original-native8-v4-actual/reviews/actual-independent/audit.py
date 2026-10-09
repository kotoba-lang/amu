from pathlib import Path
import json,hashlib,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-original-guest-native-controller-source-v4-20261009-dense';O=D/'run-outputs';R=Path(__file__).resolve().parent;G=W/'crc-original-guest-native-controller-v4-go-root-20261009/root-go.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def check(p,v,cap=None):
 st=p.lstat();assert stat.S_ISREG(st.st_mode)and not p.is_symlink()and (cap is None or st.st_size<=cap);b=p.read_bytes();assert len(b)==v['bytes']and sha(b)==v['sha256'],str(p)
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text());g=json.loads(G.read_text());c=json.loads((O/'completion.json').read_text());a=json.loads((O/'attempts.json').read_text());results=json.loads((O/'guest-results.json').read_text());t=json.loads((O/'terminal.json').read_text())
for n,v in sp.items():check(D/n,v)
for n,v in ip.items():check(Path(n),v)
for n,v in g['sha256'].items():assert sha((D/n).read_bytes())==v
for v in g['sourceReviews']+[g['integrationFixtureProof']]:check(Path(v['path']),v)
for v in g['sourceReviews']:
 q=json.loads(Path(v['path']).read_text());assert q['status']=='PASS_SOURCE_ONLY_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4'and q['sourcePinsSHA256']==g['sha256']['source-pins.json']and q['driverSHA256']==g['sha256']['run.py']
fq=json.loads(Path(g['integrationFixtureProof']['path']).read_text());assert fq['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert sp[n]['sha256']==fq[k]
assert c['sourcePinsSHA256']==g['sha256']['source-pins.json']and c['rootGOSHA256']==sha(G.read_bytes())
for k in ['terminal','attempts','generatedPins','actualEmissionProof','actualExtractionProof','actualExtractionCompletion','oldBuild8FailureProof','nativeControllerFixtureProof']:check(Path(c[k]['path']),c[k])
for p,v in json.loads((O/'generated-pins.json').read_text()).items():check(Path(p),v)
assert t=={'attemptedCalls':8,'allChildrenClosed':True,'failure':False,'noRetry':True}
assert len(a)==len(results)==len(pr['cases'])==8 and c['strictOldMemoryPolicyPassed']is True and c['pairedCases']==4 and c['status']=='COMPLETE_CURRENT_ORIGINAL_TC_GUEST8_CAPTURE_SEMANTIC_DIAGNOSTIC_ONLY'
# Independent whole-line decoding (only saved bytes, no operational imports).
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
arp=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]{1,20})'for k in fields)+'}\n').encode())
rp=re.compile(rb'\{:status :ok :result (-?[0-9]{1,20}) :fuel \{:initial ([0-9]{1,20}) :remaining ([0-9]{1,20})\} :heap \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :string-pool \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vectors \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vector-items \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\}\}\n')
summaries=[];sampleTotal=0;maximumAggregate=0;rawRefs=[];sampleCounts=[];memberCounts=[]
assert json.loads((O/'effective-environment.json').read_text())==pr['environment']and len(pr['environment'])==17
for i,(row,case,res)in enumerate(zip(a,pr['cases'],results),1):
 assert row['index']==i and row['label']==case['label']==res['label']and row['environment']==pr['environment']and row['nativeArgv']==case['nativeArgv']
 assert row['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd']and row['argv'][3].isdigit()and row['argv'][4:]==['--',*case['nativeArgv']]
 assert row['state']=='terminal'and row['returncode']==0 and row['waitEntered']is True and row['waitUncertain']is False and row['failure']is None and row['signalingAuthorityRetired']is True and row['captureStopAcknowledged']is True and row['watchdogErrors']==[]
 base=O/case['label'];paths={n:base.with_suffix('.'+n)for n in ['stdout','stderr']}
 for n in paths:check(paths[n],row[n],8388608 if n=='stdout'else 1048576);rawRefs.append(pin(paths[n]))
 ob=paths['stdout'].read_bytes();eb=paths['stderr'].read_bytes();m=rp.fullmatch(ob);am=arp.fullmatch(eb);assert m and am
 vals=list(map(int,m.groups()));answer,initial,remaining=vals[:3];assert answer==case['expectedResult']and initial==1000000 and 0<=remaining<=initial
 caps=vals[3::2];used=vals[4::2];assert caps==[16777216,268435456,4194304,134217728]and all(0<=u<=v for u,v in zip(used,caps))
 arenas=dict(zip(fields,map(int,am.groups())));assert all(0<=v<2**64 for v in arenas.values())and arenas['heap-bytes']==16*arenas['pairs']+arenas['string-pool-bytes']+16*arenas['vectors']+8*arenas['vector-items']
 assert all(arenas[k]==u for k,u in zip(fields[:4],used))
 obs=row['structuredReportObservation'];assert obs['result']==answer and obs['initialFuel']==initial and obs['remainingFuel']==remaining and obs['metered']is True and obs['arenaUsed']==dict(zip(fields[:4],used))and row['counterObservation']['values']==arenas
 assert res['case']==case and res['report']==obs and res['arena']==arenas and res['rawStdoutSHA256']==sha(ob)and res['rawStderrSHA256']==sha(eb)
 co=row['controllerObservation'];cap=co['capture'];assert co['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY'and co['strictOldMemoryPolicyPassed']is True and co['semanticQualification']is True and co['sampleReceiptPersistenceQualified']is True and co['directChildWait']=='closed0'and not co['waitUncertain']
 assert cap['stoppedWriter']is True and cap['completeRaw']is True and cap['firstFailure']is None and cap['errors']==[]and all(cap['EOF'].values())and not any(cap['dropped'].values())and cap['ownershipDecision']=='worker-granted'
 for n in paths:assert cap['hashes'][n]==row[n]and cap['retained'][n]==len(paths[n].read_bytes())
 for name,k,lim in [('limit-journal','limitJournal',65536),('memory-journal','memoryJournal',16777216)]:check(base.with_suffix('.'+name+'.jsonl'),row[k],lim)
 lj=[json.loads(v)for v in base.with_suffix('.limit-journal.jsonl').read_bytes().splitlines()];assert len(lj)==6
 ew=lj[0];keys=sorted(pr['environment']);assert ew=={'changedExpectedKeyNames':[],'missingKeyNames':[],'nativeExecEnvironmentExact':True,'nativeExecKeyNames':keys,'runtimeExtraKeyNames':ew['runtimeExtraKeyNames'],'stage':'environment-admission','suppliedKeyNames':keys}and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):
  before,after=lj[2*k-1:2*k+1];assert before['index']==k and before['limit']==name and before['stage']=='before'and before['desired']==[soft,hard]and all(x==9223372036854775807 or x>=y for x,y in zip(before['before'],[soft,hard]));assert after=={'index':k,'limit':name,'outcome':'installed','readback':[soft,hard],'stage':'outcome'}
 assert lj[5]=={'ASSetterRequested':False,'CPUGraceHardSeconds':1801,'argv':case['nativeArgv'],'stage':'exec-ready'}
 mb=base.with_suffix('.memory-journal.jsonl').read_bytes();lines=mb.splitlines();assert len(mb)==row['memoryJournalBytes']and len(lines)==row['memorySamples']==co['sampleCount']and 0<len(lines)<=90502 and all(len(v)+1<=4096 for v in lines)
 starts={};times=[]
 for j,line in enumerate(lines,1):
  seq,stamp,pid,ms=json.loads(line);assert seq==j and pid==row['pid']and type(stamp)is int and stamp>0 and 1<=len(ms)<=2 and len({v[0]for v in ms})==len(ms)
  assert pid in [v[0]for v in ms];times.append(stamp);memberCounts.append(len(ms));total=0
  for p,birth,fp in ms:
   assert type(p)is int and p>0 and type(birth)is int and birth>0 and type(fp)is int and 0<=fp<2**64
   assert p not in starts or starts[p]==birth;starts[p]=birth;total+=fp
  assert len(starts)<=2 and total<=4294967296;maximumAggregate=max(maximumAggregate,total)
 assert times==sorted(times)and len(set(times))==len(times)
 ev=co['controllerEvents'];assert ev==['group-operation']*len(lines)+['retire:before-watchdog-stop-and-wait','wait-enter','retire:final-cleanup']
 assert co['memoryObservation']==c['memoryObservations'][i-1]==res['memoryObservation']and co['memoryObservation']['status']=='sampled-observations-only'
 sampleTotal+=len(lines);sampleCounts.append(len(lines));summaries.append({'label':case['label'],'returncode':0,'result':answer,'initialFuel':initial,'remainingFuel':remaining,'usedFuel':initial-remaining,'arena17':arenas,'sampleCount':len(lines),'stdoutSHA256':sha(ob),'stderrSHA256':sha(eb)})
assert sampleTotal==19 and sampleCounts==[3,2,2,2,2,3,3,2]
for j in range(0,8,2):
 x,y=summaries[j:j+2]
 for k in ['result','initialFuel','remainingFuel','usedFuel','arena17','stdoutSHA256','stderrSHA256','returncode']:assert x[k]==y[k]
old=W/'crc-table-decision-collapse-original-crc-guest8-source-v1-20261009-dense/run-outputs';oldAudit=W/'crc-table-decision-collapse-original-crc-guest8-saved-failure-review-independent-20261009/report.json';oa=json.loads(oldAudit.read_text());assert oa['frozenCampaignStillFailed']is True and oa['completionAbsent']is True
for k in ['attempts','terminal','failure']:
 v=oa[k];check(Path(v['path']),v)
assert json.loads((old/'terminal.json').read_text())=={'attemptedCalls':2,'allChildrenClosed':True,'failure':True,'noRetry':True}and not(old/'completion.json').exists()
toolReceipt=G.parent/'tool-observation.json';tool=json.loads(toolReceipt.read_text());assert tool['exitCode']==0 and tool['attempts']==1 and tool['completionSHA256']==sha((O/'completion.json').read_bytes()) and tool['attributionOnly']is True and tool['independentKernelTrace']is False
r={'outerToolAttributionReceipt':pin(toolReceipt),'status':'PASS_INDEPENDENT_ACTUAL_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_ONLY','independent':True,'priorAuthorship':False,'sourcePinsSHA256':sha((D/'source-pins.json').read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'inputPinsSHA256':sha((D/'input-pins.json').read_bytes()),'rootGO':pin(G),'sourceReviews':g['sourceReviews'],'integrationFixtureProof':g['integrationFixtureProof'],'completion':pin(O/'completion.json'),'attempts':pin(O/'attempts.json'),'terminal':pin(O/'terminal.json'),'verified':{'sourceFiles':len(sp),'inputFiles':len(ip),'allPinsExactRegular':True,'nativeCalls':8,'normalDirectWaits0':8,'pairedCases':4,'memorySamples':19,'samplesPerCall':sampleCounts,'sampledMemberCounts':memberCounts,'maximumObservedAggregateBytes':maximumAggregate,'allSixResourceRowsPerCallExact':True,'allRawEOFCaptureStopNoDropError':True,'all17ArenaCountersAndPairedRawReportFuelExact':True,'terminationGapDiagnostics':0,'finiteSamplingPolicyPassedAll8':True},'results':summaries,'raw':rawRefs,'preservedOldG1FailureAudit':pin(oldAudit),'limits':['Saved actual scope is original CRC four OFF/ON pairs only; full256 compiled reach is false (source prefix1024 covers255), no extra1081 run.','Direct child wait0/EOF/source loader wait protocol are accepted; independent all-descendant OS tracing unavailable. Group operation chronology/authority retirement are frozen source-bound controller events, not syscall trace.','19 finite physical-footprint samples are soft4GiB observations, not hard memory peak/atomic census/AS cap. No ESRCH gap occurred here; prior strict G1 failure remains unchanged.','No timing/full19/trapstress/fixedpoint/fallback/FADDR/caps qualification. ComputeCID/ResultCID proposal was not implemented or measured here; this result is not CID/cache performance evidence.','Regular-file fsync/close and scheduling bounds remain cooperative. Root tool outer result is parent-observed, no separate outer raw receipt in this saved namespace.'],'reviewerDiagnostic':'Initial checker syntax-spacing failure before execution preserved; corrected only reviewer script, no subject mutations.', 'operationalCallsByReviewer':0,'rerunsByReviewer':0,'actualThreadFDProcessNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(R/'report.json')))
