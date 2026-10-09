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
def main(gopath):
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);L=Path(pr['parentSource']).parent
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==10 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['workloadGuestAuthorized']is False,'exact observer10 GO')
 need(g['sourcePinsSHA256']==receipt(D/'source-pins.json')['sha256']and g['driverSHA256']==receipt(D/'run.py')['sha256']and g['preregistrationSHA256']==receipt(D/'preregistration.json')['sha256']and g['inputPinsSHA256']==pr['inputPinsSHA256']==receipt(D/'input-pins.json')['sha256'],'exact registries')
 need(len(g['sourceReviews'])==2 and len({z['path']for z in g['sourceReviews']})==2,'two SOURCE reviews')
 extra={}
 def guard():
  need(receipt(gp)==gh and receipt(D/'source-pins.json')['sha256']==g['sourcePinsSHA256']and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256']and receipt(D/'preregistration.json')['sha256']==g['preregistrationSHA256'],'immutable GO/source/input registries')
  for n,z in sp.items():pin(D/n,z)
  need(len(ip)<=2048 and sum(z['bytes']for z in ip.values())<=402653184,'closure cap')
  total=0
  for p,z in ip.items():
   pp=Path(p);st=pp.lstat();need(stat.S_ISREG(st.st_mode)and not pp.is_symlink()and st.st_size==z['bytes'],'stat guard');total+=st.st_size;need(total<=402653184,'cap before read')
  for p,z in ip.items():pin(p,z)
  need(receipt(L/'source-pins.json')['sha256']==pr['parentSourcePinsSHA256'],'exact structured LC parent registry')
  em=load(L/'source-pins.json');need(set(em)=={'format','files'}and em['format']=='isolated-source-pins/v1'and type(em['files'])is list and 0<len(em['files'])<=2048,'LC parent schema')
  need(len({z['path']for z in em['files']})==len(em['files']),'unique LC source receipts')
  for z in em['files']:
   ep=Path(z['path']);need(set(z)=={'path','bytes','sha256'}and ep.is_absolute()and ep.is_relative_to(L)and str(ep)in ip,'owned registered LC source');pin(ep,z)
  for p,z in extra.items():pin(p,z)
  need(ip[pr['producer']]['sha256']==pr['producerSHA256']=='258670d2371f3c03167fb02f574c6597479a1ce3e0af9a42cac8e41499d56931'and ip[pr['loader']]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','exact producer/loader')
  for k in ['actualProducerProof','actualLoaderProof']:need(load(pr[k])['status']==pr[k+'Status'],'accepted actual prerequisite')
  ar=load(pr['actualProducerProof']);need(ar['counts']['closedLoaderCalls']==4 and next(z for z in ar['images']if z['arm']=='ON')['native']==dict(path=pr['producer'],**ip[pr['producer']]),'actual4 correspondence')
  for z in g['sourceReviews']:
   r=load(pin(z['path'],z));need(r['status']==pr['sourceReviewStatus']and r['sourcePinsSHA256']==g['sourcePinsSHA256']and r['driverSHA256']==g['driverSHA256']and r['preregistrationSHA256']==g['preregistrationSHA256'],'specific complete review')
 guard();need(not O.exists(),'fresh output');O.mkdir();rows=[];images=[];ok=False;save(O/'attempts.json',rows)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
 def capture(p,maximum):
  need(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=maximum,'bounded artifact');extra[str(p)]=receipt(p);save(O/'generated-pins.json',extra);return dict(path=str(p),**extra[str(p)])
 def call(label,args,producer=None):
  guard();need(len(rows)<10 and label not in [r['label']for r in rows],'finite18 no retry');argv=[pr['loader'],producer or pr['producer'],'0','0','aarch64','35,37,38,39','--',*args];r={'index':len(rows)+1,'label':label,'argv':argv,'effectiveEnvironment':env.copy(),'timeoutSeconds':pr['wallSeconds'],'state':'started'};rows.append(r);save(O/'attempts.json',rows)
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
  decoderPath=D/'decode.py';decoderBytes=decoderPath.read_bytes();decoderPin=sp['decode.py'];need(len(decoderBytes)==decoderPin['bytes']and H(decoderBytes)==decoderPin['sha256'],'verified exact decoder buffer')
  decoderNamespace={'__file__':str(decoderPath),'__name__':'pinned_lc_decoder_source_buffer'};exec(compile(decoderBytes,str(decoderPath),'exec'),decoderNamespace);decode=SimpleNamespace(parse=decoderNamespace['parse'])
  sources={}
  for e in pr['entries']:
   n=e['workload'];p=O/(n+'.kotoba');p.write_bytes(Path(e['source']['path']).read_bytes());p.chmod(0o444);capture(p,4194304);sources[n]=p
  diagnostic=O/'unity-observer.kotoba';diagnostic.write_bytes(Path(pr['observerSource']).read_bytes());diagnostic.chmod(0o444);capture(diagnostic,4194304)
  ordinary={}
  def build(label,src,symbol,producer):
   k=O/(label+'.kseed');b=O/(label+'.bin');raw=call(label+'-compile',['compile',str(src),'--target','aarch64-macos','--output',str(k)],producer);need(b':ok true'in raw and b':ok false'not in raw,'compile success');capture(k,4194560)
   raw2=call(label+'-extract',['extract-native',str(k),'--symbol',symbol,'--output',str(b)],producer);capture(b,4194304);need(b':ok true'in raw2 and b':ok false'not in raw2,'extract success');offsets=re.findall(rb':offset ([0-9]+)\b',raw2);need(len(offsets)==1,'unique offset');offset=int(offsets[0]);blob=k.read_bytes();m=re.match(rb'KSEED1 ([1-9][0-9]*) ([0-9]+)\n',blob);need(m is not None,'container');cut=blob.index(b'\n\n')+2;payload=blob[cut:];need(len(payload)==int(m[1])and payload==b.read_bytes(),'whole payload');exports=blob[m.end():cut-2].decode('ascii').splitlines();need(len(exports)==int(m[2])and len(set(exports))==len(exports)and (symbol+' '+str(offset)+' '+('0'if symbol=='main'else'1'))in exports,'exact selected arity');need(offset%4==0 and 0<=offset<len(payload),'entry bounds');return k,b,offset,raw
  for e in pr['entries']:
   ordinary[e['workload']]=build('ordinary-'+e['workload'],sources[e['workload']],e['symbol'],pr['producer'])
  dk,db,do,dr=build('observer',diagnostic,'main',pr['producer']);need(do==0 and kseed(dk.read_bytes())==db.read_bytes(),'sole diagnostic main0')
  for e in pr['entries']:
   n=e['workload'];k,b,offset,raw=build('observed-'+n,sources[n],e['symbol'],str(db));old=ordinary[n];need(k.read_bytes()==old[0].read_bytes()and b.read_bytes()==old[1].read_bytes()and offset==old[2],'whole ordinary LC identity');v=decode.parse(raw,b.read_bytes());save(O/(n+'-owners.json'),v);capture(O/(n+'-owners.json'),16777216);need(v['eligibleOwners']>0,'STOP_ZERO_ELIGIBLE_OWNER');images.append({'workload':n,'container':receipt(k),'native':receipt(b),'offset':offset,'eligibleOwners':v['eligibleOwners']});save(O/'images.json',images)
  guard();need(len(rows)==10 and len(images)==2,'exact10/2');save(O/'report.json',{'status':'COMPLETE_READONLY_LC_OWNER_OBSERVER10_IDENTITY_ONLY','loaderCalls':10,'images':images,'sourcePinsSHA256':g['sourcePinsSHA256'],'rootGOSHA256':gh['sha256'],'runtimeABITrapFuelQualified':False,'performanceQualified':False});ok=True
 except BaseException as ex:save(O/'failure.json',{'error':type(ex).__name__+': '+str(ex),'loaderCalls':len(rows),'firstFailureStop':True,'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
if __name__=='__main__':need(len(sys.argv)==2,'root GO only');main(sys.argv[1])
