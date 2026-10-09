"""Fixed SOURCE wrapper: named limits then exact native-loader exec. Import inert."""
from pathlib import Path
import os,sys,json,resource,hashlib,stat,fcntl

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
def allowed(argv,pr):return argv in [r['nativeArgv']for r in pr['cases']]
def runtime_case(argv,pr,row):
 assert len(argv)==5 and argv==[row['consumer']['path'],row['arm'],str(row['n']),str(row['calls']),'1']
 assert row['arm']in ['OFF','ON','C'] and type(row['n'])is int and row['n']>=0 and row['calls']in [1,2] and type(row['calls'])is int and row['warmup']==1
 assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='16777216' and pr['zeroCapabilityGrants']=='-' and pr['C2']is False
 assert all(pr['environment'][k]==v for k,v in {'KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_STRUCTURED_REPORT':'1','KEXE_ARENA_USE':'1','KEXE_RESULT_TYPE':'i64'}.items())
 return True
def admit(argv,pr,seal,sp,sealSHA):
 from run import load,runtime_registration,go_header,receipt
 assert set(seal)=={'format','index','case','runtimeRegistration','rootGO','sourcePinsSHA256','preregistrationSHA256'}
 assert seal['format']==pr['invocationSealVersion'] and seal['case']['nativeArgv']==argv
 rows=[(i+1,r)for i,r in enumerate(pr['cases'])if r['nativeArgv']==argv];assert len(rows)==1
 index,row=rows[0];assert seal['index']==index and seal['case']==row;runtime_case(argv,pr,row)
 assert seal['sourcePinsSHA256']==hashlib.sha256((D/'source-pins.json').read_bytes()).hexdigest()and seal['preregistrationSHA256']==sp['preregistration.json']['sha256']
 checked(seal['rootGO']['path'],seal['rootGO']);g=load(seal['rootGO']['path']);template=load(D/'preregistration.json');root=go_header(g,template)
 assert g['sourcePinsSHA256']==seal['sourcePinsSHA256'] and g['preregistrationSHA256']==seal['preregistrationSHA256']
 rp=root/template['qualificationOutputsRelative']/'runtime-preregistration.json';assert seal['runtimeRegistration']['path']==str(rp);checked(rp,seal['runtimeRegistration'])
 assert load(rp)==pr==runtime_registration(g,template,root)
 checked(row['consumer']['path'],row['consumer']);return True
def environment_admission(supplied,observed):
 required=set(supplied);extra=set(observed)-required
 assert len(required)==17 and required<=set(observed),'exact supplied keys present'
 assert all(observed[k]==supplied[k]for k in required),'supplied values unchanged'
 assert extra<= {'__CF_USER_TEXT_ENCODING'},'only named Python runtime metadata permitted'
 return {'stage':'environment-admission','suppliedKeyNames':sorted(required),'runtimeExtraKeyNames':sorted(extra),'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':sorted(required),'nativeExecEnvironmentExact':True}
def main(fd,sealSHA,ownershipFD,argv):
 from run import load
 sp=load(D/'source-pins.json')
 for name in sp:checked(D/name,sp[name])
 template=load(D/'preregistration.json');root=Path.cwd();assert root.resolve()==root and D==root/'source/current17-qualification'
 pr=load(root/template['qualificationOutputsRelative']/'runtime-preregistration.json');assert allowed(argv,pr),'only exact342 consumer argv'
 checked(pr['interpreter']['path'],pr['interpreter'])
 row=next(row for row in pr['cases']if row['nativeArgv']==argv);sealPath=Path(pr['freshOutputRoot'])/(row['label']+'.admission.json');sealStat=sealPath.lstat();assert stat.S_ISREG(sealStat.st_mode)and not sealPath.is_symlink()and 0<sealStat.st_size<=4096;checked(sealPath,{'bytes':sealStat.st_size,'sha256':sealSHA});sealBytes=sealPath.read_bytes();assert hashlib.sha256(sealBytes).hexdigest()==sealSHA
 seal=load(sealPath);admit(argv,pr,seal,sp,sealSHA)
 assert type(ownershipFD)is int and ownershipFD>4 and fd!=4 and ownershipFD!=fd
 try:fcntl.fcntl(4,fcntl.F_GETFD)
 except OSError as ex:assert ex.errno==9,'fixed FD4 must be absent'
 else:raise AssertionError('FD4 collision')
 assert fcntl.fcntl(ownershipFD,fcntl.F_GETFL)&os.O_NONBLOCK
 os.dup2(ownershipFD,4,inheritable=True);os.close(ownershipFD)
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
 assert len(sys.argv)>=9 and sys.argv[1]=='--journal-fd'and sys.argv[3]=='--admission-sha'and sys.argv[5]=='--ownership-fd'and sys.argv[7]=='--'
 assert len(sys.argv[4])==64 and all(c in '0123456789abcdef'for c in sys.argv[4])
 sys.exit(main(int(sys.argv[2]),sys.argv[4],int(sys.argv[6]),sys.argv[8:]))
