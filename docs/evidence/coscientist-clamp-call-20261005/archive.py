from pathlib import Path
import tarfile,json,hashlib,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-clamp-call-20261005');i=Path('/private/tmp/amu-clamp-call-integrated-20261005');p=Path('/private/tmp/amu-clamp-call-integrated-20261005-parity');d=r/'docs/evidence/coscientist-clamp-call-20261005';d.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof=json.loads((w/'fixture-proof.json').read_text());timing=json.loads((w/'timing-audit.json').read_text());integ=json.loads((w/'integrated-summary.json').read_text());imports=json.loads((w/'import-proof.json').read_text());assert timing['qualifies'] and integ['status']=='complete-3-generations-19-ports-and-per-case-corpus-parity' and imports['status']=='complete-clamp-import-substitution-refusal'
assert (w/'bootstrap-before.txt').read_bytes()==(w/'bootstrap-after.txt').read_bytes();assert (r/'seed/41-a64gen.kotoba').read_bytes()==(w/'41-a64gen-prototype.kotoba').read_bytes()
summary={'status':'qualified-native-signed-clamp-composition','decision':'Promote exact signed-extension/clamp composition after quiet timing and integrated proof. No C-level or full-release claim.','sourceHeadBefore':'e5ed92335fe44d72be11c66507b9c0f16559282d','sourceCommit':'33303be5a','hypothesis':json.loads((w/'hypothesis.json').read_text()),'generations':json.loads((w/'generations.json').read_text()),'timing':timing,'codeChanges':json.loads((w/'code-change.json').read_text()),'nativeProof':{k:proof[k] for k in ['status','fixtures','canonicalRuns','realTestLayoutIdentical','supervisorComparisons','instructionAudit']},'openImportProof':{'status':imports['status'],'executions':len(imports['runs']),'realCalls':imports['realCalls']},'workspace':json.loads((w/'bulk-state.json').read_text()),'integration':integ,'gates':{'rung':'r6m','subset':['ERR','G1','G2','G3','G4','G5'],'pass':6,'fullReleaseGateClaim':False},'bootstrapProductInventoryUnchanged':True,'prototypeSha256':sha(w/'41-a64gen-prototype.kotoba'),'unitySha256':sha(w/'seed-unity.kotoba'),'productChanged':True,'launcherSwitched':False,'officialEmbenchScore':False,'COrBetterEvidence':False}
(d/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');q=subprocess.run(['git','diff','--no-index',str(w/'baseline-41-a64gen.kotoba'),str(w/'41-a64gen-prototype.kotoba')],capture_output=True,text=True);assert q.returncode==1;(d/'prototype.diff').write_text(q.stdout)
for name in ['archive.py','audit.py','next-hypothesis.json']:(d/name).write_bytes((w/name).read_bytes())
(d/'timing-audit.json').write_bytes((w/'timing-audit.json').read_bytes())
with tarfile.open(d/'native-proof.tgz','w:gz') as t:
 for f in ['create.py','build.py','seed-unity.kotoba','seed-0.bin','seed-0.offset','seed-4.bin','seed-4.offset','41-a64gen-prototype.kotoba','baseline-41-a64gen.kotoba','baseline-a64gen-fixtures.py','generations.json','hypothesis.json','check-ports.py','ports-correctness.json','code-change.json','bulk-state.py','bulk-state.json','picojpeg-state-observer.kotoba','bulk-baseline','bulk-candidate','fixture-proof.py','fixture-proof.json','candidate-test.stdout','candidate-real.stdout','baseline-real.stdout','fixture-candidate-code.bin','fixture-baseline-code.bin','audit-extra.py','fuel-instruction-audit.json','import-proof.py','import-proof.json','baseline-open.stdout','candidate-open.stdout','candidate-closed.stdout','baseline-open-linked.bin','candidate-open-linked.bin','candidate-closed-linked.bin','canonical-fixtures.log','open-regression-unit.log','bootstrap-before.txt','bootstrap-after.txt','kexe-loader']:
  t.add(w/f,arcname=f)
 for f in ['seed/SIR','seed/HEADS','seed/MEMORY-MAP']:t.add(r/f,arcname=f)
 for f in ['clobber-state-loader.c','clobber-state-loader']:t.add(Path('/private/tmp/amu-context-call-20261005')/f,arcname='diagnostic/'+f)
 t.add(w/'open-regression-unit/unit/41-a64gen',arcname='permanent-unit')
with tarfile.open(d/'timing.tgz','w:gz') as t:
 for f in ['prepare-timing.py','remote-all.py','timing-package','all-summary.json','audit.py','timing-audit.json']:
  t.add(w/f,arcname=f)
 t.add(Path('/private/tmp/amu-context-call-20261005/measure-native-candidate-v2.py'),arcname='measure-native-candidate-v2.py')
with tarfile.open(d/'integrated-proof.tgz','w:gz') as t:
 for f in ['gates.log','gate-build/gates/r6m','integrated-ports.py','integrated-proof.py','integrated-summary.json','integrated-parity.log']:t.add(w/f,arcname=f)
 for f in ['check.tsv','compile.tsv','exports.tsv']:t.add(p/f,arcname='parity/'+f)
 for f in ['inputs.sha256','objects1.sha','objects2.sha','objects3.sha','input-check.log','ports.json','front1.out','front2.out','front3.out','g1.out','g2.out','g3.out','g3/amu','g3/amu.bin','g3/amu.kseed']:t.add(i/f,arcname='integrated/'+f)
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'))
print('PASS complete proof and raw timing archived, all bootstrap PRODUCT inventory unchanged')
