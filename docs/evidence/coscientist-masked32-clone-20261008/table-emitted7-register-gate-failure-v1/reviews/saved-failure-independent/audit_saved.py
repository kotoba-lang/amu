from pathlib import Path
import json,hashlib,re,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-decision-collapse-tc-emitted-build8-source-v1-20261008';O=D/'run-outputs';R=W/'crc-table-decision-collapse-tc-emitted-build8-saved-failure-review-independent-20261008';G=W/'crc-table-decision-collapse-tc-emitted-build8-go-root-20261008/root-go.json'
H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def receipt(p):b=Path(p).read_bytes();return {'bytes':len(b),'sha256':H(b)}
def check(p,v):assert receipt(p)=={k:v[k]for k in ['bytes','sha256']},str(p)
counts=[]
for n,rel in [('source-pins.json',True),('input-pins.json',False)]:
 reg=load(D/n);total=0
 for p,v in reg.items():check(D/p if rel else p,v);total+=v['bytes']
 counts.append([len(reg),total])
pr=load(D/'preregistration.json');g=load(G)
for n,h in g['sha256'].items():assert H((D/n).read_bytes())==h
assert g['status']=='ROOT_GO_TC_CURRENT_EMITTED_BUILD8_ONLY'and len(g['sourceReviews'])==2
for v in g['sourceReviews']:check(v['path'],v);assert load(v['path'])['status']=='PASS_SOURCE_ONLY_TC_CURRENT_EMITTED_BUILD8'
for p,v in load(O/'generated-pins.json').items():check(p,v)
for n in ['unity-candidate.kotoba','unity-emitter-observer.kotoba','original-input.kotoba']:assert (O/n).read_bytes()==(D/n).read_bytes()
a=load(O/'attempts.json');t=load(O/'terminal.json');f=load(O/'failure.json')
assert len(a)==7 and t=={'attemptedCalls':7,'allChildrenClosed':True,'failure':True,'noRetry':True};assert f['attemptedCalls']==7 and 'local7(x25)'in f['exception'];assert not (O/'completion.json').exists()and not (O/'observed-on-input-extract.stdout').exists()
labels=['candidate-compile','candidate-extract','emitter-observer-compile','emitter-observer-extract','on-input-compile','on-input-extract','observed-on-input-compile'];sums=[]
for idx,row in enumerate(a,1):
 assert row['index']==idx and row['label']==labels[idx-1]and row['state']=='terminal'and row['spawned']and row['reaped']and row['returncode']==0 and row['waitEntered']and not row['waitUncertain']and row['signalingAuthorityRetired']and row['cleanup']==[]and row['reason']is None and row['exception']is None
 assert row['environment']==pr['environment'];assert row['argv'][0]==pr['interpreter']['path']and row['argv'][1]==str(D/'launch-wrapper.py')and row['argv'][5:]==row['nativeArgv']
 for field,suffix,cap in [('stdout','stdout',8388608),('stderr','stderr',1048576),('limitJournal','limit-journal.jsonl',65536),('memoryJournal','memory-journal.jsonl',16777216)]:
  p=O/(row['label']+'.'+suffix);check(p,row[field]);assert p.stat().st_size<=cap
 jr=[json.loads(x)for x in (O/(row['label']+'.limit-journal.jsonl')).read_bytes().splitlines()];assert len(jr)==6
 ew=jr[0];keys=sorted(pr['environment']);assert ew['suppliedKeyNames']==keys and ew['nativeExecKeyNames']==keys and ew['missingKeyNames']==ew['changedExpectedKeyNames']==[]and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']]and ew['nativeExecEnvironmentExact']is True
 for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)]):
  before,after=jr[1+2*k:3+2*k];assert before['desired']==[soft,hard]and before['limit']==name and before['stage']=='before';assert after=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]};assert all(x==9223372036854775807 or x>=y for x,y in zip(before['before'],[soft,hard]))
 assert jr[5]=={'stage':'exec-ready','argv':row['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801}
 mem=[json.loads(x)for x in (O/(row['label']+'.memory-journal.jsonl')).read_bytes().splitlines()];assert len(mem)==row['memorySamples']>0 and len(mem)<=90502
 seen={};agg=[];last=0
 for seq,m in enumerate(mem,1):
  assert m[0]==seq and m[1]>last and m[2]==row['pid']and 1<=len(m[3])<=2;last=m[1];ids=[]
  for pid,birth,foot in m[3]:
   assert 0<birth and 0<=foot<=2**64-1 and seen.get(pid,birth)==birth;seen[pid]=birth;ids.append(pid)
  assert len(set(ids))==len(ids)and row['pid']in ids;agg.append(sum(x[2]for x in m[3]));assert agg[-1]<=4294967296
 assert len(seen)<=2 and max(agg)==row['peakObservedAggregateFootprintBytes']
 stderr=(O/(row['label']+'.stderr')).read_bytes();assert stderr.endswith(b'\n')and stderr.startswith(b'KEXE_ARENA_USE {')and stderr.count(b'\n')==1
 vals={k.decode():int(v)for k,v in re.findall(rb':([a-z-]+) ([0-9]+)',stderr)};assert vals==row['counterObservation']['values']and len(vals)==17;assert vals['heap-bytes']==16*vals['pairs']+vals['string-pool-bytes']+16*vals['vectors']+8*vals['vector-items'];assert row['counterObservation']['status']=='valid'
 assert b':ok true'in (O/(row['label']+'.stdout')).read_bytes()and b':ok false'not in (O/(row['label']+'.stdout')).read_bytes()
 sums.append({'call':idx,'label':row['label'],'returncode':0,'memorySamples':len(mem),'maximumObservedMembers':max(len(m[3])for m in mem),'observedLifetimeMembers':len(seen),'peakObservedFootprintBytes':max(agg)})
def kseed(p):
 b=Path(p).read_bytes();end=b.index(b'\n\n');lines=b[:end].splitlines();hh=lines[0].split();assert hh[0]==b'KSEED1';payload=b[end+2:];exports=[(x.split()[0].decode(),int(x.split()[1]),int(x.split()[2]))for x in lines[1:]];assert len(payload)==int(hh[1])and len(exports)==int(hh[2]);return payload,exports
art=[]
for n in ['candidate','emitter-observer','on-input']:
 payload,exports=kseed(O/(n+'.kseed'));assert payload==(O/(n+'.bin')).read_bytes();art.append({'role':n,'container':receipt(O/(n+'.kseed')),'native':receipt(O/(n+'.bin')),'exports':exports})
assert (O/'on-input.kseed').read_bytes()==(O/'observed-on-input.kseed').read_bytes()
payload,exports=kseed(O/'observed-on-input.kseed');raw=(O/'observed-on-input-compile.stdout').read_bytes();ns={'__name__':'offline_saved_only','__file__':str(D/'validate.py')};exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
v=ns['verify_binding'](raw,payload,exports,(D/'original-input.kotoba').read_bytes());base=load(pr['currentTypedBinding']['path']);emit=[list(map(int,l.split()[1:]))for l in raw.splitlines()if l.startswith(b'TCEMIT ')];assert len(emit)==1;cs,ce=emit[0][5:7];words=dict(v['allRawRecords']['FCODE']);span=[words[k]for k in range(cs,ce)];assert span[0]==0xaa1803e0 and span[-1]==0xaa0003e9
try:ns['verify'](raw,payload,exports,(D/'original-input.kotoba').read_bytes(),base)
except AssertionError as ex:assert str(ex)=='exact original local7(x25) input capture and temp0(x9) result publication'
else:raise AssertionError('frozen gate should refuse')
actual={(r[1],r[2]):r[3]for r in v['allRawRecords']['TCG']if r[0]==220};old={(r[1],r[2]):r[3]for r in base['allRawRecords']['TCG']if r[0]==220};diff=[{'phase':p,'field':k,'OFF':old[p,k],'TC':x}for (p,k),x in actual.items()if x!=old[p,k]]
assert actual[0,24]==3 and actual[0,31]==7 and actual[0,23]==25;reg=actual[0,23]-1;assert reg==24 and (span[0]>>16)&31==reg and span[0]&31==0
# Diagnostic only, no frozen edits: changing guessed input word passes remaining gate.
s=(D/'validate.py').read_text().replace('span[0]==0xaa1903e0','span[0]==0xaa1803e0');n2={'__name__':'offline_counterfactual','__file__':str(D/'validate.py')};exec(compile(s,'<offline-input-word-only-counterfactual>','exec'),n2)
counterfactual=n2['verify'](raw,payload,exports,(D/'original-input.kotoba').read_bytes(),base)
assert diff==[] and counterfactual['TCEmitterExecuted'] is True
nextFailure=None
result={'status':'PASS_INDEPENDENT_SAVED_FAILURE_TC_CURRENT_EMITTED_CALLS7_ONLY','independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':H((D/'source-pins.json').read_bytes()),'driverSHA256':H((D/'run.py').read_bytes()),'inputPinsSHA256':H((D/'input-pins.json').read_bytes()),'rootGOSHA256':H(G.read_bytes()),'fullFreshClosure':counts,'attemptsSHA256':H((O/'attempts.json').read_bytes()),'terminalSHA256':H((O/'terminal.json').read_bytes()),'failureSHA256':H((O/'failure.json').read_bytes()),'savedCalls':sums,'artifacts':art,'wholeObservedUnobservedKSEEDIdentity':receipt(O/'on-input.kseed'),'preservedTypedVerifierPassed':True,'TCEMIT':emit[0],'capturedSpanHex':[f'{x:08x}'for x in span],'registerDecode':{'input':'MOV X0,X24','result':'MOV X9,X0','sourceDescriptorKind':3,'sourceLocalSlot':7,'slotRegisterStoredPlusOne':25,'decodedInputRegister':24},'descriptorDifferencesFromOFF':diff,'secondGateFailureAfterInputWordOnlyCounterfactual':nextFailure,'inputWordOnlyCounterfactualAllRemainingChecksPassed':True,'frozenGateAccepted':False,'completionAbsent':True,'call8NotAttempted':True,'retryObserved':False,'operationalCallsByReviewer':0,'limitations':['Accepted saved failure only, not successful build8 certificate or guest behavior. Seven parent/wrapper leaders reaped0; native descendant closure relies on loader protocol, not independent per-descendant wait receipts.','No hardpeak or atomic/transient group memory claim. Saved journal hash/cap/sums are verified; EOF follows accepted reviewed driver path, not independent syscall tracing.','Outer CLOSED1 is root tool observation; durable terminal proves seven saved calls and failure.','Input register guess was missed in preceding SOURCE review; synthetic fixture matched that assumption and did not establish actual register mapping. My interim descriptor warning incorrectly compared pre with post; phase-paired OFF comparison has zero differences and full equality passes.','Counterfactual executes only pure validator source in memory; all remaining assertions pass. It does not revise frozen source, certify a replacement gate, or authorize another build.']}
(R/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'path':str(R/'report.json'),'bytes':(R/'report.json').stat().st_size,'sha256':H((R/'report.json').read_bytes()),'differences':diff,'span':result['capturedSpanHex']}))
