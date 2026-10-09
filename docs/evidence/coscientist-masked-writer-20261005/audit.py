from pathlib import Path
import json,statistics,math,hashlib
w=Path('/private/tmp/amu-masked-writer-20261005'); r=Path('/Users/junkawasaki/github/wt/amu-seed17'); d=r/'docs/evidence/coscientist-masked-writer-20261005';spec=json.loads((r/'bench/embench/paired-timing-spec.json').read_text());out=[]
for p in sorted((w/'remote-timing').glob('*/timing/results.json')):
 t=json.loads(p.read_text());e=json.loads((p.parent.parent/'baseline/results.json').read_text())['entries'][0];rows=t['rows'];accepted=[x for x in rows if x['accepted']]
 assert len(accepted)==90 and t['acceptedTriples']==30
 assert t['runnerSha256']=='a1b8778cf9af255f66bba3e3cad20e3baadd9653e18defe429bfa179840665ac'
 for i in range(t['attemptedTriples']):
  trio=[x for x in rows if x['attempt']==i];assert len(trio)==3 and len(set(x['accepted'] for x in trio))==1
  assert [x['arm'] for x in trio]==(['baseline','candidate','C']*2)[i%3:i%3+3]
  for x in trio:
   reasons=[]
   if max(x['loadBefore'],x['loadAfter'])>spec['maximumLoad']:reasons.append('host-load')
   if x['elapsedNanoseconds']<spec['minimumIntervalNs']:reasons.append('short-interval')
   if x['cpuActivityEnvelope']['estimatedBackgroundIdlePercent']<spec['minimumBackgroundIdlePercent']:reasons.append('background-cpu')
   assert x['rejectionReasons']==reasons
  assert trio[0]['accepted']==all(not x['rejectionReasons'] for x in trio)
 for arm in ['baseline','candidate','C']:
  xs=[x['elapsedNanoseconds']/(x['calls']*e['iterationsPerCall']) for x in accepted if x['arm']==arm];s=t['summary'][arm]
  assert len(xs)==30 and math.isclose(statistics.mean(xs),s['meanNsPerBody'],rel_tol=1e-12) and math.isclose(statistics.stdev(xs),s['sdNs'],rel_tol=1e-12)
 b=t['summary']['baseline'];c=t['summary']['candidate'];stable=max(t['summary'][a]['relativeSd'] for a in ['baseline','candidate','C'])<=spec['maximumRelativeSd']; win=stable and b['meanNsPerBody']/c['meanNsPerBody']>=spec['minimumSpeedup'] and b['meanNsPerBody']-c['meanNsPerBody']>b['sdNs']+c['sdNs'];assert t['summary']['candidateImprovesBaseline']==win
 out.append({'workload':e['workload'],'accepted':30,'attempts':t['attemptedTriples'],'recomputedConditionsMeansSd':True,'qualifyingImprovement':win,'separatedRegression':c['meanNsPerBody']-b['meanNsPerBody']>b['sdNs']+c['sdNs']})
assert [x['workload'] for x in out]==['picojpeg']
(d/'timing-audit.json').write_text(json.dumps({'status':'complete-independent-changed-workload-row-and-pin-audit','acceptedTriples':sum(x['accepted'] for x in out),'attemptedTriples':sum(x['attempts'] for x in out),'rows':out},indent=2)+'\n')
files=sorted(p for p in d.iterdir() if p.is_file() and p.name!='checksums.sha256');(d/'checksums.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files));print('PASS independent changed-workload audit')
