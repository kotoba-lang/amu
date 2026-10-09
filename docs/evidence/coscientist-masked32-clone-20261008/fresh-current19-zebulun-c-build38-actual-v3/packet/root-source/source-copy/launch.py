"""One reviewed SSH install. No compiler, guest, SCP or timing authority."""
from pathlib import Path
import hashlib,json,os,selectors,shlex,signal,stat,subprocess,sys,time
from packet import payload,REMOTE,H
from install import unique
D=Path(__file__).resolve().parent
HOST='zebulun@100.66.28.79'
def pin(r):
 p=Path(r['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==r['bytes'];b=p.read_bytes();assert len(b)==r['bytes'] and H(b)==r['sha256'];return b
def save(p,v):
 b=(json.dumps(v,indent=2)+'\n').encode();assert len(b)<=65536
 assert not os.path.lexists(p);t=p.with_name(p.name+'.pending')
 with t.open('xb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.link(t,p,follow_symlinks=False);os.unlink(t)
 fd=os.open(p.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def receipt(p):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink() and st.st_size<=65536
 b=p.read_bytes();assert len(b)==st.st_size;return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def authorize(g):
 assert set(g)=={'status','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','remoteRuntime','remoteRuntimeIdentityProof','nativeCompilerGuestTimingAuthorized','transferAuthorized','noRetry'}
 assert g['status']=='GO_ONE_CURRENT19_PACKET_INSTALL_ONLY_V3' and g['transferAuthorized'] is True and g['nativeCompilerGuestTimingAuthorized'] is False and g['noRetry'] is True
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('launch.py','driverSHA256')]:assert H((D/n).read_bytes())==g[k]
 sp=json.loads((D/'source-pins.json').read_text())
 for n,r in sp.items():pin(dict(r,path=str(D/n)))
 bank=json.loads((D/'input-pins.json').read_text())
 for p,r in bank.items():pin(dict(r,path=p))
 assert len(g['sourceReviews'])==2 and len({r['path'] for r in g['sourceReviews']})==2
 for r in g['sourceReviews']:
  q=json.loads(pin(r));assert q['status']=='PASS_SOURCE_ONLY_ONE_CURRENT19_PACKET_INSTALL_V3' and q['sourcePinsSHA256']==g['sourcePinsSHA256'] and q['preregistrationSHA256']==g['preregistrationSHA256'] and q['driverSHA256']==g['driverSHA256']
 pr=json.loads((D/'preregistration.json').read_text());assert g['remoteRuntimeIdentityProof']==pr['selectedIdentityProof']
 rr=g['remoteRuntime'];assert set(rr)=={'path','bytes','sha256'} and rr['path'].startswith('/Library/Developer/CommandLineTools/') and '..'not in Path(rr['path']).parts
 rp=json.loads(pin(g['remoteRuntimeIdentityProof']));assert rp['status']=='PASS_SOURCE_BOUND_SELECTED_ZEBULUN_INSTALL_PYTHON_IDENTITY_ONLY' and rp['host']==HOST and rp['runtime']==rr
 return True
def scope(m,b,pr):
 assert m['exactFiles']==pr['exactPacketFiles'] and m['exactLogicalBytes']==pr['exactPacketLogicalBytes']
 assert len(b)==pr['exactPayloadBytes']<=pr['maximumPayloadBytes']==8388608 and H(b)==pr['payloadSHA256']
 assert H(json.dumps(m,sort_keys=True,separators=(',',':')).encode())==pr['manifestCanonicalSHA256']
 return True
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gr=receipt(gp);g=json.loads(pin(gr),object_pairs_hook=unique);authorize(g)
 m=json.loads((D/'manifest.json').read_text());b=payload(m);scope(m,b,json.loads((D/'preregistration.json').read_text()));ph=H(b);mh=H(json.dumps(m,sort_keys=True,separators=(',',':')).encode())
 code=(D/'install.py').read_text();bootstrap='import sys,signal;signal.alarm(45);sys.argv='+repr(['install.py',ph,mh,g['remoteRuntime']['sha256']])+';exec(compile('+repr(code)+',"pinned-install.py","exec"))'
 cmd='exec /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/Users/zebulun LANG=C LC_ALL=C TZ=UTC '+shlex.quote(g['remoteRuntime']['path'])+' -I -c '+shlex.quote(bootstrap)
 assert len(cmd.encode())<=131072
 argv=['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',HOST,cmd]
 O=D/'run-outputs';assert not O.exists();O.mkdir();save(O/'attempt.json',{'argv':argv,'payloadBytes':len(b),'payloadSHA256':ph,'manifestCanonicalSHA256':mh,'SSHCallsMaximum':1,'SCPCallsMaximum':0})
 proc=None;enteredWait=False;raw={'stdout':bytearray(),'stderr':bytearray()};failure=None;rc=None;overflow={};iterations=0;success=None;cleanupErrors=[];sel=selectors.DefaultSelector();sent=0
 until=time.monotonic()+60
 try:
  proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','LANG':'C','LC_ALL':'C','TZ':'UTC'},cwd=D,bufsize=0,close_fds=True)
  save(O/'pid.json',{'pid':proc.pid,'directChildOwnedBeforeAnyWait':True})
  for role,mask in [('stdin',selectors.EVENT_WRITE),('stdout',selectors.EVENT_READ),('stderr',selectors.EVENT_READ)]:
   stream=getattr(proc,role);os.set_blocking(stream.fileno(),False);sel.register(stream,mask,role)
  while sel.get_map():
   iterations+=1;assert iterations<=16384,'bounded selector iterations'
   assert time.monotonic()<until,'SSH transfer60 deadline'
   for key,_ in sel.select(min(.05,max(0,until-time.monotonic()))):
    stream=key.fileobj;role=key.data
    if role=='stdin':
     try:n=os.write(stream.fileno(),b[sent:sent+65536])
     except BlockingIOError:continue
     assert n>0;sent+=n
     if sent==len(b):sel.unregister(stream);stream.close()
    else:
     try:q=os.read(stream.fileno(),min(4096,16384-len(raw[role])+1))
     except BlockingIOError:continue
     if len(raw[role])+len(q)>16384:
      overflow[role]=q[-1];raise AssertionError('bounded raw16KiB plus one refusal')
     if q:raw[role]+=q
     else:sel.unregister(stream);stream.close()
  enteredWait=True;rc=proc.wait(timeout=30)
  assert rc==0 and not raw['stderr'] and sent==len(b)
  q=json.loads(raw['stdout'],object_pairs_hook=unique);assert set(q)=={'status','files','logicalBytes','payloadSHA256','manifestCanonicalSHA256','runtimeExecutable','runtimeSHA256','nativeCompilerGuestTimingCalls'} and all(type(q[k])is int for k in ('files','logicalBytes','nativeCompilerGuestTimingCalls'))
  assert q['status']=='CLOSED_CURRENT19_PACKET_INSTALL_ONLY' and q['files']==m['exactFiles'] and q['logicalBytes']==m['exactLogicalBytes'] and q['payloadSHA256']==ph and q['manifestCanonicalSHA256']==mh and q['runtimeSHA256']==g['remoteRuntime']['sha256'] and q['nativeCompilerGuestTimingCalls']==0
  authorize(g);pin(gr);success={'status':'CLOSED_ONE_SSH_CURRENT19_PACKET_INSTALL_ONLY_V3','SSHCalls':1,'SCPCalls':0,'directWaitCount':1,'returncode':rc,'remoteReceipt':q,'nativeCompilerGuestTimingCalls':0,'noRetry':True}
 except BaseException as ex:
  failure=repr(ex)
  if proc is not None and not enteredWait:
   # No poll/wait has released this direct child's numeric identity. Retire before first wait, including uncertainty.
   try:os.kill(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   except BaseException as killerr:failure+=';kill='+repr(killerr)
   enteredWait=True
   try:rc=proc.wait(timeout=30)
   except BaseException as waiterr:failure+=';wait-uncertain='+repr(waiterr)
  save(O/'failure.json',{'status':'FIRST_FAILURE_NO_RETRY','failure':failure,'directWaitEntered':enteredWait,'returncode':rc,'remoteClosure':'UNKNOWN unless complete verified receipt; remote45 alarm limits interpreter only; partial root preserved','noFurtherSignalAfterWait':True,'overflowByteByStream':overflow,'rootGO':gr})
  raise
 finally:
  sel.close()
  if proc:
   for role in ('stdin','stdout','stderr'):
    stream=getattr(proc,role)
    if stream is not None:
     try:stream.close()
     except BaseException as ce:cleanupErrors.append(role+':'+repr(ce))
  for role in ('stdout','stderr'):
   with (O/role).open('xb')as f:f.write(raw[role]);f.flush();os.fsync(f.fileno())
  terminal={'status':'CLOSED_DIRECT_SSH_TRANSPORT_TERMINAL_ONLY' if rc==0 and failure is None and not cleanupErrors else 'REFUSED_TRANSPORT_TERMINAL_ONLY','directWaitEntered':enteredWait,'returncode':rc,'pipeCleanupErrors':cleanupErrors,'failure':failure,'rootGO':gr,'rawReceipts':{role:receipt(O/role)for role in ('stdout','stderr')},'attempt':receipt(O/'attempt.json'),'PIDReceipt':receipt(O/'pid.json')if (O/'pid.json').exists()else None,'noFurtherSignalAfterWait':True}
  save(O/'terminal.json',terminal)
 # Valid-last: no completion can exist before all rawfsync/terminalfsync and exact source/GO rechecks.
 assert success is not None and not cleanupErrors and terminal['status']=='CLOSED_DIRECT_SSH_TRANSPORT_TERMINAL_ONLY'
 authorize(g);pin(gr)
 success.update(rootGO=gr,sourcePinsSHA256=g['sourcePinsSHA256'],inputPinsSHA256=g['inputPinsSHA256'],preregistrationSHA256=g['preregistrationSHA256'],driverSHA256=g['driverSHA256'],sourceReviews=g['sourceReviews'],attempt=terminal['attempt'],rawReceipts=terminal['rawReceipts'],terminal=receipt(O/'terminal.json'))
 save(O/'completion.json',success)
if __name__=='__main__':main()
