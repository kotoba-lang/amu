from pathlib import Path
import json,hashlib,stat,re,struct
D=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-native-component-v4-portable-env-20261008')
G=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-native-component-v4-portable-go-root-20261008/root-go.json')
W=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_bytes())
def ref(p):
 a=p.lstat();assert stat.S_ISREG(a.st_mode) and not p.is_symlink()
 b=p.read_bytes();z=p.lstat();assert(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sp=read(D/'source-pins.json');ip=read(D/'input-pins.json');pr=read(D/'preregistration.json');g=read(G);O=D/'run-outputs'
for n,q in sp.items():assert ref(D/n)==q
for n,q in ip.items():assert ref(Path(n))==q
for n,q in read(D/'freeze.json')['files'].items():assert ref(D/n)==q
assert set(g)=={'status','maximumLoaderCalls','outputRoot','outerExecution','noRetry','TCEmitterExecutionAuthorized','generatedWorkloadExecutionAuthorized','timingAuthorized','sha256','sourceReviews'}
assert g['status']=='ROOT_GO_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY_ONLY' and g['maximumLoaderCalls']==8 and g['noRetry'] is True and g['outputRoot']==str(O) and g['outerExecution']=='require_escalated'
assert g['TCEmitterExecutionAuthorized'] is False and g['generatedWorkloadExecutionAuthorized'] is False and g['timingAuthorized'] is False
assert set(g['sha256'])=={'run.py','preregistration.json','source-pins.json','input-pins.json'}
for n,h in g['sha256'].items():assert ref(D/n)['sha256']==h
assert len(g['sourceReviews'])==2 and len({q['path']for q in g['sourceReviews']})==2
for q in g['sourceReviews']:
 p=Path(q['path']);assert ref(p)=={k:q[k]for k in ('bytes','sha256')};r=read(p)
 assert r['status']=='PASS_SOURCE_ONLY_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY' and r['sourcePinsSHA256']==g['sha256']['source-pins.json'] and r['driverSHA256']==g['sha256']['run.py']
rows=read(O/'attempts.json');c=read(O/'completion.json');generated=read(O/'generated-pins.json')
assert len(rows)==8 and read(O/'terminal.json')=={'attemptedCalls':8,'allChildrenClosed':True,'failure':False,'noRetry':True}
assert read(O/'effective-environment.json')==pr['environment'] and len(pr['environment'])==17
expectedNames={'attempts.json','terminal.json','completion.json','effective-environment.json','generated-pins.json','images.json'}|{Path(p).name for p in generated}
for row in pr['orderedChildren']:
 expectedNames.update(row['label']+'.'+s for s in ('stdout','stderr','limit-journal.jsonl','memory-journal.jsonl'))
assert {p.name for p in O.iterdir()}==expectedNames
for p,q in generated.items():assert ref(Path(p))==q
for n in ('unity-baseline.kotoba','unity-observer.kotoba','original-input.kotoba'):assert(O/n).read_bytes()==(D/n).read_bytes()
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
counterPattern=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in fields)+'}\n').encode())
memCounts=[];memorySummaries=[];environmentExtras=[];lastClock=0
for idx,a in enumerate(rows,1):
 registered=pr['orderedChildren'][idx-1];label=a['label'];assert a['index']==idx and label==registered['label'] and a['nativeArgv']==registered['nativeArgv'] and a['environment']==pr['environment']
 assert a['argv'][:3]==[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd'] and int(a['argv'][3])>=3 and a['argv'][4:]==['--',*a['nativeArgv']]
 assert a['state']=='terminal' and a['spawned'] is True and a['reaped'] is True and a['returncode']==0 and a['reason'] is None and a['exception'] is None and a['cleanup']==[]
 assert a['waitEntered'] is True and a['waitUncertain'] is False and a['signalingAuthorityRetired'] is True and a['hardMemoryCapEstablished'] is False
 for key,suffix in [('stdout','stdout'),('stderr','stderr'),('limitJournal','limit-journal.jsonl'),('memoryJournal','memory-journal.jsonl')]:assert a[key]==ref(O/(label+'.'+suffix))
 assert a['stdout']['bytes']<=8388608 and a['stderr']['bytes']<=1048576 and 0<a['limitJournal']['bytes']<=65536 and 0<a['memoryJournal']['bytes']<=16777216
 limits=[json.loads(l)for l in(O/(label+'.limit-journal.jsonl')).read_bytes().splitlines()];assert len(limits)==6
 extra=limits[0]['runtimeExtraKeyNames'];environmentExtras.append(extra)
 assert limits[0]=={'stage':'environment-admission','suppliedKeyNames':sorted(pr['environment']),'runtimeExtraKeyNames':extra,'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':sorted(pr['environment']),'nativeExecEnvironmentExact':True} and extra in ([],['__CF_USER_TEXT_ENCODING'])
 for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)]):
  before,after=limits[1+2*k:3+2*k];assert before['index']==k+1 and before['limit']==name and before['stage']=='before' and before['desired']==[soft,hard]
  assert all(type(x) is int for x in before['before']);bs,bh=before['before'];assert(bs==9223372036854775807 or bs>=soft)and(bh==9223372036854775807 or bh>=hard)
  assert after=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]}
 assert limits[-1]=={'stage':'exec-ready','argv':a['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':1801}
 stderr=(O/(label+'.stderr')).read_bytes();m=counterPattern.fullmatch(stderr);assert m and all(len(v)<=20 for v in m.groups())
 vals=dict(zip(fields,map(int,m.groups())));assert all(0<=v<2**64 for v in vals.values())
 assert vals['heap-bytes']==16*vals['pairs']+vals['string-pool-bytes']+16*vals['vectors']+8*vals['vector-items']
 assert vals['pairs']<=16777216 and vals['string-pool-bytes']<=268435456 and vals['vectors']<=4194304 and vals['vector-items']<=134217728
 assert a['counterObservation']=={'status':'valid','values':vals,'entireStderrIsCounterLine':True}
 mem=[json.loads(l)for l in(O/(label+'.memory-journal.jsonl')).read_bytes().splitlines()];assert 0<len(mem)==a['memorySamples']<=90502
 births={};peak=0;counts=set()
 for sample,m in enumerate(mem,1):
  assert len(m)==4 and m[0]==sample and m[1]>lastClock and m[2]==a['pid'];lastClock=m[1]
  members=m[3];assert 1<=len(members)<=2 and members==sorted(members) and len({x[0]for x in members})==len(members) and a['pid'] in [x[0]for x in members]
  for pid,birth,foot in members:
   assert type(pid) is int and 0<pid<2**31 and type(birth) is int and birth>0 and type(foot) is int and 0<=foot<2**64
   assert pid not in births or births[pid]==birth;births[pid]=birth
  assert len(births)<=2;total=sum(x[2]for x in members);assert total<=4294967296;peak=max(peak,total);counts.add(len(members))
 assert peak==a['peakObservedAggregateFootprintBytes'];memCounts.append(len(mem));memorySummaries.append({'label':label,'samples':len(mem),'memberCountsObserved':sorted(counts),'distinctBirths':len(births),'peakAcceptedAggregateBytes':peak})
 assert b':ok true' in(O/(label+'.stdout')).read_bytes() and b':ok false'not in(O/(label+'.stdout')).read_bytes()
assert memCounts==[63,3,64,3,2,2,2,2]
def container(path):
 raw=path.read_bytes();head,rest=raw.split(b'\n',1);parts=head.split();assert parts[0]==b'KSEED1' and len(parts)==3
 exported,payload=rest.split(b'\n\n',1);exports=[(z[0].decode(),int(z[1]),int(z[2]))for z in (line.split()for line in exported.splitlines())]
 assert len(payload)==int(parts[1]) and len(exports)==int(parts[2]) and len(set(z[0]for z in exports))==len(exports)
 return payload,exports
for role in ('current-baseline','readonly-observer','ordinary-input','observed-input'):
 payload,exports=container(O/(role+'.kseed'));assert payload==(O/(role+'.bin')).read_bytes()
 if role in ('current-baseline','readonly-observer'):assert exports==[('main',0,0)]
 else:assert exports==[('bench',1224,1),('prefix-crc',1352,1),('prefix-seed',1380,1),('table-entry',1560,1)]
 offset=next(v[1]for v in exports if v[0]==('main' if role in ('current-baseline','readonly-observer')else 'bench'))
 assert re.findall(rb':offset ([0-9]+)\b',(O/(role+'-extract.stdout')).read_bytes())==[str(offset).encode()]
assert(O/'ordinary-input.kseed').read_bytes()==(O/'observed-input.kseed').read_bytes()
assert(O/'ordinary-input.bin').read_bytes()==(O/'observed-input.bin').read_bytes()
payload,exports=container(O/'observed-input.kseed');raw=(O/'observed-input-compile.stdout').read_bytes();saved=read(O/'typed-binding.json')
# Reviewed pure validator only: imports re/struct; no driver or operational module.
ns={'__file__':str(D/'validate.py'),'__name__':'offline_reviewed_validator'};exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
assert ns['verify'](raw,payload,exports,(O/'original-input.kotoba').read_bytes())==saved
# Independently decode all final branch relocations from saved raw witnesses.
r=saved['allRawRecords'];code=dict(r['FCODE']);labels=dict(r['FLABEL']);fcode={x[1]:x[3]for x in r['FF']if x[0]==1 and x[2]==13};branchCount=0
for index,at,kind,target,aux in r['FFIX']:
 if kind==5:continue
 word=code[at];to=fcode[target] if kind==4 else labels[target]
 if kind==4 and aux:assert code[to]==0xd2800005;to+=1
 if kind in (1,4):delta=word&0x3ffffff;delta=delta if delta<2**25 else delta-2**26
 else:delta=(word>>5)&0x7ffff;delta=delta if delta<2**18 else delta-2**19
 assert at+delta==to;branchCount+=1
# Independent receipt owner/range and exact eligible call derived from inventories.
eligible=[x for x in r['TCCALL']if x[5]>0];assert len(eligible)==1 and eligible[0]==saved['eligibleSite']
assert saved['readerFN']==eligible[0][2]==1 and saved['readerSIR']==[1,174] and saved['finitePaths']==256 and saved['literalBase']==1 and saved['pooledTableBytes']==2048
sir={x[1]:x[2:]for x in r['FSIR']if x[0]==0};assert sir[1]==[1,1,1,1] and sir[174]==[2,1,0,0]
assert saved['eligibleSite'][0:6]==[220,3,1,0,1,1]
assert c['status']=='COMPLETE_CURRENT_TYPED_BIND8_READONLY_IDENTITY_ONLY' and c['sourcePinsSHA256']==g['sha256']['source-pins.json'] and c['rootGOSHA256']==ref(G)['sha256']
for k in ('terminal','attempts','generatedPins'):
 q=c[k];assert ref(Path(q['path']))=={n:q[n]for n in ('bytes','sha256')}
assert c['images']==read(O/'images.json')
for image in c['images']:
 for k in ('source','container','native'):
  q=image[k];assert ref(Path(q['path']))=={n:q[n]for n in ('bytes','sha256')}
for product in c['products']:
 for k in ('container','native'):
  q=product[k];assert ref(Path(q['path']))=={n:q[n]for n in ('bytes','sha256')}
 assert product['offset']==1224 and product['exports']==[list(x)for x in exports]
for k in ('TCEmitterExecuted','generatedWorkloadExecuted','selfhostFixedPointQualified','performanceQualified','OSStackLimitProof','hardMemoryCapEstablished'):assert c[k] is False
assert c['memoryMetric']=='sum-ri_phys_footprint' and c['memoryPolicySupersedesAS4GiB'] is True
report={'status':'PASS_INDEPENDENT_ACTUAL_CURRENT_TYPED_BIND8_READONLY_IDENTITY_PORTABLE_MEMORY_ONLY','independent':True,'priorOperationalAuthorship':False,'priorParticipation':'Independent SOURCE/fixture/failure reviewer; no driver/wrapper/validator/observer implementation authorship','sourcePinsSHA256':g['sha256']['source-pins.json'],'driverSHA256':g['sha256']['run.py'],'inputPinsSHA256':g['sha256']['input-pins.json'],'preregistrationSHA256':g['sha256']['preregistration.json'],'rootGOSHA256':ref(G)['sha256'],'completionSHA256':ref(O/'completion.json')['sha256'],'wholeSourceFilesHashed':len(sp),'wholeInputFilesHashed':len(ip),'wholeInputBytesHashed':sum(q['bytes']for q in ip.values()),'savedParentCalls':8,'allParentReaped0':True,'memorySampleCounts':memCounts,'acceptedMemorySamples':sum(memCounts),'memorySummaries':memorySummaries,'environmentRuntimeExtraKeyNames':environmentExtras,'exact17NativeExecWitnesses':8,'namedFSIZE_CPUReadbacks':8,'all17ArenaCounterRowsVerified':8,'wholeBaselineNative':ref(O/'current-baseline.bin'),'wholeObserverNative':ref(O/'readonly-observer.bin'),'wholeOriginalCRCContainer':ref(O/'ordinary-input.kseed'),'wholeOriginalCRCNative':ref(O/'ordinary-input.bin'),'wholeOrdinaryObservedIdentity':True,'benchOffset':1224,'typedBindingSummary':{k:saved[k]for k in('readerFN','readerSIR','finitePaths','literalBase','pooledTableBytes','eligibleSite','wholeCodeWords')},'independentResolvedBranchFixups':branchCount,'reviewedPureValidatorRecomputedFromRaw':True,'typedGateBeforeChild8':'Enforced by exact pinned driver ordering; saved typed binding, products and ordered successful receipts agree; no independent syscall/event trace','currentProducerBindingQualified':True,'qualificationScope':'Current source readonly observer original CRC typed/physical binding and whole output identity only','TCEmitterExecuted':False,'generatedWorkloadExecuted':False,'selfhostFixedPointQualified':False,'performanceQualified':False,'hardMemoryCapEstablished':False,'reviewerOperationalCalls':0,'evidence':{str(p):ref(p)for p in [G,*sorted(O.iterdir())]},'limitations':['Physical memory witnesses are accepted sequential sampled sums only; no atomic/transient census, AS/privatebytes/hardpeak/finiteovershoot guarantee, startup and EOF-to-wait gaps remain.','Parent receipts expose wrapper/loader reaps. Native compiler-child closure relies pinned loader supervise/wait and normal result, not separately saved guest Popen receipts.','Within-sample reread/inventory API calls checked by pinned adapter are not individually retained API traces. Completion path requires pipe EOF; no independent syscall trace.','Observer printing changes compiler arena allocation; output identity does not establish compiler arena or near-limit equivalence.','Raw binding validator was reviewed and recomputed offline; independent raw hash/sum/container/receipt/branch arithmetic supplements it. No native/runtime diagnostic rerun.','Prior preexec/environment/helper failures remain preserved with their original uncertainties and no-retry boundaries.','Root observed outer exit0; no independently saved outer raw transport receipt. No guest TC execution, effect/trap/fuel/cap rollback, fixedpoint/full19/performance qualification.']}
p=W/'report.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444)
print(json.dumps({'path':str(p),**ref(p),'status':report['status']}))
