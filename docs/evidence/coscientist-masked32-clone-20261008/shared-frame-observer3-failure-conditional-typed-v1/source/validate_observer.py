"""Pure saved-data observer validator; no semantic rewrite admission."""
import re,struct
TAGS={'SH','SQ','SF','SN','ST','SY','SS','SC','SX','SB','SE','SZ','SI','SG','SL','SD'}
def need(x,m):
 if not x:raise AssertionError(m)
def split(raw):
 need(type(raw)is bytes and 0<len(raw)<=8388608,'raw8MiB');ls=raw.splitlines(keepends=True);need(ls and all(x.endswith(b'\n')for x in ls)and ls[-1].startswith(b'{:ok true,'),'complete suffix');return ls[:-1],ls[-1]
def shape(fn,sir,f):
 if not 0<f<len(fn):return None
 r=fn[f];p=r[12]
 if not(0<p and p+15<len(sir)and r[2]in [1,2]and r[3]==1 and r[4]==r[5]==4 and 0<=r[10]<=16 and 0<=r[15]<=16):return None
 if sir[p][0:3]!=[1,f,1]or sir[p+1][0]!=18 or sir[p+2][0]!=9:return None
 for j in range(p+3,p+13):
  op,a,b,c=sir[j]
  if op==13:
   tail=sir[j+1][1]
   if not(c in [4,7]and b==0 and 0<a<len(fn)and fn[a][3]==c and fn[a][4]==4):return None
   if not(sir[j+1][0]==13 and sir[j+1][2:]==[0,1]and 0<tail<len(fn)and fn[tail][3]==1 and fn[tail][4]==fn[tail][5]==4):return None
   if sir[j+2][0:2]!=[19,0]or sir[j+3][0:2]!=[2,f]:return None
   return {'first':p,'end':j+4,'helper':a,'tail':tail,'helperSite':j,'tailSite':j+1}
  if op not in [3,4]:return None
 return None
def selection(fn,sir):
 sh={f:shape(fn,sir,f)for f in range(1,len(fn))};incoming={r['tail']for r in sh.values()if r};roots=[f for f,r in sh.items()if r and f not in incoming]
 q=[0]*16
 if not roots:return q
 f=roots[0]
 for k in range(12):
  r=sh.get(f)
  if not r or f in q[4:4+k]or q[1]+r['end']-r['first']>256:return [0]*16
  q[4+k]=f;q[0]+=1;q[1]+=r['end']-r['first'];q[2]+=2;q[3]=r['tail'];f=r['tail']
 roles={}
 for owner in q[4:]:
  r=sh[owner];helper=r['helper'];n=sir[r['helperSite']][3]
  if helper in q[4:]or helper==q[3]or(n in roles and roles[n]!=helper):return [0]*16
  roles[n]=helper
 return q
