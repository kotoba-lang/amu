"""Inert C bootstrap registration. Main requires exact reviewed GO; no guest authority."""
from pathlib import Path
import hashlib,json,stat,shlex,struct,os
D=Path(__file__).resolve().parent
GO_KEYS={'status','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','taskRoot','hostBinding','maximumChildCalls','guestAuthorized','consumerAuthorized','timingAuthorized','noRetry','C2','C19Proofs','procLibraryAlias','expectedDynamicLoadNames'}
HOST_KEYS={'machine','compiler','interpreter','linker','sdkAlias','sdk','resourceDirectory','libraryPins'}
def need(v,m):
 if not v:raise AssertionError(m)
def unique_object(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,'duplicate metadata key');d[k]=v
 return d
def load(p):return json.loads(Path(p).read_bytes(),object_pairs_hook=unique_object)
def receipt(p,maximum=536870912):
 p=Path(p);a=p.lstat();need(stat.S_ISREG(a.st_mode)and not p.is_symlink()and 0<=a.st_size<=maximum,'regular bounded pin');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable pin');return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def check(p,r):need(receipt(p)=={k:r[k]for k in('bytes','sha256')},'exact pin '+str(p))
def save(p,obj):
 b=(json.dumps(obj,indent=2)+'\n').encode();need(len(b)<=8388608,'metadata cap');q=Path(str(p)+'.pending')
 with q.open('xb',buffering=0)as f:
  v=memoryview(b)
  while v:
   n=f.write(v);need(type(n)is int and 0<n<=len(v),'metadata short write');v=v[n:]
  os.fsync(f.fileno())
 os.replace(q,p)
def scope(pr,ip,recipes):
 need(type(ip)is dict and type(recipes)is list,'registry shape')
 for k in ['exactInputFiles','exactInputLogicalBytes','maximumChildCalls','dependencyCalls','buildCalls','guestCalls','consumerCalls','timingCalls']:need(type(pr[k])is int,'integer scope '+k)
 need(pr['maximumInputFiles']==128 and pr['maximumInputBytes']==8388608 and pr['maximumDynamicHeaders']==4096 and pr['maximumDynamicHeaderBytes']==67108864 and pr['maximumSingleHeaderBytes']==8388608 and pr['maximumRawBytesPerStream']==1048576 and pr['maximumArtifactBytes']==16777216 and pr['controlledOutputReservationBytes']==1073741824,'fixed host bounds')
 need(len(ip)==pr['exactInputFiles']==108 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=8388608,'108 targeted source/image inputs')
 need(pr['maximumChildCalls']==38 and pr['dependencyCalls']==pr['buildCalls']==19 and pr['guestCalls']==pr['consumerCalls']==pr['timingCalls']==0 and pr['C2']is False and pr['noRetry']is True,'consumer build only')
 need(len(recipes)==19 and len({r['workload']for r in recipes})==19,'all19')
 for r in recipes:
  w=r['workload'];need(r['argvTemplate']==['$RESOLVED_CLANG','-std=c11','-O2','-DKEXE_OWNERSHIP_DIAGNOSTIC_V3','-I','$TASK_ROOT/build/'+w,'$TASK_ROOT/source/consumer/timing-loader.c','-o','$FRESH_BUILD/'+w+'/consumer','-lproc'],'exact consumer recipe')
 need(pr['maximumCampaignSeconds']==7200 and pr['dependencyTimeoutSeconds']==60 and pr['buildTimeoutSeconds']==180 and pr['cleanupSeconds']==30,'fixed compiler budget')
 return True
def argv(recipe,root,out,host,dep=False):
 subst={'$RESOLVED_CLANG':host['compiler']['path'],'$TASK_ROOT':str(root),'$FRESH_BUILD':str(out)}
 a=[]
 for t in recipe['argvTemplate']:
  for k,v in subst.items():t=t.replace(k,v)
  a.append(t)
 if dep:a=a[:-3];a.insert(4,'-M')
 return a
def dependencies(raw,root,host,ip):
 need(type(raw)is bytes and 0<len(raw)<=1048576 and b'\0'not in raw,'dependency raw')
 text=raw.decode('ascii').replace('\\\n',' ');lines=text.splitlines();need(0<len(lines)<=3,'one target per original translation unit')
 names=[]
 for line in lines:
  need(line.count(':')==1,'dependency target grammar');target,body=line.split(':',1);need(target.endswith('.o')and'/'not in target,'simple object target');names.extend(shlex.split(body))
 need(0<len(names)<=4096,'finite dependencies')
 got=set()
 for n in names:
  p=Path(n);p=p if p.is_absolute()else root/p;p=p.resolve(strict=True)
  if p.is_relative_to(root):need(str(p.relative_to(root))in ip or str(p)in generated_paths(root),'owned dependency')
  else:need(p.is_relative_to(Path(host['sdk']))or p.is_relative_to(Path(host['resourceDirectory'])),'SDK/resource read domain')
  got.add(str(p))
 need(len(got)<=4096,'canonical dependency count');return sorted(got)
