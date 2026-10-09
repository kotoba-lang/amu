from pathlib import Path
import json,hashlib,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-full256-prefix1081-source-v1-20261009';O=D/'run-outputs';R=Path(__file__).resolve().parent;G=W/'crc-table-full256-prefix1081-go-root-20261009/root-go.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def check(p,v,limit=None):
 s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and(limit is None or s.st_size<=limit);b=p.read_bytes();assert len(b)==v['bytes']and sha(b)==v['sha256'],str(p)
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text());g=json.loads(G.read_text());a=json.loads((O/'attempts.json').read_text());t=json.loads((O/'terminal.json').read_text());f=json.loads((O/'failure.json').read_text())
for n,v in sp.items():check(D/n,v)
for n,v in ip.items():check(Path(n),v)
for n,v in g['sha256'].items():assert sha((D/n).read_bytes())==v
for v in g['sourceReviews']+[g['integrationFixtureProof']]:check(Path(v['path']),v)
for v in g['sourceReviews']:
 q=json.loads(Path(v['path']).read_text());assert q['status']=='PASS_SOURCE_ONLY_TC_FULL256_PREFIX1081_PAIRED2'and q['sourcePinsSHA256']==g['sha256']['source-pins.json']and q['driverSHA256']==g['sha256']['run.py']
