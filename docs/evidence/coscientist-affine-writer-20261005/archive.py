from pathlib import Path
import json,hashlib,tarfile,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');d=r/'docs/evidence/coscientist-affine-writer-20261005';d.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary={'status':'complete-two-rejected-native-affine-write-experiments','sourceHeadBefore':'dbb707465fd8d8768edd5b1110828193214cbad4','productChanged':False,'fullReleaseGateClaim':False,'officialEmbenchScore':False,'COrBetter':False,'variants':[]}
common=['create.py','build.py','seed-unity.kotoba','seed-0.bin','seed-0.offset','seed-4.bin','seed-4.offset','41-a64gen-prototype.kotoba','baseline-41-a64gen.kotoba','baseline-a64gen-fixtures.py','generations.json','hypothesis.json','inspected-sir.json','check-ports.py','ports-correctness.json','code-change.json','bulk-state.py','bulk-state.json','picojpeg-state-observer.kotoba','bulk-baseline','bulk-candidate','fixture-proof.py','fixture-proof.json','candidate-test.stdout','candidate-real.stdout','baseline-real.stdout','fixture-candidate-code.bin','fixture-baseline-code.bin','import-proof.py','import-proof.json','baseline-open.stdout','candidate-open.stdout','candidate-closed.stdout','baseline-open-linked.bin','candidate-open-linked.bin','candidate-closed-linked.bin','kexe-loader']
for name,path in [('staged','amu-affine-writer-20261005'),('direct','amu-affine-writer-direct-20261005')]:
 w=Path('/private/tmp')/path;fp=json.loads((w/'fixture-proof.json').read_text());tp=json.loads((w/'timing-audit.json').read_text());ip=json.loads((w/'import-proof.json').read_text());assert not tp['qualifies'] and ip['status']=='complete-affine-import-substitution-refusal'
 assert (w/'baseline-41-a64gen.kotoba').read_bytes()==(r/'seed/41-a64gen.kotoba').read_bytes()
 if name=='direct':assert len(json.loads((w/'fallback-audit.json').read_text())['unchangedFallbacks'])==23
 entry={'variant':name,'decision':'reject-performance-promotion','hypothesis':json.loads((w/'hypothesis.json').read_text()),'generations':json.loads((w/'generations.json').read_text()),'timing':tp,'nativeProof':{k:fp[k] for k in ['status','fixtures','canonicalRuns','realTestLayoutIdentical','supervisorComparisons']},'importSubstitutions':len(ip['runs']),'workspace':json.loads((w/'bulk-state.json').read_text()),'codeChanges':json.loads((w/'code-change.json').read_text()),'prototypeSha256':sha(w/'41-a64gen-prototype.kotoba'),'producerSha256':sha(w/'seed-0.bin'),'qualificationOrdering':'Measurement preflight preceded completion of full supervisor proof. Original preflight metadata retained; final proof completed independently. No promotion.'}
 if name=='direct':entry['fallbackAudit']=json.loads((w/'fallback-audit.json').read_text())
 summary['variants'].append(entry)
 q=subprocess.run(['git','diff','--no-index',str(w/'baseline-41-a64gen.kotoba'),str(w/'41-a64gen-prototype.kotoba')],capture_output=True,text=True);assert q.returncode==1;(d/(name+'-prototype.diff')).write_text(q.stdout)
 (d/(name+'-timing-audit.json')).write_bytes((w/'timing-audit.json').read_bytes())
 with tarfile.open(d/(name+'-native-proof.tgz'),'w:gz') as t:
  fs=common+(['inspect.py','dump.kotoba','sir.log'] if name=='staged' else ['fallback-audit.py','fallback-audit-original.py','fallback-audit-original-failure.txt','fallback-audit.json'])
  for f in fs:t.add(w/f,arcname=f)
  for f in ['seed/SIR','seed/HEADS','seed/MEMORY-MAP']:t.add(r/f,arcname=f)
  for f in ['clobber-state-loader.c','clobber-state-loader']:t.add(Path('/private/tmp/amu-context-call-20261005')/f,arcname='diagnostic/'+f)
 with tarfile.open(d/(name+'-timing.tgz'),'w:gz') as t:
  for f in ['prepare-timing.py','remote-all.py','timing-package','all-summary.json','audit.py','timing-audit.json']:t.add(w/f,arcname=f)
  t.add(Path('/private/tmp/amu-context-call-20261005/measure-native-candidate-v2.py'),arcname='measure-native-candidate-v2.py')
(d/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(d/'archive.py').write_bytes(Path(__file__).read_bytes())
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'))
print('PASS both rejected variants archived, product backend remains byte-identical')
