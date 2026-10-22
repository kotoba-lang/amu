from pathlib import Path
import json,hashlib,copy,collections
P=Path('/private/tmp/amu-aes-resident-fuel-20261007');D=Path(__file__).parent
ip=json.loads((P/'root/general-vector-effect-census-v1/input-pins.json').read_text())
RANGES=[(272,2320),(4368,6416),(8464,10512),(12560,14608),(14608,14864),(14864,15152)]
def reserve(s):
 if any(s.get(i,0)!=0 for a,b in RANGES for i in range(a,b)):return False,s.copy()
 return True,{**s,272:1}
def need(op,a,b,c):
 if op in [3,4,16,19,11,12,21,22,24,25]:return a+1
 if op==26:return a+2
 if op in [5,8]:return b+1
 if op in [6,7]:return b+2
 if op==15:return c+1
 if op in [13,14]:return b+max(c,1)
 if op==23:return b+c+1
 if op==17:return a+max(b,1)
 return 0
# Indexed-domain validation only, not dominance/definedness or semantic type proof.
def audit(r):
 sir=[x['fields'] for x in r if x['tag']=='SIR'];frecs={x['fields'][0]:x['fields'][1:] for x in r if x['tag']=='FREC'}
 env=[x['fields'] for x in r if x['tag']=='TABLES'];errors=[];facts=[];bodies=[];edges=[]
 def err(s,msg):errors.append({'sir':s,'reason':msg})
 if len(env)!=1:return {'errors':[{'reason':'missing TABLES'}]}
 sn,fn,ln=env[0][:3]
 if sn!=len(sir)+1 or [x[0] for x in sir]!=list(range(1,sn)):err(0,'SIR count/noncontiguous rows')
 if sorted(frecs)!=list(range(1,fn)):err(0,'FREC ids/count')
 if fn>128:err(0,'module FN-N budget exceeds128 including reserved0/non-body definitions')
 if sn>65536:err(0,'module SIR-N budget')
 current=None;labels={};branches=[]
 for q in sir:
  i,op,a,b,c=q
  if op==1:
   if current is not None:err(i,'nested FN without END')
   if a not in frecs:err(i,'FN target missing');current=None;continue
   ff=frecs[a]
   if ff[12]!=i or ff[3]!=b:err(i,'FREC FN-SIR/arity mismatch')
   current={'fn':a,'start':i,'np':b,'ns':max(c,ff[10],b),'dp':ff[15],'blocks':1,'reads':0,'edges':0};labels={};branches=[]
   if min(b,c,ff[10],ff[15])<0:err(i,'negative FN/FF slot/depth/arity')
   params=[{'vectorOrdinal':v,'actualParameterPosition':k+1,'localSlot':k+1,'coarseFFType':4,'elementTypeProof':'FF type4 bound to pinned checker TY-VEC=vector-i64; conditional on checked FREC provenance'} for v,k in enumerate([k for k in range(min(b,5)) if ff[5+k]==4])]
   facts.append({'fn':a,'firstFourCoarseVectorParameters':params[:4],'excessCoarseVectorParameters':params[4:],'parametersBeyondFFFirstFiveUnknown':max(0,b-5),'NFChildChainsPresent':False})
   continue
  if current is None:
   err(i,'instruction outside owned FN');continue
  if op==2:
   if (a,b,c)!=(current['fn'],0,0):err(i,'END ownership/reserved operands')
   current['end']=i
   owned=[q for q in sir if current['start']<q[0]<i]
   leaders={current['start']+1}
   for j,o,x,y,z in owned:
    if o==9:leaders.add(j)
    if o in [10,11,12,19,20,26] and j+1<i:leaders.add(j+1)
   current['blocks']=len(leaders)
   current['blockLeaders']=sorted(leaders)
   if i-current['start']>8192:err(i,'body8192 budget')
   if current['ns']>128 or current['dp']>128:err(i,'actual ns/dp module precheck exceeds128')
   for s,l in branches:
    if l not in labels:err(s,'branch label outside body/missing')
   current['analysisRefusals']=(['blocks>8'] if current['blocks']>8 else [])+(['tracked locals>64'] if current['ns']>64 else [])+(['tracked temps>64'] if current['dp']>64 else [])
   bodies.append(current);current=None;continue
  if not 3<=op<=26:err(i,'unknown opcode');continue
  # Operand rules mirror gn-need + all bank-address-bearing arguments.
  temp=[];local=[];reserved=[]
  if op in [3,4,16,19,21,22,24,25,26]:temp=[a]+([a+1] if op==26 else [])
  if op==4:local=[b];reserved=[c]
  if op==5:local=[a];temp=[b];reserved=[c]
  if op in [6,7]:temp=[b,b+1];reserved=[c]
  if op==8:temp=[b];reserved=[c]
  if op in [11,12]:temp=[a];branches.append((i,b));reserved=[c];current['blocks']+=1
  if op==10:branches.append((i,a));reserved=[b,c];current['blocks']+=1
  if op==9:
   if a<=0 or a in labels:err(i,'invalid/duplicate LABEL')
   labels[a]=i;reserved=[b,c];current['blocks']+=1
  if op in [13,14]:
   if c<0:err(i,'negative call arity')
   temp=[b,b+max(c,1)-1]
   if op==13:
    if a not in frecs or frecs[a][3]!=c:err(i,'call target/arity mismatch')
    edges.append((current['fn'],i,a,b));current['edges']+=1
   else:
    if a<0 or a%8:err(i,'runtime slot domain')
    if a==176:current['reads']+=1
  if op==23:temp=[b,b+c];reserved=[a]
  if op==15:temp=[c]
  if op==17:temp=[a,a+max(b,1)-1];reserved=[c]
  if op in [18]:reserved=[a,b,c]
  if op in [3,16,22,25]:reserved=[c]
  if op in [19,25,26]:reserved=[b,c]
  if op==20:reserved=[b,c]
  if any(v<0 for v in temp):err(i,'negative temporary operand before bank read')
  if any(v<1 for v in local):err(i,'invalid local slot before bank read')
  if any(reserved):err(i,'nonzero reserved operand')
  if op in [16,21,24] and not(0<b<ln):err(i,'literal pool index domain')
  if op==22 and b not in frecs:err(i,'FADDR missing FN')
  current['dp']=max(current['dp'],need(op,a,b,c))
  current['ns']=max(current['ns'],max(local,default=0))
 if current is not None:err(current['start'],'unterminated FN')
 if len(edges)>512:err(0,'direct edge512 budget')
 reads=sum(b['reads'] for b in bodies)
 # Raw read ceiling is NOT eligible-site cap; only certificates count against256.
 return {'errors':errors,'FN_NIncludingReservedAndNonbody':fn,'bodyFunctions':len(bodies),'directEdges':len(edges),'allVectorReadCeiling':reads,'site256Budget':'cannot infer from raw reads; requires eligible certificate count','bodies':bodies,'parameterMaps':facts,'modulePrecheckPass':not errors,'elementTypeCertification':'first-five FF code4 identifies vector-i64 by exact pinned checker contract; NF child chains/body expression types and params beyond5 remain unavailable'}
