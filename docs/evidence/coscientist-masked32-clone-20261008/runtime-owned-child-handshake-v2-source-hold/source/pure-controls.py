"""Injected bounded fixtures only: zero pipes/threads/process/group/socket/setter calls."""
from pathlib import Path
import json,copy,ast,hashlib
import ownership as own
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
assert 'KEXE_OWNERSHIP_DIAGNOSTIC_V2'in s and 'oh_ticket.w[7]<=oh_now()'in hooks and 'oh_deadline=oh_ticket.w[7]'in hooks
for p in D.glob('*.py'):ast.parse(p.read_bytes())
# FD sandbox leaking ownership endpoint cannot pass the concrete close predicate.
def guestFDs(opened):own.need(4 not in opened and not({5,6}&opened),'private ownership descriptors')
assert guestFDs({0,1,2})is None
refuses('sandbox-hostFD-alias',lambda:guestFDs({0,1,2,4}));refuses('sandbox-gateFD-alias',lambda:guestFDs({0,1,2,5}))
result={'status':'PASS_PURE_DIAGNOSTIC_HELD_OWNERSHIP_V2_COMPONENTS_ONLY','positive':positive,'negative':negative,'realAPI':0,'FDCalls':0,'threadStarts':0,'nativeCalls':0,'actualWNOWAITBirthQualificationPending':True}
(D/'pure-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'positive':len(positive),'negative':len(negative)}))
