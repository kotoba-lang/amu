"""Import-inert bounded FD-owner diagnostic. No process/group APIs."""
import os,time,threading,selectors,hashlib
from pathlib import Path
CAPS={'stdout':8388608,'stderr':1048576}
class Capture:
 def __init__(self,readfds,paths,outer_deadline,cleanup_deadline,clock=time.monotonic,selector_factory=selectors.DefaultSelector,read=os.read,close=os.close,sink_factory=None,fsync=os.fsync,set_blocking=os.set_blocking):
  assert set(readfds)==set(paths)==set(CAPS)
  self.fds=dict(readfds);self.paths={k:Path(v)for k,v in paths.items()};self.clock=clock;self.absolute=min(outer_deadline,cleanup_deadline);self.deadline=self.absolute
  self.selector_factory=selector_factory;self.read=read;self.close=close;self.sink_factory=sink_factory or(lambda p:p.open('xb',buffering=0));self.fsync=fsync;self.set_blocking=set_blocking
  self.lock=threading.Lock();self.ready=threading.Event();self.stopped=threading.Event();self.thread=None;self.firstFailure=None;self.errors=[];self.retained={k:0 for k in CAPS};self.dropped={k:0 for k in CAPS};self.eof={k:False for k in CAPS};self.writerClosed=False
  self.readCalls=0;self.observedBytes=0
 def refuse(self,reason):
  with self.lock:
   if self.firstFailure is None:
    self.firstFailure=reason;self.deadline=min(self.absolute,self.clock()+1)
 def remaining(self):
  with self.lock:return max(0,self.deadline-self.clock())
 def start(self):
  assert self.thread is None
  self.thread=threading.Thread(target=self.run,name='bounded-capture-owner',daemon=False);self.thread.start()
 def run(self):
  sinks={};selector=None;owned=dict(self.fds)
  try:
   selector=self.selector_factory()
   for name,fd in owned.items():
    sinks[name]=self.sink_factory(self.paths[name]);self.set_blocking(fd,False);selector.register(fd,selectors.EVENT_READ,name)
   self.ready.set()
   while selector.get_map() and self.remaining()>0:
    # Sorted round: each ready stream gets at most64KiB per round.
    events=selector.select(min(.01,self.remaining()))
    for key,_ in sorted(events,key=lambda z:z[0].data):
     if self.remaining()<=0:break
     if self.readCalls>=4096 or self.observedBytes>=16777216:self.refuse('capture-read-budget');raise AssertionError('finite read budget')
     name=key.data
     self.readCalls+=1
     try:b=self.read(key.fd,min(65536,16777216-self.observedBytes))
     except BlockingIOError:continue
     self.observedBytes+=len(b)
     if not b:
      self.eof[name]=True;selector.unregister(key.fd);self.close(key.fd);owned.pop(name);continue
     room=CAPS[name]-self.retained[name];keep=b[:room];self.dropped[name]+=len(b)-len(keep)
     view=memoryview(keep)
     while view:
      assert self.remaining()>0,'absolute capture deadline during short writes'
      n=sinks[name].write(view);assert type(n)is int and 0<n<=len(view),'short/zero write';self.retained[name]+=n;view=view[n:]
     if len(keep)<len(b):self.refuse('raw-overflow')
   if selector.get_map():self.refuse('capture-deadline')
  except BaseException as ex:self.errors.append(repr(ex));self.refuse('capture-io-failure')
  finally:
   self.ready.set()
   for fd in list(owned.values()):
    try:self.close(fd)
    except BaseException as ex:self.errors.append('close-read:'+repr(ex))
   if selector is not None:
    try:selector.close()
    except BaseException as ex:self.errors.append('selector-close:'+repr(ex))
   for sink in sinks.values():
    try:self.fsync(sink.fileno())
    except BaseException as ex:self.errors.append('fsync:'+repr(ex));self.refuse('capture-io-failure')
    finally:
     try:sink.close()
     except BaseException as ex:self.errors.append('close-sink:'+repr(ex))
   self.writerClosed=all(s.closed for s in sinks.values());self.stopped.set()
 def join_once(self,maximum):
  assert self.thread is not None
  self.thread.join(timeout=min(maximum,max(0,self.absolute-self.clock())))
  if not self.stopped.is_set():self.refuse('capture-join-timeout');return False
  return True
 def snapshot(self):
  # Never touch files while capture can still write. A join timeout is metadata only.
  stopped=self.stopped.is_set() and self.writerClosed
  hashes=None
  if stopped:
   hashes={}
   for name,p in self.paths.items():
    if p.exists():
     assert not p.is_symlink() and p.stat().st_size<=CAPS[name]
     b=p.read_bytes();hashes[name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
  return {'stoppedWriter':stopped,'hashes':hashes,'firstFailure':self.firstFailure,'errors':list(self.errors),'retained':dict(self.retained),'dropped':dict(self.dropped),'readCalls':self.readCalls,'observedBytes':self.observedBytes,'EOF':dict(self.eof),'cooperativeWallBoundOnly':True,'completeRaw':stopped and all(self.eof.values()) and not any(self.dropped.values()) and not self.errors,'memoryAdmissionQualified':False,'semanticDecodeAuthorized':stopped and all(self.eof.values()) and not any(self.dropped.values()) and not self.errors}
