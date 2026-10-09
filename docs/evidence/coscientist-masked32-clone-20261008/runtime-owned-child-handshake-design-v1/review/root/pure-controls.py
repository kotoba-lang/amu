from model import Ownership,Refuse
import json,copy
from pathlib import Path
D=Path(__file__).resolve().parent
def setup():
 m=Ownership('GO','nonce',100);m.bind(100,11,100,0,'GO','nonce',True,11);m.release(100);m.sample([(100,11,100,8)]);m.child(101,True,False);return m
def bind(m,**kw):
 q=dict(pid=101,birth=12,pgid=100,parent=100,go='GO',nonce='nonce',durable=True,kernelBirth=12,childForkResult=101);q.update(kw);m.bind(**q)
results=[]
for gap in [False,True]:
 m=setup();bind(m);m.release(101)
 if gap:m.error(101,'member-getpgid',3)
 else:m.sample([(100,11,100,8),(101,12,100,16)])
 m.child_wait(101,12,0,True);m.before_wait();q=m.finish(0,False,True,True);assert q['strictMemoryQualified']==(not gap)and q['zeroSynthesized']is False;results.append('held-prebound-ephemeral-gap'if gap else'held-stable-sample')
def refuse(name,fn):
 try:fn()
 except Refuse:results.append(name)
 else:raise AssertionError(name)
for name,k,v in [('wrong-GO','go','other'),('wrong-nonce','nonce','other'),('wrong-parent','parent',999),('wrong-group','pgid',999),('wrong-fork','childForkResult',999),('wrong-birth','kernelBirth',13),('not-durable','durable',False)]:
 refuse(name,lambda k=k,v=v:bind(setup(),**{k:v}))
refuse('release-before-binding',lambda:setup().release(101))
refuse('unbound-current-failure',lambda:setup().error(101,'member-getpgid',3))
refuse('foreign-census',lambda:setup().sample([(100,11,100,8),(999,13,100,8)]))
def guestalias():
 m=Ownership('GO','nonce',100);m.bind(100,11,100,0,'GO','nonce',True,11);m.release(100);m.child(101,True,True)
refuse('guest-channel-alias',guestalias)
def reused():
 m=setup();bind(m);m.release(101);m.sample([(100,11,100,8),(101,13,100,8)])
refuse('PID-birth-reuse',reused)
def uncertain():
 m=setup();bind(m);m.release(101);m.child_wait(101,12,0,True);m.before_wait();m.finish(0,True,True,True)
refuse('uncertain-leader-wait',uncertain)
def postwait():
 m=setup();bind(m);m.release(101);m.before_wait();m.sample([(100,11,100,8)])
refuse('postwait-group-operation',postwait)
def missingwait():
 m=setup();bind(m);m.release(101);m.error(101,'member-getpgid',3);m.before_wait();m.finish(0,False,True,True)
refuse('leader-wait-not-child-proof',missingwait)
refuse('extra-child',lambda:setup().child(102,True,False))
q={'status':'PASS_PURE_HELD_LAUNCH_OWNERSHIP_MODEL_ONLY','controls':results,'realAPICalls':0,'nativeCalls':0,'threads':0,'FDOperations':0,'runtimeQualified':False}
(D/'pure-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(len(results))
