from pathlib import Path
from types import SimpleNamespace
import hashlib,json,ast
D=Path('/Users/junkawasaki/github/workspaces/codex/crc-capture-popen-transfer-fixture-source-v1-20261009');O=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
sp=D/'source-pins.json';ip=D/'input-pins.json';f=json.loads((D/'freeze.json').read_text());pr=json.loads((D/'preregistration.json').read_text());sps=json.loads(sp.read_text());ips=json.loads(ip.read_text())
assert sha(sp.read_bytes())=='65229d7a9b17b28f29a5896287c68410009366fd1d823d2a946c1231d3812c6f'
for p,v in [(sp,f['sourcePins']),(ip,f['inputPins'])]:assert p.stat().st_size==v['bytes'] and sha(p.read_bytes())==v['sha256']
total=0
for name,v in sps.items():
 b=(D/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256'],name;total+=len(b)
assert len(sps)==f['sourceFiles']==8 and total==f['sourceBytes']
inputTotal=0
for name,v in ips.items():
 b=Path(name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256'],name;inputTotal+=len(b)
assert len(ips)==f['inputFiles']==1945
for n,v in f['componentSourcePins'].items():assert sps[n]==v
for p in D.glob('*.py'):ast.parse(p.read_text())
assert len(pr['cases'])==11 and len(set(pr['cases']))==11
assert pr['cases']==['second-dup','original-close','construct','start-before','ambiguous-start','grant-ack','grant-no-ack','delayed-eof','retire-before-wait','uncertain-wait','atomic-callback-exception']
assert pr['maximumPipes']==17 and pr['maximumDuplicateFDs']==16 and pr['maximumAuxThreadStarts']==10 and pr['maximumSimultaneousAuxThreads']==2 and pr['maximumConcurrentOwnedFDs']==9
assert pr['maximumTotalFDsWithExactlyStdioInherited']==12 and len(pr['fixedSuppliedEnvironment'])==8
# No real Lock/Event/thread/FD instantiation: source class-only injection with a synchronous lock model.
class FakeLock:
 def __init__(self):self.held=False
 def __enter__(self):assert not self.held;self.held=True;return self
 def __exit__(self,*args):self.held=False
ins={};exec(compile((D/'integration.py').read_bytes(),'inert-integration','exec'),ins)
cs=(D/'controller.py').read_text().replace('import threading\n','').replace('from integration import classify_memory,MEMORY_POLICY\n','')
ns={'threading':SimpleNamespace(Lock=FakeLock),'classify_memory':ins['classify_memory'],'MEMORY_POLICY':ins['MEMORY_POLICY']};exec(compile(cs,'injected-controller','exec'),ns)
ctl=ns['Controller'](lambda:0,1)
def fault():assert ctl.lock.held;raise RuntimeError('pure injected failure')
try:ctl.group(fault)
except RuntimeError:pass
assert not ctl.active and ctl.events[-1]=='retire:group-exception-atomic'
try:ctl.group(lambda:None)
except AssertionError:pass
else:raise AssertionError('reentry')
ctl.wait(lambda t:0)
try:ctl.wait(lambda t:0)
except AssertionError:pass
else:raise AssertionError('repeatwait')
r={'status':'PASS_SOURCE_ONLY_FIXED_FILEIO_CAPTURE_CONTROLLER_FIXTURE','independent':True,'priorAuthorship':False,'sourcePinsSHA256':sha(sp.read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'subject':str(D),'freeze':pin(D/'freeze.json'),'inputPins':pin(ip),'verifiedClosure':{'sourceFiles':len(sps),'sourceBytes':total,'inputFiles':len(ips),'inputBytes':inputTotal,'componentSourcePins':f['componentSourcePins']},
'fixedScope':{'cases':pr['cases'],'driverLaunches':1,'auxThreadStarts':10,'simultaneousAuxThreads':2,'threadsIncludingMain':3,'pipes':17,'duplicates':16,'ownedFDPeak':9,'totalFDsWithOnlyInheritedStdio':12,'rawFilesAtMost':6,'expectedRawBytes':7,'bodySeconds':9,'rootOuterSeconds':10,'rootReapSeconds':5,'receiptBytes':32768,'totalJSONBytes':458752,'noPopenNativeGroupOperationsInsideFixture':True},
'verifiedObservations':['All actual pipe/FileIO/selector/thread/IO operations are deferred behind exact GO/pin/interpreter/eight-env/fresh-output main guard. Only optional CF runtime metadata extra is admitted.', 'Initial pipe and FileIO acquisition now lies inside owning try/finally; pending original reads, writes and reuse endpoints retained for failure cleanup. After grant only worker closes duplicate reads, with partial-failure ledger/hash-unavailable on uncertainty.', 'Expected pregrant seconddup/close/construct/start failures permanently deny worker ownership; ambiguous start joins the actual started thread before case PASS. Grant-ack and grant-no-ack distinguish stopped acknowledgement from controlled active writer, then require dead worker.', 'Delayed EOF checks active hashes unavailable, idempotent original FileIO close leaves new pipe ownership intact, writes seven bytes, closes both writers, waits for full EOF and explicitly joins/requires dead capture thread before PASS.', 'Three authority cases cover serialized explicit retirement, uncertain injected wait with permanently retired authority, and callback-exception atomic retirement. All require dead auxiliary threads. Pure synchronous FakeLock independent check confirms retirement before group exception returns, reentry/second wait refused.', 'All reads retain copied 4096/16MiB observed bounds,8MiB/1MiB prefixes and first-refusal1s drain clamped to absolute deadline. Controlled handshake waits and joins are bounded by fixed/original times. Receipts capped32KiB; completion written after fixed receipts and raw count/byte check.'],
'limitations':['This SOURCE review admits only a separately GO-ed fixed11 FileIO/thread fixture with required reviewed root supervisor. Supervisor is not yet reviewed by this report; no execution authorization or actual fixture proof is supplied here.', 'No actual Popen creation, native guest, OS child wait/group/process API, sampler memory, counter/fuel semantic qualification or nativeV4 wiring proof. Controller observe method callback cleanup/durability is outside these fixed cases.', 'Exact old FD integer reuse is not forced; arbitrary grant-boundary asynchronous interruption, unreturned syscall descriptors, constructor side effects beyond controlled cases and universal OS ownership proof remain unqualified.', 'Wall/fsync/regular-file/event/joins are cooperative. Outer10s plus5s reap supervision and fixed inherited-FD assumption must hold; missing acknowledgement or partial ledger cannot prove all closure.', 'Thread chronology is checked by fixed source-bound events/assertions, not independent OS scheduling trace. Atomic-case second thread starts only after done event, while source lock/exception placement establishes pre-return retirement.'],
'draftFindingsDisposition':'Setup scope, reuse ownership, explicit positive dead-thread ack,17-pipe narrative and exact environment admission all repaired before this freeze; one extra atomic exception case added. Earlier preflight stays a draft observation, not frozen failure.',
'operationalCalls':0,'actualFDThreadProcessNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(O/'report.json')))
