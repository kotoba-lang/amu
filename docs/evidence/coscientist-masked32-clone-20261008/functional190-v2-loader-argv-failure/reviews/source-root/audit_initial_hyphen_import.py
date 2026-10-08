from pathlib import Path
import json,hashlib,importlib.util,sys
S=Path('/Users/junkawasaki/github/workspaces/codex/tc-original19-functional190-source-v2-20261009')
D=Path(__file__).resolve().parent
sys.path.insert(0,str(S))
import run,pure_controls
def h(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sp=json.loads((S/'source-pins.json').read_bytes());ip=json.loads((S/'input-pins.json').read_bytes());pr=json.loads((S/'preregistration.json').read_bytes())
assert len(sp)==17 and len(ip)==2871
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
assert sum(r['bytes']for r in ip.values())==454726732
proofs=[json.loads(Path(pr[k]['path']).read_bytes())for k in ['OFFActualProof','TCActualProof','C95Oracle']]
assert run.source_scope(pr,*proofs)
controls=pure_controls.controls()
assert controls==json.loads((S/'pure-controls.json').read_bytes())
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
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'pins':len(ip),'report':h(D/'report.json')}))
