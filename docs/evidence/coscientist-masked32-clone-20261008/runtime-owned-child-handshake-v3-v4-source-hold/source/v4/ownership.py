"""Import-inert diagnostic held-launch protocol; fixed128B LE ABI, no unknown PID admission."""
import struct,time,select,os,json,threading,hashlib
MAGIC=0x32564e574f45584b
WIRE=struct.Struct('<8Q32s32s')
POLICY='held-launch-owned-physical-memory-diagnostic-v4'
class Refusal(Exception):pass
class RetiredAuthority(AssertionError):pass
def need(q,m):
 if not q:raise Refusal(m)
def encode(stage,seq,leader,child,birth,group,status,go,nonce):return WIRE.pack(MAGIC,stage,seq,leader,child,birth,group,status,go,nonce)
def decode(b):
 need(len(b)==128,'exact ownership frame');q=WIRE.unpack(b);need(q[0]==MAGIC,'wire magic');return q
class ExactIO:
 def __init__(self,stream,deadline,clock=time.monotonic,ready=None):
  self.stream=stream;self.deadline=deadline;self.clock=clock;self.ready=ready or self._ready;self.operations=0;self.records=0
 def _ready(self,writing,remaining):
  r,w,_=select.select([]if writing else[self.stream],[self.stream]if writing else[],[],remaining);return bool(w if writing else r)
 def transfer(self,b,writing):
  need(self.records<8,'finite protocol records');self.records+=1;n=0;out=bytearray()
  while n<128:
   self.operations+=1;need(self.operations<=4096,'finite partial IO operations');remaining=self.deadline-self.clock();need(remaining>0,'original deadline')
   try:
    need(self.ready(writing,remaining),'poll deadline');need(self.clock()<self.deadline,'late ready')
    if writing:
     k=self.stream.send(b[n:]);need(type(k)is int and 0<k<=128-n,'partial write bounds');n+=k
    else:
     q=self.stream.recv(128-n);need(type(q)is bytes and 0<len(q)<=128-n,'channel EOF/partial bounds');out.extend(q);n+=len(q)
   except InterruptedError:continue
  need(self.clock()<self.deadline,'late completed frame');return b if writing else bytes(out)
 def send(self,b):need(len(b)==128,'fixed frame');return self.transfer(b,True)
 def recv(self):return self.transfer(b'',False)
