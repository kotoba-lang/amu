from pathlib import Path
import json,hashlib,re,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-decision-collapse-tc-emitted-build8-source-v1-20261008';R=W/'crc-table-emitted13-finite-semantics-20261009-independent';H=lambda b:hashlib.sha256(b).hexdigest();L=lambda p:json.loads(Path(p).read_bytes());M=(1<<64)-1
EP=W/'crc-table-decision-collapse-tc-saved-emission-actual-review-independent-20261008/report.json';XP=W/'crc-table-decision-collapse-tc-remaining-extract1-v2-actual-review-independent-20261009/report.json';ep=L(EP);xp=L(XP);assert H(EP.read_bytes())=='98416905a0b6afad3a7cd04e1e73d50c04e10b9f667aac70a710f3271801c693';assert H(XP.read_bytes())=='f74651159f7339cc591c8c28575605a87ffd80df6922824e16d24e12684e7056';p=Path(xp['extractedNative']['path']);payload=p.read_bytes();assert len(payload)==3680 and H(payload)=='5187d8338730957bf4611f294117c811099af65c9d1117492dd57430e8fa8999'
raw=(D/'run-outputs/observed-on-input-compile.stdout').read_bytes();rows={}
for line in raw.splitlines():
 z=line.split();tag=z[0].decode()
 if tag in ['FCODE','FSIR','FLIT','FLITB','FFIX','TCG','TCEMIT']:rows.setdefault(tag,[]).append(list(map(int,z[1:])))
emit=rows['TCEMIT'];assert emit==[[220,1,0,1,256,244,257,49,50,10,23,1,2,0]];cs,ce=emit[0][5:7];span=list(struct.unpack_from('<13I',payload,(cs-1)*4));cw=dict(rows['FCODE']);assert span==[cw[i]for i in range(cs,ce)];fix=[z for z in rows['FFIX']if cs<=z[1]<ce];assert fix==[[49,252,5,1,0]]
source=(D/'original-input.kotoba').read_text();tables=[list(map(int,g.split()))for g in re.findall(r'\(vector-at \[([0-9 ]+)\]',source)];original=[x for v in tables for x in v];assert len(original)==256
lit={z[0]:z[1:]for z in rows['FLIT']};litbytes=dict(rows['FLITB']);pool=lit[1][2];assert pool==1632
for k in range(16):
 at,length,offset,token=lit[k+1];assert length==128 and offset==pool+128*k and payload[offset:offset+128]==bytes(litbytes[j]for j in range(at,at+128));assert list(struct.unpack_from('<16Q',payload,offset))==tables[k]
