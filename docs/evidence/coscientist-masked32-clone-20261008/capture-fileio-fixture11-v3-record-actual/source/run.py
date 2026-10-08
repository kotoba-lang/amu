"""Deferred real FileIO/pipe/thread fixture, no Popen/native/group APIs.

Exact GO and pins required before fixture operations. One attempt; no retry.
Root launch supervision supplies finite outer10s/reap5s; this body uses9s.
"""
import hashlib,io,json,os,pathlib,selectors,sys,threading,time
from capture import Capture
from integration import transfer_popen_reads,TransferFailure
from controller import Controller
D=pathlib.Path(__file__).resolve().parent
OUT=D/'run-outputs'
GO=D/'GO.json'
def need(x,m):
 if not x:raise AssertionError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def durable(p,x):
 b=(json.dumps(x,indent=2)+'\n').encode();need(len(b)<=32768,'receipt32KiB')
 with p.open('xb',buffering=0)as f:need(f.write(b)==len(b),'receipt write');os.fsync(f.fileno())
class Ledger:
 def __init__(self):self.live=set();self.events=[];self.peak=0
 def add(self,fd,kind):
  need(type(fd)is int and fd>=0 and fd not in self.live,'distinct owning FD');self.live.add(fd);self.peak=max(self.peak,len(self.live));self.events.append(['open',fd,kind]);need(self.peak<=9 and len(self.events)<=4096,'finite FD ledger');return fd
 def closed(self,fd,kind):
  need(fd in self.live,'known FD owner');self.live.remove(fd);self.events.append(['close',fd,kind]);need(len(self.events)<=4096,'FD event budget')
 def close(self,fd):os.close(fd);self.closed(fd,'raw')
 def pipe(self):
  a,b=os.pipe();return self.add(a,'pipe-read'),self.add(b,'pipe-write')
 def duplicate(self,fd):return self.add(os.dup(fd),'duplicate-read')
class Stream:
 def __init__(self,fd,ledger,fail=False):self.obj=io.FileIO(fd,'rb',closefd=True);self.ledger=ledger;self.fail=fail;self.calls=0
 @property
 def closed(self):return self.obj.closed
 def fileno(self):return self.obj.fileno()
 def close(self):
  self.calls+=1
  if self.fail:self.fail=False;raise OSError('injected original-close-before-close')
  if not self.obj.closed:
   fd=self.obj.fileno();self.obj.close();self.ledger.closed(fd,'FileIO-original')
class Sink:
 def __init__(self,path,ledger):self.obj=path.open('xb',buffering=0);self.fd=ledger.add(self.obj.fileno(),'sink');self.ledger=ledger
 @property
 def closed(self):return self.obj.closed
 def fileno(self):return self.obj.fileno()
 def write(self,b):return self.obj.write(b)
 def close(self):
  if not self.obj.closed:self.obj.close();self.ledger.closed(self.fd,'sink')
class Selector:
 def __init__(self,ledger,entered=None,release=None):
  self.obj=selectors.DefaultSelector();self.ledger=ledger;self.fd=ledger.add(self.obj.fileno(),'selector');self.entered=entered;self.release=release
 def register(self,*a):return self.obj.register(*a)
 def unregister(self,*a):return self.obj.unregister(*a)
 def get_map(self):return self.obj.get_map()
 def select(self,t):
  if self.release is not None:
   self.entered.set();need(self.release.wait(1),'finite controlled selector release')
  return self.obj.select(t)
 def close(self):self.obj.close();self.ledger.closed(self.fd,'selector')
