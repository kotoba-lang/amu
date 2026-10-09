"""Draft fixed wrapper: named limits then exact native-loader exec. Import inert."""
from pathlib import Path
import os,sys,json,resource,hashlib,stat

def target(before,soft,hard):
 s,h=before;inf=resource.RLIM_INFINITY
 # Required loader CPU soft30/hard31 must not raise finite inherited limits.
 assert h==inf or h>=hard,'inherited hard below exact policy'
 assert s==inf or s>=soft,'inherited soft below exact policy'
 return (soft,hard)
D=Path(__file__).resolve().parent
def checked(p,v):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink()and a.st_size==v['bytes']and a.st_size<=384*1024**2
 b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 assert hashlib.sha256(b).hexdigest()==v['sha256'];return str(p)
def allowed(argv,pr):return argv in [row['nativeArgv']for row in pr['cases']]
def runtime_case(argv,pr,row):
 from loader_grammar import interpretation
 assert interpretation(argv)=={'typedI64':[row['profile']],'guestArgv':None,'effectiveArgc':7}
 assert type(row['profile'])is int and row['profile']>=0 and row['arm']in ['OFF','ON'] and row['arity']==1
 assert argv==[pr['loader'],row['native']['path'],str(row['offset']),'1','aarch64','-',str(row['profile'])]
 assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='16777216' and pr['zeroCapabilityGrants']=='-' and pr['C2']is False
 assert all(pr['environment'][k]==v for k,v in {'KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_STRUCTURED_REPORT':'1','KEXE_ARENA_USE':'1','KEXE_RESULT_TYPE':'i64'}.items())
 return True
def admit(argv,pr,seal,sp,sealSHA):
 assert set(seal)=={'format','index','label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source','rootGO','sourcePinsSHA256','preregistrationSHA256'}
 assert seal['format']==pr['invocationSealVersion'] and seal['nativeArgv']==argv
 rows=[(i+1,row)for i,row in enumerate(pr['cases'])if row['nativeArgv']==argv];assert len(rows)==1
 index,row=rows[0];assert seal['index']==index
 for k in ['label','workload','arm','profile','symbol','offset','arity','native','container','source']:assert seal[k]==row[k]
 runtime_case(argv,pr,row)
 assert seal['sourcePinsSHA256']==hashlib.sha256((D/'source-pins.json').read_bytes()).hexdigest() and seal['preregistrationSHA256']==sp['preregistration.json']['sha256']
 checked(seal['rootGO']['path'],seal['rootGO']);go=json.loads(Path(seal['rootGO']['path']).read_bytes());assert go['status']==pr['rootGOStatus'] and go['sourcePinsSHA256']==seal['sourcePinsSHA256'] and go['preregistrationSHA256']==seal['preregistrationSHA256'] and go['C2']is False and go['maximumLoaderCalls']==10 and go['runtimeGuestAuthorized']is True and go['timingAuthorized']is False
 for k in ['native','container','source']:checked(row[k]['path'],row[k])
 from run import container
 payload,exports=container(Path(row['container']['path']).read_bytes())
 assert payload==Path(row['native']['path']).read_bytes() and (row['symbol'],row['offset'],1)in exports
 return True
def environment_admission(supplied,observed):
 required=set(supplied);extra=set(observed)-required
 assert len(required)==17 and required<=set(observed),'exact supplied keys present'
 assert all(observed[k]==supplied[k]for k in required),'supplied values unchanged'
 assert extra<= {'__CF_USER_TEXT_ENCODING'},'only named Python runtime metadata permitted'
 return {'stage':'environment-admission','suppliedKeyNames':sorted(required),'runtimeExtraKeyNames':sorted(extra),'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':sorted(required),'nativeExecEnvironmentExact':True}
def main(fd,sealSHA,argv):
 sp=json.loads((D/'source-pins.json').read_bytes())
 checked(D/'preregistration.json',sp['preregistration.json']);checked(D/'launch-wrapper.py',sp['launch-wrapper.py']);checked(D/'run.py',sp['run.py']);checked(D/'loader_grammar.py',sp['loader_grammar.py'])
 pr=json.loads((D/'preregistration.json').read_bytes());assert allowed(argv,pr),'only exact preregistered native argv'
 checked(pr['loaderArtifact']['path'],pr['loaderArtifact']);checked(pr['interpreter']['path'],pr['interpreter'])
 row=next(row for row in pr['cases']if row['nativeArgv']==argv);sealPath=Path(pr['freshOutputRoot'])/(row['label']+'.admission.json');sealStat=sealPath.lstat();assert stat.S_ISREG(sealStat.st_mode)and not sealPath.is_symlink()and 0<sealStat.st_size<=4096;checked(sealPath,{'bytes':sealStat.st_size,'sha256':sealSHA});sealBytes=sealPath.read_bytes();assert hashlib.sha256(sealBytes).hexdigest()==sealSHA
 seal=json.loads(sealBytes);admit(argv,pr,seal,sp,sealSHA)
 environmentWitness=environment_admission(pr['environment'],dict(os.environ))
 total=0
 def emit(q):
  nonlocal total
  b=(json.dumps(q,sort_keys=True)+'\n').encode();assert total+len(b)<=65536
  view=memoryview(b)
  while view:n=os.write(fd,view);assert n>0;view=view[n:]
  os.fsync(fd);total+=len(b)
 emit(environmentWitness)
 for idx,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)],1):
  before=None;want=None
  try:
   kind=getattr(resource,name);before=resource.getrlimit(kind);want=target(before,soft,hard)
   emit({'index':idx,'limit':name,'stage':'before','before':before,'desired':want})
   resource.setrlimit(kind,want);after=resource.getrlimit(kind);assert after==want
   emit({'index':idx,'limit':name,'stage':'outcome','outcome':'installed','readback':after})
  except BaseException as ex:
   emit({'index':idx,'limit':name,'stage':'outcome','outcome':'failure','before':before,'desired':want,'exception':repr(ex)});return 78
 emit({'stage':'exec-ready','argv':argv,'ASSetterRequested':False,'CPUGraceHardSeconds':31})
 os.set_inheritable(fd,False);os.execve(argv[0],argv,dict(pr['environment']))
 return 79
if __name__=='__main__':
 assert len(sys.argv)>=7 and sys.argv[1]=='--journal-fd'and sys.argv[3]=='--admission-sha'and sys.argv[5]=='--'
 assert len(sys.argv[4])==64 and all(c in '0123456789abcdef'for c in sys.argv[4])
 sys.exit(main(int(sys.argv[2]),sys.argv[4],sys.argv[6:]))
