"""Finite generic capacity/refusal model; no compiler operations."""
from pathlib import Path
import json,importlib.util
D=Path(__file__).parent;B=D.parent/'tc-homogeneous-tail-frame-compose511-source-v1-20261009'
# Original source capacity law copied, authoring source assertions replaced by exact sf-collapse form equality.
spec=importlib.util.spec_from_file_location('scan',D.parent/'shared-frame-currenttyped-observer3-library-closure-author-v1-20261009/diagnose.py');scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
assert scan.form((D/'41-a64gen-candidate.kotoba').read_text(),'sf-collapse')==scan.form((B/'41-a64gen-candidate.kotoba').read_text(),'sf-collapse').replace('Existing FN capacity bounds scans, work and additional labels to at most 511.','Existing FN-N<=512 admission bounds scans, work and additional labels to at most 511 (physical MM-FN-CAP8192).')
def run(fnn,ln,cap=131072,eligible=lambda f:True,closed=lambda f,u:True):
 if not(0<fnn<=512 and 0<ln<cap and closed(0,0)):return 0,0,ln
 f=1;used=0
 while f<fnn and used<511 and ln<cap:
  if not closed(f,used):break
  if eligible(f):used+=1;ln+=1
  f+=1
 return f-1,used,ln
controls={'FN0':run(0,1)[1]==0,'FN513':run(513,1)[1]==0,'sentinel-only':run(1,1)[1]==0,'full-label':run(512,131072)[1]==0,'one-label':run(512,131071)[1]==1,'capacity511':run(512,1)==(511,511,512),'sparse':run(512,1,eligible=lambda f:f%2==0)[1]==255,'closure-before-first':run(512,1,closed=lambda f,u:f==0)[1]==0,'closure-after-prefix':run(512,1,closed=lambda f,u:u<7)[1]==7}
assert all(controls.values());out={'status':'PASS_PURE_ORIGINAL_511_CAPACITY_GUARDS_UNCHANGED','controls':controls,'nativeCalls':0,'C2':False};(D/'budget-controls-result.json').write_text(json.dumps(out,indent=2)+'\n');print(len(controls))
