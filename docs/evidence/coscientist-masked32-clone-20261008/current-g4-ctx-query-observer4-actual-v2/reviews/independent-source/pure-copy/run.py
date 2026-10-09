"""Inert SOURCE. Current G4 query observer4 compiler-only commands only after exact two reviews and GO."""
from pathlib import Path
import json,hashlib,stat,importlib.util,re,os
D=Path(__file__).resolve().parent

def need(v,m):
 if not v:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=469762048,'bounded regular pin');b=p.read_bytes();s2=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable bytes');return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def pin(p,r):need(receipt(p)=={k:r[k]for k in ['bytes','sha256']},'exact pin:'+str(p));return Path(p)
def save(p,v):
 b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=16777216,'bounded valid-last metadata');q=Path(str(p)+'.pending')
 with q.open('wb',buffering=0)as f:
  view=memoryview(b)
  while view:
   n=f.write(view);need(type(n)is int and 0<n<=len(view),'metadata write');view=view[n:]
  os.fsync(f.fileno())
 os.replace(q,p);fd=os.open(str(Path(p).parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def container(raw):
 need(0<len(raw)<=4194560,'bounded KSEED');m=re.match(rb'KSEED1 ([1-9][0-9]{0,9}) ([1-9][0-9]{0,2})\n',raw);need(m is not None,'header');cut=raw.find(b'\n\n',m.end());need(cut>=m.end(),'separator');lines=raw[m.end():cut].splitlines();n=int(m[2]);need(1<=n<=128 and len(lines)==n,'exports');exports=[]
 for line in lines:
  q=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]{1,10}) ([0-9]{1,2})',line);need(q is not None,'export line');exports.append((q[1].decode(),int(q[2]),int(q[3])))
 payload=raw[cut+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1]) and len(set(x[0]for x in exports))==n,'whole payload/unique');need(all(x[1]%4==0 and x[1]+4<=len(payload)and x[2]<=32 for x in exports),'entry ABI');return payload,exports

