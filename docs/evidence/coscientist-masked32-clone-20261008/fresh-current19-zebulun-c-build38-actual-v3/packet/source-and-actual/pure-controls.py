"""Pure decoder and actual-source cleanup branches. No filesystem install or processes."""
from pathlib import Path
import ast,base64,copy,hashlib,json,types
from install import decode
from packet import H,REMOTE,payload,validate
D=Path(__file__).resolve().parent
b=b'one';r={'source':'/SOURCE/not-opened-by-decoder','relativePath':'inputs/a.bin','bytes':3,'sha256':H(b),'owner':'fixture'}
m={'schema':'CURRENT19_CORE_CONSUMER_CBUILD_PACKET_V1','remoteRoot':REMOTE,'files':[r],'exactFiles':1,'exactLogicalBytes':3,'owners':['fixture'],'executionCredit':False}
q={'schema':'CURRENT19_INSTALL_ENVELOPE_V1','manifest':m,'files':[{'relativePath':'inputs/a.bin','bytes':3,'sha256':H(b),'base64':base64.b64encode(b).decode()}]}
def run(z):
 raw=json.dumps(z,separators=(',',':')).encode();mh=H(json.dumps(z['manifest'],sort_keys=True,separators=(',',':')).encode());return decode(raw,H(raw),mh)
assert run(q)[1]==[('inputs/a.bin',b)]
neg=[]
def refusal(name,z):
 try:run(z)
 except (AssertionError,ValueError,TypeError,KeyError):neg.append(name)
 else:raise AssertionError(name)
for name,change in [('absolute',lambda z:z['files'][0].update(relativePath='/tmp/x')),('traversal',lambda z:z['files'][0].update(relativePath='../x')),('unknown-member-key',lambda z:z['files'][0].update(linkname='elsewhere')),('unknown-envelope',lambda z:z.update(extra=True)),('short-payload',lambda z:z['files'][0].update(base64='')),('wronghash',lambda z:z['files'][0].update(sha256='0'*64)),('stale-count',lambda z:z['manifest'].update(exactFiles=2)),('wrong-total',lambda z:z['manifest'].update(exactLogicalBytes=0)),('runtime-credit',lambda z:z['manifest'].update(executionCredit=True)),('other-root',lambda z:z['manifest'].update(remoteRoot='/tmp/root')),('too-many',lambda z:z['manifest'].update(exactFiles=257)),('unknown-owner',lambda z:z['manifest']['files'][0].update(owner='foreign'))]:
 z=copy.deepcopy(q);change(z);refusal(name,z)
for name,path in [('duplicate','inputs/a.bin'),('ancestor','inputs/a.bin/child'),('reserved','install-receipt.json'),('double-slash','inputs//b'),('backslash','inputs\\b')]:
 z=copy.deepcopy(q);rr=copy.deepcopy(r);rr['relativePath']=path;v=copy.deepcopy(z['files'][0]);v['relativePath']=path
 if name in ('reserved','double-slash','backslash'):z['manifest']['files']=[rr];z['files']=[v]
 else:z['manifest']['files'].append(rr);z['files'].append(v);z['manifest']['exactFiles']=2;z['manifest']['exactLogicalBytes']=6
 refusal(name,z)
# Execute only the real exception cleanup AST with injected process/kill/save objects.
tree=ast.parse((D/'launch.py').read_text());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='main');tr=next(x for x in main.body if isinstance(x,ast.Try));body=tr.handlers[0].body[:-1]
code=compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),'actual-launch-cleanup','exec')
proof=[]
class Out:
 def __truediv__(self,k):return k
