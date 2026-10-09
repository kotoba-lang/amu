"""Injected bounded fixtures only: zero pipes/threads/process/group/socket/setter calls."""
from pathlib import Path
import json,copy,ast,hashlib
import ownership as own
# Injection prevents even Event/Thread construction in pure protocol tests.
class PureEvent:
 def __init__(self):self.flag=False
 def set(self):self.flag=True
 def is_set(self):return self.flag
own.threading.Event=PureEvent
D=Path(__file__).resolve().parent
clock=[0.0];own.time.monotonic=lambda:clock[0];own.time.clock_gettime_ns=lambda _:int(clock[0]*10**9)
GO=bytes.fromhex('a'*64);NONCE=bytes.fromhex('b'*64)
F=lambda stage,seq,pid,birth,status=0:own.encode(stage,seq,100,pid,birth,100,status,GO,NONCE)
class Stream:
 def __init__(self,raw,partial=17):self.raw=raw;self.sent=bytearray();self.partial=partial;self.events=[];self.closed=False;self.interrupt=False
 def recv(self,n):
  if self.interrupt:self.interrupt=False;raise InterruptedError()
  q=self.raw[:min(n,self.partial)];self.raw=self.raw[len(q):];return q
 def send(self,b):
  if self.interrupt:self.interrupt=False;raise InterruptedError()
  n=min(len(b),self.partial);self.sent.extend(b[:n]);self.events.append(('send',len(self.sent)));return n
 def close(self):self.closed=True
class Ctl:
 def __init__(self,stream):self.active=True;self.events=[];self.stream=stream
 def group(self,fn):
  if not self.active:raise own.RetiredAuthority()
  self.events.append('group');return fn()
 def retire(self,why):self.active=False;self.events.append(why);self.stream.events.append(('retire',len(self.stream.sent)))
class Sampler:
 def __init__(self,mut=None):self.n=0;self.mut=mut
 def sample(self):
  self.n+=1;members=[dict(pid=100,start=11,exit=0,physicalFootprintBytes=8,uuid='0'*32)]
  if self.n==2:members.append(dict(pid=101,start=12,exit=0,physicalFootprintBytes=16,uuid='1'*32))
  if self.mut:self.mut(members)
  return dict(sample=self.n,ownedPGID=100,metric='sum-ri_phys_footprint',aggregateBytes=sum(q['physicalFootprintBytes']for q in members),thresholdBytes=4294967296,members=members,hardMemoryCapEstablished=False)
def instance(raw=None,mut=None,persist=None):
 s=Stream(raw if raw is not None else F(2,1,0,11)+F(4,2,101,12)+F(6,3,101,12)+F(8,4,101,12));rows=[];ctl=Ctl(s)
 p=own.HeldProtocol(s,100,30,GO.hex(),NONCE.hex(),persist or(lambda q:rows.append(q)or True));p.io.ready=lambda *_:True;p.io.clock=lambda:clock[0];return p,ctl,Sampler(mut),rows,s
positive=[];negative=[]
def refuses(name,fn):
 clock[0]=0
 try:fn()
 except (own.Refusal,own.RetiredAuthority,AssertionError,KeyError,ValueError,InterruptedError):negative.append(name)
 else:raise AssertionError('accepted '+name)
for partial in [1,17,128]:
 p,c,s,rows,stream=instance();stream.partial=partial;stream.interrupt=True;initial=p.handshake(c,s,lambda q:True);state={};p.receive_wait(c,state);assert p.waitError is None and p.waitReceipt=={'pid':101,'birth':12,'exit':0,'durable':True}and state=={'exitHeld':True}and len(initial)==2 and len(rows)==4 and p.io.records==8
 frames=[own.decode(bytes(stream.sent[i:i+128]))for i in range(0,len(stream.sent),128)];assert [q[1]for q in frames]==[1,3,5,7];r=next(x for x in stream.events if x[0]=='retire');assert r[1]==384 and not c.active;positive.append('partial-IO-'+str(partial)+'-EINTR-retire-before-reapACK')
