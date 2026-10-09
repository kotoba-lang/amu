"""Inert native call wiring. Invoked only by separately reviewed run.py GO."""
from pathlib import Path
import os,json,time,threading,subprocess,hashlib,importlib.util,socket
from ownership import HeldProtocol,validate_failure
from capture import Capture
from integration import transfer_popen_reads,TransferFailure
from controller import Controller
from runtime import qualify
from callback_contract import row as sample_row
from artifact_admission import accept_artifact_observation
def need(x,m):
 if not x:raise AssertionError(m)
def hfile(p,cap):
 p=Path(p);need(p.is_file()and not p.is_symlink(),'regular stopped-owner output');s=p.stat();need(s.st_size<=cap,'bounded hash');b=p.read_bytes();s2=p.stat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable stopped output');return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def persist_jsonline(file,row,used,maximum):
 b=(json.dumps(row,separators=(',',':'))+'\n').encode();need(len(b)<=4096 and used+len(b)<=maximum,'bounded journal')
 view=memoryview(b)
 while view:
  n=file.write(view);need(type(n)is int and 0<n<=len(view),'complete journal write');view=view[n:]
 os.fsync(file.fileno());return used+len(b)
def resource_journal(path,pr,nativeArgv):
 need(path.stat().st_size<=65536,'bounded setter journal');rows=[json.loads(x)for x in path.read_bytes().splitlines()];need(len(rows)==6,'exact six journal rows')
 ew=rows[0];keys=sorted(pr['environment']);need(ew=={'stage':'environment-admission','suppliedKeyNames':keys,'runtimeExtraKeyNames':ew.get('runtimeExtraKeyNames'),'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':keys,'nativeExecEnvironmentExact':True}and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']],'exact17 native environment witness')
 for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)]):
  before,after=rows[1+2*k:3+2*k];need(before['index']==k+1 and before['limit']==name and before['stage']=='before'and before['desired']==[soft,hard],'exact named setter')
  need(set(before)=={'index','limit','stage','before','desired'},'no unknown resource-row keys')
  bs,bh=before['before'];need((bs==9223372036854775807 or bs>=soft)and(bh==9223372036854775807 or bh>=hard),'no inherited finite limit raised')
  need(after=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]},'exact installed resource readback')
 need(rows[-1]=={'stage':'exec-ready','argv':nativeArgv,'ASSetterRequested':False,'CPUGraceHardSeconds':31},'exact loader exec witness');return True
