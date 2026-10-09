from pathlib import Path
import json,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'published-mode2-x8-build-fixture6-source-v1-20261009';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));import run
sp=run.load(S/'source-pins.json');ip=run.load(S/'input-pins.json');pr=run.load(S/'preregistration.json')
assert len(sp)==22 and len(ip)==47 and sum(r['bytes']for r in ip.values())==9076290
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
assert run.source_scope(pr,ip)
for n in ['pure-controls.json','wrapper-controls.json']:assert run.load(S/n)==run.load(D/n)
old=W/'tc-current7618-off18-compile36-source-v1-20261009'
unchanged=['capture.py','controller.py','integration.py','native-call.py','typed-adapter.py','runtime.py','artifact_admission.py','compiler_output.py']
for n in unchanged:assert(S/n).read_bytes()==(old/n).read_bytes()
assert pr['maximumLoaderCalls']==6 and not pr['clobberCertificateQualified']and not pr['candidateAdoptionQualified']
candidate=W/'published-mode2-x8-fuel-candidate-source-v1-20261009'
assert(S/'fixture.kotoba').read_bytes()==(candidate/'fixture.kotoba').read_bytes()and(S/'unity-candidate.kotoba').read_bytes()==(candidate/'unity-candidate.kotoba').read_bytes()
driver=(S/'run.py').read_text();wrapper=(S/'launch-wrapper.py').read_text()
assert driver.index("save(O/'terminal.json'")<driver.index("save(O/'report.json'")
assert "build_guard(load(producerBuild['path'])"in driver and "build_guard(json.loads(Path(seal['producerBuild']['path']).read_bytes())"in wrapper
assert "go['maximumLoaderCalls']==6"in wrapper and "if index>=5"in driver
assert pr['runtimeGuestAuthorized']is False and pr['timingAuthorized']is False and pr['C2']is False
report={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':run.receipt(S/'source-pins.json')['sha256'],'inputPinsSHA256':run.receipt(S/'input-pins.json')['sha256'],'driverSHA256':run.receipt(S/'run.py')['sha256'],'preregistrationSHA256':run.receipt(S/'preregistration.json')['sha256'],'sourceFiles':22,'inputFiles':47,'inputLogicalBytes':9076290,'fullPinsRehashed':True,'sourceScopeRecomputed':True,'qualifiedComponentsByteIdentical':unchanged,'fixtureAndCandidateBytesPreserved':True,'pureControls':run.load(D/'pure-controls.json'),'wrapperControls':run.load(D/'wrapper-controls.json'),'notes':['fixed six compiler/extract commands only; no synthetic guest runtime','exact current builder/OFF and own generated producer receipt+seal before use','primary argc6 arity0 guest -- grammar; exports/offsets resolved from full container','CPU/file/arena/environment preserved; sampled admission only; no hard-peak claim','valid-last terminal precedes complete; no retry/fresh namespace','candidate emitted x8/context entry/clobber proof remains HOLD'],'nativeCalls':0,'stageClobberCertificateQualified':False,'performanceQualified':False,'C2':False}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({'status':report['status'],'report':run.receipt(D/'report.json')})
