"""Offline raw census only; no compiler/native calls and no key eligibility approval."""
from collections import Counter
WIDTH={'CQ-ACTIVATE':3,'CQ-DEACTIVATE':1,'CQ-ENTRY':21,'CQ-EXIT':8,'CQ-EDGE':9,'CQ-UNSUPPORTED':1,'CQ-EXIT-UNSUPPORTED':1}
def parse(raw):
 assert type(raw)is bytes and len(raw)<=67108864
 active=False;activation=0;pending=None;queries=[];activations=[]
 for line in raw.decode('utf-8').splitlines():
  if not line.startswith('CQ-'):continue
  fields=line.split();tag=fields[0];assert tag in WIDTH and len(fields)==WIDTH[tag]+1;v=list(map(int,fields[1:]));assert all(-(1<<63)<=x<(1<<63)for x in v)
  if tag=='CQ-ACTIVATE':
   assert not active and pending is None;active=True;activation+=1;activations.append({'activation':activation,'status':v[0],'fnN':v[1],'sirN':v[2]})
  elif tag=='CQ-DEACTIVATE':assert active and pending is None;active=False;activations[-1]['finalError']=v[0]
  elif tag in ['CQ-ENTRY','CQ-UNSUPPORTED']:
   assert active and pending is None;pending={'activation':activation,'entry':v,'unsupported':tag=='CQ-UNSUPPORTED','edges':[]}
  elif tag in ['CQ-EXIT','CQ-EXIT-UNSUPPORTED']:
   assert active and pending is not None and pending['entry'][0]==v[0];pending['exit']=v
   if pending['unsupported']or tag=='CQ-EXIT-UNSUPPORTED':pending['unsupported']=True
   queries.append(pending);pending=None
  else:
   assert active and pending is None and queries and queries[-1]['activation']==activation and queries[-1]['entry'][0]==v[0];q=queries[-1];assert not q['unsupported'];assert 0<=v[1]<q['entry'][5] and v[2]>0 and 0<v[3]<q['entry'][4] and v[4]>=0 and all(x>=-1 for x in v[5:]);assert not q['edges']or v[1]>q['edges'][-1][1];q['edges'].append(v)
 assert not active and pending is None
 seenSubjects=Counter();seenSmall=Counter();subjectRepeats=smallRepeats=hit=miss=refusal=unsupported=0;classified=[]
 for q in queries:
  if q['unsupported']:unsupported+=1;continue
  e,x=q['entry'],q['exit'];assert e[0]==x[0]and x[2]>=e[2];subject=(q['activation'],e[0],1);key=subject+tuple(e[7:11]);subjectRepeats+=int(seenSubjects[subject]>0);smallRepeats+=int(seenSmall[key]>0);seenSubjects[subject]+=1;seenSmall[key]+=1
  admission=e[3]==0 and e[16]==1 and e[17]==0
  # Source-defined precondition plus actual control29 outcome; stale prior29 never counted.
  match=e[6]==1 and e[7:11]==e[11:15]
  if not admission or x[3]!=0:kind='refusal';refusal+=1
  elif match and x[4]==1:kind='existingMemoHit';hit+=1
  else:kind='existingMemoMiss';miss+=1
  classified.append({'activation':q['activation'],'subject':e[0],'phaseBefore':e[1],'phaseAfter':x[1],'workBefore':e[2],'workAfter':x[2],'workDelta':x[2]-e[2],'entryFourBounds':e[7:11],'lastFourBounds':e[11:15],'validBefore':e[6],'validAfter':x[7],'supportAfter':x[5],'poisonAfter':x[6],'existingPathClassification':kind,'orderedEdges':q['edges']})
 return {'status':'OFFLINE_RAW_FREQUENCY_CENSUS_ONLY','activations':activations,'queryCalls':len(queries),'sameTargetModeRepeats':subjectRepeats,'fourBoundProjectionRepeats':smallRepeats,'existingMemoHits':hit,'existingMemoMisses':miss,'refusals':refusal,'unsupported':unsupported,'queries':classified,'fullComputeCIDRepetitions':None,'semanticRequestEligibilityQualified':False,'fullRequestReadClosureQualified':False,'newCacheHits':0,'newQuerySkips':0,'C2':False,'timingQualified':False,'projectionMeaning':'Frequency-only same-activation target/mode +fourbound values; work/status/preaggregate/control/memo never approved for exclusion.'}
if __name__=='__main__':
 from pathlib import Path
 import sys,json
 assert len(sys.argv)==2;print(json.dumps(parse(Path(sys.argv[1]).read_bytes()),indent=2))