# Independent bounded original typed reader interpreter, not generated native.
sir={z[1]:z[2:]for z in rows['FSIR']if z[0]==0};labels={a:i for i,(op,a,b,c)in sir.items()if op==9};
def typed(x,fuel):
 assert type(x)is int and 0<=x<256 and fuel in [0,1,2];pc=2;tmp={};debits=0;read=[]
 for steps in range(256):
  op,a,b,c=sir[pc]
  if op==18:
   if fuel==0:return {'trap':'fuel-exhaustion','fuel':0,'value':None,'reads':[]}
   fuel-=1;debits+=1
  elif op==9:pass
  elif op==4:assert b==1;tmp[a]=x
  elif op==3:tmp[a]=b
  elif op==7:assert a==2;tmp[b]=int(tmp[b]<tmp[b+1])
  elif op==6:assert a==2;tmp[b]=(tmp[b]-tmp[b+1])&M
  elif op==11:
   if tmp[a]==0:pc=labels[b];continue
  elif op==10:pc=labels[a];continue
  elif op==21:assert 0<=tmp[a]<c==16;read.append((b,tmp[a]));tmp[a]=tables[b-1][tmp[a]]
  elif op==19:assert debits==1 and read==[(1+x//16,x%16)];return {'trap':None,'fuel':fuel,'value':tmp[a],'reads':read}
  else:raise AssertionError('unsupported typed opcode')
  pc+=1
 raise AssertionError('typed path cap')
def decode(w):
 rd=w&31;rn=(w>>5)&31;rm=(w>>16)&31
 if w&0xffe0ffe0==0xaa0003e0:return ['MOV64',rd,rm]
 if w&0xffc00000 in [0xf9400000,0xf9000000]:return ['LDR64'if w&0xffc00000==0xf9400000 else'STR64',rd,rn,((w>>10)&4095)*8]
 if w&0xffc00000==0xf1000000:return ['SUBS64',rd,rn,(w>>10)&4095]
 if w&0xff000010==0x54000000:
  off=(w>>5)&0x7ffff;off=off-(1<<19)if off&(1<<18)else off;return ['B.COND',w&15,off]
 if w&0xffe0001f==0xd4200000:return ['BRK',(w>>5)&65535]
 if w&0xff200000==0x8b000000:return ['ADD64.LSL',rd,rn,rm,(w>>10)&63]
 if w&0xff800000 in [0xd2800000,0xf2800000]:return ['MOVZ64'if w&0xff800000==0xd2800000 else'MOVK64',rd,(w>>5)&65535,((w>>21)&3)*16]
 if w&0xffe00c00==0xf8600800:
  option=(w>>13)&7;scaled=(w>>12)&1;assert option==3 and scaled==0,'exact UXTX unshifted64';return ['LDR64.REG',rd,rn,rm]
 raise AssertionError('unsupported/changed instruction class')
def machine(words,x,fuel):
 assert type(x)is int and 0<=x<256 and fuel in [0,1,2],'finite typed precondition'
 regs=[(0x123456789abc0000+i*0x111)&M for i in range(31)];ctx=0x200000;code=0x100000;regs[7]=ctx;regs[24]=x;before=regs.copy();mem={ctx+8:fuel,ctx+384:code};reads=[];writes=[];writtenRegs=set();flags=None;pc=0;trap=None;trace=[]
 def get(r):return 0 if r==31 else regs[r]
 def put(r,v):
  if r!=31:regs[r]=v&M;writtenRegs.add(r)
 def read(addr):
  reads.append(addr)
  if addr in mem:return mem[addr]
  assert code+pool<=addr<=code+pool+2040 and addr%8==0,'read confined actual table payload'
  return struct.unpack_from('<Q',payload,addr-code)[0]
 for steps in range(32):
  if pc==len(words):break
  assert 0<=pc<len(words);op=decode(words[pc]);trace.append(pc);nextpc=pc+1
  if op[0]=='MOV64':put(op[1],get(op[2]))
  elif op[0]=='LDR64':put(op[1],read((get(op[2])+op[3])&M))
  elif op[0]=='STR64':addr=(get(op[2])+op[3])&M;assert addr==ctx+8,'sole contextfuel write';mem[addr]=get(op[1]);writes.append((addr,mem[addr]))
  elif op[0]=='SUBS64':
   a=get(op[2]);b=op[3];value=(a-b)&M;flags={'N':value>>63,'Z':int(value==0),'C':int(a>=b),'V':int(bool(((a^b)&(a^value))>>63))};put(op[1],value)
  elif op[0]=='B.COND':assert op[1]==2,'HS carry condition';assert flags is not None;nextpc=pc+op[2]if flags['C']else pc+1
  elif op[0]=='BRK':assert op[1]==0;trap='BRK0';break
  elif op[0]=='ADD64.LSL':put(op[1],get(op[2])+(get(op[3])<<op[4]))
  elif op[0]=='MOVZ64':put(op[1],op[2]<<op[3])
  elif op[0]=='MOVK64':put(op[1],(get(op[1])&~(65535<<op[3]))|(op[2]<<op[3]))
  elif op[0]=='LDR64.REG':put(op[1],read((get(op[2])+get(op[3]))&M))
  else:raise AssertionError('decoder/model mismatch')
  pc=nextpc
 else:raise AssertionError('instruction work cap')
 return {'trap':trap,'fuel':mem[ctx+8],'value':None if trap else regs[9],'registers':regs,'before':before,'writtenRegs':sorted(writtenRegs),'reads':reads,'writes':writes,'flags':flags,'trace':trace,'ctx':ctx,'code':code}
def compare(words,x,fuel):
 a=typed(x,fuel);b=machine(words,x,fuel);assert (b['trap']is not None)==(a['trap']is not None)and b['fuel']==a['fuel']and b['value']==a['value'];assert all(b['registers'][k]==b['before'][k]for k in range(31)if k not in [0,8,9,16,17]);assert b['writes']==[(b['ctx']+8,max(0,fuel-1))]
 if fuel:
  assert b['registers'][0]==original[x]and b['registers'][8]==fuel-1 and b['registers'][16]==pool and b['registers'][17]==b['code']+x*8;assert b['reads']==[b['ctx']+8,b['ctx']+384,b['code']+pool+x*8];assert b['trace']==[0,1,2,3,6,7,8,9,10,11,12]
 else:assert b['reads']==[b['ctx']+8]and b['trace']==[0,1,2,3,4,5]and b['registers'][8]==M;assert all(b['registers'][r]==b['before'][r]for r in [9,16,17])
 assert b['flags']=={'N':int(fuel==0),'Z':int(fuel==1),'C':int(fuel>=1),'V':0}
 return b
results=[]
for fuel in [0,1,2]:
 for x in range(256):compare(span,x,fuel)
 results.append({'fuel':fuel,'inputs':256,'trap':fuel==0,'remainingFuel':max(fuel-1,0),'successValueMatchesAllTypedPaths':fuel>0})
mutations=[('wrongX25capture',0,0xaa1903e0),('wrongFuelCell',1,0xf94000e8),('charge2',2,0xf1000908),('wrongBranchDisplacement',3,0x54000042),('wrongZeroStoreValue',4,0xf90004e8),('wrongCodeBaseCell',6,0xf940bcf1),('stride4',7,0x8b000a31),('literalOffsetPlus8',8,span[8]+(8<<5)),('wrongResultX8',12,0xaa0003e8),('narrowLoadClass',10,0xb8706a20)]
refusals=[]
for name,idx,w in mutations:
 words=span.copy();words[idx]=w
 try:
  for f in [0,1,2]:
   for x in range(256):compare(words,x,f)
 except (AssertionError,KeyError,IndexError):refusals.append(name)
 else:raise AssertionError('mutation undetected:'+name)
for x in [-1,256,1<<63]:
 try:machine(span,x,1)
 except AssertionError:refusals.append('outOfPremiseInput:'+str(x))
 else:raise AssertionError('outofdomain accepted')
# Source premises; no general ABI claim.
gen=(D/'41-a64gen-candidate.kotoba').read_text();assert '(def gn-a-sreg 16)'in gen and '(dec (gn-g M (+ gn-a-sreg s)))'in gen;pre={z[2]:z[3]for z in rows['TCG']if z[0:2]==[220,0]};assert pre[0]==0 and pre[3]==176 and pre[7]==1 and pre[24]==3 and pre[31]==7 and pre[23]==25
enc=Path('/Users/junkawasaki/github/wt/amu-seed17/seed/40-a64enc.kotoba');ns=Path('/Users/junkawasaki/github/wt/amu-seed17/seed/00-ns.kotoba');assert '(def CTX-FUEL 8)'in ns.read_text()and '(def CTX-CODE-BASE 384)'in ns.read_text()
q={'status':'PASS_FINITE_SAVED_AARCH64_INTEGER_TABLE_SUBSTITUTION_MODEL_ONLY','independent':True,'priorImplementationAuthorship':False,'acceptedEmissionProofSHA256':H(EP.read_bytes()),'acceptedExtractionProofSHA256':H(XP.read_bytes()),'extractedNative':xp['extractedNative'],'rawSHA256':H(raw),'selectedSite':220,'spanCODE':[244,257],'wordsHex':[f'{w:08x}'for w in span],'decoded':[decode(w)for w in span],'literalFixup':fix[0],'literalPoolOffset':pool,'originalTypedReaderFN':1,'originalTypedReaderRange':[1,174],'typedPathsCompared':256,'instructionInputFuelCases':768,'cases':results,'mutatedInstructionRefusals':refusals[:10],'outOfPremiseInputRefusals':refusals[10:],'allowedClobbersDerivedFromSelectedSource':{'integerRegisters':[0,8,9,16,17],'NZCV':True,'soleMemoryWrite':'context X7 +8 fuel','source':'Selected retained nonleaf caller frame176; temp0LOCALslot7 rawmap25->X24, currentX7contextvalid. Source documents X0/X8 free, X16/X17 scratch, gn-take publishes temp0X9; gn-save 0,t witht0 has no earlier live temps.','preserved':'All other X registers including X7/X24, SP and instruction model memory outside fuel; no floating/vector instructions are present.'},'trapObservation':'Fuel0: LDRfuel,SUBS1 carry0,zero publication then BRK0; no table/codebase read or result publication. Machine trap handler/OS/caller stack state not modeled.','premises':['Typed i64 domain0..255 comes from selected caller mask255 and prior owned typed proof. Instructions themselves do not perform bounds checks.','X7 points to live readable/writable aligned context with fuel at8 and codebase pointer at384; pool literal memory immutable/readable little-endian and disjoint from fuel/context.','Codebase+1632+i*8 is mapped and does not wrap; this finite model uses separate aligned addresses. Real mappings/trap handlers are not independently executed.','Model implements stated AArch64 integer subset semantics, not a formally verified architecture emulator. Decoder derives operand/immediate fields from actual saved words.','Original generic reader may clobber different scratch/flags/frame bytes; comparison is typed value/one fuel debit/fuel exhaustion plus substitution local write-set, not full original machine register/stack equivalence.'],'sourceEvidence':[{'path':str(p),'bytes':p.stat().st_size,'sha256':H(p.read_bytes())}for p in [D/'41-a64gen-candidate.kotoba',D/'original-input.kotoba',enc,ns]],'hardwareExecutionByReviewer':0,'compilerProcessNetworkAPICalls':0,'runtimeQualified':False,'full19Qualified':False,'selfhostFixedpointQualified':False,'performanceQualified':False,'C2Enabled':False}
p=R/'report.json';p.write_text(json.dumps(q,indent=2)+'\n');print(str(p),p.stat().st_size,H(p.read_bytes()))
