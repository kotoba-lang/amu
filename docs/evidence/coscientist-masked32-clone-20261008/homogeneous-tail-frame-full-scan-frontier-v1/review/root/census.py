"""SOURCE/saved-word only. No native calls. Full bounded generic hypothetical discovery."""
from pathlib import Path
import importlib.util,json,copy,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-compose10-source-v1-20261009';D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('saved',S/'saved-base.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
# Same finite source predicates as the actual registered saved-base subject.
# Hoist invariant max(code) once per closure check for this diagnostic interpreter.
def closed(fn,code,fix,labels,ln):
 maximum=max(code)
 for k,x in fix.items():
  if k==0:continue
  at,kind,t,aux=x
  if not(0<at<=maximum and aux==0 and 0<=code[at]<=0xffffffff):return False
  if kind in[1,2,3]:
   if not(0<t<ln):return False
   target=labels.get(t,0)
  elif kind in[4,6]:
   if not(0<t<len(fn)):return False
   target=fn[t][13]
  else:return False
  if not(0<target<=maximum):return False
  bound=33554432 if kind in[1,4]else 262144
  if not(-bound<=target-at<bound):return False
 return True
def census():
 fn=copy.deepcopy(b.fn);code=copy.deepcopy(b.code);fix=copy.deepcopy(b.fix);labels=copy.deepcopy(b.labels);picked=[]
 assert len(fn)<=512
 b.oldfixclosed=closed
 for f in range(1,min(len(fn),512)):
  assert closed(fn,code,fix,labels,len(labels));p=b.admit(f,fn,code,fix,labels,len(labels))
  if p is None:continue
  assert len(labels)<131072;at=p['tailWord'];ln=len(labels)
  code[at-3]=0xf94007be;code[at-2]=code[at-1]=0xd503201f;labels[ln]=p['privateEntryWord'];fix[p['fixIndex']][1:3]=[1,ln]
  assert closed(fn,code,fix,labels,len(labels));picked.append(dict(p,newPrivateLabel=ln))
 raw=(W/'tc-current7618-off18-compile36-source-v1-20261009/run-outputs/nsichneu.bin').read_bytes();after=bytearray(raw)
 for p in picked:
  at=p['tailWord']
  for word,value in[(at-3,0xf94007be),(at-2,0xd503201f),(at-1,0xd503201f),(at,0x14000000|((p['privateEntryWord']-at)&0x3ffffff))]:after[(word-1)*4:word*4]=value.to_bytes(4,'little')
 return picked,labels,after
if __name__=='__main__':
 p,l,a=census();saved=json.loads((D/'report.json').read_bytes())
 assert p==saved['allPairs']and len(l)==saved['labelsAfter']and hashlib.sha256(a).hexdigest()==saved['prospectiveNativeSHA256']
 print(json.dumps({'status':'PASS_PURE_FULL_SCAN_REPRODUCTION_ONLY','ownersScanned':len(b.fn)-1,'eligibleEdges':len(p),'noNativeCalls':True}))