assert g['maximumLoaderCalls']==2 and g['noRetry']is True and g['timingAuthorized']is False and g['outputRoot']==str(O)
assert len(a)==2 and t=={'attemptedCalls':2,'allChildrenClosed':True,'failure':True,'noRetry':True}and not(O/'completion.json').exists()
assert f=={'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':"AssertionError('first failure preserved; no retry')",'attemptedCalls':2}
assert json.loads((O/'effective-environment.json').read_text())==pr['environment']
# Whole saved structured stdout decoder independently asserts all fixed report syntax/caps.
rp=re.compile(rb'\{:status :ok :result (-?[0-9]{1,20}) :fuel \{:initial ([0-9]{1,20}) :remaining ([0-9]{1,20})\} :heap \{:capacity 16777216 :used ([0-9]{1,20})\} :string-pool \{:capacity 268435456 :used ([0-9]{1,20})\} :vectors \{:capacity 4194304 :used ([0-9]{1,20})\} :vector-items \{:capacity 134217728 :used ([0-9]{1,20})\}\}\n')
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];ap=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]{1,20})'for k in fields)+'}\n').encode())
summaries=[];raws=[];sampleCounts=[];peak=0
for i,(row,case)in enumerate(zip(a,pr['cases']),1):
 assert row['index']==i and row['label']==case['label']and row['nativeArgv']==case['nativeArgv']and row['environment']==pr['environment']
 assert row['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd']and row['argv'][3].isdigit()and row['argv'][4:]==['--',*case['nativeArgv']]
 assert row['state']=='terminal'and row['returncode']==0 and row['waitEntered']and not row['waitUncertain']and row['signalingAuthorityRetired']and row['captureStopAcknowledged']and row['watchdogErrors']==[]
 base=O/case['label'];obs=row['controllerObservation'];cap=obs['capture'];assert cap['completeRaw']and cap['stoppedWriter']and cap['errors']==[]and all(cap['EOF'].values())and not any(cap['dropped'].values())and obs['directChildWait']=='closed0'and not obs['waitUncertain']
 for n,limit in [('stdout',8388608),('stderr',1048576)]:
  p=base.with_suffix('.'+n);check(p,row[n],limit);assert cap['hashes'][n]==row[n]and cap['retained'][n]==p.stat().st_size;raws.append(pin(p))
 out=base.with_suffix('.stdout').read_bytes();err=base.with_suffix('.stderr').read_bytes();m=rp.fullmatch(out);am=ap.fullmatch(err);assert m and am;v=list(map(int,m.groups()));assert v[:3]==[4018572661,1000000,997836]and v[3:]==[0,0,0,0]
 arenas=dict(zip(fields,map(int,am.groups())));assert all(z==0 for z in arenas.values())and row['counterObservation']['values']==arenas
 rpt=row['structuredReportObservation'];assert rpt['result']==4018572661 and rpt['initialFuel']==1000000 and rpt['remainingFuel']==997836 and rpt['metered']is True
 for name,k,lim in [('limit-journal','limitJournal',65536),('memory-journal','memoryJournal',16777216)]:check(base.with_suffix('.'+name+'.jsonl'),row[k],lim)
 lj=[json.loads(x)for x in base.with_suffix('.limit-journal.jsonl').read_bytes().splitlines()];assert len(lj)==6;keys=sorted(pr['environment']);ew=lj[0];assert ew=={'changedExpectedKeyNames':[],'missingKeyNames':[],'nativeExecEnvironmentExact':True,'nativeExecKeyNames':keys,'runtimeExtraKeyNames':ew['runtimeExtraKeyNames'],'stage':'environment-admission','suppliedKeyNames':keys}and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):
  before,after=lj[2*k-1:2*k+1];assert before['index']==k and before['limit']==name and before['stage']=='before'and before['desired']==[soft,hard]and all(x==9223372036854775807 or x>=y for x,y in zip(before['before'],[soft,hard]));assert after=={'index':k,'limit':name,'outcome':'installed','readback':[soft,hard],'stage':'outcome'}
 assert lj[-1]=={'ASSetterRequested':False,'CPUGraceHardSeconds':1801,'argv':case['nativeArgv'],'stage':'exec-ready'}
 mb=base.with_suffix('.memory-journal.jsonl').read_bytes();ms=mb.splitlines();assert len(mb)==row['memoryJournalBytes']and len(ms)==row['memorySamples']==obs['sampleCount'];starts={};timestamps=[]
 for j,b in enumerate(ms,1):
  assert len(b)+1<=4096;seq,stamp,pid,members=json.loads(b);assert seq==j and pid==row['pid']and 1<=len(members)<=2 and len({m[0]for m in members})==len(members)and pid in [m[0]for m in members];timestamps.append(stamp);total=0
  for p,birth,fp in members:
   assert p>0 and birth>0 and 0<=fp<2**64 and(p not in starts or starts[p]==birth);starts[p]=birth;total+=fp
  assert len(starts)<=2 and total<=4294967296;peak=max(peak,total)
 assert timestamps==sorted(timestamps)and len(set(timestamps))==len(timestamps);sampleCounts.append(len(ms));ev=obs['controllerEvents']
 if i==1:assert row['failure']is None and obs['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY'and obs['strictOldMemoryPolicyPassed']is True and cap['firstFailure']is None and ev==['group-operation']*3+['retire:before-watchdog-stop-and-wait','wait-enter','retire:final-cleanup']
 else:assert row['failure']=="AssertionError('complete semantic/sample-or-gap admission')"and obs['status']=='REFUSE'and obs['semanticQualification']is False and obs['strictOldMemoryPolicyPassed']is False and cap['firstFailure']=='sampling-uncertainty'and ev==['group-operation']*3+['retire:group-exception-atomic','retire:sampling-uncertainty','retire:before-watchdog-stop-and-wait','wait-enter','retire:final-cleanup'];assert 'failure'not in obs and 'otherRefusals'not in obs
 summaries.append({'label':case['label'],'directWaitRC':0,'CRC':4018572661,'fuelConsumed':2164,'remainingFuel':997836,'all17ArenaZero':True,'completeStdoutBytes':len(out),'completeStderrBytes':len(err),'stdoutSHA256':sha(out),'stderrSHA256':sha(err),'savedSamples':len(ms),'controllerStatus':obs['status'],'memoryObservation':obs['memoryObservation']})
assert sampleCounts==[3,2]and sum(sampleCounts)==5
for k in ['CRC','fuelConsumed','remainingFuel','stdoutSHA256','stderrSHA256']:assert summaries[0][k]==summaries[1][k]
old=W/'crc-table-decision-collapse-original-crc-guest8-source-v1-20261009-dense/run-outputs';assert json.loads((old/'terminal.json').read_text())['failure']is True and not(old/'completion.json').exists()
r={'status':'PASS_INDEPENDENT_SAVED_FAILURE_TC_PREFIX1081_PAIRED2_ONLY','independent':True,'priorAuthorship':False,'sourcePinsSHA256':sha((D/'source-pins.json').read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'inputPinsSHA256':sha((D/'input-pins.json').read_bytes()),'rootGO':pin(G),'sourceReviews':g['sourceReviews'],'fixtureProof':g['integrationFixtureProof'],'attempts':pin(O/'attempts.json'),'terminal':pin(O/'terminal.json'),'failure':pin(O/'failure.json'),'verified':{'sourceFiles':18,'inputFiles':2141,'allPinsExactRegular':True,'savedCalls':2,'directWaits0':2,'savedMemorySamples':5,'samplesPerCall':[3,2],'sampledMaximumAggregateBytes':peak,'eachSixResourceRowsExact':True,'rawExpectedCRCFuelArenaMatchBoth':True,'offlinePairRawByteIdentity':True,'completionAbsent':True,'campaignRemainsFAIL':True,'reruns':0},'savedCalls':summaries,'raw':raws,'failureProvenance':{'observed':'ON third group-operation raised; two accepted samples then atomic group retirement and sampling-uncertainty refusal; normal direct wait0 and complete raw retained.','exactKernelStageErrnoPID':'UNAVAILABLE_NOT_PERSISTED','underlyingCause':'UNAVAILABLE_NOT_PERSISTED','reason':'Controller local failure/context and otherRefusals are not returned in final observation; journal contains accepted samples only. Atomic group-exception could originate in sampler API or strict sampler policy. No evidence proves termination race or eligible ESRCH.'},'qualificationBoundary':['Complete OFF/ON saved structured results CRC4018572661/fuel2164/all17zero and identical raw are verified semantic observations. They do not convert ON memory refusal or failed campaign into qualified paired2 completion.','Source predicts1081 coveringall256 indices and prior audited emission selects site220; no dynamic per-index guest trace and no full256 campaign PASS.','OFF finite sampled policy accepted; ON refused, missing observation notzero. Five finite samples do not establish hardpeak/atomic census/all-descendant closure.','Old G1 strict failure and prior actual8 proof remain unchanged; no retry/native calls by reviewer. No full19/performance/ComputeCID/ResultCID cache benefit claim.','Saved controller retirement/closure chronology is source-bound metadata, not independent OS syscall trace. Outer session73564 CLOSED1 is parent-observed attribution only.'],'operationalCallsByReviewer':0,'rerunsByReviewer':0,'actualThreadFDProcessNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(R/'report.json')))
