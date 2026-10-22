#!/usr/bin/env python3
"""Stdlib-only offline replay. Run beside its manifest and archive; never executes a guest."""
from pathlib import Path, PurePosixPath
import json,hashlib,tarfile,tempfile,math,re,sys,statistics
BASE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
near=lambda a,b:math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-8)
def safe_name(s):
 p=PurePosixPath(s)
 assert s and not p.is_absolute() and '..' not in p.parts and str(p)==s,s
 return s
def extract_verified(directory):
 m=load(BASE/'resident-fuel-timing-manifest.json');assert m['format']=='amu.resident-fuel-timing-portable/v1';assert m['replayFile']==Path(__file__).name and sha(Path(__file__))==m['replaySHA256'],'reader hash'
 assert m['memberCount']==len(m['members'])<=2000
 assert m['uncompressedBytes']==sum(v['bytes'] for v in m['members'].values())<=m['maximumUncompressedBytes']==134217728
 archive=BASE/safe_name(m['archive']);assert archive.stat().st_size==m['archiveBytes'] and sha(archive)==m['archiveSHA256'],'archive envelope mismatch'
 seen=set()
 with tarfile.open(archive,'r:gz') as t:
  for member in t:
   name=safe_name(member.name);assert name not in seen and member.isfile() and not member.issym() and not member.islnk() and name in m['members'],'unsafe/unlisted member'
   seen.add(name);v=m['members'][name];assert member.size==v['bytes'];data=t.extractfile(member).read(member.size+1);assert len(data)==member.size and hashlib.sha256(data).hexdigest()==v['sha256'],'member hash'
   target=directory/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 assert seen==set(m['members']),'missing archive member'
 return m

def check_envelopes(H,m):
 W=H/'team-timing';E=W/'remote-campaign-evidence'
 def origin(p):
  if str(p).startswith(m['originRoot']+'/'):p=H/str(p)[len(m['originRoot'])+1:]
  else:p=Path(p)
  if not p.exists() and p.is_relative_to(W/'timing-package'):p=E/p.relative_to(W/'timing-package')
  return p
 for fn in ['campaign-artifact-pins.json','post57-artifact-pins.json']:
  pins=load(W/fn)
  for rel,v in pins.items():
   p=origin(rel) if Path(rel).is_absolute() else W/rel
   assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],rel
 assert len(load(W/'campaign-artifact-pins.json'))==525 and len(load(W/'post57-artifact-pins.json'))==484
 for fn in ['campaign-terminal-report.json','post57-terminal-report.json']:
  t=load(W/fn);assert sha(W/t['report'])==t['reportSHA256'] and sha(W/t['artifactPins'])==t['artifactPinsSHA256'];assert t['allWritesComplete']
 for fn in ['remote-campaign-run.json','campaign-collect.json','remote-semantic-run.json','remote-collect.json']:
  assert load(W/fn)['exit']==0
 prereg=load(W/'preregistration.json');assert sha(W/'preregistration.json')==m['members']['team-timing/preregistration.json']['sha256']
 assert not prereg.get('performanceAuthorized',False)
 D=H/'team-timing-audit-independent'
 for rel,h in load(D/'preregistration.json')['inputs'].items():assert sha(origin(rel))==h
 t=load(D/'terminal-report.json')
 # Independent receipts use their own schema, preserved as original records.
 for p,h in load(D/'artifact-pins.json').items():
  target=D/p;assert sha(target)==(h['sha256'] if isinstance(h,dict) else h)
 return W,E

