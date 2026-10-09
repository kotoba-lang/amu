from pathlib import Path
import json,hashlib,importlib.util,sys
S=Path('/Users/junkawasaki/github/workspaces/codex/tc-original19-functional190-source-v3-20261009')
D=Path(__file__).resolve().parent
sys.path.insert(0,str(S))
import run
spec=importlib.util.spec_from_file_location('pure_controls',S/'pure-controls.py');pure_controls=importlib.util.module_from_spec(spec);spec.loader.exec_module(pure_controls)
def h(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sp=json.loads((S/'source-pins.json').read_bytes());ip=json.loads((S/'input-pins.json').read_bytes());pr=json.loads((S/'preregistration.json').read_bytes())
assert len(sp)==18 and len(ip)==2905
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
assert sum(r['bytes']for r in ip.values())==455796828
proofs=[json.loads(Path(pr[k]['path']).read_bytes())for k in ['OFFActualProof','TCActualProof','C95Oracle']]
assert run.source_scope(pr,*proofs)
controls=pure_controls.controls()
assert controls==json.loads((S/'pure-controls.json').read_bytes())
from loader_grammar import interpretation
loaderSource=Path('/Users/junkawasaki/github/workspaces/codex/vector-masked32-source-bound-loader-build-plan-v2-native-controls/kexe_loader.c')
assert str(loaderSource)in ip
src=loaderSource.read_text();main=src[src.index('int main(int argc, char **argv)'):]
assert main.index('argc = i;')<main.index('argc != (int)(6 + arity)')<main.index('FILE *file = fopen(argv[1], "rb")')
assert 'kexe_guest_argv = argv + i + 1;'in main and 'kexe_guest_argc = argc - i - 1;'in main
assert all(interpretation(c['nativeArgv'])=={'typedI64':[c['profile']],'guestArgv':None,'effectiveArgc':7}for c in pr['cases'])
for c in pr['cases']:
 try:interpretation(c['nativeArgv'][:6]+['--']+c['nativeArgv'][6:])
 except AssertionError:pass
 else:raise AssertionError('misplaced separator accepted')
v2t=run.load(pr['retainedV2Failure']['terminal.json']['path']);v2a=run.load(pr['retainedV2Failure']['attempts.json']['path'])
assert v2t=={'loaderCalls':1,'allChildrenClosed':True,'failure':True}and len(v2a)==1 and v2a[0]['returncode']==2
assert run.load(pr['retainedV2FailureProof']['path'])['status']==pr['retainedV2FailureProofStatus']
fixture=json.loads(Path(pr['qualifiedIntegrationFixtureProof']['path']).read_bytes())
assert fixture['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('controller.py','controllerSHA256'),('integration.py','integrationSHA256')]:assert sp[n]['sha256']==fixture[k]
assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='16777216'
assert len(pr['cases'])==190 and all(c['arm']==('OFF'if i%2==0 else'TC')for i,c in enumerate(pr['cases']))
for a,b in zip(pr['cases'][::2],pr['cases'][1::2]):assert (a['workload'],a['profile'],a['source'],a['expectedResult'])==(b['workload'],b['profile'],b['source'],b['expectedResult'])
driver=(S/'run.py').read_text();native=(S/'native-call.py').read_text();wrapper=(S/'launch-wrapper.py').read_text()
assert driver.index("save(O/'terminal.json'")<driver.index("save(O/'report.json'")
assert "guard();terminal=load(O/'terminal.json')"in driver and "fresh output namespace"in driver
assert "['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']"in driver
assert 'C95FuelArenaAvailable' in driver and "'C95FuelArena':None"in driver
assert "sampleCount<=2048"in native and '8388608' in native and "4096" in native
assert "strictOldMemoryPolicyPassed"in native and 'accept_artifact_observation(observed)'in native
assert 'os.execve(argv[0],argv,dict(pr[\'environment\']))'in wrapper
assert "('RLIMIT_CPU',30,31)"in wrapper and "('RLIMIT_FSIZE',67108864,67108864)"in wrapper
report={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':h(S/'source-pins.json')['sha256'],'inputPinsSHA256':h(S/'input-pins.json')['sha256'],'driverSHA256':h(S/'run.py')['sha256'],'preregistrationSHA256':h(S/'preregistration.json')['sha256'],'sourceFiles':len(sp),'inputFiles':len(ip),'inputLogicalBytes':sum(r['bytes']for r in ip.values()),'fullPinsRehashed':True,'exact190FullOriginalCases':True,'qualifiedComponentsUnchanged':True,'pureControls':controls,'manualReview':['exact current OFF/TC lineage and whole KSEED own export binding','C95 saved result-only scope; no timing/runtime C attribution','exact17 environment metered original fuel/caps/17 counters','bounded sampled journal and raw capture; no hard peak guarantee','existing memory refusals retained; termination-gap condition unchanged','one-child direct wait and permanent group retirement','two exact SOURCE review gates and GO; fresh namespace; valid-last completion'],'runtimeCalls':0,'C2':False,'performanceQualified':False}
report.update(loaderGrammar={'pinnedSource':dict(path=str(loaderSource),**h(loaderSource)),'firstSeparatorBeforeArityValidationConfirmed':True,'exact190TypedI64Cases':True,'misplacedSeparatorRefusals':190,'nativeGuestArgsAbsent':True},retainedV2Failure={'permanentFailure':True,'loaderCalls':1,'exit':2,'guestResults':0,'remaining':189,'independentProof':pr['retainedV2FailureProof']},v2RootReviewCorrection='Root V2 checked sealed argv against its own specification and missed the pinned loader grammar; V3 checks primary loader source order and both positive/negative interpretations. Old V2 SOURCE PASS and actual failure remain preserved.')
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'pins':len(ip),'report':h(D/'report.json')}))
