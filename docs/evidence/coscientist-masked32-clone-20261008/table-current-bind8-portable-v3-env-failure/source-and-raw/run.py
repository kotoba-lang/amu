"""Inert import. Exactly8 current-source readonly binding children after specific root GO only."""
from pathlib import Path
import hashlib,json,os,sys,re,stat,subprocess,signal,time,threading,selectors,importlib.util
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
 need(0<len(b)<=4194560,'bounded container');m=re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\n',b);need(m is not None,'KSEED header');end=b.find(b'\n\n',m.end());need(end>=0,'export terminator');rows=b[m.end():end].split(b'\n');need(len(rows)==int(m[2])<=64,'export count');exports=[]
 for row in rows:
  z=row.split(b' ');need(len(z)==3 and re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_.!?/-]*',z[0])and z[1].isdigit()and z[2].isdigit(),'export row');exports.append((z[0].decode(),int(z[1]),int(z[2])))
 payload=b[end+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1])and len({z[0]for z in exports})==len(exports)and all(0<=off<len(payload)and off%4==0 and ar<=16 for _,off,ar in exports),'whole payload/exports');return payload,exports
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(b):
 m=PAT.fullmatch(b)
 if not m or any(len(x)>20 for x in m.groups()):return {'status':'unavailable-or-invalid','values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,m.groups())));valid=all(0<=x<2**64 for x in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items']and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else'invalid','values':u,'entireStderrIsCounterLine':True}

