from pathlib import Path
import struct,json,hashlib,difflib,re
from native_utils_local import payload,ref,source_pool

def norm(words):return [w&r[2]if(r:=ref(w,i*4))else w for i,w in enumerate(words)]
def abi(source):
 return {m[1]:dict(parameters=m[2].split()[1::2],result=m[3])for m in re.finditer(r'\(defn-?\s+([^\s\[()]+)\s+\[([^\]]*)\]\s+([^\s()]+)',source)}
class IR:
 def __init__(self,d,source):
  self.f={x['function']:x for x in d['functions']};self.meta={int(k):v for k,v in d['metadata'].items()};self.ir={int(k):[x['words']for x in v]for k,v in d['ir'].items()};self.types=abi(source);self.stageCache={}
  assert len(self.f)==len(self.meta)==len(self.ir)
 def vec(self,f):
  if f not in self.f:return False
  v=self.f[f];m=self.meta[f];t=self.types.get(v['name'])
  return v['parameters']==1 and t==dict(parameters=[':vector-i64'],result=':vector-i64')and m['resultType']==m['parameterType0']==4
 def sign(self,f):
  if f not in self.f:return 0
  v=self.f[f];a=self.ir[f];m=self.meta[f];t=self.types.get(v['name'])
  if v['parameters']!=1 or v['slots']!=2 or v['depth']!=2 or m!=dict(resultType=1,fuel=0,parameterType0=1)or t!=dict(parameters=[':i64'],result=':i64')or len(a)!=19:return 0
  mask=a[3][2];mod=mask+1;width=mod.bit_length()-1
  if not 1<=width<=64 or mod!=1<<width:return 0
  l,yes,end=a[1][1],a[14][1],a[16][1]
  expected=[[1,f,1,2],[9,l,0,0],[4,0,1,0],[3,1,mask,0],[6,5,0,0],[5,2,0,0],[4,0,2,0],[3,1,mod//2,0],[7,5,0,0],[11,0,yes,0],[4,0,2,0],[3,1,mod,0],[6,2,0,0],[10,end,0,0],[9,yes,0,0],[4,0,2,0],[9,end,0,0],[19,0,0,0],[2,f,0,0]]
  return width if a==expected and len({l,yes,end})==3 else 0
 def writer(self,f):
  if f not in self.f:return False
  v=self.f[f];a=self.ir[f];m=self.meta[f]
  if v['parameters']!=3 or v['slots']!=3 or v['depth']!=3 or m!=dict(resultType=4,fuel=1,parameterType0=4)or self.types.get(v['name'])!=dict(parameters=[':vector-i64',':i64',':i64'],result=':vector-i64')or len(a)!=9:return False
  return a==[[1,f,3,3],[18,0,0,0],[9,a[2][1],0,0],[4,0,1,0],[4,1,2,0],[4,2,3,0],[14,208,0,3],[19,0,0,0],[2,f,0,0]]
 def stage(self,f):
  if f in self.stageCache:return self.stageCache[f]
  self.stageCache[f]=None
  if not self.vec(f):return None
  v=self.f[f];a=self.ir[f]
  if v['slots']!=3 or v['depth']!=3 or self.meta[f]['fuel']!=1 or len(a)<13 or a[:3]!=[[1,f,1,3],[18,0,0,0],[9,a[2][1],0,0]]:return None
  j=3;read=None;constant=None;width=0
  if a[j]==[4,0,1,0]:
   if a[j+1][0:2]!=[3,1]or a[j+1][3]!=0 or a[j+2]!=[14,176,0,2]:return None
   read=a[j+1][2]
   if not 0<=read<=4095:return None
   j+=3
  elif a[j][0:2]==[3,0]and a[j][3]==0:constant=a[j][2];j+=1
  else:return None
  if a[j][0]==13:
   if a[j][2:]!=[0,1]:return None
   width=self.sign(a[j][1])
   if width==0:return None
   j+=1
  if j+10!=len(a)or a[j]!=[5,2,0,0]or a[j+1][0:2]!=[3,0]or a[j+1][3]!=0:return None
  index=a[j+1][2];put=a[j+6][1];nxt=a[j+7][1]
  if not 0<=index<=4095 or not self.writer(put)or not self.vec(nxt):return None
  expected=[[5,2,0,0],[3,0,index,0],[5,3,0,0],[4,0,1,0],[4,1,3,0],[4,2,2,0],[13,put,0,3],[13,nxt,0,1],[19,0,0,0],[2,f,0,0]]
  if a[j:]!=expected:return None
  out=dict(function=f,read=read,constant=constant,width=width,write=index,next=nxt);self.stageCache[f]=out;return out
 def chain(self,f,limit):
  out=[]
  for k in range(limit):
   s=self.stage(f)
   if s is None:break
   out.append(s);f=s['next']
  return out,f

def body(words,j,stages):
 start=j;last=-1;known=0;stores=[]
 for s in stages:
  forward=s['read']is not None and s['read']==last
  if s['read']is not None:
   if not forward:assert words[j]==0xf9400149|(s['read']<<10);j+=1
  else:
   w=words[j];kind=w&0xff80001f;assert kind in [0xd2800009,0x92800009]
   shift=((w>>21)&3)*16;imm=(w>>5)&65535;value=imm<<shift
   if kind==0x92800009:value=(~value)&((1<<64)-1)
   j+=1
   while words[j]&0xff80001f==0xf2800009:
    w=words[j];shift=((w>>21)&3)*16;value=(value&~(65535<<shift))|(((w>>5)&65535)<<shift);j+=1
   assert value==s['constant']&((1<<64)-1)
  width=s['width'];skip=forward and known>0 and known<=width
  if width and not skip:assert words[j]==0x93400129|((width-1)<<10);j+=1
  assert words[j]==0xf9000149|(s['write']<<10);stores.append(j);j+=1
  last=s['write'];known=width if width else known if forward else 0
 assert words[j]==0xd2800005 and ref(words[j+1],(j+1)*4)[0]=='B'
 return dict(start=start,end=j+2,stores=stores,tailTarget=ref(words[j+1],(j+1)*4)[1],words=j+2-start)

def find(words,lo,hi,stages,tail):
 if len(stages)<4:return None
 cost=2*len(stages)-1;high=max(max(x['write'],x['read']if x['read']is not None else 0)for x in stages)
 matches=[]
 for q in range(lo,hi-16):
  if words[q]!=0xf100011f|(cost<<10):continue
  if list(words[q+2:q+6])!=[0xf9409cf0,0xf9400210,0xd1000411,0xeb10023f]:continue
  assert list(words[q+7:q+10])==[0xf940a0f0,0x8b111210,0xa9404211]
  assert words[q+10]==0xf100021f|(high<<10)
  assert list(words[q+12:q+16])==[0xf940a4ea,0x8b110d4a,0xd1000108|(cost<<10),0xf90004e8]
  b=body(words,q+16,stages)
  for at,cond in [(q+1,3),(q+6,2),(q+11,9)]:
   r=ref(words[at],at*4);assert r and r[0]=='BC'and words[at]&0xff00001f==0x54000000|cond and r[1]==b['end']*4
  assert b['tailTarget']==tail*4
  matches.append(dict(guard=q,**b,cost=cost,high=high))
 assert len(matches)<=1
 return matches[0]if matches else None

def audit(old,new,witnessRoot=None):
 A,ae=payload(old);B,be=payload(new);source=Path(new['source']['path']).read_bytes();assert source==Path(old['source']['path']).read_bytes()
 if A==B:assert ae==be;return dict(status='WHOLE_IDENTITY',changed=False)
 W=Path(witnessRoot)if witnessRoot is not None else Path(__file__).parent;name=Path(new['source']['path']).stem
 maps=[]
 for tag,blob in [('OFF',A),('ON',B)]:
  D=W/('diagnostic-'+tag+'-v1/programs');d=json.loads((D/(name+'-map.json')).read_text());assert d['status']=='PASS_LOCAL_DIAGNOSTIC_FULL_NATIVE_CONTAINER_EXPORT_IDENTITY_AND_ACTUAL_IR';assert blob==(D/(name+'.bin')).read_bytes()and source==(D/(name+'.kotoba')).read_bytes();assert hashlib.sha256(blob).hexdigest()==d['nativeSHA256'];maps.append(d)
 off,on=maps;assert off['ir']==on['ir']and off['metadata']==on['metadata'];assert[{k:v for k,v in f.items()if k!='offset'}for f in off['functions']]==[{k:v for k,v in f.items()if k!='offset'}for f in on['functions']]
 ir=IR(on,source.decode());a=struct.unpack('<'+'I'*(len(A)//4),A);b=struct.unpack('<'+'I'*(len(B)//4),B);pool,_=source_pool(source)
 if pool:assert A[-len(pool):]==B[-len(pool):]==pool
 fa=sorted(off['functions'],key=lambda x:x['offset']);fb=sorted(on['functions'],key=lambda x:x['offset']);assert [x['function']for x in fa]==[x['function']for x in fb]and fa[0]['offset']==fb[0]['offset']==0;assert len({x['offset']for x in fa})==len(fa)
 codeA=(len(A)-len(pool))//4;codeB=(len(B)-len(pool))//4;mapping={};allowedA=set();allowedB=set();proofs=[];refs=[];padding=[]
 def retained(al,ah,bl,bh):
  na=norm(a[al:ah]);nb=norm(b[bl:bh])
  for op,l,h,j,k in difflib.SequenceMatcher(None,na,nb,autojunk=False).get_opcodes():
   l+=al;h+=al;j+=bl;k+=bl
   if op=='equal':
    assert h-l==k-j
    for p,q in zip(range(l,h),range(j,k)):mapping[p]=q
   else:
    assert op in ['insert','delete']and max(h-l,k-j)==1,(op,l,h,j,k)
    side,p,v=('OFF',l,a)if op=='delete'else('ON',j,b)
    assert v[p]==0xd503201f and v[p-1]==0xd65f03c0 and(p+1)*4%8==0
    padding.append(dict(side=side,pc=p*4,RETAlignmentOnly=True))
 for i,(f,g)in enumerate(zip(fa,fb)):
  fid=f['function'];lo=f['offset']//4;hi=fa[i+1]['offset']//4 if i+1<len(fa)else codeA;nl=g['offset']//4;nh=fb[i+1]['offset']//4 if i+1<len(fb)else codeB
  stagesA,tailA=ir.chain(fid,16);stagesB,tailB=ir.chain(fid,48)
  x=find(a,lo,hi,stagesA,off['functions'][tailA-1]['offset']//4)if len(stagesA)>=4 else None
  y=find(b,nl,nh,stagesB,on['functions'][tailB-1]['offset']//4)if len(stagesB)>=4 else None
  assert bool(x)==bool(y),(fid,x,y)
  if x and len(stagesA)!=len(stagesB):
   retained(lo,x['guard'],nl,y['guard']);retained(x['end'],hi,y['end'],nh)
   allowedA.update(range(x['guard'],x['end']));allowedB.update(range(y['guard'],y['end']));mapping[x['guard']]=y['guard']
   proofs.append(dict(function=fid,name=f['name'],old=[x['guard']*4,x['end']*4],new=[y['guard']*4,y['end']*4],oldStages=len(stagesA),newStages=len(stagesB),oldCost=x['cost'],newCost=y['cost'],oldHigh=x['high'],newHigh=y['high'],stages=stagesB,oldTail=tailA,newTail=tailB,allOriginalOrderedStageStores=True,fullFuelAndIndexEnvelopeBeforeEffects=True,firstSourceEntryAlreadyPaid=True,newTailKeepsOriginalCharge=True))
  else:retained(lo,hi,nl,nh)
 if pool:retained(codeA,len(a),codeB,len(b))
 for p,q in mapping.items():
  if p in allowedA:continue
  r=ref(a[p],p*4);nr=ref(b[q],q*4)
  if r:
   assert nr and r[0]==nr[0]and(a[p]&r[2])==(b[q]&nr[2]);assert mapping.get(r[1]//4,-1)*4==nr[1],('Incoming modified body',p,r,nr);refs.append((p,q))
  else:assert a[p]==b[q]
 for sym,(pc,arity)in ae.items():assert be[sym]==[mapping[pc//4]*4,arity]
 assert len(ae)==len(be)and proofs
 assert len(mapping)+len(allowedA)-sum(p in allowedA for p in mapping)+sum(x['side']=='OFF'for x in padding)==len(a)
 assert len(set(mapping.values()))==len(mapping)
 assert len(mapping)+len(allowedB)-sum(q in allowedB for q in mapping.values())+sum(x['side']=='ON'for x in padding)==len(b)
 return dict(status='PASS_ACTUAL_UNCHANGED_IR_TYPED_SOURCE_CW16_CW48_STAGE_FUEL_INDEX_STORE_AND_ALL_RETAINED_CODE_PROOFS',changed=True,proofs=proofs,retainedWords=len(mapping),retainedReferences=len(refs),padding=padding,actualIRAndTypesWholeIdentity=True,diagnosticWholeNativeContainerIdentity=True,noExternalEntryIntoReplacedBody=True,allColdAndNonCWCodeRetained=True,adopted=False,performanceMeasured=False)

if __name__=='__main__':
 W=Path(__file__).parent;D=W/'physical-audit-v2';D.mkdir(exist_ok=False);G=json.loads((W/'all39-g1-screen-v1/generated-artifacts.json').read_text());rows=[]
 for e in G['images']:
  r=audit(e['baseline'],e['arm']);(D/(e['tag']+'.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(dict(tag=e['tag'],changed=r['changed'],extendedBlocks=len(r.get('proofs',[]))))
 assert len(rows)==39 and sum(x['changed']for x in rows)==2
 (D/'report.json').write_text(json.dumps(dict(status='PASS_ALL39',rows=rows),indent=2)+'\n');print('PASS_ALL39',[(r['tag'],r['extendedBlocks'])for r in rows if r['changed']])
