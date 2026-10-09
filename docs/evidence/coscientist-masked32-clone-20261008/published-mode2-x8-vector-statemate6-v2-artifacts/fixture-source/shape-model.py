"""Finite intended SIR shape model only; no compiler/emitter/native operations."""
import copy,json
# Matches narrowly the gn-wrapper natural parameter loads shape; cannot assert actual lowered SIR.
def wrapper(body,n):
 if n<1 or n>3:return False
 p=1 if body and body[0]==('fuel',)else 0
 return body[p:]==[('lget',k,k+1)for k in range(n)]+[('rt','assoc-in-place',0,n),('ret',0),('end',)]and n==3
w=[('fuel',),('lget',0,1),('lget',1,2),('lget',2,3),('rt','assoc-in-place',0,3),('ret',0),('end',)]
unary=[('fuel',),('lget',0,1),('const',1,0),('const',2,1),('rt','assoc-in-place',0,3),('ret',0),('end',)]
assert wrapper(w,3)and not wrapper(unary,1)
def stage(body,np,ns,dp,known):
 if not (np==1 and 1<=ns<=3 and 1<=dp<=3):return False
 genuine=0;debits=0
 for k,ins in enumerate(body):
  if ins[0]=='fuel':debits+=1
  elif ins[0]=='call':
   _,target,t,n=ins
   if known[target]=='wrapper3':
    if not(n==3 and 0<=t<=4 and t+n<=dp):return False
    debits+=1
   elif not(n==1 and 0<=t and t+n<=dp and body[k+1:]==[('ret',t),('end',)]):return False
   else:genuine+=1
  elif ins[0]not in ['lget','const','ret','end']:return False
 return genuine==1 and debits==2
body=[('fuel',),('lget',0,1),('const',1,0),('const',2,1),('call','set-at',0,3),('call','successor',0,1),('ret',0),('end',)]
known={'set-at':'wrapper3','successor':'unary-vec-genuine'};assert stage(body,1,1,3,known)
neg=[]
for name,change,args in [('too-deep',lambda b:None,(1,1,4)),('wrong-arity',lambda b:None,(2,1,3)),('nonterminal-generic-call',lambda b:b.insert(-2,('const',1,4)),(1,1,3)),('wrong-ret-temp',lambda b:b.__setitem__(-2,('ret',1)),(1,1,3)),('unadmitted-runtime',lambda b:b.insert(-2,('rt','allocation',0,1)),(1,1,3))]:
 b=copy.deepcopy(body);change(b);assert not stage(b,*args,known);neg.append(name)
print(json.dumps(dict(status='PASS_FINITE_INTENDED_WRAPPER_AND_TERMINAL_SHAPE_MODEL_ONLY',naturalWrapper=True,unaryLiteralWrapperRefused=True,twoDebitsAndGenuineTerminalCall=True,refusedMutants=neg,actualSIRAdmissionObserved=False,emittedPathsObserved=False,nativeCalls=0),indent=2))