for name,raw in [('EOF',b''),('partial-EOF',F(2,1,0,11)[:-1]),('wrong-stage',F(4,1,0,11)),('wrong-owner',own.encode(2,1,999,0,11,999,0,GO,NONCE)),('wrong-GO',own.encode(2,1,100,0,11,100,0,bytes(32),NONCE)),('duplicate-stage',F(2,1,0,11)+F(2,1,0,11)),('wrong-child-birth',F(2,1,0,11)+F(4,2,101,13))]:
 def run(raw=raw):
  p,c,s,_,_=instance(raw);p.handshake(c,s,lambda q:True)
 refuses(name,run)
for name,mut in [('foreignPID',lambda m:m.append(dict(pid=999,start=99,exit=0,physicalFootprintBytes=0,uuid='2'*32))),('reused-birth',lambda m:m[0].update(start=99)),('exited-held-member',lambda m:m[0].update(exit=1))]:
 def run(mut=mut):
  p,c,s,_,_=instance(mut=mut);p.handshake(c,s,lambda q:True)
 refuses(name,run)
def notdurable():
 p,c,s,_,stream=instance(persist=lambda q:False)
 try:p.handshake(c,s,lambda q:True)
 finally:assert len(stream.sent)==128 # ticket only; no ACK.
refuses('fsync-refusal-noACK',notdurable)
def interruptedgrant():
 def broken(q):raise KeyboardInterrupt()
 p,c,s,_,stream=instance(persist=broken)
 try:p.handshake(c,s,lambda q:True)
 except KeyboardInterrupt:assert len(stream.sent)==128;raise InterruptedError()
refuses('interrupt-beforeACK',interruptedgrant)
def late():
 p,c,s,_,_=instance();p.io.ready=lambda *_:clock.__setitem__(0,31)or True;p.handshake(c,s,lambda q:True)
refuses('lateACK-originaldeadline',late)
def operations():
 p,c,s,_,_=instance();p.io.operations=4096;p.handshake(c,s,lambda q:True)
refuses('partialIO-operation-cap',operations)
for name,tail in [('wrong-childwait',F(8,4,101,13)),('nonzero-childwait',F(8,4,101,12,256)),('reapACK-duplicate',F(7,3,101,12))]:
 p,c,s,_,stream=instance(F(2,1,0,11)+F(4,2,101,12)+F(6,3,101,12)+tail);p.handshake(c,s,lambda q:True);p.receive_wait(c,{});assert p.waitError is not None and p.waitReceipt is None and not c.active;negative.append(name)
# Fresh API provenance: not accepting caller-supplied PID/errno alone.
context=dict(contextVersion='owned-group-sampling-failure-context-v1',typedOrigin='fresh-owned-group-api-v1',invocation='ticket',stage='member-getpgid',pid=101,queryOrdinal=21,errno=3,failureClass='kernel-oserror')
class API:queryOrdinal=21;lastAttempt={k:context[k]for k in ['contextVersion','typedOrigin','invocation','stage','pid','queryOrdinal']}
assert own.validate_failure(context,API,{100:11,101:12},100,'ticket');positive.append('current-known-ESRCH')
for name,k,v in [('leader-stage-child','stage','leader-getpgid'),('unknownPID','pid',999),('old-invocation','invocation','old'),('untyped','typedOrigin','caller'),('wrong-ordinal','queryOrdinal',20),('wrong-errno','errno',1)]:
 q=copy.deepcopy(context);q[k]=v
 class A:queryOrdinal=21;lastAttempt={k:q[k]for k in API.lastAttempt}
 refuses(name,lambda q=q,A=A:own.validate_failure(q,A,{100:11,101:12},100,'ticket'))
