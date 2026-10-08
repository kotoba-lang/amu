"""Offline metadata author only: preserves V1 and builds no archive/image."""
from pathlib import Path
import json,hashlib,ast
D=Path(__file__).resolve().parent;W=D.parent;V1=W/'vector-leaf-straight-read-cache-current19-build52-source-v1-lc-remote'
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
pr=json.loads((V1/'preregistration.json').read_text())
pr.update(status='PROSPECTIVE_EXECUTABLE_SOURCE_ONLY_LC_FRESH_BUILD52_NO_GO',schema='LC_CURRENT19_BUILD52/v2',remoteRoot='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root',canonicalCPackage=str(W/'vector-param-C-remote-rebuild-plan-v1-controls/package'),maximumLaunchTransportChildren=1,launchTimeoutSeconds=7980,remoteBuildAlarmSeconds=7920,totalSequentialDeadlineSeconds=7800,perChildRegularFileHardLimitBytes=16777216,rootFunctionalAcceptanceRequired=True)
accept=ref(W/'vector-leaf-straight-read-cache-functional255-go-v1-root/original19-functional285-acceptance.json');assert accept['sha256']=='2a4379322134f28ff101f20e829058495f3246366565b815dd86252ff77e49eb'
save('preregistration.json',pr);save('root-functional285-acceptance-ref.json',accept)
origins=json.loads((V1/'input-origins.json').read_text())
for p in sorted(V1.iterdir()):
 if p.is_file():r=ref(p);origins[r.pop('path')]=r
for p in [accept['path'],W/'vector-param-original19-remote-package-plan-v1-width/safe-extract.py',W/'vector-masked32-original19-remote-source-v2-width/transfer.py',W/'vector-param-C-remote-rebuild-plan-v1-controls/package/remote-build.py']:
 r=ref(p);origins[r.pop('path')]=r
assert len(origins)<=4096 and sum(r['bytes'] for r in origins.values())<=469762048
for p,r in origins.items():assert Path(p).stat().st_size==r['bytes'] and sha(p)==r['sha256']
save('input-origins.json',origins)
for p in D.glob('*.py'):ast.parse(p.read_bytes(),filename=str(p))
save('source-report.json',dict(status='SOURCE_ONLY_EXECUTABLE_PHASES_AUTHORED_NOT_RUN',logicalEvidenceOrigins=len(origins),logicalEvidenceBytes=sum(r['bytes'] for r in origins.values()),maximumEvidenceOrigins=4096,maximumEvidenceBytes=469762048,CBuilds=19,consumerBuilds=19,identityQueries=14,innerBuildChildren=52,assemblyChildren=0,transportChildren=3,launchChildren=1,authorSSHCompilerNativeCalls=0,authorArchiveAssemblyCalls=0,rootFunctional285Acceptance=accept,oldSourcesFailuresPreserved=True))
