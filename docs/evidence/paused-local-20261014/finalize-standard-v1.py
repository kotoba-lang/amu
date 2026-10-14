from pathlib import Path
import json,hashlib,tarfile,shutil
W=Path(__file__).parent;R=Path('/Users/junkawasaki/github/wt/codex/seed-copy-chain48-20261014');E=R/'docs/evidence/copy-chain48-20261014'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=json.loads((W/'standard-controls-receipt.json').read_text());p=json.loads((W/'main-policy-v1/report.json').read_text());assert len(s['calls'])==11 and all(x['exit']==0 for x in s['calls']);assert p['explicitPolicyRefusals']==34 and p['policyFreeResult']==42 and len(p['original19Images'])==19
for a,b in [('standard-controls-receipt.json','standard-controls.json'),('main-policy-v1/report.json','standard-policy-source19.json')]:shutil.copy2(W/a,E/b)
rows=[];archive=E/'review-standard-results.tgz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as t:
 for n in ['main-selfbuild-v1','main-policy-v1','standard-controls-raw']:
  for f in sorted((W/n).rglob('*')):
   if not f.is_file()or '__pycache__'in f.parts:continue
   rel=str(f.relative_to(W));rows.append(dict(path=rel,bytes=f.stat().st_size,sha256=sha(f)));t.add(f,arcname=rel,recursive=False)
 for n in ['standard-controls-calls.json','standard-controls-receipt.json','run-standard-controls.py']:
  f=W/n;rows.append(dict(path=n,bytes=f.stat().st_size,sha256=sha(f)));t.add(f,arcname=n,recursive=False)
(E/'review-standard-raw-custody.json').write_text(json.dumps(dict(status='PASS_STANDARD_NATIVE_SELFBUILD2_ALL10_POLICY34_SMOKE42_SOURCE19_FIXEDPOINT3',files=rows,archiveSHA256=sha(archive),archiveBytes=archive.stat().st_size),indent=2)+'\n')
readme=E/'README.md';readme.write_text(readme.read_text()+'\nLocal standard qualification passes: native selfbuild2, all10 original controls, policy34 refusals, smoke42, archived19 and nativefixedpoint3. Full raw standard outputs and hashes are archived. No historical gate or source fixture was weakened. Remote CI and main merge/readback remain separate acceptance evidence.\n')
A=R/'seed/adoption-20261012.json';d=json.loads(A.read_text());d['copyChain48Qualification'].update(standardPolicyAndSource19Pending=False,standardControlsActualPass=True);prefix='docs/evidence/copy-chain48-20261014/';d['evidenceDigests']=[x for x in d['evidenceDigests']if not x['label'].startswith(prefix)]
for f in sorted(E.iterdir()):
 if f.is_file()and f.name!='.gitignore':d['evidenceDigests'].append(dict(path=str(f.relative_to(R)),bytes=f.stat().st_size,sha256=sha(f),label=str(f.relative_to(R))))
A.write_text(json.dumps(d,indent=2)+'\n')
for x in d['sourceFiles']:
 p=R/x['path'];assert p.stat().st_size==x['bytes']and sha(p)==x['sha256']
for x in d['evidenceDigests']:
 if 'path'in x:p=R/x['path'];assert p.stat().st_size==x['bytes']and sha(p)==x['sha256']
(W/'integration-source-review.json').write_text(json.dumps(dict(status='PASS_FINAL_COPY_CHAIN_SOURCE20_EVIDENCE_FULL_STANDARD_QUALIFICATION_NOT_REMOTE_MAIN',standardCalls=11,policyRefusals=34,smokeResult=42,archivedSource19=19,sourcePins20=20,adopted=False,PRAndMainPending=True),indent=2)+'\n');print('PASS_ALL_STANDARD_CHECKS_AND_FINAL_SOURCE20_EVIDENCE_PINS',len(rows))
