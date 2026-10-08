"""Exactly one ordinary SSH launch. No compiler/build/loader changes or retry."""
from functional285 import *
import base64,copy,shlex

def main():
 need(len(sys.argv)==2,'one exact local root GO');gp=Path(sys.argv[1]);g=authorize(gp);gh=sha(gp)
 bank=load(D/'input-pins.json');extra=[ref(gp)]+g['sourceReviews']+[dict(r,path=str(D/n)) for n,r in load(D/'source-pins.json').items()]+[ref(D/'source-pins.json')]
 bounded_bank(bank,extra)
 output=D/'launch-outputs';need(not output.exists(),'fresh one SSH launch no retry');output.mkdir();remote=copy.deepcopy(g);files={}
 for n,r in load(D/'source-pins.json').items():files['source/'+n]=base64.b64encode(pin(dict(r,path=str(D/n))).read_bytes()).decode()
 files['source/source-pins.json']=base64.b64encode((D/'source-pins.json').read_bytes()).decode()
 for i,r in enumerate(g['sourceReviews']):
  b=pin(r,1048576).read_bytes();name='control/review'+str(i)+'.json';files[name]=base64.b64encode(b).decode();remote['sourceReviews'][i]=dict(path=str(ROOT/name),bytes=len(b),sha256=H(b))
 remote['originalLocalGOSHA256']=gh;rb=json.dumps(remote,indent=2).encode()+b'\n';files['control/root-go.json']=base64.b64encode(rb).decode();save(output/'derived-remote-go.json',remote)
 payload=json.dumps(dict(files=files,sourcePinsSHA256=g['sourcePinsSHA256'],remoteGOSHA256=H(rb)),separators=(',',':')).encode();need(len(payload)<=8388608,'bounded SOURCE/control stdin8MiB; historical archives never retransferred')
 wrapper="""import pathlib,json,hashlib,base64,sys,signal,runpy,os
signal.alarm(9420)
root=pathlib.Path(%r)
assert pathlib.Path.home()==pathlib.Path('/Users/zebulun') and not root.exists()
b=sys.stdin.buffer.read(8388609);assert len(b)<=8388608
req=json.loads(b);assert set(req)=={'files','sourcePinsSHA256','remoteGOSHA256'}
root.mkdir();(root/'source').mkdir();(root/'control').mkdir()
for n,t in req['files'].items():
 p=pathlib.PurePosixPath(n);assert not p.is_absolute() and len(p.parts)==2 and p.parts[0] in ['source','control'] and '..' not in p.parts and str(p)==n
 data=base64.b64decode(t,validate=True);assert len(data)<=2097152
 target=root/n
 with target.open('xb') as f:f.write(data)
 target.chmod(0o444)
assert hashlib.sha256((root/'source/source-pins.json').read_bytes()).hexdigest()==req['sourcePinsSHA256']
for n,r in json.loads((root/'source/source-pins.json').read_bytes()).items():
 assert '/' not in n and n not in ['.','..']
 p=root/'source'/n;assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
assert hashlib.sha256((root/'control/root-go.json').read_bytes()).hexdigest()==req['remoteGOSHA256']
sys.dont_write_bytecode=True;sys.path.insert(0,str(root/'source'));sys.argv=[str(root/'source/functional285.py'),str(root/'control/root-go.json')]
runpy.run_path(sys.argv[0],run_name='__main__')
print('LC_FRESH_CONSUMER_FUNCTIONAL285_REMOTE_TERMINAL',flush=True)
"""%str(ROOT)
 need(len(wrapper.encode())<=131072,'SSH literal command bound')
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/junkawasaki',TMPDIR='/private/tmp');led=Ledger(output/'children',1,env)
 def alarm(signum,frame):raise TimeoutError('one SSH launch absolute deadline')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(9480)
 try:
  authorize(gp);bounded_bank(bank,extra);need(sha(gp)==gh,'local GO stable')
  argv=['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',HOST,'python3 -c '+shlex.quote(wrapper)]
  out,err,row=led.call('fresh-functional285-launch',argv,9420,stdin=payload)
  need(not err and out==b'LC_FRESH_CONSUMER_FUNCTIONAL285_REMOTE_TERMINAL\n','explicit closed remote seal')
  authorize(gp);bounded_bank(bank,extra);need(sha(gp)==gh,'local GO stable after')
  save(output/'report.json',dict(status='PASS_FRESH_FUNCTIONAL285_V2_ONE_SSH_LAUNCH_ONLY_ACTUAL_REVIEW_PENDING',launchChildren=1,priorFailedLaunches=1,cumulativeLaunchChildren=2,maximumCumulativeLaunchChildren=2,expectedInnerChildren=285,remoteGOSHA256=H(rb),originalLocalGOSHA256=gh,payloadBytes=len(payload),payloadSHA256=H(payload),functionalAccepted=False,timingQualified=False))
 except BaseException as ex:save(output/'failure.json',dict(exception=repr(ex),noRetry=True,remoteClosureOnTransportFailure='UNKNOWN; remote bounded alarm9420 and inner9300'));raise
 finally:signal.alarm(0);save(output/'terminal.json',dict(**led.terminal(),failure=(output/'failure.json').exists()))
if __name__=='__main__':main()
