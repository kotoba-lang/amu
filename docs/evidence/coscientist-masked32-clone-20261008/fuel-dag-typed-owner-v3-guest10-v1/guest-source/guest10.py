"""Inert import. Exactly10 direct compiled fixture guest children after two actual prerequisites after specific root GO only."""
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
 need(0<len(b)<=4194560,'bounded container');m=re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\n',b);need(m is not None,'KSEED header');end=b.find(b'\n\n',m.end());need(end>=0,'export terminator');rows=b[m.end():end].split(b'\n');need(len(rows)==int(m[2])<=64,'export count');exports=[]
 for row in rows:
  z=row.split(b' ');need(len(z)==3 and re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_.!?/-]*',z[0])and z[1].isdigit()and z[2].isdigit(),'export row');exports.append((z[0].decode(),int(z[1]),int(z[2])))
 payload=b[end+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1])and len({z[0]for z in exports})==len(exports)and all(0<=off<len(payload)and off%4==0 and ar<=16 for _,off,ar in exports),'whole payload/exports');need(sum(n=='bench'and ar==1 for n,off,ar in exports)==1,'unique bench1');return payload,exports
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(b):
 m=PAT.fullmatch(b)
 if not m or any(len(x)>20 for x in m.groups()):return {'status':'unavailable-or-invalid','values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,m.groups())));valid=all(0<=x<2**64 for x in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items']and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else'invalid','values':u,'entireStderrIsCounterLine':True}
