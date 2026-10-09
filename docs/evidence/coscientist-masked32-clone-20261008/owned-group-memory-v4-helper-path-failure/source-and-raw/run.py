"""Import inert. Fixed two-Python-child owned-group read-only qualification only."""
from pathlib import Path
import os,sys,json,hashlib,stat,subprocess,selectors,time,signal,threading,importlib.util,ctypes
D=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def read(p):return json.loads(Path(p).read_bytes())
def save(p,q):Path(p).write_text(json.dumps(q,indent=2)+'\n')
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=384*1024**2,'bounded nonsymlink');b=p.read_bytes();t=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns),'immutable hash');return {'bytes':len(b),'sha256':H(b)}
def pin(p,q):need(receipt(p)=={k:q[k]for k in ['bytes','sha256']},'exact pin');return Path(p)
def main(gopath):
 gp=Path(gopath);g=read(gp);gr=receipt(gp);pr=read(D/'preregistration.json');sp=read(D/'source-pins.json');ip=read(D/'input-pins.json');O=D/'run-outputs'
 names=['run.py','preregistration.json','source-pins.json','input-pins.json']
 need(set(g)=={'status','maximumPythonChildren','maximumMemorySamples','nativeLoaderCalls','setters','noRetry','outerExecution','outputRoot','sha256','sourceReviews'},'exact GO keys')
 need(g['status']=='ROOT_GO_OWNED_GROUP_MEMORY_QUALIFICATION2_ONLY'and g['maximumPythonChildren']==2 and g['maximumMemorySamples']==8 and g['nativeLoaderCalls']==0 and g['setters']==0 and g['noRetry']is True and g['outerExecution']=='require_escalated'and g['outputRoot']==str(O),'exact qualification GO')
 need(set(g['sha256'])==set(names)and len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'exact review registry')
 def guard():
  need(receipt(gp)==gr,'GO immutable')
  for n in names:need(receipt(D/n)['sha256']==g['sha256'][n],'exact registry')
  need(len(ip)<=64 and sum(q['bytes']for q in ip.values())<=512*1024**2,'input closure bounds')
  for p,q in ip.items():pin(p,q)
  for n,q in sp.items():pin(D/n,q)
  for r in g['sourceReviews']:
   need(set(r)=={'path','bytes','sha256'},'exact review receipt');q=read(pin(r['path'],r));need(q['status']=='PASS_SOURCE_ONLY_OWNED_GROUP_MEMORY_QUALIFICATION2'and q['sourcePinsSHA256']==g['sha256']['source-pins.json']and q['driverSHA256']==g['sha256']['run.py'],'specific SOURCE review')
 guard();need(not O.exists(),'fresh no retry');O.mkdir();spec=importlib.util.spec_from_file_location('pinned_adapter',D/'adapter.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 proc=None;watch=None;api=None;anchorLock=threading.Lock();groupKillIssued=False;signalAuthority=False;waitEntered=False;waitUncertain=False;reaped=False;ok=False;cleanup=[];stop=threading.Event();expired=threading.Event();sel=selectors.DefaultSelector();pending=b'';phaseRows=[];sampleRows=[];count={'stdout':0,'stderr':0};deadline=time.monotonic()+10
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','PYTHONNOUSERSITE':'1'};argv=[pr['interpreter']['path'],str(D/'fixture.py'),'leader'];attempt={'argv':argv,'environment':env,'state':'started','maximumPythonChildren':2,'nativeLoaderCalls':0,'setters':0};save(O/'attempt.json',attempt)
 with (O/'stdout').open('xb',buffering=0)as out,(O/'stderr').open('xb',buffering=0)as err,(O/'receipts.jsonl').open('xb',buffering=0)as journal:
  journalBytes=0
  def durable(q):
   nonlocal journalBytes
   b=(json.dumps(q,sort_keys=True)+'\n').encode();need(journalBytes+len(b)<=65536,'durable receipt cap');need(journal.write(b)==len(b),'complete journal write');os.fsync(journal.fileno());journalBytes+=len(b)
  def timecheck():need(not expired.is_set()and time.monotonic()<deadline,'wall10')
  def watchdog():
   nonlocal groupKillIssued,reaped
   if not stop.wait(max(0,deadline-time.monotonic())):
    expired.set()
    with anchorLock:
     if proc is not None and proc.returncode is not None:reaped=True
     if proc is not None and signalAuthority and not waitEntered and proc.returncode is None and not reaped and not stop.is_set():
      try:os.killpg(proc.pid,signal.SIGKILL);groupKillIssued=True
      except ProcessLookupError:pass
      except BaseException as ex:cleanup.append('watchdog:'+repr(ex))
  def phase(name):
   nonlocal pending
   while b'\n'not in pending:
    timecheck()
    for key,_ in sel.select(.02):
     b=os.read(key.fd,4096);stream,file=key.data
     if not b:sel.unregister(key.fileobj);key.fileobj.close();continue
     room=65536-count[stream];file.write(b[:room]);os.fsync(file.fileno());count[stream]+=min(room,len(b));need(len(b)<=room,'capture overflow')
     if stream=='stdout':pending+=b
    need(sel.get_map()or b'\n'in pending,'premature EOF')
   line,pending=pending.split(b'\n',1);q=json.loads(line);need(q['phase']==name and q['pid']==proc.pid,'ordered ready phase');phaseRows.append(q);durable({'kind':'phase','row':q});return q
  def release(command):
   timecheck();proc.stdin.write(command+b'\n');proc.stdin.flush();durable({'kind':'release','command':command.decode()})
  def sample(expected,n):
   for _ in range(n):
    timecheck();q=sampler.sample();need([r['pid']for r in q['members']]==sorted(expected),'ready phase exact members');timecheck();sampleRows.append(q);durable({'kind':'sample','row':q});time.sleep(.02)
  try:
   proc=subprocess.Popen(argv,cwd=O,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   signalAuthority=True;attempt['pid']=proc.pid;save(O/'attempt.json',attempt);watch=threading.Thread(target=watchdog,daemon=True);watch.start()
   for name,pipe,file in [('stdout',proc.stdout,out),('stderr',proc.stderr,err)]:os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,(name,file))
   q=phase('one-ready');need(q['pgid']==proc.pid,'owned leader');api=m.DarwinOwnedGroupAPI();sampler=m.OwnedGroupSampler(api,proc.pid);sample([proc.pid],2)
   release(b'spawn');q=phase('two-ready');helper=q['helperPID'];need(q['pgid']==proc.pid and 0<helper<2**31 and helper!=proc.pid and q['helperArgv']==[pr['interpreter']['path'],str(D/'fixture.py'),'helper'],'fixed second Python child');sample([proc.pid,helper],4)
   release(b'drop');q=phase('one-again-ready');need(q['helperPID']==helper and q['helperReaped']is True and q['helperReturncode']==0,'helper reaped before sample');sample([proc.pid],2)
   release(b'finish');q=phase('leader-complete');need(q=={'phase':'leader-complete','pid':proc.pid,'childStarts':2,'helperReaped':True},'exact fixture completion');proc.stdin.close();stop.set();watch.join(timeout=.1);need(not watch.is_alive(),'watchdog closed before normal reap');need(anchorLock.acquire(timeout=max(.001,deadline-time.monotonic())),'normal reap ownership lock')
   signalAuthority=False;waitEntered=True
   try:proc.wait(timeout=min(5,max(.001,deadline-time.monotonic())))
   except BaseException:
    waitUncertain=True;raise
   finally:
    reaped=proc.returncode is not None
    anchorLock.release()
   timecheck()
   need(proc.returncode==0 and len(sampleRows)==8,'exact eight reads and normal leader')
   while sel.get_map():
    timecheck()
    for key,_ in sel.select(.02):
     b=os.read(key.fd,4096);stream,file=key.data
     if not b:sel.unregister(key.fileobj);key.fileobj.close();continue
     room=65536-count[stream];file.write(b[:room]);os.fsync(file.fileno());count[stream]+=min(room,len(b));need(len(b)<=room,'tail capture overflow');need(False,'unexpected terminal tail bytes')
   need(count['stderr']==0 and not pending,'no extra output');guard();ok=True
  except BaseException as ex:save(O/'failure.json',{'status':'FIRST_FAILURE_NO_RETRY','exception':repr(ex),'samples':len(sampleRows)})
  finally:
   cleanupDeadline=time.monotonic()+5;stop.set()
   if watch is not None:
    watch.join(timeout=.1)
    if watch.is_alive():cleanup.append('watchdog not joined before reap')
   locked=anchorLock.acquire(timeout=max(.001,cleanupDeadline-time.monotonic()))
   if not locked:cleanup.append('cleanup ownership lock unavailable; no reap or signal')
   try:
    if locked and proc is not None and proc.returncode is not None:reaped=True
    if locked and proc is not None and signalAuthority and not waitEntered and proc.returncode is None and not reaped:
     try:os.killpg(proc.pid,signal.SIGKILL);groupKillIssued=True
     except ProcessLookupError:pass
     except BaseException as ex:cleanup.append('killgroup:'+repr(ex))
     signalAuthority=False;waitEntered=True
     try:proc.wait(timeout=max(.001,cleanupDeadline-time.monotonic()))
     except BaseException as ex:waitUncertain=True;cleanup.append('reap:'+repr(ex))
     finally:reaped=proc.returncode is not None
   finally:
    if locked:anchorLock.release()
   if waitUncertain:cleanup.append('wait exception; signaling authority retired; ownership uncertain')
   if proc is not None:
    for pipe in [proc.stdin,proc.stdout,proc.stderr]:
     if pipe is not None and not pipe.closed:pipe.close()
   sel.close();attempt.update(state='terminal'if proc is None or reaped else'unclosed',reaped=reaped,returncode=None if proc is None else proc.returncode,cleanup=cleanup);save(O/'attempt.json',attempt)
 save(O/'terminal.json',{'success':ok and not cleanup,'leaderReaped':reaped,'groupTerminationIssued':groupKillIssued,'normalClosureProof':'helper wait0 + stable one-again samples + leader wait0','postReapGroupOperations':0,'waitEntered':waitEntered,'waitUncertain':waitUncertain,'signalingAuthorityRetired':not signalAuthority,'PythonChildStartsAtMost':2,'samples':len(sampleRows),'nativeLoaderCalls':0,'setters':0,'noRetry':True})
 if ok and not cleanup:
  guard();save(O/'completion.json',{'status':'COMPLETE_OWNED_GROUP_MEMORY_ADAPTER_QUALIFICATION_ONLY','sourcePinsSHA256':g['sha256']['source-pins.json'],'phases':phaseRows,'samples':sampleRows,'native8Authorized':False,'hardMemoryCapEstablished':False,'raw':{n:receipt(O/n)for n in ['stdout','stderr','receipts.jsonl','attempt.json','terminal.json']}})
 return 0 if ok and not cleanup else 78
if __name__=='__main__':need(len(sys.argv)==2,'exact GO required');sys.exit(main(sys.argv[1]))
