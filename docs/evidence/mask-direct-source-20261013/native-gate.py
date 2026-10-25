from pathlib import Path
import json,re,struct,hashlib,bisect

def sx(x,n):return x-(1<<n)if x&(1<<(n-1))else x

def ref(w,p):
 if w&0x7c000000==0x14000000:return('BL'if w&0x80000000 else'B',p+4*sx(w&0x3ffffff,26),0xfc000000)
 if w&0xff000010==0x54000000:return('BC',p+4*sx(w>>5&0x7ffff,19),0xff00001f)
 if w&0x7e000000==0x34000000:return('CB',p+4*sx(w>>5&0x7ffff,19),0xff00001f)
 if w&0x7e000000==0x36000000:return('TB',p+4*sx(w>>5&0x3fff,14),0xfff8001f)
 if w&0x3b000000==0x18000000:return('LIT',p+4*sx(w>>5&0x7ffff,19),0xff00001f)
 if w&0x9f000000==0x10000000:return('ADR',p+sx(((w>>5&0x7ffff)<<2)|(w>>29&3),21),0x9f00001f)
 assert w&0x9f000000!=0x90000000,('UNKNOWN_ADRP',p)
 return None

def payload(a):
 b=Path(a['native']['path']).read_bytes();h,v=Path(a['container']['path']).read_bytes().split(b'\n\n',1);ls=h.decode().splitlines();m,n,c=ls[0].split()
 assert m=='KSEED1'and int(n)==len(b)and int(c)==len(ls)-1 and v==b
 ex={}
 for row in ls[1:]:
  name,p,k=row.split();assert name not in ex;ex[name]=[int(p),int(k)];assert int(p)%4==0 and 0<=int(p)<len(b)
 if 'exports'in a:assert ex=={k:list(v)for k,v in a['exports'].items()}
 for kind,data in [('native',b),('container',Path(a['container']['path']).read_bytes())]:
  if 'sha256'in a[kind]:assert hashlib.sha256(data).hexdigest()==a[kind]['sha256']
 return b,ex

