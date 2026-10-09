"""Inert import. Exactly18 diagnostic compile/extract/probe children after specific root GO only."""
from pathlib import Path
import hashlib,json,os,sys,re,stat,subprocess,signal,time,resource
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'regular nonsymlink');need(0<=s.st_size<=384*1024**2,'bounded file before hash');b=p.read_bytes();s2=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable during hash');return {'bytes':len(b),'sha256':H(b)}
def pin(p,v):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==v['bytes'],'exact stat before hash');need(receipt(p)=={k:v[k]for k in ['bytes','sha256']},'exact pin');return p
def kseed(b):
 need(0<len(b)<=4194560,'bounded container');m=re.match(rb'KSEED1 ([1-9][0-9]*) 1\nmain 0 0\n\n',b);need(m is not None,'exact sole main0');p=b[m.end():];need(0<len(p)<=4194304 and len(p)==int(m[1]),'whole declared payload');return p
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(b):
 m=PAT.fullmatch(b)
 if not m or any(len(x)>20 for x in m.groups()):return {'status':'unavailable-or-invalid','values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,m.groups())));valid=all(0<=x<2**64 for x in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items']and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else'invalid','values':u,'entireStderrIsCounterLine':True}
def main(gopath):
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');S=Path(pr['parentEmitterSourceDirectory']);O=Path(pr['freshOutputRoot'])
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==18 and g['outputRoot']==str(O)and g['outerExecution']=='require_escalated'and g['noRetry']is True and g['candidateCompilerExecutionAuthorized']is True and g['componentProbeAuthorized']is True and g['generatedCodeExecutionAuthorized']is False and g['timingAuthorized']is False,'exact diagnostic18 GO')
 need(g['driverSHA256']==receipt(D/'run.py')['sha256']and g['sourcePinsSHA256']==receipt(D/'source-pins.json')['sha256']and g['preregistrationSHA256']==receipt(D/'preregistration.json')['sha256']and g['inputPinsSHA256']==pr['inputPinsSHA256']==receipt(D/'input-pins.json')['sha256'],'GO exact immutable source/driver/input pins')
 need(ip[pr['producer']]['sha256']==pr['producerSHA256']and ip[pr['loader']]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','qualified actual DAG producer/e14')
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two distinct current component SOURCE reviews')
 extra={}
 def guard():
  need(receipt(gp)==gh and receipt(D/'source-pins.json')['sha256']==g['sourcePinsSHA256']and receipt(D/'input-pins.json')['sha256']==pr['inputPinsSHA256'],'immutable registries')
  for n,z in sp.items():pin(D/n,z)
  need(len(ip)<=pr['maximumInputFiles']and sum(z['bytes']for z in ip.values())<=pr['maximumInputLogicalBytes'],'fullclosure cap')
  total=0
  for p,z in ip.items():
   pp=Path(p);st=pp.lstat();need(stat.S_ISREG(st.st_mode)and not pp.is_symlink()and st.st_size==z['bytes'],'closure stat before reads');total+=st.st_size;need(total<=pr['maximumInputLogicalBytes'],'aggregate cap before hash')
  for p,z in ip.items():pin(p,z)
  for p,z in extra.items():pin(p,z)
  need(receipt(S/'source-pins.json')['sha256']==pr['parentEmitterSourcePinsSHA256'],'exact emitter registry')
  for n,z in load(S/'source-pins.json').items():pin(S/n,z)
  need(all(z['exactReverse']for z in load(S/'reversal.json').values())and len(load(S/'reversal.json'))==4,'four registered reversals')
  need(load(pin(pr['actualProducerProof'],ip[pr['actualProducerProof']]))['status']==pr['actualProducerProofStatus'],'actual producer proof')
  lr=load(pin(pr['actualLoaderProof'],ip[pr['actualLoaderProof']]));need(lr['status']==pr['actualLoaderProofStatus']and lr['loader']==dict(path=pr['loader'],**ip[pr['loader']]),'actual diagnostic loader correspondence')
  for r in g['sourceReviews']:
   q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256']and q['driverSHA256']==g['driverSHA256']and q['preregistrationSHA256']==g['preregistrationSHA256'],'specific complete component SOURCE review')
  rev=load(D/'reversal.json');need(rev['exactReverseParent']is True and rev['parentSHA256']=='5fde80c8d567b6ce73ec0ce56e3766aef5e37484080a16be4da28923b2be5053','diagnostic exact reversal')
 guard();need(not O.exists(),'fresh no-rerun root');O.mkdir();rows=[];images=[];cases=[];ok=False;save(O/'attempts.json',rows)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
 def capture(p,maximum):
  p=Path(p);need(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=maximum,'bounded captured artifact');extra[str(p)]=receipt(p);save(O/'generated-pins.json',extra);return dict(path=str(p),**extra[str(p)])
 def call(label,args,producer=None):
  guard();need(len(rows)<18 and label not in [r['label']for r in rows],'finite18 no retry');argv=[pr['loader'],producer or pr['producer'],'0','0','aarch64','35,37,38,39','--',*args];r={'index':len(rows)+1,'label':label,'argv':argv,'effectiveEnvironment':env.copy(),'timeoutSeconds':pr['wallSeconds'],'state':'started'};rows.append(r);save(O/'attempts.json',rows)
  op=O/(label+'.stdout');ep=O/(label+'.stderr');p=None;reason=None;error=None;cleanup=[];reaped=False
  try:
   with op.open('xb')as out,ep.open('xb')as err:
    try:
     def childlimit():resource.setrlimit(resource.RLIMIT_FSIZE,(pr['fileHardLimitBytes'],pr['fileHardLimitBytes']))
     p=subprocess.Popen(argv,cwd=O,env=env,stdout=out,stderr=err,start_new_session=True,preexec_fn=childlimit);r.update(pid=p.pid);save(O/'attempts.json',rows);start=time.monotonic()
     while p.poll()is None:
      if time.monotonic()-start>pr['wallSeconds']:reason='wallcap'
      if op.stat().st_size>pr['stdoutBytesMaximum']or ep.stat().st_size>pr['stderrBytesMaximum']:reason='outputcap'
      if reason:break
      time.sleep(.02)
    except BaseException as ex:error=type(ex).__name__;reason=reason or'exception'
    finally:
     if p is not None:
      try:
       if error or reason or p.poll()is None:os.killpg(p.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      except BaseException as ex:
       cleanup.append('kill:'+type(ex).__name__)
       try:os.killpg(p.pid,signal.SIGKILL)
       except ProcessLookupError:pass
       except BaseException as ex2:cleanup.append('killagain:'+type(ex2).__name__)
      try:p.wait(timeout=pr['reapSeconds']);reaped=True
      except BaseException as ex:cleanup.append('reap:'+type(ex).__name__)
  except BaseException as ex:error=error or type(ex).__name__;reason=reason or'filefailure'
  if op.exists()and ep.exists()and(op.stat().st_size>pr['stdoutBytesMaximum']or ep.stat().st_size>pr['stderrBytesMaximum']):reason=reason or'outputcap'
  r.update(state='terminal'if p is None or reaped else'unclosed',spawned=p is not None,reaped=reaped,returncode=p.returncode if p else None,error=error,terminationReason=reason,cleanupExceptions=cleanup,stdout=None,stderr=None);save(O/'attempts.json',rows)
  for name,path in [('stdout',op),('stderr',ep)]:
   if path.exists():r[name]=receipt(path)
  save(O/'attempts.json',rows)
  if ep.exists()and ep.stat().st_size<=pr['stderrBytesMaximum']:r['counterObservation']=counters(ep.read_bytes());save(O/'attempts.json',rows)
  need(p is not None and reaped and not reason and not error and not cleanup and p.returncode==0,'FIRST_FAILURE_STOP_CLOSED');need(r.get('counterObservation',{}).get('status')=='valid','FIRST_FAILURE_STOP_EXACT17COUNTERS');guard();return op.read_bytes()
 try:
  import validate
  copied=O/'unity-component.kotoba';copied.write_bytes((D/'unity-component.kotoba').read_bytes());copied.chmod(0o444);capture(copied,4194304)
  fixture=O/'fixture.kotoba';fixture.write_bytes((D/'fixture.kotoba').read_bytes());fixture.chmod(0o444);capture(fixture,65536);guard()
  k=O/'component.kseed';b=O/'component.bin'
  raw=call('component-compile',['compile',str(copied),'--target','aarch64-macos','--output',str(k)]);need(b':ok true'in raw and b':ok false'not in raw,'diagnostic compile accepted')
  kr=capture(k,pr['containerBytesMaximum']);payload=kseed(k.read_bytes());save(O/'container-captured.json',kr);guard()
  raw=call('component-extract',['extract-native',str(k),'--symbol','main','--output',str(b)]);br=capture(b,pr['nativeBytesMaximum'])
  need(b':ok true'in raw and b':ok false'not in raw and re.findall(rb':offset ([0-9]+)\b',raw)==[b'0']and b.read_bytes()==payload,'solemain0 wholepayload')
  images.append({'source':dict(path=str(copied),**receipt(copied)),'container':kr,'native':br,'offset':0,'arity':0});save(O/'images.json',images)
  for c in pr['expectedCases']:
   raw=call('case'+str(c),['probe',str(c),str(fixture)],str(b));v=validate.verify(raw,c);cases.append(v);save(O/'cases.json',cases)
  guard();need(len(rows)==18 and len(cases)==16,'exact18/16')
  save(O/'report.json',{'status':'COMPLETE_FINITE_FUEL_DAG_COMPONENT18_STATE_RECEIPTS_ONLY','loaderCalls':18,'diagnosticBuildCalls':2,'componentProbeCalls':16,'cases':cases,'images':images,'sourcePinsSHA256':g['sourcePinsSHA256'],'rootGOSHA256':gh['sha256'],'sourceBoundFullScalarM_GPredicate':True,'abstractFuel0_1_2Only':True,'emittedFiveWordFuelWitness':True,'actualGeneratedCodeExecution':False,'actualNonresumingTrapQualified':False,'runtimeFuelArenaEquivalenceQualified':False,'fixedpointQualified':False,'performanceQualified':False});ok=True
 except BaseException as ex:save(O/'failure.json',{'error':type(ex).__name__+': '+str(ex),'closedOrStartedCalls':len(rows),'completedImages':len(images),'completedCases':len(cases),'firstFailureStop':True,'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
if __name__=='__main__':need(len(sys.argv)==2,'root GO only');main(sys.argv[1])
