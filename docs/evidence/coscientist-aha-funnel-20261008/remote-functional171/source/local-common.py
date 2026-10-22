from pathlib import Path
import json,hashlib,subprocess,signal,os,shlex
D=Path(__file__).resolve().parent
HOST='zebulun@100.66.28.79'
R='/Users/zebulun/github/workspaces/codex/vector-aha-funnel-remote-runner-v1-root'
H=lambda b:hashlib.sha256(b).hexdigest()
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def read(p):return json.loads(p.read_text())
def guard(gp,stage):
 g=read(gp);assert g['stage']==stage and g['authorizedByRoot'] is True and g['outerExecution']=='require_escalated' and g['noRetry'] is True and g['destination']==HOST and g['remoteRoot']==R
 assert g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes()) and g['inputPinsSHA256']==H((D/'input-pins.json').read_bytes())
 for n,z in read(D/'source-pins.json').items():assert H((D/n).read_bytes())==z
 for n,z in read(D/'input-pins.json').items():
  p=Path(n);assert p.is_file() and not p.is_symlink() and p.stat().st_size==z['bytes'] and H(p.read_bytes())==z['sha256']
 rev=g['independentSourceReview'];p=Path(rev['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==rev['bytes'] and H(p.read_bytes())==rev['sha256']
 j=read(p);assert j['status'].startswith('PASS_') and j['sourcePinsSHA256']==g['sourcePinsSHA256']
 assert g['guests']==0 and g['timing'] is False
 return g
class Ledger:
 def __init__(self,O,cap):assert not O.exists();O.mkdir();self.O=O;self.rows=[];self.cap=cap
 def call(self,argv,timeout,data=None):
  assert len(self.rows)<self.cap;r={'index':len(self.rows)+1,'argv':argv,'timeoutSeconds':timeout,'state':'started'};self.rows.append(r);save(self.O/'attempts.json',self.rows)
  env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'LANG':'C','LC_ALL':'C','TZ':'UTC','PYTHONDONTWRITEBYTECODE':'1'}
  p=subprocess.Popen(argv,env=env,cwd=D,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);timed=False
  try:o,e=p.communicate(input=data,timeout=timeout)
  except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);o,e=p.communicate()
  n=str(r['index']);(self.O/(n+'.stdout')).write_bytes(o);(self.O/(n+'.stderr')).write_bytes(e);r.update(state='terminal',returncode=p.returncode,timeout=timed,stdoutSHA256=H(o),stderrSHA256=H(e));save(self.O/'attempts.json',self.rows)
  assert not timed and p.returncode==0
  return o,e
 def terminal(self):save(self.O/'terminal.json',{'calls':len(self.rows),'allClosed':all(r['state']=='terminal' for r in self.rows),'failure':(self.O/'failure.json').exists()})
OPTS=['-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1']
def remote(script):
 prefix=(D/'result-contract.py').read_text()+'\n' if script=='remote-seal.py' else ''
 return ['ssh',*OPTS,HOST,'python3 -c '+shlex.quote(prefix+(D/script).read_text())]