def main(gopath):
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'guest-preregistration.json');sp=load(D/'source-pins.json');baseip=load(D/'input-pins.json');rip=g['runtimeInputPins'];pin(rip['path'],rip);ip=load(rip['path']);need(all(ip.get(p)==z for p,z in baseip.items()),'runtime closure contains full base closure');S=Path(pr['sourceDirectory']);O=Path(pr['freshOutputRoot'])
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==10 and g['outputRoot']==str(O)and g['outerExecution']=='require_escalated'and g['noRetry']is True and g['generatedCompilerExecutionAuthorized']is False and g['workloadGuestAuthorized']is True and g['timingAuthorized']is False,'exact partitioned emitted guest10 GO')
 need(g['guestDriverSHA256']==receipt(D/'guest10.py')['sha256']and g['driverSourcePinsSHA256']==receipt(D/'source-pins.json')['sha256']and g['guestPreregistrationSHA256']==receipt(D/'guest-preregistration.json')['sha256']and g['inputPinsSHA256']==pr['inputPinsSHA256']==receipt(D/'input-pins.json')['sha256']and g['sourcePinsSHA256']==pr['sourcePinsSHA256'],'GO exact immutable source/driver/input pins')
 need(ip[pr['OFFProducer']]['sha256']=='5404f22ac455d66c1295a4ad0d90987722262b86b1aacd9bc9d69c8ad5cafd69'and ip[pr['ONProducer']]['sha256']=='d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a'and ip[pr['loader']]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','qualified SR5404/e14 only')
 need(len(g['sourceReviews'])==len(g['driverReviews'])==2 and len({r['path']for r in g['sourceReviews']})==len({r['path']for r in g['driverReviews']})==2,'two distinct SOURCE and driver reviews')
 extra={}
 def guard():
  need(receipt(gp)==gh and receipt(D/'source-pins.json')['sha256']==g['driverSourcePinsSHA256']and receipt(D/'input-pins.json')['sha256']==pr['inputPinsSHA256'],'immutable registries')
  for n,z in sp.items():pin(D/n,z)
  need(len(ip)<=pr['maximumInputFiles']and sum(z['bytes']for z in ip.values())<=pr['maximumInputLogicalBytes'],'fullclosure cap')
  total=0
  for p,z in ip.items():
   pp=Path(p);st=pp.lstat();need(stat.S_ISREG(st.st_mode)and not pp.is_symlink()and st.st_size==z['bytes'],'closure stat before reads');total+=st.st_size;need(total<=pr['maximumInputLogicalBytes'],'aggregate cap before hash')
  for p,z in ip.items():pin(p,z)
  for p,z in extra.items():pin(p,z)
  need(receipt(S/'source-pins.json')['sha256']==g['sourcePinsSHA256'],'exact emitter registry')
  for n,z in load(S/'source-pins.json').items():pin(S/n,z)
  need(all(z['exactReverse']for z in load(S/'reversal.json').values())and len(load(S/'reversal.json'))==4,'four registered reversals')
  need(load(pin(pr['actualProducerProof'],ip[pr['actualProducerProof']]))['status']==pr['actualProducerProofStatus'],'actual producer proof')
  lr=load(pin(pr['actualLoaderProof'],ip[pr['actualLoaderProof']]));need(lr['status']==pr['actualLoaderProofStatus']and lr['loader']==dict(path=pr['loader'],**ip[pr['loader']]),'actual diagnostic loader correspondence')
  for r in g['sourceReviews']+g['driverReviews']:
   q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and q['driverSourcePinsSHA256']==g['driverSourcePinsSHA256']and q['guestDriverSHA256']==g['guestDriverSHA256']and q['guestPreregistrationSHA256']==g['guestPreregistrationSHA256'],'specific source partition review')
  pin(rip['path'],rip)
  need(len(ip)<=pr['maximumRuntimeInputFiles']and sum(z['bytes']for z in ip.values())<=pr['maximumRuntimeInputLogicalBytes'],'runtime complete closure caps')
  for role,expected in [('componentAcceptance',pr['componentAcceptanceStatus']),('machineAcceptance',pr['machineAcceptanceStatus'])]:
   z=g[role];need(z['path']in ip and ip[z['path']]=={k:z[k]for k in ['bytes','sha256']},'accepted proof in runtime closure');q=load(pin(z['path'],z));need(q['status']==expected,'specific actual accepted proof')
   if role=='componentAcceptance':need(q['actualLoaderCalls']==18 and q['savedCase0V3Accepted']is True and q['remainingCases']==list(range(1,16))and q['sourceBoundStateReceiptsAccepted']is True,'actual component18 prerequisite')
   else:
    need(q['actualBuildCalls']==8 and q['positiveQualifiedSiteCount']==1 and q['negativeWholeIdentity']is True,'actual compiled fixture machine prerequisite')
    fp=q['fuelTransactionProof'];need(fp=={'benchEntryUnits':1,'outerUnits':1,'additionalDynamicCharges':0,'privateContextX7Preserved':True,'fuelInteriorIngress':False,'directBenchABI':True},'actual fuel order/context proof')
    need(q['images']==load(Path(pr['buildOutputRoot'])/'images.json'),'exact four compiled images')
  bt=load(Path(pr['buildOutputRoot'])/'terminal.json');need(bt=={'loaderCalls':8,'allChildrenClosed':True,'failure':False},'one closed build8')
 guard();need(not O.exists(),'fresh no-rerun root');O.mkdir();rows=[];images=[];ok=False;save(O/'attempts.json',rows)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
 def capture(p,maximum):
  p=Path(p);need(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=maximum,'bounded captured artifact');extra[str(p)]=receipt(p);save(O/'generated-pins.json',extra);return dict(path=str(p),**extra[str(p)])
 def call(label,args,producer,offset,budget,expectedRC):
  guard();need(len(rows)<10 and label not in [r['label']for r in rows],'finite10 no retry');callenv=dict(env);callenv.pop('KEXE_COMMAND');callenv.pop('KEXE_CAP_RESOURCES_35');callenv.update(KEXE_STRUCTURED_REPORT='1',KEXE_FUEL=str(budget),KEXE_PAIRS='4096',KEXE_STRING_POOL='1048576',KEXE_VECTORS='65536',KEXE_VECTOR_ITEMS='65536');argv=[pr['loader'],producer,str(offset),'1','aarch64','-',*args];r={'index':len(rows)+1,'label':label,'argv':argv,'effectiveEnvironment':callenv.copy(),'timeoutSeconds':pr['wallSeconds'],'state':'started'};rows.append(r);save(O/'attempts.json',rows)
  op=O/(label+'.stdout');ep=O/(label+'.stderr');p=None;reason=None;error=None;cleanup=[];reaped=False
  try:
   with op.open('xb')as out,ep.open('xb')as err:
    try:
     def childlimit():resource.setrlimit(resource.RLIMIT_FSIZE,(pr['fileHardLimitBytes'],pr['fileHardLimitBytes']))
     p=subprocess.Popen(argv,cwd=O,env=callenv,stdout=out,stderr=err,start_new_session=True,preexec_fn=childlimit);r.update(pid=p.pid);save(O/'attempts.json',rows);start=time.monotonic()
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
  need(p is not None and reaped and not reason and not error and not cleanup and p.returncode==expectedRC,'FIRST_FAILURE_STOP_CLOSED');guard();return op.read_bytes(),ep.read_bytes()
 try:
  parser_namespace={'__file__':str(D/'guest-check.py'),'__name__':'pinned_guest_parser'};parser_bytes=(D/'guest-check.py').read_bytes();need(len(parser_bytes)==sp['guest-check.py']['bytes']and H(parser_bytes)==sp['guest-check.py']['sha256'],'pinned parser bytes');exec(compile(parser_bytes,str(D/'guest-check.py'),'exec'),parser_namespace)
  images=load(Path(pr['buildOutputRoot'])/'images.json');comparisons=[]
  for fixtureName,budgets,n in [('positive',[1,2,3],7),('negative',[2,3],-1)]:
   for budget in budgets:
    pair=[]
    for arm in ['OFF','ON']:
     image=next(z for z in images if z['fixture']==fixtureName and z['arm']==arm);need(image['native']['path']in ip,'image in exact runtime closure');pin(image['native']['path'],image['native']);expectedRC=120 if fixtureName=='positive'and budget==1 else 0
     raw,err=call(fixtureName+'-'+str(budget)+'-'+arm,[str(n)],image['native']['path'],image['offset'],budget,expectedRC);record=parser_namespace['verify'](raw,err,fixtureName,budget);pair.append(record)
    need(pair[0]==pair[1],'OFF ON complete result/fuel/four arena parity');comparisons.append({'fixture':fixtureName,'initialFuel':budget,'input':n,'OFF':pair[0],'ON':pair[1]});save(O/'comparisons.json',comparisons)
  guard();need(len(rows)==10 and len(comparisons)==5,'exact10/5');save(O/'report.json',{'status':'COMPLETE_FINITE_FUEL_DAG_EMITTED10_RESULT_FUEL_TRAP_ARENA_ONLY','loaderCalls':10,'priorBuildCalls':8,'cumulativeLoaderCalls':18,'comparisons':comparisons,'rootGOSHA256':gh['sha256'],'sourcePinsSHA256':g['sourcePinsSHA256'],'full19Qualified':False,'performanceQualified':False});ok=True
 except BaseException as ex:save(O/'failure.json',{'error':type(ex).__name__+': '+str(ex),'closedOrStartedCalls':len(rows),'completedImages':len(images),'firstFailureStop':True,'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
if __name__=='__main__':need(len(sys.argv)==2,'root GO only');main(sys.argv[1])
