"""Offline raw validator; import inert. No compiler/guest/solver invocation."""
import re,struct
def need(x,m):
 if not x:raise AssertionError(m)
def check_receipt(result):
 rows=result['allRawRecords'];site=result['eligibleSite'];reader_fn=site[2]
 need(result['readerFN']==reader_fn,'receipt reader matches eligible callee')
 fields=[r for r in rows['FF'] if r[0]==0 and r[1]==reader_fn]
 need(len(fields)==16,'receipt complete reader FN')
 start=next(r[3] for r in fields if r[2]==12)
 sir={r[1]:r[2:] for r in rows['FSIR'] if r[0]==0}
 need(sir[start]==[1,reader_fn,1,1],'receipt reader origin')
 end=next(j for j in sorted(sir) if j>start and sir[j]==[2,reader_fn,0,0])
 need(result['readerSIR']==[start,end],'receipt reader range matches typed ownership')
 need([r for r in rows['TCCALL'] if r[5]>0]==[site],'receipt unique eligible site')
 return result

def verify(raw,payload,exports,source):
 sizes={'FH':7,'FSIR':6,'FF':4,'FNODE':5,'FSYM':5,'FTOK':5,'FREFUSE':None,
        'FOUT':7,'FCODE':2,'FLABEL':2,'FFIX':5,'FLIT':5,'FLITB':2,'FEXP':5,
        'FEND':2,'TCG':4,'TCCALL':14}
 rows={k:[] for k in sizes}
 for line in raw.splitlines():
  parts=line.split(b' ');tag=parts[0].decode('ascii',errors='ignore')
  if tag not in rows:continue
  need(sizes[tag] is not None and len(parts)==sizes[tag]+1,'refusal/field count '+tag)
  need(all(re.fullmatch(rb'-?[0-9]{1,20}',x) for x in parts[1:]),'integer field '+tag)
  vals=list(map(int,parts[1:]));need(all(-(1<<63)<=v<(1<<64) for v in vals),'carrier bounds')
  rows[tag].append(vals)
 need(len(rows['FH'])==2 and rows['FH'][0][0:2]==[0,0] and rows['FH'][1][0:2]==[1,0],'two normal typed phases')
 need(rows['FH'][0][2:]==rows['FH'][1][2:],'readonly typed header')
 _,_,sn,fn,nn,yn,tn=rows['FH'][0]
 need(1<sn<=1024 and 1<fn<=32 and 0<nn<=65536 and 0<yn<=65536 and 0<tn<=262144,'typed cap')
 typed=[];functions=[]
 for phase in [0,1]:
  ss=[r[1:] for r in rows['FSIR'] if r[0]==phase]
  need(len(ss)==sn-1 and [r[0] for r in ss]==list(range(1,sn)),'complete ordered SIR')
  typed.append(ss)
  ff=[r[1:] for r in rows['FF'] if r[0]==phase]
  need(len(ff)==16*(fn-1) and [(r[0],r[1]) for r in ff]==[(f,k) for f in range(1,fn) for k in range(16)],'complete FN fields')
  functions.append({f:[r[2] for r in ff if r[0]==f] for f in range(1,fn)})
 need(typed[0]==typed[1],'SIR unchanged by observer/emission')
 for f in range(1,fn):
  need(all(functions[0][f][k]==functions[1][f][k] for k in range(16) if k!=13),'only FF-CODE changes at layout')
 node_maps=[];sym_maps=[];token_maps=[]
 for phase in [0,1]:
  nodes={};symbols={};tokens={}
  for tag,index,kcount,dest in [('FNODE',1,8,nodes),('FSYM',0,8,symbols)]:
   rr=[r for r in rows[tag] if r[0]==phase]
   expected=[(phase,f,functions[phase][f][index],k) for f in range(1,fn) for k in range(kcount)]
   need([tuple(r[:4]) for r in rr]==expected,'complete ordered '+tag)
   for f in range(1,fn):dest[f]=[r[4] for r in rr if r[1]==f]
  rr=[r for r in rows['FTOK'] if r[0]==phase]
  need([tuple(r[:4]) for r in rr]==[(phase,f,nodes[f][3],k) for f in range(1,fn) for k in range(4)],'complete ordered FTOK')
  for f in range(1,fn):
   ff=functions[phase][f];node=nodes[f];sym=symbols[f];tok=[r[4] for r in rr if r[1]==f];tokens[f]=tok
   need(0<ff[0]<yn and 0<ff[1]<nn and 0<=node[1]<nn and 0<=node[2]<nn
        and 0<node[3]<tn and 0<=node[5]<yn,'typed node/symbol/token refs')
   need(sym[4]==f and 0<=sym[0]<sym[1]<=len(source),'declared symbol owner/span')
   need(1<=tok[0]<=12 and 0<=tok[1]<=tok[2]<=len(source),'token kind/span')
  node_maps.append(nodes);sym_maps.append(symbols);token_maps.append(tokens)
 need(node_maps[0]==node_maps[1] and sym_maps[0]==sym_maps[1] and token_maps[0]==token_maps[1],'readonly node/symbol/token inventories')
 sir={r[0]:r[1:] for r in typed[0]};owners={};owner=0
 for j in range(1,sn):
  op,a,b,c=sir[j]
  if op==1:need(owner==0 and a in functions[0],'natural FN ownership');owner=a
  owners[j]=owner
  if op==2:need(owner==a,'matching END');owner=0
 need(owner==0,'closed whole SIR')
 calls=rows['TCCALL'];need(len({r[0] for r in calls})==len(calls),'one observer per call')
 need([r[0] for r in calls]==[j for j in range(1,sn) if sir[j][0]==13],'one TCCALL per every actual OP-CALL')
 need([(r[0],r[1],r[2]) for r in rows['TCG']]==[(r[0],phase,k) for r in calls for phase in [0,1] for k in range(38)],'complete TCG coverage; no extra sites')
 for r in calls:
  i,owner,f,t,n,base,start,end,leaf,frame,height,ctx,afterctx,err=r
  need(i in sir and sir[i]==[13,f,t,n] and owners[i]==owner,'actual typed caller edge')
  need(err==0 and end>=start and start>0,'actual emission span')
  gs=[r for r in rows['TCG'] if r[0]==i]
  need([(r[1],r[2]) for r in gs]==[(phase,k) for phase in [0,1] for k in range(38)],'complete 38-cell context observations')
 eligible=[r for r in calls if r[5]>0];need(len(eligible)==1,'exact one current original structural site')
 i,owner,reader_fn,t,n,base,*rest=eligible[0]
 need(n==1 and t==0 and rest[2]==0 and rest[3]>0,'natural framed nonleaf current edge')
 need(sir[i-4]==[3,t+1,255,0] and sir[i-3]==[6,5,t,0],'exact current mask')
 slot=sir[i-1][2];need(sir[i-2]==[5,slot,t,0] and sir[i-1]==[4,t,slot,0],'exact current store/read dominance')
 ff=functions[0][reader_fn];p=ff[12];need(ff[3]==1 and ff[4]==1 and ff[5]==1 and ff[10]==1 and ff[15]==2,'exact typed reader')
 need(sir[p]==[1,reader_fn,1,1] and sir[p+1]==[18,0,0,0],'original entry fuel')
 end=next(j for j in range(p+1,sn) if sir[j]==[2,reader_fn,0,0]);need(end-p<=258,'bounded reader')
 need([j for j in range(p,end) if sir[j][0]==18]==[p+1],'no path fuel')
 tabs=[sir[j] for j in range(p,end) if sir[j][0]==21]
 need(tabs==[[21,0,base+k,16] for k in range(16)],'exact ordered immutable slices')
 labels={sir[j][1]:j for j in range(p,end) if sir[j][0]==9}
 for x in range(256):
  pc=p+1;tmp={};fuel=0;reads=[]
  for _ in range(256):
   op,a,b,c=sir[pc]
   if op==18:fuel+=1
   elif op==9:pass
   elif op==4:need(b==1,'sole parameter');tmp[a]=x
   elif op==3:tmp[a]=b
   elif op==7:need(a==2,'signed LT only');tmp[b]=int(tmp[b]<tmp[b+1])
   elif op==6:need(a==2,'pure subtract only');tmp[b]=(tmp[b]-tmp[b+1])&((1<<64)-1)
   elif op==11:
    if tmp[a]==0:pc=labels[b];continue
   elif op==10:pc=labels[a];continue
   elif op==21:need(0<=tmp[a]<c,'original bound safe');reads.append([b,tmp[a]])
   elif op==19:break
   else:raise AssertionError('unclaimed original reader opcode')
   pc+=1
  else:raise AssertionError('path work cap')
  need(fuel==1 and reads==[[base+x//16,x%16]],'finite complete original reader mapping')
 need(len(rows['FOUT'])==1 and rows['FEND']==[[1,0]],'complete success footer')
 cn,cb,ln,xn,litn,litbn,en=rows['FOUT'][0]
 need(0<cn<=8192 and 0<ln<=512 and 0<xn<=512 and 0<litn<=64 and 0<litbn<=16384 and 0<en<=16 and cb==len(payload),'output caps/whole payload')
 need(rows['FCODE']==[[k,w] for k,w in enumerate([r[1] for r in rows['FCODE']])] and len(rows['FCODE'])==cn,'complete code words')
 need(all(0<=r[1]<(1<<32) for r in rows['FCODE']),'code word width')
 code=b''.join(struct.pack('<I',r[1]) for r in rows['FCODE'][1:]);need(payload[:len(code)]==code,'all actual emitted CODE bytes')
 need([r[0] for r in rows['FLIT']]==list(range(1,litn)) and [r[0] for r in rows['FLITB']]==list(range(1,litbn)),'full LIT/LITB capture')
 lit={r[0]:r[1:] for r in rows['FLIT']};lb={r[0]:r[1] for r in rows['FLITB']}
 need([r[0] for r in rows['FLABEL']]==list(range(1,ln)),'complete ordered FLABEL')
 labels_code={r[0]:r[1] for r in rows['FLABEL']}
 need(all(0<r[1]<=cn for r in rows['FLABEL']),'label code bounds')
 need([r[0] for r in rows['FFIX']]==list(range(1,xn)),'complete ordered FFIX')
 codewords={r[0]:r[1] for r in rows['FCODE']}
 def signed(v,width):return v-(1<<width) if v&(1<<(width-1)) else v
 for idx,at,kind,target,aux in rows['FFIX']:
  need(0<at<cn and kind in [1,2,3,4,5] and aux in [0,1],'fixed CRC fixup domain')
  word=codewords[at]
  if kind==5:
   need(target in lit and aux==0 and at+1<cn,'literal fixup target')
   second=codewords[at+1]
   need((word&0xffe00000)==0xd2800000 and (second&0xffe00000)==0xf2a00000
        and (word&31)==(second&31),'literal MOVZ/MOVK fields')
   need(((word>>5)&65535)+(((second>>5)&65535)<<16)==lit[target][2],'literal relocation value')
  else:
   if kind==4:
    need(target in functions[1] and (word&0xfc000000) in [0x14000000,0x94000000],'B or BL resolved function')
    to=functions[1][target][13]
    if aux:
     need((word&0xfc000000)==0x14000000 and codewords.get(to)==0xd2800005,'private checked entry discriminator');to+=1
   else:
    need(target in labels_code and aux==0,'label fixup target');to=labels_code[target]
   if kind in [1,4]:
    if kind==1:need((word&0xfc000000)==0x14000000,'B opcode')
    actual=at+signed(word&0x03ffffff,26)
   else:
    need((word&0xff000010)==0x54000000 if kind==2 else (word&0x7e000000)==0x34000000,'conditional branch opcode')
    actual=at+signed((word>>5)&0x7ffff,19)
   need(actual==to,'every actual branch/call relocation')
 need([r[0] for r in rows['FEXP']]==list(range(1,en)),'complete ordered FEXP')
 exported=[f for f in range(1,fn) if functions[1][f][11]==1]
 need([r[1] for r in rows['FEXP']]==exported and len(exports)==len(exported),'typed export ownership/count')
 physical_exports=[]
 for idx,export_fn,off,arity,spare in rows['FEXP']:
  ff=functions[1][export_fn];sym=sym_maps[1][export_fn]
  need(spare==0 and off==4*(ff[13]-1) and arity==ff[3],'export/FN/code relation')
  physical_exports.append((source[sym[0]:sym[1]].decode('utf-8'),off,arity))
 need(physical_exports==exports,'every source symbol/export/payload row')
 for k in range(16):
  b,length,pool,tok=lit[base+k]
  need(length==128 and pool==lit[base][2]+128*k,'actual contiguous pooled slices')
  need(all(j in lb and 0<=lb[j]<=255 for j in range(b,b+128)),'captured immutable source data')
  need(payload[pool:pool+128]==bytes(lb[j] for j in range(b,b+128)),'actual whole immutable slice bytes')
 return check_receipt({'status':'CURRENT_SOURCE_BINDING_AND_READONLY_OUTPUT_IDENTITY_ONLY','eligibleSite':eligible[0],
         'readerFN':reader_fn,'readerSIR':[p,end],'finitePaths':256,'wholeCodeWords':cn-1,
         'literalBase':base,'pooledTableBytes':2048,'allRawRecords':rows,
         'TCEmitterExecuted':False,'guestRuntimeQualified':False,'OSStackLimitProof':False})

# New bounded emitted gate. The original complete current typed validator above
# remains byte-for-byte before this extension; it is not runtime qualification.
verify_binding=verify

def emission_certificate(rows,binding,baseline):
 site=binding['eligibleSite'];i,owner,f,t,n,base,start,end,*_=site
 need(i==220 and owner==3 and f==binding['readerFN']==1 and t==0 and n==1 and base==1,'exact audited current structural edge')
 rr=rows['TCEMIT'];need(len(rr)==1,'exact one selected TC emitter, not admission alone')
 e=rr[0];need(len(e)==14,'TCEMIT fields')
 ei,ef,et,eb,domain,cs,ce,fb,fa,ub,ua,sb,sa,err=e
 need([ei,ef,et,eb,domain,cs,ce]==[i,f,t,base,256,start,end],'selected emitter/call origin and span')
 need(err==0 and ce-cs==13 and ce-cs<=64 and fa==fb+1 and ua==ub+ce-cs<=4096 and sa==sb+1<=256,'committed finite TC transaction')
 cw=dict(rows['FCODE']);span=[cw[k]for k in range(cs,ce)]
 tail=span[1:12]
 need(span[0]==0xaa1903e0 and span[12]==0xaa0003e9,'exact original local7(x25) input capture and temp0(x9) result publication')
 gs=[r for r in binding['allRawRecords']['TCG'] if r[0]==i]
 oldgs=[r for r in baseline['allRawRecords']['TCG'] if r[0]==i]
 need(gs==oldgs,'all38 caller descriptors before/after equal original generic edge')
 exact={0:0xf94004e8,1:0xf1000508,2:0x54000062,3:0xf90004ff,4:0xd4200000,
        5:0xf940c0f1,6:0x8b000e31,9:0xf8706a20,10:0xf90004e8}
 need(all(tail[k]==v for k,v in exact.items()),'exact original charge/failure-zero/trap/table address/read/fuel publication words')
 need(tail[7]&0xffe0001f==0xd2800010 and tail[8]&0xffe0001f==0xf2a00010,'fixed x16 literal address materialization')
 reloc=[r for r in rows['FFIX']if cs<=r[1]<ce]
 need(len(reloc)==1 and reloc[0][1:]==[cs+8,5,base,0] and reloc[0][0]==fb,'one original literal fixup, no callee branch')
 need(not any(w&0xfc000000 in [0x14000000,0x94000000] or w&0xfffffc1f==0xd63f0000 for w in span),'no B/BL/BLR in collapsed physical edge')
 need(not any((w&0xff000010)==0x54000000 for w in span[:1]),'no reader decision prefix')
 # Original first reader remains a callable generic definition. Its pool
 # addresses move with layout; only the relocated MOVZ/MOVK immediates differ.
 def reader_words(q):
  z=q['allRawRecords'];fn=q['readerFN'];ff={r[1]:{}for r in z['FF']if r[0]==1}
  for phase,f,k,v in z['FF']:
   if phase==1:ff[f][k]=v
  lo=ff[fn][13];hi=min(v[13]for f,v in ff.items()if v[13]>lo)
  wc=dict(z['FCODE']);out=[wc[j]for j in range(lo,hi)]
  for idx,at,kind,target,aux in z['FFIX']:
   if lo<=at<hi and kind==5:
    need(at+1<hi,'reader literal fixup inside definition')
    out[at-lo]&=~0x1fffe0;out[at+1-lo]&=~0x1fffe0
  return out
 need(reader_words(binding)==reader_words(baseline),'entire original generic reader physical body unchanged except literal address relocation')
 need(binding['readerSIR']==baseline['readerSIR'] and binding['literalBase']==baseline['literalBase'],'same reader origin')
 before=[[r[1:]for r in binding['allRawRecords']['FSIR']if r[0]==phase]for phase in [0,1]]
 old=[[r[1:]for r in baseline['allRawRecords']['FSIR']if r[0]==phase]for phase in [0,1]]
 need(before==old,'all original typed SIR identical to accepted OFF lineage')
 return {'selectedSite':i,'readerFN':f,'callerFN':owner,'spanWords':ce-cs,'fixedTailWords':tail,
         'domain':256,'pooledTableBytes':2048,'entryFuelCharges':1,'calleeBranches':0,
         'genericReaderPreservedWithRelocations':True,'TCEmitterExecuted':True,
         'guestRuntimeQualified':False,'OSStackLimitProof':False}

def verify(raw,payload,exports,source,baseline):
 binding=verify_binding(raw,payload,exports,source)
 tce=[]
 for line in raw.splitlines():
  if not line.startswith(b'TCEMIT'):continue
  fields=line.split(b' ');need(fields[0]==b'TCEMIT'and len(fields)==15,'TCEMIT exact tag/field count')
  need(all(re.fullmatch(rb'-?[0-9]{1,20}',s)for s in fields[1:]),'TCEMIT finite integer')
  vals=list(map(int,fields[1:]));need(all(-(1<<63)<=v<(1<<64)for v in vals),'TCEMIT carrier bounds');tce.append(vals)
 rows=dict(binding['allRawRecords']);rows['TCEMIT']=tce
 certificate=emission_certificate(rows,binding,baseline)
 binding.update(status='CURRENT_ORIGINAL_TC_EMISSION_AND_OBSERVER_ARTIFACT_IDENTITY_ONLY',TCEmitterExecuted=True,
                actualEmission=certificate,emitterRecords=tce)
 return binding
