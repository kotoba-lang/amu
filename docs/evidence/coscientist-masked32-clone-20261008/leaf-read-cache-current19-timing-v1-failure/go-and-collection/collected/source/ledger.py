"""Diagnostic orchestration only. Finite durable subprocess closure and waited CPU."""
from pathlib import Path
import hashlib,json,os,subprocess,signal,time,stat,resource
H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def save(p,v):
 p=Path(p);b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=16777216,'bounded durable JSON')
 t=p.with_name(p.name+'.pending')
 with t.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
 fd=os.open(p.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def ref(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink(),'regular evidence');return dict(path=str(p),bytes=s.st_size,sha256=H(p.read_bytes()))
def kill_and_reap(proc):
 # A child can exit between timeout detection and killpg. Always reap even if
 # its process group has already disappeared; ProcessLookupError is not closure.
 try:os.killpg(proc.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 for grace in range(2):
  until=time.monotonic()+30
  while True:
   pid,status,usage=os.wait4(proc.pid,os.WNOHANG)
   if pid:
    proc.returncode=os.waitstatus_to_exitcode(status)
    return dict(userSeconds=usage.ru_utime,systemSeconds=usage.ru_stime,childCpuNs=round((usage.ru_utime+usage.ru_stime)*1000000000))
   if time.monotonic()>=until:break
   time.sleep(.01)
  if grace==0:
   try:proc.kill()
   except ProcessLookupError:pass
 raise TimeoutError('bounded reap30+30 failed; unclosed stop')
class Ledger:
 def __init__(self,folder,env,snapshot=None,caps=None,deadline=172800):
  self.folder=Path(folder);self.folder.mkdir();self.env=env;self.snapshot=snapshot;self.rows=[];self.started=time.monotonic();self.deadline=deadline
  self.caps=caps or dict(runner=5415,load=10830,transport=0);self.used={k:0 for k in self.caps}
 def call(self,label,argv,timeout,kind,stdin=None):
  need(kind in self.caps and self.used[kind]<self.caps[kind] and len(self.rows)<sum(self.caps.values()),'finite class/global child cap')
  need(time.monotonic()-self.started<self.deadline,'campaign child deadline');self.used[kind]+=1
  i=len(self.rows)+1;folder=self.folder/('%05d'%i);folder.mkdir();rawcap=16384 if kind=='runner' else 1024 if kind=='load' else 8388608
  outpath=folder/'stdout';errpath=folder/'stderr';row=dict(index=i,label=label,kind=kind,argv=argv,environment=self.env.copy(),timeoutSeconds=timeout,state='started',rawBytesMaximumPerStream=rawcap)
  self.rows.append(row);save(folder/'receipt.json',row);proc=None;error=None;cleanup=None;cpu=None;before=None;after=None
  with outpath.open('xb')as out,errpath.open('xb')as err:
   try:
    def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(rawcap,rawcap))
    if kind=='runner':before=self.snapshot()
    proc=subprocess.Popen(argv,env=self.env,cwd=self.folder.parent,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limit)
    row['pid']=proc.pid;save(folder/'receipt.json',row)
    if stdin is not None:proc.stdin.write(stdin);proc.stdin.close()
    until=min(time.monotonic()+timeout,self.started+self.deadline)
    while True:
     pid,status,usage=os.wait4(proc.pid,os.WNOHANG)
     if pid:
      proc.returncode=os.waitstatus_to_exitcode(status);cpu=dict(userSeconds=usage.ru_utime,systemSeconds=usage.ru_stime,childCpuNs=round((usage.ru_utime+usage.ru_stime)*1000000000));break
     if time.monotonic()>=until:raise TimeoutError('finite wall/campaign cap')
     if outpath.stat().st_size>rawcap or errpath.stat().st_size>rawcap:raise RuntimeError('raw stream cap')
     time.sleep(.01)
   except BaseException as ex:
    error=repr(ex)
    if proc is not None and proc.returncode is None:
     try:
      cpu=kill_and_reap(proc)
     except BaseException as ex2:cleanup=repr(ex2)
   finally:
    if kind=='runner' and before is not None:
     try:after=self.snapshot()
     except BaseException as ex:cleanup=(cleanup or '')+' CPU after: '+repr(ex)
    out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
  row.update(state='spawn-failed' if proc is None else 'terminal' if proc.returncode is not None else 'unclosed',returncode=None if proc is None else proc.returncode,exception=error,cleanupException=cleanup,stdout=ref(outpath),stderr=ref(errpath),waitedCPU=cpu,CPUbefore=before,CPUafter=after)
  need(len((json.dumps(row,indent=2)+'\n').encode())<=8192,'bounded closure row');save(folder/'receipt.json',row);save(self.folder/'terminal.json',self.terminal())
  # Terminal raw/argv/environment/CPU and exact closure are durable before validation.
  need(row['state']=='terminal' and row['returncode']==0 and error is None and cleanup is None,('closed success',label,row))
  need(outpath.stat().st_size<=rawcap and errpath.stat().st_size<=rawcap,'terminal raw caps')
  return outpath.read_bytes(),errpath.read_bytes(),row
 def terminal(self):return dict(children=len(self.rows),classes=self.used.copy(),allClosed=all(r['state']in ['terminal','spawn-failed']for r in self.rows),noRetry=True)