def main(goPath):
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];generated={};results=[];ok=False
 need(set(g)=={'status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','hostAuthorizedOuterEscalation'},'exact GO fields')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==4 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False and g['C2']is False,'fixed4scope')
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'GO exact identity')
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'source review binds')
 fp=g['integrationFixtureProof'];need(fp==pr['qualifiedIntegrationFixtureProof'],'exact fixture');f=load(pin(fp['path'],fp));need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','limited actualfixture')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'matchingcomponents')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable GO/registry')
  need(len(ip)==pr['exactInputFiles']<=3072 and sum(v['bytes']for v in ip.values())==pr['exactInputLogicalBytes']<=469762048,'boundedfullclosure')
  for n,v in sp.items():pin(D/n,v)
  for n,v in ip.items():pin(n,v)
  for n,v in generated.items():pin(n,v)
  need(receipt(D/'unity-observer.kotoba')['sha256']==pr['sourceSHA256'],'whole observer SOURCE')
  a=load(pr['sourceAssembly']);parts=[Path(r['path']).read_bytes()+b'\n'for r in a['modulePins']];need(len(parts)==16 and b''.join(parts)==(D/'unity-observer.kotoba').read_bytes(),'exact current16 observer closure')
  pin(pr['baseCandidate']['path'],pr['baseCandidate']);pin(pr['baseUnity']['path'],pr['baseUnity'])
  proof=load(pin(pr['currentProducerProof']['path'],pr['currentProducerProof']));need(proof['status']=='PASS_INDEPENDENT_SAVED_HFT_COMPOSE511_BOUND_HOIST_G2_G3_G4_FIXEDPOINT6_COMPILER_ARTIFACTS_ONLY','current G4 actual compiler proof')
  need(receipt(pr['producer'])['sha256']==pr['producerSHA256']=='c3503b7f746b9279a27bba6f5b6a1e97f7a2770b694bdf42a558fd7cc856f445','currentG4 lineage')
  if str(O/'observer-producer.json')in generated:
   from producer_guard import validate_producer
   validate_producer(pr,dict(path=str(gp),**gr),g['sourcePinsSHA256'],g['preregistrationSHA256'])
  need(g['hostAuthorizedOuterEscalation']is True and pr['hostAuthorizedOuterEscalationRequired']is True and pr['loaderOwnedSandboxUnchanged']is True,'fixedhostouterpermission loader sandbox unchanged')
  b,e=container(Path(pr['candidateContainer']).read_bytes());need(b==Path(pr['producer']).read_bytes()and e==[('main',0,0)],'G0wholemain0')
 guard();need(not O.exists(),'fresh singleattempt');O.mkdir();save(O/'attempts.json',rows)
 for n in ['unity-observer.kotoba','statemate.kotoba','nsichneu.kotoba']:
  p=O/n;p.write_bytes((D/n).read_bytes());p.chmod(0o444);generated[str(p)]=receipt(p)
 save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native_call',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 def artifact(p):
  v=receipt(p);need(v['bytes']<=4194560,'artifact4MiB');generated[str(p)]=v;save(O/'generated-pins.json',generated);return dict(path=str(p),**v)
 try:
  for c in pr['cases']:
   guard();producer=Path(c['nativeArgv'][1]);pc=Path(pr['candidateContainer'])if str(producer)==pr['producer']else producer.with_suffix('.kseed');inp=Path(c['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':len(rows)+1,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':dict(path=str(producer),**receipt(producer)),'producerContainer':dict(path=str(pc),**receipt(pc)),'input':dict(path=str(inp),**receipt(inp)),'outputPath':c['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};p=O/(c['label']+'.admission.json');need(not p.exists()and not Path(c['outputPath']).exists(),'fresh admission/output');save(p,seal);p.chmod(0o444);sr=artifact(p)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);need(r['returncode']==0,'closed compilercommand');out=Path(c['outputPath']);ar=artifact(out)
   if c['kind']=='compile':
    payload,exports=container(out.read_bytes());need(ar['bytes']==r['report']['containerBytes'],'whole reportedsize')
    if c['arity']==0:need(exports==[('main',0,0)],'observed compiler sole main0')
    else:
     entries=[e for e in pr['entries']if e['workload']==c['workload']];need(len(entries)==1,'own workload evidence');e=entries[0]
     ordinary=pin(e['container']['path'],e['container']).read_bytes();need(out.read_bytes()==ordinary,'whole ordinary currentG4 container identity')
     op,oe=container(ordinary);need(payload==op==pin(e['native']['path'],e['native']).read_bytes()and exports==[tuple(x)for x in e['exports']],'whole ordinary payload/export identity')
     need('observerSummary'in r['report'],'strict parsed observer trace')
   else:
    payload,exports=container(inp.read_bytes());need(exports==[('main',0,0)]and out.read_bytes()==payload and r['report']=={'kind':'extract','offset':0,'nativeBytes':len(payload),'arity':0},'whole observer compiler main0')
   if c['label']=='observer-extract':
    ep=O/'observer-producer-evidence.json';save(ep,rows[:2]);ep.chmod(0o444);er=artifact(ep)
    pp=O/'observer-producer.json';save(pp,{'format':'ctx-observer-generated-producer/v2','rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'source':dict(path=str(O/'unity-observer.kotoba'),**receipt(O/'unity-observer.kotoba')),'native':ar,'container':dict(path=str(O/'observer.kseed'),**receipt(O/'observer.kseed')),'evidence':er});pp.chmod(0o444);artifact(pp)
    from producer_guard import validate_producer
    validate_producer(pr,dict(path=str(gp),**gr),g['sourcePinsSHA256'],g['preregistrationSHA256'])
   results.append({'label':c['label'],'artifact':ar,'report':r['report'],'memoryObservation':r['memoryObservation'],'strictOldMemoryPolicyPassed':r['strictOldMemoryPolicyPassed']});save(O/'results.json',results)
  guard();need(len(rows)==len(results)==4,'exact4');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'calls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'calls':len(rows),'closed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['closed']and not terminal['failure'],'durable terminal beforecomplete')
 proofs={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','results.json','generated-pins.json']}
 save(O/'report.json',{'status':'COMPLETE_CURRENT_G4_CTX_QUERY_OBSERVER4_ARTIFACT_AND_BOUNDED_TRACE_ONLY','calls':4,'results':results,'evidence':proofs,'sourcePinsSHA256':g['sourcePinsSHA256'],'rootGO':dict(path=str(gp),**gr),'globalApplicabilityClaim':False,'nativeAnswerReuse':False,'sharedCIDCacheImplemented':False,'scratchAdditionalWords':8,'equalKeysActualObservationRequired':True,'optimizerRuntimeQualified':False,'guestExecuted':False,'speedQualified':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'exact GO argument');main(sys.argv[1])