def validate(lines,payload,source=None,expectedFNCount=None):
 rows=[]
 for l in lines:
  m=re.fullmatch(rb'([A-Z]+)((?: -?(?:0|[1-9][0-9]{0,19}))+)\n',l);need(m is not None and m[1].decode()in TAGS,'unknown/refuse/incomplete row');v=list(map(int,m[2].split()));need(all(-(2**63)<=x<2**64 for x in v),'width');rows.append((m[1].decode(),v))
 at=0
 def take(t):
  nonlocal at
  need(at<len(rows)and rows[at][0]==t,'ordered '+t);v=rows[at][1];at+=1;return v
 def table(t,phase,n,w):
  out=[]
  for i in range(n):
   r=take(t);need(len(r)==w+2 and r[:2]==[phase,i],'complete ordered '+t);out.append(r[2:])
  return out
 def head(phase):
  h=take('SH');need(len(h)==11 and h[:2]==[phase,0],'header');need(1<=h[2]<=512 and 1<=h[3]<=196608 and 1<=h[4]<=196608 and 1<=h[5]<=262144 and 1<=h[6]<=65536 and 1<=h[7]<=524288 and 1<=h[8]<=65536 and 0<=h[9]<=131072 and 0<=h[10]<=1024,'count caps');need(h[5]*120+h[4]*240+h[6]*240+h[3]*140+h[2]*1200+h[7]*48+h[8]*240+h[9]*120+h[10]*120+1048576<=8388608,'whole output law');return h
 h0=head(0);need(expectedFNCount is None or h0[2]==expectedFNCount,'prior current FN count');q=take('SQ');need(len(q)==16 and 0<=q[0]<=12 and q[1]<=256 and q[2]<=64,'region bounds');fn=table('SF',0,h0[2],16);nodes=table('SN',0,h0[4],8);tokens=table('ST',0,h0[5],4);syms=table('SY',0,h0[6],8);sir=table('SS',0,h0[3],4);need(take('SZ')==[0],'pre footer')
 need(selection(fn,sir)==q,'non-name structural root selection');owners=q[4:4+q[0]];selected={i:f for f in owners for i in range(shape(fn,sir,f)['first'],shape(fn,sir,f)['end'])};need(len(selected)==q[1],'complete owned SIR')
 for i,n in enumerate(nodes):need(0<=n[1]<len(nodes)and 0<=n[2]<len(nodes)and 0<=n[3]<len(tokens)and 0<=n[5]<len(syms),'node token/symbol references')
 for t in tokens:need(0<=t[1]<=t[2] and (source is None or t[2]<=len(source)),'token source bounds')
 for y in syms:need(0<=y[0]<=y[1]and (source is None or y[1]<=len(source))and 0<=y[4]<len(fn),'symbol source/FN refs')
 for f,r in enumerate(fn):need(0<=r[0]<len(syms)and 0<=r[1]<len(nodes)and 0<=r[12]<len(sir),'FN identity refs')
 for f in owners:need(fn[f][1]>0 and fn[f][0]>0 and syms[fn[f][0]][4]==f,'selected declared owner identity')
 events={};states={}
 def state():
  g=take('SG');need(len(g)==18 and g[0]in [0,1]and g[1]in selected,'state site');phase,i=g[:2];G=g[2:];need(0<=G[4]<=16 and 0<=G[5]<=16 and 0<=G[3]<=32768 and G[3]%16==0 and 0<=G[2]<=10 and G[0]in [0,1,2]and G[11]in [0,1],'frame/state bounds')
  key=(phase,i);need(key not in states,'unique state');locals=[];temps=[]
  for k in range(G[4]+1):r=take('SL');need(len(r)==5 and r[:3]==[phase,i,k]and 0<=r[3]<=29 and r[4]>=0,'slot state');locals.append(r[3:])
  for k in range(G[5]):r=take('SD');need(len(r)==5 and r[:3]==[phase,i,k]and 0<=r[3]<=5,'temp descriptor');temps.append(r[3:])
  states[key]={'G':G,'locals':locals,'temps':temps}
 while at<len(rows)and rows[at][0]in ['SI','SG']:
  if rows[at][0]=='SG':state();continue
  r=take('SI');need(len(r)==6 and r[0]in selected and r[0]not in events and 1<=r[1]<=r[2]<=524288 and 0<=r[3]<=256 and r[4]==sir[r[0]][0]and r[5]==0,'actual original gn-ins interval');events[r[0]]=r
 h1=head(1);need(h1[2:7]==h0[2:7],'frontend counts stable');need(take('SQ')==q,'selection stable');fn1=table('SF',1,h1[2],16);code1=table('SC',1,h1[7],1);fix1=table('SX',1,h1[8],4);labels1=table('SB',1,h1[9],1);need(take('SZ')==[1],'emit footer')
 h2=head(2);need(h2[2:10]==h1[2:10],'layout count identity');need(take('SQ')==q,'layout selection');fn2=table('SF',2,h2[2],16);code2=table('SC',2,h2[7],1);fix2=table('SX',2,h2[8],4);labels2=table('SB',2,h2[9],1);exports=table('SE',2,h2[10],4);need(take('SZ')==[2]and at==len(rows),'final footer/no extras')
 need(fn1==fn2 and fix1==fix2 and labels1==labels2,'layout metadata unchanged');need(all(a[:13]+a[14:]==b[:13]+b[14:]for a,b in zip(fn,fn1)),'FN only CODE changes');need(all(0<=r[0]<2**32 for r in code1+code2),'u32 words')
 need(type(payload)is bytes and len(payload)>0 and len(payload)<=4194304 and len(payload)%4==0,'whole aligned payload');want=b''.join(struct.pack('<I',r[0])for r in code2[1:]);need(payload==want,'complete layout CODE projection, no literal pool')
 patched=[r[0]for r in code1]
 for x in fix1[1:]:
  pc,kind,tgt,aux=x;need(1<=pc<len(patched)and kind in [1,2,3,4,6]and aux in [0,1],'complete resolvable no-literal fix')
  target=fn1[tgt][13]if kind in [4,6]and 0<tgt<len(fn1)else labels1[tgt][0]if kind in [1,2,3]and 0<tgt<len(labels1)else 0
  need(0<target<len(patched),'fix target')
  if aux:need(kind==4 and (patched[pc]&0xfc000000)==0x14000000 and patched[target]==0xd2800005 and target+1<len(patched),'chain aux witness');target+=1
  d=target-pc
  if kind in [1,4]:need(-(1<<25)<=d<(1<<25),'imm26');patched[pc]=(patched[pc]&0xfc000000)|(d&0x3ffffff)
  else:need(-(1<<18)<=d<(1<<18),'imm19');patched[pc]=(patched[pc]&0xff00001f)|((d&0x7ffff)<<5)
 need(patched==[r[0]for r in code2],'all resolved fixups project exactly')
 expectedExports=[[f,(r[13]-1)*4,r[3],0]for f,r in enumerate(fn1)if f>0 and r[11]==1]
 need(exports==[[0,0,0,0]]+expectedExports,'complete FN/export relation')
 for f in owners:
  r=shape(fn,sir,f);i=r['first']
  while i<r['end']:
   need(i in events,'visited selected ownership');ev=events[i];need(ev[1]>=fn1[f][13]and ev[2]<=len(patched),'owned CODE interval');i+=1+ev[3]
  need(i==r['end'],'skip exact end');need((1,r['first'])in states,'post-FN snapshot')
  for j in [r['helperSite'],r['tailSite']]:need((0,j)in states and (1,j)in states,'pre/post CALL snapshot')
 expectedStates={(1,shape(fn,sir,f)['first'])for f in owners}|{(phase,j)for f in owners for j in [shape(fn,sir,f)['helperSite'],shape(fn,sir,f)['tailSite']]for phase in [0,1]};need(set(states)==expectedStates,'no orphan/missing state')
 boundary={q[3]}if owners else set();boundary|={shape(fn,sir,f)['helper']for f in owners};need(len(set(owners)|boundary)<=16,'body/boundary owner count')
 origin=[];totalReachable=set()
 for f in owners:
  root=fn[f][1];seen=set()
  def child_chain(n):
   while n:
    need(n not in seen and len(seen)<4096,'complete acyclic body identity cap');seen.add(n);child_chain(nodes[n][1]);n=nodes[n][2]
  seen.add(root);child_chain(nodes[root][1]);totalReachable|=seen;need(len(totalReachable)<=4096,'bounded selected body identity nodes')
  tok=sorted({nodes[n][3]for n in seen if nodes[n][3]>0});sym=syms[fn[f][0]];name=source[sym[0]:sym[1]].decode('utf-8')if source is not None else None
  origin.append({'owner':f,'FN':fn[f],'rootNode':root,'reachableNodes':sorted(seen),'tokenRefs':tok,'sourceNameIdentityOnly':name,'sourceTokenSpans':[[t,tokens[t][1],tokens[t][2]]for t in tok]})
 calls=[]
 for f in owners:
  sh=shape(fn,sir,f)
  for role,j in [('returning-helper',sh['helperSite']),('unary-tail',sh['tailSite'])]:
   ev=events[j];fx=[x for x in fix1[1:]if ev[1]<=x[0]<ev[2]and x[1]==4 and x[2]==sir[j][1]]
   opcode=(code1[fx[0][0]][0]&0xfc000000)if len(fx)==1 else None
   calls.append({'owner':f,'SIR':j,'role':role,'callee':sir[j][1],'codeStart':ev[1],'codeStop':ev[2],'matchingFunctionFixups':fx,'emissionClass':'generic-returning-BL'if len(fx)==1 and opcode==0x94000000 else'generic-tail-B'if len(fx)==1 and opcode==0x14000000 else'specialized-or-unclassified','preState':states[(0,j)],'postState':states[(1,j)]})
 return {'status':'OBSERVED_BOUNDED_SHARED_FRAME_REGION_STRUCTURE_ONLY'if owners else'REJECTED_BOUNDED_SHARED_FRAME_REGION_NO_ROOT_OR_12_CHAIN','selectedOwners':owners,'selectedSIR':q[1],'selectedEdges':q[2],'genericBoundaryOwners':sorted(boundary),'wholeCODEProjection':True,'allFIXProjection':True,'currentBodyNodeTokenIdentityInventoryComplete':True,'frameStates':states_to_rows(states),'callSelections':calls,'selectedBodyOrigins':origin,'safeRewriteQualified':False,'pending':['incoming private entry/dominance','parallel parameter moves','relocated homes/outgoing area/context/callee-save union/sl-vector registers','defined stack-limit trap and exact fuel/vector/17-arena equivalence'],'globalApplicabilityClaim':False}
def states_to_rows(s):return [{'phase':phase,'SIR':i,**r}for (phase,i),r in sorted(s.items())]
