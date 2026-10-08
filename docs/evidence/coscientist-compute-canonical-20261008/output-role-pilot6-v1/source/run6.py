from pathlib import Path
import json,hashlib,os,sys,subprocess,signal,time,re,stat,resource
from census import parse
from decode import parse as parse_output
from artifact import container,counters
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def need(x,m):
 if not x:raise AssertionError(m)
def pin(p):
 p=Path(p);st=p.lstat();need(stat.S_ISREG(st.st_mode) and not p.is_symlink() and 0<=st.st_size<=536870912,'bounded regular nonsymlink input');h=hashlib.sha256();n=0
 with p.open('rb') as f:
  while True:
   b=f.read(1048576)
   if not b:break
   n+=len(b);need(n<=536870912,'bounded hash');h.update(b)
 st2=p.lstat();need((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(st2.st_dev,st2.st_ino,st2.st_size,st2.st_mtime_ns) and n==st.st_size,'file immutable during hash');return {'bytes':n,'sha256':h.hexdigest()}
def main(gopath,out):
 pr=load(D/'pilot-preregistration.json');sp=load(D/'source-pins.json');go=load(gopath);gp=pin(gopath);root=Path(out).resolve();need(go['sourcePinsSHA256']==pin(D/'source-pins.json')['sha256'] and go['status']==pr['rootGOStatus'] and go['compileAuthorized'] is True and go['guestAuthorized'] is False and go['timingAuthorized'] is False and go['maxCalls']==6 and go['requiresEscalatedExecution'] is True,'exact finite compile only GO');reviews=go['sourceReviews'];need(len(reviews)==2 and len({r['path'] for r in reviews})==2,'two independent review slots')
 for r in reviews:
  need(pin(r['path'])=={'bytes':r['bytes'],'sha256':r['sha256']},'reviewpin');j=load(r['path']);need(j['sourcePinsSHA256']==go['sourcePinsSHA256'] and j['status']==pr['sourceReviewStatus'],'specific reviewed source')
 need(str(root)==go['outputDirectory'] and str(root)==pr['freshOutputDirectory'] and not root.exists(),'fresh dedicated output');root.mkdir();(root/'sources').mkdir();(root/'ports').mkdir();rows=[];images=[];generated={};save(root/'attempts.json',rows)
 fixed=[pr['loader'],pr['producer'],*[e[k]for e in pr['entries']for k in ['source','oldNative','oldContainer']]]
 need(pin(D/'origin-pins.json')['sha256']==pr['inputClosureSHA256'] and len(load(D/'origin-pins.json'))==pr['inputClosureFiles'],'bounded exact origin closure')
 for z in pr['proofs']:need(load(z['path'])['status']==z['status'],'exact actual prerequisite status')
 def guard():
  need(pin(gopath)==gp and pin(D/'source-pins.json')['sha256']==go['sourcePinsSHA256'],'GO/sourcepins immutable')
  for p,v in sp.items():need(pin(D/p)==v,'source guard')
  for p,v in load(D/'origin-pins.json').items():need(pin(p)==v,'origin guard')
  for z in fixed:need(pin(z['path'])=={'bytes':z['bytes'],'sha256':z['sha256']},'immutable input')
  for p,v in generated.items():need(pin(p)==v,'generated guard')
  for z in reviews:need(pin(z['path'])=={'bytes':z['bytes'],'sha256':z['sha256']},'review immutable')
 def capture(p):
  need(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<=pr['nativeArtifactBytes'],'bounded artifact');generated[str(p)]=pin(p);save(root/'generated-pins.json',generated)
 env={};kx={'KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(root),'KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_STRING_POOL':str(pr['stringPoolBytes']),'KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':str(pr['vectorItems']),'KEXE_ARENA_USE':'1','KEXE_FUEL':'off'};env.update({'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(root),'LANG':'C','LC_ALL':'C','TZ':'UTC'});env.update(kx)
 def call(label,producer,args):
  guard();need(len(rows)<6,'6hardcap');p=root/'ports'/label;p.mkdir(exist_ok=True);n=len(rows)+1;op=p/(str(n)+'.stdout');ep=p/(str(n)+'.stderr');argv=[pr['loader']['path'],str(producer),'0','0','aarch64','35,37,38,39','--',*args];r={'index':n,'label':label,'argv':argv,'kexeEnvironment':dict(kx),'effectiveEnvironment':dict(env),'removedInheritedKexeKeys':sorted(k for k in os.environ if k.startswith('KEXE_')),'state':'started'};rows.append(r);save(root/'attempts.json',rows)
  q=None;why=None;raised=None;cleanupErrors=[];reaped=False
  try:
   with op.open('xb')as o,ep.open('xb')as e:
    try:
     def childFileLimit():resource.setrlimit(resource.RLIMIT_FSIZE,(pr['hardOutputFileLimitBytes'],pr['hardOutputFileLimitBytes']))
     q=subprocess.Popen(argv,env=env,stdout=o,stderr=e,start_new_session=True,preexec_fn=childFileLimit);r.update(processStarted=True,pid=q.pid);save(root/'attempts.json',rows);start=time.monotonic()
     while q.poll() is None:
      if time.monotonic()-start>pr['wallSecondsPerProcess']:why='wallcap'
      if op.stat().st_size>pr['stdoutBytesPerProcess'] or ep.stat().st_size>pr['stderrBytesPerProcess']:why='outputcap'
      if why:break
      time.sleep(.02)
    except BaseException as exc:raised=exc;why=why or ('exception:'+type(exc).__name__)
    finally:
     if q is not None:
      try:
       if raised is not None or why is not None or q.poll() is None:os.killpg(q.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      except BaseException as exc:
       cleanupErrors.append('kill-or-poll:'+type(exc).__name__)
       try:os.killpg(q.pid,signal.SIGKILL)
       except ProcessLookupError:pass
       except BaseException as second:cleanupErrors.append('fallback-kill:'+type(second).__name__)
      try:q.wait(timeout=10);reaped=True
      except BaseException as exc:cleanupErrors.append('reap:'+type(exc).__name__)
  except BaseException as exc:
   raised=raised or exc;why=why or ('file-or-cleanup:'+type(exc).__name__)
  # Raw files exist before diagnostics. Honest unclosed state if no successful reap.
  rc=q.returncode if q is not None else None
  if op.exists() and ep.exists() and (op.stat().st_size>pr['stdoutBytesPerProcess'] or ep.stat().st_size>pr['stderrBytesPerProcess']):why=why or 'outputcap'
  r.update(state='terminal' if q is None or reaped else 'unclosed',processStarted=q is not None,processReaped=reaped,returncode=rc,terminationReason=why,cleanupErrors=cleanupErrors,stdoutPath=str(op),stderrPath=str(ep),stdout=None,stderr=None);save(root/'attempts.json',rows)
  try:
   if op.exists() and op.stat().st_size<=536870912:r['stdout']=pin(op)
   if ep.exists() and ep.stat().st_size<=536870912:r['stderr']=pin(ep)
  except BaseException as exc:raised=raised or exc;r['rawHashFailure']=type(exc).__name__
  finally:save(root/'attempts.json',rows)
  if raised is not None:raise raised
  need(q is not None and reaped and not cleanupErrors and not why and rc==0  ,'command closed success');arena=counters(ep.read_bytes());r['arenaCounters']=arena;save(root/'attempts.json',rows);need(arena['status']=='valid' and arena['entireStderrIsCounterLine'],'strict17 arena counters');guard()
  # A bounded stream scan, never load 512MiB stdout into RAM.
  offset=[];ok=False
  with op.open('rb')as f:
   while True:
    line=f.readline(65537)
    if not line:break
    need(len(line)<=65536,'line cap');need(b':ok false' not in line,'compiler refusal');ok=ok or b':ok true' in line;offset+=re.findall(rb':offset (\d+)\b',line)
  need(ok,'command successful receipt');return offset
 def extract(label,producer,container,native,symbol):
  offsets=call(label,producer,['extract-native',str(container),'--symbol',symbol,'--output',str(native)]);capture(native);need(len(offsets)==1,'uniqueoffset');offset=int(offsets[0]);off=native.with_suffix('.offset');off.write_text(str(offset)+'\n');capture(off);need(0<=offset<native.stat().st_size and offset%4==0,'bounded aligned entry');return offset
 try:
  guard();(root/'sources/unity-result.kotoba').write_bytes((D/'unity-result.kotoba').read_bytes());capture(root/'sources/unity-result.kotoba');obs=root/'observer.kseed';nb=root/'observer.bin';call('observer-build',pr['producer']['path'],['compile',str(root/'sources/unity-result.kotoba'),'--target','aarch64-macos','--output',str(obs)]);capture(obs);need(container(obs.read_bytes())[0]==[{'name':'main','offset':0,'arity':0}],'sole main0');guard();need(extract('observer-extract',pr['producer']['path'],obs,nb,'main')==0,'observer main0');need(container(obs.read_bytes())[1]==nb.read_bytes(),'compiler full payload')
  for e in pr['entries']:
   n=e['workload'];src=root/'sources'/(n+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());capture(src);p=root/'ports'/n;p.mkdir();image=p/'image.kseed';native=p/'native.bin';call(n,nb,['compile',str(src),'--target','aarch64-macos','--output',str(image)]);capture(image);guard();offset=extract(n,nb,image,native,e['symbol']);need(native.read_bytes()==Path(e['oldNative']['path']).read_bytes() and image.read_bytes()==Path(e['oldContainer']['path']).read_bytes() and offset==e['offset'],'diagnostic original emitter identity');qualification=parse((p/(str(len(rows)-1)+'.stdout')).read_bytes());need(qualification['activations'],'genuine analysis activation records');qualification['declaredOutput']=parse_output((p/(str(len(rows)-1)+'.stdout')).read_bytes());need(qualification['declaredOutput']['calls']==qualification['queryCalls'],'complete output query count');save(p/'frequency.json',qualification);capture(p/'frequency.json');ex,payload=container(image.read_bytes());need(payload==native.read_bytes() and any(x=={'name':e['symbol'],'offset':offset,'arity':1}for x in ex),'whole payload and exact selected export');images.append({'frequency':qualification,'workload':n,'source':pin(src),'native':pin(native),'container':pin(image),'exports':ex,'offset':offset});save(root/'images.json',images)
  guard();need(len(rows)==6 and len(images)==2,'exact6/2');save(root/'report.json',{'status':'PASS_ACTUAL_DECLARED_OUTPUT_ROLE_CRC32_SLRE_PILOT6_BYTE_IDENTITY_ONLY','calls':6,'images':2,'queryCalls':sum(x['frequency']['queryCalls']for x in images),'unsupportedProjectionQueries':sum(x['frequency']['unsupported']for x in images),'sameTargetModeRepeats':sum(x['frequency']['sameTargetModeRepeats']for x in images),'fourBoundProjectionRepeats':sum(x['frequency']['fourBoundProjectionRepeats']for x in images),'existingMemoHits':sum(x['frequency']['existingMemoHits']for x in images),'fullComputeCIDQualified':False,'fullResultCIDQualified':False,'outputRoleClosed':False,'original19Qualified':False,'newQuerySkips':0,'C2':False,'performanceClaim':False})
 except BaseException as e:save(root/'failure.json',{'reason':repr(e),'calls':len(rows),'policy':'STOP_FIRST_FAILURE_NO_RETRY'});raise
 finally:save(root/'terminal.json',{'calls':len(rows),'allCallsClosed':all(r['state']=='terminal'for r in rows),'images':len(images),'failure':(root/'failure.json').exists()})
if __name__=='__main__':need(len(sys.argv)==3,'GO/output');main(sys.argv[1],sys.argv[2])