def remaining(deadline):return max(0,deadline-time.monotonic())
def transfer_case(mode,deadline,folder):
 ledger=Ledger();streams={};writes={};pendingReads={};reuse=set();cap=None;release=threading.Event();entered=threading.Event();activeSnapshot=None;error=None
 try:
  for name in ['stdout','stderr']:
   r,w=ledger.pipe();writes[name]=w;pendingReads[name]=r
   streams[name]=Stream(r,ledger,fail=mode=='original-close'and name=='stdout');pendingReads.pop(name)
  if mode.startswith('grant'):
   for fd in list(writes.values()):ledger.close(fd)
   writes.clear()
  def duplicate(fd):
   if mode=='second-dup'and fd==streams['stderr'].fileno():raise OSError('injected seconddup')
   return ledger.duplicate(fd)
  def construct(reads):
   nonlocal cap
   if mode=='construct':raise ValueError('injected constructor')
   cap=Capture(reads,{n:folder/(n+'.raw')for n in reads},deadline,deadline,
    close=ledger.close,sink_factory=lambda p:Sink(p,ledger),
    selector_factory=lambda:Selector(ledger,entered if mode=='grant-no-ack'else None,release if mode=='grant-no-ack'else None))
   if mode.startswith('grant'):
    old=cap.grant
    def grant():
     old()
     if mode=='grant-no-ack':need(entered.wait(min(1,remaining(deadline))),'worker reached controlled select')
     raise KeyboardInterrupt('injected after grant')
    cap.grant=grant
   if mode=='grant-no-ack':cap.join_once=lambda maximum:False
   return cap
  def start(c):
   if mode=='start-before':raise KeyboardInterrupt('before actual thread start')
   c.start()
   if mode=='ambiguous-start':raise KeyboardInterrupt('after actual start before grant')
  try:
   result=transfer_popen_reads(streams,duplicate,ledger.close,construct,start,deadline,time.monotonic)
   need(mode=='delayed-eof','unexpected transfer success')
   need(result.ready.wait(min(1,remaining(deadline))),'ready capture')
   activeSnapshot=result.snapshot();need(activeSnapshot['hashes']is None and not activeSnapshot['stoppedWriter'],'active writer cannot hash')
   # Closed original FileIO close must not affect a newly owned reused FD.
   rr,rw=ledger.pipe();reuse.update([rr,rw])
   for s in streams.values():s.close();need(s.closed,'original wrapper stays closed')
   need(os.write(rw,b'Z')==1 and os.read(rr,1)==b'Z','later original close preserves new FD owner')
   ledger.close(rr);reuse.remove(rr);ledger.close(rw);reuse.remove(rw)
   need(os.write(writes['stdout'],b'answer\n')==7,'bounded delayed output')
   for fd in list(writes.values()):ledger.close(fd)
   writes.clear();need(result.join_once(remaining(deadline)),'capture stop ack')
   result.thread.join(remaining(deadline));need(not result.thread.is_alive(),'positive capture thread actually dead')
   snap=result.snapshot();need(snap['completeRaw']and snap['hashes']['stdout']['bytes']==7,'delayed EOF complete')
  except TransferFailure as ex:
   error={'cause':repr(ex.__cause__),'ownership':ex.readOwnership,'cleanup':ex.cleanup}
   need(mode!='delayed-eof','unexpected transfer refusal')
   if mode.startswith('grant'):
    need(ex.readOwnership=='worker-granted','grant cannot return reads to parent')
    if mode=='grant-no-ack':
     activeSnapshot=ex.capture.snapshot();need(activeSnapshot['hashes']is None and not activeSnapshot['stoppedWriter'],'no active-writer hash on unavailable stopack')
     need('worker-stop-ack-unavailable'in ex.cleanup,'stopack failure retained');release.set()
    else:need('worker-stop-ack-unavailable'not in ex.cleanup,'acknowledged grant failure')
   else:need(ex.readOwnership=='parent-denied','pregrant ownership permanently denied')
   for fd in list(writes.values()):ledger.close(fd)
   writes.clear()
   if cap is not None and cap.thread is not None:
    cap.thread.join(remaining(deadline));need(not cap.thread.is_alive(),'fixture thread fully stopped')
   snap=cap.snapshot()if cap is not None else None
   if mode.startswith('grant'):need(snap['stoppedWriter'],'only worker closes transferred reads')
  need(all(s.closed for s in streams.values()),'original FileIO objects closed')
  need(not ledger.live,'all owned FDs closed')
  return {'case':mode,'status':'PASS_FIXED_FILEIO_TRANSFER_ONLY','ledger':ledger.events,'peakOwnedFDs':ledger.peak,'error':error,'activeSnapshot':activeSnapshot,'capture':snap,'actualPopen':False,'actualNative':False,'childClosureQualified':False}
 finally:
  originalException=repr(sys.exc_info()[1])if sys.exc_info()[0]is not None else None;cleanupErrors=[]
  release.set()
  if cap is not None and cap.thread is not None and cap.thread.is_alive():
   cap.refuse('fixture-finally');cap.thread.join(remaining(deadline))
  # Never close worker-granted reads externally, even after join uncertainty.
  for s in streams.values():
   if not s.closed:
    try:s.close()
    except BaseException as ex:cleanupErrors.append('original-close:'+repr(ex))
  for fd in list(writes.values())+list(pendingReads.values())+list(reuse):
   try:ledger.close(fd)
   except BaseException as ex:cleanupErrors.append('parent-close:'+repr(ex))
  if originalException is not None or cleanupErrors or ledger.live or(cap is not None and cap.thread is not None and cap.thread.is_alive()):
   durable(folder/'partial-failure.json',{'originalException':originalException,'cleanupErrors':cleanupErrors,'FDLedger':ledger.events,'unclosedOwnedFDs':sorted(ledger.live),'captureThreadAlive':cap is not None and cap.thread is not None and cap.thread.is_alive(),'hashes':None,'qualified':False})