q=copy.deepcopy(context);q.update(stage='member-rusage',errno=0,failureClass='kernel-observed-exited',observedBirth=12,observedExit=100)
class A:queryOrdinal=21;lastAttempt={k:q[k]for k in API.lastAttempt}
assert own.validate_failure(q,A,{100:11,101:12},100,'ticket');positive.append('observed-known-exited-birth')
q['observedBirth']=13;refuses('exited-reused-birth',lambda:own.validate_failure(q,A,{100:11,101:12},100,'ticket'))
# SOURCE structural closure: no stub bodies; fixed C conditional patch and FD barriers.
s=(D/'kexe_loader_diagnostic.c').read_text();hooks=(D/'owner-hooks.c').read_text();assert s.count(hooks)==1 and 'WEXITED|WNOWAIT'in hooks and hooks.index('oh_hold(4,child')<hooks.index('oh_io(oh_gate[1]') and 'close(4)'in hooks and 'if(oh_close_gate())return -1;'in hooks and 'oh_arm_deadline(1)'in s
assert s.index('oh_exit_held(child)')<s.index('pid_t result=waitpid(child,&status,0)',s.index('static int supervise'))
assert s.index('supervised_pid = -1;',s.index('oh_exit_held(child)'))<s.index('pid_t result=waitpid(child,&status,0)')
assert 'KEXE_OWNERSHIP_DIAGNOSTIC_V3'in s and 'oh_ticket.w[7]<=oh_now()'in hooks and 'oh_deadline=oh_ticket.w[7]'in hooks
for p in D.glob('*.py'):ast.parse(p.read_bytes())
# FD sandbox leaking ownership endpoint cannot pass the concrete close predicate.
def guestFDs(opened):own.need(4 not in opened and not({5,6}&opened),'private ownership descriptors')
assert guestFDs({0,1,2})is None
refuses('sandbox-hostFD-alias',lambda:guestFDs({0,1,2,4}));refuses('sandbox-gateFD-alias',lambda:guestFDs({0,1,2,5}))
# V3 writer ownership: never infer acknowledgment from successful phase or
# socket cancellation. All workers/events below are inert injected objects.
class Worker:
 def __init__(self,alive):self.alive=alive;self.joins=[]
 def join(self,budget):self.joins.append(budget)
 def is_alive(self):return self.alive
for name,event,alive,accept in [('writer-blocked',False,True,False),('finally-but-thread-alive',True,True,False),('dead-no-finally-ack',False,False,False),('dead-ack',True,False,True)]:
 s=Stream(b'');p=own.HeldProtocol(s,100,1,GO.hex(),NONCE.hex(),lambda _:True);p.worker=Worker(alive)
 if event:p.writerStopped.set()
 assert p.writer_stop_acknowledged()is accept
 if accept:assert p.close()is True;positive.append(name)
 else:refuses(name,p.close)
# Future durable writer qualification requires real delayed fsync/start cases.
# This pure ordering model refuses unknown ownership after any wait entry.
def cleanup(state,waitOutcome):
 events=['retire-alarm','close-gate'];owned=state in {'ANCHORED','EXIT_HELD'}
 if not owned:return state,events
 events+=['kill-once','WAIT_ENTERED','wait']
 return ('REAPED'if waitOutcome=='child'else'UNCERTAIN'),events
for state in ['ANCHORED','EXIT_HELD','WAIT_ENTERED','REAPED','UNCERTAIN','NONE']:
 for outcome in ['child','error','deadline']:
  final,events=cleanup(state,outcome)
  if state in {'ANCHORED','EXIT_HELD'}:
   assert events.index('retire-alarm')<events.index('kill-once')<events.index('WAIT_ENTERED')<events.index('wait')
  else:assert 'kill-once'not in events and 'wait'not in events
  again,events2=cleanup(final,'child');assert 'kill-once'not in events2
