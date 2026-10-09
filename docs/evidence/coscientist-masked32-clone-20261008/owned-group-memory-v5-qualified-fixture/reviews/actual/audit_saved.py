from pathlib import Path
import json,hashlib,stat
D=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-portable-memory-qualification-v5-20261008')
G=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-portable-memory-qualification-v5-go-root-20261008/root-go.json')
W=Path(__file__).resolve().parent
def ref(p):
 a=p.lstat();assert stat.S_ISREG(a.st_mode) and not p.is_symlink()
 b=p.read_bytes();z=p.lstat();assert(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):return json.loads(p.read_bytes())
sp=read(D/'source-pins.json');ip=read(D/'input-pins.json');g=read(G);pr=read(D/'preregistration.json')
assert ref(D/'source-pins.json')['sha256']=='dec95b91de1b113329b9174c7c0a5fc8bf94f853902c608780469bd4ff331a49'
assert ref(D/'run.py')['sha256']=='8eb8dd02f6a75843f7180e9e0441e6842608f3a5327b7e5d2f68c13adbf4bdd9'
for n,q in sp.items():assert ref(D/n)==q
for n,q in ip.items():assert ref(Path(n))==q
for n,q in read(D/'freeze.json')['files'].items():assert ref(D/n)==q
assert set(g)=={'status','maximumPythonChildren','maximumMemorySamples','nativeLoaderCalls','setters','noRetry','outerExecution','outputRoot','sha256','sourceReviews'}
assert g['status']=='ROOT_GO_OWNED_GROUP_MEMORY_QUALIFICATION2_ONLY' and g['maximumPythonChildren']==2 and g['maximumMemorySamples']==8 and g['nativeLoaderCalls']==g['setters']==0
assert g['noRetry'] is True and g['outputRoot']==str(D/'run-outputs') and g['outerExecution']=='require_escalated'
assert set(g['sha256'])=={'run.py','preregistration.json','source-pins.json','input-pins.json'}
for n,h in g['sha256'].items():assert ref(D/n)['sha256']==h
assert len(g['sourceReviews'])==2 and len({q['path']for q in g['sourceReviews']})==2
for q in g['sourceReviews']:
 p=Path(q['path']);assert set(q)=={'path','bytes','sha256'} and ref(p)=={k:q[k]for k in ('bytes','sha256')}
 r=read(p);assert r['status']=='PASS_SOURCE_ONLY_OWNED_GROUP_MEMORY_QUALIFICATION2' and r['sourcePinsSHA256']==g['sha256']['source-pins.json'] and r['driverSHA256']==g['sha256']['run.py']
O=D/'run-outputs';assert {p.name for p in O.iterdir()}=={'attempt.json','terminal.json','completion.json','stdout','stderr','receipts.jsonl'}
a=read(O/'attempt.json');t=read(O/'terminal.json');c=read(O/'completion.json')
assert a=={'argv':pr['leaderArgv'],'environment':pr['environment'],'state':'terminal','maximumPythonChildren':2,'nativeLoaderCalls':0,'setters':0,'pid':23383,'reaped':True,'returncode':0,'cleanup':[]}
assert t=={'success':True,'leaderReaped':True,'groupTerminationIssued':False,'expectedNormalClosureProof':'helper wait0 + stable one-again samples + leader wait0','postReapGroupOperations':0,'waitEntered':True,'waitUncertain':False,'signalingAuthorityRetired':True,'PythonChildStartsAtMost':2,'samples':8,'nativeLoaderCalls':0,'setters':0,'noRetry':True}
raw=(O/'stdout').read_bytes();journal=(O/'receipts.jsonl').read_bytes()
assert 0<len(raw)<=65536 and raw.endswith(b'\n') and 0<len(journal)<=65536 and journal.endswith(b'\n') and (O/'stderr').read_bytes()==b''
ph=[json.loads(l)for l in raw.splitlines()];rows=[json.loads(l)for l in journal.splitlines()]
assert ph==[
 {'phase':'one-ready','pid':23383,'pgid':23383},
 {'phase':'two-ready','pid':23383,'pgid':23383,'helperPID':23384,'helperArgv':pr['helperArgv']},
 {'phase':'one-again-ready','pid':23383,'pgid':23383,'helperPID':23384,'helperReaped':True,'helperReturncode':0},
 {'phase':'leader-complete','pid':23383,'childStarts':2,'helperReaped':True}]