def authority_case(mode,deadline):
 ctl=Controller(time.monotonic,deadline);inside=threading.Event();release=threading.Event();retired=threading.Event();events=[];failures=[]
 def group_callback():inside.set();need(release.wait(min(1,remaining(deadline))),'release owned callback');events.append('group-callback-return')
 def query():
  try:ctl.group(group_callback)
  except BaseException as ex:failures.append(repr(ex))
 def retire():
  try:ctl.retire('fixture-serialized');events.append('retired');retired.set()
  except BaseException as ex:failures.append(repr(ex))
 a=threading.Thread(target=query,name='fixture-injected-group');b=threading.Thread(target=retire,name='fixture-retire')
 try:
  a.start();need(inside.wait(min(1,remaining(deadline))),'injected callback entered');b.start()
  need(not retired.is_set(),'retire cannot complete while group callback holds lock')
  release.set();a.join(remaining(deadline));b.join(remaining(deadline))
  need(not a.is_alive()and not b.is_alive()and not failures,'both authority threads stopped')
  need(events==['group-callback-return','retired'],'serialized retirement ordering')
  def wait(t):
   need(not ctl.active and ctl.waitEntered,'authority retired before injected wait');events.append('injected-wait')
   if mode=='uncertain-wait':raise KeyboardInterrupt('injected released-before-returncode wait uncertainty')
   return 0
  try:rc=ctl.wait(wait);need(mode=='retire-before-wait'and rc==0,'normal injected wait')
  except KeyboardInterrupt:need(mode=='uncertain-wait'and ctl.waitUncertain,'uncertain wait permanently retained')
  for callback in [lambda:ctl.group(lambda:events.append('ILLEGAL')),lambda:ctl.wait(wait)]:
   try:callback()
   except AssertionError:pass
   else:raise AssertionError('retired group/second wait accepted')
  return {'case':mode,'status':'PASS_REAL_LOCK_INJECTED_PROCESS_CALLBACK_ONLY','events':events,'controllerEvents':ctl.events,'waitUncertain':ctl.waitUncertain,'actualProcessAPIs':0,'actualOSWait':False}
 finally:
  release.set()
  for t in [a,b]:
   if t.ident is not None:t.join(remaining(deadline))
def atomic_exception_case(deadline):
 ctl=Controller(time.monotonic,deadline);done=threading.Event();events=[];failures=[]
 def fault():events.append('injected-callback-fault');raise RuntimeError('fixed callback exception')
 def first():
  try:
   try:ctl.group(fault)
   except RuntimeError:need(not ctl.active,'exception atomically retires before caller resumes');events.append('caller-observed-retired')
   else:raise AssertionError('callback fault missing')
  except BaseException as ex:failures.append(repr(ex))
  finally:done.set()
 def second():
  try:
   need(done.wait(min(1,remaining(deadline))),'first callback completed')
   try:ctl.group(lambda:events.append('ILLEGAL-reentry'))
   except AssertionError:events.append('reentry-refused')
   else:raise AssertionError('exception retirement window')
  except BaseException as ex:failures.append(repr(ex))
 a=threading.Thread(target=first,name='fixture-callback-fault');b=threading.Thread(target=second,name='fixture-after-fault')
 try:
  a.start();b.start();a.join(remaining(deadline));b.join(remaining(deadline))
  need(not a.is_alive()and not b.is_alive()and not failures,'atomic-case threads stopped')
  need(events==['injected-callback-fault','caller-observed-retired','reentry-refused'],'atomic exception refusal observed')
  return {'case':'atomic-callback-exception','status':'PASS_REAL_LOCK_ATOMIC_INJECTED_EXCEPTION_ONLY','events':events,'controllerEvents':ctl.events,'actualProcessAPIs':0}
 finally:
  for t in [a,b]:
   if t.ident is not None:t.join(remaining(deadline))
