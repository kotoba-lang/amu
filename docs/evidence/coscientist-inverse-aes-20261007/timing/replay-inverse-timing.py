"""Stdlib-only offline data verifier; never compiles/runs guests or invokes network/solver."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,contextlib,io,math,re
HERE=Path(__file__).resolve().parent
MANIFEST_SHA='64202e1108ad7ec932339bec6f9665ef32313154063923d00b3b6bd3863d64d3'
sha=lambda b:hashlib.sha256(b).hexdigest()
def ld(p):return json.loads(p.read_text())
def main():
 mpath=HERE/'inverse-timing-manifest.json';assert sha(mpath.read_bytes())==MANIFEST_SHA,'manifest envelope integrity';m=ld(mpath);arc=HERE/m['archive'];assert sha(arc.read_bytes())==m['archiveSHA256'] and arc.stat().st_size==m['archiveBytes'],'archive envelope integrity'
 assert m['logicalMembers']==len(m['members'])<=2000
 with tempfile.TemporaryDirectory(prefix='amu-offline-inverse-timing-') as d:
  root=Path(d);objects={}
  with tarfile.open(arc,'r:gz') as t:
   for item in t:
    assert item.isfile() and item.name.startswith('objects/') and len(item.name)==72 and item.size<=150000000
    h=item.name[8:];assert h not in objects;data=t.extractfile(item).read();assert len(data)==item.size and sha(data)==h;objects[h]=data
  assert len(objects)==m['uniqueByteObjects']
  for n,v in m['members'].items():
   path=PurePosixPath(n);assert not path.is_absolute() and '..'not in path.parts;data=objects[v['sha256']];assert len(data)==v['bytes'];p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  independent=root/m['independentReport'];original=ld(independent)
  script=(independent.parent/'review.py').read_text()
  before="for p,h in ld(D/'preregistration.json')['inputs'].items():assert sha(Path(p))==h,p"
  assert script.count(before)==1;script=script.replace(before,"for p,h in ld(D/'preregistration.json')['inputs'].items():assert sha(W/Path(p).relative_to(ORIGIN))==h,p")
  # The selected immutable review performs only JSON/hash/statistics reads;
  # its final report is written inside this disposable offline directory.
  with contextlib.redirect_stdout(io.StringIO()):exec(compile(script,'frozen-offline-timing-review','exec'),{'__file__':str(independent.parent/'review.py'),'ORIGIN':Path(m['origin'])})
  rebuilt=ld(independent);assert rebuilt==original,'independent full19 raw/statistics replay mismatch'
  sem=root/'root/remote57-semantic';entries=ld(root/'root/remote57-built/report.json')['entries'];by={r['workload']:r for r in entries}
  for n,h in ld(sem/'pins.json').items():assert sha((sem/n).read_bytes())==h
  package=root/'team-remote57-inverse-prep/sealed-envelope/package'
  cp=ld(root/'team-inverse-campaign-prep/current-input-binding.json')['packagePins']
  for n,h in cp.items():assert sha((package/n).read_bytes())==h,n
  for r in entries:
   p=package/r['workload'];header=(p/'immutable-header.h').read_text();assert sha(header.encode())==r['immutableHeaderSHA256']
   assert sha((p/'source.kotoba').read_bytes())==r['sourceSHA256'] and sha((package/'timing-host.c').read_bytes())==r['hostSourceSHA256']
   assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL' in header and '#define KEXE_EMBEDDED_ISA "aarch64"' in header
   for label,file in [('known_baseline','baseline.bin'),('known_candidate','candidate.bin'),('timing_known_c_bytes','c.dylib')]:
    match=re.search(r'static const unsigned char '+label+r'\[\] = \{([^}]*)\}',header)
    assert match and bytes(int(x) for x in match[1].split(',') if x.strip())==(p/file).read_bytes()
   assert 'timing_known_offsets[] = {'+str(r['baselineOffset'])+','+str(r['candidateOffset'])+'};' in header
   assert '#define TIMING_KNOWN_C_SYMBOL "'+r['Csymbol']+'"' in header
  attempts=ld(sem/'attempts.json');assert len(attempts)==57;seen=set()
  for a in attempts:
   name,arm=a['workload'],a['arm'];assert (name,arm)not in seen;seen.add((name,arm));r=by[name];p=sem/(name+'-'+arm+'.json');assert sha(p.read_bytes())==a['receiptSHA256'];raw=ld(p);q=json.loads(raw['stdout']);assert a['state']=='terminal' and raw['exit']==0 and not raw['stderr'] and raw['diagnosticElapsedNotStatistics']
   assert q['result']==1 and q['calls']==1 and q['warmupCalls']==0 and q['fuelPerCall']==16777216 and a['n']==r['n']
   used=0 if arm=='C' else r['expectedNativeFuelConsumed'];assert q['contextFuelBefore']==16777216 and q['contextFuelConsumed']==used and q['contextFuelAfter']==16777216-used
   assert raw['argv'][-5:]==['aarch64',str(r['n']),'1','0','16777216']
  assert len(seen)==57 and ld(sem/'report.json')['calls']==57
  decision=ld(root/'root/inverse-campaign-stage-decision.json');assert decision['independentReviewSHA256']==sha(json.dumps(original,indent=2).encode()+b'\n')
  for k in ['qualifiedGains','qualifiedRegressions']:assert decision[k]==original[k]
  assert decision['qualifiedCWins']==original['qualifiedCOrBetter'] and not decision['goalAchieved'] and not decision['productAdopted'] and not decision['officialEmbenchScore']
  print(json.dumps({'status':'PASS copied3file offline ONE inverse campaign and57semantic','logicalMembers':len(m['members']),'uniqueByteObjects':len(objects),'semanticCalls':57,'runnerProcesses':original['runnerProcesses'],'calibrationProcesses':original['calibrationProcesses'],'attemptedTriples':original['attemptedTriples'],'acceptedTriples':original['acceptedTriples'],'rejectedTriples':original['rejectedTriples'],'qualifiedGains':original['qualifiedGains'],'qualifiedRegressions':original['qualifiedRegressions'],'qualifiedCOrBetter':original['qualifiedCOrBetter'],'descriptiveBaselineOverCandidate':original['descriptiveGeometricBaselineOverCandidate'],'descriptiveCandidateOverC':original['descriptiveGeometricCandidateOverC'],'nativeNetworkSolverTimingRuns':0,'officialScore':False,'productAdopted':False},indent=2))
if __name__=='__main__':main()
