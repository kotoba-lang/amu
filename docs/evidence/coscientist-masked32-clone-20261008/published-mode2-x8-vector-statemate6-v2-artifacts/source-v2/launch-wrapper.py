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
def allowed(argv,pr):return argv in [row['nativeArgv']for row in pr['cases']]
def admit(argv,pr,seal,sp,sealSHA):
 from run import compiler_case,container,existing_candidate_guard
 assert set(seal)=={'format','index','label','nativeArgv','producer','producerContainer','existingProducerProof','input','outputPath','rootGO','sourcePinsSHA256','preregistrationSHA256'}
 assert seal['format']==pr['invocationSealVersion']and seal['nativeArgv']==argv
 rows=[(i+1,c)for i,c in enumerate(pr['cases'])if c['nativeArgv']==argv];assert len(rows)==1
 index,c=rows[0];assert seal['index']==index and seal['label']==c['label']and seal['outputPath']==c['outputPath'];compiler_case(argv,pr,c)
 assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off'and pr['environment']['KEXE_COMMAND']=='1'and pr['environment']['KEXE_CAP_RESOURCES_35']==pr['freshOutputRoot']
 assert seal['sourcePinsSHA256']==hashlib.sha256((D/'source-pins.json').read_bytes()).hexdigest()and seal['preregistrationSHA256']==sp['preregistration.json']['sha256']
 checked(seal['rootGO']['path'],seal['rootGO']);go=json.loads(Path(seal['rootGO']['path']).read_bytes());assert go['status']==pr['rootGOStatus']and go['maximumLoaderCalls']==6 and go['sourcePinsSHA256']==seal['sourcePinsSHA256']and go['preregistrationSHA256']==seal['preregistrationSHA256']and go['C2']is False and go['runtimeGuestAuthorized']is False and go['timingAuthorized']is False and go['outerHostLaunchRequiresEscalation']is True
 on=index>=3;nr=pr['candidateCompiler']if on else pr['offCompiler'];kr=pr['candidateCompilerContainer']if on else pr['offCompilerContainer'];proof=pr['candidateActualProof']if on else pr['TCActualProof']
 assert seal['producer']==nr and argv[1]==nr['path']and seal['producerContainer']==kr and seal['existingProducerProof']==proof
 checked(nr['path'],nr);checked(kr['path'],kr);checked(proof['path'],proof);payload,exports=container(Path(kr['path']).read_bytes());assert payload==Path(nr['path']).read_bytes()and exports==[('main',0,0)]
 if on:existing_candidate_guard(pr)
 else:
  q=json.loads(Path(proof['path']).read_bytes());assert q['status']==pr['TCActualProofStatus']and q['G0Native']==nr and q['G0Container']==kr
 assert seal['input']['path']==argv[8]and 0<seal['input']['bytes']<=4194560;checked(argv[8],seal['input'])
 if c['kind']=='compile':
  src=pr['statemateEntry']['source']if index==5 else pr['fixtureSource'];assert {k:seal['input'][k]for k in ['bytes','sha256']}=={k:src[k]for k in ['bytes','sha256']}
 else:container(Path(argv[8]).read_bytes())
 assert not Path(c['outputPath']).exists()and not Path(c['outputPath']).is_symlink()
 return True
def environment_admission(supplied,observed):
 required=set(supplied);extra=set(observed)-required
 assert len(required)==17 and required<=set(observed),'exact supplied keys present'
 assert all(observed[k]==supplied[k]for k in required),'supplied values unchanged'
 assert extra<= {'__CF_USER_TEXT_ENCODING'},'only named Python runtime metadata permitted'
 return {'stage':'environment-admission','suppliedKeyNames':sorted(required),'runtimeExtraKeyNames':sorted(extra),'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':sorted(required),'nativeExecEnvironmentExact':True}
def main(fd,sealSHA,argv):
 sp=json.loads((D/'source-pins.json').read_bytes())
 checked(D/'preregistration.json',sp['preregistration.json']);checked(D/'launch-wrapper.py',sp['launch-wrapper.py']);checked(D/'run.py',sp['run.py']);checked(D/'artifact_admission.py',sp['artifact_admission.py']);checked(D/'integration.py',sp['integration.py'])
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
 assert len(sys.argv)>=7 and sys.argv[1]=='--journal-fd'and sys.argv[3]=='--admission-sha'and sys.argv[5]=='--'
 assert len(sys.argv[4])==64 and all(c in '0123456789abcdef'for c in sys.argv[4])
 sys.exit(main(int(sys.argv[2]),sys.argv[4],sys.argv[6:]))