def main():
 start=time.monotonic();deadline=start+9
 sourcePins=D/'source-pins.json';expected=json.loads(sourcePins.read_text());go=json.loads(GO.read_text())
 need(len(sys.argv)==1,'fixed fixture argv')
 need(set(go)=={'status','sourcePinsSha256','outputRoot'},'exact GO keys')
 need(go=={'status':'GO_FIXED_FILEIO_THREAD_FIXTURE_ONCE','sourcePinsSha256':sha(sourcePins),'outputRoot':str(OUT)},'exact reviewed GO')
 for name,v in expected.items():need((D/name).stat().st_size==v['bytes']and sha(D/name)==v['sha256'],'frozen SOURCE identity')
 for name,v in json.loads((D/'input-pins.json').read_text()).items():
  p=pathlib.Path(name);need(p.stat().st_size==v['bytes']and sha(p)==v['sha256'],'frozen input identity')
 pr=json.loads((D/'preregistration.json').read_text());need(str(pathlib.Path(sys.executable).resolve())==pr['interpreter']['path'],'fixed interpreter');need(sha(pathlib.Path(pr['interpreter']['path']))==pr['interpreter']['sha256'],'interpreter bytes')
 supplied=pr['fixedSuppliedEnvironment'];need(all(os.environ.get(k)==v for k,v in supplied.items()),'exact supplied env values');need(set(os.environ)-set(supplied)<={'__CF_USER_TEXT_ENCODING'},'only known runtime metadata extra')
 need(not OUT.exists(),'fresh single attempt root');OUT.mkdir()
 durable(OUT/'attempt.json',{'status':'OPEN_FIXED_FIXTURE_NO_RETRY','startedMonotonic':start,'sourcePinsSha256':sha(sourcePins)})
 results=[]
 try:
  for index,mode in enumerate(pr['cases'],1):
   need(time.monotonic()<deadline,'original fixture9s absolute deadline');folder=OUT/str(index);folder.mkdir()
   q=atomic_exception_case(deadline)if mode=='atomic-callback-exception'else authority_case(mode,deadline)if mode in ['retire-before-wait','uncertain-wait']else transfer_case(mode,deadline,folder)
   q['componentSourcePins']={name:expected[name]['sha256']for name in ['capture.py','integration.py','controller.py']}
   durable(folder/'receipt.json',q);results.append({'index':index,'case':mode,'status':q['status']})
  need(time.monotonic()<deadline,'fixture absolute deadline')
  raws=list(OUT.glob('*/*.raw'));need(len(raws)<=6 and sum(p.stat().st_size for p in raws)==7,'fixed complete raw file/byte budget')
  durable(OUT/'completion.json',{'status':'PASS_FIXED_FILEIO_TRANSFER_AND_INJECTED_AUTHORITY_ONLY','cases':results,'componentSourcePins':{name:expected[name]['sha256']for name in ['capture.py','integration.py','controller.py']},'nativeCalls':0,'PopenCalls':0,'processKernelAPICalls':0,'noActiveWriterHashes':True,'nativeControllerQualified':False,'cooperativeIOWallBoundOnly':True})
  return 0
 except BaseException as ex:
  durable(OUT/'completion.json',{'status':'FIRST_FAILURE_NO_RETRY','exception':repr(ex),'completedCases':results,'nativeControllerQualified':False});return 78
if __name__=='__main__':raise SystemExit(main())
