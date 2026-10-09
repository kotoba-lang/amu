"""Independent SOURCE/read-only/pure control audit only."""
from pathlib import Path
import json,stat,hashlib,ast,sys,runpy,io,contextlib,importlib.util,copy
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense';A=Path(__file__).parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
def rec(p):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink()and a.st_size<=33554432;b=p.read_bytes();z=p.lstat();assert(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def check():
 sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
 for n,r in sp.items():assert rec(D/n)==r
 for p,r in ip.items():assert rec(p)==r
 return sp,ip
sp,ip=check();pr=load(D/'preregistration.json');ready=load(D/'source-readiness.json');assert len(sp)==19 and len(ip)==127 and sum(r['bytes']for r in ip.values())==6144468
assert pr['inputFiles']==127 and pr['inputLogicalBytes']==6144468 and pr['inputPinsSHA256']==rec(D/'input-pins.json')['sha256']
for f,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert rec(D/f)['sha256']==ready[k]
import run
assert run.registry_scope(pr,ip)and run.source_scope(pr)and run.fixture_guard(pr['ownershipIntegrationFixtureProof'],pr)
origin=Path(pr['qualifiedPolicySourcePins']['path']).parent
for n,r in load(D/'component-delta.json')['unchanged'].items():assert rec(D/n)==rec(r['path'])=={k:r[k]for k in ['bytes','sha256']}
assert (D/'native-call.py').read_text()==(origin/'native-call.py').read_text().replace('len(rows)<2','len(rows)<190')
assert (D/'launch-wrapper.py').read_text()==(origin/'launch-wrapper.py').read_text().replace("go['maximumLoaderCalls']==2","go['maximumLoaderCalls']==190")
# Actual current, not historical, lineage and qualified fixture are independently selected.
assert pr['G4Original19ActualProof']['sha256']=='005baf49538173b74b1c1ff2fb58db03259f2bf2992260dfd0a6e3bd5ca21af9'
assert pr['OFFActualProof']['sha256']=='9a7f35e275ec6bc1db8f71532d1a73058e88107be11da24a93d981fe4372ab3c'
assert pr['diagnosticLoaderBuildProof']['sha256']=='bcb637dd2ec7c6841e31c8b656da77ee83a26221b7cdddecfde2d725ed15a9e9'
assert pr['ownershipIntegrationFixtureProof']['sha256']=='5dd8208b02c894e9e2d5add5f8e3554f1b432318b8dbd03317c03017d24f2095'
m=load(pr['canonicalMatrix']['path']);oracle=load(pr['C95Oracle']['path']);assert len(m['entries'])==19 and len(oracle['rows'])==95
for e,t in zip(pr['entries'],m['entries']):
 assert e['workload']==t['workload']and e['symbol']==t['symbol']and e['iterations']==t['iterations']and e['source']['sha256']==t['expectedSourceSha256']and e['source']['path']=='/Users/junkawasaki/github/wt/amu-seed17/'+t['source']
 assert rec(e['source']['path'])=={k:e['source'][k]for k in ['bytes','sha256']}
for a,b in zip(pr['cases'][::2],pr['cases'][1::2]):assert a['arm']=='OFF'and b['arm']=='ON'and all(a[k]==b[k]for k in ['workload','profile','symbol','arity','source','expectedResult'])
assert len(pr['cases'])==190 and sum(len(e['iterations'])for e in pr['entries'])==95
schema=load(D/'go-schema.json');keys=schema['exactKeys'];assert len(keys)==len(set(keys))==21
G={k:None for k in keys};G.update(status=pr['rootGOStatus'],maximumLoaderCalls=190,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True);assert run.go_header(G,pr,Path(pr['freshOutputRoot']))
stream=io.StringIO()
with contextlib.redirect_stdout(stream):runpy.run_path(str(D/'pure-controls.py'),run_name='independent_pure_only')
controls=json.loads(stream.getvalue());assert controls==load(D/'pure-controls.json')and controls['nativeCalls']==controls['actualFDThreadProcessCalls']==0
# Independently exercise the actual callee count guard before its first API.
s=importlib.util.spec_from_file_location('inert_native_audit',D/'native-call.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n)
try:n.call(D,Path(pr['freshOutputRoot']),pr,pr['cases'][0],[None]*190,lambda *a:None,'0'*64)
except AssertionError:pass
else:raise AssertionError('191st entered')
# Primary loader argc separator semantics, not merely producer/wrapper self-consistency.
cs=Path(pr['qualifiedDiagnosticCSource']['path']).read_text();main=cs[cs.index('int main('):];assert main.index('argc = i;')<main.index('argc != (int)(6 + arity)')<main.index('FILE *file = fopen(argv[1], "rb")')
for c in pr['cases']:assert '--'not in c['nativeArgv']and len(c['nativeArgv'])==7 and c['nativeArgv'][3]=='1'and c['nativeArgv'][5]=='-'and c['nativeArgv'][6]==str(c['profile'])
source=(D/'run.py').read_text();assert source.index("finally:save(O/'terminal.json'")<source.index("status':'COMPLETE_HFT_G4_HELD_V6")
assert "time.monotonic()+60<=deadline"in source and "len(rows)==len(results)==190"in source
assert "['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']"in source
assert not Path(pr['freshOutputRoot']).exists()
for p in D.glob('*.py'):ast.parse(p.read_bytes())
assert check()==(sp,ip)
r=dict(status=pr['sourceReviewStatus'],subject=str(D),sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFiles=19,inputFiles=127,inputLogicalBytes=6144468,allPinsReread=True,authorDisclosure='Reviewer authored original V3 ownership F1/F2 repair, fixture4 SOURCE, hoist algorithm and previous fixedpoint SOURCE. Independent review here covers Dense new190 lineage/schedule/GO/registry/resources adaptation, not self-independent qualification of those prior components.',checks=dict(currentG4ArtifactProof=pr['G4Original19ActualProof'],currentOFFProof=pr['OFFActualProof'],actualV6Loader=pr['diagnosticLoaderBuildProof'],actualFixture4=pr['ownershipIntegrationFixtureProof'],unchangedLifecycleComponents=9,nativeCallerOnlyCountReplacement=True,wrapperOnlyCountReplacement=True,fullOriginalWorkloads=19,pairedProfiles=95,runtimeCases=190,actual191stGuardRefusedBeforeAPI=True,originalPrimaryLoaderGrammar=True,uniqueGOKeys=21,wholeNativePayloadOwnExports=True,pairedFuelAll17Arena=True,terminalBeforeValidLast=True),pureControls=controls,findings=[],qualificationLimits=['SOURCE only, zero native/build/GO/network/process/FD/thread operations.','Fixture4 qualifies only its observed source-bound diagnostic path; capsule/output/TMPDIR/ticket adaptation is disclosed in actual fixture proof and gives zero original95 credit.','Unknown PID/birth, wrong-origin/context, nonkernel/policy or ownership/raw failure remains refusal. Held protocol does not prove universal OS process closure.','Original30s outer/CPUsoft30-hard31/directcleanup30 preserved;570 threads/stages and44 parentFD conditional ledger; campaign12000s/4GiB reservation are explicit host accounting, not physical/resource quotas.','Sequential soft sampled footprint has no atomic census/hardpeak/finiteovershoot guarantee. Actual WNOWAIT/zombie/signal behavior beyond fixed observed fixture is not universal proof.','No performance/full-clobber/actualtypedmode2/generalABI/adoption/C2 claim; C95 only supplies results, no C fuel/arena.','Per-case64KiB metadata and aggregate16MiB guards are fail-closed; over-budget evidence may refuse even when guest answer matches.'],operations=dict(native=0,Clang=0,GO=0,Popen=0,FD=0,threadStarts=0,network=0,frozenWrites=0),audit=dict(path=str(A/'audit.py'),**rec(A/'audit.py')))
(A/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(dict(path=str(A/'report.json'),**rec(A/'report.json')))