def diagnostic(raw):
 need(len(raw)<=1048576 and b'\0'not in raw,'diagnostic raw');t=raw.decode('utf8');need('error:'not in t,'no error diagnostic');return bool(raw)
def macho(raw,expectedLoads):
 need(expectedLoads==['/usr/lib/libSystem.B.dylib'],'selected merged System/proc contract')
 need(32<=len(raw)<=16777216 and raw[:4]==b'\xcf\xfa\xed\xfe'and struct.unpack_from('<I',raw,4)[0]==0x100000c and struct.unpack_from('<I',raw,12)[0]==2,'arm64 consumer executable')
 n,size=struct.unpack_from('<II',raw,16);need(0<n<=128 and size<=65536 and 32+size<=len(raw),'load commands');off=32;loads=[]
 for i in range(n):
  kind,z=struct.unpack_from('<II',raw,off);need(z>=8 and z%8==0 and off+z<=32+size,'command length')
  if kind==12:
   at=struct.unpack_from('<I',raw,off+8)[0];need(24<=at<z,'dylib name');loads.append(raw[off+at:off+z].split(b'\0',1)[0].decode('ascii'))
  need(kind not in {0x18,0x80000018,0x1f,0x8000001f,0x20,0x23,0x80000023,0x8000001c,0x27,0x2d},'no extra dynamic search/load roles');off+=z
 need(off==32+size and sorted(loads)==sorted(expectedLoads),'System/proc load names only');return loads

def generated_paths(root):
 return {str(root/'build'/r['workload']/'timing-packet-generated.h')for r in load(D/'packet.json')['entries']}|{str(root/'inputs'/r['workload']/'C.dylib')for r in load(D/'packet.json')['entries']}
def prepared(root,g,write=False):
 from prepare import packet,c_proofs,receipt
 from header import header
 rows=packet(root);proofs=c_proofs(root,rows,g['C19Proofs']);pins={}
 for r in rows:
  w=r['workload'];q=proofs[w];c=Path(q['artifact']['path']).read_bytes();h=header(r,Path(r['OFF']['native']['path']).read_bytes(),Path(r['ON']['native']['path']).read_bytes(),c,q)
  for p,b in [(root/'build'/w/'timing-packet-generated.h',h),(root/'inputs'/w/'C.dylib',c)]:
   if write:
    need(not p.exists(),'fresh generated header/C materialization');p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb',buffering=0)as f:
     view=memoryview(b)
     while view:
      n=f.write(view);need(type(n)is int and 0<n<=len(view),'full generated write');view=view[n:]
     os.fsync(f.fileno())
    p.chmod(0o400)
   need(p.read_bytes()==b,'complete reconstructed generated bytes');pins[str(p)]={k:receipt(p)[k]for k in('bytes','sha256')}
 return pins
def environment_admission(expected,observed):
 need(type(expected)is dict and type(observed)is dict and len(expected)==7,'seven supplied environment keys')
 required=set(expected);extra=set(observed)-required
 need(required<=set(observed)and all(observed[k]==expected[k]for k in required),'required environment unchanged')
 need(extra<={'__CF_USER_TEXT_ENCODING'},'only named optional runtime metadata')
 return {'suppliedKeyNames':sorted(required),'runtimeExtraKeyNames':sorted(extra),'missingKeyNames':[],'changedExpectedKeyNames':[],'execEnvironmentExact':True}

def proc_library_selection(g,h,resolve,verify):
 a=g['procLibraryAlias'];need(type(a)is dict and set(a)=={'alias','canonicalTargetPin'},'explicit proc alias contract')
 alias=Path(h['sdk'])/'usr/lib/libproc.tbd';target=Path(h['sdk'])/'usr/lib/libSystem.B.tbd';r=a['canonicalTargetPin']
 need(a['alias']==str(alias)and r=={'path':str(target),'bytes':337542,'sha256':'607d9993892c95703a0909ff06f5843058ff1ec30b08337f42ab056d9bf325ea'},'selected actual SDK merged proc/System identity')
 need(resolve(alias)==target and r in h['libraryPins'],'canonical merged alias pinned')
 verify(target,r);need(g['expectedDynamicLoadNames']==['/usr/lib/libSystem.B.dylib'],'selected merged MachO load contract');return True

def proc_library(g,h):return proc_library_selection(g,h,lambda p:p.resolve(strict=True),check)

