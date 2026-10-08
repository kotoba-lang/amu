from pathlib import Path
import hashlib,json,stat
D=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-native-component-v3-resource-design-20261008')
W=Path(__file__).resolve().parent
G=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-resource-diagnostic1-go-root-20261008/root-go.json')
def ref(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 b=p.read_bytes();t=p.lstat();assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns)
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):return json.loads(p.read_bytes())
assert ref(G)['sha256']=='b95b6e418379e7b9f61ca4f054d1905793954e7f2b693ed2e45c27ca5b117f3b'
g=read(G);sp=read(D/'source-pins.json');ip=read(D/'input-pins.json')
assert set(g)=={'status','maximumDiagnosticChildren','nativeLoaderCalls','compilerCalls','noRetry','outerExecution','outputRoot','sha256','sourceReviews'}
assert g['status']=='ROOT_GO_RESOURCE_INSTALL_DIAGNOSTIC1_ONLY' and g['maximumDiagnosticChildren']==1 and g['nativeLoaderCalls']==g['compilerCalls']==0 and g['noRetry'] is True and g['outerExecution']=='require_escalated'
assert g['outputRoot']==str(D/'run-outputs') and set(g['sha256'])=={'run.py','preregistration.json','source-pins.json','input-pins.json'}
for n,q in sp.items():assert ref(D/n)==q
for n,q in ip.items():assert ref(Path(n))==q
for n,q in read(D/'freeze.json')['files'].items():assert ref(D/n)==q
for n,h in g['sha256'].items():assert ref(D/n)['sha256']==h
assert len(g['sourceReviews'])==2 and len({q['path'] for q in g['sourceReviews']})==2
for q in g['sourceReviews']:
 p=Path(q['path']);assert set(q)=={'path','bytes','sha256'} and ref(p)=={k:q[k] for k in ('bytes','sha256')}
 r=read(p);assert r['status']=='PASS_SOURCE_ONLY_RESOURCE_INSTALL_DIAGNOSTIC1' and r['sourcePinsSHA256']==g['sha256']['source-pins.json'] and r['driverSHA256']==g['sha256']['run.py']
O=D/'run-outputs';names={'attempt.json','outcomes.json','terminal.json','resource-journal.jsonl','stdout','stderr'}
assert {p.name for p in O.iterdir()}==names
raw=(O/'resource-journal.jsonl').read_bytes();assert 0<len(raw)<=65536 and raw.endswith(b'\n')
assert (O/'stdout').read_bytes()==raw and (O/'stderr').read_bytes()==b''
rows=[json.loads(line) for line in raw.splitlines()];assert len(rows)==6
inf=9223372036854775807
for k,(name,budget) in enumerate((('RLIMIT_FSIZE',67108864),('RLIMIT_CPU',1800),('RLIMIT_AS',4294967296)),1):
 before=rows[(k-1)*2];after=rows[(k-1)*2+1]
 assert before=={'stage':'before','index':k,'limit':name,'before':[inf,inf],'desired':[budget,budget],'infinity':inf}
 if k<3:assert after=={'stage':'outcome','index':k,'limit':name,'outcome':'installed','readback':[budget,budget]}
 else:assert after=={'stage':'outcome','index':3,'limit':'RLIMIT_AS','outcome':'failure','before':[inf,inf],'desired':[budget,budget],'readback':[inf,inf],'exception':"ValueError('current limit exceeds maximum limit')",'exceptionType':'ValueError'}
assert read(O/'outcomes.json')=={'status':'RESOURCE_INSTALL_FAILURE_EXACT_LIMIT_RETAINED','rows':rows,'nativeLoaderCalls':0,'compilerCalls':0}
pr=read(D/'preregistration.json');a=read(O/'attempt.json')
assert set(a)=={'argv','environment','nativeLoaderCalls','compilerCalls','state','pid','reason','reaped','returncode','cleanup'}
assert a['argv'][:3]==[pr['interpreter']['path'],str(D/'diagnostic-child.py'),'--journal-fd'] and len(a['argv'])==4 and int(a['argv'][3])>=3
assert a['environment']==pr['environment'] and a['nativeLoaderCalls']==a['compilerCalls']==0 and a['state']=='terminal' and type(a['pid']) is int and a['pid']>0
assert a['reason'] is None and a['reaped'] is True and a['returncode']==78 and a['cleanup']==[]
assert read(O/'terminal.json')=={'childAttempts':1,'reaped':True,'success':False,'noRetry':True,'nativeLoaderCalls':0,'compilerCalls':0}
report={'status':'PASS_INDEPENDENT_SAVED_RESOURCE_DIAGNOSTIC1_AS_FAILURE_ONLY','independent':True,'priorOperationalAuthorship':False,'priorParticipation':'Independent SOURCE reviewer and V2 saved failure auditor; no diagnostic implementation authorship','sourcePinsSHA256':g['sha256']['source-pins.json'],'driverSHA256':g['sha256']['run.py'],'rootGOSHA256':ref(G)['sha256'],'wholeSourceFilesHashed':len(sp),'wholeInputFilesHashed':len(ip),'wholeInputBytesHashed':sum(q['bytes'] for q in ip.values()),'diagnosticChildren':1,'savedReaped':True,'savedChildReturncode':78,'stdoutJournalIdentity':True,'journalBytes':len(raw),'stderrBytes':0,'installedExactReadbacks':{'RLIMIT_FSIZE':[67108864,67108864],'RLIMIT_CPU':[1800,1800]},'failedLimit':'RLIMIT_AS','failedDesired':[4294967296,4294967296],'failedReadback':[inf,inf],'exception':rows[-1]['exception'],'noRetry':True,'diagnosticSuccess':False,'native8Authorized':False,'reviewerOperationalCalls':0,'nativeLoaderCalls':0,'compilerCalls':0,'evidence':{str(p):ref(p) for p in [G,*sorted(O.iterdir())]},'limitations':['Saved ordinary-body AS setter failed in this single pinned Python invocation; it does not prove AS universally unsupported or establish the old V2 preexec failing setter.','V2 historical preexec failure remains exact-setter unknown; no retry or new native execution occurred.','Root observed outer tool exit78; no independent saved outer raw receipt is available. Saved child exit78 is verified.','Saved protocol and pinned supervisor support EOF/reap/capture checks; no independent OS trace or kernel physical-memory enforcement claim.','No loader/compiler, current-producer binding, artifact identity, fixed-point, semantics or timing qualification established.']}
p=W/'report.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444)
print(json.dumps({'path':str(p),**ref(p),'status':report['status']}))