class HeldProtocol:
 def __init__(self,stream,leader,deadline,goHex,nonceHex,persist):
  need(type(leader)is int and 0<leader<2**31,'direct leader');self.leader=leader;self.deadline=deadline;self.go=bytes.fromhex(goHex);self.nonce=bytes.fromhex(nonceHex);need(len(self.go)==len(self.nonce)==32,'current ticket');self.io=ExactIO(stream,deadline);self.persist=persist;self.bindings={};self.initial=[];self.waitReceipt=None;self.waitError=None;self.worker=None;self.phase=0;self.recordCount=0;self.closed=False;self.writerStopped=threading.Event();self.workerStarted=False;self.closeError=None
 def durable(self,row):
  self.recordCount+=1;need(self.recordCount<=8,'finite durable ownership rows');need(self.persist(row)is True,'fsynced ownership journal')
 def matching(self,raw,stage,seq):
  q=decode(raw);need(q[1]==stage and q[2]==seq and q[3]==self.leader and q[6]==self.leader and q[8]==self.go and q[9]==self.nonce,'current ordered owner frame');return q
 def handshake(self,ctl,sampler,persistSample):
  need(self.phase==0,'one handshake');self.phase=1
  remaining=self.deadline-time.monotonic();need(remaining>0,'original ticket budget')
  absolute=time.clock_gettime_ns(time.CLOCK_MONOTONIC)+int(remaining*1000000000)
  self.io.send(encode(1,0,self.leader,0,0,self.leader,absolute,self.go,self.nonce))
  for stage,seq in [(2,1),(4,2)]:
   raw=self.io.recv();q=self.matching(raw,stage,seq);pid=self.leader if stage==2 else q[4]
   need(q[7]==0 and q[5]>0 and(q[4]==0 if stage==2 else 0<pid<2**31 and pid!=self.leader),'held stage PID/birth')
   # Child cannot execute until ACK. Stable whole-group sample independently
   # reads this held live birth; sampler commits only its original complete law.
   s=ctl.group(sampler.sample);expected={self.leader}if stage==2 else{self.leader,pid}
   need({m['pid']for m in s['members']}==expected,'exact held census')
   member=next(m for m in s['members']if m['pid']==pid);need(member['start']==q[5]and member['exit']==0,'held kernel birth correlation')
   if stage==4:need(next(m for m in s['members']if m['pid']==self.leader)['start']==self.bindings[self.leader],'leader birth stable')
   need(persistSample(s)is True,'durable held sample');self.initial.append(s);self.bindings[pid]=q[5]
   self.durable({'stage':'held-birth-admitted','sequence':seq,'leader':self.leader,'pid':pid,'birth':q[5],'GO':self.go.hex(),'nonce':self.nonce.hex(),'wireSHA256':hashlib.sha256(raw).hexdigest(),'guestStillHeld':True})
   # Persist callback must complete fsync BEFORE this exact echoed ACK.
   self.io.send(encode(stage+1,seq,self.leader,q[4],q[5],self.leader,0,self.go,self.nonce))
  self.phase=2;return self.initial.copy()
 def receive_wait(self,ctl,state):
  try:
   need(self.phase==2,'wait after child release');raw=self.io.recv();q=self.matching(raw,6,3)
   need(q[4]!=self.leader and self.bindings.get(q[4])==q[5]and q[7]==0,'exact held child EXIT0 before reap')
   self.durable({'stage':'loader-child-exit-held','pid':q[4],'birth':q[5],'exit':0,'GO':self.go.hex(),'nonce':self.nonce.hex(),'wireSHA256':hashlib.sha256(raw).hexdigest(),'unreapedPIDAnchor':True})
   # Atomic retirement under controller's shared lock, before ACK allows reap.
   ctl.retire('owned-child-exit-before-reap-ACK');state.update(exitHeld=True)
   self.io.send(encode(7,3,self.leader,q[4],q[5],self.leader,0,self.go,self.nonce))
   raw=self.io.recv();q=self.matching(raw,8,4)
   need(q[4]!=self.leader and self.bindings.get(q[4])==q[5]and q[7]==0,'exact held child wait EXIT0')
   self.durable({'stage':'loader-child-wait','pid':q[4],'birth':q[5],'waitStatus':q[7],'GO':self.go.hex(),'nonce':self.nonce.hex(),'wireSHA256':hashlib.sha256(raw).hexdigest(),'noPostReapGroupQueries':True});self.waitReceipt={'pid':q[4],'birth':q[5],'exit':0,'durable':True};self.phase=3
  except BaseException as ex:
   self.waitError=repr(ex);ctl.retire('ownership-channel-failure');state.update(channelFailure=True)
  finally:
   # No receipt persist callback can follow this acknowledgment.
   self.writerStopped.set()
 def start_wait(self,ctl,state):
  need(self.worker is None,'one wait receipt worker');self.worker=threading.Thread(target=lambda:self.receive_wait(ctl,state),name='owned-child-receipt',daemon=False);self.workerStarted=True;self.worker.start()
 def finish(self):
  need(self.worker is not None,'wait worker');self.worker.join(max(0,self.deadline-time.monotonic()));need(self.writerStopped.is_set()and not self.worker.is_alive()and self.waitError is None and self.phase==3 and self.waitReceipt is not None,'bounded durable exact child wait');return True
 def writer_stop_acknowledged(self):
  # A start exception may be ambiguous: any created worker requires its own
  # finally acknowledgment AND actual thread death; return is never guessed.
  return self.worker is None or(self.writerStopped.is_set()and not self.worker.is_alive())
 def close(self):
  if not self.closed:
   self.closed=True
   try:self.io.stream.close()
   except BaseException as ex:self.closeError=repr(ex)
  if self.worker is not None:self.worker.join(max(0,self.deadline-time.monotonic()))
  need(self.writer_stop_acknowledged(),'ownership worker stop acknowledgment unavailable')
  need(self.closeError is None,'ownership socket close failed')
  return True
def validate_failure(context,api,bindings,leader,invocation):
 need(type(context)is dict and context['typedOrigin']=='fresh-owned-group-api-v1'and context['contextVersion']=='owned-group-sampling-failure-context-v1'and context['invocation']==invocation,'fresh current API origin')
 need(context['queryOrdinal']==api.queryOrdinal and context['queryOrdinal']>0 and all(context[k]==api.lastAttempt[k]for k in api.lastAttempt),'last current API fault')
 pid=context['pid'];stage=context['stage'];need(type(pid)is int and type(context['queryOrdinal'])is int,'typed PID/ordinal');need(pid in bindings,'unknown fault PID')
 need((stage=='leader-getpgid'and pid==leader)or(stage in {'member-getpgid','member-rusage'}and pid in bindings),'stage owner identity')
 need((context['errno']==3 and context['failureClass']in {'kernel-oserror','kernel-failed-return'})or(context['errno']==0 and context['failureClass']=='kernel-observed-exited'and context['observedBirth']==bindings[pid]and type(context['observedExit'])is int and context['observedExit']>0),'explicit owned error/exited birth');return True