for name,existing,entered,waitRaises,killRaises in [('owned',True,False,False,False),('wait-gap',True,False,True,False),('already-waited',True,True,False,False),('no-handle',False,False,False,False),('kill-failed',True,False,False,True)]:
 events=[]
 class Proc:
  pid=77
  def wait(self,timeout):
   events.append('wait')
   if waitRaises:raise KeyboardInterrupt('waitpid released / returncode unpublished')
   return -9
 def kill(pid,sig):
  events.append('kill')
  if killRaises:raise OSError('kill failure')
 ns={'ex':RuntimeError('original'),'proc':Proc()if existing else None,'enteredWait':entered,'os':types.SimpleNamespace(kill=kill),'signal':types.SimpleNamespace(SIGKILL=9),'rc':None,'gr':{'path':'fixture','bytes':0,'sha256':'0'*64},'overflow':{},'O':Out(),'save':lambda p,q:events.append('save')}
 exec(code,ns)
 if existing and not entered:assert events[:2]==['kill','wait'] and events.count('kill')==1 and events.count('wait')==1 and ns['enteredWait'] is True
 else:assert 'kill'not in events and 'wait'not in events
 proof.append({'case':name,'events':events,'authorityRetiredBeforeWait':ns['enteredWait']})
# Real complete SOURCE envelope and prereg count/byte/hash relation, no installer main.
from launch import scope
actual=json.loads((D/'manifest.json').read_text());encoded=payload(actual);pr=json.loads((D/'preregistration.json').read_text());assert scope(actual,encoded,pr)
assert decode(encoded,H(encoded),pr['manifestCanonicalSHA256'])[0]['exactFiles']>0
for k in ('exactPacketFiles','exactPacketLogicalBytes','exactPayloadBytes','payloadSHA256','manifestCanonicalSHA256'):
 bad=copy.deepcopy(pr);bad[k]=0 if type(bad[k])is int else '0'*64
 try:scope(actual,encoded,bad)
 except AssertionError:neg.append('scope-'+k)
 else:raise AssertionError('stale prereg relation accepted')
# Execute real finally+post-finally valid-last AST with fake I/O only.
tail=main.body[main.body.index(tr)+1:]
whole=compile(ast.fix_missing_locations(ast.Module(body=[ast.Try(body=[ast.Pass()],handlers=[],orelse=[],finalbody=tr.finalbody)]+tail,type_ignores=[])),'source-validlast','exec')
validlast=[]
class FakeFile:
 def __init__(self,label,events):self.label=label;self.events=events
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def write(self,b):self.events.append('write-'+self.label);return len(b)
 def flush(self):self.events.append('flush-'+self.label)
 def fileno(self):return self.label
class FakePath:
 def __init__(self,label,events):self.label=label;self.events=events
 def __truediv__(self,name):return FakePath(name,self.events)
 def open(self,*args):return FakeFile(self.label,self.events)
 def exists(self):return False
for fault in ('none','stdout-fsync','stderr-fsync','terminal-save'):
 events=[]
 def fsync(fd):
  events.append('fsync-'+fd)
  if fault==fd+'-fsync':raise OSError('injected rawfsync')
 def saving(p,q):
  if p.label=='terminal.json'and fault=='terminal-save':raise OSError('injected terminalsave')
  events.append('save-'+p.label)
 ns={'sel':types.SimpleNamespace(close=lambda:events.append('selector-close')),'proc':None,'O':FakePath('root',events),'raw':{'stdout':b'closed','stderr':b''},'os':types.SimpleNamespace(fsync=fsync),'rc':0,'failure':None,'cleanupErrors':[],'enteredWait':True,'gr':{},'save':saving,'receipt':lambda p:{'path':p.label,'bytes':0,'sha256':'0'*64},'success':{},'g':{'sourcePinsSHA256':'s','inputPinsSHA256':'i','preregistrationSHA256':'p','driverSHA256':'d','sourceReviews':[]},'authorize':lambda g:True,'pin':lambda r:b''}
 try:exec(whole,ns)
 except OSError:assert fault!='none'
 if fault=='none':assert events.index('save-completion.json')>events.index('save-terminal.json')>events.index('fsync-stderr')>events.index('fsync-stdout')
 else:assert 'save-completion.json'not in events
 validlast.append({'fault':fault,'events':events,'completionPublished':'save-completion.json'in events})
print(json.dumps({'status':'PASS_PURE_PACKET_DECODER_AND_SOURCE_DIRECT_CHILD_CLEANUP_ONLY','decodePositive':1,'decodeRefusals':neg,'sourceCleanupCases':proof,'actualSourceValidLastCases':validlast,'actualInstallTransferProcessCalls':0},indent=2))
