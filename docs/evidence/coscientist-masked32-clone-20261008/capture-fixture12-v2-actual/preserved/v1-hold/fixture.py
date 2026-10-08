"""Inert real pipe/thread fixture; main only via reviewed run.py. Never spawns processes."""
from pathlib import Path
import os,time,threading
from capture import Capture,CAPS
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
  p=root/case;p.mkdir();reads={};writes={}
  for name in CAPS:reads[name],writes[name]=os.pipe()
  start=time.monotonic();deadline=start+3;gate=threading.Event()
  def fsync_fault(fd):raise OSError('injected fsync fault')
  def delayed_read(fd,size):
   if case=='join-timeout':assert gate.wait(.2),'bounded injected delay'
   return os.read(fd,size)
  cap=Capture(reads,{k:p/(k+'.raw')for k in CAPS},deadline,deadline,read=delayed_read,sink_factory=ShortSink if case=='short-write'else None,**({'fsync':fsync_fault}if case=='fsync-fault'else {}))
  cap.start();joins=0
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
 return {'status':'COMPLETE_REAL_PIPE_THREADED_DIAGNOSTIC_FIXTURE_ONLY','cases':results,'nativeCalls':0,'processStarts':0,'groupAPICalls':0,'memoryAdmissionQualified':False}
