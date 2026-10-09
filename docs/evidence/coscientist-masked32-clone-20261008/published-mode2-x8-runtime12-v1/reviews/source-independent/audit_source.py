from pathlib import Path
import json,hashlib,stat,sys,io,contextlib,runpy,ast
D=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-statemate-vector-runtime12-source-v1-20261009');O=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
def rec(p):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes());fr=json.loads((D/'freeze.json').read_bytes())
for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']}
for p,r in ip.items():assert rec(p)=={k:r[k]for k in ['bytes','sha256']}
assert len(sp)==22 and len(ip)==45 and sum(x['bytes']for x in ip.values())==3073284
base=Path('/Users/junkawasaki/github/workspaces/codex/tc-original19-functional-remaining50-source-v1-20261009');same=['capture.py','integration.py','controller.py','typed-adapter.py','artifact_admission.py','callback_contract.py','runtime.py','native-call.py','loader_grammar.py'];assert all((D/n).read_bytes()==(base/n).read_bytes()for n in same)
for p in D.glob('*.py'):ast.parse(p.read_text())
controls={}
for n in ['pure-controls','wrapper-controls']:
 b=io.StringIO()
 with contextlib.redirect_stdout(b):runpy.run_path(str(D/(n+'.py')),run_name='independent_pure_no_operations')
 result=json.loads(b.getvalue());assert result==json.loads((D/(n+'.json')).read_bytes());controls[n]=result
import run
assert run.source_scope(pr)and run.loader_protocol(pr)
assert not Path(pr['freshOutputRoot']).exists()
# Independently decode exact profile ordering and whole native-own-export ABI.
order=[(w,n,a)for w,n in [('statemate',n)for n in [0,1,2,17,32]]+[('vector-fixture',1)]for a in ['OFF','ON']];assert [(c['workload'],c['profile'],c['arm'])for c in pr['cases']]==order
for c in pr['cases']:
 argv=c['nativeArgv'];assert len(argv)==7 and '--'not in argv and argv[3]=='1'and int(argv[6])==c['profile']and argv[5]=='-';payload,ex=run.container(Path(c['container']['path']).read_bytes());assert payload==Path(c['native']['path']).read_bytes()and (c['symbol'],c['offset'],1)in ex
summary={'sourceFiles':len(sp),'sourceLogicalBytes':sum(x['bytes']for x in sp.values()),'inputFiles':len(ip),'inputLogicalBytes':sum(x['bytes']for x in ip.values()),'sourcePins':rec(D/'source-pins.json'),'inputPins':rec(D/'input-pins.json'),'driver':rec(D/'run.py'),'preregistration':rec(D/'preregistration.json'),'freeze':rec(D/'freeze.json'),'pureControls':controls,'sameComponents':{n:rec(D/n)['sha256']for n in same},'cases':pr['cases'],'images':pr['images'],'C5Rows':pr['C5StatemateRows'],'loaderProtocolView':pr['loaderSupervisorProtocolView'],'candidateCompilerActualProof':pr['CandidateCompilerActualProof'],'emittedAssociationProof':pr['EmittedAssociationProof'],'freshOutputAbsent':True};(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k in ['sourceFiles','sourceLogicalBytes','inputFiles','inputLogicalBytes','sourcePins','inputPins','driver','preregistration','freeze']}));print({k:len(v['refusedMutants'])for k,v in controls.items()})
