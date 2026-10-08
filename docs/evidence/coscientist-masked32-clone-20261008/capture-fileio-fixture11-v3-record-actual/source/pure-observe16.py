"""Finite pure SOURCE controls only. AST removes controller imports; sequential injected lock. No threads, FD, clock/kernel/native operations. Prior independent V3 harness mechanism reused and disclosed; controls authored here."""
import ast,hashlib,json,pathlib,types
D=pathlib.Path(__file__).resolve().parent
S=D
ns={'__name__':'injected_integration'}
exec(compile((D/'integration.py').read_bytes(),str(D/'integration.py'),'exec'),ns)
class Lock:
 def __enter__(self):return self
 def __exit__(self,*args):return False
cn={'__name__':'injected_controller','threading':types.SimpleNamespace(Lock=Lock),
 'classify_memory':ns['classify_memory'],'MEMORY_POLICY':ns['MEMORY_POLICY']}
t=ast.parse((D/'controller.py').read_text());t.body=[x for x in t.body if not isinstance(x,(ast.Import,ast.ImportFrom))]
exec(compile(t,str(D/'controller.py'),'exec'),cn)
Controller=cn['Controller']
class Flag:
 def __init__(self):self.value=False
 def is_set(self):return self.value
class Capture:
 def __init__(self,partial=False):self.stopped=Flag();self.refusals=[];self.partial=partial
 def refuse(self,r):self.refusals.append(r)
 def join_once(self,t):self.stopped.value=True;return True
 def snapshot(self):return {'stoppedWriter':True,'completeRaw':not self.partial,'errors':[],
  'EOF':{'stdout':not self.partial,'stderr':True},'dropped':{'stdout':0,'stderr':0}}
class Clock:
 def __init__(self):self.t=0
 def __call__(self):return self.t
 def pause(self,dt):self.t+=dt
class Fault(Exception):
 def __init__(self,c):self.context=c
failure={'typedOrigin':'fresh-owned-group-api-v1','contextVersion':'owned-group-sampling-failure-context-v1',
 'stage':'leader-getpgid','pid':11,'queryOrdinal':2,'errno':3,'failureClass':'kernel-oserror'}
def exercise(mode,bound={'pid':11,'birth':22},loader=True):
 clock=Clock();cap=Capture(partial=mode=='partial');ctl=Controller(clock,1);n=0
 if mode=='no-sample':cap.stopped.value=True
 def sample():
  nonlocal n
  n+=1
  if n==1:
   if mode in ['normal','watchdog-refusal','persist-refusal']:cap.stopped.value=True
   return {'ownedPGID':11,'members':[{'pid':11,'start':22}]}
  f=dict(failure)
  if mode=='wrong-errno':f['errno']=1
  if mode=='wrong-stage':f['stage']='group-list'
  if mode=='unknown-pid':f['pid']=77
  if mode=='missing-version':f['contextVersion']='old'
  if mode=='threshold':raise ValueError('injected threshold refusal')
  raise Fault(f)
 sampler=types.SimpleNamespace(sample=sample)
 def wait(t):
  assert not ctl.active and ctl.waitEntered
  if mode=='wait-gap':raise KeyboardInterrupt('injected waitpid released, returncode not published')
  return 0
 q=ctl.observe(cap,sampler,wait,lambda t:mode!='watchdog-refusal',clock.pause,lambda r:True,lambda:mode!='bad-journal',bound,loader,lambda q:mode!='persist-refusal')
 for call in [lambda:ctl.group(lambda:None),lambda:ctl.wait(wait)]:
  try:call()
  except AssertionError:pass
  else:raise AssertionError('retired authority restored')
 return q

rows=[]
cases=[('normal',{'pid':11,'birth':22},True),('gap',{'pid':11,'birth':22},True)]+[(m,{'pid':11,'birth':22},True)for m in ['wrong-errno','unknown-pid','wrong-stage','missing-version','partial','threshold','wait-gap','bad-journal','no-sample','watchdog-refusal','persist-refusal']]+[('normal',None,True),('normal',{'pid':11,'birth':23},True),('normal',{'pid':11,'birth':22},False)]
assert len(cases)==16
for index,(mode,bound,loader)in enumerate(cases):
 q=exercise(mode,bound,loader);r=q['memoryAdmissionRecord']
 expect='COMPLETE_SEMANTIC_SAMPLED_MEMORY'if index==0 else 'SEMANTIC_DIAGNOSTIC_TERMINATION_GAP'if index==1 else 'REFUSE'
 assert q['status']==expect,(index,mode,q)
 assert r['groupAuthorityRetired']and r['groupOperationsAfterWait']==0 and r['groupOperationsAfterUncertainty']==0
 assert q['directChildWait']==r['exactDirectChildWait']and q['waitUncertain']==r['waitUncertain']
 if mode in ['gap','wrong-errno','unknown-pid','wrong-stage','missing-version','partial']:assert r['failure']is not None and r['failure']['typedOrigin']=='fresh-owned-group-api-v1'
 if mode in ['threshold','persist-refusal']:assert r['failure']['typedOrigin']=='untyped-or-policy-refusal'and r['otherRefusals']
 if mode in ['bad-journal','watchdog-refusal','wait-gap']:assert r['otherRefusals']
 if mode=='unknown-pid':assert 'failure-pid-not-previously-bound'in r['otherRefusals']
 if mode=='wait-gap':assert r['waitUncertain']and r['exactDirectChildWait']=='unavailable'
 rows.append({'index':index+1,'mode':mode,'bound':bound,'loader':loader,'status':q['status'],'record':r})
print(json.dumps({'status':'PASS_PURE_OBSERVE16_DIAGNOSTIC_RECORD_SOURCE_ONLY','controls':rows,'actualThreadFDProcessNativeAPICalls':0},indent=2))
