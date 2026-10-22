from pathlib import Path
import json,statistics,math,hashlib
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-clamp-call-20261005');p=w/'timing-package/picojpeg/timing/results.json';t=json.loads(p.read_text());e=json.loads((p.parent.parent/'baseline/results.json').read_text())['entries'][0];spec=json.loads((r/'bench/embench/paired-timing-spec.json').read_text());accepted=[x for x in t['rows'] if x['accepted']]
assert len(accepted)==90 and t['acceptedTriples']==30 and t['attemptedTriples']<=spec['maximumPairAttempts'];assert t['runnerSha256']=='a1b8778cf9af255f66bba3e3cad20e3baadd9653e18defe429bfa179840665ac'
for i in range(t['attemptedTriples']):
 trio=[x for x in t['rows'] if x['attempt']==i];assert len(trio)==3 and len(set(x['accepted'] for x in trio))==1
 assert [x['arm'] for x in trio]==(['baseline','candidate','C']*2)[i%3:i%3+3]
 for x in trio:
  reasons=[]
  if max(x['loadBefore'],x['loadAfter'])>spec['maximumLoad']:reasons.append('host-load')
  if x['elapsedNanoseconds']<spec['minimumIntervalNs']:reasons.append('short-interval')
  if x['cpuActivityEnvelope']['estimatedBackgroundIdlePercent']<spec['minimumBackgroundIdlePercent']:reasons.append('background-cpu')
  assert reasons==x['rejectionReasons']
 assert trio[0]['accepted']==all(not x['rejectionReasons'] for x in trio)
for arm in ['baseline','candidate','C']:
 xs=[x['elapsedNanoseconds']/(x['calls']*e['iterationsPerCall']) for x in accepted if x['arm']==arm];s=t['summary'][arm];assert len(xs)==30 and math.isclose(statistics.mean(xs),s['meanNsPerBody'],rel_tol=1e-12) and math.isclose(statistics.stdev(xs),s['sdNs'],rel_tol=1e-12)
b=t['summary']['baseline'];c=t['summary']['candidate'];stable=max(t['summary'][a]['relativeSd'] for a in ['baseline','candidate','C'])<=spec['maximumRelativeSd'];gap=b['meanNsPerBody']-c['meanNsPerBody'];sd=b['sdNs']+c['sdNs'];win=stable and b['meanNsPerBody']/c['meanNsPerBody']>=spec['minimumSpeedup'] and gap>sd;assert win==t['summary']['candidateImprovesBaseline'] and win
proof=json.loads((w/'ports-correctness.json').read_text());base=json.loads((w/'timing-package/product-proof.json').read_text());mf=json.loads((w/'timing-package/picojpeg/candidate/manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(w/'timing-package/picojpeg/candidate/native.bin')==mf['nativeSha256']==next(x['nativeSha256'] for x in proof['entries'] if x['workload']=='picojpeg');assert sha(w/'timing-package/picojpeg/baseline-native.bin')==mf['baselineNativeSha256']==next(x['nativeSha256'] for x in base['entries'] if x['workload']=='picojpeg')
rows=json.loads((w/'code-change.json').read_text());assert len(rows)==19 and [x['workload'] for x in rows if x['changed']]==['picojpeg']
out={'status':'complete-independent-row-and-pin-audit','acceptedTriples':30,'attemptedTriples':t['attemptedTriples'],'qualifies':win,'savedTimeFraction':gap/b['meanNsPerBody'],'meanGapNs':gap,'summedSdNs':sd,'eighteenOtherGuestBinariesByteIdentical':True,'summary':t['summary'],'officialEmbenchScore':False,'COrBetter':False};(w/'timing-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
