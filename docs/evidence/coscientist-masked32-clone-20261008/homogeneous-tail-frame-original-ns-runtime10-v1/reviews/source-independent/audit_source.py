from pathlib import Path
import json,hashlib,stat,sys,importlib.util,struct,ast
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-original-ns-runtime10-source-v1-20261009');O=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
def rec(p):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']}
for p,r in ip.items():assert rec(p)=={k:r[k]for k in ['bytes','sha256']}
assert len(sp)==18 and len(ip)==55 and sum(x['bytes']for x in ip.values())==6696257
base=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-statemate-vector-runtime12-source-v1-20261009');same=['capture.py','integration.py','controller.py','typed-adapter.py','artifact_admission.py','callback_contract.py','runtime.py','loader_grammar.py'];assert all((D/n).read_bytes()==(base/n).read_bytes()for n in same)
s=(base/'native-call.py').read_text();ns=(D/'native-call.py').read_text();assert ns==s.replace("need(len(rows)<190 and pr['cases'][len(rows)]==case,'fixed ordered190 no retry')","need(len(rows)<10 and pr['cases'][len(rows)]==case,'fixed ordered10 no retry')")
# Exact executable delta has been inspected; assert all code after initial guard is unchanged.
assert ns[ns.index(' # Existing inherited closure'):]==s[s.index(' # Existing inherited closure'):]
for p in D.glob('*.py'):ast.parse(p.read_text())
spec=importlib.util.spec_from_file_location('pure_hft_controls',D/'pure-controls.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);controls=mod.controls();assert controls==json.loads((D/'pure-controls.json').read_bytes())
import run
assert run.source_scope(pr)and run.loader_protocol(pr)and not Path(pr['freshOutputRoot']).exists()
order=[(n,a)for n in [0,1,2,17,32]for a in ['OFF','ON']];assert [(c['profile'],c['arm'])for c in pr['cases']]==order
for c in pr['cases']:
 assert len(c['nativeArgv'])==7 and '--'not in c['nativeArgv']and c['nativeArgv'][2:6]==['36440','1','aarch64','-'];p,e=run.container(Path(c['container']['path']).read_bytes());assert p==Path(c['native']['path']).read_bytes()and('batch',36440,1)in e
old=Path(pr['images']['OFF']['native']['path']).read_bytes();new=Path(pr['images']['ON']['native']['path']).read_bytes();ww=list(struct.unpack('<'+'I'*(len(old)//4),old));nn=list(struct.unpack('<'+'I'*(len(new)//4),new));diff=[dict(wordIndex=i+1,physicalByteOffset=4*i,before=a,after=b)for i,(a,b)in enumerate(zip(ww,nn))if a!=b];ec=json.loads(Path(pr['emissionCertificate']['path']).read_bytes());assert len(old)==len(new)==37520 and diff==ec['changes']and len(diff)==4
summary={'sourceFiles':len(sp),'sourceLogicalBytes':sum(x['bytes']for x in sp.values()),'inputFiles':len(ip),'inputLogicalBytes':sum(x['bytes']for x in ip.values()),'sourcePins':rec(D/'source-pins.json'),'inputPins':rec(D/'input-pins.json'),'driver':rec(D/'run.py'),'preregistration':rec(D/'preregistration.json'),'freeze':rec(D/'freeze.json'),'pureControls':controls,'sameComponents':{n:rec(D/n)['sha256']for n in same},'nativeCallSHA256':rec(D/'native-call.py')['sha256'],'cases':pr['cases'],'images':pr['images'],'C5Rows':pr['C5Rows'],'fourWordDifference':diff,'freshOutputAbsent':True};(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k in ['sourceFiles','sourceLogicalBytes','inputFiles','inputLogicalBytes','sourcePins','inputPins','driver','preregistration','freeze']}));print({k:len(v)for k,v in controls.items()if isinstance(v,list)})
