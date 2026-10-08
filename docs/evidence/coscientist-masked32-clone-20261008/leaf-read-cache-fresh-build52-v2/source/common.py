"""Finite SOURCE helpers. Import is inert; execution always needs exact GO."""
from pathlib import Path
import hashlib,json,os,subprocess,signal,time,stat,resource
D=Path(__file__).resolve().parent
HOST='zebulun@100.66.28.79'
ROOT=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root')
STAGE=Path(str(ROOT)+'-stage')
CAP=469762048
def need(x,msg):
 if not x:raise AssertionError(msg)
def H(b):return hashlib.sha256(b).hexdigest()
def sha(p):return H(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def ref(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def pin(r,cap=CAP):
 p=Path(r['path']);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==r['bytes']<=cap,('regular size',str(p)));need(sha(p)==r['sha256'],('hash',str(p)));return p
def sourceguard(base=D):
 bank=load(base/'source-pins.json')
 for name,r in bank.items():pin(dict(r,path=str(base/name)))
 return sha(base/'source-pins.json')
def authorize(phase,gp,base=D):
 gp=Path(gp);need(gp.is_file() and not gp.is_symlink() and gp.stat().st_size<=1048576,'regular GO <=1MiB');g=load(gp)
 need(g.get('phase')==phase and g.get('authorized') is True,'explicit phase GO')
 need(g.get('destination')==HOST and g.get('remoteRoot')==str(ROOT),'exact actor/root')
 need(g.get('sourcePinsSHA256')==sourceguard(base),'immutable SOURCE pins')
 need(g.get('preregistrationSHA256')==sha(base/'preregistration.json'),'immutable preregistration')
 need(g.get('functionalAuthorized') is False and g.get('timingAuthorized') is False,'build/transport does not run guest')
 rv=g.get('sourceReviews');need(isinstance(rv,list) and len(rv)==2 and rv[0]['sha256']!=rv[1]['sha256'],'two distinct SOURCE reviews')
 for r in rv:
  q=load(pin(r,1048576));need(str(q.get('status','')).startswith('PASS') and q.get('sourcePinsSHA256')==g['sourcePinsSHA256'],'review PASS on exact SOURCE')
 acceptance=load(base/'root-functional285-acceptance-ref.json')
 need(g.get('rootFunctional285AcceptanceSHA256')==acceptance['sha256'],'root current285 acceptance binding')
 if (base/'root-functional285-acceptance.json').exists():need(sha(base/'root-functional285-acceptance.json')==acceptance['sha256'],'packaged acceptance')
 else:pin(acceptance,1048576)
 return g
class Ledger:
 def __init__(self,folder,cap,env):
  self.folder=Path(folder);self.folder.mkdir();self.cap=cap;self.env=env;self.rows=[];self.started=time.monotonic()
 def call(self,label,argv,timeout,stdin=None):
  need(len(self.rows)<self.cap and time.monotonic()-self.started<7800,'finite child/deadline cap')
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
