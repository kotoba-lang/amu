"""Mock pipe/control checks only; no actual OS pipes or child executions."""
import io,json
from types import SimpleNamespace
from unittest.mock import patch
import ledger
from ledger import need,capture_piece,pump,kill_and_reap
class Pipe:
 def __init__(self,fd):self.fd=fd;self.closed=False
 def fileno(self):return self.fd
 def close(self):self.closed=True
class Selector:
 def __init__(self):self.keys={}
 def register(self,pipe,event,role):self.keys[pipe.fd]=SimpleNamespace(fileobj=pipe,data=role);return self.keys[pipe.fd]
 def unregister(self,pipe):self.keys.pop(pipe.fd)
 def select(self,timeout):return [(k,0)for k in list(self.keys.values())]
 def close(self):pass
def trial(chunks,cap=4,waitpid=True,stdin=None,write=None):
 proc=SimpleNamespace(pid=123,returncode=None,stdout=Pipe(101),stderr=Pipe(102),stdin=Pipe(103)if stdin is not None else None)
 sinks={r:io.BytesIO()for r in ['stdout','stderr']};states={r:dict(bytes=0,EOF=False,overflowByte=None)for r in sinks};counter=[0];usage=SimpleNamespace(ru_utime=.1,ru_stime=.2)
 def clock():counter[0]+=1;return counter[0]/1000
 def read(fd,n):
  row=chunks.get(fd,[])
  if not row:return b''
  value=row.pop(0)
  if isinstance(value,BaseException):raise value
  return value
 def wait(pid,opts):return (123,0,usage)if waitpid else(0,0,None)
 with patch.object(ledger.os,'set_blocking'):
  cpu,sent=pump(proc,sinks,states,cap,.1,stdin,Selector,read,write or(lambda fd,b:len(b)),wait,clock)
 return proc,sinks,states,cpu,sent

def main():
 tests=[]
 p,o,s,c,_=trial({101:[b'a',b'bcd',b''],102:[b'x',b'']})
 need(o['stdout'].getvalue()==b'abcd'and all(v['EOF']for v in s.values())and p.returncode==0 and c['childCpuNs']==300000000,'exit-before-finaldrain');tests.append('partial reads and exit before final drain retain both EOF and CPU')
 sink=io.BytesIO();state=dict(bytes=0,EOF=False,overflowByte=None)
 result=capture_piece(1,sink,state,4,lambda fd,n:b'abcde')
 need(result=='overflow'and sink.getvalue()==b'abcd'and state['bytes']==4 and state['overflowByte']==101,'never writecap+1');tests.append('overflow byte retained in closure without exceeding durable sink cap')
 requests=[];result=capture_piece(1,sink,state,4,lambda fd,n:requests.append(n)or b'')
 need(result=='EOF'and requests==[1],'exactcapEOF');tests.append('exact-cap requires bounded one-byte EOF probe')
 sink=io.BytesIO();state=dict(bytes=0,EOF=False,overflowByte=None)
 def blocked(fd,n):raise BlockingIOError()
 need(capture_piece(1,sink,state,4,blocked)=='pending'and state['bytes']==0,'EAGAIN');tests.append('nonblocking partial availability does not lose bytes')
 try:trial({101:[b'a']},waitpid=False)
 except AssertionError as ex:need('deadline'in str(ex),'boundedtimeout')
 else:raise AssertionError('timeout missing')
 tests.append('no-exit with pipes nonempty/EOF remains finite under deadline')
 p,o,s,c,sent=trial({101:[b''],102:[b'']},stdin=b'abcdefgh',write=lambda fd,b:min(2,len(b)))
 need(sent==8 and p.stdin.closed,'stdinpartial');tests.append('partial stdin writes finish through finite selector loop')
 usage=SimpleNamespace(ru_utime=.1,ru_stime=.2);p=SimpleNamespace(pid=123,returncode=None,kill=lambda:None)
 with patch.object(ledger.os,'killpg',side_effect=ProcessLookupError),patch.object(ledger.os,'wait4',return_value=(123,0,usage))as w:c=kill_and_reap(p)
 need(p.returncode==0 and w.call_count==1,'killrace reap');tests.append('process exits immediately before kill and is still reaped')
 p=SimpleNamespace(pid=123,returncode=0)
 with patch.object(ledger.os,'killpg',side_effect=ProcessLookupError),patch.object(ledger.os,'wait4')as w:need(kill_and_reap(p)is None and w.call_count==0,'alreadyreaped nosecondwait')
 tests.append('already waited child is never waited twice during pipe failure cleanup')
 try:trial({101:[b'abcde'],102:[b'']})
 except AssertionError as ex:need('cap+1'in str(ex),'overflow refuses before success')
 else:raise AssertionError('overflow success')
 tests.append('pump raises first overflow for caller kill/reap without continuing stream success')
 api=SimpleNamespace(RLIMIT_FSIZE=1,RLIM_INFINITY=-1,getrlimit=lambda key:(-1,-1),setrlimit=lambda key,value:limits.append(value));limits=[]
 ledger.regular_file_limit(api);need(limits==[(16777216,16777216)],'distinct16MiB regular cap');tests.append('regular-file limit remains16MiB independently of1024/16384 pipe cap')
 api.getrlimit=lambda key:(8192,8192)
 try:ledger.regular_file_limit(api)
 except AssertionError:pass
 else:raise AssertionError('low inherited hard limit not refused')
 tests.append('inherited hard file cap below16MiB fails closed without expansion')
 # Call the real Ledger cleanup/durability code with fully mocked Popen/pump.
 # Only regular diagnostic fixture files are created, never a child or OS pipe.
 import tempfile
 from pathlib import Path
 folder=Path(tempfile.mkdtemp(prefix='pipe-fixtures-',dir=Path(__file__).resolve().parent))
 proc=SimpleNamespace(pid=123,returncode=None,stdin=None,stdout=Pipe(101),stderr=Pipe(102))
 def fake_pump(p,sinks,states,cap,until,stdin):
  sinks['stdout'].write(b'x'*cap);states['stdout'].update(bytes=cap,overflowByte=42)
  raise AssertionError('stdout pipe exceeded cap; cap+1')
 def fake_reap(p):p.returncode=-9;return dict(userSeconds=0,systemSeconds=0,childCpuNs=0)
 led=ledger.Ledger(folder/'children',dict(PATH='/usr/bin'),caps=dict(load=1),deadline=10)
 with patch.object(ledger.subprocess,'Popen',return_value=proc),patch.object(ledger,'pump',side_effect=fake_pump),patch.object(ledger,'kill_and_reap',side_effect=fake_reap)as reap:
  try:led.call('MOCK-OVERFLOW',['MOCK'],1,'load')
  except AssertionError:pass
  else:raise AssertionError('overflow accepted')
 need(reap.call_count==1 and proc.stdout.closed and proc.stderr.closed and led.rows[0]['state']=='terminal','overflow closes/reaps')
 need((folder/'children/00001/stdout').stat().st_size==1024 and led.rows[0]['pipeStates']['stdout']['overflowByte']==42 and led.rows[0]['stdout']['bytes']==1024,'overflow durable before refusal')
 tests.append('mock overflow kills/reaps/closes and persists cap-bounded raw plus overflow byte before refusal')
 print(json.dumps(dict(status='PASS_PURE_MOCK_V2_PIPE_CONTROLS_ONLY',controls=tests,tests=len(tests),actualOSPipeCalls=0,actualChildren=0,nativeCompilerSSHCalls=0),indent=2))
if __name__=='__main__':main()