def go_guard(g,pr,sp,ip):
 need(set(g)==GO_KEYS and g['status']==pr['rootGOStatus'],'exact GO schema')
 need(type(g['maximumChildCalls'])is int and g['maximumChildCalls']==38 and all(g[k]is False for k in('guestAuthorized','consumerAuthorized','timingAuthorized','C2'))and g['noRetry']is True,'no guests/timing/retry')
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('build-preregistration.json','preregistrationSHA256'),('build.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'exact reviewed GO')
 need(type(g['sourceReviews'])is list and len(g['sourceReviews'])==2 and len({x['path']for x in g['sourceReviews']})==2,'distinct reviews')
 for r in g['sourceReviews']:
  check(r['path'],r);q=load(r['path']);need(q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256']and q['preregistrationSHA256']==g['preregistrationSHA256']and q['driverSHA256']==g['driverSHA256'],'bound review')
 h=g['hostBinding'];need(set(h)==HOST_KEYS and h['machine']=='arm64','host binding')
 need(Path(h['compiler']['path'])==Path('/Library/Developer/CommandLineTools/usr/bin/clang')and Path(h['linker']['path'])==Path('/Library/Developer/CommandLineTools/usr/bin/ld'),'exact CLT tools')
 need(Path(h['sdkAlias']).resolve(strict=True)==Path(h['sdk'])and Path(h['sdk']).is_relative_to('/Library/Developer/CommandLineTools/SDKs'),'SDK alias')
 need(Path(h['resourceDirectory']).is_relative_to('/Library/Developer/CommandLineTools/usr/lib/clang'),'resource directory')
 for k in('compiler','interpreter','linker'):check(h[k]['path'],h[k])
 need(0<len(h['libraryPins'])<=128,'canonical library pins')
 proc_library(g,h)
 for r in h['libraryPins']:need(Path(r['path']).is_relative_to(h['sdk']),'SDK library');check(r['path'],r)
 root=Path(g['taskRoot']);need(root.resolve()==root and D==root/'source/current17-phase','canonical installed layout')
 for n,r in sp.items():check(D/n,r)
 for n,r in ip.items():check(root/n,r)
 from prepare import packet,c_proofs
 c_proofs(root,packet(root),g['C19Proofs'])
 return root,h

def main(go_path):
 import subprocess,time,platform
 gp=Path(go_path);g=load(gp);gr=receipt(gp);pr=load(D/'build-preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');recipes=load(D/'recipes.json')['commands'];scope(pr,ip,recipes);root,h=go_guard(g,pr,sp,ip)
 need(platform.system()=='Darwin'and platform.machine()=='arm64','actual host architecture')
 O=root/pr['outputRelative'];need(not O.exists(),'fresh noRetry output');O.mkdir();(O/'tmp').mkdir();deadline=time.monotonic()+pr['maximumCampaignSeconds'];rows=[];dynamic={};generated={};artifacts=[];ok=False
 env=pr['environment']|{'TMPDIR':str(O/'tmp'),'SDKROOT':h['sdk']}
 def guard():
  check(gp,gr);scope(pr,ip,recipes);go_guard(g,pr,sp,ip)
  for p,r in dynamic.items():check(p,r)
  for p,r in generated.items():check(p,r)
 try:
  generated=prepared(root,g,write=True);save(O/'generated-pins.json',generated)
  for phase in('dependencies','build'):
   for recipe in recipes:
    guard();n=len(rows)+1;need(n<=38,'call ceiling');timeout=pr['dependencyTimeoutSeconds']if phase=='dependencies'else pr['buildTimeoutSeconds'];need(time.monotonic()+timeout+30<=deadline,'absolute campaign')
    work=recipe['workload'];out=O/work;out.mkdir(exist_ok=True);a=argv(recipe,root,O,h,phase=='dependencies');r={'index':n,'phase':phase,'workload':work,'argv':a,'pid':None,'state':'not-started'};rows.append(r);save(O/'attempts.json',rows)
    fo=O/f'{n:02d}.stdout';fe=O/f'{n:02d}.stderr';proc=None;entered=False;closed=False
    with fo.open('xb',buffering=0)as stdout,fe.open('xb',buffering=0)as stderr:
     try:
      proc=subprocess.Popen([h['interpreter']['path'],str(D/'build-limit-exec.py'),str(gp),str(n)],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,close_fds=True)
      r.update(pid=proc.pid,state='started');save(O/'attempts.json',rows);entered=True
      try:rc=proc.wait(timeout=timeout)
      except subprocess.TimeoutExpired:
       r['timeout']=True;proc.kill();rc=proc.wait(timeout=min(30,max(.001,deadline-time.monotonic())))
      r.update(returncode=rc,directWaitCount=1,reaped=True,state='terminal');closed=True
     except BaseException as exc:
      r['failure']=repr(exc)
      if proc is not None and not entered:
       try:proc.kill();rc=proc.wait(timeout=min(30,max(.001,deadline-time.monotonic())));r.update(returncode=rc,directWaitCount=1,reaped=True,state='terminal-refused');closed=True
       except BaseException as ce:r['cleanupFailure']=repr(ce)
      if not closed:r['state']='closure-uncertain-no-output-hashes-no-further-operations'
      raise
    need(closed and r['returncode']==0 and not r.get('timeout'),'normal direct wait only; timeout tree unqualified')
    resourcePath=O/f'{n:02d}.resources.json';resourceRow=load(resourcePath);need(resourceRow['index']==n and resourceRow['argv']==a and resourceRow['environment']==env and resourceRow['noLimitEnlargement']is True and resourceRow['GO']==dict(path=str(gp),**gr),'exact installed resources')
    witness=resourceRow['environmentWitness'];need(witness['execEnvironmentExact']is True and witness['suppliedKeyNames']==sorted(env)and witness['runtimeExtraKeyNames']in([],['__CF_USER_TEXT_ENCODING'])and witness['missingKeyNames']==witness['changedExpectedKeyNames']==[],'named runtime metadata only, exact forwarded env')
    for name,cap in [('RLIMIT_CPU',(180,181)),('RLIMIT_FSIZE',(16777216,16777216)),('RLIMIT_CORE',(0,0))]:
     actual=resourceRow['limits'][name]['actual'];need(len(actual)==2 and all(type(x)is int and 0<=x<=y for x,y in zip(actual,cap))and actual[0]<=actual[1],'lower limit readback')
    r['resources']=dict(path=str(resourcePath),**receipt(resourcePath))
    r['stdout']=dict(path=str(fo),**receipt(fo,pr['maximumRawBytesPerStream']));r['stderr']=dict(path=str(fe),**receipt(fe,pr['maximumRawBytesPerStream']));diagnostic(fe.read_bytes())
    if phase=='dependencies':
     ds=dependencies(fo.read_bytes(),root,h,ip);need(str(root/'source/consumer/timing-loader.c')in ds and str(root/'build'/work/'timing-packet-generated.h')in ds,'own consumer+header dynamic closure')
     for p in ds:dynamic[p]=receipt(p,pr['maximumSingleHeaderBytes'])
     need(len(dynamic)<=pr['maximumDynamicHeaders']and sum(x['bytes']for x in dynamic.values())<=pr['maximumDynamicHeaderBytes'],'union dynamic closure bound');r['dependencies']=ds;save(O/'dynamic-pins.json',dynamic)
    else:
     need(fo.read_bytes()==b'','build stdout empty');p=out/'consumer';ar=dict(path=str(p),**receipt(p,pr['maximumArtifactBytes']));macho(p.read_bytes(),g['expectedDynamicLoadNames']);artifacts.append({'workload':work,'symbol':recipe['cSymbol'],'consumerABI':'ARM_n_calls_warmup_5ARGV_V1','artifact':ar,'compileArgv':a,'dependencyCallIndex':recipes.index(recipe)+1,'buildCallIndex':n,'sourcePins':{k:v for k,v in ip.items()},'dynamicDependencyPins':{p:dynamic[p]for p in rows[recipes.index(recipe)]['dependencies']}})
    guard();save(O/f'{n:02d}.closure.json',r);save(O/'attempts.json',rows)
  need(len(rows)==38 and len(artifacts)==19,'complete fixed phase');guard();save(O/'terminal.json',{'directChildrenClosed':38,'allDirectChildrenReaped':True,'failure':False,'compilerDescendantClosure':'trusted normal Clang driver completion only; no arbitrary process-tree proof','noRetry':True});guard()
  save(O/'report.json',{'status':pr['completionStatus'],'GO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'hostBinding':h,'closedCompilerCalls':38,'consumerBuildCalls':19,'guestCalls':0,'artifacts':artifacts,'terminal':dict(path=str(O/'terminal.json'),**receipt(O/'terminal.json')),'attempts':dict(path=str(O/'attempts.json'),**receipt(O/'attempts.json')),'dynamicPins':dict(path=str(O/'dynamic-pins.json'),**receipt(O/'dynamic-pins.json')),'generatedPins':dict(path=str(O/'generated-pins.json'),**receipt(O/'generated-pins.json')),'independentConsumerAdmission':'HOLD until separately audited actual consumer19 proofs before342','cleanBuildClaimed':False,'performanceQualified':False,'C2':False,'noRetry':True});ok=True
 finally:
  if not ok:save(O/'failure.json',{'status':'FAILED_CURRENT17_CONSUMER_BUILD38_NO_RETRY','attempts':rows,'guestCalls':0,'completionMarkerAbsent':not(O/'report.json').exists(),'unclosedOutputNeverHashed':True})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact GO');main(sys.argv[1])
