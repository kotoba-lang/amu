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
 assert set(seal)=={'format','index','label','nativeArgv','producer','producerContainer','input','outputPath','rootGO','sourcePinsSHA256','preregistrationSHA256'}
 assert seal['format']==pr['invocationSealVersion'] and seal['nativeArgv']==argv
 rows=[(i+1,row)for i,row in enumerate(pr['cases'])if row['nativeArgv']==argv];assert len(rows)==1
 index,row=rows[0];assert seal['index']==index and seal['label']==row['label'] and seal['outputPath']==row['outputPath']
 assert argv[:1]==[pr['loader']] and argv[2:7]==['0','0','aarch64','35,37,38,39','--']
 assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off' and pr['environment']['KEXE_COMMAND']=='1' and pr['environment']['KEXE_CAP_RESOURCES_35']==pr['freshOutputRoot']
 assert seal['sourcePinsSHA256']==hashlib.sha256((D/'source-pins.json').read_bytes()).hexdigest() and seal['preregistrationSHA256']==sp['preregistration.json']['sha256']
 checked(seal['rootGO']['path'],seal['rootGO']);go=json.loads(Path(seal['rootGO']['path']).read_bytes());assert go['status']==pr['rootGOStatus'] and go['sourcePinsSHA256']==seal['sourcePinsSHA256'] and go['preregistrationSHA256']==seal['preregistrationSHA256'] and go['C2'] is False
 producer=argv[1];assert seal['producer']['path']==producer and 0<seal['producer']['bytes']<=4194304;checked(producer,seal['producer'])
 expectedContainer=pr['candidateContainer']if producer==pr['producer']else str(Path(producer).with_suffix('.kseed'))
 assert seal['producerContainer']['path']==expectedContainer and 0<seal['producerContainer']['bytes']<=4194560
 checked(expectedContainer,seal['producerContainer'])
 import re
 raw=Path(expectedContainer).read_bytes();m=re.match(rb'KSEED1 ([1-9][0-9]{0,9}) 1\nmain 0 0\n\n',raw);assert m is not None
 payload=raw[m.end():];assert 0<len(payload)<=4194304 and len(payload)==int(m[1]) and payload==Path(producer).read_bytes()
 if producer==pr['producer']:assert seal['producer']['sha256']==pr['producerSHA256']
 else:
  assert producer==str(Path(pr['freshOutputRoot'])/'memo.bin')
  from producer_guard import validate_producer
  validate_producer(pr,seal['rootGO'],seal['sourcePinsSHA256'],seal['preregistrationSHA256'])
 assert seal['input']['path']==argv[8] and seal['input']['bytes']<=4194560;checked(argv[8],seal['input'])
 if row['kind']=='compile':
  assert argv[7]=='compile' and argv[9:]==['--target','aarch64-macos','--output',row['outputPath']]
  if row['arity']==0:assert seal['input']['sha256']==pr['sourceSHA256']
  else:
   entries=[e for e in pr['entries']if row['label']==e['workload']+'-compile'];assert len(entries)==1 and {k:seal['input'][k]for k in ['bytes','sha256']}=={k:entries[0]['source'][k]for k in ['bytes','sha256']}
 else:assert row['kind']=='extract' and argv[7]=='extract-native' and argv[9:]==['--symbol',row['symbol'],'--output',row['outputPath']]
 assert not Path(row['outputPath']).exists() and not Path(row['outputPath']).is_symlink() and Path(row['outputPath']).parent==Path(pr['freshOutputRoot'])
 return True
def environment_admission(supplied,observed):
 required=set(supplied);extra=set(observed)-required
 assert len(required)==17 and required<=set(observed),'exact supplied keys present'
 assert all(observed[k]==supplied[k]for k in required),'supplied values unchanged'
 assert extra<= {'__CF_USER_TEXT_ENCODING'},'only named Python runtime metadata permitted'
 return {'stage':'environment-admission','suppliedKeyNames':sorted(required),'runtimeExtraKeyNames':sorted(extra),'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':sorted(required),'nativeExecEnvironmentExact':True}
def main(fd,sealSHA,argv):
 sp=json.loads((D/'source-pins.json').read_bytes())
 checked(D/'preregistration.json',sp['preregistration.json']);checked(D/'launch-wrapper.py',sp['launch-wrapper.py'])
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
