"""SOURCE-only finite36 actual helper controls. Import inert; explicit root GO."""
from pathlib import Path
import json,hashlib,os,sys,re,signal,subprocess,importlib.util
D=Path(__file__).resolve().parent;O=D/'run-outputs'
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,D/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
V=module('sr_controls_validate','validate.py');A=module('sr_arena_decoder','arena-decoder.py')
H=lambda b:hashlib.sha256(b).hexdigest()
def need(c,s):
 if not c:raise AssertionError(s)
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def pin(p,v):
 p=Path(p);need(p.is_file()and not p.is_symlink()and p.stat().st_size==v['bytes'],'regular pin stat');need(H(p.read_bytes())==v['sha256'],'exact pin');return p
def receipt(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':H(p.read_bytes())}
def main():
 need(len(sys.argv)==2,'root GO argument');gp=Path(sys.argv[1]);g=load(gp);gh=H(gp.read_bytes());pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-closure.json');cr=load(D/'closure-registration.json')
 need(g['status']=='ROOT_AUTHORIZED_SR_COMPONENT_CONTROLS36_ONLY'and g['maximumLoaderCalls']==36 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g.get('correctionVersion')==3 and g.get('priorFailedCalls')==6,'finiteGO')
 need(g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes())and g['driverSHA256']==H((D/'run.py').read_bytes())and g['preregistrationSHA256']==H((D/'preregistration.json').read_bytes()),'currentsourceGO')
 need(g['inputClosureSHA256']==cr['inputClosureSHA256']==H((D/'input-closure.json').read_bytes()),'closureGO')
 need(len(g['sourceReviews'])==2 and len({v['path']for v in g['sourceReviews']})==2,'two specificreviews')
 producer=D.parent/'vector-masked32-shift-orr-compiler-build4-plan-v2-native-controls/run-outputs/ON.bin';loader=D.parent/'vector-masked32-source-bound-loader-build-plan-v2-native-controls/run-outputs/kexe-loader';need(ip[str(producer)]['sha256']=='5404f22ac455d66c1295a4ad0d90987722262b86b1aacd9bc9d69c8ad5cafd69'and ip[str(loader)]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','fixed actualproducer/loader')
 extra={}
 def guard():
  need(H(gp.read_bytes())==gh and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256']and H((D/'input-closure.json').read_bytes())==cr['inputClosureSHA256'],'immutableGO/registries')
  allpins={**ip,**{str(D/n):v for n,v in sp.items()},**extra,**{z['path']:{k:z[k]for k in ['bytes','sha256']}for z in g['sourceReviews']}}
  need(len(allpins)<=1024 and sum(v['bytes']for v in allpins.values())<=384*1024**2,'full source readcap')
  total=0
  for p,v in allpins.items():
   pp=Path(p);need(pp.is_file()and not pp.is_symlink()and pp.stat().st_size==v['bytes'],'regular stat beforehash');total+=pp.stat().st_size;need(total<=384*1024**2,'runningcap beforehash')
  for p,v in allpins.items():pin(p,v)
  ar=load(D.parent/'vector-masked32-shift-orr-compiler-build4-actual-review-v2-width/report.json');need(ar['status']=='PASS_SOURCE_BOUND_ACTUAL_FULL64_SHIFT_ORR_COMPILER_BUILD4_ONLY'and ar['emitterSourcePinsSHA256']==pr['emitterSourcePinsSHA256']and ar['counts']['closedChildCalls']==4 and ar['counts']['generatedCompilerExecutions']==0,'specificactualbuild')
  rr=[v for v in ar['images']if v['arm']=='ON'];need(len(rr)==1 and rr[0]['native']==dict(path=str(producer),**ip[str(producer)])and rr[0]['offset']==rr[0]['arity']==0,'actualproducer image')
  for z in g['sourceReviews']:
   r=load(z['path']);need(r['status']=='PASS_SOURCE_ONLY_SR_ACTUAL_HELPER_COMPONENT36'and r['sourcePinsSHA256']==g['sourcePinsSHA256'] and r.get('correctionVersion')==3,'specificsource receipt')
 guard();need(not O.exists(),'freshscope/noRetry');O.mkdir();rows=[];results=[];ok=False;save(O/'attempts.json',rows)
 for n in ['unity-native-controls.kotoba','fixture-left.kotoba','fixture-right.kotoba']:
  p=O/n;p.write_bytes((D/n).read_bytes());p.chmod(0o444);extra[str(p)]={k:v for k,v in receipt(p).items()if k!='path'}
 def call(label,image,args,seconds):
  guard();need(len(rows)<36 and label not in [r['label']for r in rows],'finiteunique36')
  env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':str(seconds),'KEXE_WALL_SECONDS':str(seconds),'KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
  argv=[str(loader),str(image),'0','0','aarch64','35,37,38,39','--',*args]
  r={'index':len(rows)+1,'label':label,'argv':argv,'effectiveEnvironment':env,'state':'started','timeoutSeconds':seconds+10};rows.append(r);save(O/'attempts.json',rows);p=None;o=e=b'';err=cleanup=None
  try:p=subprocess.Popen(argv,cwd=O,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);o,e=p.communicate(timeout=seconds+10)
  except BaseException as ex:
   err=repr(ex)
   if p is not None:
    try:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     o,e=p.communicate(timeout=30)
    except BaseException as ex2:
     cleanup=repr(ex2)
     try:p.wait(timeout=30)
     except BaseException as ex3:cleanup+=';reap='+repr(ex3)
  closed=p is None or p.returncode is not None
  (O/(label+'.stdout')).write_bytes(o);(O/(label+'.stderr')).write_bytes(e)
  r.update(state='terminal'if closed else'unclosed',spawned=p is not None,returncode=None if p is None else p.returncode,error=err,cleanupException=cleanup,stdoutSHA256=H(o),stderrSHA256=H(e),counterObservation=A.counters(e));save(O/'attempts.json',rows)
  need(closed and p is not None and p.returncode==0 and err is None and cleanup is None,'FIRST_FAILURE_STOP')
  need(r['counterObservation']['status']=='valid'and r['counterObservation']['entireStderrIsCounterLine'],'strict17counter line');guard();return o
 try:
  k=O/'harness.kseed';b=O/'harness.bin'
  raw=call('compile',producer,['compile',str(O/'unity-native-controls.kotoba'),'--target','aarch64-macos','--output',str(k)],1800);need(b':ok true'in raw and b':ok false'not in raw and k.is_file()and not k.is_symlink()and 0<k.stat().st_size<=4194560,'normal harnesscompile')
  kr=receipt(k);extra[str(k)]={x:kr[x]for x in ['bytes','sha256']};save(O/'container-captured.json',kr);raw=call('extract',producer,['extract-native',str(k),'--symbol','main','--output',str(b)],1800)
  need(b':ok true'in raw and b':ok false'not in raw and re.findall(rb':offset ([0-9]+)\b',raw)==[b'0']and b.is_file()and not b.is_symlink()and 0<b.stat().st_size<=4194304,'normal extraction')
  bb=b.read_bytes();need(k.read_bytes()==f'KSEED1 {len(bb)} 1\nmain 0 0\n\n'.encode()+bb,'wholemain0container/native');extra[str(b)]={x:v for x,v in receipt(b).items()if x!='path'};save(O/'artifacts.json',extra);guard()
  for c in range(34):
   fixture=O/('fixture-left.kotoba'if c<17 else'fixture-right.kotoba');raw=call('case-'+str(c),b,['probe',str(c),str(fixture)],180);results.append(V.validate(raw,c));save(O/'comparisons.json',results)
  guard();need(len(rows)==36 and len(results)==34,'finitecompletion');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'calls':len(rows),'completedCases':len(results),'firstFailureStop':True,'noRetry':True});raise
 finally:
  save(O/'report.json',{'status':'PASS_FINITE_ACTUAL_SR_COMPONENT_STATE_AND_GUARDS_ONLY'if ok else'FAIL_SR_COMPONENT36','loaderCalls':len(rows),'completedCases':len(results),'scope':'34fixed originalchecked/lowered roots and mutated-copy guards, full scalarM/G only','emittedRegisterExecutionQualified':False,'performanceQualified':False})
  save(O/'terminal.json',{'calls':len(rows),'allCallsClosed':all(r['state']=='terminal'for r in rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
