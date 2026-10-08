from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,sys,re
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-compute-current19-query-census40-plan-v2-controls';O=Path(__file__).resolve().parent;R=D/'run-outputs';inputs={}
def pin(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):inputs[str(p)]=pin(p);return p.read_bytes()
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
audit=W/'vector-compute-current19-query-census40-actual-review-v2-census-review/report.json';assert pin(audit)['sha256']=='20540e990a2bcf0839c8e6aaea60ce5d08cf1d0f319a109c7a25f0daf9fc67ef';read(audit)
pr=json.loads(read(D/'preregistration.json'));compares=[];summaries=[];allResultCount=Counter();stats=Counter();drops=[]
for i,e in enumerate(pr['entries']):
 n=e['workload'];raw=read(R/'ports'/n/(str(3+2*i)+'.stdout'));rows=[];activation=0;entry=None
 for line in raw.decode().splitlines():
  if not line.startswith('CQ-'):continue
  t,*rest=line.split();v=list(map(int,rest))
  if t=='CQ-ACTIVATE':activation+=1
  elif t=='CQ-ENTRY':entry=v
  elif t=='CQ-EXIT':
   rows.append({'activation':activation,'fn':entry[0],'entry':entry,'exit':v,'edges':[]});entry=None
  elif t=='CQ-EDGE':rows[-1]['edges'].append(v)
  elif t in ('CQ-UNSUPPORTED','CQ-EXIT-UNSUPPORTED'):raise AssertionError('unexpected unsupported')
 last={};seen=set();results=defaultdict(set);local=Counter()
 for q in rows:
  e0,x=q['entry'],q['exit'];sub=(q['activation'],q['fn']);hit=e0[6]==1 and e0[7:11]==e0[11:15]and x[4]==1;assert e0[3]==x[3]==0
  q['projection']={'exitStatus':x[3],'exitSupport':x[5],'exitPoison':x[6],'orderedEdges':q['edges']}
  # Canonical complete captured projection bytes; equality below is byte equality, never digest equality.
  q['projectionBytes']=json.dumps(q['projection'],sort_keys=True,separators=(',',':')).encode()
  valid=e0[16]==x[5]==1 and e0[17]==x[6]==0 and e0[3]==x[3]==0
  if not valid:drops.append({'workload':n,'activation':q['activation'],'fn':q['fn'],'entrySupport':e0[16],'exitSupport':x[5]})
  if sub in seen and not hit:
   assert e0[7:11]!=e0[11:15];prior=last[sub];pvalid=prior['entry'][16]==prior['exit'][5]==1 and prior['entry'][17]==prior['exit'][6]==0
   equal=q['projectionBytes']==prior['projectionBytes'];classification='excludedSupportPoison'if not(valid and pvalid)else('projectionIdentical'if equal else 'projectionDifferent')
   stats[classification]+=1;local[classification]+=1
   compares.append({'workload':n,'activation':q['activation'],'fn':q['fn'],'entryBounds':e0[7:11],'storedMemoBounds':e0[11:15],'priorEntryBounds':prior['entry'][7:11],'priorWasExistingMemoHit':prior['entry'][6]==1 and prior['entry'][7:11]==prior['entry'][11:15]and prior['exit'][4]==1,'classification':classification,'exactProjectionBytesEqual':equal,'projection':q['projection'],'priorProjection':prior['projection']})
  seen.add(sub);last[sub]=q
  if valid:results[sub].add(q['projectionBytes'])
 for sub,values in results.items():allResultCount[len(values)]+=1
 summaries.append({'workload':n,'calls':len(rows),'changedBoundMissComparisons':sum(local.values()),'comparisons':dict(local),'subjects':len(seen),'successfulSubjects':len(results),'distinctSuccessfulProjectionCount':sum(len(v)for v in results.values()),'distinctProjectionCountsBySubject':dict(Counter(len(v)for v in results.values()))})
assert sum(stats.values())==269
source=json.loads(read(D/'source-pins.json'));kernel=read(D/'unity-census.kotoba').decode();mm=re.search(r'\(def MM-WORDS (\d+)\)',kernel);words=int(mm.group(1))if mm else None
r={'status':'OFFLINE_ORDERED_OUTPUT_PROJECTION_CENSUS_ONLY','queryCalls':4212,'changedBoundMisses':269,'comparison':'Most recent prior same workload+activation+fn query, including existing memo hits; exact canonical captured-projection byte equality','comparisonCounts':dict(stats),'supportPoisonExcludedQueries':drops,'successfulDistinctProjectionMultiplicityAcrossSubjects':dict(allResultCount),'totalDistinctSuccessfulSubjectProjections':sum(k*v for k,v in allResultCount.items()),'perWorkload':summaries,'projectionFields':['CQ-EXIT status/support/poison','complete ordered CQ-EDGE records:caller,edgeOrdinal,SIRsite,target,base,all4contributions'],'preserved':['emptyedge sequence','-1neutral','0poison','duplicate edge records','original order','caller/SIR/target/base identity'],'notCaptured':['edge arity: CQ-EDGE schema has no arity; cannot claim preservation of unknown arity','query summary/certificate control9..14','complete written scratch, memo and aggregate state','trap details and cleanup effects','dynamic read closure and rule/ABI/input contract seal','allocation/IO diagnostics and budget guard event order'],'exitOtherFields':'phase/work/control29/memoValidAfter captured separately; phase/work and memo-internal fields are excluded only from this explicitly incomplete output projection, with no production exclusion approval','candidateMeaning':'Identical captured output is only a cohort for a closed-role shadow experiment; no downstream stopping or full semantic reuse qualified','fullResultCIDQualified':False,'fullComputeCIDQualified':False,'productionReuseQualified':False,'newQuerySkips':0,'C2':False,'nativeCalls':0,'SSHCalls':0,'MMWORDS':words,'binaryFullMSnapshotBytes':words*8 if words else None,'stdoutCapBytes':67108864,'participation':'Same census source/actual reviewer. Offline exact saved projection analysis only; frozen source plan unmodified.'}
save(O/'comparisons.json',compares);save(O/'report.json',r);save(O/'input-pins.json',inputs);save(O/'source-pins.json',{p.name:pin(p)for p in sorted(O.iterdir())if p.is_file()and p.name!='source-pins.json'});print(json.dumps({'report':pin(O/'report.json'),'counts':dict(stats),'distinct':dict(allResultCount),'MMWORDS':words}))
