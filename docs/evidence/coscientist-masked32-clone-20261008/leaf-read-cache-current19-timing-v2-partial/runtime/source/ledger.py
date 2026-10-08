"""Diagnostic V2:16MiB regular-file limit, separately bounded nonblocking pipes."""
from pathlib import Path
import hashlib,json,os,subprocess,signal,time,stat,resource,selectors
H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def save(p,v):
 p=Path(p);b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=16777216,'bounded durable JSON');t=p.with_name(p.name+'.pending')
 with t.open('wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p);fd=os.open(p.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def ref(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink(),'regular evidence');return dict(path=str(p),bytes=s.st_size,sha256=H(p.read_bytes()))
def regular_file_limit(api=resource):
 soft,hard=api.getrlimit(api.RLIMIT_FSIZE)
 need(hard==api.RLIM_INFINITY or hard>=16777216,'inherited hard regular-file limit below16MiB')
 api.setrlimit(api.RLIMIT_FSIZE,(16777216,16777216))
def cpu_usage(usage):return dict(userSeconds=usage.ru_utime,systemSeconds=usage.ru_stime,childCpuNs=round((usage.ru_utime+usage.ru_stime)*1000000000))
def kill_and_reap(proc):
 try:os.killpg(proc.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 if proc.returncode is not None:return None
 for grace in range(2):
  until=time.monotonic()+30
  while True:
   pid,status,usage=os.wait4(proc.pid,os.WNOHANG)
   if pid:proc.returncode=os.waitstatus_to_exitcode(status);return cpu_usage(usage)
   if time.monotonic()>=until:break
   time.sleep(.01)
  if grace==0:
   try:proc.kill()
   except ProcessLookupError:pass
 raise TimeoutError('bounded reap30+30 failed; unclosed stop')
def capture_piece(fd,sink,state,cap,read=os.read):
 """One bounded read. Durable sink never receives cap+1; overflow byte retained."""
 need(type(cap)is int and cap>=0 and 0<=state['bytes']<=cap and not state['EOF'],'pipe capture bounds')
 request=min(65536,cap-state['bytes']+1)
 try:b=read(fd,request)
 except BlockingIOError:return 'pending'
 need(type(b)is bytes and len(b)<=request,'bounded pipe read')
 if not b:state['EOF']=True;return 'EOF'
 left=cap-state['bytes'];payload=b[:left]
 if payload:
  written=sink.write(payload);need(type(written)is int and 0<=written<=len(payload),'pipe sink write');state['bytes']+=written;need(written==len(payload),'complete durable sink write')
 if len(b)>left:
  state['overflowByte']=b[left];return 'overflow'
 return 'data'
def pump(proc,sinks,states,rawcap,until,stdin_payload=None,selector_factory=selectors.DefaultSelector,read=os.read,write=os.write,wait=os.wait4,clock=time.monotonic):
 """Finite selector loop: feed stdin and drain both outputs without blocking."""
 selector=selector_factory();sent=0;cpu=None
 try:
  for role in ['stdout','stderr']:
   pipe=getattr(proc,role);os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,role)
  if stdin_payload is not None:
   need(type(stdin_payload)is bytes and len(stdin_payload)<=8388608,'stdin8MiB');os.set_blocking(proc.stdin.fileno(),False)
   if stdin_payload:selector.register(proc.stdin,selectors.EVENT_WRITE,'stdin')
   else:proc.stdin.close()
  while True:
   if proc.returncode is None:
    pid,status,usage=wait(proc.pid,os.WNOHANG)
    if pid:proc.returncode=os.waitstatus_to_exitcode(status);cpu=cpu_usage(usage);proc._ledger_cpu=cpu
   if proc.returncode is not None and all(s['EOF']for s in states.values()) and (stdin_payload is None or sent==len(stdin_payload)):break
   need(clock()<until,'finite pipe/child deadline')
   for key,mask in selector.select(min(.01,max(0,until-clock()))):
    role=key.data;pipe=key.fileobj
    if role=='stdin':
     try:n=write(pipe.fileno(),stdin_payload[sent:sent+65536])
     except BlockingIOError:continue
     need(type(n)is int and 0<n<=min(65536,len(stdin_payload)-sent),'bounded stdin write');sent+=n;proc._ledger_stdin_sent=sent
     if sent==len(stdin_payload):selector.unregister(pipe);pipe.close()
    else:
     result=capture_piece(pipe.fileno(),sinks[role],states[role],rawcap,read)
     if result=='EOF':selector.unregister(pipe);pipe.close()
     need(result!='overflow',role+' pipe exceeded cap; cap+1 byte retained in closure')
  return cpu,sent
 finally:selector.close()
class Ledger:
 def __init__(self,folder,env,snapshot=None,caps=None,deadline=172800):
  self.folder=Path(folder);self.folder.mkdir();self.env=env;self.snapshot=snapshot;self.rows=[];self.started=time.monotonic();self.deadline=deadline;self.caps=caps or dict(runner=5415,load=10830,transport=0);self.used={k:0 for k in self.caps}
 def call(self,label,argv,timeout,kind,stdin=None):
  need(kind in self.caps and self.used[kind]<self.caps[kind]and len(self.rows)<sum(self.caps.values()),'finite class/global cap');need(time.monotonic()-self.started<self.deadline,'campaign child deadline');self.used[kind]+=1
  i=len(self.rows)+1;folder=self.folder/('%05d'%i);folder.mkdir();rawcap=16384 if kind=='runner'else 1024 if kind=='load'else 8388608;outpath=folder/'stdout';errpath=folder/'stderr'
  row=dict(index=i,label=label,kind=kind,argv=argv,environment=self.env.copy(),timeoutSeconds=timeout,state='started',rawBytesMaximumPerStream=rawcap,regularFileBytesMaximum=16777216,pipeCapture='nonblocking-cap-plus-one',stdoutPath=str(outpath),stderrPath=str(errpath));self.rows.append(row);save(folder/'receipt.json',row)
  proc=None;error=None;cleanup=None;cpu=None;before=None;after=None;sent=0;states={a:dict(bytes=0,EOF=False,overflowByte=None)for a in ['stdout','stderr']}
  with outpath.open('xb')as out,errpath.open('xb')as err:
   try:
    def limit():
     # This ceiling also applies to immutable C materialization outside stdout.
     regular_file_limit()
    if kind=='runner':before=self.snapshot()
    proc=subprocess.Popen(argv,env=self.env,cwd=self.folder.parent,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limit)
    row['pid']=proc.pid;save(folder/'receipt.json',row);until=min(time.monotonic()+timeout,self.started+self.deadline)
    cpu,sent=pump(proc,dict(stdout=out,stderr=err),states,rawcap,until,stdin)
   except BaseException as ex:
    error=repr(ex)
    if proc is not None:cpu=getattr(proc,'_ledger_cpu',cpu);sent=getattr(proc,'_ledger_stdin_sent',sent)
    if proc is not None:
     try:
      reaped=kill_and_reap(proc)
      if reaped is not None:cpu=reaped
     except BaseException as ex2:cleanup=repr(ex2)
   finally:
    if proc is not None:
     for role in ['stdin','stdout','stderr']:
      pipe=getattr(proc,role)
      if pipe is not None:
       try:pipe.close()
       except BaseException as ex:cleanup=(cleanup or '')+' pipeclose '+role+': '+repr(ex)
    if kind=='runner'and before is not None:
     try:after=self.snapshot()
     except BaseException as ex:cleanup=(cleanup or '')+' CPU after: '+repr(ex)
    out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
  row.update(state='spawn-failed'if proc is None else'terminal'if proc.returncode is not None else'unclosed',returncode=None if proc is None else proc.returncode,exception=error,cleanupException=cleanup,stdout=ref(outpath),stderr=ref(errpath),waitedCPU=cpu,CPUbefore=before,CPUafter=after,pipeStates=states,stdinBytesSent=sent)
  need(len((json.dumps(row,indent=2)+'\n').encode())<=8192,'bounded closure8KiB');save(folder/'receipt.json',row);save(self.folder/'terminal.json',self.terminal())
  # Exact closure and all observed raw bytes (overflow byte in receipt) durable
  # before success validation. Buffered/unread bytes after failed kill are UNKNOWN.
  need(row['state']=='terminal'and row['returncode']==0 and error is None and cleanup is None,('closed success',label,row));need(all(s['EOF']and s['overflowByte']is None for s in states.values()),'both pipesEOF withoutoverflow');need(outpath.stat().st_size<=rawcap and errpath.stat().st_size<=rawcap,'strict bounded durable streams')
  return outpath.read_bytes(),errpath.read_bytes(),row
 def terminal(self):return dict(children=len(self.rows),classes=self.used.copy(),allClosed=all(r['state']in ['terminal','spawn-failed']for r in self.rows),noRetry=True)