assert pr['helperArgv']==[pr['interpreter']['path'],str(D/'fixture.py'),'helper']
assert [q['kind']for q in rows]==['phase','sample','sample','release','phase','sample','sample','sample','sample','release','phase','sample','sample','release','phase']
assert [q['row']for q in rows if q['kind']=='phase']==ph
assert [q for q in rows if q['kind']=='release']==[{'kind':'release','command':x}for x in ('spawn','drop','finish')]
samples=[q['row']for q in rows if q['kind']=='sample'];assert len(samples)==8
births={};uuids={};sums=[];membercounts=[]
for index,q in enumerate(samples,1):
 assert set(q)=={'sample','ownedPGID','metric','aggregateBytes','thresholdBytes','members','hardMemoryCapEstablished'}
 assert q['sample']==index and q['ownedPGID']==23383 and q['metric']=='sum-ri_phys_footprint' and q['thresholdBytes']==4294967296 and q['hardMemoryCapEstablished'] is False
 wanted=[23383,23384] if 3<=index<=6 else [23383]
 assert [m['pid']for m in q['members']]==wanted
 for m in q['members']:
  assert set(m)=={'pid','start','exit','physicalFootprintBytes','uuid'}
  assert type(m['start']) is int and m['start']>0 and m['exit']==0 and type(m['physicalFootprintBytes']) is int and 0<=m['physicalFootprintBytes']<2**64
  assert len(m['uuid'])==32 and len(bytes.fromhex(m['uuid']))==16
  assert m['pid'] not in births or births[m['pid']]==m['start']
  assert m['pid'] not in uuids or uuids[m['pid']]==m['uuid']
  births[m['pid']]=m['start'];uuids[m['pid']]=m['uuid']
 total=sum(m['physicalFootprintBytes']for m in q['members']);assert total==q['aggregateBytes'] and total<=4294967296
 sums.append(total);membercounts.append(len(q['members']))
assert sums==[10355144]*2+[20693904]*4+[10420680]*2 and len(births)==2
assert set(c)=={'status','sourcePinsSHA256','phases','samples','native8Authorized','hardMemoryCapEstablished','actualNormalClosureProof','raw'}
assert c['status']=='COMPLETE_OWNED_GROUP_MEMORY_ADAPTER_QUALIFICATION_ONLY' and c['sourcePinsSHA256']==g['sha256']['source-pins.json'] and c['phases']==ph and c['samples']==samples
assert c['native8Authorized'] is False and c['hardMemoryCapEstablished'] is False
assert c['actualNormalClosureProof']=={'helperWait0':True,'stableOneAgainSamples':2,'leaderWait0':True}
assert set(c['raw'])=={'stdout','stderr','receipts.jsonl','attempt.json','terminal.json'}
for n,q in c['raw'].items():assert ref(O/n)==q
report={
 'status':'PASS_INDEPENDENT_SAVED_OWNED_GROUP_MEMORY_ADAPTER_V5_FIXTURE_ONLY',
 'independent':True,'priorOperationalAuthorship':False,'priorParticipation':'Independent V5 SOURCE reviewer and V4 saved failure auditor; no fixture/adapter/driver authorship',
 'sourcePinsSHA256':g['sha256']['source-pins.json'],'driverSHA256':g['sha256']['run.py'],'inputPinsSHA256':g['sha256']['input-pins.json'],'preregistrationSHA256':g['sha256']['preregistration.json'],'rootGOSHA256':ref(G)['sha256'],
 'wholeSourceFilesHashed':len(sp),'wholeInputFilesHashed':len(ip),'wholeInputBytesHashed':sum(q['bytes']for q in ip.values()),
 'acceptedSamples':8,'memberCounts':membercounts,'independentAggregateFootprintBytes':sums,'distinctMemberBirths':2,'birthAndUUIDStableAcrossSavedSamples':True,
 'leaderWait0Verified':True,'helperWait0HandshakeVerified':True,'stableOneAgainSamples':2,'normalClosureEstablishedForFixedFixture':True,
 'groupTerminationIssued':False,'signalAuthorityRetired':True,'waitUncertain':False,'savedPostReapGroupOperations':0,'noRetry':True,
 'completionRawHashesVerified':True,'stdoutBytes':len(raw),'stderrBytes':0,'journalBytes':len(journal),
 'qualificationScope':'Limited successful fixed Python one/two/one owned-group adapter fixture with soft sum-ri_phys_footprint only',
 'native8Authorized':False,'hardMemoryCapEstablished':False,'currentProducerBindingQualified':False,'timingQualified':False,'reviewerOperationalCalls':0,
 'evidence':{str(p):ref(p)for p in [G,*sorted(O.iterdir())]},
 'limitations':[
  'Parent supervisor completion path requires both raw pipe EOF and reap, and exact saved raw hashes match; no independent OS syscall trace. Individual inventory calls and repeated within-sample birth reads are checked by pinned adapter but not separately retained raw API records.',
  'Helper wait0 is the fixed leader handshake plus pinned fixture/leader wait0, not a separately exposed helper Popen object in this auditor.',
  'Two stable live members observed only in the controlled waiting phases; sequential census cannot exclude transient members or unsampled memory spikes.',
  'Soft footprint sum without shared-page deduplication; no RSS/privatebytes/AS equivalence, hard peak limit or finite overshoot guarantee.',
  'Root observed outer exit0; saved leader exit0 is verified but no independent saved outer raw transport receipt.',
  'Earlier V4 failure remains preserved with unknown helper closure and no completion; V5 success does not retroactively close it.',
  'No native loader/compiler/resource setter/SSH/CPU/process API executed by reviewer. This fixture does not establish native8/current producer/semantic/fixedpoint/performance qualification.'
 ]}
p=W/'report.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444)
print(json.dumps({'path':str(p),**ref(p),'status':report['status']}))
