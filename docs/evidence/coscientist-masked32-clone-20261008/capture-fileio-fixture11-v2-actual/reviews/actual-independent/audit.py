from pathlib import Path
import hashlib,json,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-capture-popen-transfer-fixture-source-v2-20261009';S=W/'crc-capture-popen-transfer-fixture-supervisor-source-v3-root-20261009';N=W/'crc-original-guest-native-controller-source-v4-20261009-dense';O=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def check(p,v):
 assert not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode);b=p.read_bytes();assert len(b)==v['bytes']and sha(b)==v['sha256'],str(p)
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text());sg=json.loads((S/'GO.json').read_text());go=json.loads((D/'GO.json').read_text());term=json.loads((S/'run-outputs/terminal.json').read_text());cp=json.loads((D/'run-outputs/completion.json').read_text())
for n,v in sp.items():check(D/n,v)
for n,v in ip.items():check(Path(n),v)
for n,v in sg['pins'].items():check(Path(n),v)
for v in sg['sourceReviews']+[sg['supervisorReview']]:check(Path(v['path']),v)
assert sha((S/'supervise.py').read_bytes())==sg['supervisorSHA256']
assert go=={'status':'GO_FIXED_FILEIO_THREAD_FIXTURE_ONCE','sourcePinsSha256':sha((D/'source-pins.json').read_bytes()),'outputRoot':str(D/'run-outputs')}
assert term['returncode']==0 and term['terminal']is True and term['waitUncertain']is False and term['failure']is None and term['driverLaunches']==1 and not term['killedDirectChild']
for n,v in term['raw'].items():check(S/'run-outputs'/n,v);assert v['bytes']==0
assert cp['status']=='PASS_FIXED_FILEIO_TRANSFER_AND_INJECTED_AUTHORITY_ONLY'and len(cp['cases'])==11
components={n:sha((D/n).read_bytes())for n in ['capture.py','integration.py','controller.py']};assert components==cp['componentSourcePins']
for n,v in components.items():assert sha((N/n).read_bytes())==v
receipts=[];peak=0
for i,mode in enumerate(pr['cases'],1):
 p=D/'run-outputs'/str(i)/'receipt.json';q=json.loads(p.read_text());assert q['case']==mode and q['componentSourcePins']==components and cp['cases'][i-1]=={'index':i,'case':mode,'status':q['status']}
 if i<=8:
  live=set();localpeak=0
  for action,fd,kind in q['ledger']:
   assert type(fd)is int and fd>=0
   if action=='open':assert fd not in live;live.add(fd);localpeak=max(localpeak,len(live))
   else:assert action=='close'and fd in live;live.remove(fd)
  assert not live and localpeak==q['peakOwnedFDs']<=9;peak=max(peak,localpeak)
  act=q['activeSnapshot']
  if i in [7,8]:assert act['hashes']is None and not act['stoppedWriter']
  else:assert act is None
  if i<=5:assert q['error']['ownership']=='parent-denied'
  elif i<=7:assert q['error']['ownership']=='worker-granted'and q['capture']['stoppedWriter']
  if i==7:assert q['error']['cleanup']==['worker-stop-ack-unavailable']
  if i==8:assert q['error']is None and q['capture']['completeRaw']
  cap=q['capture']
  if cap and cap['hashes']:
   for n,v in cap['hashes'].items():check(p.parent/(n+'.raw'),v)
 else:
  assert q['actualProcessAPIs']==0
  if i==9:assert q['events']==['group-callback-return','retired','injected-wait']and not q['waitUncertain']
  if i==10:assert q['events']==['group-callback-return','retired','injected-wait']and q['waitUncertain']
  if i==11:assert q['events']==['injected-callback-fault','caller-observed-retired','reentry-refused']and 'retire:group-exception-atomic'in q['controllerEvents']
 receipts.append(pin(p))
raws=sorted((D/'run-outputs').glob('*/*.raw'));assert len(raws)==6 and sum(p.stat().st_size for p in raws)==7
for p in raws:assert p.read_bytes()==(b'answer\n'if p.parent.name=='8'and p.name=='stdout.raw'else b'')
assert not list((D/'run-outputs').glob('*/partial-failure.json'))
r={'status':'PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','independent':True,'priorAuthorship':False,'captureSHA256':components['capture.py'],'integrationSHA256':components['integration.py'],'controllerSHA256':components['controller.py'],'sourcePinsSHA256':sha((D/'source-pins.json').read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'completion':pin(D/'run-outputs/completion.json'),'GO':pin(D/'GO.json'),'supervisorGO':pin(S/'GO.json'),'supervisorTerminal':pin(S/'run-outputs/terminal.json'),'sourceReviews':sg['sourceReviews'],'supervisorReview':sg['supervisorReview'],'verified':{'sourceFiles':len(sp),'inputFiles':len(ip),'supervisorPins':len(sg['pins']),'allPinsExactRegular':True,'fixedCases':11,'rawFiles':6,'rawBytes':7,'savedLedgerPeak':peak,'allEightTransferLedgersClose':True,'activeSnapshots7And8HashesUnavailable':True,'componentsExactlyNativeV4':True,'singleSupervisorDirectChildReaped0':True,'supervisorStdoutStderrBytes':[0,0]},'receipts':receipts,'raws':[pin(p)for p in raws],'limitations':['This is saved evidence for controlled FileIO/pipe/thread and injected authority callbacks only; no native/Popen/actual group/OS wait or memory qualification.','Thread-dead acknowledgement, ownership transfer chronology, grant interruption and no extra operations derive from frozen source assertions plus saved success receipts, not independent OS syscall trace. Ledgers/raw hashes are independently checked; no universal asynchronous ownership proof.','Root outer tool exit0 is parent-observed, no saved outer raw receipt here. Durable helper terminal independently records fixture child41189 reaped0, elapsed0.18162479199963855.','Future nativeV4 must separately review its exact wiring and bind this report. Hard peak, descendants, fuel/counters/guest8/full19/performance remain unqualified.'],'reviewerOperations':0,'actualFDThreadProcessNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(O/'report.json')))