def call(D,O,pr,case,rows,save,admissionSHA256):
 need(len(rows)<2 and pr['cases'][len(rows)]==case,'fixed ordered190 no retry')
 # Existing inherited closure is checked by caller before Popen, never during sampling.
 spec=importlib.util.spec_from_file_location('typed_owned_sampler',D/'typed-adapter.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 invocation=admissionSHA256;api=mod.DarwinOwnedGroupAPI(invocation) # Library setup before Popen; no query yet.
 base=O/case['label'];lj=base.with_suffix('.limit-journal.jsonl');mj=base.with_suffix('.memory-journal.jsonl')
 paths={k:base.with_suffix('.'+k)for k in ['stdout','stderr']}
 r={'index':len(rows)+1,'label':case['label'],'state':'started','environment':pr['environment'],'nativeArgv':case['nativeArgv']};rows.append(r);save(O/'attempts.json',rows)
 peer=None;host=None;protocol=None;ownershipState={};proc=None;cap=None;ctl=None;stop=threading.Event();watch=None;watchErrors=[];waitCalled=False;waitRC=None;waitUncertain=False;captureAck=False;observed=None;failure=None;sampleBytes=0;sampleCount=0;birthBinding={};deadline=time.monotonic()+30
 oj=base.with_suffix('.ownership-journal.jsonl');ownershipBytes=0
 with lj.open('xb',buffering=0)as limitFile,mj.open('xb',buffering=0)as memoryFile,oj.open('xb',buffering=0)as ownershipFile:
  def waitDirect(budget):
   nonlocal waitCalled,waitRC,waitUncertain
   need(not waitCalled,'one direct wait');waitCalled=True
   try:waitRC=proc.wait(timeout=max(.001,min(30,budget)));return waitRC
   except BaseException:waitUncertain=True;raise
  def stopWatchdog(budget):
   stop.set()
   if watch is not None:watch.join(timeout=min(.5,max(0,budget)))
   return (watch is None or not watch.is_alive())and not watchErrors
  def persistSample(q):
   nonlocal sampleBytes,sampleCount
   sampleCount+=1;need(sampleCount<=2048 and q['sample']==sampleCount,'exact ordered finite sample journal')
   numeric,newBinding=sample_row(q,time.monotonic_ns(),proc.pid,birthBinding);birthBinding.update(newBinding)
   sampleBytes=persist_jsonline(memoryFile,numeric,sampleBytes,8388608);return True
  def persistOwnership(q):
   nonlocal ownershipBytes
   ownershipBytes=persist_jsonline(ownershipFile,q,ownershipBytes,65536);return True
  def qualifiedResources():
   need(protocol is not None and protocol.finish()is True,'exact childwait0');ownershipState.update(qualified=True,childWait0=True)
   return resource_journal(lj,pr,case['nativeArgv'])
  def validateRaw(raw):
   out=paths['stdout'].read_bytes();err=paths['stderr'].read_bytes();need(0<len(out)<=8388608 and len(err)<=1048576,'bounded complete raw')
   report=qualify(out,err,case['expectedResult']);r['structuredReportObservation']=report;r['counterObservation']={'status':'valid','values':report['arena17']};return True
  try:
   need(len(os.listdir('/dev/fd'))<=32,'finite initial parent FD inventory')
   host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
   argv=[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd',str(limitFile.fileno()),'--admission-sha',admissionSHA256,'--ownership-fd',str(peer.fileno()),'--',*case['nativeArgv']];r['argv']=argv;save(O/'attempts.json',rows)
   proc=subprocess.Popen(argv,cwd=O,env=dict(pr['environment']),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,close_fds=True,pass_fds=(limitFile.fileno(),peer.fileno()),start_new_session=True)
   peer.close();peer=None;r['pid']=proc.pid;ctl=Controller(time.monotonic,deadline);save(O/'attempts.json',rows)
   cap=transfer_popen_reads({'stdout':proc.stdout,'stderr':proc.stderr},os.dup,os.close,lambda reads:Capture(reads,paths,deadline,deadline),lambda c:c.start(),deadline,time.monotonic)
   def watchdog():
    if not stop.wait(max(0,deadline-time.monotonic())):
     try:ctl.group(lambda:os.killpg(proc.pid,9))
     except AssertionError:pass # Already permanently retired; no signal performed.
     except BaseException as ex:watchErrors.append(repr(ex))
   watch=threading.Thread(target=watchdog,name='owned-authority-watchdog',daemon=False);watch.start()
   sampler=mod.OwnedGroupSampler(api,proc.pid)
   seal=json.loads((O/(case['label']+'.admission.json')).read_bytes());nonce=hashlib.sha256((admissionSHA256+seal['rootGO']['sha256']).encode()).hexdigest()
   protocol=HeldProtocol(host,proc.pid,deadline,seal['rootGO']['sha256'],nonce,persistOwnership)
   initial=protocol.handshake(ctl,sampler,persistSample);protocol.start_wait(ctl,ownershipState)
   fault=lambda context:validate_failure(context,api,protocol.bindings,proc.pid,invocation)
   observed=ctl.observe(cap,sampler,waitDirect,stopWatchdog,time.sleep,validateRaw,qualifiedResources,birthBinding,True,persistSample,initial,ownershipState,fault)
   captureAck=observed['capture']['stoppedWriter'];need(accept_artifact_observation(observed) is True and observed['sampleReceiptPersistenceQualified']is True,'complete semantic/sample-or-gap admission')
  except BaseException as ex:
   failure=repr(ex)
   if isinstance(ex,TransferFailure):cap=ex.capture
  finally:
   try:
    if ctl is not None:ctl.retire('final-cleanup')
   except BaseException as ex:failure=failure or'cleanup-retire:'+repr(ex)
   try:
    if not stopWatchdog(max(0,deadline-time.monotonic())):failure=failure or'watchdog-stop-ack-unavailable'
   except BaseException as ex:failure=failure or'cleanup-watchdog:'+repr(ex)
   if cap is not None:
    try:
     if failure:cap.refuse('final-cleanup')
     if not cap.stopped.is_set():cap.join_once(max(0,deadline-time.monotonic()))
     captureAck=cap.snapshot()['stoppedWriter']
    except BaseException as ex:failure=failure or'cleanup-capture:'+repr(ex)
   if proc is not None and not waitCalled:
    try:
     if ctl is not None and not ctl.waitEntered:ctl.wait(waitDirect)
     else:waitDirect(max(0,deadline-time.monotonic()))
    except BaseException as ex:failure=failure or repr(ex)
    # Controller metadata can fail before invoking the callback. Still attempt
    # exactly one local direct wait; no group authority is restored.
    if not waitCalled:
     try:waitDirect(max(0,deadline-time.monotonic()))
     except BaseException as ex:failure=failure or repr(ex)
   if proc is not None:
    # Closed Popen originals never own worker duplicates. Idempotent object close only.
    for s in [proc.stdout,proc.stderr]:
     try:
      if s is not None and not s.closed:s.close()
     except BaseException as ex:failure=failure or'original-pipe-close:'+repr(ex)
   try:
    if protocol is not None:protocol.close()
    elif host is not None:host.close()
    if peer is not None:peer.close()
   except BaseException as ex:failure=failure or'ownership-cleanup:'+repr(ex)
   for file in [limitFile,memoryFile,ownershipFile]:
    try:os.fsync(file.fileno())
    except BaseException as ex:failure=failure or'final-journal-fsync:'+repr(ex)
 r.update(state='terminal'if waitCalled and waitRC is not None and not waitUncertain else'unclosed',returncode=waitRC,waitEntered=waitCalled,waitUncertain=waitUncertain,signalingAuthorityRetired=ctl is None or not ctl.active,captureStopAcknowledged=captureAck,failure=failure,controllerObservation=observed,memorySamples=sampleCount,memoryJournalBytes=sampleBytes,watchdogErrors=watchErrors)
 r['ownershipJournal']=hfile(oj,65536);r['ownershipBindings']=protocol.bindings if protocol else{};r['childWaitReceipt']=protocol.waitReceipt if protocol else None
 r['limitJournal']=hfile(lj,65536);r['memoryJournal']=hfile(mj,8388608)
 if captureAck:
  for name,p in paths.items():
   if p.exists():r[name]=hfile(p,8388608 if name=='stdout'else 1048576)
 save(O/'attempts.json',rows)
 need(failure is None and waitRC==0 and not waitUncertain and captureAck and not watchErrors,'first failure preserved; no retry')
 return {'label':case['label'],'case':case,'returncode':waitRC,'report':r['structuredReportObservation'],'arena':r['counterObservation']['values'],'rawStdoutSHA256':r['stdout']['sha256'],'rawStderrSHA256':r['stderr']['sha256'],'memoryObservation':observed['memoryObservation'],'strictHeldSamplingPolicyPassed':observed['strictHeldSamplingPolicyPassed']}
