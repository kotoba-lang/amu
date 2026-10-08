from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,stat,re,statistics
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-compute-result-projection-offline-v1-census-review';C=W/'vector-compute-current19-query-census40-plan-v2-controls';A=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();return {'bytes':s.st_size,'sha256':H(p)}
assert H(D/'report.json')=='878a3b9ec0374d3f29a2b8bbdae477467e360792b0ed23c78c7366c9d1cffed0'
sp=load(D/'source-pins.json');assert H(D/'source-pins.json').startswith('b350');pins=load(D/'input-pins.json');publishedCount=len(pins)
for p,v in pins.items():assert rec(p)==v
for n,v in sp.items():assert rec(D/n)==v;pins[str(D/n)]=v
pr=load(C/'preregistration.json');computed=[];summaries=[];drops=[];stats=Counter();multiplicity=Counter();nqueries=0;successsubjects=0;workgroups=defaultdict(list)
for i,e in enumerate(pr['entries']):
 name=e['workload'];p=C/'run-outputs/ports'/name/(str(3+2*i)+'.stdout');raw=p.read_bytes();queries=[];activation=0;active=None;lastquery=None
 for line in raw.decode('utf8').splitlines():
  if not line.startswith('CQ-'):continue
  tag,*xs=line.split();v=list(map(int,xs));assert all(-(1<<63)<=z<(1<<63)for z in v)
  if tag=='CQ-ACTIVATE':assert active is None;activation+=1;lastquery=None
  elif tag=='CQ-DEACTIVATE':assert len(v)==1 and active is None;lastquery=None
  elif tag=='CQ-ENTRY':assert len(v)==21 and active is None and activation>0;active=v;lastquery=None
  elif tag=='CQ-EXIT':
   assert len(v)==8 and active is not None and v[0]==active[0];lastquery={'activation':activation,'fn':v[0],'entry':active,'exit':v,'edges':[]};queries.append(lastquery);active=None
  elif tag=='CQ-EDGE':
   assert len(v)==9 and lastquery is not None and active is None and v[0]==lastquery['fn'];assert not lastquery['edges']or lastquery['edges'][-1][1]<v[1];lastquery['edges'].append(v)
  else:raise AssertionError('unsupported CQ tag '+tag)
 assert active is None
 latest={};distinct=defaultdict(set);seen=set();local=Counter();nqueries+=len(queries)
 for q in queries:
  ent=q['entry'];ex=q['exit'];subject=(q['activation'],q['fn']);assert ent[3]==ex[3]==0
  hit=ent[6]==1 and ent[7:11]==ent[11:15]and ex[4]==1
  projection={'exitStatus':ex[3],'exitSupport':ex[5],'exitPoison':ex[6],'orderedEdges':q['edges']}
  # Independent ordered tuple serialization preserves every edge/ordinal including duplicates and neutral/poison values.
  ordered=(ex[3],ex[5],ex[6],tuple(tuple(v)for v in q['edges']))
  q['projection']=projection;q['ordered']=ordered
  valid=ent[16]==ex[5]==1 and ent[17]==ex[6]==0
  if not valid:drops.append({'workload':name,'activation':q['activation'],'fn':q['fn'],'entrySupport':ent[16],'exitSupport':ex[5]})
  if subject in latest and not hit:
   assert ent[7:11]!=ent[11:15];prev=latest[subject];pe=prev['entry'];px=prev['exit'];pv=pe[16]==px[5]==1 and pe[17]==px[6]==0;equal=ordered==prev['ordered'];kind='excludedSupportPoison'if not(valid and pv)else('projectionIdentical'if equal else'projectionDifferent');stats[kind]+=1;local[kind]+=1;workgroups[kind].append(ex[2]-ent[2]);assert ex[2]>=ent[2]
   computed.append({'workload':name,'activation':q['activation'],'fn':q['fn'],'entryBounds':ent[7:11],'storedMemoBounds':ent[11:15],'priorEntryBounds':pe[7:11],'priorWasExistingMemoHit':pe[6]==1 and pe[7:11]==pe[11:15]and px[4]==1,'classification':kind,'exactProjectionBytesEqual':equal,'projection':projection,'priorProjection':prev['projection']})
   # Confirm equality conclusion exactly matches author's canonical JSON bytes, with no hash-equality assumption.
   enc=lambda z:json.dumps(z,sort_keys=True,separators=(',',':')).encode();assert equal==(enc(projection)==enc(prev['projection']))
  latest[subject]=q;seen.add(subject)
  if valid:distinct[subject].add(ordered)
 multi=Counter(len(v)for v in distinct.values());multiplicity.update(multi);successsubjects+=len(distinct)
 summaries.append({'workload':name,'calls':len(queries),'changedBoundMissComparisons':sum(local.values()),'comparisons':dict(local),'subjects':len(seen),'successfulSubjects':len(distinct),'distinctSuccessfulProjectionCount':sum(len(v)for v in distinct.values()),'distinctProjectionCountsBySubject':dict(multi)})
