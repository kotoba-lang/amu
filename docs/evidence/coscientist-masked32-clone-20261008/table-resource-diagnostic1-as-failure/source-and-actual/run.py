"""Inert import. One Python resource diagnostic child; never runs native loader."""
from pathlib import Path
import os,sys,json,hashlib,stat,subprocess,selectors,signal,time
D=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def read(p):return json.loads(Path(p).read_bytes())
def save(p,q):Path(p).write_text(json.dumps(q,indent=2)+'\n')
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=384*1024**2,'bounded nonsymlink input')
 b=p.read_bytes();t=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns),'immutable during hash')
 return {'bytes':len(b),'sha256':H(b)}
def pin(p,q):need(receipt(p)=={k:q[k]for k in ['bytes','sha256']},'exact pin '+str(p));return Path(p)
def main(go):
 gp=Path(go);g=read(gp);gr=receipt(gp);pr=read(D/'preregistration.json');sp=read(D/'source-pins.json');ip=read(D/'input-pins.json');O=D/'run-outputs'
 need(set(g)=={'status','maximumDiagnosticChildren','nativeLoaderCalls','compilerCalls','noRetry','outerExecution','outputRoot','sha256','sourceReviews'},'exact GO keys')
 need(g['status']=='ROOT_GO_RESOURCE_INSTALL_DIAGNOSTIC1_ONLY'and g['maximumDiagnosticChildren']==1 and g['nativeLoaderCalls']==0 and g['compilerCalls']==0 and g['noRetry']is True and g['outerExecution']=='require_escalated'and g['outputRoot']==str(O),'diagnostic only GO')
 names=['run.py','preregistration.json','source-pins.json','input-pins.json'];need(set(g['sha256'])==set(names),'exact registry keys')
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two reviews')
 def guard():
  need(receipt(gp)==gr,'GO immutable')
  for n in names:need(receipt(D/n)['sha256']==g['sha256'][n],'exact reviewed registry')
  for p,q in ip.items():pin(p,q)
  for n,q in sp.items():pin(D/n,q)
  for r in g['sourceReviews']:
   need(set(r)=={'path','bytes','sha256'},'exact review receipt');q=read(pin(r['path'],r));need(q['status']=='PASS_SOURCE_ONLY_RESOURCE_INSTALL_DIAGNOSTIC1'and q['sourcePinsSHA256']==g['sha256']['source-pins.json']and q['driverSHA256']==g['sha256']['run.py'],'exact source review')
 guard();need(not O.exists(),'fresh no-retry outputs');O.mkdir()
 argv=[pr['interpreter']['path'],str(D/'diagnostic-child.py'),'--journal-fd'];env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','PYTHONNOUSERSITE':'1'}
 proc=None;reason=None;cleanup=[];reaped=False;rows=[];outcomes=None;ok=False
 with (O/'resource-journal.jsonl').open('xb',buffering=0)as journal,(O/'stdout').open('xb',buffering=0)as out,(O/'stderr').open('xb',buffering=0)as err:
  argv.append(str(journal.fileno()));attempt={'argv':argv,'environment':env,'nativeLoaderCalls':0,'compilerCalls':0,'state':'started'};save(O/'attempt.json',attempt)
  try:
   proc=subprocess.Popen(argv,cwd=O,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(journal.fileno(),),start_new_session=True)
   attempt['pid']=proc.pid;save(O/'attempt.json',attempt);deadline=time.monotonic()+10
   sel=selectors.DefaultSelector();sizes={'stdout':0,'stderr':0}
   for name,pipe,file in [('stdout',proc.stdout,out),('stderr',proc.stderr,err)]:os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,(name,file))
   while sel.get_map()or proc.poll()is None:
    if time.monotonic()>deadline:reason='outerwall10';break
    for key,_ in sel.select(.02):
     b=os.read(key.fd,65536);name,file=key.data
     if not b:sel.unregister(key.fileobj);key.fileobj.close();continue
     room=65536-sizes[name];file.write(b[:room]);sizes[name]+=min(room,len(b));os.fsync(file.fileno())
     if len(b)>room:reason='bounded_capture_overflow';break
    if reason:break
   sel.close()
  except BaseException as ex:reason='exception';attempt['exception']=repr(ex)
  finally:
   if proc is not None:
    try:
     if reason or proc.poll()is None:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    except BaseException as ex:cleanup.append(repr(ex))
    try:proc.wait(timeout=5);reaped=True
    except BaseException as ex:cleanup.append(repr(ex))
    for pipe in [proc.stdout,proc.stderr]:
     if pipe is not None and not pipe.closed:pipe.close()
   attempt.update(state='terminal'if proc is None or reaped else'unclosed',reason=reason,reaped=reaped,returncode=None if proc is None else proc.returncode,cleanup=cleanup)
 save(O/'attempt.json',attempt)
 try:
  need(proc is not None and reaped and not reason and not cleanup,'one child closed without capture failure')
  raw=(O/'resource-journal.jsonl').read_bytes();need(0<len(raw)<=65536,'bounded journal');rows=[json.loads(line)for line in raw.splitlines()]
  need((O/'stdout').read_bytes()==raw,'durable journal/stdout identity');need((O/'stderr').stat().st_size==0,'empty diagnostic stderr')
  expected=[('RLIMIT_FSIZE',67108864),('RLIMIT_CPU',1800),('RLIMIT_AS',4294967296)]
  from importlib.util import spec_from_file_location,module_from_spec
  spec=spec_from_file_location('pinned_resource_policy',D/'diagnostic-child.py');m=module_from_spec(spec);spec.loader.exec_module(m)
  k=0;failed=False
  for index,(name,budget)in enumerate(expected,1):
   need(k+1<len(rows),'exact before/outcome pair');before,after=rows[k:k+2];k+=2
   need(before['stage']=='before'and before['index']==index and before['limit']==name,'ordered before')
   target=None if before['desired']is None else m.desired(before['before'],budget,before['infinity'])
   if target is None:need('readException'in before and after['outcome']=='failure','resource read/availability failure retained')
   else:need(list(target)==before['desired'],'never raise inherited finite limit')
   need(after['stage']=='outcome'and after['index']==index and after['limit']==name,'ordered outcome')
   if after['outcome']=='failure':failed=True;need(proc.returncode==78 and k==len(rows),'first resource failure stops');break
   need(after['outcome']=='installed'and after['readback']==list(target),'exact installed readback')
  if not failed:need(rows[k:]==[{'stage':'terminal','status':'ALL_THREE_INSTALLED_EXACT_READBACK','nativeLoaderCalls':0,'compilerCalls':0}]and proc.returncode==0,'exact diagnostic completion');ok=True
  outcomes={'status':'RESOURCE_INSTALL_PASS_ONLY_NO_NATIVE_GO'if ok else'RESOURCE_INSTALL_FAILURE_EXACT_LIMIT_RETAINED','rows':rows,'nativeLoaderCalls':0,'compilerCalls':0};save(O/'outcomes.json',outcomes)
 except BaseException as ex:save(O/'failure.json',{'status':'DIAGNOSTIC_PROTOCOL_OR_SUPERVISOR_FAILURE_NO_RETRY','exception':repr(ex)})
 finally:
  save(O/'terminal.json',{'childAttempts':1,'reaped':reaped,'success':ok,'noRetry':True,'nativeLoaderCalls':0,'compilerCalls':0})
 if ok:
  guard();save(O/'completion.json',{'status':'COMPLETE_RESOURCE_INSTALL_DIAGNOSTIC1_ONLY','sourcePinsSHA256':g['sha256']['source-pins.json'],'raw':{n:receipt(O/n)for n in ['resource-journal.jsonl','stdout','stderr','attempt.json','outcomes.json','terminal.json']},'nativeLoaderCalls':0,'compilerCalls':0,'native8Authorized':False})
 return 0 if ok else 78
if __name__=='__main__':need(len(sys.argv)==2,'exact reviewed GO required');sys.exit(main(sys.argv[1]))
