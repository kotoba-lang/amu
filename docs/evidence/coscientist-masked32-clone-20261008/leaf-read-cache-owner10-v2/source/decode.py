"""Bounded readonly owner/layout records. No instruction semantic or ABI qualification."""
import re
WIDTH={'HEADER':11,'SIR':4,'FREC':16,'CODE':1,'FIX':4,'LIT':4,'LITB':1,'EXP':4,'LABEL':1,'END':0}
def parse(raw,payload):
 assert type(raw)is bytes and len(raw)<=16777216
 phases={};pairs=[];pending=None;lp=[];reads=[];last=None
 for line in raw.decode('ascii').splitlines():
  if line.startswith('LO '):
   a=line.split();assert len(a)>=4;phase=int(a[1]);tag=a[2];idx=int(a[3]);assert phase in(3,4)and tag in WIDTH and len(a)==4+WIDTH[tag];values=list(map(int,a[4:]));assert all(-(1<<63)<=v<(1<<63)for v in values)
   d=phases.setdefault(phase,{k:{}for k in WIDTH});assert idx not in d[tag];d[tag][idx]=values
  elif line.startswith(('LA ','LG ','LF ','LS ')):
   a=line.split();tag=a[0];v=list(map(int,a[1:]));assert all(-(1<<63)<=x<(1<<63)for x in v)
   if tag=='LA':
    assert len(v)==9 and v[0]in(0,1)and v[1]>0 and 0<v[2]<v[6]and v[4]==0
    if v[0]==0:assert pending is None;pending={'before':v,'after':None,'LG':{0:{},1:{}},'LF':{0:{},1:{}},'LS':{0:{},1:{}}}
    else:assert pending is not None and pending['after']is None and v[1:4]==pending['before'][1:4];pending['after']=v
    last=v[0]
   else:
    assert len(v)==5 and pending is not None and v[:3]==[last,*pending['before'][1:3]];k=v[3];assert k not in pending[tag][last]and k in(range(1,8)if tag=='LS'else range(16));pending[tag][last][k]=v[4]
    if tag=='LS'and last==1 and k==7:
     for t in('LG','LF','LS'):
      for phase in(0,1):assert sorted(pending[t][phase])==list(range(1,8)if t=='LS'else range(16))
     pairs.append(pending);pending=None
  elif line.startswith('LP '):
   v=list(map(int,line.split()[1:]));assert len(v)==11 and v[-1]==0 and 0<v[2]<=v[3];lp.append(v)
  elif line.startswith('LR '):
   v=list(map(int,line.split()[1:]));assert len(v)==6 and v[-1]==0 and 0<v[3]<=v[4];reads.append(v)
 assert pending is None and set(phases)=={3,4} and len(pairs)==len(lp)
 for phase,d in phases.items():
  assert set(d['HEADER'])=={0}and set(d['END'])=={0};h=d['HEADER'][0];assert h[0]==0 and 0<h[1]<=128 and 0<h[2]<=66016 and 0<h[3]<=65536
  for tag,n,start in [('SIR',h[2],1),('FREC',h[1],1),('LABEL',h[3],1),('CODE',h[4],1),('FIX',h[5],1),('LIT',h[6],1),('LITB',h[7],0),('EXP',h[10],1)]:assert sorted(d[tag])==list(range(start,n))
 d=phases[4];h=d['HEADER'][0];assert 4*(h[4]-1)<=len(payload)
 for pc,z in d['CODE'].items():assert 0<=z[0]<2**32 and payload[4*(pc-1):4*pc]==z[0].to_bytes(4,'little')
 owners=[]
 for pair,pro in zip(pairs,lp):
  before=pair['before'];after=pair['after'];i,f,np=before[1:4];assert pro[:2]==[i,f]and pro[2]==after[7];sir=phases[3]['SIR'];ff=phases[3]['FREC'][f];assert ff[12]==i and sir[i]==[1,f,np,ff[10]]
  ends=[p for p in range(i+1,h[2])if sir[p][0]in(1,2)];assert ends and sir[ends[0]]==[2,f,0,0];end=ends[0]
  for stage in(0,1):assert all(pair['LF'][stage][k]==ff[k]for k in range(16)if k!=13) # FF-CODE is assigned after lc-assign
  bg=pair['LG'][0];ag=pair['LG'][1];accepted=bg[0]==1 and bg[2]==bg[3]==bg[8]==0 and ag[2]==3 and 0<ag[3]<=160 and ag[8]==3 and 0<ag[15]<=np
  if accepted:
   assert pro[4:8]==[ag[3],3,3,1]and pro[9]==1;assert ag[3]%16==0 and ag[3]==((8*(ag[4]+ag[5]+2)+15)//16)*16+32
   sites=[v for v in reads if i<v[0]<end];assert len(sites)>=2 and all(v[2]==3 and sir[v[0]][:1]==[14]and sir[v[0]][1]==176 for v in sites)
   assert d['FREC'][f][13]==pro[2];owners.append({'fn':f,'SIRstart':i,'SIRend':end,'slot':ag[15],'frame':ag[3],'nsv':3,'mode':3,'sreg':pair['LS'][1],'prologueCodeSpan':[pro[2],pro[3]],'readCodeSpans':sites,'physicalSaveRestoreInitQualified':False})
 return {'status':'PASS_READONLY_LC_OWNER_LAYOUT_RECORDS_ONLY','owners':owners,'eligibleOwners':len(owners),'assignmentPairs':len(pairs),'readEvents':len(reads),'phases':phases,'emitterByteIdentityRequiredSeparately':True,'runtimeABITrapFuelQualified':False}