positive.append('eighteen-exact-child-cleanup-orderings')
s=(D/'kexe_loader_diagnostic.c').read_text();call=(D/'native-call.py').read_text();assert call.index("r['pid']=proc.pid;save(")<call.index('peer.close();peer=None')
assert 'ownershipAck=protocol is None or protocol.writer_stop_acknowledged()'in call
assert "hfile(oj,65536)if ownershipAck and ownershipFile.closed"in call
assert 'with lj.open' in call and "as ownershipFile:"not in call
assert 'UNACKNOWLEDGED_OWNERSHIP_JOURNALS.append(retainedJournal)'in call
assert 'if (oh_arm_deadline(0) != 0) return oh_supervisor_refuse(child,78);'in s
assert 'if (oh_exit_held(child) != 0) return oh_supervisor_refuse(child,78);'in s
abort=hooks[hooks.index('static void oh_abort_unwaited'):hooks.index('static int oh_supervisor_refuse')]
assert abort.index('supervised_pid=-1;alarm(0)')<abort.index('kill(child,SIGKILL)')<abort.index('oh_child_state=OH_WAIT_ENTERED')<abort.index('waitpid(')
assert 'oh_child_state!=OH_ANCHORED&&oh_child_state!=OH_EXIT_HELD'in abort
assert 'oh_owned_child=child;oh_child_state=OH_ANCHORED;'in s
positive.append('V3-all-three-failure-closure-source-orderings')
assert 'earlyLeaderSignalAuthority=False;waitCalled=True'in call
assert 'os.kill(proc.pid,9)'in call and "early-owned-group-kill"not in call
assert "r['invocation']==admissionSHA256 and r['pid']==proc.pid"in call
assert call.index('earlyLeaderSignalAuthority=False\n    try:')<call.index('os.kill(proc.pid,9)')
positive.append('current-direct-Popen-invocation-no-postwait-signal')
# V5: execute actual setup AST through the pre-handshake boundary; all host
# interfaces are injected inert objects. No Thread/Popen/FD implementation runs.
callSource=(D/'native-call.py').read_text();tree=ast.parse(callSource)
fun=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='call')
setupTry=next(n for n in ast.walk(fun)if isinstance(n,ast.Try)and any(isinstance(q,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='proc'for t in q.targets)for q in n.body))
end=next(i for i,q in enumerate(setupTry.body)if isinstance(q,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='ticketMayHaveBeenSent'for t in q.targets))
setup=setupTry.body[:end]
cleanupNode=next(n for n in ast.walk(fun)if isinstance(n,ast.If)and 'earlyLeaderSignalAuthority'in ast.unparse(n.test)and 'ticketMayHaveBeenSent'in ast.unparse(n.test))
assert 'not ctl.waitEntered'in ast.unparse(cleanupNode.test)
assert callSource.count('deadline=time.monotonic()+30')==1
assert callSource.index('ticketMayHaveBeenSent=True')<callSource.index('initial=protocol.handshake')
setupCases=[]
faults=['none','fd-inventory','socketpair','host-nonblocking','peer-nonblocking','argv-save','Popen','PID-save','peer-close','controller-constructor','capture-second-dup','watchdog-constructor','watchdog-start','sampler-constructor','seal-read','protocol-constructor']
for fault in faults:
 events=[];saveOrdinal=[0]
 def checkpoint(name):
  events.append(name)
  if fault==name:raise RuntimeError('injected-'+name)
 class MockEndpoint:
  def __init__(self,name):self.name=name
  def setblocking(self,b):assert b is False;checkpoint(self.name+'-nonblocking')
  def fileno(self):return 6
  def close(self):checkpoint(self.name+'-close')
 class MockSocket:
  @staticmethod
  def socketpair():checkpoint('socketpair');return MockEndpoint('host'),MockEndpoint('peer')
 class MockFile:
  def fileno(self):return 5
 class MockProc:
  pid=100;stdout=None;stderr=None
 class MockSubprocess:
  DEVNULL=-3;PIPE=-1
  @staticmethod
  def Popen(*args,**kw):checkpoint('Popen');return MockProc()
 class MockCtl:
  def __init__(self,*args):checkpoint('controller-constructor');self.active=True;self.waitEntered=False;self.waitUncertain=False
  def retire(self,reason):self.active=False;events.append('retire:'+reason)
 class MockCapture:
  class Stopped:
   def is_set(self):return True
  stopped=Stopped()
  def refuse(self,reason):events.append('capture-refuse')
  def snapshot(self):return {'stoppedWriter':True}
 def mockTransfer(*args):checkpoint('capture-second-dup');return MockCapture()
 class MockWatch:
  def __init__(self,*args,**kw):checkpoint('watchdog-constructor')
  def start(self):checkpoint('watchdog-start')
  def join(self,timeout):events.append('watchdog-joined')
  def is_alive(self):return False
 class MockThreading:Thread=MockWatch
 class MockSampler:
  def __init__(self,*args):checkpoint('sampler-constructor')
 class MockMod:OwnedGroupSampler=MockSampler
 class MockPath:
  def __truediv__(self,v):return self
  def read_bytes(self):checkpoint('seal-read');return json.dumps({'rootGO':{'sha256':'a'*64}}).encode()
 class MockProtocol:
  def __init__(self,*args):checkpoint('protocol-constructor')
 class MockOS:
  @staticmethod
  def listdir(p):checkpoint('fd-inventory');return []
  @staticmethod
  def kill(pid,sig):assert pid==100 and sig==9;events.append('exact-leader-kill')
  dup=None;close=None
 class MockTime:
  @staticmethod
  def monotonic():return 5.0
 class MockStop:
  def set(self):events.append('watchdog-stop')
 def mockSave(*args):
  saveOrdinal[0]+=1;checkpoint('argv-save'if saveOrdinal[0]==1 else'PID-save')
 ns=dict(proc=None,peer=None,host=None,ctl=None,cap=None,watch=None,earlyLeaderSignalAuthority=False,ticketMayHaveBeenSent=False,cleanupWatchdogStopAck=False,waitCalled=False,waitRC=None,waitUncertain=False,r={'invocation':'ticket'},rows=[],O=MockPath(),D=D,case={'label':'case','nativeArgv':['native']},pr={'interpreter':{'path':'python'},'environment':{}},limitFile=MockFile(),admissionSHA256='ticket',save=mockSave,Controller=MockCtl,time=MockTime,deadline=30.0,need=own.need,os=MockOS,socket=MockSocket,subprocess=MockSubprocess,threading=MockThreading,transfer_popen_reads=mockTransfer,Capture=None,paths={},mod=MockMod,api=None,json=json,hashlib=hashlib,HeldProtocol=MockProtocol,persistOwnership=None,retainedJournal=[None,None],stop=MockStop(),watchErrors=[],failure=None)
 stopFn=next(n for n in ast.walk(fun)if isinstance(n,ast.FunctionDef)and n.name=='stopWatchdog')
 exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(stopFn)],type_ignores=[])),'source-stop-watchdog-mock','exec'),ns)
 failed=False
 try:exec(compile(ast.fix_missing_locations(ast.Module(body=copy.deepcopy(setup),type_ignores=[])),'source-pre-ticket-setup-mock','exec'),ns)
 except RuntimeError:failed=True;ns['failure']='injected-setup-refusal'
 assert failed is (fault!='none')
 if failed:
  # First three actual finally blocks: controller retirement, watchdog
  # acknowledgment and FD-only capture stop. Then exact pre-ticket kill.
  exec(compile(ast.fix_missing_locations(ast.Module(body=copy.deepcopy(setupTry.finalbody[:3]),type_ignores=[])),'source-stop-before-signal-mock','exec'),ns)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(cleanupNode)],type_ignores=[])),'source-early-leader-cleanup-mock','exec'),ns)
  owns=ns['proc']is not None
  assert events.count('exact-leader-kill')==(1 if owns else 0)
  if owns:
   assert ns['earlyLeaderSignalAuthority']is False and ns['cleanupWatchdogStopAck']is True and(ns['ctl']is None or not ns['ctl'].active)
   waitFn=next(n for n in ast.walk(fun)if isinstance(n,ast.FunctionDef)and n.name=='waitDirect')
   waitBody=copy.deepcopy([q for q in waitFn.body if not isinstance(q,ast.Nonlocal)])
   for q in ast.walk(ast.Module(body=waitBody,type_ignores=[])):
    if isinstance(q,ast.Try):q.body=[ast.Assign(targets=[ast.Name(id='mockWaitReturned',ctx=ast.Store())],value=z.value)if isinstance(z,ast.Return)else z for z in q.body]
   def mockWait(*,timeout):
    assert ns['waitCalled']and not ns['earlyLeaderSignalAuthority'];events.append('sole-direct-wait');return 0
   ns['proc'].wait=mockWait;ns['budget']=25
   exec(compile(ast.fix_missing_locations(ast.Module(body=waitBody,type_ignores=[])),'source-sole-wait-mock','exec'),ns)
   exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(cleanupNode)],type_ignores=[])),'source-postwait-cleanup-mock','exec'),ns)
   assert events.count('exact-leader-kill')==1 and events.count('sole-direct-wait')==1
 assert ns['ticketMayHaveBeenSent']is False and ns['deadline']==30.0
 setupCases.append({'fault':fault,'failed':failed,'directChildHandleObtained':ns['proc']is not None,'events':events,'originalDeadlineUnchanged':True,'TICKETSent':False,'actualOperations':0})
