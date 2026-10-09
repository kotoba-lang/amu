"""Strict finite observer schema + ordinary SIR/typed owner/source joins."""
import re,struct
WIDTH={'FH':7,'FSIR':6,'FF':4,'FNODE':5,'FSYM':5,'FTOK':5,'FCALL':17,'FG':4,'FOUT':7,'FCODE':2,'FLABEL':2,'FFIX':5,'FLIT':5,'FLITB':2,'FEXP':5,'FEND':2}
def verify(raw,source,native,offset):
 assert isinstance(raw,bytes)and len(raw)<=1048576;rows={k:[]for k in WIDTH};ok=[]
 for line in raw.splitlines():
  if line.startswith(b'{:ok true,'):
   assert re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output "[^"\r\n]+", :bytes [0-9]+\}',line);ok.append(line);continue
  z=line.decode('ascii').split();assert z and z[0]in WIDTH and len(z)==WIDTH[z[0]]+1;v=list(map(int,z[1:]));assert all(-(1<<63)<=x<(1<<63)for x in v);rows[z[0]].append(v)
 assert len(ok)==1 and len(rows['FH'])==2 and len(rows['FOUT'])==1 and rows['FEND']==[[1,0]]
 heads={z[0]:z for z in rows['FH']};assert set(heads)=={0,1};assert heads[0]==[0,*heads[1][1:]];_,err,sn,fn,nn,sy,tn=heads[0];assert err==0 and 1<sn<=128 and 1<fn<=16
 S={};F={};names={};nodes={}
 for phase in [0,1]:
  sir=[z for z in rows['FSIR']if z[0]==phase];assert [z[1]for z in sir]==list(range(1,sn));S[phase]={z[1]:z[2:]for z in sir}
  ff=[z for z in rows['FF']if z[0]==phase];assert len(ff)==16*(fn-1)and len({tuple(z[:3])for z in ff})==len(ff);F[phase]={f:[next(z[3]for z in ff if z[1:3]==[f,k])for k in range(16)]for f in range(1,fn)}
  for f in F[phase]:
   rec=F[phase][f];n=[z for z in rows['FNODE']if z[:2]==[phase,f]];s=[z for z in rows['FSYM']if z[:2]==[phase,f]];t=[z for z in rows['FTOK']if z[:2]==[phase,f]]
   assert len(n)==len(s)==8 and len(t)==4 and [z[3]for z in n]==list(range(8))and [z[3]for z in s]==list(range(8))and [z[3]for z in t]==list(range(4));assert all(z[2]==rec[1]for z in n)and all(z[2]==rec[0]for z in s)and 0<rec[1]<nn and 0<rec[0]<sy
   nv=[z[4]for z in n];sv=[z[4]for z in s];tv=[z[4]for z in t];assert all(z[2]==nv[3]for z in t)and 0<nv[3]<tn and 0<=tv[1]<=tv[2]<=len(source)and 0<=sv[0]<sv[1]<=len(source)
   name=source[sv[0]:sv[1]].decode('ascii');assert name in ['mask','mix','extra','bench'];names[phase,f]=name;nodes[phase,f]=nv
 assert S[0]==S[1]and len(set(names[0,f]for f in F[0]))==4 and set(names[0,f]for f in F[0])=={'mask','mix','extra','bench'}
 for f in F[0]:assert names[0,f]==names[1,f]and all(F[0][f][k]==F[1][f][k]for k in range(16)if k!=13)
 ids={names[0,f]:f for f in F[0]};mask,mix,extra,bench=[ids[n]for n in ['mask','mix','extra','bench']]
 for f,r in F[0].items():
  assert r[4]==1 and r[3]==(2 if f==mix else 1)and all(r[5+k]==1 for k in range(r[3]));assert r[11]==(1 if f==bench else 0)and r[14]==(0 if f==mask else 1)
 owners={};current=0;ends={};labels={}
 for i,z in S[0].items():
  op,a,b,c=z
  assert op in {1,2,3,4,5,6,7,8,9,13,18,19}
  if op==1:assert current==0 and a in F[0]and F[0][a][12]==i and b==F[0][a][3]and c==F[0][a][10];current=a
  assert current>0;owners[i]=current
  if op==9:assert a>0 and a not in labels;labels[a]=i
  if op==2:assert a==current and b==c==0;ends[a]=i;current=0
 assert current==0 and set(ends)==set(F[0]);calls=[(i,z)for i,z in S[0].items()if z[0]==13];assert sum(z[1]==mask for i,z in calls)==2 and {owners[i]for i,z in calls if z[1]==mask}=={mix,extra}
 for f,rec in F[0].items():
  fuel=[j for j,z in S[0].items()if owners[j]==f and z[0]==18];assert fuel==([]if f==mask else[rec[12]+1]);assert all(S[0][j]==[18,0,0,0]for j in fuel)
 p=F[0][mask][12];expected=[[1,mask,1,1],[9,S[0][p+1][1],0,0],[4,0,1,0],[3,1,4294967295,0],[6,5,0,0],[19,0,0,0],[2,mask,0,0]];assert [S[0][j]for j in range(p,ends[mask]+1)]==expected
 ep=F[0][mix][12];end=ends[mix];assert S[0][ep+1]==[18,0,0,0]and S[0][end-2]==[13,mask,0,1]and S[0][end-1]==[19,0,0,0]
 admitted=[z for z in rows['FCALL']if z[5]>0];assert len(admitted)==1;a=admitted[0];i,owner,f,t,n,before,after,start,stop,sites,newsites,ctx,newctx,leaf,freg,e0,e1=a;assert owner==bench and owners[i]==bench and f==mix and S[0][i]==[13,mix,t,2]and n==2 and before==end and after==0 and newsites==sites+1 and ctx==0 and newctx==1 and leaf==freg==e0==e1==0 and 0<stop-start<=192
 assert [z[0]for z in rows['FCALL']]==[i for i,z in calls];assert len({z[0]for z in rows['FCALL']})==len(rows['FCALL'])
 for call in rows['FCALL']:
  for phase in [0,1]:
   g=[z for z in rows['FG']if z[:2]==[call[0],phase]];assert len(g)==16 and [z[2]for z in g]==list(range(16))
   if call[5]>0:
    values=[z[3]for z in g];assert values[0]==0 and values[3]>0 and values[3]%16==0 and values[4]==F[0][bench][10]and values[5]==F[0][bench][15]and values[7]==phase and values[11]==0
    assert values[6]==(2 if phase==0 else 1)
    if phase==0:assert values[6]==call[3]+call[4]
 h=rows['FOUT'][0];cn,cb,ln,fxn,ltn,lbn,en=h;assert 1<cn<=256 and cb==len(native)and (cn-1)*4==cb and ltn==lbn==1
 code=rows['FCODE'];assert [z[0]for z in code]==list(range(cn))and code[0]==[0,0]and all(0<=z[1]<2**32 for z in code);assert b''.join(struct.pack('<I',z[1])for z in code[1:])==native
 for tag,count in [('FLABEL',ln),('FFIX',fxn),('FLIT',ltn),('FLITB',lbn),('FEXP',en)]:assert [z[0]for z in rows[tag]]==list(range(1,count))
 assert (F[1][bench][13]-1)*4==offset and 0< F[1][mix][13] <F[1][bench][13] and rows['FEXP']==[[1,bench,offset,1,0]]
 # Exact current fixedfixture physical transition: original context reload then original five fuel words.
 words={j:w for j,w in code};assert start==47 and stop==62 and sites==0 and newsites==1
 assert [words[j]for j in range(start,start+3)]==[0xaa1303e0,0xd28000e1,0xf9401fe7]
 assert [words[j]for j in range(start+3,start+8)]==[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0]
 assert rows['FFIX']==[[1,34,4,mask,0]];pc=34;w=words[pc];assert w>>26==0b000101
 disp=w&0x03ffffff;disp=disp-(1<<26)if disp&(1<<25)else disp
 assert (pc-1)*4+disp*4==(F[1][mask][13]-1)*4
 return {'status':'PASS_FINITE_TYPED_OWNER_OBSERVER_RECORDS_ONLY','functionNamesToIDs':ids,'SIRRows':sn-1,'admittedCall':a,'staticMaskReferences':2,'calleeEnd':end,'codeWords':cn,'nativeBytes':cb,'benchOffset':offset,'ordinaryTypedSourceOwnerCorrespondence':True,'actualCPUTrapQualified':False,'performanceQualified':False}
