from pathlib import Path
import json,tarfile,hashlib,tempfile
e=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,x in json.loads((e/'archive-manifest.json').read_text()).items():assert sha(e/name)==x['sha256'] and (e/name).stat().st_size==x['bytes'],name
root=Path(tempfile.mkdtemp(prefix='amu-local-index-replay-'))
for name in ['native-proof.tgz','timing.tgz']:
 with tarfile.open(e/name) as t:t.extractall(root,filter='data')
w=root/'amu-local-constant-index-wrapper-20261006';(root/'remote-evidence').rename(w/'remote-evidence')
old='/private/tmp/amu-local-constant-index-wrapper-20261006'
exec(compile((w/'timing-audit.py').read_text().replace(old,str(w)),str(w/'timing-audit.py'),'exec'),{'__name__':'__main__'})
assert (w/'timing-audit.json').read_bytes()==(e/'timing-audit.json').read_bytes()
assert len({sha(w/f'seed-{g}.bin') for g in [2,3,4]})==1
assert sha(w/'seed-2.bin')=='c161cee0516f929950635b6399cd1d49f94315f368491fa17b310ad13d508a20'
pre=json.loads((w/'preflight.json').read_text());pkg=w/'remote-evidence/timing-package'
for name,digest in pre['proofPins'].items():assert sha(pkg/name)==digest,name
out={'status':'complete-extracted-archive-replay','archiveChecksums':True,'rawTimingAdmissionStatisticsAndHashAuditExact':True,'nativeFixedPointExact':True,'proofPinsExact':True,'freshNativeExecutions':0,'limits':'Replays retained evidence, not a fresh benchmark or full native test rerun.'};(e/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));print('extracted',root)
