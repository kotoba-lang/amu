"""One reviewed real-pipe fixture driver; no native or process-group APIs."""
from pathlib import Path
import hashlib,json,os,resource,stat,subprocess,time,sys
D=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def pin(p,v):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==v['bytes'],'regular exact pinned file');b=p.read_bytes();z=p.lstat();need((s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_ino,z.st_size,z.st_mtime_ns)and H(b)==v['sha256'],'immutable pin');return b
def install_limits():
 for name,soft,hard in [('RLIMIT_FSIZE',65536,65536),('RLIMIT_CPU',10,11)]:
  kind=getattr(resource,name);before=resource.getrlimit(kind)
  need(all(a==resource.RLIM_INFINITY or a>=b for a,b in zip(before,(soft,hard))),'do not raise inherited limits')
  resource.setrlimit(kind,(soft,hard));need(resource.getrlimit(kind)==(soft,hard),'resource readback')
def main(gopath):
 g=json.loads(Path(gopath).read_text());need(g['status']=='ROOT_GO_ONE_FIXED_FILEIO_FIXTURE_SUPERVISED','exact GO')
 need(H((D/'supervise.py').read_bytes())==g['supervisorSHA256'],'exact supervisor')
 for p,v in g['pins'].items():pin(p,v)
 for p,v in g['sourceReviews'].items():pin(p,v)
 pr=json.loads(Path(g['preregistration']).read_text());need(pr['maximumDriverLaunches']==1 and pr['noRetry']is True and pr['rootOuterWallSeconds']==10 and pr['rootReapSeconds']==5,'fixed launch/deadlines')
 argv=pr['fixedArgv'];env=pr['fixedSuppliedEnvironment'];need(len(argv)==2 and len(env)==8,'exact argv/env scope');pin(argv[0],pr['interpreter'])
 O=D/'run-outputs';need(not O.exists(),'fresh no retry output');O.mkdir();p=None;failure=None;killed=False;rc=None;started=time.monotonic()
 with (O/'stdout').open('xb',buffering=0)as out,(O/'stderr').open('xb',buffering=0)as err:
  try:
   p=subprocess.Popen(argv,cwd=Path(argv[1]).parent,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,preexec_fn=install_limits)
   (O/'started.json').write_text(json.dumps({'pid':p.pid,'argv':argv,'deadlineSeconds':10,'reapSeconds':5})+'\n')
   try:rc=p.wait(timeout=max(.001,10-(time.monotonic()-started)))
   except subprocess.TimeoutExpired:
    failure='outer10s';p.kill();killed=True
    try:rc=p.wait(timeout=5)
    except subprocess.TimeoutExpired:failure='unclosed_after_kill_reap5s'
  except BaseException as ex:
   failure=repr(ex)
   if p is not None and p.returncode is None:
    try:
     p.kill();killed=True;rc=p.wait(timeout=5)
    except BaseException as cleanup:failure+=';cleanup:'+repr(cleanup)
   elif p is not None:rc=p.returncode
 q={'status':'CLOSED0_FIXED_FIXTURE_DRIVER_ONLY'if rc==0 and failure is None else'FAIL_FIXED_FIXTURE_DRIVER','pid':None if p is None else p.pid,'returncode':rc,'terminal':rc is not None,'failure':failure,'killedDirectChild':killed,'elapsedSeconds':time.monotonic()-started,'driverLaunches':int(p is not None),'nativeLaunches':0,'fixtureContainsPopen':False,'groupAPICalls':0,'resourcePolicy':{'FSIZE':[65536,65536],'CPU':[10,11],'wall':10,'reap':5},'raw':{}}
 for name in ['stdout','stderr']:
  pth=O/name;need(pth.stat().st_size<=65536,'raw bounded')
  if rc is None:q['raw'][name]={'bytes':pth.stat().st_size,'sha256':None,'activeWriterHashUnavailable':True}
  else:
   b=pth.read_bytes();q['raw'][name]={'bytes':len(b),'sha256':H(b)}
 (O/'terminal.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q));need(q['status']=='CLOSED0_FIXED_FIXTURE_DRIVER_ONLY','one attempt failed')
if __name__=='__main__':need(len(sys.argv)==2,'GO path');main(sys.argv[1])
