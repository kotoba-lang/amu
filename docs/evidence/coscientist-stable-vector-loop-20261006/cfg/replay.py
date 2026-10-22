from pathlib import Path
import json,collections
D=Path(__file__).resolve().parent
inputdata=json.loads((D/'replay-inputs.json').read_text());C=inputdata['constants'];op=lambda n:C['OP-'+n]
def parse(p,phase=False):
 text=p.read_text();text=text.split('PCPHASE ')[1] if phase else text;sir={};ff={};fn={};cache={}
 for l in text.splitlines():
  x=l.split()
  if not x:continue
  if x[0]=='SIR':sir[int(x[1])]=tuple(map(int,x[2:]))
  elif x[0]=='PCFF':f,k,v=map(int,x[1:]);ff.setdefault(f,{})[k]=v
  elif x[0]=='FN':fn[int(x[1])]=tuple(map(int,x[2:]))
  elif x[0]=='CACHE':cache[int(x[1])]=tuple(map(int,x[2:]))
 return sir,ff,fn,cache

def defines(q):
 o,a,b,c=q
 if o in [op(x) for x in ['CONST','LGET','STR','TAB','VEC','FADDR','VECP','RES2']]:return a
 if o in [op(x) for x in ['BIN','CMP','UN','CALL','RT','CALLI']]:return b
 if o==op('CAP'):return c
 return -1

def cfg(sir,start,end):
 labels={};pred={i:[] for i in range(start+1,end)}
 for i in pred:
  o,a,b,c=sir[i]
  if o==op('LABEL'):
   if a in labels or not 0<a<C['MM-LABEL-CAP']:raise ValueError('duplicate/outside label')
   labels[a]=i
 for i in pred:
  o,a,b,c=sir[i]
  if o==op('RET'):succ=[]
  elif o==op('BR'):succ=[labels[a]]
  elif o in [op('BRZ'),op('BRNZ')]:succ=[labels[b],i+1]
  else:succ=[i+1]
  for s in succ:
   if s==end:continue
   if s not in pred:raise ValueError('bad CFG target')
   pred[s].append(i)
 return pred,labels

# Work-budgeted iterative postorder; a path cycle with no intervening definition
# is refused, rather than interpreting a recursive origin claim as proven.
def origin(sir,pred,site,t,slot,budget):
 stack=[(site,False)];mark={};val={};visits=0;reason=None
 while stack:
  node,done=stack.pop()
  if done:
   val[node]=bool(pred[node]) and all(val.get(p,False) for p in pred[node]);mark[node]=2;continue
  if node in mark:
   if mark[node]==1:return False,visits,'cycle',list(mark)
   continue
  if visits>=budget:return False,visits,'visit-cap',list(mark)
  visits+=1
  mark[node]=1
  if defines(sir[node])==t:
   val[node]=sir[node][0]==op('LGET') and sir[node][2]==slot;mark[node]=2
   if not val[node]:reason='alternative/redefined-temp'
   continue
  if not pred[node]:val[node]=False;mark[node]=2;reason='entry-undefined';continue
  stack.append((node,True))
  for p in reversed(pred[node]):
   if mark.get(p)==1:return False,visits,'cycle',list(mark)
   if p not in mark:stack.append((p,False))
 return val[site],visits,reason,list(mark)
def query_before(sir,pred,site,t,slot,budget):
 if not pred[site]:return False,0,'entry-undefined',[]
 total=0;seen=set();notes=[]
 for p in pred[site]:
  yes,n,why,nodes=origin(sir,pred,p,t,slot,budget-total);total+=n;seen.update(nodes)
  if not yes:return False,total,why,sorted(seen)
 return True,total,None,sorted(seen)

def analyze(sir,ff,meta,cache,f):
 start=ff[C['FF-SIR']];np=ff[C['FF-NPARAMS']];slot=[k+1 for k in range(np) if ff.get(C['FF-PT0']+k)==C['TY-VEC']];end=next(i for i in range(start+1,max(sir)+1) if sir[i][0] in [op('END'),op('FN')]);frame=((8*(meta[2]+meta[3]+2)+15)//16)*16+((8*(meta[4]+3)+15)//16)*16
 pre=(1<=np<=5 and len(slot)==1 and all(ff.get(C['FF-PT0']+k) in [C['TY-VEC'],C['TY-I64'],C['TY-BOOL']] for k in range(np)) and end-start<=8192 and sir[end][:2]==(op('END'),f) and meta[5]==1 and meta[4]<=7 and frame<=32768 and cache[start][2]==0)
 r={'fn':f,'start':start,'end':end,'preconditions':pre,'oldFrame':meta[1],'newFrameEstimate':frame,'queries':[],'refusals':[],'visits':0}
 if not pre:return r
 slot=slot[0];pred,labels=cfg(sir,start,end);backs=0;reads=0
 for i in range(start+1,end):
  o,a,b,c=sir[i];good=True;need=None
  if o in [op(x) for x in ['CONST','LGET','RET','FUEL','LABEL']]:pass
  elif o==op('LSET'):
   if a==slot:need=b
  elif o in [op('BIN'),op('CMP'),op('UN')]:good=a<C[{op('BIN'):'BOP-F64-ADD',op('CMP'):'CC-F64-EQ',op('UN'):'UOP-F64-NEG'}[o]]
  elif o==op('RT'):reads+=1;good=a==C['RT-VECTOR-AT'] and c==2 and 0<=b<=5;need=b
  elif o in [op('BR'),op('BRZ'),op('BRNZ')]:backs+=int(labels[a if o==op('BR') else b]<i)
  else:good=False
  if not good:r['refusals'].append({'sir':i,'reason':'excluded-op-shape','instruction':sir[i]});continue
  if need is not None:
   yes,n,why,nodes=query_before(sir,pred,i,need,slot,131072-r['visits']);r['visits']+=n;r['queries'].append({'sir':i,'temp':need,'origin':slot if yes else None,'visits':n,'reason':why,'proofNodes':nodes})
   if not yes:r['refusals'].append({'sir':i,'reason':why})
 r['reads']=reads;r['backedges']=backs;r['admit']=reads>=2 and backs>0 and not r['refusals'];return r


rows=[]
for x in inputdata['cases']:
 sir={int(k):tuple(v) for k,v in x['sir'].items()};ff={int(k):{int(a):b for a,b in v.items()} for k,v in x['ff'].items()};fn={int(k):tuple(v) for k,v in x['fn'].items()};cache={int(k):tuple(v) for k,v in x['cache'].items()}
 for f,m in fn.items():
  r=analyze(sir,ff[f],m,cache,f);r['workload']=x['workload']
  if r['preconditions']:rows.append(r)
expected=json.loads((D/'analysis.json').read_text())['examinedEligible'];assert json.loads(json.dumps(rows))==expected
print('PASS portable exact original19 analysis replay',len(rows),'eligible-shaped functions')
