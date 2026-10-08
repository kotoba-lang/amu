"""Read/hash exact accepted actual285, bind full closure; no operational execution."""
from prepare import *
G=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-go-v2-root';A=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-actual-review-v2-independent'
def main():
 acceptance=ref(G/'functional285-acceptance.json');review=ref(A/'report.json');base=ref(A/'timing-nmax-baselines.json')
 assert acceptance['sha256']=='98f7a496cd85d7ba2bdb1bd090ebb29efd3224ce44299b103e68afac5c8218c0'
 assert review['sha256']=='ce0f24cf1fea99cbe94b0fbab995d1c1e19c843f08934f80d97f6e370d0600d6'
 assert base['sha256']=='f128d8777ab69450cf2e4ff359a0ce2bbc2c9892ba716644ab5269c5db9b297f'
 ac=load(acceptance['path']);rv=load(review['path']);baselines=load(base['path']);pr=load(D/'preregistration.json')
 assert ac['independentActualReceipt']==review and ac['timingNmaxBaselines']==base and ac['closedNativeAndCChildren']==285 and ac['nativeOFFLCPairs']==95 and ac['originalWorkloads']==19 and ac['functionalQualified']is True and ac['timingQualified']is False
 assert rv['allClosed']is True and rv['strict14FieldJSON']is True and rv['nativeSemanticFuelFourTerminalArenaParityExact']is True
 semantics={}
 for c,e in zip(baselines['cases'],pr['entries']):
  assert c['workload']==e['workload']and c['n']==e['n']and all(c[k]==e[k]for k in ['runner','C','header','OFF','LC']);semantics[c['workload']]={}
  for arm,role in [('baseline','OFF'),('candidate','LC'),('C','C')]:semantics[c['workload']][arm]={k:v for k,v in c['semantics'][role].items()if k not in ['calls','warmupCalls']}
 save('expected-semantics.json',semantics)
 for filename,path in [('fresh285-acceptance.json',acceptance['path']),('fresh285-independent-report.json',review['path']),('fresh285-nmax-baselines.json',base['path']),('fresh285-collection-receipt.json',G/'collected/collection-receipt.json')]: (D/filename).write_bytes(Path(path).read_bytes())
 local=load(D/'input-pins.json');remote=load(D/'remote-input-pins.json')
 # Merge every independent actual input, not just runtime artifacts or selected nmax.
 for path,r in load(A/'input-pins.json').items():assert {k:ref(path)[k]for k in ['bytes','sha256']}==r;local[path]=r
 for folder in (G,A):
  for p in folder.rglob('*'):
   if p.is_file()and '__pycache__'not in p.parts:r=ref(p);local[r.pop('path')]=r
 receipt=load(G/'collected/collection-receipt.json');assert len(receipt['members'])==600
 for m in receipt['members']:
  p=G/'collected'/m['path'];r=ref(p);assert {k:r[k]for k in ['bytes','sha256']}=={k:m[k]for k in ['bytes','sha256']};remote[receipt['root']+'/'+m['path']]={k:m[k]for k in ['bytes','sha256']}
 # Collector-generated top-level receipt is explicit byte-identical new SOURCE.
 remote[ROOT+'/source/fresh285-collection-receipt.json']={k:ref(D/'fresh285-collection-receipt.json')[k]for k in ['bytes','sha256']}
 save('input-pins.json',local);save('remote-input-pins.json',remote)
 binding=dict(calls=285,comparisons=95,workloads=19,independentlyAccepted=True,acceptance=acceptance,independentReview=review,baseline=base,sourcePinsSHA256=ac['sourcePinsSHA256'],localGOSHA256=ac['localGOSHA256'],remoteGOSHA256=ac['remoteGOSHA256'],semanticDefinition='Exact nmax accepted lastcall fields, remove only calls/warmupCalls from accepted12semantic fields; elapsed/maxRSS already excluded by auditor. Timing warmup1/everycall resets all4cursors+fuel same cb3f source.',all570RawStreamsAnd285ClosureRowsRetained=True)
 save('fresh285-binding.json',binding);pr.update(status='PROSPECTIVE_TIMING_SOURCE_ACTUAL285_BOUND_NO_GO',fresh285Acceptance=acceptance,fresh285IndependentReview=review,expectedSemantics=ref(D/'expected-semantics.json'),phaseBoundary='Operational diagnostic adapter now present; no main execution until exact frozen SOURCE/two SOURCE reviews/separate root GO. All prior failures preserved; no historical pool.',pending=['final SOURCE freeze','two independent final SOURCE reviews','separate exact root GO'],maximumInputFiles=8192,localClosureFiles=len(local),localClosureBytes=sum(r['bytes']for r in local.values()),remoteClosureFiles=len(remote),remoteClosureBytes=sum(r['bytes']for r in remote.values()))
 assert len(local)<=8192 and len(remote)<=8192 and pr['localClosureBytes']<=469762048 and pr['remoteClosureBytes']<=469762048
 save('preregistration.json',pr);role=load(D/'evidence-role-contract.json');role.update(prospectiveInputCountAmendment=dict(priorMaximum=4096,newMaximum=8192,reason='Retain full570 fresh285 raw streams+complete601 collectedmembers and independent proof inputs alongside original3953origins; no dropping',bytesMaximumUnchanged=469762048),actual285CollectorReceipt=dict(originalLocal=ref(G/'collected/collection-receipt.json'),remoteSource=ROOT+'/source/fresh285-collection-receipt.json',role='Collector synthetic generated receipt transported byte-identical SOURCE; never guessed old remote origin'),timingCollectionLimits=dict(regularMembers=65536,regularFileBytes=16777216,expandedFileBytes=805306368,USTARBytes=872415232,compressedBytes=872415232,sourceAndControlIncluded=True));save('evidence-role-contract.json',role)
 print(json.dumps(dict(localFiles=len(local),localBytes=pr['localClosureBytes'],remoteFiles=len(remote),remoteBytes=pr['remoteClosureBytes'],fresh285Accepted=True,finalFreeze=False,operationalCalls=0)))
if __name__=='__main__':main()