r=load(D/'report.json');assert computed==load(D/'comparisons.json')and nqueries==r['queryCalls']==4212 and sum(stats.values())==r['changedBoundMisses']==269 and dict(stats)==r['comparisonCounts']=={'projectionDifferent':209,'projectionIdentical':60}
assert json.loads(json.dumps(summaries))==r['perWorkload']and drops==r['supportPoisonExcludedQueries']==[{'workload':'slre','activation':1,'fn':24,'entrySupport':1,'exitSupport':0}]
assert dict(multiplicity)=={1:329,2:209}and successsubjects==538 and sum(k*v for k,v in multiplicity.items())==r['totalDistinctSuccessfulSubjectProjections']==747
assert {str(k):v for k,v in multiplicity.items()}==r['successfulDistinctProjectionMultiplicityAcrossSubjects']
assert all(r[k]is False for k in ['fullResultCIDQualified','fullComputeCIDQualified','productionReuseQualified','C2'])and r['newQuerySkips']==r['nativeCalls']==r['SSHCalls']==0
src=(C/'unity-census.kotoba').read_text();assert '(cq-print "CQ-EDGE" [f e (vw-e M e 1) (vw-e M e 2) (vw-e M e 3)'in src and '(cq-print "CQ-EXIT" [f (vw-c m 26) (vw-c m 0) (vw-c m 1) (vw-c m 29)'in src
assert r['MMWORDS']==8388608 and r['binaryFullMSnapshotBytes']==67108864 and r['stdoutCapBytes']==67108864
for p in [D/'source-pins.json',Path(__file__).resolve(),A/'initial-reader-failure.json']:pins[str(p)]=rec(p)
for p,v in pins.items():assert rec(p)==v
(A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');(A/'reconstructed-comparisons.json').write_text(json.dumps(computed,indent=2)+'\n')
out={'status':'PASS_INDEPENDENT_OFFLINE_CAPTURED_OUTPUT_PROJECTION_COUNTS_ONLY','sourceReportSHA256':H(D/'report.json'),'sourcePinsSHA256':H(D/'source-pins.json'),'inputPinsSHA256':H(A/'input-pins.json'),'reconstructedComparisonsSHA256':H(A/'reconstructed-comparisons.json'),'counts':{'savedQueryCalls':4212,'changedBoundMisses':269,'projectionIdentical':60,'projectionDifferent':209,'successfulSubjects':538,'distinctSuccessfulSubjectProjections':747,'auditorNativeSSHCalls':0},'publishedInputReferencesRebound':publishedCount,'currentLogicalWorkDeltaByCapturedComparison':{k:{'queries':len(v),'sum':sum(v),'median':statistics.median(v),'min':min(v),'max':max(v)}for k,v in workgroups.items()},'logicalWorkScope':'Actual CQ-EXIT work minus CQ-ENTRY work for these current miss queries only; analysis work units, not time, avoided work, savings, downstream work or new skip.','checks':{'allPublishedRefsRegularExactBytes':True,'originalJournalsReparsedStrictEntryExitEdgeDimensions':True,'latestSameWorkloadActivationFunctionIncludingMemoHits':True,'independentOrderedTupleAndCanonicalCapturedBytesEquality':True,'all269ComparisonsAndPerWorkloadCountsExact':True,'emptyEdgesDuplicateRecordsOrderMinusOneZeroPreserved':True,'slreColdSupportDropExcludedNotAmongChangedBoundPairs':True,'sourcePrintFieldsMatchCapturedProjection':True},'limitations':['CQ-EDGE omits edge arity; CQ-EXIT omits summary/certificate controls9..14. No complete declared output role, ResultCID or read/input contract seal proven.','Written scratch/memo/aggregate state, trap/cleanup, dynamic read closure, allocation/IO and budget event order remain uncaptured.','60 identical captured projections are a prospective closed-role-shadow cohort only; no downstream stopping, production key exclusion, new skips, performance or C2 qualification.','Full binary M snapshot is exactly64MiB before framing; feasible file/buffer/journal implementation still requires separate review.'],'participation':'Independent saved-raw projection reviewer, not author of this projection analysis/census source and no new native execution.','fullResultCIDQualified':False,'productionReuseQualified':False,'performanceQualified':False,'newQuerySkips':0,'C2':False}
(A/'report.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'reportSHA256':H(A/'report.json'),'inputPinsSHA256':out['inputPinsSHA256'],'publishedInputs':publishedCount}))
