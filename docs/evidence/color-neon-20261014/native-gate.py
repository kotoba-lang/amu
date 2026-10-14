from pathlib import Path
import struct,json,difflib
from native_utils_local import payload,ref,source_pool

def audit(old,new):
 A,ae=payload(old);B,be=payload(new)
 assert Path(old['source']['path']).read_bytes()==Path(new['source']['path']).read_bytes()
 if A==B:
  assert ae==be
  return dict(status='WHOLE_IDENTITY',changed=False)
 pool,entries=source_pool(Path(new['source']['path']).read_bytes())
 if pool:assert A[-len(pool):]==B[-len(pool):]==pool
 a=struct.unpack('<'+'I'*(len(A)//4),A);b=struct.unpack('<'+'I'*(len(B)//4),B)
 hs=[[i for i,w in enumerate(v)if w==cmp]for v,cmp in [(a,0xf100fe7f),(b,0xf100f67f)]]
 assert len(hs[0])==len(hs[1])==3
 start=hs[0][0]-3;assert start==hs[1][0]-3
 cold=[ref(v[start-29],(start-29)*4)[1]//4 for v in [a,b]]
 assert a[start-30]==b[start-30]==0xf101027f
 M={};references=[];padding=[];variants=[]
 def eq(p,q):
  x=ref(a[p],p*4);y=ref(b[q],q*4)
  if x:
   assert y and x[0]==y[0]and(a[p]&x[2])==(b[q]&y[2]),(p,q,x,y)
   references.append((p,q,x,y))
  else:assert a[p]==b[q],(p,q,hex(a[p]),hex(b[q]))
  M[p]=q
 def norm(v):return [w&r[2]if(r:=ref(w,i*4))else w for i,w in enumerate(v)]
 na,nb=norm(a),norm(b)
 for lo,hi,ql,qh in [(0,start,0,start),(cold[0],len(a),cold[1],len(b))]:
  for op,l,h,j,k in difflib.SequenceMatcher(None,na[lo:hi],nb[ql:qh],autojunk=False).get_opcodes():
   l+=lo;h+=lo;j+=ql;k+=ql
   if op=='equal':
    assert h-l==k-j
    for p,q in zip(range(l,h),range(j,k)):eq(p,q)
   else:
    assert op in ['insert','delete']and max(h-l,k-j)==1
    side,p,v=('old',l,a)if op=='delete'else('new',j,b)
    assert v[p]==0xd503201f and v[p-1]==0xd65f03c0 and(p+1)*4%8==0
    padding.append(dict(side=side,pc=p*4,unreachableAfterRET=True,literalAlignment8=True))
 bodies=json.loads(Path(__file__).with_name('neon-body-words.json').read_text())
 for ordinal,(h,q)in enumerate(zip(*hs)):
  ar=ref(a[h+1],(h+1)*4)[1]//4;br=ref(b[q+1],(q+1)*4)[1]//4
  endA=ref(a[ar+1],(ar+1)*4)[1]//4;endB=ref(b[br+1],(br+1)*4)[1]//4
  unit=a[ar+2:endA]
  assert a[h+2:ar-1]==unit*2
  assert b[br+2:endB-1]==unit,('SCALAR_REMAINDER_DELTA',ordinal)
  assert a[ar]==b[br]==0xf101027f
  assert a[h+1]&0xff00001f==b[q+1]&0xff00001f==0x54000002
  assert a[ar+1]&0xff00001f==b[br+1]&0xff00001f==0x54000002
  assert ref(a[ar-1],(ar-1)*4)[:2]==('B',h*4)
  assert ref(b[br-1],(br-1)*4)[:2]==('B',q*4)
  assert ref(b[endB-1],(endB-1)*4)[:2]==('B',br*4)
  expected=[0x8b130c89,*bodies[ordinal]['words'],0x91001273]
  assert list(b[q+2:br-1])==expected,('EXACT_NEON_WORDS',ordinal)
  assert all(ref(w,(q+2+i)*4)is None for i,w in enumerate(expected))
  assert not any(w&0xfffffc1f in [0xd61f0000,0xd63f0000]for w in expected)
  if ordinal<2:
   for p,t in zip(range(h-3,h),range(q-3,q)):eq(p,t)
  M[h]=q;M[h+1]=q+1
  for p,t in [(ar,br),(ar+1,br+1)]:eq(p,t)
  for i in range(len(unit)):eq(ar+2+i,br+2+i)
  nextA=(hs[0][1]-3 if ordinal==0 else hs[0][2])if ordinal<2 else cold[0]
  nextB=(hs[1][1]-3 if ordinal==0 else hs[1][2])if ordinal<2 else cold[1]
  assert nextA-endA==nextB-endB==8 and a[endA:nextA]==b[endB:nextB]and a[nextA-1]==0xd65f03c0
  for p,t in zip(range(endA,nextA),range(endB,nextB)):eq(p,t)
  variants.append(dict(kind=ordinal,oldHead=h*4,newHead=q*4,scalarWords=len(unit),exactNEONWords=len(expected),integerPointerBase=4,scratchGP=9,indexRegister=19,vectorRegisters=list(range(6)),fourPixels=True,signed16WrapClampUnsignedWiden=True,scalarRemainderSameWords=True,frameABIAndEpilogueUnchanged=True))
 oldPad={x['pc']for x in padding if x['side']=='old'};newPad={x['pc']for x in padding if x['side']=='new'}
 for p,q,x,y in references:
  if not start<=p<cold[0]:assert not start*4<=x[1]<cold[0]*4,('EXTERNAL_FAST_ENTRY',p,x)
  assert x[1]%4==y[1]%4==0 and M.get(x[1]//4,-1)*4==y[1],(p*4,q*4,x,y)
  assert x[1]not in oldPad and y[1]not in newPad
 for name,(pc,arity)in ae.items():assert be[name]==[M[pc//4]*4,arity]
 assert len(ae)==len(be)
 return dict(status='PASS_FULL_RETAINED_CODE_RELOCATIONS_EXACT_NEON_WORDS_SCALAR_REMAINDER_AND_ABI',changed=True,variants=variants,oldFastSpan=[start*4,cold[0]*4],newFastSpan=[start*4,cold[1]*4],padding=padding,retainedWords=len(M),references=len(references),fullGuardAndPrepaymentAndColdIdentity=True,allOutsideFastWordsCovered=True,sourcePoolBytes=len(pool),originalSourceAndExports=True,exhaustiveExactWordArithmeticWitness=True,gateInvokesNoCompilerOrGuest=True,adopted=False,performanceMeasured=False)

if __name__=='__main__':
 W=Path(__file__).parent;D=W/'physical-audit-v1';D.mkdir(exist_ok=False);G=json.loads((W/'all39-g1-screen-v1/generated-artifacts.json').read_text());rows=[]
 for x in G['images']:
  r=audit(x['baseline'],x['arm']);(D/(x['tag']+'.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(dict(tag=x['tag'],changed=r['changed']))
 assert len(rows)==39 and sum(x['changed']for x in rows)==2
 (D/'report.json').write_text(json.dumps(dict(status='PASS_ALL39',rows=rows),indent=2)+'\n');print('PASS_ALL39')
