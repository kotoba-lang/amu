"""One pinned diagnostic fixture driver. Deferred until exact reviewed GO."""
from pathlib import Path
import hashlib,json,os,resource,stat,subprocess,time,sys
D=Path(__file__).resolve().parent
F=Path('/Users/junkawasaki/github/workspaces/codex/crc-capture-popen-transfer-fixture-source-v1-20261009')
H=lambda b:hashlib.sha256(b).hexdigest()
_uncertain_child=None

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
 global _uncertain_child
 g=json.loads(Path(gopath).read_text())
 need(set(g)=={'status','supervisorSHA256','pins','sourceReviews','supervisorReview','outputRoot'},'exact GO fields')
 need(g['status']=='ROOT_GO_ONE_FIXED_FILEIO_FIXTURE_SUPERVISED_V2' and g['outputRoot']==str(D/'run-outputs'),'exact GO')
 need(H((D/'supervise.py').read_bytes())==g['supervisorSHA256'],'exact supervisor')
 for p,v in g['pins'].items():pin(p,v)
 def bound(p):need(str(p)in g['pins'],'declared child/registry binding');return pin(p,g['pins'][str(p)])
 sp=json.loads(bound(F/'source-pins.json'));ip=json.loads(bound(F/'input-pins.json'));pr=json.loads(bound(F/'preregistration.json'))
 for name,v in sp.items():need(g['pins'].get(str(F/name))==v,'exact complete child SOURCE registry');bound(F/name)
 for name,v in ip.items():need(g['pins'].get(name)==v,'exact complete child input registry');bound(Path(name))
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two distinct child SOURCE reviews')
 for r in g['sourceReviews']:
  q=json.loads(pin(r['path'],r));need(q['status']=='PASS_SOURCE_ONLY_FIXED_FILEIO_CAPTURE_CONTROLLER_FIXTURE' and q['sourcePinsSHA256']==H(bound(F/'source-pins.json')) and q['driverSHA256']==sp['run.py']['sha256'],'exact child SOURCE reviews')
 sr=g['supervisorReview'];q=json.loads(pin(sr['path'],sr));need(q['status']=='PASS_SOURCE_ONLY_ONE_FIXED_FILEIO_FIXTURE_SUPERVISOR_V2' and q['supervisorSHA256']==g['supervisorSHA256'],'exact independent supervisor review')
 need(pr['maximumDriverLaunches']==1 and pr['noRetry']is True and pr['rootOuterWallSeconds']==10 and pr['rootReapSeconds']==5,'fixed launch/deadlines')
 argv=pr['fixedArgv'];env=pr['fixedSuppliedEnvironment'];need(argv==[pr['interpreter']['path'],str(F/'run.py')] and len(env)==8,'fixed argv/env scope');bound(Path(argv[0]));bound(Path(argv[1]))
 O=D/'run-outputs';need(not O.exists(),'fresh no retry output');O.mkdir();p=None;failure=None;killed=False;rc=None;waitUncertain=False;waitEntered=False;started=time.monotonic()
 with (O/'stdout').open('xb',buffering=0)as out,(O/'stderr').open('xb',buffering=0)as err:
  try:
   p=subprocess.Popen(argv,cwd=F,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,preexec_fn=install_limits)
   (O/'started.json').write_text(json.dumps({'pid':p.pid,'argv':argv,'deadlineSeconds':10,'reapSeconds':5})+'\n')
   waitEntered=True
   try:rc=p.wait(timeout=max(.001,10-(time.monotonic()-started)))
   except subprocess.TimeoutExpired:
    failure='outer10s';p.kill();killed=True
    try:rc=p.wait(timeout=5)
    except BaseException as ex:waitUncertain=True;_uncertain_child=p;failure+=';reap:'+repr(ex)
   except BaseException as ex:waitUncertain=True;_uncertain_child=p;failure=repr(ex)
  except BaseException as ex:
   failure=repr(ex)
   if p is not None and not waitEntered:
    try:p.kill();killed=True;waitEntered=True;rc=p.wait(timeout=5)
    except BaseException as cleanup:waitUncertain=True;_uncertain_child=p;failure+=';cleanup:'+repr(cleanup)
   elif p is not None and rc is None:waitUncertain=True;_uncertain_child=p
 q={'status':'CLOSED0_FIXED_FIXTURE_DRIVER_ONLY'if rc==0 and failure is None else'FAIL_FIXED_FIXTURE_DRIVER','pid':None if p is None else p.pid,'returncode':rc,'terminal':rc is not None and not waitUncertain,'waitUncertain':waitUncertain,'failure':failure,'killedDirectChild':killed,'elapsedSeconds':time.monotonic()-started,'driverLaunches':int(p is not None),'nativeLaunches':0,'fixtureContainsPopen':False,'explicitGroupAPICalls':0,'noExplicitSignalOrWaitAfterUncertainWait':True,'resourcePolicy':{'FSIZE':[65536,65536],'CPU':[10,11],'wall':10,'reap':5},'raw':{}}
 for name in ['stdout','stderr']:
  pth=O/name;need(pth.stat().st_size<=65536,'raw bounded')
  if not q['terminal']:q['raw'][name]={'bytes':pth.stat().st_size,'sha256':None,'activeWriterHashUnavailable':True}
  else:
   b=pth.read_bytes();q['raw'][name]={'bytes':len(b),'sha256':H(b)}
 (O/'terminal.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q));need(q['status']=='CLOSED0_FIXED_FIXTURE_DRIVER_ONLY','one attempt failed')
if __name__=='__main__':need(len(sys.argv)==2,'GO path');main(sys.argv[1])
