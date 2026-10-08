"""Offline source-data discovery; no native compiler or guest execution."""
from pathlib import Path
import copy,json,hashlib,importlib.util
D=Path(__file__).parent;W=D.parent
spec=importlib.util.spec_from_file_location('base',D/'saved-base.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def discover(limit=10,fix=None,labels=None,labelcap=131072):
 fn=copy.deepcopy(b.fn);code=copy.deepcopy(b.code);fix=copy.deepcopy(b.fix if fix is None else fix);labels=copy.deepcopy(b.labels if labels is None else labels);picked=[]
 if not b.oldfixclosed(fn,code,fix,labels,len(labels)):return picked,fn,code,fix,labels
 for f in range(1,len(fn)):
  if len(picked)>=limit or len(labels)>=labelcap:break
  if not b.oldfixclosed(fn,code,fix,labels,len(labels)):break
  p=b.admit(f,fn,code,fix,labels,len(labels))
  if not p:continue
  at=p['tailWord'];ln=len(labels);code[at-3]=0xf94007be;code[at-2]=code[at-1]=0xd503201f;labels[ln]=p['privateEntryWord'];fix[p['fixIndex']][1:3]=[1,ln]
  assert b.oldfixclosed(fn,code,fix,labels,len(labels));picked.append(dict(p,newPrivateLabel=ln))
 return picked,fn,code,fix,labels
pairs,fn,code,fix,labels=discover();assert len(pairs)==10
assert [p['owner']for p in pairs]==[132,133,134,135,136,138,139,140,141,142]
assert b.admit(137)is None and b.fn[137][15]!=b.fn[138][15]
assert fn==b.fn and len(code)==len(b.code)and len(fix)==len(b.fix)and len(labels)==len(b.labels)+10
assert all(code[b.fn[p['target']][13]+i]==b.code[b.fn[p['target']][13]+i]for p in pairs for i in range(6))
# Actual ordinary whole native/container, new prospective kernel derived only from structural discovery.
O=W/'tc-current7618-off18-compile36-source-v1-20261009/run-outputs';before=(O/'nsichneu.bin').read_bytes();raw=(O/'nsichneu.kseed').read_bytes();after=bytearray(before);changes=[]
for p in pairs:
 at=p['tailWord']
 for word,value in [(at-3,0xf94007be),(at-2,0xd503201f),(at-1,0xd503201f),(at,0x14000000|((p['privateEntryWord']-at)&0x3ffffff))]:
  offset=(word-1)*4;old=int.from_bytes(before[offset:offset+4],'little');after[offset:offset+4]=value.to_bytes(4,'little');changes.append(dict(wordIndex=word,physicalByteOffset=offset,before=old,after=value))
assert len(changes)==40 and len(set(x['wordIndex']for x in changes))==40
assert all(before[i:i+4]==after[i:i+4]for i in range(0,len(before),4)if i//4+1 not in {x['wordIndex']for x in changes})
cut=raw.index(b'\n\n')+2;assert raw[cut:]==before;container=raw[:cut]+after
negative={}
x=copy.deepcopy(b.fix);x[max(x)+1]=[1,1,len(b.labels),0];negative['old-label-count-alias-refused-before-first-mutation']=discover(fix=x)[0]==[]
x=copy.deepcopy(b.fix);x[max(x)+1]=[1,1,131071,0];negative['high-label-refused']=discover(fix=x)[0]==[]
l=copy.deepcopy(b.labels);l[1]=0;x=copy.deepcopy(b.fix);x[max(x)+1]=[1,1,1,0];negative['unresolved-label-refused']=discover(fix=x,labels=l)[0]==[]
negative['zero-label-capacity-no-mutation']=discover(labelcap=len(b.labels))[0]==[]
negative['one-label-slot-stops-after-one']=len(discover(labelcap=len(b.labels)+1)[0])==1
negative['work-budget-one-stops-after-one']=len(discover(limit=1)[0])==1
negative['work-budget10-stops-before-next-eligible']=len(pairs)==10 and b.admit(143,fn,code,fix,labels,len(labels))is not None
negative['cross-F80-to96-generic']=b.admit(137)is None
negative['public-prologues-param-moves-unchanged']=all(before[(b.fn[p['target']][13]-1)*4:(b.fn[p['target']][13]+5)*4]==after[(b.fn[p['target']][13]-1)*4:(b.fn[p['target']][13]+5)*4]for p in pairs)
# Unknown incoming private-header label after mutation blocks the next pair; completed earlier independently valid edge retained.
l=copy.deepcopy(labels);l[max(l)+1]=b.fn[144][13]+5;negative['unknown-next-private-entry-refused']=b.admit(143,fn,code,fix,l,len(l))is None
assert all(negative.values())
result={'status':'PASS_PURE_SAVED_TYPED_SEQUENTIAL_TEN_EDGE_CERTIFICATE_ONLY','pairs':pairs,'functionsBeforeAfter':len(fn),'CODECountBeforeAfter':len(code),'FIXCountBeforeAfter':len(fix),'oldLabelCount':len(b.labels),'newLabelCount':len(labels),'namespaceClosureCheckedBeforeAndAfterEveryMutation':True,'negatives':negative,'originalNative':{'path':str(O/'nsichneu.bin'),'bytes':len(before),'sha256':hashlib.sha256(before).hexdigest()},'changes':changes,'expectedNativeBytes':len(after),'expectedNativeSHA256':hashlib.sha256(after).hexdigest(),'expectedContainerBytes':len(container),'expectedContainerSHA256':hashlib.sha256(container).hexdigest(),'headerExportsAndAllOtherBytesUnchanged':True,'actualCandidateEmissionQualified':False,'nativeCalls':0}
(D/'compose-controls-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(pairs),result['expectedNativeSHA256'])
