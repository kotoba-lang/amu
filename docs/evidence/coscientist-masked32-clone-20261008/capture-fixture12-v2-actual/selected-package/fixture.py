"""Inert real pipe/thread fixture; main only via reviewed run.py. Never spawns processes."""
from pathlib import Path
import os,time,threading
from capture import Capture,CAPS
from transaction import setup,SetupFailure
class ShortSink:
 def __init__(self,p):self.f=p.open('xb',buffering=0)
 def write(self,b):return self.f.write(b[:3])
 def fileno(self):return self.f.fileno()
 def close(self):self.f.close()
 @property
 def closed(self):return self.f.closed
def run_fixture(root):
 root=Path(root);assert not root.exists();root.mkdir();results=[]
 for index,case in enumerate(['delayed-after-refusal','asymmetric-EOF','open-expiry','stderr-cap-plus-one','stdout-cap-plus-one','short-write','fsync-fault','join-timeout']):
  p=root/case;p.mkdir();start=time.monotonic();deadline=start+3;gate=threading.Event();blocked=threading.Event()
  def fsync_fault(fd):raise OSError('injected fsync fault')
  def delayed_read(fd,size):
   if case=='join-timeout':blocked.set();assert gate.wait(.5),'bounded injected delay'
   return os.read(fd,size)
  cap,writes=setup(os.pipe,os.close,lambda reads:Capture(reads,{k:p/(k+'.raw')for k in CAPS},deadline,deadline,read=delayed_read,sink_factory=ShortSink if case=='short-write'else None,**({'fsync':fsync_fault}if case=='fsync-fault'else {})),lambda c:c.start());joins=0
  try:
   assert cap.ready.wait(.5)
   if case in ['delayed-after-refusal','open-expiry']:cap.refuse('injected-sampler-identity-uncertainty')
   if case in ['stderr-cap-plus-one','stdout-cap-plus-one']:
    # Nonblocking bounded pumping; no unbounded pipe write/backpressure wait.
    stream='stderr'if case.startswith('stderr')else'stdout';fd=writes[stream];os.set_blocking(fd,False);pending=CAPS[stream]+1
    while pending and time.monotonic()<deadline:
     try:n=os.write(fd,b'x'*min(65536,pending));pending-=n
     except BlockingIOError:time.sleep(.001)
    assert pending==0
   else:os.write(writes['stdout'],b'answer');os.write(writes['stderr'],b'counter')
   if case=='asymmetric-EOF':
    os.close(writes.pop('stderr'))
    while not cap.eof['stderr'] and time.monotonic()<start+.5:time.sleep(.001)
    assert cap.eof['stderr'] and not cap.eof['stdout']
   if case!='open-expiry':
    for fd in writes.values():os.close(fd)
    writes.clear()
   if case=='join-timeout':
    assert blocked.wait(.25),'acknowledged blocked-read before join'
    joins+=1;assert not cap.join_once(.001);assert cap.snapshot()['hashes']is None
    gate.set()
    # One cleanup join allowed, same absolute/first-failure deadline; no acceptance repair.
   joins+=1;assert cap.join_once(2),'writer stop acknowledgement required'
   q=cap.snapshot();assert q['stoppedWriter'] and q['memoryAdmissionQualified'] is False
   if case=='delayed-after-refusal':assert q['retained']['stdout']==6 and q['completeRaw'] and q['firstFailure']is not None
   if case=='asymmetric-EOF':assert all(q['EOF'].values()) and q['completeRaw']
   if case=='open-expiry':assert not all(q['EOF'].values()) and q['firstFailure']is not None
   if case in ['stderr-cap-plus-one','stdout-cap-plus-one']:assert q['retained'][stream]==CAPS[stream] and q['dropped'][stream]==1 and not q['semanticDecodeAuthorized']
   if case=='short-write':assert q['retained']['stdout']==6 and q['completeRaw']
   if case=='fsync-fault':assert q['errors'] and not q['semanticDecodeAuthorized']
   if case=='join-timeout':assert q['firstFailure']=='capture-join-timeout'
   results.append({'case':case,'capture':q,'refusalBeforeWrites':case=='delayed-after-refusal','joinAttempts':joins})
  finally:
   for fd in writes.values():os.close(fd)
   # Parent never closes capture-owned read FDs, even after join timeout.
   gate.set()
   if not cap.stopped.is_set() and joins<2:
    cap.refuse('fixture-cleanup');joins+=1;cap.join_once(max(0,deadline-time.monotonic()))
   assert cap.stopped.is_set(),'no stopped-writer acknowledgement; hashes unavailable'
 setup_results=[]
 for case in ['second-pipe','constructor','start-before','ambiguous-start']:
  p=root/case;p.mkdir();deadline=time.monotonic()+3;allocated=[];closed=[];calls=[0]
  def pipe():
   calls[0]+=1
   if case=='second-pipe'and calls[0]==2:raise OSError('injected second pipe')
   pair=os.pipe();allocated.extend(pair);return pair
  def close(fd):os.close(fd);closed.append(fd)
  def construct(reads):
   if case=='constructor':raise ValueError('injected constructor')
   return Capture(reads,{k:p/(k+'.raw')for k in CAPS},deadline,deadline)
  def start_fault(c):
   if case=='start-before':raise KeyboardInterrupt('injected before start')
   c.start();raise KeyboardInterrupt('injected after actual start')
  try:setup(pipe,close,construct,start_fault)
  except SetupFailure as ex:
   assert ex.readOwnership=='parent-denied'and sorted(allocated)==sorted(closed)and not ex.cleanupErrors
   if case=='ambiguous-start':
    assert ex.capture.stopped.wait(.5)and ex.capture.join_once(.5)
    assert ex.capture.snapshot()['hashes']is None and not any(p.iterdir())
   setup_results.append({'case':case,'readOwnership':ex.readOwnership,'allocatedFDs':len(allocated),'closedFDs':len(closed),'hashes':None,'lateDeniedWorkerTouchesFDs':False})
  else:raise AssertionError('setup negative unexpectedly admitted')
 return {'status':'COMPLETE_REAL_PIPE_THREADED_DIAGNOSTIC_FIXTURE_ONLY','cases':results,'setupCases':setup_results,'nativeCalls':0,'processStarts':0,'groupAPICalls':0,'memoryAdmissionQualified':False}
