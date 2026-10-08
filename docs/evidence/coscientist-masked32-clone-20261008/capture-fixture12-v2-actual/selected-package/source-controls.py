"""Injected synchronous worker tests only; no real thread, FD, fsync or pipe calls."""
from pathlib import Path
from types import SimpleNamespace
import ast,json
from capture import Capture
D=Path(__file__).resolve().parent
class Clock:
 def __init__(self):self.t=0
 def __call__(self):return self.t
class Sink:
 def __init__(self):self.b=bytearray();self.closed=False
 def write(self,b):self.b.extend(b[:3]);return min(3,len(b))
 def fileno(self):return 0
 def close(self):self.closed=True
class Selector:
 def __init__(self,clock):self.map={};self.clock=clock
 def register(self,fd,kind,name):self.map[fd]=SimpleNamespace(fd=fd,data=name)
 def unregister(self,fd):del self.map[fd]
 def get_map(self):return self.map
 def select(self,timeout):self.clock.t+=timeout;return [(v,1)for v in self.map.values()]
 def close(self):pass
def test(fault=False,openpipe=False):
 clock=Clock();sinks={};closed=[];data={1:[b'answer',b''],2:[b'counter',b'']}
 def sink(p):s=Sink();sinks[str(p)]=s;return s
 def read(fd,n):
  if openpipe:raise BlockingIOError()
  return data[fd].pop(0)
 def fsync(fd):
  if fault:raise OSError('injected')
 cap=Capture({'stdout':1,'stderr':2},{'stdout':'s','stderr':'e'},3,3,clock=clock,selector_factory=lambda:Selector(clock),read=read,close=closed.append,sink_factory=sink,fsync=fsync,set_blocking=lambda fd,v:None)
 cap.refuse('sample-identity-uncertainty');first=cap.deadline;clock.t=.1;cap.refuse('later-failure');assert cap.deadline==first
 cap.grant();cap.run();assert cap.stopped.is_set()and cap.writerClosed and sorted(closed)==[1,2]
 if openpipe:assert not any(cap.eof.values())and clock.t<=1.01
 else:assert cap.retained=={'stdout':6,'stderr':7}and all(cap.eof.values())
 if fault:assert cap.errors
 assert cap.firstFailure=='sample-identity-uncertainty'
for p in D.glob('*.py'):ast.parse(p.read_text())
from transaction import setup,SetupFailure
def setup_test(case):
 ids=iter([1,2,3,4]);allocated=[];closed=[];calls=[0];delayed=[];capbox=[]
 def pipe():
  calls[0]+=1
  if case=='second-pipe'and calls[0]==2:raise OSError('injected')
  pair=(next(ids),next(ids));allocated.extend(pair);return pair
 def construct(reads):
  if case=='constructor':raise ValueError('injected')
  c=Capture(reads,{'stdout':'untouched-s','stderr':'untouched-e'},1,1,selector_factory=lambda:(_ for _ in ()).throw(AssertionError('denied worker touched selector')))
  capbox.append(c);return c
 def start(c):
  if case=='ambiguous-start':delayed.append(c.run)
  raise KeyboardInterrupt('ambiguous start failure')
 try:setup(pipe,closed.append,construct,start)
 except SetupFailure as ex:assert ex.readOwnership=='parent-denied'and sorted(closed)==sorted(allocated)and not ex.cleanupErrors
 else:raise AssertionError('setup failure accepted')
 for later in delayed:later()
 for c in capbox:
  assert c.ownership=='parent-denied'and c.snapshot()['hashes']is None
  try:c.grant()
  except AssertionError:pass
  else:raise AssertionError('denial reversed')
for case in ['second-pipe','constructor','start-before','ambiguous-start']:setup_test(case)
test();test(fault=True);test(openpipe=True)
# Metadata-only snapshot while no stopped writer; does not inspect output paths.
cap=Capture({'stdout':1,'stderr':2},{'stdout':'never-read','stderr':'never-read2'},1,1)
assert cap.snapshot()['hashes']is None
q={'status':'PASS_PURE_INJECTED_WORKER_SOURCE_ONLY','synchronousInjectedRuns':3,'nativeCalls':0,'realThreadsStarted':0,'realPipeCalls':0,'processAPICalls':0,'fixtureExecuted':False,'runtimeQualification':False}
q['transactionalSetupNegativeControls']=4;q['denialIrreversible']=True;q['deniedLateWorkerNoFDTouch']=True
ns={'__name__':'separate_pure_ownership_model'};exec(compile((D/'ownership-model.py').read_bytes(),'ownership-model.py','exec'),ns)
q['separateOwnershipModel']=ns['controls']()
(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n')