def source_pool(source):
 import importlib.util
 p=Path(__file__).with_name('source-pool.py')
 spec=importlib.util.spec_from_file_location('current_source_owned_pool',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m.source_pool(source)

def audit(old,arm):
 A,ae=payload(old);N,ne=payload(arm);S=Path(old['source']['path']).read_bytes();assert S==Path(arm['source']['path']).read_bytes()
 if A==N:assert ae==ne;return dict(status='PASS_WHOLE_NATIVE_EXPORT_SOURCE_EXACT',changed=False)
 pool,entries=source_pool(S);op=len(A)-len(pool);np=len(N)-len(pool)
 assert A[op:]==N[np:]==pool,'SOURCE_POOL_BYTES'
 oa=na=0
 if pool:
  assert op%8==np%8==0
  oa=4 if A[op-4:op]==bytes(4)else 0;na=4 if N[np-4:np]==bytes(4)else 0
  assert ((op-oa+7)&-8)==op and ((np-na+7)&-8)==np
 ca,cn=op-oa,np-na;assert ca%4==cn%4==0
 ow=list(struct.unpack('<'+'I'*(ca//4),A[:ca]));nw=list(struct.unpack('<'+'I'*(cn//4),N[:cn])) # Current native images may end with compiler-owned inline lookup tables; their every word is compared below.
 sites=[];removed=set();mp={};p=q=0;scanSites=[];alignment=[]
 while p<ca:
  matched=False
  if p+8<=ca and q+4<=cn:
   mov=ow[p//4];mask=ow[p//4+1];src=(mov>>16)&31;dst=mov&31
   if mov&~((31<<16)|31)==0xaa0003e0 and dst==0 and src<31 and src!=dst and mask==0xd3401c00:
    fused=0xd3401c00|(src<<5)
    if nw[q//4]==fused:
     mp[p]=q;removed.add(p+4);sites.append(dict(oldPC=p,newPC=q,sourceRegister=src,destinationRegister=dst,width=8,oldWords=[hex(mov),hex(mask)],newWord=hex(fused),oldBytes=8,newBytes=4,all64ValuesEquivalent=True,allRegistersAndNZCVPreserved=True))
     p+=8;q+=4;matched=True
  if not matched and p>=4 and q>=4 and q<cn and ow[p//4-1]==nw[q//4-1]==0xd65f03c0:
   oldPad=4 if ow[p//4]==0xd503201f and p%8==4 and q%8==0 else 0
   newPad=4 if nw[q//4]==0xd503201f and q%8==4 and p%8==0 else 0
   if oldPad or newPad:
    assert A[p+oldPad:]==N[q+newPad:],'COMPLETE_INLINE_TABLE_TAIL_EQUALITY'
    alignment.append(dict(oldPC=p,newPC=q,removedBytes=oldPad,insertedBytes=newPad,followingTerminalRET=True,wholeRemainingTailEqual=True))
    if oldPad:removed.add(p)
    p+=oldPad;q+=newPad
  if not matched:
   assert p<ca and q<cn;mp[p]=q;p+=4;q+=4
 assert p==ca and q==cn and cn-ca==sum(s['newBytes']-8 for s in sites)+sum(x['insertedBytes']-x['removedBytes']for x in alignment),'UNATTRIBUTED_CODE_SIZE'
 def pos(p):
  if op<=p<len(A):return np+p-op
  assert p in mp,('REMOVED_OR_UNKNOWN_TARGET',p)
  return mp[p]
 # Literal/FADDR fixups use complete retained source-emitter pointer recipes,
 # never numeric constant normalization or native occurrence heuristics.
 literal={};literalRows=[];faddr={};faddrRows=[]
 for p in range(0,ca-8,4):
  if any(x not in mp for x in [p,p+4,p+8]):continue
  a,b,c=ow[p//4:p//4+3];d=a&31
  if a!=(0x10000000|d)or d==31:continue
  if b&~0x3ffc00 not in(0x91000000|(d<<5)|d,0xd1000000|(d<<5)|d):continue
  sign=-1 if b&0x40000000 else 1;want=(0xd1400000 if sign<0 else 0x91400000)|(d<<5)|d
  if c&~0x3ffc00!=want:continue
  target=p+sign*((b>>10&4095)+(c>>10&4095)*4096);nt=pos(target);delta=nt-pos(p);mag=abs(delta);assert mag>>12<=4095
  base=0xd1000000 if delta<0 else 0x91000000;faddr[p+4]=base|(d<<5)|d|((mag&4095)<<10);faddr[p+8]=base|0x400000|(d<<5)|d|((mag>>12)<<10)
  faddrRows.append(dict(oldPC=p,newPC=pos(p),oldTarget=target,newTarget=nt))
 for p in range(8,ca-24,4):
  if p not in mp or p+4 not in mp:continue
  u=ow[p//4];v=nw[pos(p)//4]
  if u==v or u&0xffe00000!=0xd2800000:continue
  rd=u&31;assert rd in(1,16,17)and v&~0x1fffe0==u&~0x1fffe0,'UNKNOWN_MOVZ_CHANGE'
  second=ow[p//4+1];assert second&~0x1fffe0==0xf2a00000|rd
  val=(u>>5&65535)|((second>>5&65535)<<16);owned=[e for e in entries if e['offset']==val-op]
  if rd==1:owned=[e for e in owned if e['kind']=='string'and ow[p//4+2]==(0xd2800002|(e['length']<<5))]
  assert len(owned)==1;entry=owned[0];length=entry['length'];at=p//4
  if rd==1:
   assert (ow[at+3]&~0x3ffc00==0xf94003e0 or ow[at+3]==0xaa0703e0)and ow[at+4:at+6]==[0xf9401c10,0xd63f0200]
   reason='source string offset/length + CTX callback56'
  elif rd==17 and entry['kind']=='string':
   assert ow[at-3]==(0xd2800011|(length<<5))and ow[at-2]==0xeb11013f and ow[at-1]&~0xffffe0==0x54000001 and ow[at+2]==0xeb11011f and ow[at+3]&~0xffffe0==0x54000000
   candidates=[t for t in range(max(7,at-41),at)if ow[t]==0xa9402608 and ow[t-2:t]==[0xf94094f0,0x8b111210]and ow[t-7:t-5]==[0xf94090f0,0xf9400210]and ow[t-5]&~0x3e0==0xd1000411 and ow[t-4]==0xeb10023f and ow[t-3]&~0xffffe0==0x54000002];assert len(candidates)==1
   reason='source descriptor string offset/length comparison'
  elif rd==16 and ow[at-1]==0xf940c0e5:
   assert ow[at+2:at+6]==[0x8b1000a5,0xd2800002,0xf9400080,0xf94000a1]or(ow[at+2]==0x8b1000a5 and all(ow[at+j]&~(31<<16)==x for j,x in[(3,0xaa0003e1),(4,0xaa0003e2),(5,0xaa0003e3)])and ow[at+6:at+8]==[0xf940048a,0xf940088b])
   reason='source numeric plane CTX_CODE_BASE5/offset16/ordered loads'
  else:
   assert rd==16 and ow[at-2]==0xf940c0f1 and ow[at-1]&~(31<<16)==0x8b000e31 and ow[at+2]&~31==0xf8706a20
   reason='source literal CTX_CODE_BASE17/index8/offset16/LDR'
  nv=pos(val);literal[p]=(u&~0x1fffe0)|((nv&65535)<<5);literal[p+4]=(second&~0x1fffe0)|((nv>>16)<<5);literalRows.append(dict(oldPC=p,newPC=pos(p),oldValue=val,newValue=nv,reason=reason))
 refs=[];allrefs=[];wordmap=[];tail=[]
 for p in range(0,ca,4):
  u=ow[p//4];r=ref(u,p)
  if r:allrefs.append(dict(pc=p,kind=r[0],target=r[1]))
  if p in removed:continue
  q=pos(p);v=nw[q//4];fused=next((x['newWord']for x in sites if x['oldPC']==p),None);expected=int(fused,16)if fused else literal.get(p,faddr.get(p,u));rr=ref(v,q)
  if r or rr:
   assert r and rr and r[0]==rr[0]and (u&r[2])==(v&r[2]);nt=pos(r[1])
   if rr[1]!=nt:
    assert r[0]=='B'and rr[1]==pos(r[1]+8)and ow[r[1]//4:r[1]//4+2]==[0xd2800005,0xf94004e8]
    tail.append(dict(oldPC=p,newPC=q,oldTarget=r[1],newTarget=rr[1]))
   expected=v;refs.append(dict(oldPC=p,newPC=q,kind=r[0],oldTarget=r[1],newTarget=rr[1]))
  assert v==expected,('UNDECLARED_WORD',p,q,hex(u),hex(v));wordmap.append(dict(oldPC=p,newPC=q,oldWord=hex(u),newWord=hex(v)))
 assert set(ae)==set(ne)
 for name,(p,arity)in ae.items():assert ne[name]==[pos(p),arity]
 assert not tail,'NO_EXTRA_TAIL_REWRITE'
 for pad in alignment:
  if pad['removedBytes']:
   assert not [r for r in allrefs if r['target']==pad['oldPC']]
   assert not [x for x,a in ae.values()if x==pad['oldPC']]
   assert not [x for x in faddrRows if x['oldTarget']==pad['oldPC']]
 assert sites,'NO_DECLARED_FUSION_CHANGE'
 for site in sites:
  interior=site['oldPC']+4
  assert not [r for r in allrefs if r['target']==interior],('FUSION_INTERIOR_REFERENCE',interior)
  assert not [x for x,a in ae.values()if x==interior]
  assert not [x for x in faddrRows if x['oldTarget']==interior]
 return dict(status='PASS_DIRECT_MASK_FUSION_FULL_NATIVE_RELOCATION_REPLAY',changed=True,sites=sites,alignment=alignment,oldBytes=len(A),newBytes=len(N),retainedWords=len(wordmap),wordMap=wordmap,PCMap=refs,literalPairs=literalRows,FADDR=faddrRows,sourcePoolBytes=len(pool),oldCodeEnd=ca,newCodeEnd=cn,exports=ne,allOtherWordsReferencesExportsAndPoolPreserved=True,performanceMeasured=False)
