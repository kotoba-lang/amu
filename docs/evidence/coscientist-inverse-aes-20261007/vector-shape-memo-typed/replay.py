"""Stdlib data-only fixedfixture reader; no archived code execution."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,sys,sysconfig,os,re
BASE=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();temp_roots=[]
allowed={BASE/'typed-vector-proof.manifest.json',BASE/'typed-vector-proof.tgz',Path(__file__).resolve()};stdlib=Path(sysconfig.get_path('stdlib')).resolve()
def guard(event,args):
 if event!='open'or isinstance(args[0],int):return
 f=Path(os.fsdecode(args[0])).resolve()
 if f in allowed or any(f.is_relative_to(p)for p in temp_roots):return
 if f.is_relative_to(stdlib)and'site-packages'not in f.parts and'dist-packages'not in f.parts:return
 raise PermissionError('hermetic path rejected '+str(f))
sys.addaudithook(guard)
mp=BASE/'typed-vector-proof.manifest.json';assert sha(mp.read_bytes())=='c9b897d996d85060a3ce5534a0dc65d7282d8b2a282c1a254e93dd6294d29625','manifest envelope hash';m=json.loads(mp.read_text());archive=BASE/m['archive']
assert archive.stat().st_size==m['archiveBytes']<=4194304 and sha(archive.read_bytes())==m['archiveSHA256'],'archive envelope hash'
assert len(m['paths'])<=1000 and m['uncompressedObjectBytes']<=33554432

WIDTH={'PIPELINE':4,'SELECTOR':14,'COUNTS':2,'SIR':5,'FREC':17,'FNNAME':3,'ALLOC':6,'EDGE':5,'ARG':10,'CAPTURE':8,'CAPTUREPOST':7,'REPLAY':5,'BOUNDS':7,'COMPARE':5,'END':4,'RESULT':8}
def parse(text):
 out=[]
 for line in text.splitlines():
  p=line.split();assert p and p[0]in WIDTH and len(p)==1+WIDTH[p[0]],('recordwidth',line);assert all(re.fullmatch(r'-?\d+',x)for x in p[1:]);out.append((p[0],list(map(int,p[1:]))))
 return out
def validate(text,c):
 assert 0<=c<3;records=parse(text);by={t:[x for tag,x in records if tag==t]for t in WIDTH}
 def one(tag):assert len(by[tag])==1,(tag,'singleton');return by[tag][0]
 unity=(W/'vector-typed-analysis-v8/unity-vector-analysis-on.kotoba').read_text();const=lambda n:int(re.search(r'\(def '+re.escape(n)+r' (\d+)\)',unity)[1]);heap=const('MM-HEAP-BASE');words=const('gn-a-lp')+const('MM-LABEL-CAP')+82
 pipeline=one('PIPELINE');assert pipeline[0]==c and pipeline[1]==0 and pipeline[3]==8388608
 pre,n,base,top,ok,err=one('ALLOC');assert pre==base==max(pipeline[2],heap)and n==words and top==base+words and top<=pipeline[3]and ok==1 and err==0
 sn,fn=one('COUNTS');assert fn==6 and [x[0]for x in by['SIR']]==list(range(1,sn))and [x[0]for x in by['FREC']]==list(range(1,fn))
 S=(D/'fixture.kotoba').read_text();names={f:S[a:b]for f,a,b in by['FNNAME']};assert set(names.values())=={'positive-sink','zero-sink','preserving-self','unknown-entry','bench'}and len(names)==5
 lookup={n:f for f,n in names.items()};frec={x[0]:x[1:]for x in by['FREC']};sir={x[0]:x[1:]for x in by['SIR']};opcall=const('OP-CALL');opfn=const('OP-FN')
 for n in ['positive-sink','zero-sink','preserving-self','unknown-entry']:assert frec[lookup[n]][const('FF-PT0')]==const('TY-VEC')
 for n in ['positive-sink','zero-sink','preserving-self']:assert frec[lookup[n]][const('FF-KIND')]==const('FK-PRIV')and frec[lookup[n]][const('FF-EXPORT')]==0
 for n in ['unknown-entry','bench']:assert frec[lookup[n]][const('FF-EXPORT')]!=0
 edges=[];caller=0
 for j,op,a,b,arity in by['SIR']:
  if op==opfn:caller=a
  if op==opcall:assert arity==frec[a][const('FF-NPARAMS')];edges.append([len(edges),caller,j,a,b])
 assert by['EDGE']==edges and edges;ed={e:(f,j,t,b)for e,f,j,t,b in edges};siteEdge={j:e for e,f,j,t,b in edges};sf=lookup['preserving-self'];assert any(f==t==sf for e,f,j,t,b in edges),'noactualselfOPCALL'
 end=one('END');assert end[0:2]==[c,0]and end[2]==(1 if c==2 else 0)and 0<=end[3]<=268435456
 assert one('RESULT')==[c,1,1,50689,1,8388608,base,words]
 positive=[];zero=[];selfskip=[];lastarg=None;pendingcap=None
 for tag,x in records:
  if tag=='ARG':
   f,j,t,k,pos,known,token,L,selfflag,contribute=x;assert j in siteEdge and ed[siteEdge[j]][0:3]==(f,j,t)and 0<=k<4 and pos>=0 and L>=0 and known in [0,1]
   assert selfflag==int(f==t and known==1 and token==pos);assert contribute==int(pos>0 and not selfflag);lastarg=x
   if selfflag:selfskip.append(x)
  elif tag=='CAPTURE':
   f,j,t,k,b,L,link,ref=x;assert ref==0 and lastarg is not None;assert lastarg[0:4]==[f,j,t,k]and lastarg[7]==L and lastarg[9]==1;assert link==siteEdge[j]+1 and ed[link-1]==(f,j,t,b);pendingcap=x
  elif tag=='CAPTUREPOST':
   f,j,t,k,link,ref,value=x;assert pendingcap is not None and pendingcap[0:4]==[f,j,t,k]and pendingcap[6]==link and ref==0 and 0<=value<=pendingcap[5]
   if t==lookup['positive-sink']and pendingcap[5]==4 and value==4:positive.append(x)
   if t==lookup['zero-sink']and pendingcap[5]==0 and value==0:zero.append(x)
   pendingcap=None
  elif tag=='REPLAY':
   f,e,t,k,value=x;assert e in ed and ed[e][0]==f and ed[e][2]==t and 0<=k<4 and value>=-1
 if c<2:assert positive and zero and selfskip,'missinggenuinepositive/zero/preservesSelf'
 if c==0:assert not by['COMPARE']and not by['BOUNDS']
 elif c==1:
  compares=by['COMPARE'];assert len(compares)==5 and [x[0]for x in compares]==list(range(1,fn))and all(x[1:]==[1,0,0,1]for x in compares)
  batches=[];batch=[]
  for tag,x in records:
   if tag=='BOUNDS':batch.append(x)
   if tag=='COMPARE':batches.append((x[0],batch));batch=[]
  assert not batch and len(batches)==5
  for f,rows in batches:
   prepared=[x for x in rows if x[0]==2];direct=[x for x in rows if x[0]==0];replay=[x for x in rows if x[0]==1]
   assert [x[1]for x in prepared]==list(range(1,fn))and all(x[2:6]==[-1]*4 for x in prepared)
   assert [x[1:]for x in direct]==[x[1:]for x in replay]and [x[1]for x in direct]==list(range(1,fn))
  replay=by['REPLAY'];assert len(replay)==4*len(edges)
  for e,f,j,t,b in edges:assert sorted(x[3]for x in replay if x[1]==e)==[0,1,2,3]
  assert any(x[4]==4 and x[2]==lookup['positive-sink']for x in replay)and any(x[4]==0 and x[2]==lookup['zero-sink']for x in replay)
  assert all(x[4]==-1 for x in replay if ed[x[1]][0]==ed[x[1]][2]==sf)
 else:assert end[3]==268435456 and not any(by[t]for t in ['ARG','CAPTURE','CAPTUREPOST','REPLAY','COMPARE','BOUNDS'])
 return {'case':c,'status':'PASS','positive4':len(positive),'unknown0':len(zero),'preservesSelfEvents':len(selfskip),'actualSelfOPCALL':True,'freshAggregateReplay':c==1,'fullMCleanupReceipt':True,'ownedCells':50689,'scope':'thisactualfixtureonly;notuniversal'}

with tempfile.TemporaryDirectory(prefix='typed-vector-data-',dir=BASE)as td:
 root=Path(td).resolve();temp_roots.append(root);objects={}
 with tarfile.open(archive,'r:gz')as tar:
  for member in tar:
   assert member.isfile()and member.name.startswith('objects/')and len(member.name)==72 and member.size<=33554432
   data=tar.extractfile(member).read();h=member.name[8:];assert sha(data)==h and h not in objects;objects[h]=data
 assert len(objects)==m['objects']and sum(map(len,objects.values()))==m['uncompressedObjectBytes']
 for n,pin in m['paths'].items():
  rel=PurePosixPath(n);assert not rel.is_absolute()and'..'not in rel.parts;data=objects[pin['sha256']];assert len(data)==pin['bytes'];p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 W=root;D=W/'vector-shape-memo-vector-controls-v1-width';load=lambda p:json.loads(p.read_text())
 delta=load(D/'source-deltas.json');source=(D/'unity-vector-controls.kotoba').read_text();assert source.count(delta['insert'])==source.count(delta['mainNew'])==1
 rev=source.replace(delta['insert'],'',1).replace(delta['mainNew'],delta['mainOld'],1)
 for a,b in delta['renames'].items():assert rev.count('(defn- '+b+' ')==1;rev=rev.replace('(defn- '+b+' ','(defn- '+a+' ',1)
 assert rev==(W/'vector-typed-analysis-v8/unity-vector-analysis-on.kotoba').read_text()
 assert sha((D/'producer.bin').read_bytes())=='2a0d9a3b47dab57ca8b52532e7ce5c9cff9b189de1e62af564b9436646dd239b'
 assert sha((D/'kexe-loader').read_bytes())=='8fc787ca556773b6991b44f51e0d4fdec52cf93ef37673cb289eb726c98dff64'
 rows=load(D/'attempts.json');labels=['controls-compile','controls-extract','case-0','case-1','case-2','baseline-compile','baseline-extract'];assert len(rows)==7 and [r['label']for r in rows]==labels
 origin='/Users/junkawasaki/github/workspaces/codex/vector-shape-memo-vector-controls-v1-width';path=lambda n:origin+'/'+n
 suffixes=[['compile',path('unity-vector-controls.kotoba'),'--target','aarch64-macos','--output',path('controls.kseed')],['extract-native',path('controls.kseed'),'--symbol','main','--output',path('controls.bin')],['probe','0'],['probe','1'],['probe','2'],['compile',path('fixture.kotoba'),'--target','aarch64-macos','--output',path('baseline.kseed')],['extract-native',path('baseline.kseed'),'--symbol','bench','--output',path('baseline.bin')]]
 for i,r in enumerate(rows):
  image='controls.bin'if 2<=i<=4 else 'producer.bin';off=int((D/'controls.offset').read_text())if 2<=i<=4 else 0
  assert r['argv']==[path('kexe-loader'),path(image),str(off),'0','aarch64','35,37,38,39','--']+suffixes[i]and r['returncode']==0 and r['state']=='terminal'and r['index']==i+1
  assert r['caps']=={'seconds':1200 if 2<=i<=4 else 1800,'vectorItems':134217728}and(D/(r['label']+'.stderr')).read_bytes()==b''
  if i not in [2,3,4]:assert b':ok true'in(D/(r['label']+'.stdout')).read_bytes()
 for kind,sym,arity in [('controls','main',0),('baseline','bench',1)]:
  data=(D/(kind+'.bin')).read_bytes();head,payload=(D/(kind+'.kseed')).read_bytes().split(b'\n\n',1);lines=head.decode().splitlines();magic,n,ne=lines[0].split();assert magic=='KSEED1'and int(n)==len(data)and int(ne)==len(lines)-1 and payload==data
  exports=[(a,int(off),int(ar))for a,off,ar in [x.split()for x in lines[1:]]];match=[x for x in exports if x[0]==sym];assert len(match)==1 and match[0][1]==int((D/(kind+'.offset')).read_text())and match[0][2]==arity
 assert len((D/'baseline.bin').read_bytes())==624 and int((D/'baseline.offset').read_text())==424 and sha((D/'baseline.bin').read_bytes())=='c51adf3c8ed7c62c3479e42c9eca2592a763dd1aea15c19998a52c5e77716e5c'
 results=[validate((D/f'case-{c}.stdout').read_text(),c)for c in range(3)]
 records=parse((D/'case-1.stdout').read_text());replay=[x for t,x in records if t=='REPLAY'];assert [x for x in replay if x[1]==0]==[[3,0,3,k,-1]for k in range(4)]
 batches=[];buf=[]
 for t,x in records:
  if t=='BOUNDS':buf.append(x)
  if t=='COMPARE':batches.append((x[0],buf));buf=[]
 for f,rr in batches:
  fresh=[x for x in rr if x[0]==2];direct=[x for x in rr if x[0]==0];hit=[x for x in rr if x[0]==1];assert all(x[2:6]==[-1]*4 for x in fresh)and [x[1:]for x in direct]==[x[1:]for x in hit]
  if f==4:assert next(x for x in hit if x[1]==2)[2]==0
  if f==5:assert next(x for x in hit if x[1]==1)[2]==4 and next(x for x in hit if x[1]==3)[2]==4
 print(json.dumps({'status':'PASS_PORTABLE_TYPED_VECTOR_FIXED_FIXTURE_ONLY','actualLoaderCalls':7,'diagnosticBodies':3,'caseResults':results,'nativeByReplay':0,'sourceReverseV8Exact':True,'freshReplayEquality':True,'baseline624BOffset424CaptureOnly':True,'fourGenerationProof':'separate sibling packet','runtimePerformance':'UNQUALIFIED','universalMExternalArenaABI':'HOLD'}))
