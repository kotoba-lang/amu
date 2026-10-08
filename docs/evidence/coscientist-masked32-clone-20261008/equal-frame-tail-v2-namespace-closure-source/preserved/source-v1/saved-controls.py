"""Pure finite actual-word structural admission witnesses and field mutation refusals."""
import json,importlib.util,copy
from pathlib import Path
D=Path(__file__).parent;S=D.parent/'shared-frame-currenttyped-observer3-source-v1-20261009';raw=(S/'run-outputs/nsichneu-compile.stdout').read_bytes()
rows=[(l.split()[0].decode(),list(map(int,l.split()[1:])))for l in raw.splitlines()if not l.startswith(b'{')]
fn={a[1]:a[2:]for t,a in rows if t=='SF'and a[0]==1};sir={a[1]:a[2:]for t,a in rows if t=='SS'};code={a[1]:a[2]for t,a in rows if t=='SC'and a[0]==1};fix={a[1]:a[2:]for t,a in rows if t=='SX'and a[0]==1};labels={a[1]:a[2]for t,a in rows if t=='SB'and a[0]==1}
spec=importlib.util.spec_from_file_location('v',S/'validate_observer.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def admit(f,fn=fn,code=code,fix=fix,labels=labels,ln=None):
 try:
  shape=v.shape([fn[i]for i in range(len(fn))],[sir[i]for i in range(len(sir))],f);assert shape
  g=shape['tail'];assert g!=f and v.shape([fn[i]for i in range(len(fn))],[sir[i]for i in range(len(sir))],g)
  for h in[f,g]:assert fn[h][10]==1 and fn[h][15]in[4,7]and fn[h][14]==1
  assert fn[f][15]==fn[g][15];F=80 if fn[f][15]==4 else 96
  for h in[f,g]:
   at=fn[h][13];assert[code[at+i]for i in range(6)]==[0xa9bf7bfd,0x910003fd,0xd10003ff+(F<<10),0xf90003f3,0xf90003e7+(((F-8)//8)<<10),0xaa0003f3]
  start=fn[f][13];stop=min([r[13]for r in fn.values()if r[13]>start]+[max(code)+1]);target=fn[g][13];assert start<target
  found=[(k,x)for k,x in fix.items()if k>0 and start+6<=x[0]<stop and x[1]==4 and x[2]==g];assert len(found)==1
  k,x=found[0];at=x[0];assert x[3]==0 and[code[at+i]for i in range(-4,1)]==[0xaa0903e0,0xf94003f3,0x910003bf,0xa8c17bfd,0x14000000]and code[at+1]==0xd4200020 and at+2==stop
  assert all(not(at-4<=p<=at)and not(target<p<=target+5)for i,p in labels.items()if i>0)
  assert all(j==k or(not(at-4<=z[0]<=at)and not(target<=z[0]<target+6))for j,z in fix.items()if j>0)
  assert 0<(ln if ln is not None else len(labels))<131072
  return {'owner':f,'target':g,'F':F,'fixIndex':k,'tailWord':at,'privateEntryWord':target+5,'CODECountUnchanged':True,'FIXCountUnchanged':True,'addedLabels':1,'rewriteWords':[0xf94007be,0xd503201f,0xd503201f]}
 except(AssertionError,KeyError,IndexError):return None
positive=admit(132);assert positive
negative={}
for name,off,value in [('mismatched-F',2,0xd10183ff),('wrong-context-slot',4,0xf9002fe7),('wrong-callee-save',3,0xf90003f4),('wrong-parameter-entry',5,0xaa0003f4)]:
 c=copy.deepcopy(code);c[fn[133][13]+off]=value;negative[name]=admit(132,code=c)is None
l=copy.deepcopy(labels);l[max(l)+1]=positive['privateEntryWord'];negative['unknown-incoming-label']=admit(132,labels=l)is None
x=copy.deepcopy(fix);x[max(x)+1]=[positive['tailWord']-1,1,1,0];negative['extra-restore-relocation']=admit(132,fix=x)is None
x=copy.deepcopy(fix);x[positive['fixIndex']][3]=1;negative['chain-AUX']=admit(132,fix=x)is None
negative['label-cap']=admit(132,ln=131072)is None
f=copy.deepcopy(fn);f[133][15]=7;negative['different-temp-home-map']=admit(132,fn=f)is None
c=copy.deepcopy(code);c[positive['tailWord']-2]=0xd4200000;negative['extra-observable-trap']=admit(132,code=c)is None
assert all(negative.values())
result={'status':'PASS_PURE_SAVED_WORD_ADMISSION_CONTROLS_ONLY','firstPositive':positive,'allObservedPositiveOwners':[f for f in range(1,len(fn))if admit(f)],'negatives':negative,'candidateSourceCompiled':False,'nativeCalls':0}
(D/'saved-controls-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
