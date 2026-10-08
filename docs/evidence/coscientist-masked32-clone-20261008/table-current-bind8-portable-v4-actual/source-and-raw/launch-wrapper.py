"""Draft fixed wrapper: named limits then exact native-loader exec. Import inert."""
from pathlib import Path
import os,sys,json,resource,hashlib,stat

def target(before,soft,hard):
 s,h=before;inf=resource.RLIM_INFINITY
 # Required loader CPU soft1800/hard1801 must not raise finite inherited limits.
 assert h==inf or h>=hard,'inherited hard below exact policy'
 assert s==inf or s>=soft,'inherited soft below exact policy'
 return (soft,hard)
D=Path(__file__).resolve().parent
def checked(p,v):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink()and a.st_size==v['bytes']and a.st_size<=384*1024**2
 b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 assert hashlib.sha256(b).hexdigest()==v['sha256'];return str(p)
def allowed(argv,pr):return argv in [row['nativeArgv']for row in pr['orderedChildren']]
def environment_admission(supplied,observed):
 required=set(supplied);extra=set(observed)-required
 assert len(required)==17 and required<=set(observed),'exact supplied keys present'
 assert all(observed[k]==supplied[k]for k in required),'supplied values unchanged'
 assert extra<= {'__CF_USER_TEXT_ENCODING'},'only named Python runtime metadata permitted'
 return {'stage':'environment-admission','suppliedKeyNames':sorted(required),'runtimeExtraKeyNames':sorted(extra),'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':sorted(required),'nativeExecEnvironmentExact':True}
def main(fd,argv):
 sp=json.loads((D/'source-pins.json').read_bytes())
 checked(D/'preregistration.json',sp['preregistration.json']);checked(D/'launch-wrapper.py',sp['launch-wrapper.py'])
 pr=json.loads((D/'preregistration.json').read_bytes());assert allowed(argv,pr),'only exact preregistered native argv'
 checked(pr['loader']['path'],pr['loader']);checked(pr['interpreter']['path'],pr['interpreter'])
 producer=argv[1]
 if producer==pr['producer']['path']:checked(producer,pr['producer'])
 else:
  generated=json.loads((D/'run-outputs/generated-pins.json').read_bytes());checked(producer,generated[producer])
 environmentWitness=environment_admission(pr['environment'],dict(os.environ))
 total=0
 def emit(q):
  nonlocal total
  b=(json.dumps(q,sort_keys=True)+'\n').encode();assert total+len(b)<=65536
  view=memoryview(b)
  while view:n=os.write(fd,view);assert n>0;view=view[n:]
  os.fsync(fd);total+=len(b)
 emit(environmentWitness)
 for idx,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):
  before=None;want=None
  try:
   kind=getattr(resource,name);before=resource.getrlimit(kind);want=target(before,soft,hard)
   emit({'index':idx,'limit':name,'stage':'before','before':before,'desired':want})
   resource.setrlimit(kind,want);after=resource.getrlimit(kind);assert after==want
   emit({'index':idx,'limit':name,'stage':'outcome','outcome':'installed','readback':after})
  except BaseException as ex:
   emit({'index':idx,'limit':name,'stage':'outcome','outcome':'failure','before':before,'desired':want,'exception':repr(ex)});return 78
 emit({'stage':'exec-ready','argv':argv,'ASSetterRequested':False,'CPUGraceHardSeconds':1801})
 os.set_inheritable(fd,False);os.execve(argv[0],argv,dict(pr['environment']))
 return 79
if __name__=='__main__':
 assert len(sys.argv)>=5 and sys.argv[1]=='--journal-fd'and sys.argv[3]=='--'
 sys.exit(main(int(sys.argv[2]),sys.argv[4:]))
