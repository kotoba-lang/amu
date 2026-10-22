"""Finite offline transition model of reviewed loader vector alloc/assoc!/arena enter/leave."""
from pathlib import Path
import json
D=Path(__file__).resolve().parent
class Trap(Exception):pass
class Arena:
 def __init__(self):self.used=0;self.top=0;self.table={};self.items={};self.marks=[];self.epoch=0
 def alloc(self,n):
  self.used+=1;self.table[self.used]=(self.top,n)
  for i in range(n):self.items[self.top+i]=0
  self.top+=n;return self.used
 def enter(self):self.marks.append((self.used,self.top))
 def leave(self):self.used,self.top=self.marks.pop();self.epoch+=1
 def resolve(self,h):
  if not 0<h<=self.used:raise Trap('invalid handle')
  return self.table[h]
 def read(self,h,i):
  base,n=self.resolve(h)
  if not 0<=i<n:raise Trap('index')
  return self.items[base+i]
 def write(self,h,i,value):
  base,n=self.resolve(h)
  if not 0<=i<n:raise Trap('index')
  self.items[base+i]=value;return h
class Cache:
 def __init__(self):self.key=0;self.epoch=-1
 def read(self,a,h,i,epoch=True):
  if self.key!=h or self.key==0 or epoch and self.epoch!=a.epoch:self.base,self.n=a.resolve(h);self.key=h;self.epoch=a.epoch
  if not 0<=i<self.n:raise Trap('cached index')
  return a.items[self.base+i]
def obs(f):
 try:return {'result':f(),'trap':False}
 except Trap as e:return {'trap':True,'reason':str(e)}
rows=[]
a=Arena();c=Cache();a.enter();h=a.alloc(3);assert c.read(a,h,0)==0;a.leave();new=a.alloc(1);assert h==new==1
actual=obs(lambda:a.read(new,2));unsafe=obs(lambda:c.read(a,new,2,False));safe=obs(lambda:c.read(a,new,2,True));assert actual['trap'] and not unsafe['trap'] and safe['trap'];rows.append({'control':'scope release then new valid reusedpositivehandle changes length3to1','handle':new,'original':actual,'unsafeKeyOnly':unsafe,'epochGuard':safe,'mutantDetected':True})
a=Arena();c=Cache();h=a.alloc(3);c.read(a,h,0);a.leave if False else None;a.enter();a.alloc(4);a.leave();assert a.read(h,2)==c.read(a,h,2,False);rows.append({'control':'caller handle predates balanced callee scope','safeWithoutResetKeyInvalidation':True,'requiresProof':'callee enter/leave structural balance cannot leave caller scope'})
a=Arena();c=Cache();h=a.alloc(3);before=c.read(a,h,0);a.write(h,0,99);after=c.read(a,h,0);assert before==0 and after==99;rows.append({'control':'contents-only write requires fresh element load','before':before,'after':after,'unsafeCachedValue':before,'mutantDetected':True})
a=Arena();c=Cache();h=a.alloc(3);c.read(a,h,0);a.enter();h2=a.alloc(4);c.read(a,h2,0);a.leave();actual=obs(lambda:a.read(h2,0));unsafe=obs(lambda:c.read(a,h2,0,False));safe=obs(lambda:c.read(a,h2,0,True));assert actual['trap'] and not unsafe['trap'] and safe['trap'];rows.append({'control':'released handle without reallocation must revalidate','original':actual,'unsafeKeyOnly':unsafe,'epochGuard':safe,'mutantDetected':True})
(D/'lifetime-model.json').write_text(json.dumps({'status':'PASS executed finite source-bound lifetime model; actual native controls remain future work','rows':rows,'scope':'Host transition subset reviewed at intern_vector/checked_vector_alloc/assoc_in_place/arena_enter/arena_leave; no native execution or complete runtime proof.','legalLifetimeSourceScenario':'(defn run [] :i64 (let [x (arena-scope (let [v (vector-alloc 3)] (vector-at v 0))) v (vector-alloc 1)] (vector-at v 2))) ; inner handle does not escape; outside fresh valid handle reuses numericID. Source scenario not compiled by this read-only task.'},indent=2)+'\n');print('PASS lifetime4controls3unsafe laws rejected')
