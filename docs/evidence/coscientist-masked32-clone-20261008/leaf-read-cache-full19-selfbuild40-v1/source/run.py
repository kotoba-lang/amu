"""Inert import. Exactly10 compile/extract children after specific root GO only."""
from pathlib import Path
import hashlib,json,os,sys,re,stat,subprocess,signal,time,resource
from types import SimpleNamespace
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
def parse_container(b):
 need(0<len(b)<=4194560,'bounded container');m=re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\n',b);need(m is not None,'KSEED header');n=int(m[2]);need(n<=128,'export cap');cut=b.find(b'\n\n',m.end());need(cut>=m.end(),'export separator');lines=b[m.end():cut].splitlines();need(len(lines)==n,'export count');exports=[]
 for line in lines:
  q=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);need(q is not None,'export schema');exports.append((q[1].decode(),int(q[2]),int(q[3])))
 payload=b[cut+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1]),'whole declared payload');need(len({z[0]for z in exports})==n,'unique names');need(all(z[1]%4==0 and z[1]+4<=len(payload)and z[2]<=32 for z in exports),'bounded aligned entries');return payload,exports
def main(gopath):
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);L=Path(pr['parentSource']).parent
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==40 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['workloadGuestAuthorized']is False,'exact40 GO')
 need(g['sourcePinsSHA256']==receipt(D/'source-pins.json')['sha256']and g['driverSHA256']==receipt(D/'run.py')['sha256']and g['preregistrationSHA256']==receipt(D/'preregistration.json')['sha256']and g['inputPinsSHA256']==pr['inputPinsSHA256']==receipt(D/'input-pins.json')['sha256'],'exact registries')
 need(len(g['sourceReviews'])==2 and len({z['path']for z in g['sourceReviews']})==2,'two specific SOURCE reviews');extra={}
 def guard():
  need(receipt(gp)==gh and receipt(D/'source-pins.json')['sha256']==g['sourcePinsSHA256']and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256']and receipt(D/'preregistration.json')['sha256']==g['preregistrationSHA256'],'immutable registries')
  for n,z in sp.items():pin(D/n,z)
  need(len(ip)==pr['exactInputFiles']<=2048 and sum(z['bytes']for z in ip.values())==pr['exactInputLogicalBytes']<=402653184,'closure cap');total=0
  for p,z in ip.items():
   q=Path(p);st=q.lstat();need(stat.S_ISREG(st.st_mode)and not q.is_symlink()and st.st_size==z['bytes'],'stat before read');total+=st.st_size;need(total<=402653184,'aggregate before hash')
  for p,z in ip.items():pin(p,z)
  need(receipt(L/'source-pins.json')['sha256']==pr['parentSourcePinsSHA256'],'structured parent pins');em=load(L/'source-pins.json');need(set(em)=={'format','files'}and em['format']=='isolated-source-pins/v1'and type(em['files'])is list and len({z['path']for z in em['files']})==len(em['files']),'structured exact schema')
  for z in em['files']:need(set(z)=={'path','bytes','sha256'}and Path(z['path']).is_relative_to(L)and str(z['path'])in ip,'owned source receipt');pin(z['path'],z)
  for p,z in extra.items():pin(p,z)
  need(ip[pr['producer']]['sha256']==pr['producerSHA256']=='258670d2371f3c03167fb02f574c6597479a1ce3e0af9a42cac8e41499d56931'and ip[pr['loader']]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','producer/loader')
  for k in ['actualProducerProof','actualLoaderProof','actualOwnerProof']:need(load(pr[k])['status']==pr[k+'Status'],'exact actual prerequisite')
  ar=load(pr['actualProducerProof']);need(ar['counts']['closedLoaderCalls']==4 and next(z for z in ar['images']if z['arm']=='ON')['native']==dict(path=pr['producer'],**ip[pr['producer']]),'producer actual correspondence')
  owner=load(pr['actualOwnerProof']);need(owner['inputPinsSHA256']==receipt(pr['actualOwnerInputPins'])['sha256']and owner['counts']['closedLoaderCalls']==10 and owner['counts']['ordinaryWorkloads']==2 and owner['checks']['wholeOrdinaryObservedContainersNativeExportsOffsetsIdentical']is True,'actual owner10 join')
  mat=load(pr['canonicalMatrix']);need(mat['format']=='amu.embench-comparison-matrix-spec/v1'and mat['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'and len(mat['entries'])==19,'canonical19')
  need(len(pr['entries'])==19 and len({e['workload']for e in pr['entries']})==19,'all19 unique')
  for e,me in zip(pr['entries'],mat['entries']):need(e['workload']==me['workload']and e['symbol']==me['symbol']and e['iterations']==me['iterations']and e['source']['sha256']==me['expectedSourceSha256']and e['source']['path'].endswith('/'+me['source']),'matrix exact whole-source binding');pin(e['source']['path'],e['source'])
  need([e['workload']for e in pr['entries']if 'retained'in e]==['md5sum','nettle-sha256'],'exact retained complement')
  for z in g['sourceReviews']:
   r=load(pin(z['path'],z));need(r['status']==pr['sourceReviewStatus']and r['sourcePinsSHA256']==g['sourcePinsSHA256']and r['driverSHA256']==g['driverSHA256']and r['preregistrationSHA256']==g['preregistrationSHA256'],'specific complete reviews')
 guard();need(not O.exists(),'fresh namespace');O.mkdir();rows=[];images=[];generations=[];ok=False;save(O/'attempts.json',rows)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
 save(O/'effective-environment.json',env)
 def capture(p,maximum):
  need(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=maximum,'bounded artifact');extra[str(p)]=receipt(p);save(O/'generated-pins.json',extra);return dict(path=str(p),**extra[str(p)])
 def call(label,args,producer=None):
  guard();need(len(rows)<40 and label not in [r['label']for r in rows],'finite40 no retry');argv=[pr['loader'],producer or pr['producer'],'0','0','aarch64','35,37,38,39','--',*args];r={'index':len(rows)+1,'label':label,'argv':argv,'effectiveEnvironment':env.copy(),'timeoutSeconds':pr['wallSeconds'],'state':'started'};rows.append(r);save(O/'attempts.json',rows)
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
  def build(label,src,symbol,arity,producer):
   k=O/(label+'.kseed');b=O/(label+'.bin');raw=call(label+'-compile',['compile',str(src),'--target','aarch64-macos','--output',str(k)],producer);need(b':ok true'in raw and b':ok false'not in raw,'compile success');kr=capture(k,pr['containerBytesMaximum']);payload,exports=parse_container(k.read_bytes());entry=[z for z in exports if z[0]==symbol];need(len(entry)==1 and entry[0][2]==arity,'exact selected export ABI')
   if arity==0:need(exports==[('main',0,0)],'sole main0 compiler')
   raw2=call(label+'-extract',['extract-native',str(k),'--symbol',symbol,'--output',str(b)],producer);br=capture(b,pr['nativeBytesMaximum']);need(b':ok true'in raw2 and b':ok false'not in raw2,'extract success');offsets=re.findall(rb':offset ([0-9]+)\b',raw2);need(len(offsets)==1 and int(offsets[0])==entry[0][1],'exact extract offset');need(b.read_bytes()==payload,'whole native payload');return dict(label=label,container=kr,native=br,exports=exports,offset=entry[0][1])
  owner=load(pr['actualOwnerProof'])
  for e in pr['entries']:
   n=e['workload']
   if 'retained'in e:
    z=e['retained'];k=pin(z['container']['path'],z['container']);b=pin(z['native']['path'],z['native']);payload,exports=parse_container(k.read_bytes());need(payload==b.read_bytes(),'retained whole payload');entry=[q for q in exports if q[0]==e['symbol']];need(len(entry)==1 and entry[0][2]==1,'retained ABI');w=next(q for q in owner['workloads']if q['workload']==n);need(receipt(b)=={k:w['native'][k]for k in ['bytes','sha256']}and entry[0][1]==w['offset'],'actual retained identity');image=dict(workload=n,retained=True,container=z['container'],native=z['native'],exports=exports,offset=entry[0][1]);images.append(image)
   else:
    src=O/(n+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());src.chmod(0o444);need(receipt(src)=={k:e['source'][k]for k in ['bytes','sha256']},'exact source copy');capture(src,4194304);image=build(n,src,e['symbol'],1,pr['producer']);image.update(workload=n,retained=False);images.append(image)
   save(O/'images.json',images)
  need(len(rows)==34 and len(images)==19,'original19 joined38 phase boundary');save(O/'original19-boundary.json',dict(newClosedCalls=34,retainedClosedCalls=4,joinedClosedCompileExtractCalls=38,workloads=19,generatedWorkloadExecution=False))
  source=O/'unity-lc-on.kotoba';source.write_bytes(Path(pr['parentSource']).read_bytes());source.chmod(0o444);need(receipt(source)==ip[pr['parentSource']],'immutable exact selfbuild source');capture(source,4194304);producer=pr['producer'];previous=None
  for generation in [1,2,3]:
   image=build('G'+str(generation),source,'main',0,producer);image['generation']=generation
   if previous is not None:need(Path(image['container']['path']).read_bytes()==Path(previous['container']['path']).read_bytes()and Path(image['native']['path']).read_bytes()==Path(previous['native']['path']).read_bytes(),'G1 G2 G3 fixed point whole artifact')
   else:
    old=Path(pr['producer']).read_bytes();new=Path(image['native']['path']).read_bytes();image['G0ToG1NativeEquality']=old==new;image['G0ToG1FirstDifferentByte']=next((i for i,(a,b)in enumerate(zip(old,new))if a!=b),None if len(old)==len(new)else min(len(old),len(new)));image['G0ToG1EqualityRequired']=False;oldContainer=next(z for z in load(pr['actualProducerProof'])['images']if z['arm']=='ON')['container'];image['G0Container']=oldContainer;image['G0Native']=dict(path=pr['producer'],**ip[pr['producer']]);image['G0ToG1ContainerEquality']=Path(oldContainer['path']).read_bytes()==Path(image['container']['path']).read_bytes()
   generations.append(image);save(O/'generations.json',generations);previous=image;producer=image['native']['path']
  guard();need(len(rows)==40 and len(generations)==3,'exact40');save(O/'report.json',dict(status='COMPLETE_LC_ORIGINAL19_COMPILATION_G1_G2_G3_FIXEDPOINT_ONLY',closedLoaderCalls=40,original19JoinedCompileExtractCalls=38,retainedOrdinaryCalls=4,selfbuildCalls=6,images=images,generations=generations,sourcePinsSHA256=g['sourcePinsSHA256'],rootGOSHA256=gh['sha256'],runtimeWorkloadExecution=False,runtimeABITrapFuelQualified=False,performanceQualified=False,officialScore=False,fullSelfhostGoalAchieved=False));ok=True
 except BaseException as ex:save(O/'failure.json',dict(error=type(ex).__name__+': '+str(ex),loaderCalls=len(rows),firstFailureStop=True,noRetry=True));raise
 finally:save(O/'terminal.json',dict(loaderCalls=len(rows),allChildrenClosed=all(r['state']=='terminal'for r in rows),failure=not ok))
if __name__=='__main__':need(len(sys.argv)==2,'root GO only');main(sys.argv[1])
