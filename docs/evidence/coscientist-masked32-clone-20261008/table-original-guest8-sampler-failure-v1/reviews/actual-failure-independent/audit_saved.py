from pathlib import Path
import json,hashlib,re
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-decision-collapse-original-crc-guest8-source-v1-20261009-dense';O=D/'run-outputs';R=W/'crc-table-decision-collapse-original-crc-guest8-saved-failure-review-independent-20261009';G=W/'crc-table-decision-collapse-original-crc-guest8-go-root-20261009/root-go.json';H=lambda b:hashlib.sha256(b).hexdigest();L=lambda p:json.loads(Path(p).read_bytes())
def rec(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def pin(p,v):r=rec(p);assert {k:r[k]for k in ['bytes','sha256']}=={k:v[k]for k in ['bytes','sha256']}
counts=[]
for n,rel in [('source-pins.json',True),('input-pins.json',False)]:
 reg=L(D/n);total=0
 for p,v in reg.items():pin(D/p if rel else p,v);total+=v['bytes']
 counts.append([len(reg),total])
assert counts==[[11,555989],[2032,393409826]];pr=L(D/'preregistration.json');g=L(G)
for n,h in g['sha256'].items():assert H((D/n).read_bytes())==h
assert g['status']=='ROOT_GO_CURRENT_ORIGINAL_TC_GUEST8_ONLY'and g['maximumLoaderCalls']==8 and g['generatedWorkloadExecutionAuthorized']is True and g['TCEmitterExecutionAuthorized']is False and g['timingAuthorized']is False and g['noRetry']is True
assert len(g['sourceReviews'])==2
for q in g['sourceReviews']:
 pin(q['path'],q);v=L(q['path']);assert v['status']=='PASS_SOURCE_ONLY_CURRENT_ORIGINAL_TC_GUEST8'and v['sourcePinsSHA256']==g['sha256']['source-pins.json']and v['driverSHA256']==g['sha256']['run.py']
a=L(O/'attempts.json');assert len(a)==2;assert L(O/'terminal.json')=={'attemptedCalls':2,'allChildrenClosed':True,'failure':True,'noRetry':True};assert L(O/'failure.json')=={'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':"AssertionError('first failure stop closed')",'attemptedCalls':2};assert not(O/'completion.json').exists()
for p,v in L(O/'generated-pins.json').items():pin(p,v)
ns={'__name__':'pure_saved_runtime_parser','__file__':str(D/'validate-runtime.py')};exec(compile((D/'validate-runtime.py').read_bytes(),str(D/'validate-runtime.py'),'exec'),ns)
rows=[]
for i,r in enumerate(a):
 c=pr['cases'][i];assert r['index']==i+1 and r['label']==c['label']and r['nativeArgv']==c['nativeArgv']and r['environment']==pr['environment']and r['argv'][0]==pr['interpreter']['path']and r['argv'][1]==str(D/'launch-wrapper.py')and r['argv'][5:]==c['nativeArgv'];assert r['state']=='terminal'and r['spawned']and r['reaped']and r['returncode']==0 and r['waitEntered']and not r['waitUncertain']and r['signalingAuthorityRetired']
 label=r['label']
 for field,suffix,cap in [('stdout','stdout',8388608),('stderr','stderr',1048576),('limitJournal','limit-journal.jsonl',65536),('memoryJournal','memory-journal.jsonl',16777216)]:pin(O/(label+'.'+suffix),r[field]);assert r[field]['bytes']<=cap
 jr=[json.loads(x)for x in(O/(label+'.limit-journal.jsonl')).read_bytes().splitlines()];assert len(jr)==6;e=jr[0];keys=sorted(pr['environment']);assert e=={'stage':'environment-admission','suppliedKeyNames':keys,'runtimeExtraKeyNames':e['runtimeExtraKeyNames'],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':keys,'nativeExecEnvironmentExact':True}and e['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]
 for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)]):
  before,after=jr[1+2*k:3+2*k];assert before['stage']=='before'and before['limit']==name and before['desired']==[soft,hard]and before['index']==k+1;assert all(x==9223372036854775807 or x>=y for x,y in zip(before['before'],[soft,hard]));assert after=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]}
 assert jr[-1]=={'stage':'exec-ready','argv':r['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801}
 mem=[json.loads(x)for x in(O/(label+'.memory-journal.jsonl')).read_bytes().splitlines()];assert len(mem)==r['memorySamples']==[2,1][i];seen={};tot=[];last=0
 for idx,m in enumerate(mem,1):
  assert m[0]==idx and m[1]>last and m[2]==r['pid']and 1<=len(m[3])<=2;last=m[1];ids=[]
  for pid,birth,foot in m[3]:assert birth>0 and 0<=foot<2**64 and seen.get(pid,birth)==birth;seen[pid]=birth;ids.append(pid)
  assert r['pid']in ids and len(set(ids))==len(ids);tot.append(sum(x[2]for x in m[3]));assert tot[-1]<=4294967296
 assert len(seen)<=2 and max(tot)==r['peakObservedAggregateFootprintBytes'];stderr=(O/(label+'.stderr')).read_bytes();vals={k.decode():int(v)for k,v in re.findall(rb':([a-z-]+) ([0-9]+)',stderr)};assert len(vals)==17 and vals==r['counterObservation']['values']and all(v==0 for v in vals.values());assert stderr==('KEXE_ARENA_USE {'+' '.join(':'+k+' 0'for k in vals)+'}\n').encode()
 raw=(O/(label+'.stdout')).read_bytes();observed=ns['observe_report'](raw);assert observed==r['structuredReportObservation']
 if i==0:assert r['reason']is None and r['exception']is None and r['cleanup']==[]and observed['decoded']['result']==3523407757 and observed['decoded']['remainingFuel']==999996 and observed['decoded']['initialFuel']==1000000 and observed['decoded']['metered']is True
 else:assert raw==b''and r['reason']=='exception'and r['exception']=="ProcessLookupError(3, 'No such process')"and r['cleanup']==["killgroup:PermissionError(1, 'Operation not permitted')"]and observed['status']=='unavailable-or-invalid'
 rows.append({'index':i+1,'arm':c['arm'],'returncode':0,'reason':r['reason'],'exception':r['exception'],'cleanup':r['cleanup'],'acceptedMemorySamples':len(mem),'memberCounts':[len(m[3])for m in mem],'aggregateFootprints':tot,'stdout':r['stdout'],'stderr':r['stderr'],'counterFields':17,'allCountersZero':True,'structuredObservation':observed,'waitUncertain':False,'authorityRetired':True})
res=L(O/'guest-results.json');assert len(res)==1 and res[0]['report']==rows[0]['structuredObservation']['decoded']and res[0]['rawStdoutSHA256']==a[0]['stdout']['sha256']and res[0]['rawStderrSHA256']==a[0]['stderr']['sha256']
for c in pr['cases'][2:]:assert not(O/(c['label']+'.stdout')).exists()
for field in ['offArtifact','onArtifact','offContainer','onContainer','actualEmissionProof','actualExtractionProof','actualExtractionCompletion','oldBuild8FailureProof']:pin(pr[field]['path'],pr[field])
q={'status':'PASS_INDEPENDENT_SAVED_FAILURE_CURRENT_ORIGINAL_TC_GUEST8_ONLY','independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':g['sha256']['source-pins.json'],'driverSHA256':g['sha256']['run.py'],'inputPinsSHA256':g['sha256']['input-pins.json'],'rootGOSHA256':H(G.read_bytes()),'sourceReviews':g['sourceReviews'],'freshClosure':counts,'attempts':rec(O/'attempts.json'),'terminal':rec(O/'terminal.json'),'failure':rec(O/'failure.json'),'savedCalls':rows,'successfulAcceptedResults':1,'completePairedResults':0,'remainingUnexecutedCalls':6,'completionAbsent':True,'frozenCampaignStillFailed':True,'samplerProvenance':'Stored ON exception is ProcessLookupError without traceback. In frozen adapter.sample path, os.getpgid can raise that exception in group(owned leader) or member(member pid), each potentially called more than once. Exact invocation/PID and syscall failure cause are not recorded. No proof that a census race caused it.','cleanupProvenance':'Frozen except/finally attempts killpg while retained signal authority before wait; saved cleanup records PermissionError, then leader wait returned0 and authority retired. No successful cleanup groupkill inferred.','captureLimit':'ON failure path closes pipes after cleanup without complete drain. stdout0 is retained empty capture, not proof guest produced no result. Captured allzero counter line and parent exit0 do not qualify ON semantic success, fuel or complete output.','operationalCallsByReviewer':0,'rerunsByReviewer':0,'limits':['Saved failure accepted, not paired guest semantics; ON result/fuel unknown, remaining6 unexecuted.','AllChildrenClosed refers to recorded two parent leaders; descendant closure relies loader wait protocol, not independent individual receipts.','Named setters/env/caps and accepted memory prefixes verified, not complete lifecycle census/hardpeak guarantee.','Root tool CLOSED1/exactonce is attributed to root observation, no independent syscall trace.','Old seven-call build failure preserved; separate extraction and repaired emission identities remain narrow proofs, no native repeats or performance/full19/cache/fixedpoint qualification.'],'blockers':[]}
p=R/'report.json';p.write_text(json.dumps(q,indent=2)+'\n');p.chmod(0o444);print(str(p),p.stat().st_size,H(p.read_bytes()))
