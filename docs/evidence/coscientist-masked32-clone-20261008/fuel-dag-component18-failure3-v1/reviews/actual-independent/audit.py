"""Offline saved-raw audit only, after parent confirms terminal closure. No process APIs called."""
from pathlib import Path
import json,hashlib,sys,stat,importlib.util,re
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-fuel-scalar-dag-component18-source-v1-width';O=Path(__file__).resolve().parent
ip={}
def load(p):return json.loads(Path(p).read_text())
def pin(p,v=None):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=402653184;h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert s==p.lstat();z={'bytes':s.st_size,'sha256':h.hexdigest()}
 if v is not None:assert z=={k:v[k]for k in ('bytes','sha256')},str(p)
 ip[str(p)]=z;return z
def module(n,p):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main(gopath):
 R=D/'run-outputs';pr=load(D/'preregistration.json');pin(D/'preregistration.json');g=load(gopath);gh=pin(gopath);sp=pin(D/'source-pins.json');assert sp['sha256']==g['sourcePinsSHA256']=='7be013ea72525ce912f0e3c6bd3db91c190a801b5c6a38c72b8ba5addbb6d38c'
 assert g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==18 and g['outputRoot']==str(R)and g['noRetry']is True and g['candidateCompilerExecutionAuthorized']is True and g['componentProbeAuthorized']is True and g['generatedCodeExecutionAuthorized']is False and g['timingAuthorized']is False
 assert g['driverSHA256']==pin(D/'run.py')['sha256']and g['preregistrationSHA256']==pin(D/'preregistration.json')['sha256']and g['inputPinsSHA256']==pin(D/'input-pins.json')['sha256']==pr['inputPinsSHA256']
 for n,v in load(D/'source-pins.json').items():pin(D/n,v)
 origins=load(D/'input-pins.json');assert len(origins)==1738 and sum(v['bytes']for v in origins.values())==369725436
 for p,v in origins.items():pin(p,v)
 assert len(g['sourceReviews'])==2
 for z in g['sourceReviews']:
  pin(z['path'],z);r=load(z['path']);assert r['status']=='PASS_SOURCE_ONLY_FUEL_DAG_COMPONENT18'and r['sourcePinsSHA256']==sp['sha256']and r['driverSHA256']==g['driverSHA256']and r['preregistrationSHA256']==g['preregistrationSHA256']
 for k in ['actualProducerProof','actualLoaderProof']:assert load(pr[k])['status']==pr[k+'Status']
 driver=module('reviewed_component_driver',D/'run.py');validator=module('reviewed_component_receipts',D/'validate.py')
 rows=load(R/'attempts.json');pin(R/'attempts.json');terminal=load(R/'terminal.json');pin(R/'terminal.json');assert terminal['allChildrenClosed']is True and terminal['loaderCalls']==len(rows)<=18
 expected=[('component-compile',pr['producer'],['compile',str(R/'unity-component.kotoba'),'--target','aarch64-macos','--output',str(R/'component.kseed')]),('component-extract',pr['producer'],['extract-native',str(R/'component.kseed'),'--symbol','main','--output',str(R/'component.bin')])]
 expected.extend(('case'+str(c),str(R/'component.bin'),['probe',str(c),str(R/'fixture.kotoba')])for c in range(16))
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(R),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(R),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
 decoded=[];firstFailure=None
 for i,row in enumerate(rows):
  label,producer,args=expected[i];assert row['index']==i+1 and row['label']==label and row['argv']==[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--',*args]and row['effectiveEnvironment']==env and row['timeoutSeconds']==1810
  assert row['state']=='terminal'and row['spawned']is True and row['reaped']is True and type(row['pid'])is int and row['pid']>0
  op=R/(label+'.stdout');ep=R/(label+'.stderr');pin(op,row['stdout']);pin(ep,row['stderr']);assert op.stat().st_size<=1048576 and ep.stat().st_size<=1048576
  ctr=driver.counters(ep.read_bytes());assert ctr==row['counterObservation']
  success=row['returncode']==0 and not row['error']and not row['terminationReason']and not row['cleanupExceptions']and ctr['status']=='valid'
  if not success:firstFailure=i;assert i==len(rows)-1;break
  raw=op.read_bytes()
  if i<2:
   assert b':ok true'in raw and b':ok false'not in raw
   if i==1:assert re.findall(rb':offset ([0-9]+)\b',raw)==[b'0']
  else:
   try:decoded.append(validator.verify(raw,i-2))
   except (AssertionError,ValueError):firstFailure=i;assert i==len(rows)-1;break
 for p,v in load(R/'generated-pins.json').items():pin(p,v)
 assert (R/'unity-component.kotoba').read_bytes()==(D/'unity-component.kotoba').read_bytes();assert(R/'fixture.kotoba').read_bytes()==(D/'fixture.kotoba').read_bytes()
 images=load(R/'images.json')if(R/'images.json').exists()else[]
 if images:
  pin(R/'images.json');assert len(images)==1;image=images[0];pin(image['source']['path'],image['source']);pin(image['container']['path'],image['container']);pin(image['native']['path'],image['native']);assert image['offset']==image['arity']==0 and driver.kseed(Path(image['container']['path']).read_bytes())==Path(image['native']['path']).read_bytes()
 if terminal['failure']:
  assert(R/'failure.json').exists();pin(R/'failure.json');result='FAIL_PRESERVED_INDEPENDENT_SAVED_RAW_FUEL_DAG_COMPONENT18'
 else:
  assert firstFailure is None and len(rows)==18 and len(decoded)==16 and not(R/'failure.json').exists();actual=load(R/'report.json');pin(R/'report.json');assert actual['status']=='COMPLETE_FINITE_FUEL_DAG_COMPONENT18_STATE_RECEIPTS_ONLY'and actual['cases']==decoded and actual['sourcePinsSHA256']==sp['sha256']and actual['rootGOSHA256']==gh['sha256']
  assert load(R/'cases.json')==decoded;pin(R/'cases.json');result='PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_COMPONENT18_STATE_RECEIPTS_ONLY'
 report={'status':result,'sourcePinsSHA256':sp['sha256'],'rootGOSHA256':gh['sha256'],'loaderCalls':len(rows),'componentCasesVerified':len(decoded),'firstFailureIndex':None if firstFailure is None else firstFailure+1,'allRecordedChildrenClosed':True,'emittedFuelFiveWords':not terminal['failure'],'sourceBoundScalarM_GPredicateOnly':True,'abstractFuelModelOnly':True,'actualGeneratedCodeExecution':False,'actualNonresumingTrapQualified':False,'runtimeFuelArenaEquivalenceQualified':False,'fixedpointQualified':False,'full19Qualified':False,'performanceQualified':False,'participation':'Reviewer previously independently SOURCE reviewed component18 and authored separate earlier diagnostics. This audits saved raw and driver terminal claims; parent supplies actual OS-session closure, no independent OS trace or rerun.','nativeCompilerSSHCallsByReviewer':0}
 for n,z in [('report.json',report),('input-pins.json',ip)]: (O/n).write_text(json.dumps(z,indent=2)+'\n')
 print(json.dumps(report))
if __name__=='__main__':
 assert len(sys.argv)==3 and sys.argv[1]=='ROOT_CONFIRMED_TERMINAL_CLOSURE';main(Path(sys.argv[2]))
