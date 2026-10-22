"""Inert, bounded offline observer validator. No native invocation."""
import pathlib,json,re
D=pathlib.Path(__file__).resolve().parent
WIDTH={'SIR':4,'FREC':16,'CODE':1,'FIX':4,'LIT':4,'LITB':1,'LABEL':1,'EXP':4}
INT=re.compile(r'0|-?[1-9][0-9]*')
def parse(raw):
 assert type(raw)is bytes and len(raw)<=67108864
 phases={};active=None;calls=[];pending=None
 for line in raw.splitlines():
  if not line.startswith(b'MO '):continue
  tokens=line.decode('ascii').split(' ');assert all(tokens) and len(tokens)>=4
  assert INT.fullmatch(tokens[1]) and INT.fullmatch(tokens[3]);p=int(tokens[1]);tag=tokens[2];index=int(tokens[3]);vals=[]
  for v in tokens[4:]:assert INT.fullmatch(v);x=int(v);assert -(1<<63)<=x<(1<<63);vals.append(x)
  if tag=='CALL':
   assert active is None and p==0 and index in (0,1) and len(vals)==11
   if index==0:assert pending is None;pending=vals
   else:
    assert pending is not None and vals[:4]==pending[:4] and vals[4]>=pending[4] and vals[5]>=pending[5];calls.append({'before':pending,'after':vals});pending=None
  elif tag=='HEADER':
   assert p in (1,2,3,4) and p not in phases and active is None and index==0 and len(vals)==11
   phases[p]={'header':vals,**{k:[]for k in WIDTH}};active=p
  elif tag=='END':assert active==p and index==0 and not vals;active=None
  else:
   assert active==p and tag in WIDTH and len(vals)==WIDTH[tag];phases[p][tag].append([index]+vals)
 assert active is None and pending is None and set(phases)=={1,2,3,4}
 for p,s in phases.items():
  e,fn,sir,label,code,fix,lit,litb,cb,out,exp=s['header'];assert e==0 and 1<=fn<=128 and 1<=sir<=66016 and 1<=label<=65536 and 1<=code<=524288 and 1<=fix<=65536 and 1<=lit<=16384 and 0<=litb<=262144 and 1<=exp<=1024
  domains={'SIR':(1,sir),'FREC':(1,fn)}
  if p>=3:domains.update(CODE=(1,code),FIX=(1,fix),LIT=(1,lit),LITB=(0,litb),LABEL=(1,label),EXP=(1,exp))
  for tag,rows in ((k,s[k])for k in WIDTH):
   expected=list(range(*domains[tag])) if tag in domains else []
   assert [r[0]for r in rows]==expected
 return phases,calls