def check_admission_and_semantics(E):
 spec=load(E/'paired-timing-spec.json');feature=load(E/'fresh-remote-feature.json')['fields']
 assert feature['architecture']['exit']==feature['AES']['exit']==0 and feature['architecture']['stdout'].strip()=='arm64' and feature['AES']['stdout'].strip()=='1'
 assert feature['host']['stdout'].strip().split('.')[0]==spec['host'] and feature['model']['stdout'].strip()=='Mac16,10'
 assert sha(E/'timing-host.c')=='39cdbfa14ace3196029c5f1d50be8d2a1200d7aa9ab3c08d2435837e23b752eb'
 manifest=load(E/'compiled-manifest.json');entries=manifest['entries'];assert len(entries)==19 and manifest['allThreeArmsSamePerWorkloadRunner']
 semantic=load(E/'semantic-preflight.json');assert semantic['calls']==57 and semantic['performanceCalls']==0 and len(semantic['entries'])==19
 seen=set();changed=[]
 for e,s in zip(entries,semantic['entries']):
  name=e['workload'];d=E/name;assert s['workload']==name and s['n']==e['n'] and s['expectedNativeFuel']==e['expectedNativeFuelConsumed']
  assert sha(d/'source.kotoba')==e['sourceSHA256'] and sha(d/'runner')==e['runnerSHA256'] and sha(d/'immutable-header.h')==e['immutableHeaderSHA256']
  assert sha(d/'baseline.bin')==e['baselineNativeSHA256'] and sha(d/'candidate.bin')==e['candidateNativeSHA256'] and sha(d/'c.dylib')==e['CbinarySHA256']
  assert e['requiredMask']==6 and e['hostSourceSHA256']==sha(E/'timing-host.c') and load(d/'input-manifest.json')==e
  header=(d/'immutable-header.h').read_text()
  def array(n):
   hit=re.search(r'\b'+n+r'\[\]\s*=\s*\{([^}]*)\};',header);assert hit,n
   return [int(x.strip()) for x in hit[1].split(',') if x.strip()]
  for key,file in [('known_baseline','baseline.bin'),('known_candidate','candidate.bin'),('timing_known_c_bytes','c.dylib')]:assert bytes(array(key))==(d/file).read_bytes()
  assert array('timing_known_sizes')==[(d/'baseline.bin').stat().st_size,(d/'candidate.bin').stat().st_size]
  assert array('timing_known_offsets')==[e['baselineOffset'],e['candidateOffset']]
  assert 'timing_known_images[] = {known_baseline,known_candidate}' in header
  assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL' in header and '#define KEXE_EMBEDDED_ISA "aarch64"' in header and '#define TIMING_KNOWN_DYLIB 1' in header
  assert '#define TIMING_KNOWN_C_SYMBOL '+json.dumps(e['Csymbol']) in header
  for off,file in [(e['baselineOffset'],'baseline.bin'),(e['candidateOffset'],'candidate.bin')]:assert off%4==0 and 0<=off<=(d/file).stat().st_size-4
  if e['baselineNativeSHA256']!=e['candidateNativeSHA256']:changed.append(name)
  assert [a['arm'] for a in s['arms']]==['baseline','candidate','C']
  for a in s['arms']:
   arm=a['arm'];assert (name,arm) not in seen;seen.add((name,arm));assert load(d/('semantic-'+arm+'.json'))==a and a['exit']==0 and a['stderr']=='' and a['diagnosticElapsedNotStatistics']
   v=json.loads(a['stdout']);fuel=0 if arm=='C' else e['expectedNativeFuelConsumed'];assert v['result']==1 and v['calls']==1 and v['warmupCalls']==0
   assert v['fuelPerCall']==v['contextFuelBefore']==16777216 and v['contextFuelConsumed']==fuel and v['contextFuelAfter']==16777216-fuel and v['artifactKind']==('dylib' if arm=='C' else 'raw')
   assert v['format']=='kotoba.runtime-sample/v1' and v['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1'
 assert len(seen)==57 and changed==['nettle-aes']
 return changed

def audit(H,W,E):
    D=H/'team-timing-audit-independent'
    spec=load(E/'paired-timing-spec.json');go=load(E/'ROOT-GO.json');assert go==load(H/'root/ROOT-GO.json') and go['performanceAuthorized'];assert go['preregistrationSHA256']==sha(E/'preregistration.json') and go['packageInputPinsSHA256']==sha(E/'package-input-pins.json') and go['remoteSemanticReportSHA256']==sha(E/'semantic-preflight.json')
    for f,h in load(E/'package-input-pins.json').items():assert sha(E/f)==h,f
    for f,h in load(W/'post57-artifact-pins.json').items():assert sha(W/f)==h['sha256'] and (W/f).stat().st_size==h['bytes'],f
    sem=load(E/'semantic-preflight.json');assert sem['calls']==57 and sem['performanceCalls']==0
    campaign=load(E/'campaign.json');assert campaign['status']=='terminal-onecampaign all19 attempted';entries=load(E/'compiled-manifest.json')['entries'];assert len(entries)==len(campaign['entries'])==19
    arms=['baseline','candidate','C'];out=[];totals={'acceptedTriples':0,'attemptedTriples':0,'rejectedTriples':0,'rawAttemptRows':0,'calibrationRows':0};allcomplete=True
    for entry,terminal in zip(entries,campaign['entries']):
     name=entry['workload'];assert terminal['workload']==name;p=E/name;q=load(p/'timing/results.json');assert q['host'].split('.')[0]==spec['host'] and q['specSha256']==sha(E/'paired-timing-spec.json') and q['runnerSha256']==entry['runnerSHA256']==sha(p/'runner');assert q['manifest']==load(p/'candidate/manifest.json') and q['baselineResultsSha256']==sha(p/'baseline/results.json')
     def value(row):
      arm=row['arm'];assert arm in arms;assert type(row['elapsedNanoseconds']) is int and row['elapsedNanoseconds']>0 and type(row['calls']) is int and 0<row['calls']<=100000000 and row['warmupCalls']==spec['warmupCalls'] and row['result']==1
      f=0 if arm=='C' else entry['expectedNativeFuelConsumed'];assert row['fuelPerCall']==row['contextFuelBefore']==16777216 and row['contextFuelConsumed']==f and row['contextFuelAfter']==16777216-f and row['artifactKind']==('dylib' if arm=='C' else 'raw')
      assert row['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1' and row['format']=='kotoba.runtime-sample/v1'
     # Reconstruct calibration exactly from freshretained armsequence, no history.
     calibration=q.get('calibrationRows',[]);counts={};cursor=0
     for arm in arms:
      calls=3;converged=False
      for i in range(5):
       if cursor==len(calibration):break
       row=calibration[cursor]
       if row['arm']!=arm:break
       cursor+=1;value(row);assert row['calls']==calls and row['calibrationAttempt']==i
       elapsed=row['elapsedNanoseconds']
       if spec['targetIntervalNs']*.75<=elapsed<=spec['targetIntervalNs']*1.5:converged=True;counts[arm]=calls;break
       calls=max(1,min(100000000,round(calls*spec['targetIntervalNs']/elapsed)))
      if not converged:assert q['status']=='failed';break
     assert cursor==len(calibration)
     totals['calibrationRows']+=len(calibration)
     rows=q['rows'];assert len(rows)%3==0 and len(rows)//3<=spec['maximumPairAttempts'];accepted=0;reasonCounts={};xs={a:[] for a in arms}
     for attempt in range(len(rows)//3):
      group=rows[attempt*3:attempt*3+3];assert [r['arm'] for r in group]==arms[attempt%3:]+arms[:attempt%3];quiet=True
      for r in group:
       value(r);assert r['attempt']==attempt and r['calls']==counts[r['arm']]
       c=r['cpuActivityEnvelope'];before=c['before'];after=c['after'];assert before['processors']==after['processors'] and before['api']==after['api']=='host_processor_info/PROCESSOR_CPU_LOAD_INFO';assert after['monotonicNs']>before['monotonicNs']
       for point in [before,after]:assert len(point['ticks'])==4 and all(type(v)is int and 0<=v<=0xffffffff for v in point['ticks'])
       delta=[(b-a)&0xffffffff for a,b in zip(before['ticks'],after['ticks'])];assert delta==c['deltaTicks'];total=sum(delta);assert total>0;idle=100*delta[2]/total;envelope=after['monotonicNs']-before['monotonicNs'];assert near(idle,c['idlePercent']) and envelope==c['envelopeNs'];assert type(c['childCpuNs'])is int and c['childCpuNs']>=0 and type(c['logicalCpuCount'])is int and c['logicalCpuCount']>0
       child=100*c['childCpuNs']/(envelope*c['logicalCpuCount']);assert child<=100;bg=min(100,idle+child);assert near(bg,c['estimatedBackgroundIdlePercent'])
       assert envelope>=r['elapsedNanoseconds'];assert math.isfinite(r['loadBefore']) and math.isfinite(r['loadAfter']) and r['loadBefore']>=0 and r['loadAfter']>=0
       reasons=[]
       if max(r['loadBefore'],r['loadAfter'])>spec['maximumLoad']:reasons.append('host-load')
       if r['elapsedNanoseconds']<spec['minimumIntervalNs']:reasons.append('short-interval')
       if bg<spec['minimumBackgroundIdlePercent']:reasons.append('background-cpu')
       assert reasons==r['rejectionReasons'];quiet&=not reasons
       for reason in reasons:reasonCounts[reason]=reasonCounts.get(reason,0)+1
      for r in group:assert r['accepted']==quiet
      accepted+=int(quiet)
      if quiet:
       for r in group:xs[r['arm']].append(r['elapsedNanoseconds']/(r['calls']*entry['n']))
      if accepted==spec['samplesPerArm']:assert attempt==len(rows)//3-1
     assert q.get('acceptedTriples',0)==accepted and q.get('attemptedTriples',0)==len(rows)//3
     totals['acceptedTriples']+=accepted;totals['attemptedTriples']+=len(rows)//3;totals['rejectedTriples']+=len(rows)//3-accepted;totals['rawAttemptRows']+=len(rows)
     complete=q['status']=='complete-provisional-candidate-timing' and accepted==30 and len(counts)==3;allcomplete&=complete
     rowout={'workload':name,'status':q['status'],'acceptedTriples':accepted,'attemptedTriples':len(rows)//3,'rejectedTriples':len(rows)//3-accepted,'calibrationRows':len(calibration),'rejectionReasonRows':reasonCounts,'rawSha256':sha(p/'timing/results.json'),'complete':complete}
     if complete:
      assert terminal['exit']==0 and q['performanceMeasured'] and q['officialEmbenchScore']==False
      summary={}
      for a in arms:
       mu=statistics.mean(xs[a]);sd=statistics.stdev(xs[a]);summary[a]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu,'samples':len(xs[a])}
       for k,v in summary[a].items():assert near(v,q['summary'][a][k]),(name,a,k,v,q['summary'][a][k])
      b=summary['baseline'];c=summary['candidate'];ref=summary['C'];stable=max(x['relativeSd'] for x in summary.values())<=spec['maximumRelativeSd'];speed=b['meanNsPerBody']/c['meanNsPerBody'];ratio=c['meanNsPerBody']/ref['meanNsPerBody'];gain=stable and speed>=spec['minimumSpeedup'] and b['meanNsPerBody']-c['meanNsPerBody']>b['sdNs']+c['sdNs'];regression=stable and 1/speed>=spec['minimumSpeedup'] and c['meanNsPerBody']-b['meanNsPerBody']>b['sdNs']+c['sdNs'];cbetter=stable and 1/ratio>=spec['minimumSpeedup'] and ref['meanNsPerBody']-c['meanNsPerBody']>ref['sdNs']+c['sdNs']
      assert stable==q['summary']['stable'] and near(speed,q['summary']['baselineOverCandidate']) and near(ratio,q['summary']['candidateOverC']) and gain==q['summary']['candidateImprovesBaseline'];assert terminal['summary']==q['summary']
      rowout.update(summary=summary,stable=stable,baselineOverCandidate=speed,candidateOverC=ratio,qualifiedGain=gain,qualifiedRegression=regression,qualifiedCOrBetter=cbetter,classification='gain' if gain else 'regression' if regression else 'neutral' if stable else 'unstable')
     else:assert terminal['status']==q['status'];rowout['failure']=q.get('failure');rowout['classification']='incomplete';assert 'summary' not in q
     out.append(rowout)
    aggregate=None
    if allcomplete:
     gm=lambda vs:math.exp(statistics.mean(math.log(v) for v in vs));speed=gm([r['baselineOverCandidate'] for r in out]);aggregate={'baselineOverCandidateGeometricMean':speed,'candidateRelativeTimePercent':100*(1/speed-1),'candidateOverCGeometricMean':gm([r['candidateOverC'] for r in out]),'baselineOverCGeometricMean':gm([r['baselineOverCandidate']*r['candidateOverC'] for r in out]),'descriptiveOnly':True,'all19Stable':all(r['stable'] for r in out)}
    result={'status':'PASS independent raw audit complete19' if allcomplete else 'PASS independent raw audit with partialcampaign; nofull19aggregate','all19Complete':allcomplete,'rawRowsTotals':totals,'entries':out,'aggregate':aggregate,'qualifiedGains':[r['workload'] for r in out if r.get('qualifiedGain')],'qualifiedRegressions':[r['workload'] for r in out if r.get('qualifiedRegression')],'qualifiedCOrBetter':[r['workload'] for r in out if r.get('qualifiedCOrBetter')],'goalAchieved':False,'officialScore':False,'productAdoption':False,'ownGuestCalls':0,'ownNetworkAttempts':0,'ownTimingRuns':0,'trustBoundary':'Offline checks parse retained runner samples and CPUfields; trusted frozen source/producer/OS. Child CPU share reconstructed from recordedns, not independently remeasured. No rawhardwarecounter/trace universalproof.'};return result

def finish(H,m,result,changed):
 expected=m['expected'];assert result['all19Complete'] and result['rawRowsTotals']=={'acceptedTriples':570,'attemptedTriples':687,'rejectedTriples':117,'rawAttemptRows':2061,'calibrationRows':145}
 assert result['qualifiedGains']==expected['qualifiedGains']==['nettle-aes'] and result['qualifiedRegressions']==expected['qualifiedRegressions']==[] and result['qualifiedCOrBetter']==expected['qualifiedCOrBetter']==[]
 assert result['aggregate']['all19Stable']==expected['all19Stable']==True
 frozen=load(H/'team-timing-audit-independent/report.json')
 for x,y in zip(result['entries'],frozen['entries']):
  assert x['workload']==y['workload'] and x['classification']==y['classification']
  for arm in ['baseline','candidate','C']:
   for k,v in x['summary'][arm].items():assert near(v,y['summary'][arm][k])
  for k in ['baselineOverCandidate','candidateOverC']:assert near(x[k],y[k])
 decision=load(H/'root/performance-decision.json');assert not decision['productAdoption'] and not decision['officialScore'] and not decision['goalAchieved'] and not decision['full19CompilerGainClaim']
 aes=next(x for x in result['entries'] if x['workload']=='nettle-aes')
 assert near(decision['qualifiedAESBaselineOverCandidate'],aes['baselineOverCandidate']) and near(decision['AESOverC'],aes['candidateOverC'])
 assert near(decision['full19BaselineOverCandidate'],result['aggregate']['baselineOverCandidateGeometricMean']) and near(decision['full19CandidateOverC'],result['aggregate']['candidateOverCGeometricMean'])
 assert changed==['nettle-aes'] and all(not z for z in [result['goalAchieved'],result['officialScore'],result['productAdoption']])
 return {'status':'PASS portable offline full19 timing and57 semantics','memberCount':m['memberCount'],'semanticCalls':57,'attemptedTriples':687,'acceptedTriples':570,'rejectedTriples':117,'calibrationRows':145,'rawAttemptRows':2061,'qualifiedGains':result['qualifiedGains'],'qualifiedRegressions':[],'candidateBetterThanC':[],'AESBaselineOverCandidate':aes['baselineOverCandidate'],'AESOverC':aes['candidateOverC'],'aggregate':result['aggregate'],'allThreeArmsSameFrozenRunner':True,'nativeBytesChanged':changed,'productAdoption':False,'officialScore':False,'goalAchieved':False,'ownNativeCalls':0,'ownTimingRuns':0,'trustBoundary':m['trustBoundary']}

def main():
 with tempfile.TemporaryDirectory(prefix='amu-rf-timing-offline-') as temporary:
  H=Path(temporary);m=extract_verified(H);W,E=check_envelopes(H,m);changed=check_admission_and_semantics(E);result=audit(H,W,E);print(json.dumps(finish(H,m,result,changed),indent=2))
if __name__=='__main__':main()