# Refusal rather than signal if ticket, wait, authority retirement or watchdog
# stop acknowledgment is uncertain. Evaluate exact SOURCE predicate.
base=dict(proc=MockProc(),ctl=None,ticketMayHaveBeenSent=False,waitCalled=False,waitUncertain=False,earlyLeaderSignalAuthority=True,cleanupWatchdogStopAck=True)
assert eval(compile(ast.Expression(cleanupNode.test),'source-cleanup-predicate','eval'),base)
for k,v in [('ticketMayHaveBeenSent',True),('waitCalled',True),('waitUncertain',True),('earlyLeaderSignalAuthority',False),('cleanupWatchdogStopAck',False)]:
 q=dict(base);q[k]=v;assert not eval(compile(ast.Expression(cleanupNode.test),'source-cleanup-predicate','eval'),q)
activeCtl=object.__new__(MockCtl);activeCtl.active=True;q=dict(base,ctl=activeCtl);assert not eval(compile(ast.Expression(cleanupNode.test),'source-cleanup-predicate','eval'),q)
for k in ['waitEntered','waitUncertain']:
 inactiveCtl=object.__new__(MockCtl);inactiveCtl.active=False;inactiveCtl.waitEntered=False;inactiveCtl.waitUncertain=False;setattr(inactiveCtl,k,True)
 q=dict(base,ctl=inactiveCtl);assert not eval(compile(ast.Expression(cleanupNode.test),'source-cleanup-predicate','eval'),q)
positive.append('V5-sixteen-source-bound-pre-ticket-setup-boundaries')
positive.append('V5-eight-source-bound-uncertainty-no-signal-predicates')
result={'status':'PASS_PURE_DIAGNOSTIC_HELD_OWNERSHIP_V5_COMPONENTS_ONLY','positive':positive,'negative':negative,'realAPI':0,'FDCalls':0,'threadStarts':0,'nativeCalls':0,'actualWNOWAITBirthQualificationPending':True,'sourceBoundSetupCases':setupCases}
(D/'pure-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'positive':len(positive),'negative':len(negative)}))
