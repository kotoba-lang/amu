from pathlib import Path
import ast,json,hashlib,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-full256-prefix1081-source-v1-20261009';V=W/'crc-original-guest-native-controller-source-v4-20261009-dense';O=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def exact(p,v):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==v['bytes'] and H(p)==v['sha256']
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text())
for n,v in sp.items():exact(D/n,v)
for p,v in ip.items():exact(Path(p),v)
assert len(ip)==pr['inputCount'] and sum(v['bytes']for v in ip.values())==pr['inputLogicalBytes'];assert H(D/'input-pins.json')==pr['inputRegistrySHA256']
for n in ['capture.py','integration.py','controller.py','adapter.py','typed-adapter.py','runtime.py','validate-runtime.py','launch-wrapper.py']:assert (D/n).read_bytes()==(V/n).read_bytes()
for p in D.glob('*.py'):ast.parse(p.read_text())
assert not (D/'run-outputs').exists()
assert pr['maximumLoaderCalls']==pr['maximumPythonWrapperStarts']==pr['maximumNativeGuestChildStarts']==2 and pr['maximumNativeCompilerChildStarts']==0
assert [c['arm']for c in pr['cases']]==['OFF','ON'];assert len(pr['cases'])==2
for c in pr['cases']:
 assert c['symbol']=='prefix-crc' and c['argument']==1081 and c['expectedResult']==4018572661 and c['expectedRemainingFuel']==997836 and c['nativeArgv'][-1]=='1081'
 assert c['nativeArgv'][2]==str(1352 if c['arm']=='OFF' else 1392)
 assert c['nativeArgv'][5]=='-'
assert pr['environment']['KEXE_FUEL']=='1000000' and len(pr['environment'])==17
basepr=json.loads((V/'preregistration.json').read_text());assert {k:v for k,v in pr['environment'].items()if k!='TMPDIR'}=={k:v for k,v in basepr['environment'].items()if k!='TMPDIR'}
proof=pr['priorActualGuest8IndependentProof'];exact(Path(proof['path']),proof);assert proof['sha256']=='6c8e86547cb5311ce48a8ce7ef5a8eada9daac1568b59d4b4f841d643dc6105c'
assert json.loads(Path(proof['path']).read_text())['status']=='PASS_INDEPENDENT_ACTUAL_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_ONLY'
cert=json.loads((D/'fuel-reach-certificate.json').read_text());t=ast.parse((D/'derive-source.py').read_text());removed=[]
# This author model only reads frozen source and typed rows. Remove final certificate publication and print.
for node in t.body[-2:]:assert isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
t.body=t.body[:-2];ns={'__file__':str(D/'derive-source.py'),'__name__':'root_source_only'};exec(compile(t,str(D/'derive-source.py'),'exec'),ns);assert json.loads(json.dumps(ns['out']))==cert
assert cert['uniqueTableIndices']==256 and cert['expectedCRC']==4018572661 and cert['consumedFuel']==2164 and cert['firstVisitIterationByIndex']['154']==1081
run=(D/'run.py').read_text();native=(D/'native-call.py').read_text();assert "'full256CandidateReachQualified':False"in run and "'sourceBoundFull256PrefixParityQualified':True"in run
assert "report['remainingFuel']==case['expectedRemainingFuel']"in native
q={'status':'PASS_SOURCE_ONLY_TC_FULL256_PREFIX1081_PAIRED2','sourcePinsSHA256':H(D/'source-pins.json'),'driverSHA256':H(D/'run.py'),'sourceFiles':len(sp),'inputFiles':len(ip),'inputBytes':pr['inputLogicalBytes'],'unchangedAuditedRuntimeComponents':8,'sourceModelRecomputed':True,'expectedCRC':4018572661,'expectedFuelConsumed':2164,'calls':2,'priorActualGuest8ProofSHA256':proof['sha256'],'nativeCalls':0,'operationalGO':False,'dynamicAllIndexTraceQualified':False,'performanceQualified':False}
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q))
