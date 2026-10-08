from pathlib import Path
import json,hashlib,stat,sys,io,contextlib,runpy,ast
D=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-vector-statemate6-source-v2-20261009')
O=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(D))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(p,r):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode) and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];return len(b)
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes());fr=json.loads((D/'freeze.json').read_bytes())
assert sha(D/'source-pins.json')=='072fa092ab1ae7f4f54db0b7335c104f314885f8ca18fb3c46fe5d23d94157f6'
assert sha(D/'input-pins.json')=='508fb0f682a17079aa1d163c195aca675fcc0ad774bf231a72c2aa2d81dcec3c'
sb=sum(verify(D/n,r) for n,r in sp.items());ib=sum(verify(p,r) for p,r in ip.items());assert len(sp)==22 and len(ip)==80 and ib==11077437
for n in D.glob('*.py'):ast.parse(n.read_text())
old=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-build-fixture6-source-v1-20261009')
components=['capture.py','integration.py','controller.py','native-call.py','typed-adapter.py','artifact_admission.py','runtime.py','compiler_output.py']
assert all((D/n).read_bytes()==(old/n).read_bytes() for n in components)
controls={}
for script,saved in [('pure-controls.py','pure-controls.json'),('wrapper-controls.py','wrapper-controls.json')]:
 b=io.StringIO()
 with contextlib.redirect_stdout(b):runpy.run_path(str(D/script),run_name='independent_pure_injected_control')
 got=json.loads(b.getvalue());expected=json.loads((D/saved).read_bytes());assert got==expected
 controls[script]=got
import run
assert run.source_scope(pr,ip) and run.existing_candidate_guard(pr)
assert not Path(pr['freshOutputRoot']).exists()
# Independently decode reused producer container boundary and exact owned main export.
payload,ex=run.container(Path(pr['candidateCompilerContainer']['path']).read_bytes());assert payload==Path(pr['candidateCompiler']['path']).read_bytes() and ex==[('main',0,0)]
summary={'sourceFiles':len(sp),'sourceLogicalBytes':sb,'inputFiles':len(ip),'inputLogicalBytes':ib,'sourcePinsSHA256':sha(D/'source-pins.json'),'inputPinsSHA256':sha(D/'input-pins.json'),'driverSHA256':sha(D/'run.py'),'preregistrationSHA256':sha(D/'preregistration.json'),'freezeSHA256':sha(D/'freeze.json'),'freeze':fr,'componentHashes':{n:sha(D/n)for n in components},'pureControls':controls,'cases':pr['cases'],'freshOutputAbsent':True,'candidateActualProof':pr['candidateActualProof'],'preservedCandidateBuildRootGO':pr['candidateBuildRootGO'],'candidateSealedBuild':pr['candidateSealedBuild'],'candidateCompiler':pr['candidateCompiler'],'candidateCompilerContainer':pr['candidateCompilerContainer']}
(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'counts':[len(sp),sb,len(ip),ib],'controlRefusals':{k:len(v['refusedMutants'])for k,v in controls.items()},'freeze':fr},indent=2))