def validate(raw,workload,observerContainer,ordinaryONContainer,expectedONPin):
 phases,calls=parse(raw);packets=json.loads((D/'proposed-packets.json').read_bytes());pkt=next(p for p in packets if p['module']==workload)
 before=phases[1];after=phases[2];sir={r[0]:r[1:]for r in before['SIR']};fr={r[0]:r[1:]for r in before['FREC']}
 # Fixed actual-source contexts. No acceptance from printed installer status/counts.
 assert before['SIR']==pkt['input']['sir'][1:]
 # Pre-generation FF-CODE is zero; prior observer FREC may contain generated code offsets.
 expectedfr=[r.copy()for r in pkt['input']['frec'][1:]]
 for row in expectedfr:row[14]=0
 assert before['FREC']==expectedfr
 ns=before['header'][2];nf=before['header'][1];nl=before['header'][3];expected={k:v.copy()for k,v in sir.items()};expectedF={k:v.copy()for k,v in fr.items()};keys={};sites=[];cloneN=0
 for r in sorted(pkt['input']['requested'],key=lambda r:r['callSIR']):
  i=r['callSIR'];op,f,t,n=sir[i];assert op==13 and n==2
  pre=sir[i-1];assert pre[0]==3 and pre[1]==t+1 and pre[3]==0 and 1<=pre[2]<=31
  value=pre[2];key=(f,value);reused=key in keys
  if not reused:
   c=nf+cloneN;q=ns+cloneN*15;label=nl+cloneN;keys[key]=c
   ff=fr[f].copy();assert ff[2]==2 and ff[11]==0 and ff[3]==2 and ff[4]==1 and ff[5:7]==[1,1] and ff[14]==1
   start=ff[12];ff[12]=q;ff[13]=0;expectedF[c]=ff
   for k in range(15):
    row=sir[start+k].copy()
    if k in (0,14):row[1]=c
    elif k==2:row[1]=label
    elif k in (4,8):row=[3,1 if k==4 else 3,value,0]
    expected[q+k]=row
   cloneN+=1
  c=keys[key];expected[i][1]=c
  # Exact source owner, no workload name/FN hardcoded acceptance.
  owners=[f0 for f0,v in fr.items() if 0<v[12]<=i and v[12] in sir and sir[v[12]][:2]==[1,f0] and (end:=next((j for j in range(v[12]+1,ns)if sir[j][0]==2),0))>i and sir[end][1:]==[f0,0,0]];assert len(owners)==1
  sites.append({'sir':i,'owner':owners[0],'originalCallee':f,'clone':c,'value':value,'reuse':reused})
 assert after['SIR']==[[i]+expected[i]for i in sorted(expected)] and after['FREC']==[[i]+expectedF[i]for i in sorted(expectedF)]
 assert after['header'][1:4]==[nf+cloneN,ns+15*cloneN,nl+cloneN]
 for phase in (3,4):
  s=phases[phase];assert s['SIR']==after['SIR'] and s['header'][1:4]==after['header'][1:4]
  for row in s['FREC']:
   original=expectedF[row[0]];assert all(row[k+1]==v for k,v in enumerate(original)if k!=13)
 assert phases[4]['FIX']==phases[3]['FIX'] and phases[4]['LITB']==phases[3]['LITB']
 assert len(phases[4]['LIT'])==len(phases[3]['LIT'])
 cursor=((phases[4]['header'][4]-1)*4+7)&~7
 for old,new in zip(phases[3]['LIT'],phases[4]['LIT']):
  assert old[:3]==new[:3] and old[4]==new[4] and new[3]==cursor and 0<=new[1] and 0<=new[2] and new[1]+new[2]<=phases[4]['header'][7]
  cursor=(cursor+new[2]+7)&~7
 # Final emitted code is capture, not a permission to infer machine equivalence.
 final=phases[4];code={r[0]:r[1]for r in final['CODE']};offsets=sorted((r[14],r[0])for r in final['FREC']if r[14]>0);assert len({pc for pc,f in offsets})==len(offsets)
 spans=[]
 for j,(pc,f)in enumerate(offsets):
  end=offsets[j+1][0]if j+1<len(offsets)else final['header'][4]
  assert 1<=pc<end<=final['header'][4]
  words=[code[k]for k in range(pc,end)];spans.append({'fn':f,'codeStart':pc,'codeEnd':end,'codeWords':end-pc,'rawBLWords':sum((v&0xfc000000)==0x94000000 for v in words),'rawBLRWords':sum((v&0xfffffc1f)==0xd63f0000 for v in words),'rawSUBSPWords':sum((v&0xffc003ff)==0xd10003ff for v in words),'rawADDSPWords':sum((v&0xffc003ff)==0x910003ff for v in words),'possibleInlineDataNotClassified':True,'frameOpcodeCountsAreStaticOnly':True})
 # Source FX-BL26=4; target is FN. Bind callsite span by actual before/after generator records.
 joins=[]
 for site in sites:
  found=[r for r in calls if r['before'][0]==site['sir']and r['before'][1]==site['clone']];assert len(found)==1;c=found[0];assert c['before'][3]==2 and c['after'][6]==0
  fx=[r for r in phases[3]['FIX']if c['before'][5]<=r[0]<c['after'][5]and r[2]==4 and r[3]==site['clone']]
  joins.append({**site,'generatorCallSpan':c,'BLFixRows':fx,'directBLRegistered':bool(fx)})
 import hashlib
 a=pathlib.Path(observerContainer).read_bytes();b=pathlib.Path(ordinaryONContainer).read_bytes();assert len(b)==expectedONPin['bytes'] and hashlib.sha256(b).hexdigest()==expectedONPin['sha256'] and a==b
 header,payload=a.split(b'\n\n',1);lines=header.decode('ascii').splitlines();top=lines[0].split(' ');assert len(top)==3 and top[0]=='KSEED1' and int(top[1])==len(payload) and int(top[2])==len(lines)-1
 exports=[]
 for line in lines[1:]:
  name,pc,arity=line.split(' ');assert INT.fullmatch(pc) and INT.fullmatch(arity);pc=int(pc);arity=int(arity);assert 0<=pc<len(payload) and arity>=0;exports.append((name,pc,arity))
 assert len({e[0]for e in exports})==len(exports)
 assert [(r[2],r[3])for r in final['EXP']]==[(e[1],e[2])for e in exports]
 ffmap={r[0]:r[1:]for r in final['FREC']}
 for er in final['EXP']:
  assert er[4]==0 and er[1]in ffmap;ff=ffmap[er[1]];assert ff[11]==1 and er[2]==(ff[13]-1)*4 and er[3]==ff[3]
 assert {er[1]for er in final['EXP']}=={f for f,ff in ffmap.items()if ff[11]==1}
 assert final['header'][8]==len(payload)
 codeBytes=b''.join(code[k].to_bytes(4,'little',signed=False)for k in range(1,final['header'][4]));assert payload[:len(codeBytes)]==codeBytes
 fcode={r[0]:r[14]for r in final['FREC']}
 for join in joins:
  for fx in join['BLFixRows']:
   at=fx[1];target=fx[3];assert 1<=at<final['header'][4] and target in fcode and fcode[target]>0 and fx[4]==0
   displacement=fcode[target]-at;assert -(1<<25)<=displacement<(1<<25);assert code[at]==(0x94000000|(displacement&0x03ffffff))
 return {'status':'PASS_FIXED_ON_CLONE_CAPTURE_WHOLE_NONINSTRUMENTED_IDENTITY_ONLY','sites':joins,'cloneCount':cloneN,'appendedSIR':15*cloneN,'functionCodeSpans':spans,'performanceQualified':False,'fuelRuntimeProved':False}
