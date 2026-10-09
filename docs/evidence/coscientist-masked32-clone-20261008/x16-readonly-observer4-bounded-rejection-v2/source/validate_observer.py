"""Finite saved-data validator. No process/native APIs. SOURCE instrument trusted only after artifact/source binding."""
import re,struct
PATTERN=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0]
def need(x,m):
 if not x:raise AssertionError(m)
def split(raw):
 need(type(raw)is bytes and 0<len(raw)<=8388608,'raw8MiB')
 lines=raw.splitlines(keepends=True);need(all(x.endswith(b'\n')for x in lines),'whole newline')
 need(lines and lines[-1].startswith(b'{:ok true,'),'exact compiler suffix')
 return lines[:-1],lines[-1]
def validate(lines,payload):
 need(type(payload)is bytes and 0<len(payload)<=4194304,'bounded whole native payload')
 rows=[]
 for line in lines:
  m=re.fullmatch(rb'(RH|RQ|RF|RS|RC|RI|RE)((?: -?(?:0|[1-9][0-9]{0,19}))+)\n',line);need(m is not None,'unknown/refuse/truncated row')
  v=list(map(int,m[2].split()));need(all(-(2**63)<=n<2**64 for n in v),'finite field widths');rows.append((m[1].decode(),v))
 pos=0
 def take(tag):
  nonlocal pos
  need(pos<len(rows)and rows[pos][0]==tag,'ordered '+tag);v=rows[pos][1];pos+=1;return v
 h0=take('RH');need(len(h0)==5 and h0[0:2]==[0,0]and 1<=h0[2]<=8192 and 1<=h0[3]<=196608,'typed header');need(h0[2]*1000+524288*12+262144<=8388608,'pre-output capacity law')
 q0=take('RQ');need(len(q0)==22 and 0<=q0[0]<=16 and 0<=q0[1]<=256 and 0<=q0[2]<=64 and all(n>=0 for n in q0),'partition bounds')
 selected=q0[6:6+q0[0]];need(selected==sorted(set(selected))and all(0<f<h0[2]for f in selected)and q0[6+q0[0]:]==[0]*(16-q0[0]),'ordered selected owners')
 fn0=[take('RF')for _ in range(h0[2])]
 for i,r in enumerate(fn0):need(len(r)==6 and r[:2]==[0,i]and 0<=r[2]<h0[3]and 0<=r[4]<=16 and r[5]>=0,'complete FN summary')
 sir0={};ranges={}
 for f in selected:
  ss=[]
  while pos<len(rows)and rows[pos][0]=='RS'and rows[pos][1][1]==f:
   r=take('RS');need(len(r)==7 and r[:2]==[0,f]and r[2]==fn0[f][2]+len(ss),'complete ordered SIR');ss.append(r)
  need(2<=len(ss)<=256 and ss[0][3:5]==[1,f]and ss[-1][3:5]==[2,f],'owned FN END')
  for r in ss:need(r[2]not in sir0,'unique SIR');sir0[r[2]]=r
  ranges[f]=(ss[0][2],ss[-1][2]+1)
 need(len(sir0)==q0[1],'full selected SIR count');need(take('RE')==[0],'pre footer')
 events={}
 while pos<len(rows)and rows[pos][0]=='RI':
  r=take('RI');need(len(r)==8 and r[0]in sir0 and r[0]not in events and 1<=r[1]<=r[2]<=524288 and 0<=r[3]<=256 and r[-1]==0 and r[4]in [0,1]and r[5]in [0,1,2]and r[6]in [0,1],'actual emitted interval');events[r[0]]=r
 h1=take('RH');need(len(h1)==5 and h1[:4]==[1,0,h0[2],h0[3]]and 1<=h1[4]<=524288,'post header');need(take('RQ')==q0,'immutable selection')
 fn1=[take('RF')for _ in range(h0[2])]
 for i,(a,b)in enumerate(zip(fn0,fn1)):need(len(b)==6 and b[:2]==[1,i]and a[2]==b[2]and a[4:]==b[4:]and 0<=b[3]<h1[4],'FN identity/code bounds')
 code={}
 for f in selected:
  start,end=ranges[f]
  for i in range(start,end):r=take('RS');need(r==[1,*sir0[i][1:]],'SIR unchanged')
  c=take('RC');need(len(c)>=3 and c[0]==f and c[1]==fn1[f][3]and 1<=c[1]<c[2]<=h1[4]and len(c)-3==c[2]-c[1]and all(0<=w<2**32 for w in c[3:]),'complete CODE interval')
  for j,w in enumerate(c[3:],c[1]):need(j not in code,'disjoint CODE owners');code[j]=w
  i=start
  while i<end:
   need(i in events,'missing gn-ins event');e=events[i];need(c[1]<=e[1]<=e[2]<=c[2],'event owned physical CODE');i+=1+e[3]
  need(i==end,'exact consumed SIR coverage')
 need(take('RE')==[1]and pos==len(rows),'complete footer/no extras')
 pairs=[];excluded=[]
 for f in selected:
  start,end=ranges[f];prior=None;middle=[]
  for i in range(start,end):
   op=sir0[i][3];e=events.get(i)
   if op==18:
    if e is not None and e[3]==0 and e[4]==0 and e[5]in [0,2]and e[2]-e[1]==5:need([code.get(k)for k in range(e[1],e[2])]==PATTERN,'ordinary fuel words exact')
    ordinary=e is not None and e[3]==0 and e[4]==0 and e[5]in [0,2]and e[2]-e[1]==5 and [code.get(k)for k in range(e[1],e[2])]==PATTERN
    if ordinary:
     off=(e[1]-1)*4;need(off+20<=len(payload)and list(struct.unpack('<5I',payload[off:off+20]))==PATTERN,'actual wholepayload fuel projection')
     if prior is not None and all(events.get(j)is not None and events[j][1]==events[j][2]and events[j][3]==0 for j in middle)and prior[2]==e[1]:pairs.append({'FN':f,'firstSIR':prior[0],'secondSIR':i,'removeLDRWord':e[1],'physicalByteOffset':off,'interveningSIR':middle[:]})
     prior=e;middle=[]
    else:prior=None;middle=[];excluded.append({'FN':f,'SIR':i,'reason':'not-exact-ordinary-published-fiveword-fuel'})
   elif op in [3,4]and prior is not None:middle.append(i)
   else:prior=None;middle=[]
 return {'status':'ELIGIBLE_INITIAL_BOUNDED_X16_RELOAD_RULE_ONLY'if pairs else'REJECTED_INITIAL_BOUNDED_X16_RELOAD_RULE_NO_PAIR','pairs':pairs,'eligiblePairs':len(pairs),'selectedFNs':selected,'selectedSIR':len(sir0),'largeFNOmitted':q0[4],'budgetFNOmitted':q0[5],'typedPotentialPairsBoundedFunctions':q0[3],'excludedFuelSites':excluded,'globalApplicabilityClaim':False,'productRuleImplemented':False}
