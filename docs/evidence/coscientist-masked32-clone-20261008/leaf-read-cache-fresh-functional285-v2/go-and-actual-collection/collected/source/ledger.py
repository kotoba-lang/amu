from pathlib import Path
import hashlib,json,os,subprocess,signal,time,stat,resource
H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+"\n")
def ref(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=H(p.read_bytes()))
class Ledger:
 def __init__(self,folder,cap,env):
  self.folder=Path(folder);self.folder.mkdir();self.cap=cap;self.env=env;self.rows=[];self.started=time.monotonic()
 def call(self,label,argv,timeout,stdin=None):
  need(len(self.rows)<self.cap and time.monotonic()-self.started<9300,'finite child/deadline cap')
  i=len(self.rows)+1;outpath=self.folder/(str(i)+'.stdout');errpath=self.folder/(str(i)+'.stderr')
  row=dict(index=i,label=label,argv=argv,environment=self.env.copy(),timeoutSeconds=timeout,state='started',stdoutPath=str(outpath),stderrPath=str(errpath));self.rows.append(row);save(self.folder/'attempts.json',self.rows)
  proc=None;error=None;cleanup=None
  # Raw files are created before spawn and grow under bounded monitored caps.
  with outpath.open('xb') as out,errpath.open('xb') as err:
   try:
    def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(16777216,16777216))
    proc=subprocess.Popen(argv,env=self.env,cwd=self.folder.parent,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limit)
    if stdin is not None:proc.stdin.write(stdin);proc.stdin.close()
    until=time.monotonic()+timeout
    while proc.poll() is None:
     if time.monotonic()>=until:raise TimeoutError('finite wall cap')
     if outpath.stat().st_size>16777216 or errpath.stat().st_size>16777216:raise RuntimeError('raw stream cap')
     time.sleep(.05)
    proc.wait(timeout=30)
   except BaseException as ex:
    error=repr(ex)
    if proc is not None:
     try:
      if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL)
      proc.wait(timeout=30)
     except BaseException as ex2:
      cleanup=repr(ex2)
      try:proc.kill();proc.wait(timeout=30)
      except BaseException as ex3:cleanup+='; '+repr(ex3)
  row.update(state='spawn-failed' if proc is None else 'terminal' if proc.poll() is not None else 'unclosed',returncode=None if proc is None else proc.returncode,exception=error,cleanupException=cleanup,stdout=ref(outpath),stderr=ref(errpath));save(self.folder/'attempts.json',self.rows)
  need(row['state']=='terminal' and row['returncode']==0 and error is None and cleanup is None,('closed success',label,row))
  need(outpath.stat().st_size<=16777216 and errpath.stat().st_size<=16777216,'terminal raw caps')
  return outpath.read_bytes(),errpath.read_bytes(),row
 def terminal(self):return dict(children=len(self.rows),allClosed=all(r['state'] in ['terminal','spawn-failed'] for r in self.rows))
