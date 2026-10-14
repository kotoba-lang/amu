from pathlib import Path
import struct,json,difflib
from native_utils_local import payload,ref,source_pool

def norm(v):
 return [w&r[2]if(r:=ref(w,i*4))else w for i,w in enumerate(v)]
def narrow(w):
 return (((w>>10)&63)+1)if w&0xffff03ff==0x93400129 else 0
def load(w):return w&0xffc003ff==0xf9400149
def store(w):return w&0xffc003ff==0xf9000149
def movwide(w):return w&0xff80001f in [0x92800009,0xd2800009,0xf2800009]

def audit(old,new):
 A,ae=payload(old);B,be=payload(new)
 assert Path(old['source']['path']).read_bytes()==Path(new['source']['path']).read_bytes()
 if A==B:
  assert ae==be
  return dict(status='WHOLE_IDENTITY',changed=False)
 pool,_=source_pool(Path(new['source']['path']).read_bytes())
 if pool:assert A[-len(pool):]==B[-len(pool):]==pool
 a=struct.unpack('<'+'I'*(len(A)//4),A);b=struct.unpack('<'+'I'*(len(B)//4),B)
 removed=set();blocks=[]
 # Exact canonical CW guard/prepayment and complete <=16-stage linear body.
 for at in range(12,len(a)-16):
  if list(a[at:at+2])!=[0xf940a4ea,0x8b110d4a]:continue
  sub=a[at+2];cost=(sub>>10)&4095;n=(cost+1)//2
  if sub&0xffc003ff!=0xd1000108 or cost!=2*n-1 or not 4<=n<=16 or a[at+3]!=0xf90004e8:continue
  q=at-12
  assert a[q]&0xffc003ff==0xf100011f and(a[q]>>10)&4095==cost
  assert list(a[q+2:q+6])==[0xf9409cf0,0xf9400210,0xd1000411,0xeb10023f]
  assert list(a[q+7:q+10])==[0xf940a0f0,0x8b111210,0xa9404211]
  assert a[q+10]&0xffc003ff==0xf100021f
  guards=[q+1,q+6,q+11];targets=[]
  for j,cond in zip(guards,[3,2,9]):
   r=ref(a[j],j*4);assert r and r[0]=='BC'and a[j]&0xff00001f==0x54000000|cond;targets.append(r[1]//4)
  assert len(set(targets))==1
  start=at+4;j=start;lastIndex=-1;lastWidth=0;steps=[]
  for k in range(n):
   first=j;forward=False;read=None;constant=False
   if load(a[j]):
    read=(a[j]>>10)&4095;forward=read==lastIndex
    if forward:removed.add(j)
    j+=1
   else:
    assert movwide(a[j]);constant=True
    while movwide(a[j]):j+=1
   width=narrow(a[j]);omitNarrow=False
   if width:
    omitNarrow=forward and lastWidth>0 and lastWidth<=width
    if omitNarrow:removed.add(j)
    j+=1
   assert store(a[j]);index=(a[j]>>10)&4095
   steps.append(dict(oldSpan=[first*4,(j+1)*4],readIndex=read,writeIndex=index,signWidth=width,previousSignWidth=lastWidth,forwardedLoad=forward,omittedNarrow=omitNarrow,constant=constant,originalStoreRetained=True))
   lastIndex=index;lastWidth=width if width else lastWidth if forward else 0;j+=1
  assert a[j]==0xd2800005 and ref(a[j+1],(j+1)*4)[0]=='B'
  assert targets[0]==j+2,'Cold path must start immediately after fast body'
  assert not any(ref(w,(start+i)*4)for i,w in enumerate(a[start:j]))
  blocks.append(dict(oldGuard=q*4,oldBody=[start*4,j*4],stages=n,cost=cost,steps=steps,allOriginalRangeFuelDescriptorGuardsRetained=True))
 assert removed,'Changed image without certified CW omission'
 virtual=[(i,w)for i,w in enumerate(a)if i not in removed];vn=norm([w for i,w in virtual]);bn=norm(b)
 # Normalize references at their original coordinates, not virtual offsets.
 vn=[w&r[2]if(r:=ref(w,i*4))else w for i,w in virtual]
 mapping={};padding=[]
 for op,lo,hi,ql,qh in difflib.SequenceMatcher(None,vn,bn,autojunk=False).get_opcodes():
  if op=='equal':
   assert hi-lo==qh-ql
   for v,t in zip(range(lo,hi),range(ql,qh)):mapping[virtual[v][0]]=t
  else:
   assert op in ['insert','delete']and max(hi-lo,qh-ql)==1,(op,lo,hi,ql,qh)
   side,i,v=('old',virtual[lo][0],a)if op=='delete'else('new',ql,b)
   assert v[i]==0xd503201f and v[i-1]==0xd65f03c0 and(i+1)*4%8==0
   padding.append(dict(side=side,pc=i*4,unreachableRETAlignmentOnly=True))
 refs=0
 for i,j in mapping.items():
  r=ref(a[i],i*4);nr=ref(b[j],j*4)
  if r:
   assert nr and r[0]==nr[0]and(a[i]&r[2])==(b[j]&nr[2])
   assert r[1]%4==nr[1]%4==0 and mapping.get(r[1]//4,-1)*4==nr[1],('Incoming omitted word',i,r,nr)
   refs+=1
  else:assert a[i]==b[j],(i,j)
 for name,(pc,arity)in ae.items():assert be[name]==[mapping[pc//4]*4,arity]
 assert len(ae)==len(be)
 return dict(status='PASS_CLOSED_LINEAR_CW_FORWARDING_ALL_RETAINED_WORDS_RELOCATIONS_STORES_GUARDS_ABI',changed=True,blocks=blocks,omittedWords=len(removed),forwardedLoads=sum(s['forwardedLoad']for x in blocks for s in x['steps']),omittedNarrow=sum(s['omittedNarrow']for x in blocks for s in x['steps']),retainedWords=len(mapping),references=refs,padding=padding,sourcePoolBytes=len(pool),noExternalEntryToOmittedWords=True,allOriginalStoresAndColdPathAndChargesRetained=True,adopted=False,performanceMeasured=False)

if __name__=='__main__':
 W=Path(__file__).parent;D=W/'physical-audit-v1';D.mkdir(exist_ok=False);G=json.loads((W/'all39-g1-screen-v1/generated-artifacts.json').read_text());rows=[]
 for e in G['images']:
  r=audit(e['baseline'],e['arm']);(D/(e['tag']+'.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(dict(tag=e['tag'],changed=r['changed'],forwardedLoads=r.get('forwardedLoads',0),omittedNarrow=r.get('omittedNarrow',0)))
 assert len(rows)==39
 (D/'report.json').write_text(json.dumps(dict(status='PASS_ALL39',rows=rows),indent=2)+'\n');print('PASS_ALL39',[(r['tag'],r['forwardedLoads'],r['omittedNarrow'])for r in rows if r['changed']])
