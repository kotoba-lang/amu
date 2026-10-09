"""Strict offline declared output projection decoder; no native calls or reuse approval."""
import json
WIDTH={'CQ-ACTIVATE':3,'CQ-DEACTIVATE':1,'CQ-ENTRY':21,'CQ-EXIT':8,'CQ-EDGE':9,'CQ-UNSUPPORTED':1,'CQ-EXIT-UNSUPPORTED':1,'CR-RESULT':11,'CR-WVF':3,'CR-FNF':3,'CR-EDGE':14,'CR-EDGE-INVALID':3,'CR-END':5}
OP_CALL=13
def parse(raw):
 assert isinstance(raw,bytes)and len(raw)<=67108864
 active=False;activation=0;pending=None;closed=None;rows=[];edgePending=None
 for line in raw.decode().splitlines():
  if not line.startswith(('CQ-','CR-')):continue
  fs=line.split();tag=fs[0];assert tag in WIDTH and len(fs)==WIDTH[tag]+1;v=list(map(int,fs[1:]));assert all(-(1<<63)<=x<(1<<63)for x in v)
  if tag=='CQ-ACTIVATE':assert not active and pending is None and closed is None;active=True;activation+=1
  elif tag=='CQ-DEACTIVATE':assert active and pending is None and closed is None and edgePending is None;active=False
  elif tag in ('CQ-ENTRY','CQ-UNSUPPORTED'):
   assert active and pending is None and closed is None;pending={'activation':activation,'entry':v,'unsupported':tag=='CQ-UNSUPPORTED','exit':None,'result':None,'wvf':[],'fnf':[],'edges':[],'invalidEdges':[]}
  elif tag in ('CQ-EXIT','CQ-EXIT-UNSUPPORTED'):
   assert pending and closed is None and pending['entry'][0]==v[0];pending['exit']=v;pending['unsupported']|=tag=='CQ-EXIT-UNSUPPORTED';closed=pending;pending=None
  else:
   assert active and closed is not None and closed['entry'][0]==v[0]
   q=closed
   if tag=='CR-RESULT':assert not q['unsupported']and q['result']is None and not q['wvf'];q['result']=v
   elif tag=='CR-WVF':
    assert q['result']and len(q['wvf'])==len(q['fnf'])and len(q['wvf'])<16 and not q['edges'];assert v[1]==len(q['wvf']);q['wvf'].append(v[2])
   elif tag=='CR-FNF':
    assert len(q['wvf'])==len(q['fnf'])+1 and v[1]==len(q['fnf'])and not q['edges'];q['fnf'].append(v[2])
   elif tag=='CQ-EDGE':
    assert len(q['wvf'])==len(q['fnf'])==16 and edgePending is None and 0<=v[1]<q['entry'][5];assert not q['edges']or v[1]>q['edges'][-1][1];edgePending=v
   elif tag=='CR-EDGE':
    assert edgePending and v[:5]==edgePending[:5]and v[10:]==edgePending[5:];assert v[6]==OP_CALL and v[7]==v[3]and v[8]==v[4]and v[9]==v[5]and 0<=v[5]<=128
    assert 0<v[2]and v[3]>0 and v[4]>=0 and all(x>=-1 for x in v[10:]);q['edges'].append(v);edgePending=None
   elif tag=='CR-EDGE-INVALID':assert edgePending and v==edgePending[:3];q['invalidEdges'].append(v);edgePending=None
   elif tag=='CR-END':
    assert edgePending is None and v[3]in (0,1)and v[4]==len(q['edges'])+len(q['invalidEdges'])
    if q['unsupported']:assert v[3]==0 and q['result']is None
    else:
     assert v[3]==1 and len(q['wvf'])==len(q['fnf'])==16 and q['result']is not None
     e,x,r=q['entry'],q['exit'],q['result'];assert r[:5]==[x[0],x[3],x[5],x[6],x[7]]and v[1:3]==[e[16],e[17]]and r[2:4]==[q['wvf'][15],q['wvf'][14]]
    q['supportedSuccessful']=not q['unsupported']and not q['invalidEdges']and v[1:3]==[1,0]and q['result'][1:4]==[0,1,0]
    q['projection']={'statusSupportPoisonMemoValid':q['result'][1:5]if q['result']else None,'summaryControls9to14':q['result'][5:]if q['result']else None,'subjectVWFields':q['wvf'],'subjectFNFields':q['fnf'],'orderedEdges':q['edges']}
    q['canonicalProjectionBytes']=json.dumps(q['projection'],sort_keys=True,separators=(',',':')).encode().hex();rows.append(q);closed=None
 assert not active and pending is None and closed is None and edgePending is None
 return {'status':'OFFLINE_DECLARED_OUTPUT_ROLE_PROJECTION_ONLY','queries':rows,'calls':len(rows),'supportedSuccessful':sum(q['supportedSuccessful']for q in rows),'fullResultCIDQualified':False,'fullComputeCIDQualified':False,'downstreamSkips':0,'C2':False}
if __name__=='__main__':
 import sys
 from pathlib import Path
 assert len(sys.argv)==2;print(json.dumps(parse(Path(sys.argv[1]).read_bytes()),indent=2))
