"""Independent regular-byte reads and pure injected checks only. No operational calls."""
from pathlib import Path
import json,hashlib,shutil,sys,runpy,io,contextlib,ast,copy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-g4-original19-runtime190-source-v1-20261009-root';O=Path(__file__).resolve().parent;C=O/'copied-source'
assert not C.exists();C.mkdir()
def rec(p):
 p=Path(p);a=p.lstat();assert p.is_file()and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def rd(p):return json.loads(Path(p).read_bytes())
sp=rd(D/'source-pins.json');ip=rd(D/'input-pins.json');pr=rd(D/'preregistration.json')
def verify():
 assert all(rec(D/n)==r for n,r in sp.items());assert all(rec(Path(n))==r for n,r in ip.items())
 assert len(sp)==18 and len(ip)==pr['inputFiles']==120 and sum(v['bytes']for v in ip.values())==pr['inputLogicalBytes']<=33554432
verify()
for n in sp:shutil.copyfile(D/n,C/n)
shutil.copyfile(D/'source-pins.json',C/'source-pins.json');shutil.copyfile(D/'input-pins.json',C/'input-pins.json')
for p in C.glob('*.py'):ast.parse(p.read_bytes())
base=W/'published-mode2-x8-statemate-vector-runtime12-source-v1-20261009'
delta=rd(D/'delta.json');assert len(delta['copiedComponents'])==9
for n in delta['copiedComponents']:assert(D/n).read_bytes()==(base/n).read_bytes(),n
assert (D/'launch-wrapper.py').read_text()==(base/'launch-wrapper.py').read_text().replace("go['maximumLoaderCalls']==12","go['maximumLoaderCalls']==190")
sys.path.insert(0,str(C));pure=[]
for n in ['pure-controls.py','wrapper-controls.py']:
 s=io.StringIO()
 with contextlib.redirect_stdout(s):runpy.run_path(str(C/n),run_name='pure_review')
 (O/(n+'.stdout')).write_text(s.getvalue());q=json.loads(s.getvalue());pure.append(q)
 assert q['operationalCalls']==0
import run,runtime,callback_contract
assert run.source_scope(pr)
extra=[]
def refusal(n,f):
 try:f()
 except (AssertionError,KeyError,IndexError,TypeError,ValueError):extra.append(n)
 else:raise AssertionError('accepted '+n)
for name,change in [('wholeON-payload-owner',lambda q:q['imagesON'][0]['native'].update(sha256='0'*64)),('wholeOFF-owner',lambda q:q['imagesOFF'][0]['native'].update(sha256='0'*64)),('source-path-retarget',lambda q:q['entries'][0]['source'].update(path='/unowned/ns.kotoba')),('changed-saved-C',lambda q:q['cases'][0].update(expectedResult=42)),('ordered-ON-OFF-swap',lambda q:q['cases'].__setitem__(slice(0,2),q['cases'][0:2][::-1])),('not-current19-proof',lambda q:q['G4Original19Completion'].update(sha256='0'*64))]:
 q=copy.deepcopy(pr);change(q);refusal(name,lambda q=q:run.source_scope(q))
sample={'sample':1,'ownedPGID':123,'metric':'sum-ri_phys_footprint','aggregateBytes':100,'thresholdBytes':4294967296,'members':[{'pid':123,'start':99,'exit':0,'physicalFootprintBytes':100,'uuid':'0'*32}],'hardMemoryCapEstablished':False}
assert callback_contract.row(sample,1,123,{})==([1,1,123,[[123,99,100]]],{'pid':123,'birth':99})
for name,change in [('sample2049',lambda q:q.update(sample=2049)),('wrong-owner',lambda q:q.update(ownedPGID=456)),('missing-leader',lambda q:q['members'][0].update(pid=456)),('noninteger-pid',lambda q:q['members'][0].update(pid=True)),('overthreshold',lambda q:q.update(aggregateBytes=4294967297)),('wrong-sum',lambda q:q.update(aggregateBytes=101)),('unknown-row-field',lambda q:q.update(extra=True)),('hardpeak-lie',lambda q:q.update(hardMemoryCapEstablished=True))]:
 q=copy.deepcopy(sample);change(q);refusal(name,lambda q=q:callback_contract.row(q,1,123,{}))
refusal('birth-change',lambda:callback_contract.row(sample,1,123,{'pid':123,'birth':98}))
spec=importlib.util.spec_from_file_location('native',C/'native-call.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
refusal('wrong-first-case-before-adapter',lambda:m.call(C,Path(pr['freshOutputRoot']),pr,pr['cases'][1],[],lambda *a:None,'0'*64))
assert not Path(pr['freshOutputRoot']).exists()
verify()
r={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':rec(D/'source-pins.json')['sha256'],'inputPinsSHA256':rec(D/'input-pins.json')['sha256'],'driverSHA256':rec(D/'run.py')['sha256'],'preregistrationSHA256':rec(D/'preregistration.json')['sha256'],'sourceFiles':len(sp),'inputFiles':len(ip),'inputBytes':sum(v['bytes']for v in ip.values()),'sourceAuthorshipIndependent':True,'fullPinsVerifiedBeforeAfter':True,'pureControls':[{'status':q['status'],'positiveCases':q.get('typedArgvCases',q.get('positiveWholeImagesAndExportCases')),'refusedMutants':len(q['refusedMutants'])}for q in pure],'additionalIndependentRefusals':extra,'qualifiedRuntime12ComponentsExact':delta['copiedComponents'],'wrapperOnly12to190GOCeiling':True,'currentG4Compile38IndependentProof':pr['G4Original19ActualProof'],'currentG4Completion':pr['G4Original19Completion'],'fixedpointProof':pr['FixedpointActualProof'],'currentOFFActualProof':pr['OFFActualProof'],'C95Oracle':pr['C95Oracle'],'findings':[],'evidenceScope':['All19 sources and95 original profiles/symbols exact canonical matrix; current7618 OFF and currentG4 ON wholeimages independently saved and own exports matched.','Correct typed i64 runtime argc7 without --; zero grants and exact17 fuel/arena/report environment.','190 fixed adjacent cases; complete stdout/stderr/Boolean oracle and fuel/all17 arena parity; no historical C fuel/arena imported.','Unchanged qualified lifecycle: stopped writer/raw hashing, durable accepted sample journal, immutable first refusal, born owner, authority retirement, one direct wait and explicit typed gap policy; unknown/unbound PID still refuses.','CPU30/hard31 FSIZE64MiB, 2048 rows and4GiB controlled retained reservation; finite12000s campaign, cooperative deadlines not hard I/O bound.','Completion after durable terminal, full final pins and190 closed new rows; no GO or operations performed.'],'nativeCalls':0,'processCalls':0,'threadsOrFDOperations':0,'full19RuntimeQualified':False,'fullClobberCertificateQualified':False,'generalCandidateAdoptionQualified':False,'performanceQualified':False,'hardPeakQualified':False,'C2':False}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(O/'report.json'),**rec(O/'report.json'))))
