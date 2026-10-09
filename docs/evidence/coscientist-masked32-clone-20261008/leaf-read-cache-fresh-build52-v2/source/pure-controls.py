"""Offline guards/argv/source controls; no Ledger.call or operational main."""
from common import *
import ast, tempfile
pr=load(D/'preregistration.json');origins=load(D/'input-origins.json')
assert len(pr['entries'])==19 and pr['totalChildren']==52 and pr['identityQueries']==14
assert pr['maximumChildren']==64 and len(origins)<=4096 and sum(r['bytes'] for r in origins.values())<=CAP
assert sha(Path(load(D/'root-functional285-acceptance-ref.json')['path']))=='2a4379322134f28ff101f20e829058495f3246366565b815dd86252ff77e49eb'
rows=[]
for row in pr['entries']:
 argv=[s.replace('$RESOLVED_CLANG','/Library/Developer/CommandLineTools/usr/bin/clang').replace('$TASK_ROOT',str(ROOT/'package/c-inputs')).replace('$FRESH_BUILD',str(ROOT/'build52')) for s in row['CBuild']]
 assert argv[:4]==['/Library/Developer/CommandLineTools/usr/bin/clang','-O2','-std=gnu11','-dynamiclib']
 assert argv[-2:]==['-o',str(ROOT/'build52'/row['workload']/'c.dylib')]
 assert not any('$' in a or a in ['>','2>',';','&&','-###','-M','-MD','-x'] for a in argv)
 assert any(a.endswith('.c') for a in argv[4:-2])
 for s in row['CBuild']:
  if s.startswith('$TASK_ROOT/'):
   pp=Path(pr['canonicalCPackage'])/s.removeprefix('$TASK_ROOT/');assert pp.exists()
 consumer=[s.replace('$RESOLVED_CLANG','/Library/Developer/CommandLineTools/usr/bin/clang').replace('$PACKAGE',str(ROOT/'package')).replace('$FRESH_BUILD',str(ROOT/'build52')) for s in row['consumerBuild']]
 assert consumer[5].endswith('/sources/timing-host-telemetry.c') and consumer[:3]==['/Library/Developer/CommandLineTools/usr/bin/clang','-O2','-std=c11']
 rows.append(dict(workload=row['workload'],CArgv=argv,consumerArgv=consumer,sourceBodyN=row['n'],profiles=row['profiles']))
rejects=0
with tempfile.TemporaryDirectory(dir=D,prefix='pure-fixture-') as td:
 t=Path(td);p=t/'value';p.write_bytes(b'fixture');r=ref(p)
 for q in [dict(r,sha256='0'*64),dict(r,bytes=r['bytes']+1)]:
  try:pin(q)
  except AssertionError:rejects+=1
  else:raise AssertionError('wrong pin accepted')
 link=t/'symlink';link.symlink_to(p)
 try:pin(dict(r,path=str(link)))
 except AssertionError:rejects+=1
 else:raise AssertionError('symlink accepted')
 go=t/'wrong-go.json';save(go,dict(phase='transfer',authorized=True))
 try:authorize('build',go)
 except AssertionError:rejects+=1
 else:raise AssertionError('wrong phase accepted')
for p in D.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
assert rejects==4
save(D/'phase-controls-result.json',dict(status='PASS_PURE_GUARD_4_REJECTIONS_EXACT38_ARGV_ROLES_AND_SYNTAX',entries=rows,pinAndGORejections=4,preregisteredQueries=pr['identityQueryArgv'],maximumFutureInnerChildren=52,operationalEntrypointCalls=0,SSHCompilerNativeCalls=0,archiveAssemblyCalls=0))