def main(gopath):
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'preregistration.json')
 sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=D/'run-outputs'
 need(set(g)=={'status','maximumLoaderCalls','outputRoot','outerExecution','noRetry','TCEmitterExecutionAuthorized','generatedWorkloadExecutionAuthorized','timingAuthorized','sha256','sourceReviews'},'no unknown GO fields')
 need(set(g['sha256'])=={'run.py','preregistration.json','source-pins.json','input-pins.json'},'exact GO hashes')
 need(all(set(r)=={'path','bytes','sha256'}for r in g['sourceReviews']),'exact review receipt fields')
 need(g['status']=='ROOT_GO_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY_ONLY' and g['maximumLoaderCalls']==8
      and g['outputRoot']==str(O) and g['outerExecution']=='require_escalated'
      and g['noRetry']is True and g['TCEmitterExecutionAuthorized']is False
      and g['generatedWorkloadExecutionAuthorized']is False and g['timingAuthorized']is False,'exact bind8 GO')
 for name in ['run.py','preregistration.json','source-pins.json','input-pins.json']:
  need(g['sha256'][name]==receipt(D/name)['sha256'],'specific immutable gate '+name)
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'root and independent driver SOURCE reviews')
 need(pr['maximumPythonWrapperStarts']==8 and pr['maximumNativeCompilerChildStarts']==8 and pr['maximumSimultaneousGroupMembers']==2,'finite exec/fork scope')
 need(pr['producer']['sha256']=='d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a'
      and pr['baseline41SHA256']=='4ed9b5600505c33013c966d266a977a3d4ccd56ad3cdc425b1805acf390b95f3','explicit distinct stage0/current source')
 need(ip[pr['producer']['path']]=={k:pr['producer'][k]for k in ['bytes','sha256']}
      and ip[pr['loader']['path']]=={k:pr['loader'][k]for k in ['bytes','sha256']},'producer/loader pins in full declared closure')
 extra={}
 def guard():
  need(receipt(gp)==gh,'immutable GO')
  for name in ['run.py','preregistration.json','source-pins.json','input-pins.json']:
   need(receipt(D/name)['sha256']==g['sha256'][name],'immutable registry/driver')
  need(len(ip)<=pr['maximumInputFiles'] and sum(v['bytes']for v in ip.values())<=pr['maximumInputLogicalBytes'],'closure admission')
  for path,v in ip.items():pin(path,v)
  for name,v in sp.items():pin(D/name,v)
  for path,v in extra.items():pin(path,v)
  for r in g['sourceReviews']:
   q=load(pin(r['path'],r));need(q['status']=='PASS_SOURCE_ONLY_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY'
      and q['sourcePinsSHA256']==g['sha256']['source-pins.json']
      and q['driverSHA256']==g['sha256']['run.py'],'specific reviewed driver')
  pp=load(pr['actualProducerProof']);need(pp['status']==pr['actualProducerProofStatus'],'actual stage0 producer proof')
  ons=[r for r in pp['images'] if r.get('arm')=='ON'];need(len(ons)==1
      and ons[0]['native']==pr['producer'],'actual stage0 identity; no variant stitching')
  lp=load(pr['actualLoaderProof']);need(lp['status']==pr['actualLoaderProofStatus']
      and lp['loader']==pr['loader'],'actual existing loader identity')
  fq=load(pin(pr['qualifiedMemoryFixtureProof']['path'],pr['qualifiedMemoryFixtureProof']))
  need(fq['status']==pr['qualifiedMemoryFixtureProofStatus']and fq['acceptedSamples']==8 and fq['memberCounts']==[1,1,2,2,2,2,1,1]and fq['normalClosureEstablishedForFixedFixture']is True and fq['hardMemoryCapEstablished']is False and fq['native8Authorized']is False,'accepted limited fixed fixture only')
  fc=load(pin(pr['qualifiedMemoryFixtureCompletion']['path'],pr['qualifiedMemoryFixtureCompletion']));need(fc['status']=='COMPLETE_OWNED_GROUP_MEMORY_ADAPTER_QUALIFICATION_ONLY','exact fixture completion')
 guard();need(pr['qualifiedMemoryFixtureProof']is not None,'accepted actual fixture proof required')
 fq=load(pin(pr['qualifiedMemoryFixtureProof']['path'],pr['qualifiedMemoryFixtureProof']));need(fq['status']==pr['qualifiedMemoryFixtureProofStatus'],'accepted exact actual memory fixture')
 spec=importlib.util.spec_from_file_location('pinned_memory_adapter',D/'adapter.py');memoryModule=importlib.util.module_from_spec(spec);spec.loader.exec_module(memoryModule)
 guard();need(not O.exists(),'fresh no retry output');O.mkdir();rows=[];images=[];ok=False
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),
      'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),
      'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216',
      'KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800',
      'KEXE_FUEL':'off','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1'}
 save(O/'effective-environment.json',env);save(O/'attempts.json',rows)
 def capture(path,maximum):
  path=Path(path);need(path.is_file()and not path.is_symlink()and 0<path.stat().st_size<=maximum,'artifact bound')
  extra[str(path)]=receipt(path);save(O/'generated-pins.json',extra);return dict(path=str(path),**extra[str(path)])
 def call(label,args,producer):
  guard();need(len(rows)<8 and label not in [r['label']for r in rows],'finite8 no retry')
  nativeArgv=[pr['loader']['path'],str(producer),'0','0','aarch64','35,37,38,39','--',*args]
  r={'index':len(rows)+1,'label':label,'nativeArgv':nativeArgv,'environment':env.copy(),'state':'started'}
  rows.append(r);save(O/'attempts.json',rows);out=O/(label+'.stdout');err=O/(label+'.stderr');lj=O/(label+'.limit-journal.jsonl');mj=O/(label+'.memory-journal.jsonl')
  proc=None;reason=None;exception=None;cleanup=[];reaped=False;signalAuthority=False;waitEntered=False;waitUncertain=False
  anchor=threading.Lock();stop=threading.Event();expired=threading.Event();watch=None;sel=selectors.DefaultSelector();bytesOut={'stdout':0,'stderr':0};sampleCount=0;peakFootprint=0;memoryBytes=0
  with out.open('xb',buffering=0)as of,err.open('xb',buffering=0)as ef,lj.open('xb',buffering=0)as limits,mj.open('xb',buffering=0)as memory:
   argv=[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd',str(limits.fileno()),'--',*nativeArgv];r['argv']=argv;save(O/'attempts.json',rows)
   deadline=time.monotonic()+1810
   def watchdog():
    nonlocal reason
    if not stop.wait(max(0,deadline-time.monotonic())):
     expired.set();reason='outerwall1810'
     with anchor:
      if proc is not None and signalAuthority and not waitEntered and proc.returncode is None:
       try:os.killpg(proc.pid,signal.SIGKILL)
       except ProcessLookupError:pass
       except BaseException as ex:cleanup.append('watchdog:'+repr(ex))
   try:
    proc=subprocess.Popen(argv,cwd=O,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(limits.fileno(),),start_new_session=True)
    signalAuthority=True;r['pid']=proc.pid;save(O/'attempts.json',rows);watch=threading.Thread(target=watchdog,daemon=True);watch.start()
    for name,pipe,file in [('stdout',proc.stdout,of),('stderr',proc.stderr,ef)]:os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,(name,file))
    sampler=memoryModule.OwnedGroupSampler(memoryModule.DarwinOwnedGroupAPI(),proc.pid);nextSample=time.monotonic()
    while sel.get_map():
     need(not expired.is_set()and time.monotonic()<deadline,'outerwall1810')
     for key,_ in sel.select(.02):
      b=os.read(key.fd,65536);name,file=key.data
      if not b:sel.unregister(key.fileobj);key.fileobj.close();continue
      cap=8388608 if name=='stdout'else 1048576;room=cap-bytesOut[name];need(file.write(b[:room])==min(room,len(b)),'complete bounded raw write');bytesOut[name]+=min(room,len(b));need(len(b)<=room,'raw capture overflow')
     if not sel.get_map():break
     if time.monotonic()>=nextSample:
      q=sampler.sample();sampleCount+=1;peakFootprint=max(peakFootprint,q['aggregateBytes'])
      # Compact full accepted witness; at most2 [PID,birth,footprint] rows, no guessed zeros.
      witness=[q['sample'],time.monotonic_ns(),q['ownedPGID'],[[x['pid'],x['start'],x['physicalFootprintBytes']]for x in q['members']]]
      b=(json.dumps(witness,separators=(',',':'))+'\n').encode();need(sampleCount<=90502 and memoryBytes+len(b)<=16777216,'finite memory receipt budget');need(memory.write(b)==len(b),'full memory receipt');os.fsync(memory.fileno());memoryBytes+=len(b);nextSample=time.monotonic()+.02
    stop.set();watch.join(timeout=.1);need(not watch.is_alive(),'watchdog joined before reap')
    need(anchor.acquire(timeout=max(.001,deadline-time.monotonic())),'normal ownership lock')
    try:
     signalAuthority=False;waitEntered=True
     try:proc.wait(timeout=min(30,max(.001,deadline-time.monotonic())))
     except BaseException:waitUncertain=True;raise
     finally:reaped=proc.returncode is not None
    finally:anchor.release()
    need(not expired.is_set()and time.monotonic()<deadline,'normal closed before outerwall')
   except BaseException as ex:exception=repr(ex);reason=reason or'exception'
   finally:
    cleanupDeadline=time.monotonic()+30;stop.set()
    if watch is not None:
     watch.join(timeout=.1)
     if watch.is_alive():cleanup.append('watchdog unjoined')
    locked=anchor.acquire(timeout=max(.001,cleanupDeadline-time.monotonic()))
    if not locked:cleanup.append('ownership lock unavailable; no signal/reap')
    try:
     if locked and proc is not None and signalAuthority and not waitEntered and proc.returncode is None:
      try:os.killpg(proc.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      except BaseException as ex:cleanup.append('killgroup:'+repr(ex))
      signalAuthority=False;waitEntered=True
      try:proc.wait(timeout=max(.001,cleanupDeadline-time.monotonic()))
      except BaseException as ex:waitUncertain=True;cleanup.append('wait:'+repr(ex))
      finally:reaped=proc.returncode is not None
    finally:
     if locked:anchor.release()
    if waitUncertain:cleanup.append('wait ownership uncertain; authority retired/no later group operations')
    if proc is not None:
     for pipe in [proc.stdout,proc.stderr]:
      if pipe is not None and not pipe.closed:pipe.close()
    sel.close();os.fsync(of.fileno());os.fsync(ef.fileno());os.fsync(limits.fileno());os.fsync(memory.fileno())
  journalBounded=0<=lj.stat().st_size<=65536 and 0<=mj.stat().st_size<=16777216
  if not journalBounded:reason=reason or'journalcap'
  limitReceipt=receipt(lj)if lj.stat().st_size<=65536 else {'bytes':lj.stat().st_size,'sha256':None,'overcapNotRead':True}
  memoryReceipt=receipt(mj)if mj.stat().st_size<=16777216 else {'bytes':mj.stat().st_size,'sha256':None,'overcapNotRead':True}
  r.update(state='terminal'if proc is None or reaped else'unclosed',spawned=proc is not None,reaped=reaped,returncode=None if proc is None else proc.returncode,reason=reason,exception=exception,cleanup=cleanup,waitEntered=waitEntered,waitUncertain=waitUncertain,signalingAuthorityRetired=not signalAuthority,stdout=receipt(out),stderr=receipt(err),limitJournal=limitReceipt,memoryJournal=memoryReceipt,memorySamples=sampleCount,peakObservedAggregateFootprintBytes=peakFootprint,hardMemoryCapEstablished=False)
  if err.stat().st_size<=1048576:r['counterObservation']=counters(err.read_bytes())
  save(O/'attempts.json',rows)
  need(proc is not None and reaped and proc.returncode==0 and not reason and not exception and not cleanup,'first failure stop closed')
  need(0<lj.stat().st_size<=65536,'bounded limit journal');limitsRows=[json.loads(x)for x in lj.read_bytes().splitlines()]
  need(len(limitsRows)==5,'exact two named setters plus exec witness')
  for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)]):
   before,after=limitsRows[2*k:2*k+2];need(before['index']==k+1 and before['limit']==name and before['stage']=='before'and before['desired']==[soft,hard],'exact desired resource')
   bs,bh=before['before'];need((bs==9223372036854775807 or bs>=soft)and(bh==9223372036854775807 or bh>=hard),'named setters never raise inherited finite limits')
   need(after=={'index':k+1,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]},'exact named setter/readback')
  need(limitsRows[-1]=={'stage':'exec-ready','argv':nativeArgv,'ASSetterRequested':False,'CPUGraceHardSeconds':1801},'exact pinned native exec witness')
  need(sampleCount>0 and r.get('counterObservation',{}).get('status')=='valid','observed process memory and exact17 counters')
  raw=out.read_bytes();need(b':ok true'in raw and b':ok false'not in raw,'compiler/extract normal success');guard();return raw
 def build(label,src,producer):
  src=Path(src);k=O/(label+'.kseed');n=O/(label+'.bin')
  call(label+'-compile',['compile',str(src),'--target','aarch64-macos','--output',str(k)],producer)
  kr=capture(k,4194560);payload,ex=kseed(k.read_bytes());need(ex==[('main',0,0)],'whole built compiler main0')
  raw=call(label+'-extract',['extract-native',str(k),'--symbol','main','--output',str(n)],producer)
  nr=capture(n,4194304);need(n.read_bytes()==payload and re.findall(rb':offset ([0-9]+)\b',raw)==[b'0'],'whole fresh compiler extraction')
  row={'role':label,'source':dict(path=str(src),**receipt(src)),'container':kr,'native':nr,'exports':ex}
  images.append(row);save(O/'images.json',images);return n
 try:
  copies={}
  for name in ['unity-baseline.kotoba','unity-observer.kotoba','original-input.kotoba']:
   path=O/name;path.write_bytes((D/name).read_bytes());path.chmod(0o444);capture(path,4194304);copies[name]=path
  stage0=pr['producer']['path']
  baseline=build('current-baseline',copies['unity-baseline.kotoba'],stage0)
  observer=build('readonly-observer',copies['unity-observer.kotoba'],stage0)
  vb=(D/'validate.py').read_bytes();need(H(vb)==sp['validate.py']['sha256'],'exact validator source buffer')
  ns={'__file__':str(D/'validate.py'),'__name__':'pinned_readonly_binding_validator'};exec(compile(vb,str(D/'validate.py'),'exec'),ns)
  products=[];binding=None
  for label,producer in [('ordinary-input',baseline),('observed-input',observer)]:
   k=O/(label+'.kseed');n=O/(label+'.bin')
   raw=call(label+'-compile',['compile',str(copies['original-input.kotoba']),'--target','aarch64-macos','--output',str(k)],producer)
   kr=capture(k,4194560);payload,ex=kseed(k.read_bytes());need(sum(s=='bench'and a==1 for s,off,a in ex)==1,'original input bench1')
   if products:
    need(k.read_bytes()==Path(products[0]['container']['path']).read_bytes(),'whole observed == fresh current ordinary before extract')
    binding=ns['verify'](raw,payload,ex,copies['original-input.kotoba'].read_bytes())
    save(O/'typed-binding.json',binding);capture(O/'typed-binding.json',8388608);guard()
   cr=call(label+'-extract',['extract-native',str(k),'--symbol','bench','--output',str(n)],producer)
   nr=capture(n,4194304);off=next(off for s,off,a in ex if s=='bench')
   need(n.read_bytes()==payload and re.findall(rb':offset ([0-9]+)\b',cr)==[str(off).encode()],'whole original extraction/export')
   products.append({'role':label,'container':kr,'native':nr,'offset':off,'exports':ex,'compileRaw':str(O/(label+'-compile.stdout'))})
  need(Path(products[0]['native']['path']).read_bytes()==Path(products[1]['native']['path']).read_bytes(),'whole fresh current native identity')
  need(binding is not None,'binding accepted before eighth child');guard()
  need(len(rows)==8 and all(r['state']=='terminal'for r in rows),'all eight closed')
  completion={'status':'COMPLETE_CURRENT_TYPED_BIND8_READONLY_IDENTITY_ONLY',
       'images':images,'products':products,'sourcePinsSHA256':g['sha256']['source-pins.json'],
       'rootGOSHA256':gh['sha256'],'TCEmitterExecuted':False,'generatedWorkloadExecuted':False,
       'selfhostFixedPointQualified':False,'performanceQualified':False,'OSStackLimitProof':False,'hardMemoryCapEstablished':False,'memoryMetric':'sum-ri_phys_footprint','memoryPolicySupersedesAS4GiB':True}
  ok=True
 except BaseException as ex:
  save(O/'failure.json',{'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':repr(ex),'attemptedCalls':len(rows)});raise
 finally:
  save(O/'terminal.json',{'attemptedCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok,'noRetry':True})
 if ok:
  need(len(rows)==8 and all(r['state']=='terminal'for r in rows),'valid-last all eight closed')
  completion['terminal']=capture(O/'terminal.json',1048576)
  completion['attempts']=dict(path=str(O/'attempts.json'),**receipt(O/'attempts.json'))
  completion['generatedPins']=dict(path=str(O/'generated-pins.json'),**receipt(O/'generated-pins.json'))
  guard();save(O/'completion.json',completion)
if __name__=='__main__':need(len(sys.argv)==2,'exact reviewed root GO required');main(sys.argv[1])
